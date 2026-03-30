"""Tests for Domain 2: CHW Competency & Task-Shifting evaluation.

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

from global_health_ai_evals.domain2_chw_competency.domain2_chw_competency import (
    EVAL_VERSION,
    _auto_grader_model,
    chw_competency_eval,
    chw_competency_gap_analysis,
    load_inspect_dataset,
)
from global_health_ai_evals.domain2_chw_competency.domain2_rubric import (
    DIMENSION_ORDER,
    DIMENSION_PROMPTS,
    GRADER_SYSTEM_PROMPT,
    PEDIATRIC_CASE_IDS,
)
from global_health_ai_evals.metadata import EvalMetadata, TaskVersion, load_eval_metadata


# ---------------------------------------------------------------------------
# Metadata / versioning
# ---------------------------------------------------------------------------


class TestMetadata:
    def test_eval_yaml_loads(self) -> None:
        meta: EvalMetadata = load_eval_metadata("domain2_chw_competency")
        assert meta.title != ""
        assert meta.description != ""

    def test_version_format(self) -> None:
        meta = load_eval_metadata("domain2_chw_competency")
        assert isinstance(meta.version, TaskVersion)
        assert meta.version.comparability_version >= 1
        assert meta.version.interface_version in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

    def test_version_to_metadata(self) -> None:
        d = EVAL_VERSION.to_metadata()
        assert "full_task_version" in d
        assert "task_interface_version" in d
        assert "task_comparability_version" in d


# ---------------------------------------------------------------------------
# Dataset
# ---------------------------------------------------------------------------


class TestDataset:
    @pytest.mark.dataset_download
    def test_load_inspect_dataset(self) -> None:
        dataset = load_inspect_dataset()
        assert len(dataset.samples) == 8, "Expected 8 samples (4 cases x 2 conditions)"

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
    def test_sample_ids_contain_d2_prefix(self) -> None:
        dataset = load_inspect_dataset()
        for sample in dataset.samples:
            assert "D2_" in str(sample.id)

    @pytest.mark.dataset_download
    def test_four_unique_cases(self) -> None:
        dataset = load_inspect_dataset()
        case_ids = {s.metadata["case_id"] for s in dataset.samples}
        assert len(case_ids) == 4
        assert case_ids == {"D2_iCCM_001", "D2_UG_001", "D2_NG_001", "D2_KE_001"}

    @pytest.mark.dataset_download
    def test_domain_metadata(self) -> None:
        dataset = load_inspect_dataset()
        for sample in dataset.samples:
            assert sample.metadata["domain"] == "2"


# ---------------------------------------------------------------------------
# Task construction
# ---------------------------------------------------------------------------


class TestTaskConstruction:
    @pytest.mark.dataset_download
    def test_chw_competency_eval_returns_task(self) -> None:
        task = chw_competency_eval()
        assert task is not None
        assert task.dataset is not None
        assert task.scorer is not None
        assert task.solver is not None

    @pytest.mark.dataset_download
    def test_eval_task_metadata_has_version(self) -> None:
        task = chw_competency_eval()
        assert task.metadata is not None
        assert "full_task_version" in task.metadata

    @pytest.mark.dataset_download
    def test_eval_task_metadata_has_framework(self) -> None:
        task = chw_competency_eval()
        assert task.metadata is not None
        assert task.metadata["eval_framework"] == (
            "Open Global Health & Biosecurity AI Evaluations"
        )

    @pytest.mark.dataset_download
    def test_eval_task_metadata_has_domain(self) -> None:
        task = chw_competency_eval()
        assert task.metadata is not None
        assert task.metadata["domain"] == "2"
        assert task.metadata["domain_name"] == "CHW Competency & Task-Shifting"

    @pytest.mark.dataset_download
    def test_unscaffolded_filter(self) -> None:
        task = chw_competency_eval(prompt_type="unscaffolded")
        for s in task.dataset.samples:
            assert s.metadata["prompt_type"] == "unscaffolded"

    @pytest.mark.dataset_download
    def test_scaffolded_filter(self) -> None:
        task = chw_competency_eval(prompt_type="scaffolded")
        for s in task.dataset.samples:
            assert s.metadata["prompt_type"] == "scaffolded"

    @pytest.mark.dataset_download
    def test_unscaffolded_has_four_samples(self) -> None:
        task = chw_competency_eval(prompt_type="unscaffolded")
        assert len(task.dataset.samples) == 4

    @pytest.mark.dataset_download
    def test_gap_analysis_includes_both_conditions(self) -> None:
        task = chw_competency_gap_analysis()
        prompt_types = {s.metadata["prompt_type"] for s in task.dataset.samples}
        assert prompt_types == {"unscaffolded", "scaffolded"}

    @pytest.mark.dataset_download
    def test_gap_analysis_has_all_samples(self) -> None:
        task = chw_competency_gap_analysis()
        assert len(task.dataset.samples) == 8

    @pytest.mark.dataset_download
    def test_task_has_version_attribute(self) -> None:
        task = chw_competency_eval()
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

    @pytest.mark.dataset_download
    def test_manual_grader_override(self) -> None:
        grader = "openai/gpt-4o-mini"
        task = chw_competency_eval(grader_model=grader)
        assert task.metadata["grader_model"] == grader
        assert task.metadata["grader_selection"] == "manual"

    @pytest.mark.dataset_download
    def test_auto_grader_selection_metadata(self) -> None:
        task = chw_competency_eval()
        assert task.metadata["grader_selection"] == "auto"


# ---------------------------------------------------------------------------
# Rubric dimensions
# ---------------------------------------------------------------------------


class TestRubricDimensions:
    def test_nine_dimensions(self) -> None:
        assert len(DIMENSION_ORDER) == 9

    def test_all_dimensions_have_prompts(self) -> None:
        for dim in DIMENSION_ORDER:
            assert dim in DIMENSION_PROMPTS
            assert len(DIMENSION_PROMPTS[dim]) > 100

    def test_dimension_names_are_prefixed(self) -> None:
        for dim in DIMENSION_ORDER:
            assert dim.startswith("D2_")

    def test_grader_system_prompt_exists(self) -> None:
        assert "JSON" in GRADER_SYSTEM_PROMPT
        assert "score" in GRADER_SYSTEM_PROMPT
        assert "CHW" in GRADER_SYSTEM_PROMPT

    def test_dimension_prompts_request_json(self) -> None:
        for dim, prompt in DIMENSION_PROMPTS.items():
            assert "JSON" in prompt, f"{dim} prompt should request JSON output"

    def test_gate_dimensions_documented(self) -> None:
        assert "GATE" in DIMENSION_PROMPTS["D2_scope_appropriateness"]
        assert "GATE" in DIMENSION_PROMPTS["D2_resource_realism"]
        assert "GATE" in DIMENSION_PROMPTS["D2_danger_sign_recognition"]

    def test_pediatric_case_ids(self) -> None:
        assert "D2_iCCM_001" in PEDIATRIC_CASE_IDS
        assert "D2_KE_001" in PEDIATRIC_CASE_IDS
        assert len(PEDIATRIC_CASE_IDS) == 2
