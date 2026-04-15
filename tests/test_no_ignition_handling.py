from __future__ import annotations

import pytest

pytest.importorskip("numpy")

from src.app.core.config import CAConfig
from src.app.core.engine import ForestFireCA
from src.app.experiments.analysis import analyze_results
from src.app.experiments.runner import _first_ignition_point, _simulate_single_run


@pytest.mark.parametrize("tree_cells, expected", [([(0, 0)], (0, 0)), ([(2, 2)], (2, 2)), ([], None)])
def test_first_ignition_point_uses_nearest_tree_or_none(
    tree_cells: list[tuple[int, int]],
    expected: tuple[int, int] | None,
) -> None:
    ca = ForestFireCA(
        CAConfig(
            width=3,
            height=3,
            init_tree_density=0.0,
            lightning_enabled=False,
            rain_enabled=False,
            seed=1,
        )
    )

    for row, col in tree_cells:
        ca.plant_decid(row, col)

    assert _first_ignition_point(ca) == expected


def test_simulate_single_run_returns_no_ignition_flags_when_no_trees() -> None:
    cfg = CAConfig(
        width=5,
        height=5,
        init_tree_density=0.0,
        lightning_enabled=False,
        rain_enabled=False,
        seed=19,
    )

    result = _simulate_single_run(cfg, max_steps=20, critical_baf_threshold=0.8)

    assert result["ignition_succeeded"] is False
    assert result["no_ignition"] is True
    assert result["truncated_by_max_steps"] is False
    assert result["fire_duration"] == 0
    assert result["time_to_extinguish"] == 0


def test_analysis_excludes_no_ignition_from_temporal_kpis() -> None:
    rows = [
        {
            "scenario": "s1",
            "run_id": "r-ignited",
            "baf": 0.6,
            "auc_normalized": 0.4,
            "time_to_extinguish": 20,
            "critical": False,
            "truncated_by_max_steps": False,
            "no_ignition": False,
            "peak_fire_size": 4,
            "auc": 11,
            "peak_fire_fraction": 0.3,
            "max_spread_rate": 1.8,
            "fire_duration": 9,
        },
        {
            "scenario": "s1",
            "run_id": "r-no-ignition",
            "baf": 0.0,
            "auc_normalized": 0.0,
            "time_to_extinguish": 0,
            "critical": False,
            "truncated_by_max_steps": False,
            "no_ignition": True,
            "peak_fire_size": 0,
            "auc": 0,
            "peak_fire_fraction": 0.0,
            "max_spread_rate": 0.0,
            "fire_duration": 0,
        },
    ]

    summary = analyze_results(rows)

    assert summary.overall["runs_total"] == 2
    assert summary.overall["no_ignition_runs_count"] == 1
    assert summary.overall["no_ignition_runs_share"] == 0.5
    assert summary.overall["time_to_extinguish_mean"] == 20.0

    s1_stats = summary.by_scenario["s1"]
    assert s1_stats["no_ignition_count"] == 1
    assert s1_stats["no_ignition_share"] == 0.5
    assert s1_stats["time_to_extinguish_mean"] == 20.0
