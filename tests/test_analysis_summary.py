from __future__ import annotations

from copy import deepcopy

import pytest

from src.app.experiments.analysis import _parse_ofat_scenario_name, analyze_results


def test_analyze_results_does_not_mutate_input_rows() -> None:
    input_rows = [
        {
            "scenario": "s1",
            "run_id": "run-1",
            "baf": 0.2,
            "auc_normalized": 0.3,
            "time_to_extinguish": 12,
            "critical": False,
            "truncated_by_max_steps": False,
            "peak_fire_size": 1,
            "auc": 1,
            "peak_fire_fraction": 0.1,
            "max_spread_rate": 1.0,
            "fire_duration": 8,
        },
        {
            "scenario": "s1",
            "run_id": "run-2",
            "baf": 0.7,
            "auc_normalized": 0.8,
            "time_to_extinguish": 20,
            "critical": True,
            "truncated_by_max_steps": True,
            "peak_fire_size": 2,
            "auc": 2,
            "peak_fire_fraction": 0.2,
            "max_spread_rate": 2.0,
            "fire_duration": 12,
        },
    ]
    rows_before = deepcopy(input_rows)

    analyze_results(input_rows)

    assert input_rows == rows_before
    assert all("time_to_extinguish_global_norm" not in row for row in input_rows)


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


def test_bool_params_are_excluded_from_continuous_correlations() -> None:
    rows = [
        {
            "scenario": "s1",
            "baf": 0.1,
            "peak_fire_size": 1.0,
            "fire_duration": 10.0,
            "max_spread_rate": 0.5,
            "time_to_extinguish": 20.0,
            "auc_normalized": 0.1,
            "auc": 1.0,
            "peak_fire_fraction": 0.1,
            "critical": False,
            "truncated_by_max_steps": False,
            "param_temperature_c": 10.0,
            "param_use_barrier": False,
        },
        {
            "scenario": "s1",
            "baf": 0.2,
            "peak_fire_size": 2.0,
            "fire_duration": 11.0,
            "max_spread_rate": 0.7,
            "time_to_extinguish": 22.0,
            "auc_normalized": 0.2,
            "auc": 2.0,
            "peak_fire_fraction": 0.2,
            "critical": False,
            "truncated_by_max_steps": False,
            "param_temperature_c": 20.0,
            "param_use_barrier": False,
        },
        {
            "scenario": "s2",
            "baf": 0.8,
            "peak_fire_size": 8.0,
            "fire_duration": 20.0,
            "max_spread_rate": 2.5,
            "time_to_extinguish": 40.0,
            "auc_normalized": 0.8,
            "auc": 8.0,
            "peak_fire_fraction": 0.8,
            "critical": True,
            "truncated_by_max_steps": False,
            "param_temperature_c": 30.0,
            "param_use_barrier": True,
        },
        {
            "scenario": "s2",
            "baf": 0.9,
            "peak_fire_size": 9.0,
            "fire_duration": 21.0,
            "max_spread_rate": 2.7,
            "time_to_extinguish": 42.0,
            "auc_normalized": 0.9,
            "auc": 9.0,
            "peak_fire_fraction": 0.9,
            "critical": True,
            "truncated_by_max_steps": False,
            "param_temperature_c": 40.0,
            "param_use_barrier": True,
        },
    ]

    summary = analyze_results(rows, correlation_top_n=20)

    assert summary.continuous_param_correlations
    assert all(pkey != "param_use_barrier" for pkey, *_ in summary.continuous_param_correlations)
    assert any(pkey == "param_use_barrier" for pkey, *_ in summary.binary_param_effects)


def test_pairwise_significance_includes_bh_adjusted_p_values_and_effect_size() -> None:
    rows = []
    scenarios = {
        "s_low": (0.1, 0.1),
        "s_mid": (0.5, 0.5),
        "s_high": (0.9, 0.9),
    }
    for scenario_name, (baf_base, auc_norm_base) in scenarios.items():
        for idx in range(12):
            offset = (idx % 3) * 0.005
            rows.append(
                {
                    "scenario": scenario_name,
                    "run_id": f"{scenario_name}-{idx}",
                    "baf": baf_base + offset,
                    "auc_normalized": auc_norm_base + offset,
                    "time_to_extinguish": 100.0 + idx,
                    "critical": baf_base >= 0.8,
                    "truncated_by_max_steps": False,
                    "peak_fire_size": 1.0,
                    "auc": 1.0,
                    "peak_fire_fraction": 0.1,
                    "max_spread_rate": 0.5,
                    "fire_duration": 10.0,
                    "param_temperature_c": 20.0,
                }
            )

    summary = analyze_results(rows, significance_permutations=500)

    assert "baf" in summary.scenario_pairwise_significance
    assert "auc_normalized" in summary.scenario_pairwise_significance

    baf_tests = summary.scenario_pairwise_significance["baf"]
    assert len(baf_tests) == 3  # 3 choose 2
    assert all(float(item["p_value_adj"]) >= float(item["p_value"]) for item in baf_tests)
    assert all(bool(item["significant_bh_005"]) for item in baf_tests)
    assert all(str(item["effect_label"]) == "large" for item in baf_tests)

    overview = summary.overall["pairwise_significance_tests"]["baf"]
    assert overview["pairs_total"] == 3
    assert overview["significant_bh_005"] == 3


def test_analysis_builds_2d_interaction_surface_for_top_baf_params() -> None:
    rows = [
        {
            "scenario": "s_low_low",
            "baf": 0.2,
            "auc_normalized": 0.2,
            "time_to_extinguish": 100,
            "critical": False,
            "truncated_by_max_steps": False,
            "peak_fire_size": 1,
            "auc": 2,
            "peak_fire_fraction": 0.1,
            "max_spread_rate": 1.0,
            "fire_duration": 10,
            "param_humidity": 0.2,
            "param_wind_strength": 0.2,
        },
        {
            "scenario": "s_high_low",
            "baf": 0.8,
            "auc_normalized": 0.8,
            "time_to_extinguish": 140,
            "critical": True,
            "truncated_by_max_steps": False,
            "peak_fire_size": 2,
            "auc": 4,
            "peak_fire_fraction": 0.2,
            "max_spread_rate": 2.0,
            "fire_duration": 14,
            "param_humidity": 0.8,
            "param_wind_strength": 0.2,
        },
        {
            "scenario": "s_low_high",
            "baf": 0.5,
            "auc_normalized": 0.5,
            "time_to_extinguish": 120,
            "critical": False,
            "truncated_by_max_steps": False,
            "peak_fire_size": 2,
            "auc": 3,
            "peak_fire_fraction": 0.2,
            "max_spread_rate": 1.5,
            "fire_duration": 12,
            "param_humidity": 0.2,
            "param_wind_strength": 0.8,
        },
        {
            "scenario": "s_high_high",
            "baf": 0.9,
            "auc_normalized": 0.9,
            "time_to_extinguish": 160,
            "critical": True,
            "truncated_by_max_steps": False,
            "peak_fire_size": 3,
            "auc": 5,
            "peak_fire_fraction": 0.3,
            "max_spread_rate": 2.5,
            "fire_duration": 16,
            "param_humidity": 0.8,
            "param_wind_strength": 0.8,
        },
    ]

    summary = analyze_results(rows, correlation_top_n=10)

    assert summary.interaction_surfaces
    surface = summary.interaction_surfaces[0]
    assert surface["param_x"] in {"param_humidity", "param_wind_strength"}
    assert surface["param_y"] in {"param_humidity", "param_wind_strength"}
    assert surface["param_x"] != surface["param_y"]
    assert surface["cells_total"] == 4
    assert surface["cells_observed"] == 4
    assert surface["cell_coverage"] == 1.0
    assert "interaction_surface_primary_pair" in summary.overall


def test_analysis_aggregates_and_ranks_new_spatial_metrics() -> None:
    rows = [
        {
            "scenario": "s1",
            "run_id": "s1-1",
            "baf": 0.4,
            "auc_normalized": 0.3,
            "time_to_extinguish": 10,
            "critical": False,
            "truncated_by_max_steps": False,
            "peak_fire_size": 2,
            "auc": 5,
            "peak_fire_fraction": 0.2,
            "max_spread_rate": 1.5,
            "fire_duration": 5,
            "burned_components": 3,
            "largest_cluster_share": 0.5,
            "shape_complexity": 2.2,
        },
        {
            "scenario": "s2",
            "run_id": "s2-1",
            "baf": 0.5,
            "auc_normalized": 0.35,
            "time_to_extinguish": 12,
            "critical": False,
            "truncated_by_max_steps": False,
            "peak_fire_size": 3,
            "auc": 6,
            "peak_fire_fraction": 0.25,
            "max_spread_rate": 1.7,
            "fire_duration": 6,
            "burned_components": 1,
            "largest_cluster_share": 1.0,
            "shape_complexity": 1.6,
        },
    ]

    summary = analyze_results(rows)

    assert summary.overall["burned_components_mean_all"] == pytest.approx(2.0)
    assert summary.overall["largest_cluster_share_mean_all"] == pytest.approx(0.75)
    assert summary.overall["shape_complexity_mean_all"] == pytest.approx(1.9)

    assert summary.by_scenario["s1"]["burned_components_mean"] == pytest.approx(3.0)
    assert summary.by_scenario["s2"]["largest_cluster_share_mean"] == pytest.approx(1.0)

    assert summary.overall["ranking_by_burned_components_mean"][0][0] == "s1"
    assert summary.overall["ranking_by_shape_complexity_mean"][0][0] == "s1"
    assert summary.overall["ranking_by_largest_cluster_share_mean"][0][0] == "s2"
