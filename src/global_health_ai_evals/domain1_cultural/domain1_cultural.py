"""Domain 1: Cultural Contextual Validity — Inspect Task Definitions.

Tests whether frontier LLMs demonstrate cultural contextual validity when
interpreting longitudinal immigrant health narratives.

Two tasks:
    cultural_confabulation_eval       — Primary eval (filterable by prompt_type)
    cultural_confabulation_gap_analysis — Both conditions for gap measurement

Grader model auto-detection:
    When evaluating Claude  → GPT-4o as grader
    When evaluating GPT     → Claude Sonnet as grader
    When evaluating Gemini  → Claude Sonnet as grader

Based on documented failure modes from real-world experiment:
    - Temporal flattening
    - Institutional reflex
    - Compliance framing
    - Role collapse
    - Over-medicalization
    - Procedural care without interpretation

Reference: Seydi, R. (2026). Cultural Confabulation: A Structural Evaluation Gap
in Large Language Model Reasoning.
"""

from __future__ import annotations

import json
from pathlib import Path

from inspect_ai import Task, task
from inspect_ai.dataset import MemoryDataset, Sample
from inspect_ai.solver import generate

from global_health_ai_evals.domain1_cultural.domain1_rubric import (
    cultural_confabulation_scorer,
)
from global_health_ai_evals.metadata import load_eval_metadata

EVAL_VERSION = load_eval_metadata("domain1_cultural").version


def _resolve_dataset_path() -> Path:
    """Resolve the JSONL dataset path relative to the project root."""
    current = Path(__file__).resolve().parent
    for _ in range(5):
        candidate = current / "datasets" / "domain1_cultural_inspect.jsonl"
        if candidate.exists():
            return candidate
        current = current.parent
    raise FileNotFoundError(
        "Cannot find datasets/domain1_cultural_inspect.jsonl. "
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
    return MemoryDataset(samples=samples, name="domain1_cultural")


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
def cultural_confabulation_eval(
    prompt_type: str = "unscaffolded",
    eval_model: str | None = None,
    grader_model: str | None = None,
) -> Task:
    """Domain 1: Cultural Contextual Validity evaluation.

    Tests whether frontier LLMs demonstrate cultural contextual validity
    when interpreting longitudinal immigrant health narratives.

    Args:
        prompt_type: "unscaffolded" (primary eval) or "scaffolded" (ceiling reference).
        eval_model: Model being evaluated (used for auto grader selection).
            If None, auto-detection reads from the Inspect CLI --model flag.
        grader_model: Explicit grader model override. If None, auto-selects
            a grader that differs from the eval model.

    Returns:
        Task for cultural confabulation evaluation.
    """
    dataset = load_inspect_dataset()

    filtered = MemoryDataset(
        samples=[
            s for s in dataset.samples
            if s.metadata.get("prompt_type") == prompt_type
        ],
        name=f"domain1_cultural_{prompt_type}",
    )

    resolved_grader: str = grader_model or _auto_grader_model(eval_model)

    return Task(
        dataset=filtered,
        solver=[generate()],
        scorer=cultural_confabulation_scorer(),
        model_roles={"grader": resolved_grader},
        version=EVAL_VERSION.comparability_version,
        metadata={
            **EVAL_VERSION.to_metadata(),
            "eval_framework": "Open Global Health & Biosecurity AI Evaluations",
            "domain": "1",
            "domain_name": "Cultural & Contextual Validity",
            "paper_reference": (
                "Seydi, R. (2026). Cultural Confabulation: A Structural "
                "Evaluation Gap in LLM Reasoning."
            ),
            "prompt_type": prompt_type,
            "grader_model": resolved_grader,
            "grader_selection": "auto" if grader_model is None else "manual",
        },
    )


@task
def cultural_confabulation_gap_analysis(
    eval_model: str | None = None,
    grader_model: str | None = None,
) -> Task:
    """Run both unscaffolded and scaffolded conditions to measure the gap.

    The gap (scaffolded_score - unscaffolded_score) is the empirical
    measure of cultural confabulation. A model that scores 13/18 with
    scaffolding and 7/18 without has a gap of 6 points — representing
    the degree to which contextual validity depends on user-provided
    interpretive infrastructure that real users cannot be expected to provide.

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
        scorer=cultural_confabulation_scorer(),
        model_roles={"grader": resolved_grader},
        version=EVAL_VERSION.comparability_version,
        metadata={
            **EVAL_VERSION.to_metadata(),
            "eval_framework": "Open Global Health & Biosecurity AI Evaluations",
            "domain": "1",
            "eval_type": "gap_analysis",
            "grader_model": resolved_grader,
            "gap_hypothesis": (
                "All three frontier models show >=4 point delta "
                "between scaffolded and unscaffolded"
            ),
        },
    )
