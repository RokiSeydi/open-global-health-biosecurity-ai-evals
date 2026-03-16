"""Task registry for Inspect CLI discovery.

Registers all evaluation tasks so they can be invoked via:
    inspect eval src/global_health_ai_evals/domain1_cultural/domain1_cultural.py
    inspect eval src/global_health_ai_evals/domain1_cultural/domain1_cultural.py@cultural_confabulation_gap_analysis
"""

from .domain1_cultural.domain1_cultural import (
    cultural_confabulation_eval,
    cultural_confabulation_gap_analysis,
)

__all__ = [
    "cultural_confabulation_eval",
    "cultural_confabulation_gap_analysis",
]
