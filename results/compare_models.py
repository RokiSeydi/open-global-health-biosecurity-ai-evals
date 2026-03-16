#!/usr/bin/env python3
"""Cross-model comparison script for Domain 1 evaluation results.

Reads Inspect eval log files, extracts per-dimension scores for each model
and prompt type, computes the scaffolded-unscaffolded gap, and produces:
    - results/scores_table.csv      — full dimension scores per model
    - results/gap_analysis.csv      — gap scores per model
    - Terminal summary table

Usage:
    python results/compare_models.py
    python results/compare_models.py --log-dir logs/
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from typing import Any

from inspect_ai.log import list_eval_logs, read_eval_log, read_eval_log_samples


DIMENSION_ORDER: list[str] = [
    "D1_narrative_arc",
    "D1_institutional_reflex",
    "D1_intent_recognition",
    "D1_compliance_framing",
    "D1_register_respect",
    "D1_contextual_proportionality",
]


def extract_model_name(eval_spec: Any) -> str:
    """Extract a readable model name from the eval spec."""
    model = eval_spec.model
    if hasattr(model, "name"):
        model = model.name
    model = str(model)
    for prefix in ("anthropic/", "openai/", "google/"):
        if model.startswith(prefix):
            model = model[len(prefix):]
    return model


def extract_results(log_dir: str) -> list[dict[str, Any]]:
    """Extract scored results from all eval logs in the directory."""
    records: list[dict[str, Any]] = []

    logs = list_eval_logs(log_dir)
    if not logs:
        print(f"No eval logs found in {log_dir}")
        sys.exit(1)

    for log_info in logs:
        log = read_eval_log(log_info.name)

        if log.status != "success":
            print(f"  Skipping {log_info.name} (status: {log.status})")
            continue

        model_name: str = extract_model_name(log.eval)

        for sample in read_eval_log_samples(log_info.name):
            if not sample.scores:
                continue

            for scorer_name, score_obj in sample.scores.items():
                metadata: dict[str, Any] = score_obj.metadata or {}
                dimension_scores: dict[str, int] = metadata.get("dimension_scores", {})
                if not dimension_scores:
                    continue

                records.append({
                    "model": model_name,
                    "sample_id": sample.id,
                    "prompt_type": metadata.get("prompt_type", "unknown"),
                    "total_score": metadata.get("total_score", 0),
                    "max_score": metadata.get("max_score", 18),
                    "outcome": metadata.get("outcome", "unknown"),
                    "gate_triggered": metadata.get("gate_triggered", False),
                    "critical_fail": metadata.get("critical_fail", False),
                    **{dim: dimension_scores.get(dim, -1) for dim in DIMENSION_ORDER},
                })

    return records


def write_scores_table(records: list[dict[str, Any]], output_path: Path) -> None:
    """Write full dimension scores to CSV."""
    fieldnames: list[str] = [
        "model", "prompt_type", "total_score", "max_score", "outcome",
        "gate_triggered", "critical_fail",
    ] + DIMENSION_ORDER

    with open(output_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for record in sorted(records, key=lambda r: (r["model"], r["prompt_type"])):
            writer.writerow(record)

    print(f"Wrote {output_path}")


def write_gap_analysis(
    records: list[dict[str, Any]], output_path: Path
) -> list[dict[str, Any]]:
    """Compute and write scaffolded-unscaffolded gap per model."""
    by_model: dict[str, dict[str, dict[str, Any]]] = {}
    for r in records:
        model: str = r["model"]
        if model not in by_model:
            by_model[model] = {}
        by_model[model][r["prompt_type"]] = r

    rows: list[dict[str, Any]] = []
    for model, prompt_types in sorted(by_model.items()):
        unscaffolded: dict[str, Any] = prompt_types.get("unscaffolded", {})
        scaffolded: dict[str, Any] = prompt_types.get("scaffolded", {})

        u_total: int = unscaffolded.get("total_score", 0)
        s_total: int = scaffolded.get("total_score", 0)

        row: dict[str, Any] = {
            "model": model,
            "unscaffolded_total": u_total,
            "scaffolded_total": s_total,
            "gap": s_total - u_total,
            "unscaffolded_outcome": unscaffolded.get("outcome", "N/A"),
            "scaffolded_outcome": scaffolded.get("outcome", "N/A"),
        }

        for dim in DIMENSION_ORDER:
            u_dim: int = unscaffolded.get(dim, 0)
            s_dim: int = scaffolded.get(dim, 0)
            row[f"{dim}_gap"] = s_dim - u_dim

        rows.append(row)

    fieldnames: list[str] = [
        "model", "unscaffolded_total", "scaffolded_total", "gap",
        "unscaffolded_outcome", "scaffolded_outcome",
    ] + [f"{dim}_gap" for dim in DIMENSION_ORDER]

    with open(output_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    print(f"Wrote {output_path}")
    return rows


def print_summary(
    records: list[dict[str, Any]], gap_rows: list[dict[str, Any]]
) -> None:
    """Print summary tables to terminal."""
    print("\n" + "=" * 78)
    print("DOMAIN 1: CULTURAL CONTEXTUAL VALIDITY — CROSS-MODEL COMPARISON")
    print("=" * 78)

    print(f"\n{'Model':<22} {'Type':<14} {'Score':>7} {'Outcome':<16} {'Gate':>5}")
    print("-" * 68)
    for r in sorted(records, key=lambda x: (x["model"], x["prompt_type"])):
        gate_str: str = "YES" if r["gate_triggered"] else ""
        print(
            f"{r['model']:<22} {r['prompt_type']:<14} "
            f"{r['total_score']:>2}/{r['max_score']:<4} "
            f"{r['outcome']:<16} {gate_str:>5}"
        )

    if gap_rows:
        print(f"\n{'Model':<22} {'Unscaffolded':>12} {'Scaffolded':>10} {'Gap':>5} "
              f"{'Outcome (unscaffolded)':<24}")
        print("-" * 78)
        for row in gap_rows:
            outcome: str = row["unscaffolded_outcome"]
            if row.get("gate_triggered"):
                outcome += " (gate)"
            print(
                f"{row['model']:<22} "
                f"{row['unscaffolded_total']:>5}/18    "
                f"{row['scaffolded_total']:>5}/18  "
                f"{'+' if row['gap'] >= 0 else ''}{row['gap']:<4} "
                f"{outcome:<24}"
            )

        print("\nGap Hypothesis: All models show >= 4 point delta")
        all_pass: bool = all(
            row["gap"] >= 4 for row in gap_rows if row["scaffolded_total"] > 0
        )
        print(f"Result: {'SUPPORTED' if all_pass else 'NOT YET TESTABLE (need scaffolded runs)'}")

    print("=" * 78)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare Domain 1 eval results across models"
    )
    parser.add_argument(
        "--log-dir", default="logs/",
        help="Directory containing Inspect eval logs (default: logs/)",
    )
    args = parser.parse_args()

    project_root: Path = Path(__file__).resolve().parent.parent
    log_dir: Path = project_root / args.log_dir
    results_dir: Path = project_root / "results"

    print(f"Reading logs from: {log_dir}")
    records: list[dict[str, Any]] = extract_results(str(log_dir))

    if not records:
        print("No scored results found. Run evaluations first.")
        sys.exit(1)

    print(f"Found {len(records)} scored results")

    write_scores_table(records, results_dir / "scores_table.csv")
    gap_rows: list[dict[str, Any]] = write_gap_analysis(
        records, results_dir / "gap_analysis.csv"
    )
    print_summary(records, gap_rows)


if __name__ == "__main__":
    main()
