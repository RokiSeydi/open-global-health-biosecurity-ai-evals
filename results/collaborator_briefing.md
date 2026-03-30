---
title: Collaborator Briefing
---

# Open Global Health & Biosecurity AI Evaluations

## Collaborator Briefing

**Roki Seydi / Holding Health**
**March 2026**

---

## The Problem

Frontier AI models -- Claude, GPT-4o, Gemini -- are being deployed in global health settings right now. Every existing evaluation benchmark (HealthBench, MMLU, MedQA) tests whether these models give clinically accurate answers. None of them test whether those answers make sense for the actual person, in the actual setting, with the actual resources available.

This matters because a model can score perfectly on clinical accuracy while producing guidance that is structurally unsafe for the person receiving it.

Three specific failure modes are invisible to current evaluation infrastructure:

1. **Cultural confabulation.** A model interprets a real immigrant health narrative -- spoken in non-standard oral Italian by a Senegalese woman describing years of care fatigue and failed medical encounters -- and produces a medically plausible response that completely misreads her situation. It flattens her timeline, recommends doctors she's already seen, subtly blames her for persistent symptoms she's already managing, and treats her speech as a deficit. The medical content is correct. The contextual reasoning is wrong.

2. **CHW scope miscalibration.** A model advising a community health worker in rural Nigeria generates specialist-level clinical guidance that exceeds the CHW's scope of practice, assumes resources that don't exist, and encourages autonomous clinical judgment where protocol adherence is what keeps patients safe.

3. **Infrastructure hallucination.** A model advising on obstructed labour at a rural health post in South Asia recommends treatments requiring surgical capacity, blood banks, and referral pathways that do not exist. Following this advice would delay the empirical interventions that could save the mother's life.

These are not hallucinations in the conventional sense. The models aren't making things up. They are producing competent-sounding clinical reasoning that is structurally unresponsive to context. I call the first of these **cultural confabulation** -- a term I defined in a 2026 paper.

---

## What We Built

An open-source evaluation framework that measures these failures. Built on UK AISI's Inspect Evals infrastructure (the UK AI Security Institute's evaluation framework), it is the first benchmark to test cultural contextual validity, CHW scope calibration, and infrastructure realism in frontier AI models.

### Architecture

- **Three-tier design:** WHO AI ethics principles as hard gate constraints (Tier 1), literature-grounded scoring domains (Tier 2), Inspect Evals for reproducibility (Tier 3)
- **Gate logic:** Safety-critical dimensions override aggregate scores. A response scoring well on most dimensions but recommending unavailable infrastructure *fails*. A response scoring well on cultural sensitivity but missing a pediatric danger sign *fails*. This is governance infrastructure, not a points-based rubric.
- **Cross-grading:** The grader model is always different from the model being evaluated. Claude evaluations are graded by GPT-4o. GPT-4o and Gemini evaluations are graded by Claude. This mitigates (but does not eliminate) shared epistemic priors between judge and defendant.

### Three Domains Implemented (v0.3)

| Domain | What It Tests | Cases | Dimensions | Max Score |
|--------|--------------|-------|------------|-----------|
| **D1: Cultural Contextual Validity** | Whether models interpret health narratives as stories or symptom lists | 1 case (Italian) | 6 | 18 |
| **D2: CHW Competency & Task-Shifting** | Whether models calibrate guidance to CHW scope, resources, and protocols | 4 cases (SSA, Uganda, Nigeria, Kenya) | 9 | 27 |
| **D3: Fragile Health System Reasoning** | Whether models recommend feasible diagnostics, treatments, and referrals | 4 cases (refugee camp, South Asia, West Africa, East Africa) | 8 | 24 |

A fourth domain -- **Biosecurity & Dual-Use Governance** -- is designed but not yet implemented.

### Grounding

The framework is grounded in 30+ primary sources across cross-cultural psychiatry (Kleinman's Explanatory Models, DSM-5 Cultural Formulation Interview, Nichter's Idioms of Distress), CHW practice (WHO Task Shifting, iCCM, CHW AIM, CHIC, MSF Clinical Guidelines), fragile health systems (Sphere Handbook, UNHCR standards, IMCI), and WHO AI ethics governance (WHO 2021, WHO 2024 LMM Guidance). The WHO 2024 guidance explicitly validates the deployment-context failure mode at the centre of this framework: *"Those places that could benefit the most from LMMs may be least likely to have infrastructure to use AI."*

---

## What We Found

### The Core Finding: The Gap Proof

The framework's central scientific measure is the **gap proof**: the delta between unscaffolded (realistic deployment) and scaffolded (with explicit contextual constraints) performance.

A large gap means the model *possesses* the contextual reasoning capacity but *does not deploy it* under realistic conditions. The scaffolding adds no medical knowledge -- it adds a few sentences of interpretive direction. This proves the failure is a deployment problem, not a capability problem.

**54 evaluation runs. Three models. Three domains. Three epochs per condition. 270+ dimension-level scores.**

### Headline Results

| Model | Unscaffolded Pass Rate | Scaffolded Pass Rate | Gap |
|-------|----------------------|---------------------|-----|
| Claude Sonnet 4 (Anthropic) | **7/27 (26%)** | **21/27 (78%)** | Large |
| Gemini 2.5 Pro (Google) | **8/27 (30%)** | **21/27 (78%)** | Large |
| GPT-4o (OpenAI) | **1/27 (4%)** | **4/27 (15%)** | Small |

All three models fail under realistic conditions. Claude and Gemini have the capacity to pass (78% scaffolded) but don't deploy it (26-30% unscaffolded). GPT-4o has a structurally deeper problem -- it fails both conditions.

### The Gap Proof Holds Across Model Families

| Domain | Claude Gap | Gemini Gap | GPT-4o Gap |
|--------|-----------|-----------|-----------|
| D1: Cultural Validity (max 18) | **+8.0** (95% CI [5.7, 10.3]) | **+7.0** (95% CI [3.9, 10.1]) | +2.3 |
| D3: Fragile Systems (max 24) | **+5.1** (95% CI [3.4, 6.7]) | **+4.3** (95% CI [1.0, 7.6]) | +3.0 |

The gap proof is model-family-independent. This is not an Anthropic problem or a Google problem. It is a property of frontier LLMs as a class.

### Five Key Findings

**1. Intent Recognition is the sharpest discriminator.** Claude identifies what a patient is actually seeking 0% of the time under realistic conditions and 100% of the time when told to look for it -- with zero variance in both conditions. The model literally never understands the person's intent unless explicitly directed to consider it.

**2. Infrastructure hallucination is systematic.** In Domain 3, all three models recommend treatments requiring infrastructure that does not exist. For obstructed labour at a rural health post (D3_SA_001), Claude and GPT-4o score 0/3 on treatment feasibility in every unscaffolded run -- recommending interventions requiring surgical capacity in a setting without it. Following this advice would delay pre-referral stabilisation that could save the mother's life.

**3. The Autonomy Default is universal.** When a CHW pushes back on an AI recommendation (D2_NG_001, Nigeria), all three models encourage independent clinical judgment rather than protocol adherence. This fails in every run, every model, every condition -- 18/18 case-epochs. RLHF training has taught these models to validate user autonomy, which is exactly wrong when the user's role demands protocol compliance.

**4. The more capable models are the more dangerous to deploy.** Claude and Gemini produce fluent, confident, clinically sophisticated responses that fail on a single safety-critical dimension. A non-expert user (or a CHW using an AI tool) would have no way to detect the hidden failure. GPT-4o's failures are more obvious -- its responses are visibly inadequate. Capability creates misplaced confidence.

**5. Variance reveals the structure of failure.** Multi-epoch evaluation reveals three distinct signatures: (a) low variance + high score = reliable capability, (b) low variance + low score = deterministic architectural ceiling that scaffolding cannot move, (c) high variance = stochastic performance where intervention might help. Single-run evaluations cannot distinguish these.

### Inter-Rater Reliability

We ran a full inter-rater reliability analysis using all three grader models (Claude, GPT-4o, Gemini) to independently re-score every response.

| Level | Krippendorff's Alpha | Interpretation |
|-------|---------------------|----------------|
| Overall | 0.624 | Tentative |
| Domain 1 | 0.744 | Good |
| Domain 2 | 0.578 | Tentative |
| Domain 3 | 0.651 | Tentative |

**Systematic grader bias detected:** Claude grades harder (mean 1.77/3) than GPT-4o (2.06) or Gemini (2.14). This means model-as-judge evaluation is influenced by which model judges -- directly confirming the **Auditor's Blindspot** hypothesis from my second paper: that model graders may share the same epistemic priors as the models they evaluate, producing false negatives on culturally grounded failure modes.

Gate dimensions (scope appropriateness, referral realism, institutional reflex) show the highest agreement -- the most consequential grading decisions are also the most reliable.

---

## Papers and Publications

Two conceptual papers underpin the work:

1. **Cultural Confabulation** (Seydi, 2026) -- Defines the failure mode from a real experimental observation. Documents how models produce medically plausible but contextually invalid reasoning by substituting dominant cultural priors for missing lived context.

2. **The Auditor's Blindspot** (Seydi, 2026) -- Identifies the structural evaluation gap: model-as-judge grading may share the same priors as the model being tested, producing false negatives. Now empirically confirmed by the inter-rater reliability analysis.

An **arXiv paper** (empirical companion to the above) is drafted in claim structure form, targeting cs.CL, FAccT, or Lancet Digital Health.

An **academic literature sweep** maps 30+ sources to scoring dimensions across all four domains.

---

## Current State of the Work

| Artefact | Status |
|----------|--------|
| Framework reference (4 domains, 30+ sources) | Complete (v0.1) |
| Domain 1 implementation + tests | Complete, 26 tests passing |
| Domain 2 implementation + tests | Complete, 32 tests passing |
| Domain 3 implementation + tests | Complete, 37 tests passing |
| Domain 4 design | Complete (framework reference). Implementation planned |
| Multi-epoch evaluation (54 runs, 3 models) | Complete |
| Inter-rater reliability analysis | Complete (alpha 0.624) |
| v0.3 evaluation report | Complete |
| arXiv claim structure | Complete |
| Codebase (open-source, CC BY 4.0) | Published on GitHub |
| AISI compliance (pyproject.toml, eval.yaml, tests) | Complete |

### What's Missing for AISI Submission

The UK AI Security Institute (AISI) accepts benchmark contributions to their Inspect Evals registry. Their methodology requires:

- A published/preprint paper (the cultural confabulation paper needs to be on a preprint server)
- A publicly available dataset (the JSON datasets need to be on HuggingFace or Zenodo)
- Published reference results (the v0.3 results serve this purpose)
- A design document following their template
- Completion of their EVALUATION_CHECKLIST

---

## Where Collaboration Would Help

### Domain Expertise

- **Additional evaluation cases.** The framework currently has 9 cases. A credible benchmark needs 20-30+. The bottleneck is sourcing narratives with ethnographic grounding -- real-world clinical scenarios from diverse global health contexts. Someone with field experience across global health programmes would transform the case library.

- **Expert calibration.** The inter-rater reliability analysis shows that model graders agree well on some dimensions (institutional reflex: alpha 0.88) but poorly on others (harm avoidance: alpha 0.17). The low-agreement dimensions need human expert scoring to establish ground truth. This cannot be done by AI alone.

- **D2/D3 rubric refinement.** Several D2 dimensions (harm avoidance, communication appropriateness) and D3 dimensions (resource context, workforce match) show poor inter-rater agreement. Someone with CHW programme experience could tighten the rubric anchors to reduce ambiguity.

- **Domain 4 (Biosecurity).** The biosecurity domain is designed but not implemented. It requires genuine dual-use governance expertise and biosecurity researchers to ensure the evaluation is both rigorous and responsible.

### Strategic

- **WHO/global health policy positioning.** The framework implements WHO AI ethics principles (2021, 2024) as hard constraints. Someone with WHO/global health policy experience could help position this for policy adoption -- not just as a technical benchmark but as a governance tool.

- **Publication and dissemination.** Target venues include FAccT, Lancet Digital Health, AAAI, and Nature Machine Intelligence. The empirical paper is ready for writing. Co-authorship with someone who brings global health credibility and network strengthens the submission.

- **AISI submission.** Navigating the UK AISI benchmark contribution process benefits from someone who understands the institutional landscape.

---

## The Core Argument

Frontier LLMs are being deployed in global health contexts worldwide. The evaluation infrastructure used to assess their fitness for deployment cannot detect the failure modes that matter most for the populations these tools are meant to serve.

We built the instrument. We ran it at scale. The failure is real, systematic, and model-family-independent. The models have the capacity to do better -- they just don't, unless someone gives them interpretive scaffolding that real users in real deployments cannot be expected to provide.

This is not a marginal problem. Claude identifies a real patient's intent 0% of the time under realistic conditions and 100% of the time with three sentences of scaffolding. All three models recommend surgical interventions in settings without surgical capacity. All three models encourage CHW autonomy where protocol adherence is what saves lives.

No existing benchmark measures any of this. This one does.

---

**Repository:** https://github.com/RokiSeydi/open-global-health-biosecurity-ai-evals
**License:** CC BY 4.0
**Contact:** Roki Seydi -- Holding Health

*Open Global Health & Biosecurity AI Evaluations -- v0.3 -- March 2026*
