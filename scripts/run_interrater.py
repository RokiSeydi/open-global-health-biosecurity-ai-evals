#!/usr/bin/env python3
"""Inter-rater reliability analysis for model-as-judge grading.

Extracts model responses from existing eval logs and re-grades each response
with multiple grader models. Computes Krippendorff's alpha (ordinal) per
dimension and overall to measure grader agreement.

Addresses the Auditor's Blindspot: grader models may share epistemic priors
with the eval target, producing correlated errors rather than independent
assessments. Measuring inter-rater reliability quantifies this risk.

Usage:
    python scripts/run_interrater.py
    python scripts/run_interrater.py --epoch 1
    python scripts/run_interrater.py --domains 1 3
    python scripts/run_interrater.py --dry-run
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import math
import os
import sys
from pathlib import Path
from typing import Any

# Add project source to path for rubric imports
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT / "src"))

# Load API keys from .env
from dotenv import load_dotenv
load_dotenv(_PROJECT_ROOT / ".env")

# litellm expects GEMINI_API_KEY; project stores it as GOOGLE_API_KEY
if os.getenv("GOOGLE_API_KEY") and not os.getenv("GEMINI_API_KEY"):
    os.environ["GEMINI_API_KEY"] = os.environ["GOOGLE_API_KEY"]

from inspect_ai.log import list_eval_logs, read_eval_log, read_eval_log_samples

import anthropic
import openai
from google import genai

# Import rubric data from each domain
from global_health_ai_evals.domain1_cultural.domain1_rubric import (
    DIMENSION_ORDER as D1_ORDER,
    DIMENSION_PROMPTS as D1_PROMPTS,
    GRADER_SYSTEM_PROMPT as D1_SYSTEM_PROMPT,
)
from global_health_ai_evals.domain2_chw_competency.domain2_rubric import (
    DIMENSION_ORDER as D2_ORDER,
    DIMENSION_PROMPTS as D2_PROMPTS,
    GRADER_SYSTEM_PROMPT as D2_SYSTEM_PROMPT,
)
from global_health_ai_evals.domain3_fragile_health_systems.domain3_rubric import (
    DIMENSION_ORDER as D3_ORDER,
    DIMENSION_PROMPTS as D3_PROMPTS,
    GRADER_SYSTEM_PROMPT as D3_SYSTEM_PROMPT,
)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

GRADER_MODELS: list[str] = ["claude", "gpt4o", "gemini"]

DOMAIN_CONFIG: dict[str, dict[str, Any]] = {
    "1": {
        "system_prompt": D1_SYSTEM_PROMPT,
        "dimension_prompts": D1_PROMPTS,
        "dimension_order": D1_ORDER,
        "max_score": 18,
    },
    "2": {
        "system_prompt": D2_SYSTEM_PROMPT,
        "dimension_prompts": D2_PROMPTS,
        "dimension_order": D2_ORDER,
        "max_score": 27,
    },
    "3": {
        "system_prompt": D3_SYSTEM_PROMPT,
        "dimension_prompts": D3_PROMPTS,
        "dimension_order": D3_ORDER,
        "max_score": 24,
    },
}

LOG_DIRS: dict[str, dict[str, str]] = {
    "1": {
        "claude": "multi_epoch_d1_claude",
        "gpt4o": "multi_epoch_d1_gpt4o",
        "gemini": "multi_epoch_d1_gemini",
    },
    "2": {
        "claude": "multi_epoch_d2_claude",
        "gpt4o": "multi_epoch_d2_gpt4o",
        "gemini": "multi_epoch_d2_gemini",
    },
    "3": {
        "claude": "multi_epoch_d3_claude",
        "gpt4o": "multi_epoch_d3_gpt4o",
        "gemini": "multi_epoch_d3_gemini",
    },
}

# Concurrency control — avoid rate limits
_SEMAPHORE = asyncio.Semaphore(5)


# ---------------------------------------------------------------------------
# Response extraction
# ---------------------------------------------------------------------------


def _extract_model_name(eval_spec: Any) -> str:
    """Extract readable model name from eval spec."""
    model = eval_spec.model
    if hasattr(model, "name"):
        model = model.name
    return str(model)


def extract_responses(
    logs_root: Path,
    domains: list[str],
    target_epoch: int,
) -> list[dict[str, Any]]:
    """Extract model responses from eval logs for the specified epoch.

    Returns a list of dicts with keys:
        response_id, domain, eval_model, case_id, prompt_type, epoch,
        model_response, original_scores
    """
    responses: list[dict[str, Any]] = []

    for domain in domains:
        config = DOMAIN_CONFIG[domain]
        for model_key, log_subdir in LOG_DIRS[domain].items():
            log_dir = logs_root / log_subdir
            if not log_dir.exists():
                print(f"  SKIP: {log_dir} not found")
                continue

            logs = list_eval_logs(str(log_dir))
            if not logs:
                print(f"  SKIP: no logs in {log_dir}")
                continue

            for log_info in logs:
                log = read_eval_log(log_info.name)
                if log.status != "success":
                    continue

                eval_model = _extract_model_name(log.eval)

                for sample in read_eval_log_samples(log_info.name):
                    # Filter to target epoch
                    sample_epoch = getattr(sample, "epoch", 1)
                    if sample_epoch != target_epoch:
                        continue

                    if not sample.scores:
                        continue

                    # Get the model response
                    model_response = sample.output.completion if sample.output else ""
                    if not model_response:
                        continue

                    # Get metadata
                    sample_id = sample.id if hasattr(sample, "id") else "unknown"
                    metadata = {}
                    for _scorer_name, score_obj in sample.scores.items():
                        metadata = score_obj.metadata or {}
                        break

                    case_id = metadata.get("case_id", "")
                    if not case_id:
                        # D1 has a single case; derive from sample id
                        sid = str(sample_id)
                        if "IT_001" in sid:
                            case_id = "D1_IT_001"
                        else:
                            case_id = f"D{domain}_unknown"
                    prompt_type = metadata.get("prompt_type", "unknown")
                    original_dim_scores = metadata.get("dimension_scores", {})

                    response_id = (
                        f"D{domain}_{model_key}_{case_id}_{prompt_type}_e{target_epoch}"
                    )

                    responses.append({
                        "response_id": response_id,
                        "domain": domain,
                        "eval_model": model_key,
                        "case_id": case_id,
                        "prompt_type": prompt_type,
                        "epoch": target_epoch,
                        "model_response": model_response,
                        "original_scores": original_dim_scores,
                        "sample_id": sample_id,
                    })

    return responses


# ---------------------------------------------------------------------------
# Grading
# ---------------------------------------------------------------------------


# SDK clients — initialised lazily
_anthropic_client: anthropic.AsyncAnthropic | None = None
_openai_client: openai.AsyncOpenAI | None = None
_gemini_client: genai.Client | None = None


def _get_anthropic() -> anthropic.AsyncAnthropic:
    global _anthropic_client
    if _anthropic_client is None:
        _anthropic_client = anthropic.AsyncAnthropic()
    return _anthropic_client


def _get_openai() -> openai.AsyncOpenAI:
    global _openai_client
    if _openai_client is None:
        _openai_client = openai.AsyncOpenAI()
    return _openai_client


def _get_gemini() -> genai.Client:
    global _gemini_client
    if _gemini_client is None:
        _gemini_client = genai.Client(api_key=os.environ.get("GOOGLE_API_KEY"))
    return _gemini_client


async def _call_anthropic(
    system_prompt: str, user_input: str,
) -> str:
    """Call Anthropic Claude Sonnet."""
    client = _get_anthropic()
    response = await client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=150,
        temperature=0.0,
        system=system_prompt,
        messages=[{"role": "user", "content": user_input}],
    )
    return response.content[0].text.strip()


async def _call_openai(
    system_prompt: str, user_input: str,
) -> str:
    """Call OpenAI GPT-4o."""
    client = _get_openai()
    response = await client.chat.completions.create(
        model="gpt-4o",
        max_tokens=150,
        temperature=0.0,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input},
        ],
    )
    return response.choices[0].message.content.strip()


async def _call_gemini(
    system_prompt: str, user_input: str,
) -> str:
    """Call Google Gemini 2.5 Pro."""
    client = _get_gemini()
    # google-genai uses sync API; run in executor
    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(
        None,
        lambda: client.models.generate_content(
            model="gemini-2.5-pro",
            contents=f"{system_prompt}\n\n{user_input}",
            config=genai.types.GenerateContentConfig(
                temperature=0.0,
                max_output_tokens=2000,  # Gemini 2.5 Pro uses thinking tokens
            ),
        ),
    )
    text = response.text
    if text is None:
        raise ValueError(f"Gemini returned no text. Finish reason: {response.candidates[0].finish_reason if response.candidates else 'unknown'}")
    return text.strip()


_CALLERS = {
    "claude": _call_anthropic,
    "gpt4o": _call_openai,
    "gemini": _call_gemini,
}


async def grade_dimension(
    grader_model: str,
    system_prompt: str,
    dim_prompt: str,
    model_response: str,
) -> tuple[int, str]:
    """Grade a single dimension using the specified grader model.

    Returns (score, rationale).
    """
    grader_input = f"""{dim_prompt}

--- MODEL RESPONSE TO EVALUATE ---
{model_response}
---

Score this response. Respond with JSON only."""

    caller = _CALLERS[grader_model]

    async with _SEMAPHORE:
        try:
            completion = await caller(system_prompt, grader_input)

            # Strip markdown fences if present
            if completion.startswith("```"):
                completion = completion.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

            result = json.loads(completion)
            score = max(0, min(3, int(result["score"])))
            rationale = str(result.get("rationale", ""))
            return score, rationale

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            return 0, f"Parse error: {e}"
        except Exception as e:
            print(f"      API ERROR ({grader_model}): {type(e).__name__}: {e}")
            return -1, f"API error: {e}"


async def grade_response(
    response: dict[str, Any],
    grader_model: str,
    domain_config: dict[str, Any],
) -> dict[str, int]:
    """Grade all dimensions for a single response with a single grader.

    Returns dict mapping dimension_id -> score.
    """
    tasks = []
    dim_ids = []

    for dim_id in domain_config["dimension_order"]:
        dim_prompt = domain_config["dimension_prompts"][dim_id]
        tasks.append(
            grade_dimension(
                grader_model=grader_model,
                system_prompt=domain_config["system_prompt"],
                dim_prompt=dim_prompt,
                model_response=response["model_response"],
            )
        )
        dim_ids.append(dim_id)

    results = await asyncio.gather(*tasks)

    scores: dict[str, int] = {}
    for dim_id, (score, _rationale) in zip(dim_ids, results):
        scores[dim_id] = score

    return scores


async def run_all_grading(
    responses: list[dict[str, Any]],
    domains: list[str],
) -> list[dict[str, Any]]:
    """Grade all responses with all grader models.

    Returns list of dicts with keys:
        response_id, domain, eval_model, case_id, prompt_type,
        grader_model, dimension_id, score
    """
    all_records: list[dict[str, Any]] = []
    total = len(responses) * len(GRADER_MODELS)
    completed = 0

    for response in responses:
        domain = response["domain"]
        config = DOMAIN_CONFIG[domain]

        for grader_model in GRADER_MODELS:
            grader_short = grader_model
            completed += 1
            print(
                f"  [{completed}/{total}] Grading {response['response_id']} "
                f"with {grader_short}..."
            )

            dim_scores = await grade_response(response, grader_model, config)

            for dim_id, score in dim_scores.items():
                all_records.append({
                    "response_id": response["response_id"],
                    "domain": domain,
                    "eval_model": response["eval_model"],
                    "case_id": response["case_id"],
                    "prompt_type": response["prompt_type"],
                    "grader_model": grader_short,
                    "dimension_id": dim_id,
                    "score": score,
                })

    return all_records


# ---------------------------------------------------------------------------
# Krippendorff's alpha (ordinal)
# ---------------------------------------------------------------------------


def krippendorff_alpha_ordinal(
    ratings: list[list[int | None]],
    levels: int = 4,
) -> float:
    """Compute Krippendorff's alpha for ordinal data.

    Args:
        ratings: list of items, each item is a list of rater scores
                 (None = missing). Each inner list has one entry per rater.
        levels: number of ordinal levels (4 for 0-3 scale).

    Returns:
        Alpha value. 1.0 = perfect agreement, 0.0 = chance, <0 = worse than chance.
    """
    # Build coincidence matrix
    n_raters = len(ratings[0]) if ratings else 0
    if n_raters < 2:
        return float("nan")

    # Ordinal distance metric: d²(c,k) = sum over g from c to k of (n_g)
    # For simplicity, use squared difference as distance (interval assumption
    # is common for 0-3 scales and produces similar results to ordinal for
    # small number of levels)
    coincidence: dict[tuple[int, int], float] = {}
    marginals: dict[int, float] = {}
    n_total = 0.0

    for item_ratings in ratings:
        present = [r for r in item_ratings if r is not None and r >= 0]
        m = len(present)
        if m < 2:
            continue

        for i in range(m):
            for j in range(m):
                if i == j:
                    continue
                c, k = present[i], present[j]
                key = (c, k)
                coincidence[key] = coincidence.get(key, 0) + 1.0 / (m - 1)

            marginals[present[i]] = marginals.get(present[i], 0) + 1.0
            n_total += 1.0

    if n_total == 0:
        return float("nan")

    # Observed disagreement
    d_o = 0.0
    for (c, k), count in coincidence.items():
        d_o += count * (c - k) ** 2
    d_o /= n_total

    # Expected disagreement
    d_e = 0.0
    for c in range(levels):
        for k in range(levels):
            n_c = marginals.get(c, 0)
            n_k = marginals.get(k, 0)
            d_e += n_c * n_k * (c - k) ** 2
    d_e /= n_total * (n_total - 1)

    if d_e == 0:
        return 1.0

    return 1.0 - d_o / d_e


def compute_agreement(
    records: list[dict[str, Any]],
) -> dict[str, Any]:
    """Compute Krippendorff's alpha from grading records.

    Returns dict with:
        overall_alpha, per_dimension alpha, per_domain alpha,
        agreement_matrix (pairwise)
    """
    grader_list = sorted(set(r["grader_model"] for r in records))
    grader_idx = {g: i for i, g in enumerate(grader_list)}
    n_graders = len(grader_list)

    # Group by (response_id, dimension_id) — each gets n_graders ratings
    from collections import defaultdict

    rating_map: dict[tuple[str, str], list[int | None]] = defaultdict(
        lambda: [None] * n_graders
    )

    for r in records:
        key = (r["response_id"], r["dimension_id"])
        gi = grader_idx[r["grader_model"]]
        rating_map[key][gi] = r["score"]

    # Overall alpha
    all_ratings = list(rating_map.values())
    overall_alpha = krippendorff_alpha_ordinal(all_ratings)

    # Per-dimension alpha
    dimensions = sorted(set(r["dimension_id"] for r in records))
    dim_alphas: dict[str, float] = {}
    for dim in dimensions:
        dim_ratings = [
            v for (_, d), v in rating_map.items() if d == dim
        ]
        if len(dim_ratings) >= 2:
            dim_alphas[dim] = krippendorff_alpha_ordinal(dim_ratings)
        else:
            dim_alphas[dim] = float("nan")

    # Per-domain alpha
    domains = sorted(set(r["domain"] for r in records))
    domain_alphas: dict[str, float] = {}
    for domain in domains:
        domain_dims = [d for d in dimensions if d.startswith(f"D{domain}_")]
        domain_ratings = [
            v for (_, d), v in rating_map.items() if d in domain_dims
        ]
        if len(domain_ratings) >= 2:
            domain_alphas[domain] = krippendorff_alpha_ordinal(domain_ratings)
        else:
            domain_alphas[domain] = float("nan")

    # Pairwise agreement (percentage of exact matches)
    pairwise: dict[tuple[str, str], dict[str, float]] = {}
    for i, g1 in enumerate(grader_list):
        for j, g2 in enumerate(grader_list):
            if i >= j:
                continue
            exact = 0
            within_one = 0
            total = 0
            for ratings in all_ratings:
                s1, s2 = ratings[i], ratings[j]
                if s1 is None or s2 is None or s1 < 0 or s2 < 0:
                    continue
                total += 1
                if s1 == s2:
                    exact += 1
                if abs(s1 - s2) <= 1:
                    within_one += 1
            if total > 0:
                pairwise[(g1, g2)] = {
                    "exact_match": exact / total,
                    "within_one": within_one / total,
                    "n": total,
                }

    # Score distribution per grader
    grader_distributions: dict[str, dict[int, int]] = {}
    for g in grader_list:
        dist: dict[int, int] = {0: 0, 1: 0, 2: 0, 3: 0}
        for r in records:
            if r["grader_model"] == g and r["score"] >= 0:
                dist[r["score"]] = dist.get(r["score"], 0) + 1
        grader_distributions[g] = dist

    # Mean score per grader
    grader_means: dict[str, float] = {}
    for g in grader_list:
        scores = [r["score"] for r in records if r["grader_model"] == g and r["score"] >= 0]
        grader_means[g] = sum(scores) / len(scores) if scores else 0.0

    return {
        "overall_alpha": overall_alpha,
        "dimension_alphas": dim_alphas,
        "domain_alphas": domain_alphas,
        "pairwise_agreement": pairwise,
        "grader_distributions": grader_distributions,
        "grader_means": grader_means,
        "n_items": len(all_ratings),
        "n_graders": n_graders,
        "grader_list": grader_list,
    }


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


def print_results(agreement: dict[str, Any]) -> None:
    """Print a human-readable summary of inter-rater reliability results."""
    print("\n" + "=" * 80)
    print("  INTER-RATER RELIABILITY ANALYSIS")
    print("  Open Global Health & Biosecurity AI Evaluations")
    print("=" * 80)

    print(f"\n  Graders:    {', '.join(agreement['grader_list'])}")
    print(f"  Items:      {agreement['n_items']} (response × dimension pairs)")
    print(f"  Raters:     {agreement['n_graders']}")

    # Overall alpha
    alpha = agreement["overall_alpha"]
    interpretation = (
        "excellent" if alpha >= 0.80
        else "good" if alpha >= 0.67
        else "tentative" if alpha >= 0.40
        else "poor"
    )
    print(f"\n  OVERALL Krippendorff's alpha: {alpha:.3f} ({interpretation})")

    # Per-domain alpha
    print(f"\n  PER-DOMAIN ALPHA:")
    domain_names = {"1": "Cultural Contextual Validity", "2": "CHW Competency", "3": "Fragile Health Systems"}
    for domain, a in sorted(agreement["domain_alphas"].items()):
        name = domain_names.get(domain, f"Domain {domain}")
        interp = (
            "excellent" if a >= 0.80
            else "good" if a >= 0.67
            else "tentative" if a >= 0.40
            else "poor"
        )
        print(f"    D{domain} ({name}): {a:.3f} ({interp})")

    # Per-dimension alpha
    print(f"\n  PER-DIMENSION ALPHA:")
    print(f"    {'Dimension':<40} {'Alpha':>7} {'Level':>12}")
    print(f"    {'─' * 60}")
    for dim, a in sorted(agreement["dimension_alphas"].items()):
        interp = (
            "excellent" if a >= 0.80
            else "good" if a >= 0.67
            else "tentative" if a >= 0.40
            else "poor" if not math.isnan(a)
            else "N/A"
        )
        a_str = f"{a:.3f}" if not math.isnan(a) else "N/A"
        print(f"    {dim:<40} {a_str:>7} {interp:>12}")

    # Pairwise agreement
    print(f"\n  PAIRWISE AGREEMENT:")
    print(f"    {'Pair':<30} {'Exact':>7} {'±1':>7} {'N':>6}")
    print(f"    {'─' * 52}")
    for (g1, g2), stats in sorted(agreement["pairwise_agreement"].items()):
        label = f"{g1} × {g2}"
        print(
            f"    {label:<30} {stats['exact_match']:>6.1%} "
            f"{stats['within_one']:>6.1%} {stats['n']:>6.0f}"
        )

    # Grader means (detect systematic bias)
    print(f"\n  GRADER MEAN SCORES (detect systematic bias):")
    for g, m in sorted(agreement["grader_means"].items()):
        print(f"    {g:<20} {m:.2f}/3")

    # Score distributions
    print(f"\n  SCORE DISTRIBUTIONS:")
    print(f"    {'Grader':<20} {'0':>5} {'1':>5} {'2':>5} {'3':>5}")
    print(f"    {'─' * 42}")
    for g, dist in sorted(agreement["grader_distributions"].items()):
        total = sum(dist.values())
        print(
            f"    {g:<20} "
            f"{dist.get(0, 0)/total:>4.0%} "
            f"{dist.get(1, 0)/total:>4.0%} "
            f"{dist.get(2, 0)/total:>4.0%} "
            f"{dist.get(3, 0)/total:>4.0%}"
        )

    # Interpretation
    print(f"\n  INTERPRETATION:")
    if alpha >= 0.80:
        print("    Excellent agreement across graders. Model-as-judge scores are")
        print("    reliable. The Auditor's Blindspot risk is LOW for this data.")
    elif alpha >= 0.67:
        print("    Good agreement across graders. Model-as-judge scores are usable")
        print("    for tentative conclusions. Some Auditor's Blindspot risk remains.")
    elif alpha >= 0.40:
        print("    Tentative agreement only. Model-as-judge scores show meaningful")
        print("    grader disagreement. Auditor's Blindspot risk is MODERATE.")
        print("    Dimension-level scores should be interpreted cautiously.")
    else:
        print("    Poor agreement. Model-as-judge grading is unreliable for this data.")
        print("    Auditor's Blindspot risk is HIGH. Dimension scores may reflect")
        print("    grader priors rather than response quality.")

    print("\n" + "=" * 80)


def write_csv(
    records: list[dict[str, Any]],
    agreement: dict[str, Any],
    output_dir: Path,
) -> None:
    """Write detailed results to CSV files."""
    output_dir.mkdir(parents=True, exist_ok=True)

    # Raw scores
    csv_path = output_dir / "interrater_raw_scores.csv"
    fieldnames = [
        "response_id", "domain", "eval_model", "case_id",
        "prompt_type", "grader_model", "dimension_id", "score",
    ]
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in records:
            writer.writerow({k: r[k] for k in fieldnames})
    print(f"  Wrote: {csv_path}")

    # Alpha summary
    alpha_path = output_dir / "interrater_alpha_summary.csv"
    with open(alpha_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["level", "dimension", "alpha"])
        writer.writerow(["overall", "all", f"{agreement['overall_alpha']:.4f}"])
        for domain, a in sorted(agreement["domain_alphas"].items()):
            writer.writerow([f"domain_{domain}", "all", f"{a:.4f}"])
        for dim, a in sorted(agreement["dimension_alphas"].items()):
            a_str = f"{a:.4f}" if not math.isnan(a) else "NaN"
            writer.writerow(["dimension", dim, a_str])
    print(f"  Wrote: {alpha_path}")

    # Pairwise agreement
    pair_path = output_dir / "interrater_pairwise.csv"
    with open(pair_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["grader_1", "grader_2", "exact_match", "within_one", "n"])
        for (g1, g2), stats in sorted(agreement["pairwise_agreement"].items()):
            writer.writerow([
                g1, g2,
                f"{stats['exact_match']:.4f}",
                f"{stats['within_one']:.4f}",
                int(stats["n"]),
            ])
    print(f"  Wrote: {pair_path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


async def async_main(args: argparse.Namespace) -> None:
    """Main async entry point."""
    logs_root = _PROJECT_ROOT / "logs"
    output_dir = _PROJECT_ROOT / "results"

    domains = [str(d) for d in args.domains]
    print(f"Inter-rater reliability analysis")
    print(f"  Domains:       {domains}")
    print(f"  Target epoch:  {args.epoch}")
    print(f"  Grader models: {GRADER_MODELS}", flush=True)
    print(flush=True)

    # Step 1: Extract responses
    print("Step 1: Extracting model responses from eval logs...")
    responses = extract_responses(logs_root, domains, args.epoch)
    print(f"  Found {len(responses)} responses to re-grade")

    if not responses:
        print("  ERROR: No responses found. Check log directories.")
        sys.exit(1)

    if args.dry_run:
        print("\n  DRY RUN — would grade these responses:")
        for r in responses:
            print(f"    {r['response_id']}")
        n_calls = len(responses) * len(GRADER_MODELS) * sum(
            len(DOMAIN_CONFIG[d]["dimension_order"]) for d in domains
        ) // len(domains)
        print(f"\n  Total API calls: ~{n_calls}")
        print(f"  Estimated cost:  ~${n_calls * 0.003:.2f} (rough)")
        return

    # Step 2: Grade all responses with all grader models
    print(f"\nStep 2: Grading {len(responses)} responses × {len(GRADER_MODELS)} graders...")
    records = await run_all_grading(responses, domains)

    # Filter out API errors
    errors = [r for r in records if r["score"] < 0]
    if errors:
        print(f"\n  WARNING: {len(errors)} API errors encountered")
        for e in errors[:5]:
            print(f"    {e['response_id']} / {e['grader_model']} / {e['dimension_id']}")
    records = [r for r in records if r["score"] >= 0]

    # Step 3: Compute agreement
    print(f"\nStep 3: Computing agreement metrics ({len(records)} valid scores)...")
    agreement = compute_agreement(records)

    # Step 4: Output
    print_results(agreement)
    write_csv(records, agreement, output_dir)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Inter-rater reliability analysis for model-as-judge grading"
    )
    parser.add_argument(
        "--epoch", type=int, default=1,
        help="Which epoch to re-grade (default: 1)",
    )
    parser.add_argument(
        "--domains", nargs="+", type=int, default=[1, 2, 3],
        choices=[1, 2, 3],
        help="Domains to analyse (default: all)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Show what would be graded without making API calls",
    )
    args = parser.parse_args()
    asyncio.run(async_main(args))


if __name__ == "__main__":
    main()
