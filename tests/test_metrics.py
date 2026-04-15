from __future__ import annotations

import importlib.util
import json
import math
from pathlib import Path

METRICS_PATH = Path(__file__).resolve().parents[1] / "src" / "app" / "core" / "metrics.py"
spec = importlib.util.spec_from_file_location("metrics_module", METRICS_PATH)
assert spec and spec.loader
metrics = importlib.util.module_from_spec(spec)
spec.loader.exec_module(metrics)

peak_fire_size = metrics.peak_fire_size
time_to_peak = metrics.time_to_peak
fire_duration = metrics.fire_duration
area_under_curve = metrics.area_under_curve
burned_area_fraction = metrics.burned_area_fraction
calculate_fire_metrics = metrics.calculate_fire_metrics
time_to_extinguish = metrics.time_to_extinguish
max_spread_rate = metrics.max_spread_rate
calculate_derived_metrics = metrics.calculate_derived_metrics
metrics_to_json = metrics.metrics_to_json
read_metrics_payload = metrics.read_metrics_payload
METRICS_PAYLOAD_SCHEMA_VERSION = metrics.METRICS_PAYLOAD_SCHEMA_VERSION


def test_peak_fire_size_returns_zero_for_empty_series() -> None:
    assert peak_fire_size([]) == 0


def test_peak_fire_size_returns_zero_for_all_zero_series() -> None:
    assert peak_fire_size([0, 0, 0]) == 0


def test_peak_fire_size_cleans_negative_and_float_values() -> None:
    # -3 -> 0, 2.9 -> 2, 1.1 -> 1
    assert peak_fire_size([-3, 2.9, 1.1]) == 2


def test_time_to_peak_returns_zero_for_empty_series_index_from_zero() -> None:
    assert time_to_peak([]) == 0


def test_time_to_peak_returns_first_peak_index_from_zero_when_multiple_equal_peaks() -> None:
    assert time_to_peak([1, 5, 3, 5, 2]) == 1


def test_time_to_peak_uses_zero_based_index_not_one_based_step() -> None:
    # Peak value 7 is at index 2 (3rd step if one-based)
    assert time_to_peak([1, 4, 7, 2]) == 2


def test_fire_duration_returns_zero_for_empty_series() -> None:
    assert fire_duration([]) == 0


def test_fire_duration_returns_zero_for_all_zero_series() -> None:
    assert fire_duration([0, 0, 0]) == 0


def test_fire_duration_counts_only_positive_after_cleaning_values() -> None:
    # Cleaned series: [0, 2, 0, 0, 1]
    assert fire_duration([-1.2, 2.6, -0.1, 0.0, 1.9]) == 2


def test_area_under_curve_returns_zero_for_empty_series() -> None:
    assert area_under_curve([]) == 0


def test_area_under_curve_returns_zero_for_all_zero_series() -> None:
    assert area_under_curve([0, 0, 0]) == 0


def test_area_under_curve_sums_cleaned_negative_and_float_values() -> None:
    # Cleaned series: [0, 1, 3, 0] => 4
    assert area_under_curve([-2.0, 1.9, 3.1, -4.5]) == 4


def test_burned_area_fraction_returns_zero_when_initial_tree_cells_is_zero() -> None:
    assert burned_area_fraction(0, 10) == 0.0


def test_burned_area_fraction_clamps_to_one_when_final_burnt_exceeds_initial() -> None:
    assert burned_area_fraction(10, 15) == 1.0


def test_burned_area_fraction_cleans_negative_and_float_inputs() -> None:
    # int(12.9)=12, int(5.7)=5
    assert math.isclose(burned_area_fraction(12.9, 5.7), 5 / 12)
    assert burned_area_fraction(-10, 8) == 0.0


def test_calculate_fire_metrics_handles_empty_series_and_missing_burnt() -> None:
    result = calculate_fire_metrics([], initial_tree_cells=20, final_counts={})

    assert result == {
        "baf": 0.0,
        "peak_fire_size": 0,
        "time_to_peak": 0,
        "fire_duration": 0,
        "auc": 0,
    }


def test_calculate_fire_metrics_with_multiple_equal_peaks_and_clamped_baf() -> None:
    result = calculate_fire_metrics(
        burning_cells=[-1, 2.8, 5.9, 5.1, 0],
        initial_tree_cells=4,
        final_counts={"burnt": 9},
    )

    assert result == {
        "baf": 1.0,
        "peak_fire_size": 5,
        "time_to_peak": 2,
        "fire_duration": 3,
        "auc": 12,
    }


def test_time_to_extinguish_returns_first_zero_after_fire_start() -> None:
    assert time_to_extinguish([0, 2, 3, 1, 0, 0]) == 4


def test_time_to_extinguish_returns_zero_when_fire_never_starts_all_zeros() -> None:
    assert time_to_extinguish([0, 0, 0, 0]) == 0


def test_time_to_extinguish_returns_zero_when_fire_never_starts_after_cleaning() -> None:
    assert time_to_extinguish([-1.9, -0.2, 0.0]) == 0


def test_max_spread_rate_uses_max_positive_delta() -> None:
    assert max_spread_rate([0, 1, 4, 2, 7]) == 5


def test_calculate_derived_metrics_includes_critical_and_steps_total() -> None:
    result = calculate_derived_metrics(
        burning_cells=[0, 1, 4, 0],
        step_count=3,
        initial_tree_cells=10,
        critical_baf_threshold=0.5,
        baf=0.75,
    )

    assert result == {
        "time_to_extinguish": 3,
        "max_spread_rate": 3,
        "initial_tree_cells": 10,
        "steps_total": 3,
        "steps_total_or_fire_horizon": 3,
        "peak_fire_fraction": 0.4,
        "auc_normalization_denominator": 30,
        "auc_normalized": 1 / 6,
        "critical": True,
    }


def test_read_metrics_payload_is_backward_compatible_for_legacy_payload() -> None:
    legacy_payload = {
        "initial_tree_cells": 4,
        "burning_cells_t": [0, 1.9, -3, 2],
        "final_counts": {"burnt": 2.8, "empty": 1},
        "metrics": {"baf": 0.5, "auc": 3},
    }

    normalized = read_metrics_payload(legacy_payload)

    assert normalized == {
        "schema_version": METRICS_PAYLOAD_SCHEMA_VERSION,
        "generated_at_utc": "",
        "seed": None,
        "step_count": 0,
        "initial_tree_cells": 4,
        "burning_cells_t": [0, 1, 0, 2],
        "final_counts": {"burnt": 2, "empty": 1},
        "metrics": {"baf": 0.5, "auc": 3},
        "config_snapshot": {},
    }


def test_metrics_to_json_produces_stable_structure_with_new_payload_fields() -> None:
    payload = {
        "metrics": {"auc": 3, "baf": 0.5},
        "final_counts": {"burnt": 2, "empty": 1},
        "burning_cells_t": [0, 1, 2],
        "initial_tree_cells": 4,
        "schema_version": METRICS_PAYLOAD_SCHEMA_VERSION,
        "generated_at_utc": "2026-03-27T12:00:00Z",
        "seed": 42,
        "step_count": 3,
        "config_snapshot": {
            "humidity": 0.25,
            "wind_enabled": True,
        },
    }

    first = metrics_to_json(payload)
    second = metrics_to_json(dict(reversed(list(payload.items()))))

    assert first == second

    decoded = json.loads(first)
    assert list(decoded.keys()) == [
        "burning_cells_t",
        "config_snapshot",
        "final_counts",
        "generated_at_utc",
        "initial_tree_cells",
        "metrics",
        "schema_version",
        "seed",
        "step_count",
    ]
    assert decoded["schema_version"] == METRICS_PAYLOAD_SCHEMA_VERSION
    assert decoded["generated_at_utc"] == "2026-03-27T12:00:00Z"
    assert decoded["seed"] == 42
    assert decoded["step_count"] == 3
    assert decoded["config_snapshot"] == {"humidity": 0.25, "wind_enabled": True}
