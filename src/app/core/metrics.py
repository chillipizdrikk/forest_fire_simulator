from __future__ import annotations

import json
from typing import Sequence


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


def metrics_to_json(payload: dict[str, object]) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)
