from __future__ import annotations

import json
from typing import Sequence

METRICS_PAYLOAD_SCHEMA_VERSION = 2


def _clean_burning_series(burning_cells: Sequence[int]) -> list[int]:
    return [max(0, int(value)) for value in burning_cells]


def peak_fire_size(burning_cells: Sequence[int]) -> int:
    series = _clean_burning_series(burning_cells)
    return max(series, default=0)


def time_to_peak(burning_cells: Sequence[int]) -> int:
    series = _clean_burning_series(burning_cells)
    if not series:
        return 0
    peak = max(series)
    return int(series.index(peak))


def fire_duration(burning_cells: Sequence[int]) -> int:
    series = _clean_burning_series(burning_cells)
    return sum(1 for value in series if value > 0)


def area_under_curve(burning_cells: Sequence[int]) -> int:
    series = _clean_burning_series(burning_cells)
    return int(sum(series))


def burned_area_fraction(initial_tree_cells: int, final_burnt_cells: int) -> float:
    trees = max(0, int(initial_tree_cells))
    burnt = max(0, int(final_burnt_cells))
    if trees == 0:
        return 0.0
    return float(min(1.0, burnt / trees))


def time_to_extinguish(burning_cells: Sequence[int]) -> int:
    series = _clean_burning_series(burning_cells)
    if all(burning == 0 for burning in series):
        return 0
    fire_started = False
    for step_idx, burning in enumerate(series):
        if burning > 0:
            fire_started = True
        if fire_started and burning == 0:
            return int(step_idx)
    return max(len(series) - 1, 0)


def max_spread_rate(burning_cells: Sequence[int]) -> int:
    series = _clean_burning_series(burning_cells)
    if len(series) < 2:
        return 0
    diffs = [series[idx] - series[idx - 1] for idx in range(1, len(series))]
    return int(max(diffs, default=0))


def calculate_fire_metrics(
    burning_cells: Sequence[int],
    initial_tree_cells: int,
    final_counts: dict[str, int],
) -> dict[str, int | float]:
    final_burnt = int(final_counts.get("burnt", 0))
    metrics = {
        "baf": burned_area_fraction(initial_tree_cells, final_burnt),
        "peak_fire_size": peak_fire_size(burning_cells),
        "time_to_peak": time_to_peak(burning_cells),
        "fire_duration": fire_duration(burning_cells),
        "auc": area_under_curve(burning_cells),
    }
    return metrics


def calculate_derived_metrics(
    *,
    burning_cells: Sequence[int],
    step_count: int,
    initial_tree_cells: int,
    critical_baf_threshold: float,
    baf: float,
    steps_total_or_fire_horizon: int | None = None,
) -> dict[str, int | float | bool]:
    trees_total = max(0, int(initial_tree_cells))
    steps_total = max(0, int(step_count))
    steps_normalizer = max(0, int(steps_total_or_fire_horizon if steps_total_or_fire_horizon is not None else steps_total))
    peak_size = peak_fire_size(burning_cells)
    auc = area_under_curve(burning_cells)
    auc_denominator = trees_total * steps_normalizer

    return {
        "time_to_extinguish": time_to_extinguish(burning_cells),
        "max_spread_rate": max_spread_rate(burning_cells),
        "initial_tree_cells": trees_total,
        "steps_total": steps_total,
        "steps_total_or_fire_horizon": steps_normalizer,
        "peak_fire_fraction": float(peak_size / trees_total) if trees_total > 0 else 0.0,
        "auc_normalization_denominator": int(auc_denominator),
        "auc_normalized": float(auc / auc_denominator) if auc_denominator > 0 else 0.0,
        "critical": bool(float(baf) >= float(critical_baf_threshold)),
    }


def metrics_to_json(payload: dict[str, object]) -> str:
    normalized = read_metrics_payload(payload)
    return json.dumps(normalized, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def read_metrics_payload(raw_payload: dict[str, object]) -> dict[str, object]:
    payload = dict(raw_payload)

    final_counts_raw = payload.get("final_counts", {})
    final_counts = final_counts_raw if isinstance(final_counts_raw, dict) else {}

    metrics_raw = payload.get("metrics", {})
    metrics = metrics_raw if isinstance(metrics_raw, dict) else {}

    config_snapshot_raw = payload.get("config_snapshot", {})
    config_snapshot = config_snapshot_raw if isinstance(config_snapshot_raw, dict) else {}

    return {
        "schema_version": int(payload.get("schema_version", METRICS_PAYLOAD_SCHEMA_VERSION)),
        "generated_at_utc": str(payload.get("generated_at_utc", "")),
        "seed": payload.get("seed"),
        "step_count": int(payload.get("step_count", 0)),
        "initial_tree_cells": int(payload.get("initial_tree_cells", 0)),
        "burning_cells_t": [max(0, int(value)) for value in payload.get("burning_cells_t", [])],
        "final_counts": {str(key): int(value) for key, value in final_counts.items()},
        "metrics": {str(key): value for key, value in metrics.items()},
        "config_snapshot": {str(key): value for key, value in config_snapshot.items()},
    }
