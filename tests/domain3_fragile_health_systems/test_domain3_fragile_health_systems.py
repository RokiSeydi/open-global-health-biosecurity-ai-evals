"""Tests for Domain 3: Fragile Health System Reasoning evaluation.

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

from global_health_ai_evals.domain3_fragile_health_systems.domain3_fragile_health_systems import (
    EVAL_VERSION,
    _auto_grader_model,
    fragile_health_eval,
    fragile_health_gap_analysis,
    load_inspect_dataset,
)
from global_health_ai_evals.domain3_fragile_health_systems.domain3_rubric import (
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
        meta: EvalMetadata = load_eval_metadata("domain3_fragile_health_systems")
        assert meta.title != ""
        assert meta.description != ""

    def test_version_format(self) -> None:
        meta = load_eval_metadata("domain3_fragile_health_systems")
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
    def test_sample_ids_contain_d3_prefix(self) -> None:
        dataset = load_inspect_dataset()
        for sample in dataset.samples:
            assert "D3_" in str(sample.id)

    @pytest.mark.dataset_download
    def test_four_unique_cases(self) -> None:
        dataset = load_inspect_dataset()
        case_ids = {s.metadata["case_id"] for s in dataset.samples}
        assert len(case_ids) == 4
        assert case_ids == {"D3_RC_001", "D3_SA_001", "D3_WA_001", "D3_EA_001"}

    @pytest.mark.dataset_download
    def test_domain_metadata(self) -> None:
        dataset = load_inspect_dataset()
        for sample in dataset.samples:
            assert sample.metadata["domain"] == "3"

    @pytest.mark.dataset_download
    def test_each_case_has_both_conditions(self) -> None:
        dataset = load_inspect_dataset()
        case_conditions: dict[str, set[str]] = {}
        for sample in dataset.samples:
            cid = sample.metadata["case_id"]
            pt = sample.metadata["prompt_type"]
            case_conditions.setdefault(cid, set()).add(pt)
        for cid, conditions in case_conditions.items():
            assert conditions == {"unscaffolded", "scaffolded"}, (
                f"Case {cid} missing condition"
            )

    @pytest.mark.dataset_download
    def test_narrative_types_are_fragile_system(self) -> None:
        dataset = load_inspect_dataset()
        for sample in dataset.samples:
            assert "fragile_system" in sample.metadata["narrative_type"]


# ---------------------------------------------------------------------------
# Task construction
# ---------------------------------------------------------------------------


class TestTaskConstruction:
    @pytest.mark.dataset_download
    def test_fragile_health_eval_returns_task(self) -> None:
        task = fragile_health_eval()
        assert task is not None
        assert task.dataset is not None
        assert task.scorer is not None
        assert task.solver is not None

    @pytest.mark.dataset_download
    def test_eval_task_metadata_has_version(self) -> None:
        task = fragile_health_eval()
        assert task.metadata is not None
        assert "full_task_version" in task.metadata

    @pytest.mark.dataset_download
    def test_eval_task_metadata_has_framework(self) -> None:
        task = fragile_health_eval()
        assert task.metadata is not None
        assert task.metadata["eval_framework"] == (
            "Open Global Health & Biosecurity AI Evaluations"
        )

    @pytest.mark.dataset_download
    def test_eval_task_metadata_has_domain(self) -> None:
        task = fragile_health_eval()
        assert task.metadata is not None
        assert task.metadata["domain"] == "3"
        assert task.metadata["domain_name"] == "Fragile Health System Reasoning"

    @pytest.mark.dataset_download
    def test_unscaffolded_filter(self) -> None:
        task = fragile_health_eval(prompt_type="unscaffolded")
        for s in task.dataset.samples:
            assert s.metadata["prompt_type"] == "unscaffolded"

    @pytest.mark.dataset_download
    def test_scaffolded_filter(self) -> None:
        task = fragile_health_eval(prompt_type="scaffolded")
        for s in task.dataset.samples:
            assert s.metadata["prompt_type"] == "scaffolded"

    @pytest.mark.dataset_download
    def test_unscaffolded_has_four_samples(self) -> None:
        task = fragile_health_eval(prompt_type="unscaffolded")
        assert len(task.dataset.samples) == 4

    @pytest.mark.dataset_download
    def test_gap_analysis_includes_both_conditions(self) -> None:
        task = fragile_health_gap_analysis()
        prompt_types = {s.metadata["prompt_type"] for s in task.dataset.samples}
        assert prompt_types == {"unscaffolded", "scaffolded"}

    @pytest.mark.dataset_download
    def test_gap_analysis_has_all_samples(self) -> None:
        task = fragile_health_gap_analysis()
        assert len(task.dataset.samples) == 8

    @pytest.mark.dataset_download
    def test_task_has_version_attribute(self) -> None:
        task = fragile_health_eval()
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
        task = fragile_health_eval(grader_model=grader)
        assert task.metadata["grader_model"] == grader
        assert task.metadata["grader_selection"] == "manual"

    @pytest.mark.dataset_download
    def test_auto_grader_selection_metadata(self) -> None:
        task = fragile_health_eval()
        assert task.metadata["grader_selection"] == "auto"


# ---------------------------------------------------------------------------
# Rubric dimensions
# ---------------------------------------------------------------------------


class TestRubricDimensions:
    def test_eight_dimensions(self) -> None:
        assert len(DIMENSION_ORDER) == 8

    def test_all_dimensions_have_prompts(self) -> None:
        for dim in DIMENSION_ORDER:
            assert dim in DIMENSION_PROMPTS
            assert len(DIMENSION_PROMPTS[dim]) > 100

    def test_dimension_names_are_prefixed(self) -> None:
        for dim in DIMENSION_ORDER:
            assert dim.startswith("D3_")

    def test_grader_system_prompt_exists(self) -> None:
        assert "JSON" in GRADER_SYSTEM_PROMPT
        assert "score" in GRADER_SYSTEM_PROMPT
        assert "fragile" in GRADER_SYSTEM_PROMPT.lower()

    def test_dimension_prompts_request_json(self) -> None:
        for dim, prompt in DIMENSION_PROMPTS.items():
            assert "JSON" in prompt, f"{dim} prompt should request JSON output"

    def test_gate_dimensions_documented(self) -> None:
        assert "GATE" in DIMENSION_PROMPTS["D3_diagnostic_feasibility"]
        assert "GATE" in DIMENSION_PROMPTS["D3_treatment_feasibility"]

    def test_expected_dimension_ids(self) -> None:
        expected = {
            "D3_resource_context",
            "D3_diagnostic_feasibility",
            "D3_treatment_feasibility",
            "D3_referral_realism",
            "D3_workforce_match",
            "D3_infrastructure_transparency",
            "D3_harm_from_gaps",
            "D3_syndromic_reasoning",
        }
        assert set(DIMENSION_ORDER) == expected

    def test_max_score_is_24(self) -> None:
        # 8 dimensions x 3 max = 24
        assert len(DIMENSION_ORDER) * 3 == 24

    def test_diagnostic_feasibility_mentions_category_a(self) -> None:
        assert "Category A" in DIMENSION_PROMPTS["D3_diagnostic_feasibility"]

    def test_treatment_feasibility_mentions_category_b(self) -> None:
        assert "Category B" in DIMENSION_PROMPTS["D3_treatment_feasibility"]
