"""Task registry for Inspect CLI discovery.

Registers all evaluation tasks so they can be invoked via:
    inspect eval global_health_ai_evals/domain1_cultural/domain1_cultural.py
    inspect eval global_health_ai_evals/domain1_cultural/domain1_cultural.py@cultural_confabulation_gap_analysis
    inspect eval global_health_ai_evals/domain2_chw_competency/domain2_chw_competency.py
    inspect eval global_health_ai_evals/domain2_chw_competency/domain2_chw_competency.py@chw_competency_gap_analysis
    inspect eval global_health_ai_evals/domain3_fragile_health_systems/domain3_fragile_health_systems.py
    inspect eval global_health_ai_evals/domain3_fragile_health_systems/domain3_fragile_health_systems.py@fragile_health_gap_analysis
"""

# ruff: noqa: F401

from global_health_ai_evals.domain1_cultural.domain1_cultural import (
    cultural_confabulation_eval,
    cultural_confabulation_gap_analysis,
)
from global_health_ai_evals.domain2_chw_competency.domain2_chw_competency import (
    chw_competency_eval,
    chw_competency_gap_analysis,
)
from global_health_ai_evals.domain3_fragile_health_systems.domain3_fragile_health_systems import (
    fragile_health_eval,
    fragile_health_gap_analysis,
)

__all__ = [
    "cultural_confabulation_eval",
    "cultural_confabulation_gap_analysis",
    "chw_competency_eval",
    "chw_competency_gap_analysis",
    "fragile_health_eval",
    "fragile_health_gap_analysis",
]
