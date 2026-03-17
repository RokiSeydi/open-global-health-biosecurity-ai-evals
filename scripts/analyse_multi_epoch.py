#!/usr/bin/env python3
"""Statistical analysis of multi-epoch evaluation results.

Reads all eval logs from a multi-epoch run directory, extracts per-dimension
scores, and computes:
    - Per-model, per-condition means and standard errors
    - Per-dimension variance across epochs
    - Gap (scaffolded - unscaffolded) with confidence intervals
    - Summary table for publication

Usage:
    python scripts/analyse_multi_epoch.py --log-dir logs/multi_epoch_20260316_...
"""

from __future__ import annotations

import argparse
import csv
import math
import sys
from pathlib import Path
from typing import Any

from inspect_ai.log import list_eval_logs, read_eval_log, read_eval_log_samples


DIMENSION_ORDER: list[str] = [
    "D1_narrative_arc",
    "D1_institutional_reflex",
    "D1_intent_recognition",
    "D1_compliance_framing",
    "D1_register_respect",
    "D1_contextual_proportionality",
]


def extract_model_name(eval_spec: Any) -> str:
    """Extract a readable model name from the eval spec."""
    model = eval_spec.model
    if hasattr(model, "name"):
        model = model.name
    model = str(model)
    for prefix in ("anthropic/", "openai/", "google/"):
        if model.startswith(prefix):
            model = model[len(prefix):]
    return model


def extract_all_results(log_dir: str) -> list[dict[str, Any]]:
    """Extract scored results from all eval logs."""
    records: list[dict[str, Any]] = []
    logs = list_eval_logs(log_dir)

    if not logs:
        print(f"No eval logs found in {log_dir}")
        sys.exit(1)

    for log_info in logs:
        log = read_eval_log(log_info.name)
        if log.status != "success":
            continue

        model_name: str = extract_model_name(log.eval)

        for sample in read_eval_log_samples(log_info.name):
            if not sample.scores:
                continue
            for scorer_name, score_obj in sample.scores.items():
                metadata: dict[str, Any] = score_obj.metadata or {}
                dimension_scores: dict[str, int] = metadata.get("dimension_scores", {})
                if not dimension_scores:
                    continue
                records.append({
                    "model": model_name,
                    "prompt_type": metadata.get("prompt_type", "unknown"),
                    "total_score": metadata.get("total_score", 0),
                    "outcome": metadata.get("outcome", "unknown"),
                    "gate_triggered": metadata.get("gate_triggered", False),
                    "dimension_scores": dimension_scores,
                })

    return records


def mean(values: list[float]) -> float:
    """Compute mean."""
    if not values:
        return 0.0
    return sum(values) / len(values)


def std_err(values: list[float]) -> float:
    """Compute standard error of the mean."""
    n = len(values)
    if n < 2:
        return 0.0
    m = mean(values)
    variance = sum((x - m) ** 2 for x in values) / (n - 1)
    return math.sqrt(variance / n)


def std_dev(values: list[float]) -> float:
    """Compute sample standard deviation."""
    n = len(values)
    if n < 2:
        return 0.0
    m = mean(values)
    variance = sum((x - m) ** 2 for x in values) / (n - 1)
    return math.sqrt(variance)


def analyse(records: list[dict[str, Any]], output_dir: Path) -> None:
    """Run full statistical analysis and print results."""
    # Group by model and condition
    grouped: dict[str, dict[str, list[dict[str, Any]]]] = {}
    for r in records:
        model = r["model"]
        pt = r["prompt_type"]
        if model not in grouped:
            grouped[model] = {}
        if pt not in grouped[model]:
            grouped[model][pt] = []
        grouped[model][pt].append(r)

    print("\n" + "=" * 80)
    print("MULTI-EPOCH STATISTICAL ANALYSIS — DOMAIN 1: CULTURAL CONTEXTUAL VALIDITY")
    print("=" * 80)

    all_rows: list[dict[str, Any]] = []

    for model in sorted(grouped.keys()):
        print(f"\n{'─'*80}")
        print(f"  MODEL: {model}")
        print(f"{'─'*80}")

        for condition in ["unscaffolded", "scaffolded"]:
            runs = grouped[model].get(condition, [])
            if not runs:
                continue

            totals: list[float] = [r["total_score"] for r in runs]
            n = len(totals)

            print(f"\n  {condition.upper()} (n={n})")
            print(f"    Total score:  {mean(totals):.1f}/18  "
                  f"(SD={std_dev(totals):.2f}, SE={std_err(totals):.2f})")
            print(f"    Range:        {min(totals):.0f} – {max(totals):.0f}")
            print(f"    Raw scores:   {[int(t) for t in totals]}")

            # Per-dimension analysis
            print(f"    {'Dimension':<35} {'Mean':>5} {'SD':>6} {'SE':>6} {'Range':>8}")
            print(f"    {'─'*60}")

            row: dict[str, Any] = {
                "model": model,
                "condition": condition,
                "n": n,
                "total_mean": round(mean(totals), 2),
                "total_sd": round(std_dev(totals), 2),
                "total_se": round(std_err(totals), 2),
            }

            for dim in DIMENSION_ORDER:
                dim_vals: list[float] = [
                    r["dimension_scores"].get(dim, 0) for r in runs
                ]
                m = mean(dim_vals)
                sd = std_dev(dim_vals)
                se = std_err(dim_vals)
                short_dim = dim.replace("D1_", "")
                print(f"    {short_dim:<35} {m:>5.2f} {sd:>6.2f} {se:>6.2f} "
                      f"{min(dim_vals):.0f}–{max(dim_vals):.0f}")
                row[f"{dim}_mean"] = round(m, 2)
                row[f"{dim}_sd"] = round(sd, 2)

            # Outcomes
            outcomes: list[str] = [r["outcome"] for r in runs]
            outcome_counts: dict[str, int] = {}
            for o in outcomes:
                outcome_counts[o] = outcome_counts.get(o, 0) + 1
            print(f"    Outcomes:     {outcome_counts}")

            gates = sum(1 for r in runs if r["gate_triggered"])
            if gates > 0:
                print(f"    Gate triggered: {gates}/{n} runs")

            all_rows.append(row)

        # Gap analysis
        unscaffolded_runs = grouped[model].get("unscaffolded", [])
        scaffolded_runs = grouped[model].get("scaffolded", [])

        if unscaffolded_runs and scaffolded_runs:
            u_totals: list[float] = [r["total_score"] for r in unscaffolded_runs]
            s_totals: list[float] = [r["total_score"] for r in scaffolded_runs]
            u_mean = mean(u_totals)
            s_mean = mean(s_totals)
            gap = s_mean - u_mean

            # Gap SE (assuming independent samples)
            gap_se = math.sqrt(std_err(u_totals) ** 2 + std_err(s_totals) ** 2)
            ci_95_lower = gap - 1.96 * gap_se
            ci_95_upper = gap + 1.96 * gap_se

            print(f"\n  GAP ANALYSIS")
            print(f"    Unscaffolded mean: {u_mean:.1f}/18")
            print(f"    Scaffolded mean:   {s_mean:.1f}/18")
            print(f"    Gap:               +{gap:.1f}")
            print(f"    Gap SE:            {gap_se:.2f}")
            print(f"    95% CI:            [{ci_95_lower:.1f}, {ci_95_upper:.1f}]")
            print(f"    Hypothesis (>=4):  "
                  f"{'SUPPORTED' if ci_95_lower >= 4 else 'NOT YET SUPPORTED' if gap >= 4 else 'NOT SUPPORTED'}")

    # Write CSV
    if all_rows:
        csv_path = output_dir / "multi_epoch_stats.csv"
        fieldnames = list(all_rows[0].keys())
        with open(csv_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in all_rows:
                writer.writerow(row)
        print(f"\n  Wrote: {csv_path}")

    print("\n" + "=" * 80)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analyse multi-epoch evaluation results"
    )
    parser.add_argument(
        "--log-dir", required=True,
        help="Directory containing multi-epoch eval logs",
    )
    args = parser.parse_args()

    log_dir = Path(args.log_dir)
    if not log_dir.exists():
        print(f"Log directory not found: {log_dir}")
        sys.exit(1)

    output_dir = Path(__file__).resolve().parent.parent / "results"
    output_dir.mkdir(exist_ok=True)

    records = extract_all_results(str(log_dir))
    print(f"Found {len(records)} scored results")
    analyse(records, output_dir)


if __name__ == "__main__":
    main()
