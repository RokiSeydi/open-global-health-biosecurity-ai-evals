"""Domain 2: CHW Competency & Task-Shifting — Inspect Task Definitions.

Tests whether AI clinical guidance is calibrated to CHW competency, scope of
practice, and resource constraints — or whether it defaults to specialist-level
recommendations that could be dangerous in a CHW setting.

Two tasks:
    chw_competency_eval       — Primary eval (filterable by prompt_type)
    chw_competency_gap_analysis — Both conditions for gap measurement

Grader model auto-detection:
    When evaluating Claude  → GPT-4o as grader
    When evaluating GPT     → Claude Sonnet as grader
    When evaluating Gemini  → Claude Sonnet as grader

Based on: WHO Task Shifting (2008), WHO CHW Guidelines (2018), iCCM/IMCI,
MSF Clinical Guidelines (2023), CHIC best practices.

Six failure modes:
    - Task inflation
    - False universalism in resource assumptions
    - Decontextualization
    - Danger sign blindness
    - Broken referral pathways
    - Procedural care without calibration
"""

from __future__ import annotations

import json
from pathlib import Path

from inspect_ai import Task, task
from inspect_ai.dataset import MemoryDataset, Sample
from inspect_ai.solver import generate

from global_health_ai_evals.domain2_chw_competency.domain2_rubric import (
    chw_competency_scorer,
)
from global_health_ai_evals.metadata import load_eval_metadata

EVAL_VERSION = load_eval_metadata("domain2_chw_competency").version


def _resolve_dataset_path() -> Path:
    """Resolve the JSONL dataset path relative to the project root."""
    current = Path(__file__).resolve().parent
    for _ in range(5):
        candidate = current / "datasets" / "domain2_chw_competency_inspect.jsonl"
        if candidate.exists():
            return candidate
        current = current.parent
    raise FileNotFoundError(
        "Cannot find datasets/domain2_chw_competency_inspect.jsonl. "
        "Run: python scripts/generate_inspect_dataset.py"
    )


def load_inspect_dataset() -> MemoryDataset:
    """Load the Inspect-compatible JSONL dataset."""
    path = _resolve_dataset_path()
    samples: list[Sample] = []
    with open(path) as f:
        for line in f:
            if line.strip():
                record: dict[str, object] = json.loads(line)
                samples.append(Sample(
                    id=str(record["id"]),
                    input=str(record["input"]),
                    target=str(record["target"]),
                    metadata=record.get("metadata", {}),
                ))
    return MemoryDataset(samples=samples, name="domain2_chw_competency")


def _auto_grader_model(eval_model: str | None) -> str:
    """Select a grader model that differs from the model being evaluated.

    Rules:
        Claude models     → use OpenAI GPT-4o as grader
        OpenAI models     → use Anthropic Claude Sonnet as grader
        Google models     → use Anthropic Claude Sonnet as grader
        DeepSeek models   → use Anthropic Claude Sonnet as grader
        Meta/Llama models → use Anthropic Claude Sonnet as grader
        Unknown/None      → default to Anthropic Claude Sonnet
    """
    if eval_model is None:
        return "anthropic/claude-sonnet-4-20250514"

    model_lower = eval_model.lower()
    if "anthropic" in model_lower or "claude" in model_lower:
        return "openai/gpt-4o"
    else:
        return "anthropic/claude-sonnet-4-20250514"


@task
def chw_competency_eval(
    prompt_type: str = "unscaffolded",
    eval_model: str | None = None,
    grader_model: str | None = None,
) -> Task:
    """Domain 2: CHW Competency & Task-Shifting evaluation.

    Tests whether AI clinical guidance is calibrated to CHW competency,
    scope of practice, and resource constraints.

    Args:
        prompt_type: "unscaffolded" (primary eval) or "scaffolded" (ceiling reference).
        eval_model: Model being evaluated (used for auto grader selection).
            If None, auto-detection reads from the Inspect CLI --model flag.
        grader_model: Explicit grader model override. If None, auto-selects
            a grader that differs from the eval model.

    Returns:
        Task for CHW competency evaluation.
    """
    dataset = load_inspect_dataset()

    filtered = MemoryDataset(
        samples=[
            s for s in dataset.samples
            if s.metadata.get("prompt_type") == prompt_type
        ],
        name=f"domain2_chw_competency_{prompt_type}",
    )

    resolved_grader: str = grader_model or _auto_grader_model(eval_model)

    return Task(
        dataset=filtered,
        solver=[generate()],
        scorer=chw_competency_scorer(),
        model_roles={"grader": resolved_grader},
        version=EVAL_VERSION.comparability_version,
        metadata={
            **EVAL_VERSION.to_metadata(),
            "eval_framework": "Open Global Health & Biosecurity AI Evaluations",
            "domain": "2",
            "domain_name": "CHW Competency & Task-Shifting",
            "prompt_type": prompt_type,
            "grader_model": resolved_grader,
            "grader_selection": "auto" if grader_model is None else "manual",
        },
    )


@task
def chw_competency_gap_analysis(
    eval_model: str | None = None,
    grader_model: str | None = None,
) -> Task:
    """Run both unscaffolded and scaffolded conditions to measure the gap.

    The gap (scaffolded_score - unscaffolded_score) measures the degree to
    which the model's CHW-appropriate guidance depends on the user explicitly
    providing scope and resource constraints that real CHW users cannot be
    expected to provide.

    Args:
        eval_model: Model being evaluated (used for auto grader selection).
        grader_model: Explicit grader model override.

    Returns:
        Task for gap analysis evaluation.
    """
    dataset = load_inspect_dataset()

    resolved_grader: str = grader_model or _auto_grader_model(eval_model)

    return Task(
        dataset=dataset,
        solver=[generate()],
        scorer=chw_competency_scorer(),
        model_roles={"grader": resolved_grader},
        version=EVAL_VERSION.comparability_version,
        metadata={
            **EVAL_VERSION.to_metadata(),
            "eval_framework": "Open Global Health & Biosecurity AI Evaluations",
            "domain": "2",
            "eval_type": "gap_analysis",
            "grader_model": resolved_grader,
            "gap_hypothesis": (
                "All frontier models show measurable delta between scaffolded "
                "and unscaffolded conditions on CHW competency calibration"
            ),
        },
    )
