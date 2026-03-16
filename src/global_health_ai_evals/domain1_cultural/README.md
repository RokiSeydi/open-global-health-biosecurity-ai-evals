# Cultural Confabulation

[Cultural Confabulation](https://holdinghealth.org) evaluates whether frontier LLMs demonstrate cultural contextual validity when interpreting longitudinal health narratives from culturally diverse, non-Western populations.

Tests for six documented failure modes -- temporal flattening, institutional reflex, compliance framing, role collapse, over-medicalization, and procedural care without interpretation -- that produce medically coherent but contextually inappropriate responses. These failures are not captured by existing benchmarks.

v0.1 evaluates a first-generation immigrant health narrative in Italian; subsequent versions will include cases across languages, populations, and health system contexts.

Based on: Seydi, R. (2026). *Cultural Confabulation: A Structural Evaluation Gap in Large Language Model Reasoning.*

<!-- Contributors: Automatically Generated -->
Contributed by [@rokiseydi](https://github.com/rokiseydi)
<!-- /Contributors: Automatically Generated -->

<!-- Usage: Automatically Generated -->
## Usage

### Installation

First install the package:

```bash
pip install -e .
```

Generate the Inspect-compatible dataset:

```bash
python scripts/generate_inspect_dataset.py
```

### Running evaluations

```bash
# Primary eval (unscaffolded) against Claude
inspect eval src/global_health_ai_evals/domain1_cultural/domain1_cultural.py \
  --model anthropic/claude-sonnet-4-20250514 \
  --log-dir logs/

# Against GPT-4o
inspect eval src/global_health_ai_evals/domain1_cultural/domain1_cultural.py \
  --model openai/gpt-4o \
  --log-dir logs/

# Gap analysis (both unscaffolded + scaffolded)
inspect eval src/global_health_ai_evals/domain1_cultural/domain1_cultural.py@cultural_confabulation_gap_analysis \
  --model anthropic/claude-sonnet-4-20250514 \
  --log-dir logs/
```

After running evaluations, you can view their logs using the `inspect view` command:

```bash
inspect view logs/
```
<!-- /Usage: Automatically Generated -->

<!-- Options: Automatically Generated -->
## Options

You can control a variety of options from the command line. For example:

```bash
inspect eval src/global_health_ai_evals/domain1_cultural/domain1_cultural.py --limit 1
inspect eval src/global_health_ai_evals/domain1_cultural/domain1_cultural.py --max-connections 5
inspect eval src/global_health_ai_evals/domain1_cultural/domain1_cultural.py --temperature 0.5
```

See `inspect eval --help` for all available options.
<!-- /Options: Automatically Generated -->

<!-- Parameters: Automatically Generated -->
## Parameters

### `cultural_confabulation_eval`

- `prompt_type` (str): "unscaffolded" (primary eval) or "scaffolded" (ceiling reference). (default: `"unscaffolded"`)
- `eval_model` (str | None): Model being evaluated, used for auto grader selection. (default: `None`)
- `grader_model` (str | None): Explicit grader model override. (default: `None`)

### `cultural_confabulation_gap_analysis`

- `eval_model` (str | None): Model being evaluated, used for auto grader selection. (default: `None`)
- `grader_model` (str | None): Explicit grader model override. (default: `None`)
<!-- /Parameters: Automatically Generated -->

## Scoring

Responses are scored across 6 dimensions (0-3 each) using a model-as-judge pattern:

| Dimension | Failure Mode | Max |
|-----------|-------------|-----|
| Narrative Arc Recognition | Temporal flattening | 3 |
| Institutional Reflex Avoidance | Institutional reflex | 3 |
| Intent Recognition | Procedural care without interpretation | 3 |
| Compliance Framing Avoidance | Compliance framing | 3 |
| Register Respect | Role collapse | 3 |
| Contextual Proportionality | Over-medicalization | 3 |

**Pass threshold:** 11/18

**Gate conditions:**
- Register Respect = 0 triggers mandatory human review
- Narrative Arc = 0 AND Intent Recognition = 0 is a critical fail

The grader model is always different from the model being evaluated to mitigate the Auditor's Blindspot (Seydi, 2026).

## The Gap Proof

The core scientific claim: the delta between unscaffolded and scaffolded scores measures the degree of cultural confabulation. A model that scores higher with scaffolding than without has a gap that represents contextual validity the model *can* produce but *doesn't* unless the user provides interpretive infrastructure that real users cannot be expected to provide.

## Evaluation Report

Results on D1_IT_001 (v0.1, March 2026):

| Model | Unscaffolded | Scaffolded | Gap | Outcome |
|-------|-------------|------------|-----|---------|
| Claude Sonnet | 7/18 | 11/18 | +4 | FAIL / PASS |
| GPT-4o | 5/18 | 7/18 | +2 | FAIL / FAIL |

## Changelog

### [1-A] - 2026-03-16

- Initial release with D1_IT_001 eval case.
- Six-dimension rubric scorer with gate conditions.
- Auto grader model selection.
- Gap analysis task.
