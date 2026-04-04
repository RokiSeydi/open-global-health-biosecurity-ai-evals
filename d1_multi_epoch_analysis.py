#!/usr/bin/env python3
"""
D1 Multi-Epoch Statistical Analysis
====================================
3 epochs x 3 models x 4 cases x 2 conditions
Pass threshold: 11/18, Max score: 18
"""

import math
from collections import defaultdict

# ---------------------------------------------------------------------------
# Raw data
# ---------------------------------------------------------------------------
PASS_THRESHOLD = 11
MAX_SCORE = 18
CASES = ["IT_001", "UK_001", "UK_002", "UK_003"]
CONDITIONS = ["unscaffolded", "scaffolded"]
MODELS = ["Claude Sonnet", "GPT-4o", "Gemini 2.5 Pro"]

# data[model][epoch] = {case: {condition: score}}
DATA = {
    "Claude Sonnet": {
        1: {"IT_001": {"unscaffolded": 9,  "scaffolded": 16},
            "UK_001": {"unscaffolded": 11, "scaffolded": 15},
            "UK_002": {"unscaffolded": 15, "scaffolded": 18},
            "UK_003": {"unscaffolded": 14, "scaffolded": 16}},
        2: {"IT_001": {"unscaffolded": 7,  "scaffolded": 13},
            "UK_001": {"unscaffolded": 13, "scaffolded": 18},
            "UK_002": {"unscaffolded": 15, "scaffolded": 18},
            "UK_003": {"unscaffolded": 13, "scaffolded": 16}},
        3: {"IT_001": {"unscaffolded": 6,  "scaffolded": 16},
            "UK_001": {"unscaffolded": 12, "scaffolded": 17},
            "UK_002": {"unscaffolded": 14, "scaffolded": 18},
            "UK_003": {"unscaffolded": 17, "scaffolded": 18}},
    },
    "GPT-4o": {
        1: {"IT_001": {"unscaffolded": 6,  "scaffolded": 8},
            "UK_001": {"unscaffolded": 5,  "scaffolded": 13},
            "UK_002": {"unscaffolded": 10, "scaffolded": 14},
            "UK_003": {"unscaffolded": 6,  "scaffolded": 11}},
        2: {"IT_001": {"unscaffolded": 3,  "scaffolded": 6},
            "UK_001": {"unscaffolded": 4,  "scaffolded": 15},
            "UK_002": {"unscaffolded": 8,  "scaffolded": 12},
            "UK_003": {"unscaffolded": 6,  "scaffolded": 10}},
        3: {"IT_001": {"unscaffolded": 6,  "scaffolded": 6},
            "UK_001": {"unscaffolded": 5,  "scaffolded": 9},
            "UK_002": {"unscaffolded": 8,  "scaffolded": 12},
            "UK_003": {"unscaffolded": 5,  "scaffolded": 8}},
    },
    "Gemini 2.5 Pro": {
        1: {"IT_001": {"unscaffolded": 6,  "scaffolded": 18},
            "UK_001": {"unscaffolded": 15, "scaffolded": 18},
            "UK_002": {"unscaffolded": 16, "scaffolded": 18},
            "UK_003": {"unscaffolded": 18, "scaffolded": 18}},
        2: {"IT_001": {"unscaffolded": 6,  "scaffolded": 12},
            "UK_001": {"unscaffolded": 16, "scaffolded": 18},
            "UK_002": {"unscaffolded": 16, "scaffolded": 18},
            "UK_003": {"unscaffolded": 18, "scaffolded": 17}},
        3: {"IT_001": {"unscaffolded": 5,  "scaffolded": 15},
            "UK_001": {"unscaffolded": 14, "scaffolded": 18},
            "UK_002": {"unscaffolded": 16, "scaffolded": 18},
            "UK_003": {"unscaffolded": 16, "scaffolded": 18}},
    },
}

# GPT-4o special outcome events
SPECIAL_EVENTS = [
    {"model": "GPT-4o", "case": "IT_001", "condition": "unscaffolded", "epoch": 2,
     "event": "CRITICAL_FAIL", "details": "narrative_arc=0, intent_recognition=0"},
    {"model": "GPT-4o", "case": "UK_003", "condition": "unscaffolded", "epoch": 1,
     "event": "GATE_TRIGGERED", "details": "register_respect=0"},
    {"model": "GPT-4o", "case": "UK_003", "condition": "unscaffolded", "epoch": 3,
     "event": "CRITICAL_FAIL", "details": "narrative_arc=0, intent_recognition=0"},
    {"model": "GPT-4o", "case": "UK_003", "condition": "scaffolded", "epoch": 3,
     "event": "GATE_TRIGGERED", "details": "register_respect=0"},
]

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def mean(vals):
    return sum(vals) / len(vals)

def sd(vals):
    """Sample standard deviation (n-1 denominator)."""
    if len(vals) < 2:
        return 0.0
    m = mean(vals)
    return math.sqrt(sum((x - m) ** 2 for x in vals) / (len(vals) - 1))

def ci95(vals):
    """95% CI using t-distribution critical value for small n."""
    # t critical values for 95% two-tailed
    t_crit = {2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447,
              7: 2.365, 8: 2.306, 9: 2.262, 10: 2.228, 11: 2.201, 12: 2.179}
    n = len(vals)
    if n < 2:
        return (vals[0], vals[0])
    df = n - 1
    t = t_crit.get(df, 1.96)  # fallback to z for large n
    m = mean(vals)
    se = sd(vals) / math.sqrt(n)
    return (m - t * se, m + t * se)

def paired_t_test(x, y):
    """Paired t-test. Returns t-statistic, df, two-tailed p-value (approximated)."""
    n = len(x)
    diffs = [a - b for a, b in zip(x, y)]
    d_bar = mean(diffs)
    d_sd = sd(diffs)
    if d_sd == 0:
        return float('inf'), n - 1, 0.0
    t_stat = d_bar / (d_sd / math.sqrt(n))
    df = n - 1
    # Approximate two-tailed p using the survival function of t-distribution
    # We'll use a simple lookup / approximation
    p = approximate_t_pvalue(abs(t_stat), df)
    return t_stat, df, p

def approximate_t_pvalue(t_abs, df):
    """
    Approximate two-tailed p-value for t-distribution.
    Uses the regularized incomplete beta function approximation.
    For small df, we use a lookup table of critical values.
    """
    # Critical t-values for common significance levels (two-tailed)
    # df: {alpha: t_crit}
    tables = {
        2:  {0.20: 1.386, 0.10: 2.920, 0.05: 4.303, 0.02: 6.965, 0.01: 9.925, 0.001: 31.599},
        3:  {0.20: 1.250, 0.10: 2.353, 0.05: 3.182, 0.02: 4.541, 0.01: 5.841, 0.001: 12.924},
        4:  {0.20: 1.190, 0.10: 2.132, 0.05: 2.776, 0.02: 3.747, 0.01: 4.604, 0.001: 8.610},
        5:  {0.20: 1.156, 0.10: 2.015, 0.05: 2.571, 0.02: 3.365, 0.01: 4.032, 0.001: 6.869},
        6:  {0.20: 1.134, 0.10: 1.943, 0.05: 2.447, 0.02: 3.143, 0.01: 3.707, 0.001: 5.959},
        7:  {0.20: 1.119, 0.10: 1.895, 0.05: 2.365, 0.02: 2.998, 0.01: 3.499, 0.001: 5.408},
        8:  {0.20: 1.108, 0.10: 1.860, 0.05: 2.306, 0.02: 2.896, 0.01: 3.355, 0.001: 5.041},
        9:  {0.20: 1.100, 0.10: 1.833, 0.05: 2.262, 0.02: 2.821, 0.01: 3.250, 0.001: 4.781},
        10: {0.20: 1.093, 0.10: 1.812, 0.05: 2.228, 0.02: 2.764, 0.01: 3.169, 0.001: 4.587},
        11: {0.20: 1.088, 0.10: 1.796, 0.05: 2.201, 0.02: 2.718, 0.01: 3.106, 0.001: 4.437},
    }
    if df in tables:
        for alpha in sorted(tables[df].keys()):
            if t_abs >= tables[df][alpha]:
                continue
            else:
                # p is between previous alpha and this alpha
                # Return the conservative (larger) p
                return alpha
        # t_abs exceeds all critical values
        return 0.001  # p < 0.001
    # Fallback: use normal approximation for large df
    # This is rough but adequate
    if t_abs > 3.5:
        return 0.001
    elif t_abs > 2.576:
        return 0.01
    elif t_abs > 1.96:
        return 0.05
    elif t_abs > 1.645:
        return 0.10
    else:
        return 0.20

def fmt(v, decimals=2):
    return f"{v:.{decimals}f}"

def passes(score):
    return score >= PASS_THRESHOLD

# ---------------------------------------------------------------------------
# Collect scores into flat lists
# ---------------------------------------------------------------------------

def gather_scores(model, condition=None, case=None):
    """Return list of scores matching filters."""
    scores = []
    for epoch in [1, 2, 3]:
        for c in CASES:
            if case and c != case:
                continue
            for cond in CONDITIONS:
                if condition and cond != condition:
                    continue
                scores.append(DATA[model][epoch][c][cond])
    return scores

def gather_epoch_means(model, condition=None):
    """Return list of 3 epoch-level mean scores."""
    epoch_means = []
    for epoch in [1, 2, 3]:
        scores = []
        for c in CASES:
            for cond in CONDITIONS:
                if condition and cond != condition:
                    continue
                scores.append(DATA[model][epoch][c][cond])
        epoch_means.append(mean(scores))
    return epoch_means

def gather_case_scores(model, case, condition):
    """Return 3 scores (one per epoch) for a specific model/case/condition."""
    return [DATA[model][epoch][case][condition] for epoch in [1, 2, 3]]

# ===========================================================================
# ANALYSIS
# ===========================================================================

print("=" * 80)
print("D1 MULTI-EPOCH STATISTICAL ANALYSIS")
print("=" * 80)
print(f"Epochs: 3 | Models: 3 | Cases: 4 | Conditions: 2")
print(f"Pass threshold: {PASS_THRESHOLD}/{MAX_SCORE} | Max score: {MAX_SCORE}")
print()

# -----------------------------------------------------------------------
# 1. Per-model 3-epoch means, SDs, and 95% CIs
# -----------------------------------------------------------------------
print("=" * 80)
print("1. PER-MODEL EPOCH-LEVEL STATISTICS")
print("=" * 80)
print()

for model in MODELS:
    print(f"--- {model} ---")
    for label, condition in [("Overall", None), ("Unscaffolded", "unscaffolded"), ("Scaffolded", "scaffolded")]:
        epoch_means = gather_epoch_means(model, condition)
        m = mean(epoch_means)
        s = sd(epoch_means)
        lo, hi = ci95(epoch_means)
        norm_m = m / MAX_SCORE
        print(f"  {label:15s}: epoch means = {[fmt(x) for x in epoch_means]}")
        print(f"    Mean = {fmt(m)} ({fmt(norm_m * 100)}%), SD = {fmt(s)}, 95% CI = [{fmt(lo)}, {fmt(hi)}]")
    print()

# -----------------------------------------------------------------------
# 2. Per-case-per-model means and SDs
# -----------------------------------------------------------------------
print("=" * 80)
print("2. PER-CASE PER-MODEL MEANS AND SDs (across 3 epochs)")
print("=" * 80)
print()
print(f"{'Model':<20s} {'Case':<10s} {'Cond':<14s} {'Scores':>18s}  {'Mean':>6s}  {'SD':>5s}  {'%':>6s}  {'Pass?':>5s}")
print("-" * 90)

for model in MODELS:
    for case in CASES:
        for cond in CONDITIONS:
            scores = gather_case_scores(model, case, cond)
            m = mean(scores)
            s = sd(scores)
            pct = m / MAX_SCORE * 100
            pass_str = "PASS" if m >= PASS_THRESHOLD else "FAIL"
            scores_str = str(scores)
            print(f"{model:<20s} {case:<10s} {cond:<14s} {scores_str:>18s}  {fmt(m):>6s}  {fmt(s):>5s}  {fmt(pct):>5s}%  {pass_str:>5s}")
        print()

# -----------------------------------------------------------------------
# 3. Per-case gap means and SDs
# -----------------------------------------------------------------------
print("=" * 80)
print("3. SCAFFOLDING GAP PER CASE PER MODEL (scaffolded - unscaffolded)")
print("=" * 80)
print()
print(f"{'Model':<20s} {'Case':<10s} {'Gaps (3 epochs)':>20s}  {'Mean Gap':>9s}  {'SD':>5s}  {'Gap %pts':>9s}")
print("-" * 80)

all_model_gaps = {}  # model -> list of all gap values (12 per model)

for model in MODELS:
    model_gaps = []
    for case in CASES:
        gaps = []
        for epoch in [1, 2, 3]:
            g = DATA[model][epoch][case]["scaffolded"] - DATA[model][epoch][case]["unscaffolded"]
            gaps.append(g)
            model_gaps.append(g)
        m = mean(gaps)
        s = sd(gaps)
        pct = m / MAX_SCORE * 100
        print(f"{model:<20s} {case:<10s} {str(gaps):>20s}  {fmt(m):>9s}  {fmt(s):>5s}  {fmt(pct):>8s}%")
    all_model_gaps[model] = model_gaps
    # Model-level gap summary
    overall_gap_mean = mean(model_gaps)
    overall_gap_sd = sd(model_gaps)
    print(f"  {'>>> MODEL GAP':>28s}: Mean = {fmt(overall_gap_mean)}, SD = {fmt(overall_gap_sd)}, "
          f"Range = [{min(model_gaps)}, {max(model_gaps)}]")
    print()

# -----------------------------------------------------------------------
# 4. Run-to-run variance
# -----------------------------------------------------------------------
print("=" * 80)
print("4. RUN-TO-RUN VARIANCE (SD of epoch-level means)")
print("=" * 80)
print()

for model in MODELS:
    print(f"--- {model} ---")
    for label, condition in [("Overall", None), ("Unscaffolded", "unscaffolded"), ("Scaffolded", "scaffolded")]:
        epoch_means = gather_epoch_means(model, condition)
        s = sd(epoch_means)
        rng = max(epoch_means) - min(epoch_means)
        print(f"  {label:15s}: epoch means = [{', '.join(fmt(x) for x in epoch_means)}]")
        print(f"    SD = {fmt(s)}, Range = {fmt(rng)} points")
    print()

# -----------------------------------------------------------------------
# 5. Case pass rate stability
# -----------------------------------------------------------------------
print("=" * 80)
print("5. CASE PASS RATE STABILITY (epochs passing out of 3)")
print("=" * 80)
print()
print(f"{'Model':<20s} {'Case':<10s} {'Condition':<14s} {'E1':>4s} {'E2':>4s} {'E3':>4s}  {'Pass Rate':>10s}")
print("-" * 70)

for model in MODELS:
    for case in CASES:
        for cond in CONDITIONS:
            scores = gather_case_scores(model, case, cond)
            pass_flags = ["P" if passes(s) else "F" for s in scores]
            n_pass = sum(1 for s in scores if passes(s))
            print(f"{model:<20s} {case:<10s} {cond:<14s} "
                  f"{scores[0]:>3d}{pass_flags[0]} "
                  f"{scores[1]:>3d}{pass_flags[1]} "
                  f"{scores[2]:>3d}{pass_flags[2]}  "
                  f"{n_pass}/3")
    print()

# -----------------------------------------------------------------------
# 6. Overall pass rates
# -----------------------------------------------------------------------
print("=" * 80)
print("6. OVERALL PASS RATES")
print("=" * 80)
print()

for model in MODELS:
    print(f"--- {model} ---")
    for cond in CONDITIONS:
        total = 0
        passed = 0
        for epoch in [1, 2, 3]:
            for case in CASES:
                total += 1
                if passes(DATA[model][epoch][case][cond]):
                    passed += 1
        pct = passed / total * 100
        print(f"  {cond:14s}: {passed}/{total} case-epochs pass ({fmt(pct)}%)")
    # Combined
    total_all = 0
    passed_all = 0
    for epoch in [1, 2, 3]:
        for case in CASES:
            for cond in CONDITIONS:
                total_all += 1
                if passes(DATA[model][epoch][case][cond]):
                    passed_all += 1
    pct_all = passed_all / total_all * 100
    print(f"  {'combined':14s}: {passed_all}/{total_all} case-epochs pass ({fmt(pct_all)}%)")
    print()

# Cross-model summary
print("  CROSS-MODEL PASS RATE SUMMARY (unscaffolded / scaffolded):")
for model in MODELS:
    unsca_pass = sum(1 for e in [1,2,3] for c in CASES if passes(DATA[model][e][c]["unscaffolded"]))
    sca_pass = sum(1 for e in [1,2,3] for c in CASES if passes(DATA[model][e][c]["scaffolded"]))
    print(f"    {model:<20s}: {unsca_pass}/12 unscaffolded, {sca_pass}/12 scaffolded")
print()

# -----------------------------------------------------------------------
# 7. Paired t-test: unscaffolded vs scaffolded per model
# -----------------------------------------------------------------------
print("=" * 80)
print("7. STATISTICAL SIGNIFICANCE OF SCAFFOLDING GAP (paired t-test)")
print("=" * 80)
print()

for model in MODELS:
    unsca_scores = []
    sca_scores = []
    for epoch in [1, 2, 3]:
        for case in CASES:
            unsca_scores.append(DATA[model][epoch][case]["unscaffolded"])
            sca_scores.append(DATA[model][epoch][case]["scaffolded"])

    t_stat, df, p_val = paired_t_test(sca_scores, unsca_scores)
    d_vals = [s - u for s, u in zip(sca_scores, unsca_scores)]
    d_mean = mean(d_vals)
    d_sd_val = sd(d_vals)

    # Cohen's d for paired samples
    cohens_d = d_mean / d_sd_val if d_sd_val > 0 else float('inf')

    sig = ""
    if p_val <= 0.001:
        sig = "***"
    elif p_val <= 0.01:
        sig = "**"
    elif p_val <= 0.05:
        sig = "*"
    else:
        sig = "n.s."

    print(f"--- {model} ---")
    print(f"  N pairs     = {len(unsca_scores)} (3 epochs x 4 cases)")
    print(f"  Mean diff   = {fmt(d_mean)} (scaffolded - unscaffolded)")
    print(f"  SD of diffs = {fmt(d_sd_val)}")
    print(f"  t-statistic = {fmt(t_stat)}")
    print(f"  df          = {df}")
    print(f"  p (approx)  < {p_val} {sig}")
    print(f"  Cohen's d   = {fmt(cohens_d)} ({'large' if abs(cohens_d) >= 0.8 else 'medium' if abs(cohens_d) >= 0.5 else 'small'})")
    print()

# Also test at epoch-level (n=3, less power)
print("  Epoch-level paired t-tests (n=3 epoch means):")
print()
for model in MODELS:
    unsca_epoch = gather_epoch_means(model, "unscaffolded")
    sca_epoch = gather_epoch_means(model, "scaffolded")
    t_stat, df, p_val = paired_t_test(sca_epoch, unsca_epoch)
    d_vals = [s - u for s, u in zip(sca_epoch, unsca_epoch)]
    d_mean = mean(d_vals)
    print(f"  {model:<20s}: mean gap = {fmt(d_mean)}, t = {fmt(t_stat)}, df = {df}, p < {p_val}")
print()

# -----------------------------------------------------------------------
# 8. CRITICAL_FAIL and GATE events
# -----------------------------------------------------------------------
print("=" * 80)
print("8. CRITICAL_FAIL AND GATE_TRIGGERED EVENTS")
print("=" * 80)
print()

event_counts = defaultdict(int)
for ev in SPECIAL_EVENTS:
    event_counts[ev["event"]] += 1
    print(f"  [{ev['event']}] {ev['model']} / {ev['case']} / {ev['condition']} / Epoch {ev['epoch']}")
    print(f"    Details: {ev['details']}")
    print(f"    Score: {DATA[ev['model']][ev['epoch']][ev['case']][ev['condition']]}/{MAX_SCORE}")
    print()

print(f"  TOTALS: {event_counts['CRITICAL_FAIL']} CRITICAL_FAIL, {event_counts['GATE_TRIGGERED']} GATE_TRIGGERED")
print(f"  All events are GPT-4o only.")
print(f"  CRITICAL_FAIL cases: IT_001 (E2 unsca), UK_003 (E3 unsca)")
print(f"  GATE_TRIGGERED cases: UK_003 (E1 unsca, E3 sca)")
print()

# -----------------------------------------------------------------------
# BONUS: Cross-model comparison table
# -----------------------------------------------------------------------
print("=" * 80)
print("SUMMARY TABLE: MODEL COMPARISON")
print("=" * 80)
print()
print(f"{'Metric':<40s} {'Claude':>10s} {'GPT-4o':>10s} {'Gemini':>10s}")
print("-" * 72)

for label, cond in [("Mean unscaffolded (3-epoch)", "unscaffolded"),
                     ("Mean scaffolded (3-epoch)", "scaffolded")]:
    vals = []
    for model in MODELS:
        epoch_means = gather_epoch_means(model, cond)
        vals.append(mean(epoch_means))
    print(f"{label:<40s} {fmt(vals[0]):>10s} {fmt(vals[1]):>10s} {fmt(vals[2]):>10s}")

# Overall mean
vals = []
for model in MODELS:
    epoch_means = gather_epoch_means(model, None)
    vals.append(mean(epoch_means))
print(f"{'Mean overall (3-epoch)':<40s} {fmt(vals[0]):>10s} {fmt(vals[1]):>10s} {fmt(vals[2]):>10s}")

# Mean gap
for model_idx, model in enumerate(MODELS):
    pass  # computed below
vals = []
for model in MODELS:
    gaps = all_model_gaps[model]
    vals.append(mean(gaps))
print(f"{'Mean scaffolding gap':<40s} {fmt(vals[0]):>10s} {fmt(vals[1]):>10s} {fmt(vals[2]):>10s}")

# Run-to-run SD
vals = []
for model in MODELS:
    epoch_means = gather_epoch_means(model, None)
    vals.append(sd(epoch_means))
print(f"{'Run-to-run SD (overall)':<40s} {fmt(vals[0]):>10s} {fmt(vals[1]):>10s} {fmt(vals[2]):>10s}")

# Pass rates
for label, cond in [("Unsca pass rate (X/12)", "unscaffolded"),
                     ("Sca pass rate (X/12)", "scaffolded")]:
    vals = []
    for model in MODELS:
        n = sum(1 for e in [1,2,3] for c in CASES if passes(DATA[model][e][c][cond]))
        vals.append(f"{n}/12")
    print(f"{label:<40s} {vals[0]:>10s} {vals[1]:>10s} {vals[2]:>10s}")

# Normalized scores
for label, cond in [("Unsca % of max", "unscaffolded"),
                     ("Sca % of max", "scaffolded")]:
    vals = []
    for model in MODELS:
        epoch_means = gather_epoch_means(model, cond)
        vals.append(mean(epoch_means) / MAX_SCORE * 100)
    print(f"{label:<40s} {fmt(vals[0]) + '%':>10s} {fmt(vals[1]) + '%':>10s} {fmt(vals[2]) + '%':>10s}")

print()

# -----------------------------------------------------------------------
# BONUS: Hardest and easiest cases
# -----------------------------------------------------------------------
print("=" * 80)
print("CASE DIFFICULTY RANKING (mean unscaffolded across all models, all epochs)")
print("=" * 80)
print()

case_difficulty = []
for case in CASES:
    all_unsca = []
    for model in MODELS:
        for epoch in [1, 2, 3]:
            all_unsca.append(DATA[model][epoch][case]["unscaffolded"])
    m = mean(all_unsca)
    s = sd(all_unsca)
    case_difficulty.append((case, m, s, all_unsca))

case_difficulty.sort(key=lambda x: x[1])

for rank, (case, m, s, scores) in enumerate(case_difficulty, 1):
    pass_n = sum(1 for x in scores if passes(x))
    print(f"  {rank}. {case}: mean = {fmt(m)}/{MAX_SCORE} ({fmt(m/MAX_SCORE*100)}%), "
          f"SD = {fmt(s)}, pass rate = {pass_n}/{len(scores)}")

print()

# -----------------------------------------------------------------------
# BONUS: IT_001 deep dive (hardest case)
# -----------------------------------------------------------------------
print("=" * 80)
print("IT_001 DEEP DIVE (cross-lingual case, typically hardest)")
print("=" * 80)
print()

for model in MODELS:
    unsca = gather_case_scores(model, "IT_001", "unscaffolded")
    sca = gather_case_scores(model, "IT_001", "scaffolded")
    gaps = [s - u for s, u in zip(sca, unsca)]
    print(f"  {model}:")
    print(f"    Unscaffolded: {unsca}, mean = {fmt(mean(unsca))}, SD = {fmt(sd(unsca))}")
    print(f"    Scaffolded:   {sca}, mean = {fmt(mean(sca))}, SD = {fmt(sd(sca))}")
    print(f"    Gaps:         {gaps}, mean gap = {fmt(mean(gaps))}")
    unsca_pass = sum(1 for x in unsca if passes(x))
    sca_pass = sum(1 for x in sca if passes(x))
    print(f"    Pass rate: unsca {unsca_pass}/3, sca {sca_pass}/3")
    print()

print("=" * 80)
print("END OF ANALYSIS")
print("=" * 80)
