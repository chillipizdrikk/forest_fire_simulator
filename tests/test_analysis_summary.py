from __future__ import annotations

import pytest

from src.app.experiments.analysis import _parse_ofat_scenario_name, analyze_results


def test_analysis_includes_all_uncensored_and_quantiles() -> None:
    rows = [
        {
            "scenario": "s1",
            "baf": 0.1,
            "auc_normalized": 0.2,
            "time_to_extinguish": 10,
            "critical": False,
            "truncated_by_max_steps": False,
            "peak_fire_size": 1,
            "auc": 1,
            "peak_fire_fraction": 0.1,
            "max_spread_rate": 1.0,
            "fire_duration": 1,
        },
        {
            "scenario": "s1",
            "baf": 0.9,
            "auc_normalized": 0.8,
            "time_to_extinguish": 20,
            "critical": True,
            "truncated_by_max_steps": True,
            "peak_fire_size": 2,
            "auc": 2,
            "peak_fire_fraction": 0.2,
            "max_spread_rate": 2.0,
            "fire_duration": 2,
        },
    ]

    summary = analyze_results(rows)
    stats = summary.by_scenario["s1"]

    assert summary.overall["baf_mean_all"] == 0.5
    assert summary.overall["baf_mean_uncensored"] == 0.1
    assert summary.overall["baf_p25"] == pytest.approx(0.3)
    assert summary.overall["baf_p50"] == pytest.approx(0.5)
    assert summary.overall["baf_p75"] == pytest.approx(0.7)
    assert summary.overall["baf_p95"] == pytest.approx(0.86)

    assert stats["censored_share"] == 0.5
    assert stats["baf_mean_all"] == 0.5
    assert stats["baf_mean_uncensored"] == 0.1
    assert stats["baf_p25"] == pytest.approx(0.3)
    assert stats["baf_p50"] == pytest.approx(0.5)
    assert stats["baf_p75"] == pytest.approx(0.7)
    assert stats["baf_p95"] == pytest.approx(0.86)


def test_analysis_includes_family_level_sensitivity_for_ofat_variants() -> None:
    rows = [
        {
            "scenario": "anchor_mid_windy_rain_humidity_025",
            "baf": 0.7,
            "auc_normalized": 0.07,
            "time_to_extinguish": 150,
            "critical": False,
            "truncated_by_max_steps": False,
            "peak_fire_size": 3,
            "auc": 4,
            "peak_fire_fraction": 0.3,
            "max_spread_rate": 2.0,
            "fire_duration": 15,
            "param_humidity": 0.25,
        },
        {
            "scenario": "anchor_mid_windy_rain_humidity_025",
            "baf": 0.65,
            "auc_normalized": 0.06,
            "time_to_extinguish": 145,
            "critical": False,
            "truncated_by_max_steps": False,
            "peak_fire_size": 3,
            "auc": 4,
            "peak_fire_fraction": 0.3,
            "max_spread_rate": 2.0,
            "fire_duration": 14,
            "param_humidity": 0.25,
        },
        {
            "scenario": "anchor_mid_windy_rain_humidity_035",
            "baf": 0.45,
            "auc_normalized": 0.04,
            "time_to_extinguish": 130,
            "critical": False,
            "truncated_by_max_steps": False,
            "peak_fire_size": 2,
            "auc": 3,
            "peak_fire_fraction": 0.2,
            "max_spread_rate": 1.5,
            "fire_duration": 13,
            "param_humidity": 0.35,
        },
        {
            "scenario": "anchor_mid_windy_rain_humidity_035",
            "baf": 0.40,
            "auc_normalized": 0.03,
            "time_to_extinguish": 120,
            "critical": False,
            "truncated_by_max_steps": False,
            "peak_fire_size": 2,
            "auc": 3,
            "peak_fire_fraction": 0.2,
            "max_spread_rate": 1.5,
            "fire_duration": 12,
            "param_humidity": 0.35,
        },
        {
            "scenario": "anchor_mid_windy_rain_humidity_045",
            "baf": 0.2,
            "auc_normalized": 0.015,
            "time_to_extinguish": 110,
            "critical": False,
            "truncated_by_max_steps": False,
            "peak_fire_size": 1,
            "auc": 2,
            "peak_fire_fraction": 0.1,
            "max_spread_rate": 1.0,
            "fire_duration": 10,
            "param_humidity": 0.45,
        },
        {
            "scenario": "anchor_mid_windy_rain_humidity_045",
            "baf": 0.15,
            "auc_normalized": 0.010,
            "time_to_extinguish": 100,
            "critical": False,
            "truncated_by_max_steps": False,
            "peak_fire_size": 1,
            "auc": 2,
            "peak_fire_fraction": 0.1,
            "max_spread_rate": 1.0,
            "fire_duration": 9,
            "param_humidity": 0.45,
        },
    ]

    summary = analyze_results(rows)

    family_diag = summary.correlations_by_family_diagnostics["anchor_mid_windy_rain / humidity"]
    assert family_diag["non_constant_param_count"] == 1
    family_corr = summary.correlations_by_family["anchor_mid_windy_rain / humidity"]
    humidity_baf = [item for item in family_corr if item[0] == "param_humidity" and item[1] == "baf"]
    assert humidity_baf
    assert humidity_baf[0][2] < 0.0
    assert humidity_baf[0][5] < 0.0


def test_analysis_separates_ofat_axes_in_family_level_sensitivity() -> None:
    rows = []

    humidity_values = [0.2, 0.3, 0.4]
    humidity_baf = [0.8, 0.6, 0.4]
    for idx, (param_value, baf_value) in enumerate(zip(humidity_values, humidity_baf)):
        rows.append(
            {
                "scenario": f"transition_low_humidity_humidity_{int(param_value * 100):03d}",
                "baf": baf_value,
                "auc_normalized": baf_value / 10,
                "time_to_extinguish": 100 - idx * 10,
                "critical": False,
                "truncated_by_max_steps": False,
                "peak_fire_size": 1,
                "auc": 1,
                "peak_fire_fraction": 0.1,
                "max_spread_rate": 1.0,
                "fire_duration": 10,
                "param_humidity": param_value,
                "param_wind_strength": 6.0,
                "param_temperature_c": 20.0,
            }
        )
        rows.append(
            {
                "scenario": f"transition_low_humidity_humidity_{int(param_value * 100):03d}",
                "baf": baf_value - 0.05,
                "auc_normalized": (baf_value - 0.05) / 10,
                "time_to_extinguish": 95 - idx * 10,
                "critical": False,
                "truncated_by_max_steps": False,
                "peak_fire_size": 1,
                "auc": 1,
                "peak_fire_fraction": 0.1,
                "max_spread_rate": 1.0,
                "fire_duration": 10,
                "param_humidity": param_value,
                "param_wind_strength": 6.0,
                "param_temperature_c": 20.0,
            }
        )

    wind_values = [4.0, 6.0, 8.0]
    wind_baf = [0.2, 0.5, 0.8]
    for idx, (param_value, baf_value) in enumerate(zip(wind_values, wind_baf)):
        rows.append(
            {
                "scenario": f"transition_low_humidity_wind_strength_{int(param_value):02d}",
                "baf": baf_value,
                "auc_normalized": baf_value / 10,
                "time_to_extinguish": 70 + idx * 10,
                "critical": False,
                "truncated_by_max_steps": False,
                "peak_fire_size": 1,
                "auc": 1,
                "peak_fire_fraction": 0.1,
                "max_spread_rate": 1.0,
                "fire_duration": 10,
                "param_humidity": 0.3,
                "param_wind_strength": param_value,
                "param_temperature_c": 20.0,
            }
        )
        rows.append(
            {
                "scenario": f"transition_low_humidity_wind_strength_{int(param_value):02d}",
                "baf": baf_value + 0.05,
                "auc_normalized": (baf_value + 0.05) / 10,
                "time_to_extinguish": 75 + idx * 10,
                "critical": False,
                "truncated_by_max_steps": False,
                "peak_fire_size": 1,
                "auc": 1,
                "peak_fire_fraction": 0.1,
                "max_spread_rate": 1.0,
                "fire_duration": 10,
                "param_humidity": 0.3,
                "param_wind_strength": param_value,
                "param_temperature_c": 20.0,
            }
        )

    summary = analyze_results(rows)

    humidity_axis_name = "transition_low_humidity / humidity"
    wind_axis_name = "transition_low_humidity / wind_strength"
    assert humidity_axis_name in summary.correlations_by_family
    assert wind_axis_name in summary.correlations_by_family

    humidity_corr = summary.correlations_by_family[humidity_axis_name]
    assert {item[0] for item in humidity_corr} == {"param_humidity"}
    humidity_baf_corr = next(item for item in humidity_corr if item[1] == "baf")
    assert humidity_baf_corr[2] < 0.0

    wind_corr = summary.correlations_by_family[wind_axis_name]
    assert {item[0] for item in wind_corr} == {"param_wind_strength"}
    wind_baf_corr = next(item for item in wind_corr if item[1] == "baf")
    assert wind_baf_corr[2] > 0.0


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        (
            "anchor_mid_windy_rain_humidity_025",
            ("anchor_mid_windy_rain", "humidity", 0.25),
        ),
        (
            "transition_low_humidity_temperature_c_20",
            ("transition_low_humidity", "temperature_c", 20.0),
        ),
        (
            "transition_low_humidity_wind_strength_08",
            ("transition_low_humidity", "wind_strength", 8.0),
        ),
    ],
)
def test_parse_ofat_scenario_name_with_nested_underscores(
    name: str,
    expected: tuple[str, str, float],
) -> None:
    # Convention: only humidity uses percent-encoding (_025 -> 0.25), while
    # wind_strength and temperature_c parse the token as a direct number.
    assert _parse_ofat_scenario_name(name) == expected
