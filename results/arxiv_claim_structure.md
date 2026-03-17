# arXiv Paper — Claim Structure

## Working Title

**Cultural Confabulation in Frontier LLMs: A Multi-Epoch Evaluation of Contextual Validity Failure in Global Health AI Deployment**

*Alternative:* Measuring the Gap Between Capability and Deployment: Cultural Contextual Validity in Frontier Language Models

---

## Central Thesis

Frontier LLMs produce medically coherent but contextually invalid clinical reasoning when interpreting health narratives from culturally diverse populations — and they do so despite possessing the interpretive capacity to respond appropriately. This failure mode, which we term *cultural confabulation*, is structurally invisible to existing AI evaluation benchmarks and represents a deployment-critical safety gap for global health AI.

---

## Claim Architecture

### Claim 1 (Definitional): Cultural confabulation is a distinct failure mode

**Statement:** Cultural confabulation is not hallucination, not bias, and not a knowledge gap. It is the production of factually plausible, medically coherent reasoning that is contextually wrong — stripped of the meaning that makes clinical guidance safe and appropriate for the actual person in the actual situation.

**Evidence:**
- Both models produce responses that would score well on clinical accuracy benchmarks (medically correct advice, appropriate terminology, standard-of-care recommendations)
- Yet both score below the contextual validity pass threshold (Claude 6.3/18, GPT-4o 3.9/18) when evaluated against the person's actual situation, intent, and constraints
- The failure is not random — it is systematic across six documented dimensions that each target a specific failure pattern

**Why it matters:** If the failure were hallucination, existing benchmarks would catch it. If it were bias, existing fairness metrics would detect it. Cultural confabulation passes both checks while producing responses that are structurally unsafe for the person receiving them.

**Differentiation from prior work:**
- HealthBench (OpenAI, 2025) evaluates clinical accuracy — cultural confabulation passes clinical accuracy checks
- WMDP evaluates hazardous knowledge — cultural confabulation involves no hazardous knowledge
- Bias benchmarks evaluate demographic disparities in output — cultural confabulation is not a demographic disparity, it is a structural reasoning failure that applies to any narrative requiring contextual interpretation

---

### Claim 2 (Empirical — Primary): The gap between scaffolded and unscaffolded performance proves the failure is one of deployment, not capability

**Statement:** Claude Sonnet 4 scores 6.3/18 under realistic conditions and 15.0/18 when given minimal interpretive scaffolding — a gap of +8.7 points (95% CI [6.9, 10.4]). The model possesses the contextual reasoning capacity to interpret the narrative appropriately but does not deploy it unless explicitly directed to do so.

**Evidence:**
- 3 epochs × 2 conditions × 1 case = 9 scored samples per cell
- Claude unscaffolded: mean 6.3/18 (SD=1.58, SE=0.53), FAIL in 8/9, GATE in 1/9
- Claude scaffolded: mean 15.0/18 (SD=2.18, SE=0.73), PASS in 9/9 (100%)
- Gap: +8.7, SE=0.90, 95% CI [6.9, 10.4] — lower bound well above 4-point hypothesis threshold
- The scaffolding adds no medical knowledge — it adds three sentences of interpretive direction

**Why it matters:** This proves the failure is not a training data problem, a knowledge problem, or a capability limitation. The model *has* the capacity. It doesn't use it. This means the failure is addressable — but only if it is measured, which no current benchmark does.

**Key sub-finding:** Intent Recognition is the sharpest discriminator. Claude scores 0.22/3 unscaffolded (SD=0.44) and 3.00/3 scaffolded (SD=0.00 — zero variance, perfect ceiling). The model identifies the person's actual intent 0% of the time under realistic conditions and 100% of the time when told to look for it. This is the single cleanest demonstration of latent capacity that is never deployed.

---

### Claim 3 (Empirical — Secondary): GPT-4o exhibits a structurally deeper failure with hard architectural ceilings

**Statement:** GPT-4o scores 3.9/18 unscaffolded and 6.4/18 scaffolded — failing both conditions. 67% of unscaffolded runs trigger CRITICAL_FAIL (Narrative Arc = 0 AND Intent Recognition = 0). Two dimensions show zero variance across all 18 runs, suggesting deterministic failure patterns rather than stochastic variation.

**Evidence:**
- GPT-4o unscaffolded: mean 3.9/18 (SD=0.93), CRITICAL_FAIL in 6/9 runs
- GPT-4o scaffolded: mean 6.4/18 (SD=1.42), FAIL in 8/9, CRITICAL_FAIL in 1/9
- Gap: +2.6, 95% CI [1.4, 3.7] — does not reach 4-point threshold
- Register Respect: exactly 1/3 in all 18 runs (SD=0.00) — both conditions
- Contextual Proportionality: exactly 1/3 in all 18 runs (SD=0.00) — both conditions

**Why it matters:** GPT-4o's failure is qualitatively different from Claude's. Claude has latent capacity that scaffolding unlocks. GPT-4o has dimensions where scaffolding has literally no effect — the model's response pattern is fixed. This suggests different models fail in structurally different ways, which matters for deployment risk assessment: Claude's failure is addressable through prompt design; GPT-4o's failure on these dimensions may require architectural or training changes.

---

### Claim 4 (Methodological): Variance is informative — it reveals the structure of failure

**Statement:** Multi-epoch evaluation reveals three distinct variance signatures that carry different implications for intervention:

| Signature | Example | Implication |
|-----------|---------|-------------|
| Low variance + high score | Claude scaffolded Intent Recognition (3.00, SD=0.00) | Reliable capability — the model can do this consistently |
| Low variance + low score | GPT-4o Register Respect (1.00, SD=0.00) | Reliable failure — deterministic ceiling, not stochastic noise |
| High variance | Claude scaffolded Contextual Proportionality (2.11, SD=1.17, range 0–3) | Unstable dimension — model sometimes succeeds, sometimes fails |

**Evidence:** Per-dimension SD values across 9 runs per cell (see dimension-level table in report).

**Why it matters:** Single-run evaluations cannot distinguish between stochastic noise and structural failure. The zero-variance dimensions in GPT-4o would appear identical to moderate-variance dimensions in a single run. Multi-epoch evaluation is necessary to characterise the *type* of failure, not just its magnitude — and the type of failure determines what kind of intervention is required.

---

### Claim 5 (Benchmark gap): No existing AI evaluation benchmark measures cultural contextual validity

**Statement:** Existing benchmarks fall into categories that are structurally incapable of detecting cultural confabulation:

| Category | Examples | What they test | What they miss |
|----------|---------|---------------|---------------|
| Clinical accuracy | HealthBench, MedQA, PubMedQA | Whether the model's medical content is correct | Whether correct content is contextually appropriate for *this person* |
| Hazardous knowledge | WMDP, BioLP-bench | Whether the model has dangerous information | Whether the model applies information appropriately in context |
| Bias & fairness | BBQ, BOLD, StereoSet | Whether outputs vary by demographic group | Contextual reasoning failures that are not demographic disparities |
| Refusal | Strong Reject, XSTest | Whether models refuse inappropriate requests | Whether models reason correctly about ambiguous boundary cases |
| General reasoning | MMLU, GPQA, ARC | Whether models have domain knowledge | Whether models deploy knowledge contextually |

**Evidence:** Literature review of 30+ evaluation benchmarks mapped against the six failure dimensions (see Academic Literature Sweep in repository). None evaluates longitudinal narrative interpretation, care fatigue recognition, register respect for non-standard speech, or calibration to individual constraints.

**Why it matters:** A model could score perfectly on HealthBench, MMLU, and every existing clinical AI benchmark while producing responses that are structurally unsafe for the specific person they are advising. Cultural confabulation is invisible to the current evaluation infrastructure.

---

### Claim 6 (Methodological caution): The Auditor's Blindspot — model-as-judge grading shares priors with the eval target

**Statement:** When the grader model shares epistemic or cultural priors with the model being evaluated, scores may reflect consensus on dominant priors rather than contextual validity. Grader identity materially affects scores, and the direction of the effect is not always predictable.

**Evidence:**
- v0.1 found that switching from Claude-grading-Claude to GPT-4o-grading-Claude changed the scaffolded score from 11/18 to 14/18 — a 3-point swing
- The direction was counter-intuitive: the same-model grader scored *lower*, not higher
- Cross-grading is necessary but not sufficient — both grader models may share the same dominant priors that cultural confabulation tests for

**Why it matters:** The model-as-judge paradigm is now standard in AI evaluation. If the judge shares the same failure modes as the defendant, the evaluation produces false negatives. This is a structural limitation of automated evaluation for culturally grounded failure modes — and it applies to every eval framework that uses LLMs as graders, including this one.

**Honest limitation:** This framework uses model-as-judge and is therefore subject to its own critique. We mitigate with cross-grading but acknowledge this as a fundamental limitation that can only be fully resolved by human expert calibration.

---

## Paper Structure (Suggested)

1. **Introduction** — The deployment problem. LLMs are being deployed in global health contexts. Existing evaluations measure clinical accuracy, not contextual validity. Define cultural confabulation.

2. **Related Work** — Evaluation benchmarks (HealthBench, WMDP, MMLU, bias benchmarks). Cultural competence in clinical AI. Explanatory models framework (Kleinman). DSM-5 Cultural Formulation Interview. WHO AI ethics guidance.

3. **Framework Design** — Six-dimension rubric with theoretical grounding. Scoring method. Cross-grading protocol. Gap proof methodology.

4. **Experimental Setup** — D1_IT_001 case description. Two conditions. Three epochs. Inspect Evals infrastructure.

5. **Results** — Multi-epoch statistics. Aggregate scores. Dimension-level analysis. Gap with confidence intervals. Zero-variance findings. Intent Recognition as sharpest discriminator.

6. **Discussion** — Gap as evidence of deployment failure vs capability failure. GPT-4o architectural ceilings. Variance signatures and intervention implications. Auditor's Blindspot.

7. **Limitations** — Single case, two models, single language, 3 epochs, model-as-judge, no human calibration.

8. **Conclusion** — Cultural confabulation is measurable, systematic, and invisible to existing benchmarks. The gap proof demonstrates it is a deployment failure, not a capability failure. Open-source framework for community extension.

---

## Target Venues

| Venue | Fit | Angle |
|-------|-----|-------|
| **arXiv cs.CL** | Primary | Evaluation methodology + empirical results |
| **FAccT 2026/2027** | Strong | Fairness implications, deployment safety, structural evaluation gap |
| **AAAI 2027** | Strong | Novel evaluation methodology, multi-epoch design |
| **Lancet Digital Health** | Strong | Global health deployment safety, clinical contextual validity |
| **Nature Machine Intelligence** | Reach | Novel failure mode definition, cross-model empirical evidence |
| **EMNLP 2026** | Good | Evaluation methodology for NLP |
| **CHI 2027** | Possible | If framed around user-facing deployment implications |

---

## Relationship to Existing Papers

This arXiv paper is the **empirical companion** to two conceptual papers:

1. **Cultural Confabulation (Seydi, 2026)** — Defines the failure mode from qualitative experimental observation. The arXiv paper provides the quantitative statistical evidence with a reproducible evaluation instrument.

2. **The Auditor's Blindspot (Seydi, 2026)** — Identifies the model-as-judge evaluation gap. The arXiv paper demonstrates a concrete instance (grader identity affecting scores) and documents mitigation through cross-grading.

The arXiv paper should be positioned as: *"We defined cultural confabulation [cite paper 1]. We identified the evaluation gap [cite paper 2]. Here we build the instrument, run it, and report the first multi-epoch statistical evidence that the failure is real, systematic, and structurally invisible to existing benchmarks."*

---

## Strongest Single Sentence

> Claude Sonnet 4 identifies the intent behind a real immigrant health narrative 0% of the time under realistic conditions and 100% of the time when given three sentences of interpretive scaffolding — a latent capacity gap that no existing AI evaluation benchmark detects.
