from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import csv
from typing import Any

import numpy as np

from src.app.core.config import CAConfig
from src.app.core.engine import ForestFireCA
from src.app.core.metrics import calculate_derived_metrics
from src.app.experiments.scenarios import ScenarioDefinition


@dataclass(frozen=True)
class ExperimentResult:
    run_id: str
    scenario: str
    seed: int
    params: dict[str, Any]
    metrics: dict[str, Any]


def _first_ignition_point(cfg: CAConfig) -> tuple[int, int]:
    return cfg.height // 2, cfg.width // 2


def _simulate_single_run(cfg: CAConfig, max_steps: int, critical_baf_threshold: float) -> dict[str, Any]:
    ca = ForestFireCA(cfg)
    ignite_row, ignite_col = _first_ignition_point(cfg)
    ca.ignite(ignite_row, ignite_col)

    fire_started = ca.has_active_fire()
    for _ in range(max_steps):
        if fire_started and not ca.has_active_fire():
            break
        ca.step()
        fire_started = fire_started or ca.has_active_fire()

    final_metrics = ca.finalize_run_metrics()
    series = [int(v) for v in ca.burning_cells_history]

    return {
        **final_metrics,
        **calculate_derived_metrics(
            burning_cells=series,
            step_count=ca.step_count,
            critical_baf_threshold=critical_baf_threshold,
            baf=float(final_metrics.get("baf", 0.0)),
        ),
    }


def run_experiments(
    *,
    defaults: dict[str, Any],
    scenarios: list[ScenarioDefinition],
    runs_per_scenario: int,
    base_seed: int,
    max_steps: int,
    critical_baf_threshold: float,
) -> list[ExperimentResult]:
    rng = np.random.default_rng(base_seed)
    all_results: list[ExperimentResult] = []

    for scenario in scenarios:
        merged_params: dict[str, Any] = {**defaults, **scenario.params}
        for run_index in range(runs_per_scenario):
            seed = int(rng.integers(0, np.iinfo(np.int32).max))
            cfg = CAConfig(**{**merged_params, "seed": seed})
            metrics = _simulate_single_run(cfg, max_steps=max_steps, critical_baf_threshold=critical_baf_threshold)

            all_results.append(
                ExperimentResult(
                    run_id=f"{scenario.name}-{run_index:04d}",
                    scenario=scenario.name,
                    seed=seed,
                    params=merged_params,
                    metrics=metrics,
                )
            )
    return all_results


def persist_results(results: list[ExperimentResult], output_dir: str | Path) -> tuple[Path, Path | None]:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, Any]] = []
    for result in results:
        row = {
            "run_id": result.run_id,
            "scenario": result.scenario,
            "seed": result.seed,
        }
        row.update({f"param_{k}": v for k, v in result.params.items()})
        row.update(result.metrics)
        rows.append(row)

    csv_path = output_path / f"experiment_results_{ts}.csv"
    fieldnames = sorted({key for row in rows for key in row.keys()})
    with csv_path.open("w", newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(fp, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    parquet_path: Path | None = None
    try:
        import pandas as pd

        frame = pd.DataFrame(rows)
        parquet_path = output_path / f"experiment_results_{ts}.parquet"
        frame.to_parquet(parquet_path, index=False)
    except Exception:
        parquet_path = None

    return csv_path, parquet_path


def results_to_dicts(results: list[ExperimentResult]) -> list[dict[str, Any]]:
    payload: list[dict[str, Any]] = []
    for result in results:
        payload.append(
            {
                "run_id": result.run_id,
                "scenario": result.scenario,
                "seed": result.seed,
                "params": dict(result.params),
                "metrics": dict(result.metrics),
            }
        )
    return payload
