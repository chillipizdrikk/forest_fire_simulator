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
