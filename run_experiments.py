from __future__ import annotations

import argparse
from pathlib import Path

from src.app.experiments.analysis import analyze_results, generate_report
from src.app.experiments.runner import persist_results, results_to_dicts, run_experiments
from src.app.experiments.scenarios import load_scenarios


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Batch experiments for forest fire simulator")
    parser.add_argument("--scenarios", default="scenarios.yaml", help="Path to scenarios.yaml")
    parser.add_argument("--n", type=int, default=100, help="Runs per scenario")
    parser.add_argument("--seed", type=int, default=42, help="Master seed for reproducible batches")
    parser.add_argument("--max-steps", type=int, default=500, help="Max simulation steps per run")
    parser.add_argument("--critical-baf-threshold", type=float, default=0.8, help="Threshold for critical scenario")
    parser.add_argument("--results-dir", default="results/raw", help="Directory for CSV/Parquet outputs")
    parser.add_argument("--reports-dir", default="reports", help="Directory for markdown/html reports")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    scenarios_path = Path(args.scenarios)
    if "sensitivity" in scenarios_path.stem and args.n < 100:
        print(f"[info] Sensitivity run requires at least 100 runs per scenario; overriding --n from {args.n} to 100.")
        args.n = 100

    defaults, scenarios = load_scenarios(args.scenarios)
    results = run_experiments(
        defaults=defaults,
        scenarios=scenarios,
        runs_per_scenario=args.n,
        base_seed=args.seed,
        max_steps=args.max_steps,
        critical_baf_threshold=args.critical_baf_threshold,
    )

    csv_path, parquet_path = persist_results(results, Path(args.results_dir))

    flattened_rows = []
    for item in results_to_dicts(results):
        row = {"run_id": item["run_id"], "scenario": item["scenario"], "seed": item["seed"]}
        row.update({f"param_{k}": v for k, v in item["params"].items()})
        row.update(item["metrics"])
        flattened_rows.append(row)

    summary = analyze_results(flattened_rows, critical_baf_threshold=args.critical_baf_threshold)
    md_path, html_path, _ = generate_report(flattened_rows, summary, Path(args.reports_dir))

    print(f"Results CSV: {csv_path}")
    print(f"Results Parquet: {parquet_path if parquet_path else 'not generated (missing parquet dependencies)'}")
    print(f"Report markdown: {md_path}")
    print(f"Report html: {html_path}")


if __name__ == "__main__":
    main()
