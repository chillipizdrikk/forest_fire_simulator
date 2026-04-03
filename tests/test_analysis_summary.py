from __future__ import annotations

import pytest

from src.app.experiments.analysis import analyze_results


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
