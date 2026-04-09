from __future__ import annotations

from pathlib import Path

from src.app.experiments.analysis import analyze_results, generate_report


def _sample_rows() -> list[dict[str, object]]:
    return [
        {
            "run_id": "a-1",
            "scenario": "a",
            "baf": 0.2,
            "auc_normalized": 0.1,
            "time_to_extinguish": 20,
            "critical": False,
            "truncated_by_max_steps": False,
            "peak_fire_size": 1,
            "auc": 1,
            "peak_fire_fraction": 0.1,
            "max_spread_rate": 1.0,
            "fire_duration": 3,
        },
        {
            "run_id": "a-2",
            "scenario": "a",
            "baf": 0.3,
            "auc_normalized": 0.2,
            "time_to_extinguish": 22,
            "critical": False,
            "truncated_by_max_steps": True,
            "peak_fire_size": 1,
            "auc": 1,
            "peak_fire_fraction": 0.1,
            "max_spread_rate": 1.0,
            "fire_duration": 4,
        },
        {
            "run_id": "b-1",
            "scenario": "b",
            "baf": 0.8,
            "auc_normalized": 0.7,
            "time_to_extinguish": 40,
            "critical": True,
            "truncated_by_max_steps": False,
            "peak_fire_size": 2,
            "auc": 3,
            "peak_fire_fraction": 0.2,
            "max_spread_rate": 2.0,
            "fire_duration": 8,
        },
        {
            "run_id": "b-2",
            "scenario": "b",
            "baf": 0.9,
            "auc_normalized": 0.8,
            "time_to_extinguish": 45,
            "critical": True,
            "truncated_by_max_steps": False,
            "peak_fire_size": 2,
            "auc": 3,
            "peak_fire_fraction": 0.2,
            "max_spread_rate": 2.0,
            "fire_duration": 9,
        },
    ]


def test_generate_report_includes_censoring_audit_section(tmp_path: Path) -> None:
    rows = _sample_rows()
    summary = analyze_results(rows)
    audit_payload = {
        "target_censored_share": 0.02,
        "initial_max_steps": 500,
        "final_max_steps": 800,
        "stop_reason": "max_retries_reached",
        "rounds": [
            {
                "round": 1,
                "from_max_steps": 500,
                "to_max_steps": 800,
                "rerun_scenarios": ["a"],
                "scenario_deltas": [
                    {
                        "scenario": "a",
                        "before_censored_share": 0.50,
                        "after_censored_share": 0.01,
                        "before_baf_mean_all": 0.25,
                        "after_baf_mean_all": 0.20,
                        "before_auc_normalized_mean_all": 0.15,
                        "after_auc_normalized_mean_all": 0.10,
                    }
                ],
            }
        ],
    }

    md_path, html_path, _ = generate_report(rows, summary, tmp_path, censoring_audit=audit_payload)

    md_text = md_path.read_text(encoding="utf-8")
    html_text = html_path.read_text(encoding="utf-8")

    assert "## Censoring max_steps bias audit" in md_text
    assert "Round 1: max_steps 500 -> 800" in md_text
    assert "a: censored_share 0.5000 -> 0.0100" in md_text

    assert "<h2>Censoring max_steps bias audit</h2>" in html_text
    assert "Round 1: max_steps 500 -&gt; 800" in html_text
