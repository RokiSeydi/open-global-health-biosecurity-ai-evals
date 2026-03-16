"""Task registry for Inspect CLI discovery.

Registers all evaluation tasks so they can be invoked via:
    inspect eval global_health_ai_evals/domain1_cultural/domain1_cultural.py
    inspect eval global_health_ai_evals/domain1_cultural/domain1_cultural.py@cultural_confabulation_gap_analysis
"""

# ruff: noqa: F401

from global_health_ai_evals.domain1_cultural.domain1_cultural import (
    cultural_confabulation_eval,
    cultural_confabulation_gap_analysis,
)

__all__ = [
    "cultural_confabulation_eval",
    "cultural_confabulation_gap_analysis",
]
