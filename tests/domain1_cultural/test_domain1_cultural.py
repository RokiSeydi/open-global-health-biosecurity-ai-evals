"""Tests for Domain 1: Cultural Contextual Validity evaluation.

Tests cover:
    - Dataset loading and sample structure
    - Task construction and metadata
    - Rubric dimension completeness
    - Grader auto-selection logic
    - Eval metadata / versioning
    - Scorer gate conditions
"""

from __future__ import annotations

import pytest

from global_health_ai_evals.domain1_cultural.domain1_cultural import (
    EVAL_VERSION,
    _auto_grader_model,
    cultural_confabulation_eval,
    cultural_confabulation_gap_analysis,
    load_inspect_dataset,
)
from global_health_ai_evals.domain1_cultural.domain1_rubric import (
    DIMENSION_ORDER,
    DIMENSION_PROMPTS,
    GRADER_SYSTEM_PROMPT,
)
from global_health_ai_evals.metadata import EvalMetadata, TaskVersion, load_eval_metadata


# ---------------------------------------------------------------------------
# Metadata / versioning
# ---------------------------------------------------------------------------


class TestMetadata:
    def test_eval_yaml_loads(self) -> None:
        meta: EvalMetadata = load_eval_metadata("domain1_cultural")
        assert meta.title != ""
        assert meta.description != ""

    def test_version_format(self) -> None:
        meta = load_eval_metadata("domain1_cultural")
        assert isinstance(meta.version, TaskVersion)
        assert meta.version.comparability_version >= 1
        assert meta.version.interface_version in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

    def test_version_to_metadata(self) -> None:
        d = EVAL_VERSION.to_metadata()
        assert "full_task_version" in d
        assert "task_interface_version" in d
        assert "task_comparability_version" in d

    def test_version_validation_rejects_bad_format(self) -> None:
        with pytest.raises(ValueError):
            TaskVersion("bad")
        with pytest.raises(ValueError):
            TaskVersion("1-a")  # lowercase
        with pytest.raises(ValueError):
            TaskVersion("A-1")  # reversed


# ---------------------------------------------------------------------------
# Dataset
# ---------------------------------------------------------------------------


class TestDataset:
    @pytest.mark.dataset_download
    def test_load_inspect_dataset(self) -> None:
        dataset = load_inspect_dataset()
        assert len(dataset.samples) == 8, "Expected 8 samples (4 cases x 2 prompt types)"

    @pytest.mark.dataset_download
    def test_sample_has_required_fields(self) -> None:
        dataset = load_inspect_dataset()
        for sample in dataset.samples:
            assert sample.id is not None
            assert sample.input != ""
            assert sample.target != ""
            assert sample.metadata is not None
            assert "prompt_type" in sample.metadata
            assert "case_id" in sample.metadata

    @pytest.mark.dataset_download
    def test_sample_prompt_types(self) -> None:
        dataset = load_inspect_dataset()
        prompt_types = {s.metadata["prompt_type"] for s in dataset.samples}
        assert prompt_types == {"unscaffolded", "scaffolded"}

    @pytest.mark.dataset_download
    def test_sample_ids_contain_case_id(self) -> None:
        dataset = load_inspect_dataset()
        valid_case_ids = {"D1_IT_001", "D1_UK_001", "D1_UK_002", "D1_UK_003"}
        for sample in dataset.samples:
            assert any(cid in str(sample.id) for cid in valid_case_ids)


# ---------------------------------------------------------------------------
# Task construction
# ---------------------------------------------------------------------------


class TestTaskConstruction:
    @pytest.mark.dataset_download
    def test_cultural_confabulation_eval_returns_task(self) -> None:
        task = cultural_confabulation_eval()
        assert task is not None
        assert task.dataset is not None
        assert task.scorer is not None
        assert task.solver is not None

    @pytest.mark.dataset_download
    def test_eval_task_metadata_has_version(self) -> None:
        task = cultural_confabulation_eval()
        assert task.metadata is not None
        assert "full_task_version" in task.metadata

    @pytest.mark.dataset_download
    def test_eval_task_metadata_has_framework(self) -> None:
        task = cultural_confabulation_eval()
        assert task.metadata is not None
        assert task.metadata["eval_framework"] == (
            "Open Global Health & Biosecurity AI Evaluations"
        )

    @pytest.mark.dataset_download
    def test_unscaffolded_filter(self) -> None:
        task = cultural_confabulation_eval(prompt_type="unscaffolded")
        for s in task.dataset.samples:
            assert s.metadata["prompt_type"] == "unscaffolded"

    @pytest.mark.dataset_download
    def test_scaffolded_filter(self) -> None:
        task = cultural_confabulation_eval(prompt_type="scaffolded")
        for s in task.dataset.samples:
            assert s.metadata["prompt_type"] == "scaffolded"

    @pytest.mark.dataset_download
    def test_gap_analysis_includes_both_conditions(self) -> None:
        task = cultural_confabulation_gap_analysis()
        prompt_types = {s.metadata["prompt_type"] for s in task.dataset.samples}
        assert prompt_types == {"unscaffolded", "scaffolded"}

    @pytest.mark.dataset_download
    def test_task_has_version_attribute(self) -> None:
        task = cultural_confabulation_eval()
        assert task.version is not None
        assert isinstance(task.version, int)
        assert task.version >= 1


# ---------------------------------------------------------------------------
# Grader auto-selection
# ---------------------------------------------------------------------------


class TestGraderAutoSelection:
    def test_claude_model_gets_openai_grader(self) -> None:
        assert "openai" in _auto_grader_model("anthropic/claude-sonnet-4-20250514")

    def test_openai_model_gets_claude_grader(self) -> None:
        assert "anthropic" in _auto_grader_model("openai/gpt-4o")

    def test_google_model_gets_claude_grader(self) -> None:
        assert "anthropic" in _auto_grader_model("google/gemini-2.5-pro")

    def test_none_defaults_to_claude_grader(self) -> None:
        assert "anthropic" in _auto_grader_model(None)

    def test_manual_grader_override(self) -> None:
        grader = "openai/gpt-4o-mini"
        task = cultural_confabulation_eval(grader_model=grader)
        assert task.metadata["grader_model"] == grader
        assert task.metadata["grader_selection"] == "manual"

    def test_auto_grader_selection_metadata(self) -> None:
        task = cultural_confabulation_eval()
        assert task.metadata["grader_selection"] == "auto"


# ---------------------------------------------------------------------------
# Rubric dimensions
# ---------------------------------------------------------------------------


class TestRubricDimensions:
    def test_six_dimensions(self) -> None:
        assert len(DIMENSION_ORDER) == 6

    def test_all_dimensions_have_prompts(self) -> None:
        for dim in DIMENSION_ORDER:
            assert dim in DIMENSION_PROMPTS
            assert len(DIMENSION_PROMPTS[dim]) > 100

    def test_dimension_names_are_prefixed(self) -> None:
        for dim in DIMENSION_ORDER:
            assert dim.startswith("D1_")

    def test_grader_system_prompt_exists(self) -> None:
        assert "JSON" in GRADER_SYSTEM_PROMPT
        assert "score" in GRADER_SYSTEM_PROMPT

    def test_dimension_prompts_request_json(self) -> None:
        for dim, prompt in DIMENSION_PROMPTS.items():
            assert "JSON" in prompt, f"{dim} prompt should request JSON output"
