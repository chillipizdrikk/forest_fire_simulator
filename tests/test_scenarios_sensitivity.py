from __future__ import annotations

from src.app.experiments.scenarios import load_scenarios


def test_sensitivity_scenarios_file_loads_and_contains_transitional_band() -> None:
    defaults, scenarios = load_scenarios("scenarios_sensitivity.yaml")

    assert defaults["humidity"] == 0.35
    assert len(scenarios) >= 9

    scenario_names = {item.name for item in scenarios}
    assert "anchor_hot_dry" in scenario_names
    assert "anchor_cool_wet" in scenario_names
    assert "anchor_mid_windy_rain" in scenario_names
    assert "transition_mid_humidity" in scenario_names


def test_global_sensitivity_scenarios_file_loads_transitional_grid() -> None:
    defaults, scenarios = load_scenarios("scenarios_global_sensitivity.yaml")

    assert defaults["humidity"] == 0.42
    assert defaults["rain_enabled"] is True
    assert len(scenarios) == 25

    scenario_names = {item.name for item in scenarios}
    assert "global_h28_r15" in scenario_names
    assert "global_h56_r55" in scenario_names

    humidity_values = {item.params["humidity"] for item in scenarios}
    rain_values = {item.params["rain_intensity"] for item in scenarios}
    temperature_values = {item.params["temperature_c"] for item in scenarios}
    wind_values = {item.params["wind_strength"] for item in scenarios}
    conifer_values = {item.params["conifer_ratio"] for item in scenarios}

    assert humidity_values == {0.28, 0.35, 0.42, 0.49, 0.56}
    assert rain_values == {0.15, 0.25, 0.35, 0.45, 0.55}
    assert temperature_values == {20.0, 22.0, 24.0, 26.0, 28.0}
    assert wind_values == {0.35, 0.45, 0.55, 0.65, 0.75}
    assert conifer_values == {0.35, 0.425, 0.5, 0.575, 0.65}

    grid_cells = {(item.params["humidity"], item.params["rain_intensity"]) for item in scenarios}
    assert len(grid_cells) == len(humidity_values) * len(rain_values)