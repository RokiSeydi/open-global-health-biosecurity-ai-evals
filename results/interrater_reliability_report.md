---
title: Inter-Rater Reliability Analysis
---

# Inter-Rater Reliability Analysis

**Open Global Health & Biosecurity AI Evaluations v0.3**

Roki Seydi / Holding Health | March 2026

---

## 1. Overview

This report presents the inter-rater reliability analysis for the model-as-judge grading system used across all three evaluation domains. Three frontier LLMs were used as independent graders to re-score the same model responses, enabling measurement of grading agreement and detection of systematic bias.

**Design:** Each model response from the v0.3 evaluation runs (epoch 1, all 3 domains, all 3 evaluated models) was independently re-graded by all three grader models using the same rubric prompts from the original evaluation. This produces a 3-grader x N-dimension reliability matrix per response.

**Scope:**

- **Grader models:** Claude Sonnet 4.5, GPT-4o, Gemini 2.5 Pro
- **Responses graded:** 54 model responses (3 models x 2 conditions x 3 domains, with 4 cases per domain for D2/D3 and 3 cases for D1)
- **Total dimension scores:** 1,332 attempted, 1,325 valid (99.5% success rate)
- **API errors:** 7 (all Gemini 503 high-demand errors)
- **Scale:** 0-3 ordinal per dimension
- **Metric:** Krippendorff's alpha (ordinal)

## 2. Overall Agreement

| Level | Krippendorff's Alpha | Interpretation |
|-------|---------------------|----------------|
| **Overall** | **0.624** | **Tentative** |
| Domain 1 — Cultural & Contextual Validity | 0.744 | Good |
| Domain 2 — CHW Competency & Task-Shifting | 0.578 | Tentative |
| Domain 3 — Fragile Health System Reasoning | 0.651 | Tentative |

**Interpretation thresholds** (Krippendorff, 2011): alpha >= 0.800 = reliable, 0.667-0.800 = good (tentative conclusions permissible), < 0.667 = tentative, < 0.400 = poor.

The overall alpha of 0.624 falls in the "tentative" range. This means the grading signal is detectable but not definitive — consistent with the Auditor's Blindspot hypothesis (Seydi, 2026) that model-as-judge systems may share epistemic priors with the models they evaluate.

## 3. Dimension-Level Agreement

### Domain 1 — Cultural & Contextual Validity (6 dimensions)

| Dimension | Alpha | Interpretation |
|-----------|-------|----------------|
| Institutional reflex | **0.880** | **Excellent** |
| Intent recognition | **0.834** | **Excellent** |
| Narrative arc | 0.740 | Good |
| Register respect | 0.658 | Tentative |
| Compliance framing | 0.517 | Tentative |
| Contextual proportionality | 0.380 | Poor |

Domain 1 shows the strongest overall agreement. Two dimensions — institutional reflex and intent recognition — achieve excellent reliability (alpha > 0.8). These are dimensions with clear, observable behavioral markers (does the model defer to institutional authority? does it understand what the patient is asking?). The weaker dimensions (compliance framing, contextual proportionality) involve more subjective judgments about cultural nuance.

### Domain 2 — CHW Competency & Task-Shifting (9 dimensions)

| Dimension | Alpha | Interpretation |
|-----------|-------|----------------|
| Scope appropriateness | **0.765** | **Good** |
| System awareness | 0.713 | Good |
| Treatment precision | 0.710 | Good |
| Referral pathway | 0.510 | Tentative |
| Protocol fidelity | 0.477 | Tentative |
| Danger sign recognition | 0.299 | Poor |
| Resource realism | 0.245 | Poor |
| Communication appropriateness | 0.198 | Poor |
| Harm avoidance | 0.171 | Poor |

Domain 2 has the widest spread. Gate dimensions (scope appropriateness) perform well — binary pass/fail decisions are easier for graders to agree on. However, four dimensions show poor agreement (alpha < 0.3). These are dimensions where rubric interpretation appears most subjective: what counts as "harm avoidance" or "communication appropriateness" may be evaluated quite differently depending on the grader model's own cultural priors.

### Domain 3 — Fragile Health System Reasoning (8 dimensions)

| Dimension | Alpha | Interpretation |
|-----------|-------|----------------|
| Referral realism | **0.845** | **Excellent** |
| Harm from gaps | 0.566 | Tentative |
| Treatment feasibility | 0.488 | Tentative |
| Infrastructure transparency | 0.480 | Tentative |
| Diagnostic feasibility | 0.360 | Poor |
| Syndromic reasoning | 0.297 | Poor |
| Workforce match | 0.229 | Poor |
| Resource context | 0.217 | Poor |

Domain 3 is bimodal. Referral realism achieves excellent agreement — graders can clearly assess whether a referral pathway exists in context. But several dimensions (resource context, workforce match, syndromic reasoning) show poor agreement. These dimensions require graders to evaluate the realism of recommendations against real-world resource constraints — precisely the kind of judgment where models may lack grounded knowledge.

## 4. Systematic Grader Bias

| Grader Model | Mean Score (0-3) | N |
|-------------|-----------------|---|
| Claude Sonnet 4.5 | **1.77** | 444 |
| GPT-4o | 2.06 | 444 |
| Gemini 2.5 Pro | **2.14** | 437 |

Claude grades systematically harder than the other two models (mean 1.77 vs 2.06-2.14). This 0.37-point gap per dimension means:

- When Claude is the grader (as it is for GPT-4o and Gemini evaluations in the standard pipeline), those models receive lower scores than they would from a Gemini or GPT-4o grader.
- When GPT-4o is the grader (as it is for Claude evaluations), Claude receives relatively higher scores.
- This creates a directional bias: **Claude's eval scores may be slightly inflated relative to GPT-4o/Gemini scores** due to grader assignment.

The magnitude (~0.37/dimension, ~12% of the scale) is meaningful but does not reverse pass/fail outcomes in most cases. It does, however, affect the precise score values reported in the v0.3 evaluation report.

## 5. Pairwise Agreement

| Grader Pair | Exact Match (%) | Within-1 (%) | N |
|------------|----------------|-------------|---|
| Gemini x GPT-4o | **66.4** | 88.6 | 437 |
| Claude x GPT-4o | 61.9 | **91.9** | 444 |
| Claude x Gemini | 52.9 | 85.8 | 437 |

Gemini and GPT-4o agree most often on exact scores (66.4%), while Claude and GPT-4o have the highest within-1 agreement (91.9%). Claude and Gemini show the lowest exact agreement (52.9%), consistent with Claude grading harder and Gemini grading more leniently.

## 6. Implications for the Evaluation Framework

### What This Validates

1. **The gap proof is robust.** Even with tentative grader agreement, the scaffolded-vs-unscaffolded delta is large enough (typically 3-6 points on an 18-27 scale) to exceed grading noise. The signal survives inter-rater variance.

2. **Gate dimensions work.** The highest-agreement dimensions include gate dimensions (scope appropriateness 0.765, referral realism 0.845, institutional reflex 0.880). Since gate failures drive AUTO_FAIL and CRITICAL_FAIL outcomes, the most consequential grading decisions are also the most reliable.

3. **Failure mode detection is reliable for some modes.** Institutional reflex (0.880) and intent recognition (0.834) — two of the six D1 failure modes — are consistently detected across graders.

### What This Flags

1. **D2 rubric prompts need tightening.** Four dimensions with alpha < 0.3 indicate rubric ambiguity. Harm avoidance and communication appropriateness should have more concrete behavioral anchors.

2. **Grader bias should be reported.** The systematic 0.37-point gap between Claude and Gemini grading should be disclosed as a known limitation. Future work could use grader-averaged scores or calibration adjustments.

3. **D3 resource-dependent dimensions need domain expertise.** Resource context (0.217) and workforce match (0.229) — dimensions requiring knowledge of real-world health system constraints — show poor grader agreement. This suggests model graders may lack the contextual knowledge these dimensions demand, reinforcing the case for human expert grading on infrastructure-dependent assessments.

## 7. Recommendations

1. **Report grader agreement alongside scores.** Include alpha values in the evaluation report as a confidence qualifier for each domain.

2. **Prioritize rubric revision for low-alpha dimensions.** Target harm_avoidance, communication_appropriateness, resource_context, and workforce_match for more explicit scoring criteria.

3. **Consider grader ensembles.** Average scores across 2-3 grader models to reduce systematic bias. This increases cost but improves reliability.

4. **Pursue human validation.** For dimensions with alpha < 0.4, human expert grading is essential to establish ground truth. This is particularly important for Domain 4 (biosecurity), where the stakes of mis-grading are highest.

---

*Analysis conducted using `scripts/run_interrater.py`. Raw data: `results/interrater_raw_scores.csv`. Summary statistics: `results/interrater_alpha_summary.csv`, `results/interrater_pairwise.csv`.*
