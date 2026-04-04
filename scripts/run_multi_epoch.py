#!/usr/bin/env python3
"""Multi-epoch evaluation runner for variance quantification.

Runs N independent eval passes per model per condition (unscaffolded/scaffolded)
and stores logs for statistical analysis.

Usage:
    python scripts/run_multi_epoch.py --epochs 3
    python scripts/run_multi_epoch.py --epochs 5 --models claude
    python scripts/run_multi_epoch.py --epochs 3 --conditions unscaffolded
    python scripts/run_multi_epoch.py --epochs 3 --domain legal
    python scripts/run_multi_epoch.py --epochs 3 --domain sociological --models claude gpt4o
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path


MODELS: dict[str, str] = {
    "claude": "anthropic/claude-sonnet-4-20250514",
    "gpt4o": "openai/gpt-4o",
    "gemini": "google/gemini-2.5-pro",
    "deepseek": "deepseek/deepseek-r1",
    "llama": "meta/llama-4-maverick",
}

CONDITIONS: list[str] = ["unscaffolded", "scaffolded"]

DOMAIN_TASK_FILES: dict[str, str] = {
    "d1": "src/global_health_ai_evals/domain1_cultural/domain1_cultural.py",
    "d2": "src/global_health_ai_evals/domain2_chw_competency/domain2_chw_competency.py",
    "d3": "src/global_health_ai_evals/domain3_fragile_health_systems/domain3_fragile_health_systems.py",
    "legal": "src/global_health_ai_evals/legal_reasoning/legal_reasoning.py",
    "sociological": "src/global_health_ai_evals/sociological_reasoning/sociological_reasoning.py",
}

TASK_FILE = DOMAIN_TASK_FILES["d1"]  # default for backwards compat


def run_eval(
    model_key: str,
    model_id: str,
    condition: str,
    epoch: int,
    log_dir: Path,
    task_file: str = TASK_FILE,
) -> bool:
    """Run a single eval pass. Returns True on success."""
    label = f"{model_key}/{condition}/epoch-{epoch}"
    print(f"\n{'='*60}")
    print(f"  RUNNING: {label}")
    print(f"  Model:     {model_id}")
    print(f"  Condition: {condition}")
    print(f"  Epoch:     {epoch}")
    print(f"{'='*60}\n")

    cmd: list[str] = [
        "inspect", "eval", task_file,
        "--model", model_id,
        "-T", f"prompt_type={condition}",
        "--log-dir", str(log_dir),
    ]

    try:
        result = subprocess.run(
            cmd,
            cwd=str(Path(__file__).resolve().parent.parent),
            capture_output=False,
            timeout=300,
        )
        if result.returncode == 0:
            print(f"\n  OK: {label}")
            return True
        else:
            print(f"\n  FAILED: {label} (exit code {result.returncode})")
            return False
    except subprocess.TimeoutExpired:
        print(f"\n  TIMEOUT: {label}")
        return False
    except Exception as e:
        print(f"\n  ERROR: {label} — {e}")
        return False


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run multi-epoch evaluations for variance quantification"
    )
    parser.add_argument(
        "--epochs", type=int, default=3,
        help="Number of independent epochs per model per condition (default: 3)",
    )
    parser.add_argument(
        "--models", nargs="+", default=list(MODELS.keys()),
        choices=list(MODELS.keys()),
        help="Models to evaluate (default: all)",
    )
    parser.add_argument(
        "--conditions", nargs="+", default=CONDITIONS,
        choices=CONDITIONS,
        help="Conditions to run (default: both)",
    )
    parser.add_argument(
        "--domain", default="d1",
        choices=list(DOMAIN_TASK_FILES.keys()),
        help="Domain to evaluate (default: d1)",
    )
    args = parser.parse_args()

    task_file: str = DOMAIN_TASK_FILES[args.domain]

    project_root: Path = Path(__file__).resolve().parent.parent
    timestamp: str = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_dir: Path = project_root / "logs" / f"multi_epoch_{args.domain}_{timestamp}"
    log_dir.mkdir(parents=True, exist_ok=True)

    total_runs: int = args.epochs * len(args.models) * len(args.conditions)
    print(f"Multi-epoch evaluation run")
    print(f"  Domain:     {args.domain}")
    print(f"  Task file:  {task_file}")
    print(f"  Epochs:     {args.epochs}")
    print(f"  Models:     {args.models}")
    print(f"  Conditions: {args.conditions}")
    print(f"  Total runs: {total_runs}")
    print(f"  Log dir:    {log_dir}")
    print()

    results: list[dict[str, str | bool]] = []
    run_num = 0

    for model_key in args.models:
        model_id: str = MODELS[model_key]
        for condition in args.conditions:
            for epoch in range(1, args.epochs + 1):
                run_num += 1
                print(f"\n[{run_num}/{total_runs}]")
                success = run_eval(model_key, model_id, condition, epoch, log_dir, task_file)
                results.append({
                    "model": model_key,
                    "condition": condition,
                    "epoch": str(epoch),
                    "success": success,
                })

    # Summary
    passed = sum(1 for r in results if r["success"])
    failed = sum(1 for r in results if not r["success"])

    print(f"\n{'='*60}")
    print(f"  COMPLETE: {passed}/{total_runs} succeeded, {failed} failed")
    print(f"  Logs:     {log_dir}")
    print(f"\n  Next: python scripts/analyse_multi_epoch.py --log-dir {log_dir}")
    print(f"{'='*60}")

    if failed > 0:
        for r in results:
            if not r["success"]:
                print(f"  FAILED: {r['model']}/{r['condition']}/epoch-{r['epoch']}")
        sys.exit(1)


if __name__ == "__main__":
    main()
