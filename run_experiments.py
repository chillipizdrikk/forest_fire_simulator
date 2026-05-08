from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Any

from src.app.experiments.analysis import analyze_results
from src.app.experiments.reporting import generate_report
from src.app.experiments.scenarios import load_scenarios


def _sanitize_cli_argv(argv: list[str]) -> list[str]:
    # Users sometimes copy bash-style line continuations "\" into PowerShell,
    # where "\" is passed as a literal argument and breaks argparse.
    return [arg for arg in argv if arg.strip() not in {"\\", "\\n", "\\r\\n"}]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Batch experiments for forest fire simulator")
    parser.add_argument("--scenarios", default="scenarios.yaml", help="Path to scenarios.yaml")
    parser.add_argument("--n", type=int, default=100, help="Runs per scenario")
    parser.add_argument("--seed", type=int, default=42, help="Master seed for reproducible batches")
    parser.add_argument("--max-steps", type=int, default=500, help="Max simulation steps per run")
    parser.add_argument("--critical-baf-threshold", type=float, default=0.8, help="Threshold for critical scenario")
    parser.add_argument(
        "--censor-target-share",
        type=float,
        default=0.02,
        help="Target maximum censored share per scenario after audit reruns",
    )
    parser.add_argument(
        "--censor-max-retries",
        type=int,
        default=2,
        help="Max rerun rounds for scenarios above censor-target-share",
    )
    parser.add_argument(
        "--censor-step-multiplier",
        type=float,
        default=1.6,
        help="Multiplier for max_steps when rerunning censored scenarios",
    )
    parser.add_argument(
        "--disable-censor-audit",
        action="store_true",
        help="Disable adaptive reruns for scenarios with high censored share",
    )
    parser.add_argument("--results-dir", default="results/raw", help="Directory for CSV/Parquet outputs")
    parser.add_argument("--reports-dir", default="reports", help="Directory for markdown/html reports")
    raw_argv = list(sys.argv[1:] if argv is None else argv)
    sanitized = _sanitize_cli_argv(raw_argv)
    return parser.parse_args(sanitized)


def _flatten_results(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    flattened_rows: list[dict[str, Any]] = []
    for item in results:
        row = {"run_id": item["run_id"], "scenario": item["scenario"], "seed": item["seed"]}
        row.update({f"param_{k}": v for k, v in item["params"].items()})
        row.update(item["metrics"])
        flattened_rows.append(row)
    return flattened_rows


def _group_results_by_scenario(results: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for item in results:
        grouped.setdefault(str(item["scenario"]), []).append(item)
    return grouped


def _collect_problematic_scenarios(summary: Any, target_share: float) -> list[str]:
    return sorted(
        [
            scenario_name
            for scenario_name, stats in summary.by_scenario.items()
            if float(stats.get("censored_share", 0.0)) >= float(target_share)
        ]
    )


def _scenario_snapshot(summary: Any, scenario_name: str) -> dict[str, float]:
    stats = summary.by_scenario.get(scenario_name, {})
    return {
        "censored_share": float(stats.get("censored_share", 0.0)),
        "baf_mean_all": float(stats.get("baf_mean_all", 0.0)),
        "auc_normalized_mean_all": float(stats.get("auc_normalized_mean_all", 0.0)),
    }


def main() -> None:
    from src.app.experiments.runner import ExperimentResult, persist_results, results_to_dicts, run_experiments as run_batch

    args = parse_args()

    scenarios_path = Path(args.scenarios)
    if "sensitivity" in scenarios_path.stem and args.n < 100:
        print(f"[info] Sensitivity run requires at least 100 runs per scenario; overriding --n from {args.n} to 100.")
        args.n = 100

    defaults, scenarios = load_scenarios(args.scenarios)
    results = run_batch(
        defaults=defaults,
        scenarios=scenarios,
        runs_per_scenario=args.n,
        base_seed=args.seed,
        max_steps=args.max_steps,
        critical_baf_threshold=args.critical_baf_threshold,
    )

    results_payload = results_to_dicts(results)
    current_max_steps = int(args.max_steps)
    scenario_defs = {scenario.name: scenario for scenario in scenarios}
    grouped_results = _group_results_by_scenario(results_payload)
    audit_rounds: list[dict[str, Any]] = []
    stop_reason = "audit_disabled" if args.disable_censor_audit else "target_met_initial"

    if not args.disable_censor_audit:
        for round_index in range(1, max(0, int(args.censor_max_retries)) + 1):
            rows_before = _flatten_results([item for group in grouped_results.values() for item in group])
            summary_before = analyze_results(rows_before, critical_baf_threshold=args.critical_baf_threshold)
            problematic = _collect_problematic_scenarios(summary_before, args.censor_target_share)
            if not problematic:
                stop_reason = "target_met"
                break

            next_max_steps = max(current_max_steps + 1, int(current_max_steps * float(args.censor_step_multiplier)))
            rerun_scenarios = [scenario_defs[name] for name in problematic if name in scenario_defs]
            rerun_results = run_batch(
                defaults=defaults,
                scenarios=rerun_scenarios,
                runs_per_scenario=args.n,
                base_seed=args.seed + round_index * 100_003,
                max_steps=next_max_steps,
                critical_baf_threshold=args.critical_baf_threshold,
            )
            rerun_payload = results_to_dicts(rerun_results)
            rerun_grouped = _group_results_by_scenario(rerun_payload)
            for scenario_name, items in rerun_grouped.items():
                grouped_results[scenario_name] = items

            rows_after = _flatten_results([item for group in grouped_results.values() for item in group])
            summary_after = analyze_results(rows_after, critical_baf_threshold=args.critical_baf_threshold)

            scenario_deltas = []
            for scenario_name in problematic:
                before = _scenario_snapshot(summary_before, scenario_name)
                after = _scenario_snapshot(summary_after, scenario_name)
                scenario_deltas.append(
                    {
                        "scenario": scenario_name,
                        "before_censored_share": before["censored_share"],
                        "after_censored_share": after["censored_share"],
                        "before_baf_mean_all": before["baf_mean_all"],
                        "after_baf_mean_all": after["baf_mean_all"],
                        "before_auc_normalized_mean_all": before["auc_normalized_mean_all"],
                        "after_auc_normalized_mean_all": after["auc_normalized_mean_all"],
                    }
                )

            audit_rounds.append(
                {
                    "round": round_index,
                    "from_max_steps": current_max_steps,
                    "to_max_steps": next_max_steps,
                    "rerun_scenarios": problematic,
                    "scenario_deltas": scenario_deltas,
                }
            )
            current_max_steps = next_max_steps

        else:
            stop_reason = "max_retries_reached"

    final_results_payload = [item for group in grouped_results.values() for item in group]
    final_rows = _flatten_results(final_results_payload)
    final_summary = analyze_results(final_rows, critical_baf_threshold=args.critical_baf_threshold)
    final_problematic = _collect_problematic_scenarios(final_summary, args.censor_target_share)
    if stop_reason == "target_met_initial" and final_problematic:
        stop_reason = "target_not_met_initial"

    censoring_audit = {
        "target_censored_share": float(args.censor_target_share),
        "initial_max_steps": int(args.max_steps),
        "final_max_steps": int(current_max_steps),
        "stop_reason": stop_reason,
        "rounds": audit_rounds,
        "final_problematic_scenarios": final_problematic,
    }

    persisted_results = [
        ExperimentResult(
            run_id=str(item["run_id"]),
            scenario=str(item["scenario"]),
            seed=int(item["seed"]),
            params=dict(item["params"]),
            metrics=dict(item["metrics"]),
        )
        for item in final_results_payload
    ]

    csv_path, parquet_path = persist_results(persisted_results, Path(args.results_dir))
    md_path, html_path, _ = generate_report(
        final_rows,
        final_summary,
        Path(args.reports_dir),
        censoring_audit=censoring_audit,
    )

    print(f"Results CSV: {csv_path}")
    print(f"Results Parquet: {parquet_path if parquet_path else 'not generated (missing parquet dependencies)'}")
    print(f"Report markdown: {md_path}")
    print(f"Report html: {html_path}")
    print(
        "[censor-audit] "
        f"target={args.censor_target_share:.4f}, final_problematic={len(final_problematic)}, "
        f"rounds={len(audit_rounds)}, max_steps={args.max_steps}->{current_max_steps}, stop_reason={stop_reason}"
    )


if __name__ == "__main__":
    main()
