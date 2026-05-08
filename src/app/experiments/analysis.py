from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
import re
from statistics import mean
from typing import Any

from src.app.experiments.statistics import (
    _benjamini_hochberg,
    _bootstrap_corr_ci,
    _bootstrap_mean_ci,
    _bootstrap_slope_ci,
    _clamp_01,
    _cliffs_delta,
    _cliffs_delta_label,
    _linear_slope,
    _pearson_corr,
    _percentile,
    _pearson_p_value,
    _permutation_test_mean_diff,
)


@dataclass(frozen=True)
class AnalysisSummary:
    overall: dict[str, Any]
    by_scenario: dict[str, dict[str, Any]]
    scenario_ranking: list[tuple[str, float]]
    continuous_param_correlations: list[dict[str, float | str | bool]]
    continuous_param_correlations_controlled: list[dict[str, float | str | bool]]
    binary_param_effects: list[tuple[str, str, float, float, float, float]]
    correlations: list[dict[str, float | str | bool]]
    controlled_correlations: list[dict[str, float | str | bool]]
    correlations_by_scenario: dict[str, list[dict[str, float | str | bool]]]
    correlations_by_scenario_diagnostics: dict[str, dict[str, Any]]
    correlations_by_family: dict[str, list[dict[str, float | str | bool]]]
    correlations_by_family_diagnostics: dict[str, dict[str, Any]]
    scenario_pairwise_significance: dict[str, list[dict[str, Any]]]
    interaction_surfaces: list[dict[str, Any]]


def _format_p_value(value: float) -> str:
    if value < 0.0001:
        return "<1e-4"
    return f"{value:.4f}"


def _correlation_sort_key(
    row: dict[str, float | str | bool], mode: str
) -> tuple[float, ...]:
    r_abs = abs(float(row["r"]))
    q_value = float(row["q_value"])
    p_value = float(row["p_value"])
    if mode == "q_then_abs_r":
        return (q_value, p_value, -r_abs)
    if mode == "p_then_abs_r":
        return (p_value, q_value, -r_abs)
    return (-r_abs, q_value, p_value)


def _sort_correlations(
    rows: list[dict[str, float | str | bool]],
    *,
    ranking_mode: str,
    top_n: int,
) -> list[dict[str, float | str | bool]]:
    ordered = sorted(rows, key=lambda row: _correlation_sort_key(row, ranking_mode))
    return ordered[:top_n]


def _attach_bh_q_values(
    rows: list[dict[str, float | str | bool]],
) -> list[dict[str, float | str | bool]]:
    if not rows:
        return []
    q_values = _benjamini_hochberg([float(row["p_value"]) for row in rows])
    enriched: list[dict[str, float | str | bool]] = []
    for row, q_value in zip(rows, q_values):
        next_row = dict(row)
        next_row["q_value"] = float(q_value)
        next_row["q_le_005"] = bool(q_value <= 0.05)
        enriched.append(next_row)
    return enriched


def _normalize_01(values: list[float]) -> list[float]:
    if not values:
        return []
    lo = min(values)
    hi = max(values)
    if hi == lo:
        return [0.0 for _ in values]
    span = hi - lo
    return [_clamp_01((value - lo) / span) for value in values]


def _uncensored_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [row for row in rows if not bool(row.get("truncated_by_max_steps", False))]


def _ignited_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [row for row in rows if not bool(row.get("no_ignition", False))]


def _mean_metric(rows: list[dict[str, Any]], key: str) -> float:
    values = [float(row.get(key, 0.0)) for row in rows]
    return float(mean(values)) if values else 0.0


def _kaplan_meier_tte_metrics(
    rows: list[dict[str, Any]],
    *,
    horizons: tuple[float, ...] = (200.0,),
) -> dict[str, Any]:
    observations = [
        (
            float(row.get("time_to_extinguish", 0.0)),
            not bool(row.get("truncated_by_max_steps", False)),
        )
        for row in rows
        if not bool(row.get("no_ignition", False))
    ]
    if not observations:
        return {
            "tte_survival_sample_size": 0,
            "time_to_extinguish_survival_median": 0.0,
            "time_to_extinguish_survival_median_reached": False,
            "time_to_extinguish_survival_median_lower_bound": 0.0,
            "time_to_extinguish_survival_probabilities": {
                str(int(h)): 0.0 for h in horizons
            },
        }

    by_time: dict[float, dict[str, int]] = {}
    for time_value, is_event in observations:
        bucket = by_time.setdefault(time_value, {"events": 0, "censored": 0})
        if is_event:
            bucket["events"] += 1
        else:
            bucket["censored"] += 1

    n_at_risk = len(observations)
    survival = 1.0
    survival_after_event_time: dict[float, float] = {}
    median_time: float | None = None
    for time_value in sorted(by_time.keys()):
        events = by_time[time_value]["events"]
        censored = by_time[time_value]["censored"]
        if n_at_risk > 0 and events > 0:
            survival *= max(0.0, 1.0 - float(events / n_at_risk))
            survival_after_event_time[time_value] = survival
            if median_time is None and survival <= 0.5:
                median_time = time_value
        n_at_risk -= events + censored

    max_observed_time = max(time_value for time_value, _ in observations)
    survival_probabilities: dict[str, float] = {}
    event_times = sorted(survival_after_event_time.keys())
    for horizon in horizons:
        horizon_survival = 1.0
        for event_time in event_times:
            if event_time > horizon:
                break
            horizon_survival = survival_after_event_time[event_time]
        survival_probabilities[str(int(horizon))] = float(_clamp_01(horizon_survival))

    return {
        "tte_survival_sample_size": len(observations),
        "time_to_extinguish_survival_median": float(
            median_time if median_time is not None else max_observed_time
        ),
        "time_to_extinguish_survival_median_reached": bool(median_time is not None),
        "time_to_extinguish_survival_median_lower_bound": float(max_observed_time),
        "time_to_extinguish_survival_probabilities": survival_probabilities,
    }


def _critical_share(rows: list[dict[str, Any]]) -> float:
    return (
        float(sum(bool(row.get("critical", False)) for row in rows) / len(rows))
        if rows
        else 0.0
    )


def _pairwise_significance_by_metric(
    by_scenario: dict[str, list[dict[str, Any]]],
    *,
    metric_key: str,
    n_resamples: int = 2000,
    seed: int = 42,
) -> list[dict[str, Any]]:
    scenario_names = sorted(by_scenario.keys())
    rows: list[dict[str, Any]] = []
    for idx, (name_a, name_b) in enumerate(combinations(scenario_names, 2)):
        values_a = [float(item.get(metric_key, 0.0)) for item in by_scenario[name_a]]
        values_b = [float(item.get(metric_key, 0.0)) for item in by_scenario[name_b]]
        if not values_a or not values_b:
            continue
        mean_a = float(mean(values_a))
        mean_b = float(mean(values_b))
        p_value = _permutation_test_mean_diff(
            values_a, values_b, n_resamples=n_resamples, seed=seed + idx
        )
        delta = _cliffs_delta(values_a, values_b)
        rows.append(
            {
                "scenario_a": name_a,
                "scenario_b": name_b,
                "metric": metric_key,
                "n_a": len(values_a),
                "n_b": len(values_b),
                "mean_a": mean_a,
                "mean_b": mean_b,
                "mean_diff": float(mean_a - mean_b),
                "p_value": p_value,
                "effect_cliffs_delta": float(delta),
                "effect_label": _cliffs_delta_label(delta),
            }
        )
    adjusted = _benjamini_hochberg([float(row["p_value"]) for row in rows])
    for row, p_adj in zip(rows, adjusted):
        row["p_value_adj"] = float(p_adj)
        row["significant_bh_005"] = bool(p_adj <= 0.05)
    rows.sort(
        key=lambda row: (
            float(row["p_value_adj"]),
            -abs(float(row["effect_cliffs_delta"])),
        )
    )
    return rows


def _select_top_baf_params(
    continuous_correlations: list[dict[str, float | str | bool]],
    *,
    top_k: int = 2,
) -> list[str]:
    selected: list[str] = []
    ranked = sorted(
        continuous_correlations,
        key=lambda item: _correlation_sort_key(item, "q_then_abs_r"),
    )
    for item in ranked:
        pkey = str(item["param_key"])
        mkey = str(item["metric_key"])
        if mkey != "baf":
            continue
        if pkey in selected:
            continue
        selected.append(pkey)
        if len(selected) >= top_k:
            break
    return selected


def _build_interaction_surface(
    rows: list[dict[str, Any]],
    *,
    param_x: str,
    param_y: str,
    critical_baf_threshold: float,
) -> dict[str, Any] | None:
    filtered = [
        row
        for row in rows
        if isinstance(row.get(param_x), (int, float))
        and not isinstance(row.get(param_x), bool)
        and isinstance(row.get(param_y), (int, float))
        and not isinstance(row.get(param_y), bool)
    ]
    if not filtered:
        return None

    x_values = sorted({float(row.get(param_x, 0.0)) for row in filtered})
    y_values = sorted({float(row.get(param_y, 0.0)) for row in filtered})
    if len(x_values) < 2 or len(y_values) < 2:
        return None

    grouped: dict[tuple[float, float], list[dict[str, Any]]] = {}
    for row in filtered:
        x = float(row.get(param_x, 0.0))
        y = float(row.get(param_y, 0.0))
        grouped.setdefault((x, y), []).append(row)

    mean_baf_grid: list[list[float | None]] = []
    catastrophic_grid: list[list[float | None]] = []
    covered_cells = 0
    for y in y_values:
        baf_row: list[float | None] = []
        crit_row: list[float | None] = []
        for x in x_values:
            cell_rows = grouped.get((x, y), [])
            if not cell_rows:
                baf_row.append(None)
                crit_row.append(None)
                continue
            covered_cells += 1
            baf_values = [float(item.get("baf", 0.0)) for item in cell_rows]
            baf_mean = float(mean(baf_values)) if baf_values else 0.0
            catastrophic_probability = (
                float(
                    sum(value >= critical_baf_threshold for value in baf_values)
                    / len(baf_values)
                )
                if baf_values
                else 0.0
            )
            baf_row.append(baf_mean)
            crit_row.append(catastrophic_probability)
        mean_baf_grid.append(baf_row)
        catastrophic_grid.append(crit_row)

    if covered_cells < 4:
        return None

    x_lo, x_hi = x_values[0], x_values[-1]
    y_lo, y_hi = y_values[0], y_values[-1]

    corners = {
        "f00": grouped.get((x_lo, y_lo), []),
        "f10": grouped.get((x_hi, y_lo), []),
        "f01": grouped.get((x_lo, y_hi), []),
        "f11": grouped.get((x_hi, y_hi), []),
    }
    interaction_score_baf = 0.0
    if all(corners.values()):
        corner_means = {
            key: float(mean(float(item.get("baf", 0.0)) for item in values))
            for key, values in corners.items()
        }
        interaction_score_baf = abs(
            (corner_means["f11"] - corner_means["f10"])
            - (corner_means["f01"] - corner_means["f00"])
        )

    coverage = float(covered_cells / (len(x_values) * len(y_values)))
    return {
        "param_x": param_x,
        "param_y": param_y,
        "x_values": x_values,
        "y_values": y_values,
        "mean_baf_grid": mean_baf_grid,
        "catastrophic_grid": catastrophic_grid,
        "cell_coverage": coverage,
        "cells_total": len(x_values) * len(y_values),
        "cells_observed": covered_cells,
        "interaction_score_baf": float(interaction_score_baf),
    }


def analyze_results(
    rows: list[dict[str, Any]],
    *,
    ranking_metric: str = "auc_normalized_mean",
    critical_baf_threshold: float = 0.8,
    correlation_top_n: int = 10,
    scenario_correlation_min_runs: int = 5,
    significance_permutations: int = 2000,
) -> AnalysisSummary:
    tte_survival_horizons = (200.0,)
    working_rows = [dict(row) for row in rows]
    ignited_rows = _ignited_rows(working_rows)

    uncensored_all = _uncensored_rows(working_rows)
    uncensored_ignited = _uncensored_rows(ignited_rows)
    global_tte_rows = uncensored_ignited if uncensored_ignited else ignited_rows
    global_tte_values = [
        float(row.get("time_to_extinguish", 0.0)) for row in global_tte_rows
    ]
    global_tte_norm = _normalize_01(global_tte_values)
    global_tte_norm_by_run_id = {
        str(row.get("run_id", f"row_{idx}")): norm
        for idx, (row, norm) in enumerate(zip(global_tte_rows, global_tte_norm))
    }

    by_scenario: dict[str, list[dict[str, Any]]] = {}
    for row in working_rows:
        by_scenario.setdefault(str(row["scenario"]), []).append(row)

    baf_values = [float(row.get("baf", 0.0)) for row in working_rows]
    censored_runs_count = int(
        sum(bool(row.get("truncated_by_max_steps", False)) for row in working_rows)
    )
    censored_runs_share = (
        float(censored_runs_count / len(working_rows)) if working_rows else 0.0
    )
    no_ignition_runs_count = int(
        sum(bool(row.get("no_ignition", False)) for row in working_rows)
    )
    no_ignition_runs_share = (
        float(no_ignition_runs_count / len(working_rows)) if working_rows else 0.0
    )
    tte_min = min(global_tte_values) if global_tte_values else 0.0
    tte_max = max(global_tte_values) if global_tte_values else 0.0
    tte_span = tte_max - tte_min
    for row in working_rows:
        run_id = str(row.get("run_id", ""))
        if run_id in global_tte_norm_by_run_id:
            row["time_to_extinguish_global_norm"] = float(
                global_tte_norm_by_run_id[run_id]
            )
            continue
        if bool(row.get("no_ignition", False)):
            row["time_to_extinguish_global_norm"] = 0.0
            continue
        if tte_span == 0.0:
            row["time_to_extinguish_global_norm"] = 0.0
            continue
        tte_value = float(row.get("time_to_extinguish", 0.0))
        row["time_to_extinguish_global_norm"] = _clamp_01(
            (tte_value - tte_min) / tte_span
        )
    overall = {
        "runs_total": len(working_rows),
        "baf_mean": float(mean(baf_values)) if baf_values else 0.0,
        "baf_mean_all": float(mean(baf_values)) if baf_values else 0.0,
        "baf_mean_uncensored": _mean_metric(uncensored_all, "baf"),
        "auc_normalized_mean": _mean_metric(working_rows, "auc_normalized"),
        "auc_normalized_mean_all": _mean_metric(working_rows, "auc_normalized"),
        "auc_normalized_mean_uncensored": _mean_metric(
            uncensored_all, "auc_normalized"
        ),
        "burned_components_mean": _mean_metric(working_rows, "burned_components"),
        "burned_components_mean_all": _mean_metric(working_rows, "burned_components"),
        "burned_components_mean_uncensored": _mean_metric(
            uncensored_all, "burned_components"
        ),
        "largest_cluster_share_mean": _mean_metric(
            working_rows, "largest_cluster_share"
        ),
        "largest_cluster_share_mean_all": _mean_metric(
            working_rows, "largest_cluster_share"
        ),
        "largest_cluster_share_mean_uncensored": _mean_metric(
            uncensored_all, "largest_cluster_share"
        ),
        "shape_complexity_mean": _mean_metric(working_rows, "shape_complexity"),
        "shape_complexity_mean_all": _mean_metric(working_rows, "shape_complexity"),
        "shape_complexity_mean_uncensored": _mean_metric(
            uncensored_all, "shape_complexity"
        ),
        "time_to_extinguish_mean": _mean_metric(ignited_rows, "time_to_extinguish"),
        "time_to_extinguish_mean_all": _mean_metric(working_rows, "time_to_extinguish"),
        "time_to_extinguish_mean_uncensored": _mean_metric(
            uncensored_ignited, "time_to_extinguish"
        ),
        "critical_mean_all": _critical_share(working_rows),
        "critical_mean_uncensored": _critical_share(uncensored_all),
        "critical_share": _critical_share(working_rows),
        "critical_share_uncensored": _critical_share(uncensored_all),
        "baf_p95": _percentile(baf_values, 0.95),
        "baf_p75": _percentile(baf_values, 0.75),
        "baf_p50": _percentile(baf_values, 0.50),
        "baf_p25": _percentile(baf_values, 0.25),
        "baf_p99": _percentile(baf_values, 0.99),
        "catastrophic_probability": (
            float(
                sum(v >= critical_baf_threshold for v in baf_values) / len(baf_values)
            )
            if baf_values
            else 0.0
        ),
        "critical_baf_threshold": critical_baf_threshold,
        "scenario_ranking_metric": ranking_metric,
        "censored_runs_count": censored_runs_count,
        "censored_runs_share": censored_runs_share,
        "no_ignition_runs_count": no_ignition_runs_count,
        "no_ignition_runs_share": no_ignition_runs_share,
        "time_to_extinguish_norm_scope": (
            "uncensored_ignited_only" if uncensored_ignited else "ignited_runs"
        ),
        "time_to_extinguish_global_min": tte_min,
        "time_to_extinguish_global_max": tte_max,
    }
    overall.update(
        _kaplan_meier_tte_metrics(working_rows, horizons=tte_survival_horizons)
    )

    scenario_stats: dict[str, dict[str, Any]] = {}
    for scenario_name, items in by_scenario.items():
        local_baf = [float(item.get("baf", 0.0)) for item in items]
        local_peak = [float(item.get("peak_fire_size", 0.0)) for item in items]
        local_auc = [float(item.get("auc", 0.0)) for item in items]
        local_peak_norm = [float(item.get("peak_fire_fraction", 0.0)) for item in items]
        local_auc_norm = [float(item.get("auc_normalized", 0.0)) for item in items]
        local_components = [float(item.get("burned_components", 0.0)) for item in items]
        local_largest_cluster_share = [
            float(item.get("largest_cluster_share", 0.0)) for item in items
        ]
        local_shape_complexity = [
            float(item.get("shape_complexity", 0.0)) for item in items
        ]
        uncensored_items = _uncensored_rows(items)
        ignited_items = _ignited_rows(items)
        uncensored_ignited_items = _uncensored_rows(ignited_items)
        run_tte_global_norm = [
            float(item.get("time_to_extinguish_global_norm", 0.0)) for item in items
        ]
        run_risk_scores = [
            float(
                mean(
                    [
                        _clamp_01(baf),
                        _clamp_01(auc_norm),
                        _clamp_01(peak_norm),
                        _clamp_01(tte_global_norm),
                    ]
                )
            )
            for item, baf, auc_norm, peak_norm, tte_global_norm in zip(
                items, local_baf, local_auc_norm, local_peak_norm, run_tte_global_norm
            )
            if not bool(item.get("no_ignition", False))
        ]
        run_risk_scores_uncensored = [
            score
            for item, score in zip(ignited_items, run_risk_scores)
            if not bool(item.get("truncated_by_max_steps", False))
        ]
        baf_mean_ci_low, baf_mean_ci_high = _bootstrap_mean_ci(
            local_baf, confidence=0.95
        )
        risk_mean_ci_low, risk_mean_ci_high = _bootstrap_mean_ci(
            run_risk_scores, confidence=0.95
        )
        scenario_stats[scenario_name] = {
            "runs": len(items),
            "baf_mean": float(mean(local_baf)) if local_baf else 0.0,
            "baf_mean_all": float(mean(local_baf)) if local_baf else 0.0,
            "baf_mean_uncensored": _mean_metric(uncensored_items, "baf"),
            "baf_mean_ci_low": baf_mean_ci_low,
            "baf_mean_ci_high": baf_mean_ci_high,
            "baf_p95": _percentile(local_baf, 0.95),
            "baf_p75": _percentile(local_baf, 0.75),
            "baf_p50": _percentile(local_baf, 0.50),
            "baf_p25": _percentile(local_baf, 0.25),
            "peak_fire_size_mean": float(mean(local_peak)) if local_peak else 0.0,
            "auc_mean": float(mean(local_auc)) if local_auc else 0.0,
            "peak_fire_fraction_mean": (
                float(mean(local_peak_norm)) if local_peak_norm else 0.0
            ),
            "auc_normalized_mean": (
                float(mean(local_auc_norm)) if local_auc_norm else 0.0
            ),
            "auc_normalized_mean_all": (
                float(mean(local_auc_norm)) if local_auc_norm else 0.0
            ),
            "auc_normalized_mean_uncensored": _mean_metric(
                uncensored_items, "auc_normalized"
            ),
            "burned_components_mean": (
                float(mean(local_components)) if local_components else 0.0
            ),
            "burned_components_mean_uncensored": _mean_metric(
                uncensored_items, "burned_components"
            ),
            "largest_cluster_share_mean": (
                float(mean(local_largest_cluster_share))
                if local_largest_cluster_share
                else 0.0
            ),
            "largest_cluster_share_mean_uncensored": _mean_metric(
                uncensored_items, "largest_cluster_share"
            ),
            "shape_complexity_mean": (
                float(mean(local_shape_complexity)) if local_shape_complexity else 0.0
            ),
            "shape_complexity_mean_uncensored": _mean_metric(
                uncensored_items, "shape_complexity"
            ),
            "critical_count": int(
                sum(bool(item.get("critical", False)) for item in items)
            ),
            "critical_mean_all": _critical_share(items),
            "critical_mean_uncensored": _critical_share(uncensored_items),
            "critical_share": _critical_share(items),
            "critical_share_uncensored": _critical_share(uncensored_items),
            "censored_share": float(
                sum(bool(item.get("truncated_by_max_steps", False)) for item in items)
                / len(items)
            ),
            "max_spread_rate_mean": float(
                mean(float(item.get("max_spread_rate", 0.0)) for item in items)
            ),
            "time_to_extinguish_mean": _mean_metric(
                ignited_items, "time_to_extinguish"
            ),
            "time_to_extinguish_mean_all": float(
                mean(float(item.get("time_to_extinguish", 0.0)) for item in items)
            ),
            "time_to_extinguish_mean_uncensored": _mean_metric(
                uncensored_ignited_items, "time_to_extinguish"
            ),
            "risk_score_mean": float(mean(run_risk_scores)) if run_risk_scores else 0.0,
            "risk_score_mean_uncensored": (
                float(mean(run_risk_scores_uncensored))
                if run_risk_scores_uncensored
                else 0.0
            ),
            "risk_score_mean_ci_low": risk_mean_ci_low,
            "risk_score_mean_ci_high": risk_mean_ci_high,
            "no_ignition_count": int(
                sum(bool(item.get("no_ignition", False)) for item in items)
            ),
            "no_ignition_share": float(
                sum(bool(item.get("no_ignition", False)) for item in items) / len(items)
            ),
        }
        scenario_stats[scenario_name].update(
            _kaplan_meier_tte_metrics(items, horizons=tte_survival_horizons)
        )

    ranking = sorted(
        (
            (name, float(stats.get(ranking_metric, 0.0)))
            for name, stats in scenario_stats.items()
        ),
        key=lambda x: x[1],
        reverse=True,
    )
    overall["ranking_by_burned_components_mean"] = sorted(
        (
            (name, float(stats.get("burned_components_mean", 0.0)))
            for name, stats in scenario_stats.items()
        ),
        key=lambda item: item[1],
        reverse=True,
    )
    overall["ranking_by_shape_complexity_mean"] = sorted(
        (
            (name, float(stats.get("shape_complexity_mean", 0.0)))
            for name, stats in scenario_stats.items()
        ),
        key=lambda item: item[1],
        reverse=True,
    )
    overall["ranking_by_largest_cluster_share_mean"] = sorted(
        (
            (name, float(stats.get("largest_cluster_share_mean", 0.0)))
            for name, stats in scenario_stats.items()
        ),
        key=lambda item: item[1],
        reverse=True,
    )

    pairwise_significance = {
        "baf": _pairwise_significance_by_metric(
            by_scenario,
            metric_key="baf",
            n_resamples=significance_permutations,
            seed=91,
        ),
        "auc_normalized": _pairwise_significance_by_metric(
            by_scenario,
            metric_key="auc_normalized",
            n_resamples=significance_permutations,
            seed=191,
        ),
    }
    overall["pairwise_significance_tests"] = {
        metric: {
            "pairs_total": len(rows_for_metric),
            "significant_bh_005": int(
                sum(
                    bool(item.get("significant_bh_005", False))
                    for item in rows_for_metric
                )
            ),
        }
        for metric, rows_for_metric in pairwise_significance.items()
    }
    overall["pairwise_significance_permutations"] = int(
        max(1, significance_permutations)
    )

    continuous_param_keys = sorted(
        {
            key
            for row in working_rows
            for key in row
            if key.startswith("param_")
            and isinstance(row[key], (int, float))
            and not isinstance(row[key], bool)
        }
    )
    binary_param_keys = sorted(
        {
            key
            for row in working_rows
            for key in row
            if key.startswith("param_") and isinstance(row[key], bool)
        }
    )
    metric_keys = [
        "baf",
        "peak_fire_size",
        "fire_duration",
        "max_spread_rate",
        "time_to_extinguish",
        "burned_components",
        "largest_cluster_share",
        "shape_complexity",
    ]
    continuous_param_correlations = _collect_top_correlations(
        working_rows,
        continuous_param_keys,
        metric_keys,
        top_n=correlation_top_n,
    )
    continuous_param_correlations_controlled = _collect_controlled_top_correlations(
        working_rows,
        by_scenario,
        continuous_param_keys,
        metric_keys,
        top_n=correlation_top_n,
    )
    binary_param_effects = _collect_binary_param_effects(
        working_rows,
        binary_param_keys,
        metric_keys,
        top_n=correlation_top_n,
    )
    interaction_surfaces: list[dict[str, Any]] = []
    top_baf_params = _select_top_baf_params(continuous_param_correlations, top_k=2)
    if len(top_baf_params) == 2:
        surface = _build_interaction_surface(
            working_rows,
            param_x=top_baf_params[0],
            param_y=top_baf_params[1],
            critical_baf_threshold=critical_baf_threshold,
        )
        if surface is not None:
            interaction_surfaces.append(surface)
    overall["interaction_surfaces_count"] = len(interaction_surfaces)
    if interaction_surfaces:
        primary_surface = interaction_surfaces[0]
        overall["interaction_surface_primary_pair"] = (
            f"{primary_surface['param_x']} x {primary_surface['param_y']}"
        )
        overall["interaction_surface_primary_coverage"] = float(
            primary_surface["cell_coverage"]
        )
        overall["interaction_surface_primary_score_baf"] = float(
            primary_surface["interaction_score_baf"]
        )

    correlations_by_scenario: dict[str, list[dict[str, float | str | bool]]] = {}
    correlations_by_scenario_diagnostics: dict[str, dict[str, Any]] = {}
    for scenario_name, scenario_rows in by_scenario.items():
        non_constant_params = _count_non_constant_params(
            scenario_rows, continuous_param_keys
        )
        constant_params = [
            pkey for pkey in continuous_param_keys if pkey not in non_constant_params
        ]
        correlations_by_scenario_diagnostics[scenario_name] = {
            "runs": len(scenario_rows),
            "min_runs_required": scenario_correlation_min_runs,
            "non_constant_param_count": len(non_constant_params),
            "total_param_count": len(continuous_param_keys),
            "constant_param_keys": constant_params,
        }
        if len(scenario_rows) < scenario_correlation_min_runs:
            continue
        correlations_by_scenario[scenario_name] = _collect_top_correlations(
            scenario_rows,
            continuous_param_keys,
            metric_keys,
            top_n=correlation_top_n,
        )

    family_rows: dict[tuple[str, str], list[dict[str, Any]]] = {}
    non_ofat_family_rows: dict[str, list[dict[str, Any]]] = {}
    for row in working_rows:
        scenario_name = str(row.get("scenario", ""))
        parsed = _parse_ofat_scenario_name(scenario_name)
        if parsed:
            base_name, varied_param_name, _ = parsed
            family_rows.setdefault((base_name, varied_param_name), []).append(row)
        else:
            non_ofat_family_rows.setdefault(scenario_name, []).append(row)

    family_metric_keys = ["baf", "auc_normalized", "time_to_extinguish"]
    correlations_by_family: dict[str, list[dict[str, float | str | bool]]] = {}
    correlations_by_family_diagnostics: dict[str, dict[str, Any]] = {}
    for (base_name, varied_param_name), items in family_rows.items():
        family_name = f"{base_name} / {varied_param_name}"
        varied_param_key = f"param_{varied_param_name}"
        non_constant_params = _count_non_constant_params(items, [varied_param_key])
        constant_params = [varied_param_key] if not non_constant_params else []
        correlations_by_family_diagnostics[family_name] = {
            "runs": len(items),
            "min_runs_required": scenario_correlation_min_runs,
            "non_constant_param_count": len(non_constant_params),
            "total_param_count": 1,
            "constant_param_keys": constant_params,
            "ofat_base_name": base_name,
            "ofat_varied_param_name": varied_param_name,
        }
        if len(items) < scenario_correlation_min_runs:
            continue

        family_corrs: list[dict[str, float | str | bool]] = []
        family_test_rows: list[tuple[int, float]] = []
        for pkey in non_constant_params:
            px = [float(row.get(pkey, 0.0)) for row in items]
            for mkey in family_metric_keys:
                my = [float(row.get(mkey, 0.0)) for row in items]
                corr = _pearson_corr(px, my)
                slope = _linear_slope(px, my)
                if corr is None or slope is None:
                    continue
                corr_ci_low, corr_ci_high = _bootstrap_corr_ci(
                    px, my, confidence=0.95, n_resamples=1000
                )
                slope_ci_low, slope_ci_high = _bootstrap_slope_ci(
                    px, my, confidence=0.95, n_resamples=1000
                )
                p_value = _pearson_p_value(px, my, corr)
                row_idx = len(family_corrs)
                family_corrs.append(
                    {
                        "param_key": pkey,
                        "metric_key": mkey,
                        "r": float(corr),
                        "r_ci_low": float(corr_ci_low),
                        "r_ci_high": float(corr_ci_high),
                        "p_value": float(p_value),
                        "slope": float(slope),
                        "slope_ci_low": float(slope_ci_low),
                        "slope_ci_high": float(slope_ci_high),
                    }
                )
                family_test_rows.append((row_idx, p_value))
        if family_corrs:
            q_values = _benjamini_hochberg([item[1] for item in family_test_rows])
            for (row_idx, _), q_value in zip(family_test_rows, q_values):
                family_corrs[row_idx]["q_value"] = float(q_value)
                family_corrs[row_idx]["q_le_005"] = bool(q_value <= 0.05)
        family_corrs = _sort_correlations(
            family_corrs, ranking_mode="q_then_abs_r", top_n=correlation_top_n
        )
        if family_corrs:
            correlations_by_family[family_name] = family_corrs

    for scenario_name, items in non_ofat_family_rows.items():
        correlations_by_family_diagnostics[scenario_name] = {
            "runs": len(items),
            "min_runs_required": scenario_correlation_min_runs,
            "non_constant_param_count": 0,
            "total_param_count": 0,
            "constant_param_keys": [],
            "ofat_excluded": True,
        }

    return AnalysisSummary(
        overall=overall,
        by_scenario=scenario_stats,
        scenario_ranking=ranking,
        continuous_param_correlations=continuous_param_correlations,
        continuous_param_correlations_controlled=continuous_param_correlations_controlled,
        binary_param_effects=binary_param_effects,
        correlations=continuous_param_correlations,
        controlled_correlations=continuous_param_correlations_controlled,
        correlations_by_scenario=correlations_by_scenario,
        correlations_by_scenario_diagnostics=correlations_by_scenario_diagnostics,
        correlations_by_family=correlations_by_family,
        correlations_by_family_diagnostics=correlations_by_family_diagnostics,
        scenario_pairwise_significance=pairwise_significance,
        interaction_surfaces=interaction_surfaces,
    )


def _collect_top_correlations(
    rows: list[dict[str, Any]],
    numeric_param_keys: list[str],
    metric_keys: list[str],
    *,
    top_n: int,
) -> list[dict[str, float | str | bool]]:
    correlations: list[dict[str, float | str | bool]] = []
    for pkey in numeric_param_keys:
        px = [float(row.get(pkey, 0.0)) for row in rows]
        if not px:
            continue
        for mkey in metric_keys:
            my = [float(row.get(mkey, 0.0)) for row in rows]
            corr = _pearson_corr(px, my)
            if corr is None:
                continue
            ci_low, ci_high = _bootstrap_corr_ci(
                px, my, confidence=0.95, n_resamples=1000
            )
            p_value = _pearson_p_value(px, my, corr)
            correlations.append(
                {
                    "param_key": pkey,
                    "metric_key": mkey,
                    "r": float(corr),
                    "r_ci_low": float(ci_low),
                    "r_ci_high": float(ci_high),
                    "p_value": float(p_value),
                }
            )
    correlations = _attach_bh_q_values(correlations)
    return _sort_correlations(correlations, ranking_mode="q_then_abs_r", top_n=top_n)


def _count_non_constant_params(
    rows: list[dict[str, Any]], numeric_param_keys: list[str]
) -> list[str]:
    non_constant: list[str] = []
    for pkey in numeric_param_keys:
        values = [float(row.get(pkey, 0.0)) for row in rows]
        if not values:
            continue
        vmin = min(values)
        vmax = max(values)
        if vmax > vmin:
            non_constant.append(pkey)
    return non_constant


def _collect_controlled_top_correlations(
    rows: list[dict[str, Any]],
    by_scenario: dict[str, list[dict[str, Any]]],
    numeric_param_keys: list[str],
    metric_keys: list[str],
    *,
    top_n: int,
) -> list[dict[str, float | str | bool]]:
    scenario_means: dict[str, dict[str, float]] = {}
    keys_for_demean = numeric_param_keys + metric_keys
    for scenario_name, scenario_rows in by_scenario.items():
        scenario_means[scenario_name] = {}
        for key in keys_for_demean:
            values = [float(row.get(key, 0.0)) for row in scenario_rows]
            scenario_means[scenario_name][key] = float(mean(values)) if values else 0.0

    correlations: list[dict[str, float | str | bool]] = []
    for pkey in numeric_param_keys:
        px = [
            float(row.get(pkey, 0.0)) - scenario_means[str(row["scenario"])][pkey]
            for row in rows
            if str(row["scenario"]) in scenario_means
        ]
        if not px:
            continue
        for mkey in metric_keys:
            my = [
                float(row.get(mkey, 0.0)) - scenario_means[str(row["scenario"])][mkey]
                for row in rows
                if str(row["scenario"]) in scenario_means
            ]
            corr = _pearson_corr(px, my)
            if corr is None:
                continue
            ci_low, ci_high = _bootstrap_corr_ci(
                px, my, confidence=0.95, n_resamples=1000
            )
            p_value = _pearson_p_value(px, my, corr)
            correlations.append(
                {
                    "param_key": pkey,
                    "metric_key": mkey,
                    "r": float(corr),
                    "r_ci_low": float(ci_low),
                    "r_ci_high": float(ci_high),
                    "p_value": float(p_value),
                }
            )

    correlations = _attach_bh_q_values(correlations)
    return _sort_correlations(correlations, ranking_mode="q_then_abs_r", top_n=top_n)


def _collect_binary_param_effects(
    rows: list[dict[str, Any]],
    binary_param_keys: list[str],
    metric_keys: list[str],
    *,
    top_n: int,
) -> list[tuple[str, str, float, float, float, float]]:
    effects: list[tuple[str, str, float, float, float, float]] = []
    for pkey in binary_param_keys:
        bool_rows = [row for row in rows if isinstance(row.get(pkey), bool)]
        if not bool_rows:
            continue
        px = [1.0 if bool(row.get(pkey, False)) else 0.0 for row in bool_rows]
        if len(set(px)) < 2:
            continue
        for mkey in metric_keys:
            my = [float(row.get(mkey, 0.0)) for row in bool_rows]
            true_values = [y for x, y in zip(px, my) if x == 1.0]
            false_values = [y for x, y in zip(px, my) if x == 0.0]
            if not true_values or not false_values:
                continue
            mean_diff = float(mean(true_values) - mean(false_values))
            point_biserial = _pearson_corr(px, my)
            if point_biserial is None:
                continue
            ci_low, ci_high = _bootstrap_corr_ci(
                px, my, confidence=0.95, n_resamples=1000
            )
            effects.append((pkey, mkey, mean_diff, point_biserial, ci_low, ci_high))

    effects.sort(key=lambda item: abs(item[3]), reverse=True)
    return effects[:top_n]


def _parse_ofat_scenario_name(name: str) -> tuple[str, str, float] | None:
    """Parse OFAT names '<base>_<param>_<value_token>' with per-parameter token scaling."""
    match = re.fullmatch(
        r"(?P<base>.+)_(?P<param>humidity|wind_strength|temperature_c)_(?P<value_token>\d+)",
        name,
    )
    if match is None:
        return None

    base_name = match.group("base")
    param_name = match.group("param")
    value_token = match.group("value_token")
    try:
        numeric_value = float(value_token)
    except ValueError:
        return None

    if param_name == "humidity":
        value = numeric_value / 100.0
    elif param_name == "wind_strength":
        value = numeric_value / 10.0
    else:
        value = numeric_value
    return base_name, param_name, value
