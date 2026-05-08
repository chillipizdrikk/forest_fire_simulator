from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
import math
from pathlib import Path
from random import Random
import re
from statistics import mean
from typing import Any


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


def _percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return float(ordered[0])
    q_clamped = _clamp_01(float(q))
    pos = (len(ordered) - 1) * q_clamped
    lower_idx = int(pos)
    upper_idx = min(lower_idx + 1, len(ordered) - 1)
    if lower_idx == upper_idx:
        return float(ordered[lower_idx])
    fraction = pos - lower_idx
    lower = ordered[lower_idx]
    upper = ordered[upper_idx]
    return float(lower + fraction * (upper - lower))


def _bootstrap_mean_ci(
    values: list[float],
    *,
    confidence: float = 0.95,
    n_resamples: int = 2000,
    seed: int = 42,
) -> tuple[float, float]:
    if not values:
        return 0.0, 0.0
    if len(values) == 1:
        value = float(values[0])
        return value, value

    rng = Random(seed)
    n = len(values)
    sample_means = []
    for _ in range(n_resamples):
        sample = [values[rng.randrange(n)] for _ in range(n)]
        sample_means.append(float(mean(sample)))

    alpha = (1.0 - confidence) / 2.0
    ci_low = _percentile(sample_means, alpha)
    ci_high = _percentile(sample_means, 1.0 - alpha)
    return ci_low, ci_high


def _pearson_corr(xs: list[float], ys: list[float]) -> float | None:
    if not xs or not ys or len(xs) != len(ys):
        return None
    x_mean = mean(xs)
    y_mean = mean(ys)
    x_std = (sum((x - x_mean) ** 2 for x in xs) / len(xs)) ** 0.5
    y_std = (sum((y - y_mean) ** 2 for y in ys) / len(ys)) ** 0.5
    if x_std == 0.0 or y_std == 0.0:
        return None
    cov = sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, ys)) / len(xs)
    return float(cov / (x_std * y_std))


def _pearson_p_value(xs: list[float], ys: list[float], corr: float) -> float:
    n = len(xs)
    if n != len(ys) or n < 3:
        return 1.0
    abs_corr = abs(float(corr))
    if abs_corr >= 1.0:
        return 0.0
    denom = 1.0 - (abs_corr**2)
    if denom <= 0.0:
        return 0.0
    t_stat = abs_corr * ((n - 2) / denom) ** 0.5
    # Normal approximation of two-sided p-value for Student's t.
    # Stable for ranking reliability, and avoids optional heavy dependencies.
    return float(_clamp_01(math.erfc(t_stat / math.sqrt(2.0))))


def _format_p_value(value: float) -> str:
    if value < 0.0001:
        return "<1e-4"
    return f"{value:.4f}"


def _correlation_sort_key(row: dict[str, float | str | bool], mode: str) -> tuple[float, ...]:
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


def _attach_bh_q_values(rows: list[dict[str, float | str | bool]]) -> list[dict[str, float | str | bool]]:
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


def _bootstrap_corr_ci(
    xs: list[float],
    ys: list[float],
    *,
    confidence: float = 0.95,
    n_resamples: int = 1000,
    seed: int = 42,
) -> tuple[float, float]:
    if not xs or not ys or len(xs) != len(ys):
        return 0.0, 0.0
    if len(xs) == 1:
        corr = _pearson_corr(xs, ys)
        if corr is None:
            return 0.0, 0.0
        return corr, corr

    rng = Random(seed)
    n = len(xs)
    sample_corrs: list[float] = []
    for _ in range(n_resamples):
        idxs = [rng.randrange(n) for _ in range(n)]
        bxs = [xs[i] for i in idxs]
        bys = [ys[i] for i in idxs]
        corr = _pearson_corr(bxs, bys)
        if corr is not None:
            sample_corrs.append(corr)

    if not sample_corrs:
        corr = _pearson_corr(xs, ys)
        if corr is None:
            return 0.0, 0.0
        return corr, corr

    alpha = (1.0 - confidence) / 2.0
    ci_low = _percentile(sample_corrs, alpha)
    ci_high = _percentile(sample_corrs, 1.0 - alpha)
    return ci_low, ci_high


def _linear_slope(xs: list[float], ys: list[float]) -> float | None:
    if not xs or not ys or len(xs) != len(ys):
        return None
    x_mean = mean(xs)
    denom = sum((x - x_mean) ** 2 for x in xs)
    if denom == 0.0:
        return None
    y_mean = mean(ys)
    numer = sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, ys))
    return float(numer / denom)


def _bootstrap_slope_ci(
    xs: list[float],
    ys: list[float],
    *,
    confidence: float = 0.95,
    n_resamples: int = 1000,
    seed: int = 42,
) -> tuple[float, float]:
    if not xs or not ys or len(xs) != len(ys):
        return 0.0, 0.0
    if len(xs) == 1:
        slope = _linear_slope(xs, ys)
        if slope is None:
            return 0.0, 0.0
        return slope, slope

    rng = Random(seed)
    n = len(xs)
    sample_slopes: list[float] = []
    for _ in range(n_resamples):
        idxs = [rng.randrange(n) for _ in range(n)]
        bxs = [xs[i] for i in idxs]
        bys = [ys[i] for i in idxs]
        slope = _linear_slope(bxs, bys)
        if slope is not None:
            sample_slopes.append(slope)

    if not sample_slopes:
        slope = _linear_slope(xs, ys)
        if slope is None:
            return 0.0, 0.0
        return slope, slope

    alpha = (1.0 - confidence) / 2.0
    ci_low = _percentile(sample_slopes, alpha)
    ci_high = _percentile(sample_slopes, 1.0 - alpha)
    return ci_low, ci_high


def _clamp_01(value: float) -> float:
    return max(0.0, min(1.0, value))


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
            "time_to_extinguish_survival_probabilities": {str(int(h)): 0.0 for h in horizons},
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
        "time_to_extinguish_survival_median": float(median_time if median_time is not None else max_observed_time),
        "time_to_extinguish_survival_median_reached": bool(median_time is not None),
        "time_to_extinguish_survival_median_lower_bound": float(max_observed_time),
        "time_to_extinguish_survival_probabilities": survival_probabilities,
    }


def _critical_share(rows: list[dict[str, Any]]) -> float:
    return float(sum(bool(row.get("critical", False)) for row in rows) / len(rows)) if rows else 0.0


def _cliffs_delta(xs: list[float], ys: list[float]) -> float:
    if not xs or not ys:
        return 0.0
    greater = 0
    lower = 0
    for x in xs:
        for y in ys:
            if x > y:
                greater += 1
            elif x < y:
                lower += 1
    denom = len(xs) * len(ys)
    if denom == 0:
        return 0.0
    return float((greater - lower) / denom)


def _cliffs_delta_label(delta: float) -> str:
    ad = abs(float(delta))
    if ad < 0.147:
        return "negligible"
    if ad < 0.33:
        return "small"
    if ad < 0.474:
        return "medium"
    return "large"


def _permutation_test_mean_diff(
    xs: list[float],
    ys: list[float],
    *,
    n_resamples: int = 2000,
    seed: int = 42,
) -> float:
    if not xs or not ys:
        return 1.0
    observed = float(mean(xs) - mean(ys))
    combined = [*xs, *ys]
    n_x = len(xs)
    rng = Random(seed)
    extreme = 0
    for _ in range(max(1, int(n_resamples))):
        shuffled = list(combined)
        rng.shuffle(shuffled)
        perm_x = shuffled[:n_x]
        perm_y = shuffled[n_x:]
        perm_diff = float(mean(perm_x) - mean(perm_y))
        if abs(perm_diff) >= abs(observed):
            extreme += 1
    return float((extreme + 1) / (max(1, int(n_resamples)) + 1))


def _benjamini_hochberg(p_values: list[float]) -> list[float]:
    if not p_values:
        return []
    m = len(p_values)
    ordered = sorted(enumerate(p_values), key=lambda item: item[1])
    adjusted = [1.0] * m
    running_min = 1.0
    for rank in range(m, 0, -1):
        idx, p = ordered[rank - 1]
        raw = float(p * m / rank)
        running_min = min(running_min, raw)
        adjusted[idx] = float(_clamp_01(running_min))
    return adjusted


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
        p_value = _permutation_test_mean_diff(values_a, values_b, n_resamples=n_resamples, seed=seed + idx)
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
    rows.sort(key=lambda row: (float(row["p_value_adj"]), -abs(float(row["effect_cliffs_delta"]))))
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
                float(sum(value >= critical_baf_threshold for value in baf_values) / len(baf_values))
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
        interaction_score_baf = abs((corner_means["f11"] - corner_means["f10"]) - (corner_means["f01"] - corner_means["f00"]))

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
    global_tte_values = [float(row.get("time_to_extinguish", 0.0)) for row in global_tte_rows]
    global_tte_norm = _normalize_01(global_tte_values)
    global_tte_norm_by_run_id = {
        str(row.get("run_id", f"row_{idx}")): norm for idx, (row, norm) in enumerate(zip(global_tte_rows, global_tte_norm))
    }

    by_scenario: dict[str, list[dict[str, Any]]] = {}
    for row in working_rows:
        by_scenario.setdefault(str(row["scenario"]), []).append(row)

    baf_values = [float(row.get("baf", 0.0)) for row in working_rows]
    censored_runs_count = int(sum(bool(row.get("truncated_by_max_steps", False)) for row in working_rows))
    censored_runs_share = float(censored_runs_count / len(working_rows)) if working_rows else 0.0
    no_ignition_runs_count = int(sum(bool(row.get("no_ignition", False)) for row in working_rows))
    no_ignition_runs_share = float(no_ignition_runs_count / len(working_rows)) if working_rows else 0.0
    tte_min = min(global_tte_values) if global_tte_values else 0.0
    tte_max = max(global_tte_values) if global_tte_values else 0.0
    tte_span = tte_max - tte_min
    for row in working_rows:
        run_id = str(row.get("run_id", ""))
        if run_id in global_tte_norm_by_run_id:
            row["time_to_extinguish_global_norm"] = float(global_tte_norm_by_run_id[run_id])
            continue
        if bool(row.get("no_ignition", False)):
            row["time_to_extinguish_global_norm"] = 0.0
            continue
        if tte_span == 0.0:
            row["time_to_extinguish_global_norm"] = 0.0
            continue
        tte_value = float(row.get("time_to_extinguish", 0.0))
        row["time_to_extinguish_global_norm"] = _clamp_01((tte_value - tte_min) / tte_span)
    overall = {
        "runs_total": len(working_rows),
        "baf_mean": float(mean(baf_values)) if baf_values else 0.0,
        "baf_mean_all": float(mean(baf_values)) if baf_values else 0.0,
        "baf_mean_uncensored": _mean_metric(uncensored_all, "baf"),
        "auc_normalized_mean": _mean_metric(working_rows, "auc_normalized"),
        "auc_normalized_mean_all": _mean_metric(working_rows, "auc_normalized"),
        "auc_normalized_mean_uncensored": _mean_metric(uncensored_all, "auc_normalized"),
        "burned_components_mean": _mean_metric(working_rows, "burned_components"),
        "burned_components_mean_all": _mean_metric(working_rows, "burned_components"),
        "burned_components_mean_uncensored": _mean_metric(uncensored_all, "burned_components"),
        "largest_cluster_share_mean": _mean_metric(working_rows, "largest_cluster_share"),
        "largest_cluster_share_mean_all": _mean_metric(working_rows, "largest_cluster_share"),
        "largest_cluster_share_mean_uncensored": _mean_metric(uncensored_all, "largest_cluster_share"),
        "shape_complexity_mean": _mean_metric(working_rows, "shape_complexity"),
        "shape_complexity_mean_all": _mean_metric(working_rows, "shape_complexity"),
        "shape_complexity_mean_uncensored": _mean_metric(uncensored_all, "shape_complexity"),
        "time_to_extinguish_mean": _mean_metric(ignited_rows, "time_to_extinguish"),
        "time_to_extinguish_mean_all": _mean_metric(working_rows, "time_to_extinguish"),
        "time_to_extinguish_mean_uncensored": _mean_metric(uncensored_ignited, "time_to_extinguish"),
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
            float(sum(v >= critical_baf_threshold for v in baf_values) / len(baf_values)) if baf_values else 0.0
        ),
        "critical_baf_threshold": critical_baf_threshold,
        "scenario_ranking_metric": ranking_metric,
        "censored_runs_count": censored_runs_count,
        "censored_runs_share": censored_runs_share,
        "no_ignition_runs_count": no_ignition_runs_count,
        "no_ignition_runs_share": no_ignition_runs_share,
        "time_to_extinguish_norm_scope": "uncensored_ignited_only" if uncensored_ignited else "ignited_runs",
        "time_to_extinguish_global_min": tte_min,
        "time_to_extinguish_global_max": tte_max,
    }
    overall.update(_kaplan_meier_tte_metrics(working_rows, horizons=tte_survival_horizons))

    scenario_stats: dict[str, dict[str, Any]] = {}
    for scenario_name, items in by_scenario.items():
        local_baf = [float(item.get("baf", 0.0)) for item in items]
        local_peak = [float(item.get("peak_fire_size", 0.0)) for item in items]
        local_auc = [float(item.get("auc", 0.0)) for item in items]
        local_peak_norm = [float(item.get("peak_fire_fraction", 0.0)) for item in items]
        local_auc_norm = [float(item.get("auc_normalized", 0.0)) for item in items]
        local_components = [float(item.get("burned_components", 0.0)) for item in items]
        local_largest_cluster_share = [float(item.get("largest_cluster_share", 0.0)) for item in items]
        local_shape_complexity = [float(item.get("shape_complexity", 0.0)) for item in items]
        uncensored_items = _uncensored_rows(items)
        ignited_items = _ignited_rows(items)
        uncensored_ignited_items = _uncensored_rows(ignited_items)
        run_tte_global_norm = [float(item.get("time_to_extinguish_global_norm", 0.0)) for item in items]
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
        baf_mean_ci_low, baf_mean_ci_high = _bootstrap_mean_ci(local_baf, confidence=0.95)
        risk_mean_ci_low, risk_mean_ci_high = _bootstrap_mean_ci(run_risk_scores, confidence=0.95)
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
            "peak_fire_fraction_mean": float(mean(local_peak_norm)) if local_peak_norm else 0.0,
            "auc_normalized_mean": float(mean(local_auc_norm)) if local_auc_norm else 0.0,
            "auc_normalized_mean_all": float(mean(local_auc_norm)) if local_auc_norm else 0.0,
            "auc_normalized_mean_uncensored": _mean_metric(uncensored_items, "auc_normalized"),
            "burned_components_mean": float(mean(local_components)) if local_components else 0.0,
            "burned_components_mean_uncensored": _mean_metric(uncensored_items, "burned_components"),
            "largest_cluster_share_mean": (
                float(mean(local_largest_cluster_share)) if local_largest_cluster_share else 0.0
            ),
            "largest_cluster_share_mean_uncensored": _mean_metric(uncensored_items, "largest_cluster_share"),
            "shape_complexity_mean": float(mean(local_shape_complexity)) if local_shape_complexity else 0.0,
            "shape_complexity_mean_uncensored": _mean_metric(uncensored_items, "shape_complexity"),
            "critical_count": int(sum(bool(item.get("critical", False)) for item in items)),
            "critical_mean_all": _critical_share(items),
            "critical_mean_uncensored": _critical_share(uncensored_items),
            "critical_share": _critical_share(items),
            "critical_share_uncensored": _critical_share(uncensored_items),
            "censored_share": float(sum(bool(item.get("truncated_by_max_steps", False)) for item in items) / len(items)),
            "max_spread_rate_mean": float(mean(float(item.get("max_spread_rate", 0.0)) for item in items)),
            "time_to_extinguish_mean": _mean_metric(ignited_items, "time_to_extinguish"),
            "time_to_extinguish_mean_all": float(mean(float(item.get("time_to_extinguish", 0.0)) for item in items)),
            "time_to_extinguish_mean_uncensored": _mean_metric(uncensored_ignited_items, "time_to_extinguish"),
            "risk_score_mean": float(mean(run_risk_scores)) if run_risk_scores else 0.0,
            "risk_score_mean_uncensored": (
                float(mean(run_risk_scores_uncensored)) if run_risk_scores_uncensored else 0.0
            ),
            "risk_score_mean_ci_low": risk_mean_ci_low,
            "risk_score_mean_ci_high": risk_mean_ci_high,
            "no_ignition_count": int(sum(bool(item.get("no_ignition", False)) for item in items)),
            "no_ignition_share": float(sum(bool(item.get("no_ignition", False)) for item in items) / len(items)),
        }
        scenario_stats[scenario_name].update(_kaplan_meier_tte_metrics(items, horizons=tte_survival_horizons))

    ranking = sorted(
        ((name, float(stats.get(ranking_metric, 0.0))) for name, stats in scenario_stats.items()),
        key=lambda x: x[1],
        reverse=True,
    )
    overall["ranking_by_burned_components_mean"] = sorted(
        ((name, float(stats.get("burned_components_mean", 0.0))) for name, stats in scenario_stats.items()),
        key=lambda item: item[1],
        reverse=True,
    )
    overall["ranking_by_shape_complexity_mean"] = sorted(
        ((name, float(stats.get("shape_complexity_mean", 0.0))) for name, stats in scenario_stats.items()),
        key=lambda item: item[1],
        reverse=True,
    )
    overall["ranking_by_largest_cluster_share_mean"] = sorted(
        ((name, float(stats.get("largest_cluster_share_mean", 0.0))) for name, stats in scenario_stats.items()),
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
            "significant_bh_005": int(sum(bool(item.get("significant_bh_005", False)) for item in rows_for_metric)),
        }
        for metric, rows_for_metric in pairwise_significance.items()
    }
    overall["pairwise_significance_permutations"] = int(max(1, significance_permutations))

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
        {key for row in working_rows for key in row if key.startswith("param_") and isinstance(row[key], bool)}
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
        overall["interaction_surface_primary_coverage"] = float(primary_surface["cell_coverage"])
        overall["interaction_surface_primary_score_baf"] = float(primary_surface["interaction_score_baf"])

    correlations_by_scenario: dict[str, list[dict[str, float | str | bool]]] = {}
    correlations_by_scenario_diagnostics: dict[str, dict[str, Any]] = {}
    for scenario_name, scenario_rows in by_scenario.items():
        non_constant_params = _count_non_constant_params(scenario_rows, continuous_param_keys)
        constant_params = [pkey for pkey in continuous_param_keys if pkey not in non_constant_params]
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
                corr_ci_low, corr_ci_high = _bootstrap_corr_ci(px, my, confidence=0.95, n_resamples=1000)
                slope_ci_low, slope_ci_high = _bootstrap_slope_ci(px, my, confidence=0.95, n_resamples=1000)
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
        family_corrs = _sort_correlations(family_corrs, ranking_mode="q_then_abs_r", top_n=correlation_top_n)
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
            ci_low, ci_high = _bootstrap_corr_ci(px, my, confidence=0.95, n_resamples=1000)
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


def _count_non_constant_params(rows: list[dict[str, Any]], numeric_param_keys: list[str]) -> list[str]:
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
            ci_low, ci_high = _bootstrap_corr_ci(px, my, confidence=0.95, n_resamples=1000)
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
            ci_low, ci_high = _bootstrap_corr_ci(px, my, confidence=0.95, n_resamples=1000)
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


def _save_plots(
    rows: list[dict[str, Any]],
    figures_dir: Path,
    *,
    interaction_surfaces: list[dict[str, Any]] | None = None,
) -> list[Path]:
    figures_dir.mkdir(parents=True, exist_ok=True)
    generated: list[Path] = []
    try:
        import matplotlib.pyplot as plt
    except Exception:
        return generated

    grouped: dict[str, list[float]] = {}
    for row in rows:
        grouped.setdefault(str(row["scenario"]), []).append(float(row.get("baf", 0.0)))

    labels_all = sorted(grouped.keys())
    ofat_labels = [label for label in labels_all if _parse_ofat_scenario_name(label) is not None]
    base_labels = [label for label in labels_all if label not in ofat_labels]
    labels = base_labels if base_labels else labels_all
    values = [grouped[label] for label in labels]

    # Global histogram (all scenarios mixed) with scenario means for quick orientation.
    baf_values = [float(r.get("baf", 0.0)) for r in rows]
    if baf_values:
        fig = plt.figure(figsize=(7, 4))
        plt.hist(baf_values, bins=30, color="#7aa6c2", edgecolor="white", alpha=0.9)
        for label in labels:
            local = grouped.get(label, [])
            if local:
                plt.axvline(sum(local) / len(local), linestyle="--", linewidth=1.2, alpha=0.7, label=f"{label} mean")
        plt.title("BAF distribution (all scenarios mixed)")
        plt.xlabel("baf")
        plt.ylabel("count")
        if labels:
            plt.legend(fontsize=8, ncol=2, frameon=False)
        hist_path = figures_dir / "baf_hist.png"
        fig.tight_layout()
        fig.savefig(hist_path)
        plt.close(fig)
        generated.append(hist_path)

    # Boxplot by scenario with better readability for longer labels.
    if values:
        fig = plt.figure(figsize=(max(8, len(labels) * 1.2), 4.8))
        plt.boxplot(values, tick_labels=labels, showfliers=True)
        plt.title("Scenario comparison by burned area fraction")
        plt.ylabel("baf")
        plt.ylim(-0.02, 1.02)
        plt.xticks(rotation=20, ha="right")
        plt.grid(axis="y", alpha=0.25, linestyle=":")
        box_path = figures_dir / "scenario_baf_boxplot.png"
        fig.tight_layout()
        fig.savefig(box_path)
        plt.close(fig)
        generated.append(box_path)

    # Keep OFAT variants separate to avoid overcrowding core scenario comparisons.
    if ofat_labels:
        ofat_values = [grouped[label] for label in ofat_labels]
        fig = plt.figure(figsize=(max(10, len(ofat_labels) * 0.45), 5.2))
        plt.boxplot(ofat_values, tick_labels=ofat_labels, showfliers=False)
        plt.title("OFAT subscenario comparison by burned area fraction")
        plt.ylabel("baf")
        plt.ylim(-0.02, 1.02)
        plt.xticks(rotation=35, ha="right", fontsize=8)
        plt.grid(axis="y", alpha=0.25, linestyle=":")
        ofat_box_path = figures_dir / "scenario_baf_boxplot_ofat.png"
        fig.tight_layout()
        fig.savefig(ofat_box_path)
        plt.close(fig)
        generated.append(ofat_box_path)

    # Per-scenario histograms in a small-multiples layout for local interpretation.
    if labels:
        cols = min(3, len(labels))
        rows_n = (len(labels) + cols - 1) // cols
        fig, axes = plt.subplots(rows_n, cols, figsize=(4.6 * cols, 3.2 * rows_n), squeeze=False, sharex=True, sharey=False)
        fixed_bins = [idx / 20 for idx in range(21)]
        for idx, label in enumerate(labels):
            ax = axes[idx // cols][idx % cols]
            local = grouped[label]
            ax.hist(local, bins=fixed_bins, color="#6bbf83", edgecolor="#f5f5f5", alpha=0.95, linewidth=0.8)
            local_mean = sum(local) / len(local) if local else 0.0
            ax.axvline(local_mean, color="#2b6f3e", linestyle="--", linewidth=1.2)
            ax.set_title(label)
            ax.set_xlim(-0.02, 1.02)
            ax.grid(axis="y", alpha=0.2, linestyle=":")
        for idx in range(len(labels), rows_n * cols):
            ax = axes[idx // cols][idx % cols]
            ax.axis("off")
        fig.suptitle("BAF distribution per scenario", y=1.02)
        for ax in axes[-1]:
            ax.set_xlabel("baf")
        for row_axes in axes:
            row_axes[0].set_ylabel("count")
        scenario_hist_path = figures_dir / "scenario_baf_hist_grid.png"
        fig.tight_layout()
        fig.savefig(scenario_hist_path)
        plt.close(fig)
        generated.append(scenario_hist_path)

    # Scenario-wise mean and uncertainty (p25-p75) for fast comparison.
    if values:
        means = []
        p25 = []
        p75 = []
        for label in labels:
            local_sorted = sorted(grouped[label])
            n = len(local_sorted)
            means.append(sum(local_sorted) / n)
            i25 = int((n - 1) * 0.25)
            i75 = int((n - 1) * 0.75)
            p25.append(local_sorted[i25])
            p75.append(local_sorted[i75])

        fig = plt.figure(figsize=(max(8, len(labels) * 1.2), 4.6))
        x = list(range(len(labels)))
        # Mean may sit outside IQR in skewed distributions, which would yield negative
        # error bars and break matplotlib. Clamp to zero for one-sided spread.
        lower_err = [max(0.0, m - q1) for m, q1 in zip(means, p25)]
        upper_err = [max(0.0, q3 - m) for m, q3 in zip(means, p75)]
        plt.errorbar(x, means, yerr=[lower_err, upper_err], fmt="o", capsize=4, color="#1f4e79")
        plt.xticks(x, labels, rotation=20, ha="right")
        plt.ylim(-0.02, 1.02)
        plt.ylabel("baf")
        plt.title("Scenario mean BAF with interquartile range")
        plt.grid(axis="y", alpha=0.25, linestyle=":")
        summary_path = figures_dir / "scenario_baf_mean_iqr.png"
        fig.tight_layout()
        fig.savefig(summary_path)
        plt.close(fig)
        generated.append(summary_path)

    if ofat_labels:
        ofat_by_base_and_param: dict[tuple[str, str], list[tuple[float, float]]] = {}
        for label in ofat_labels:
            parsed = _parse_ofat_scenario_name(label)
            if not parsed:
                continue
            base_name, param_name, value = parsed
            local = grouped[label]
            local_mean = sum(local) / len(local) if local else 0.0
            ofat_by_base_and_param.setdefault((base_name, param_name), []).append((value, local_mean))

        if ofat_by_base_and_param:
            base_names = sorted({base for base, _ in ofat_by_base_and_param.keys()})
            fig, axes = plt.subplots(
                len(base_names),
                1,
                figsize=(8.4, max(3.2, 3.0 * len(base_names))),
                squeeze=False,
                sharey=True,
            )
            colors = {"humidity": "#2b8cbe", "wind_strength": "#e34a33", "temperature_c": "#31a354"}
            for row_index, base_name in enumerate(base_names):
                ax = axes[row_index][0]
                for param_name in ("humidity", "wind_strength", "temperature_c"):
                    pairs = sorted(ofat_by_base_and_param.get((base_name, param_name), []), key=lambda item: item[0])
                    if not pairs:
                        continue
                    xs = [item[0] for item in pairs]
                    ys = [item[1] for item in pairs]
                    ax.plot(xs, ys, marker="o", linewidth=1.8, label=param_name, color=colors[param_name])
                ax.set_title(base_name)
                ax.set_ylim(-0.02, 1.02)
                ax.grid(alpha=0.25, linestyle=":")
                ax.set_ylabel("mean baf")
                ax.legend(frameon=False, fontsize=8, ncol=3, loc="upper right")

            axes[-1][0].set_xlabel("parameter value")
            fig.suptitle("OFAT sensitivity curves (mean BAF)", y=1.01)
            ofat_curve_path = figures_dir / "scenario_baf_mean_ofat_curves.png"
            fig.tight_layout()
            fig.savefig(ofat_curve_path)
            plt.close(fig)
            generated.append(ofat_curve_path)

    if interaction_surfaces:
        for surface in interaction_surfaces:
            x_values = [float(v) for v in surface.get("x_values", [])]
            y_values = [float(v) for v in surface.get("y_values", [])]
            mean_baf_grid = surface.get("mean_baf_grid", [])
            catastrophic_grid = surface.get("catastrophic_grid", [])
            param_x = str(surface.get("param_x", "param_x")).replace("param_", "")
            param_y = str(surface.get("param_y", "param_y")).replace("param_", "")
            if not x_values or not y_values or not mean_baf_grid or not catastrophic_grid:
                continue

            def _grid_to_array(grid: Any) -> tuple[Any, Any]:
                import numpy as np

                matrix = np.full((len(y_values), len(x_values)), np.nan, dtype=float)
                for yi, row_values in enumerate(grid):
                    for xi, value in enumerate(row_values):
                        if value is None:
                            continue
                        matrix[yi, xi] = float(value)
                masked = np.ma.masked_invalid(matrix)
                return matrix, masked

            try:
                _, baf_masked = _grid_to_array(mean_baf_grid)
                fig = plt.figure(figsize=(7.0, 5.2))
                im = plt.imshow(baf_masked, origin="lower", aspect="auto", vmin=0.0, vmax=1.0, cmap="YlOrRd")
                plt.colorbar(im, label="mean baf")
                plt.xticks(range(len(x_values)), [f"{v:.3g}" for v in x_values], rotation=30, ha="right")
                plt.yticks(range(len(y_values)), [f"{v:.3g}" for v in y_values])
                plt.xlabel(param_x)
                plt.ylabel(param_y)
                plt.title(f"2D interaction surface: mean BAF ({param_x} × {param_y})")
                baf_path = figures_dir / f"interaction_mean_baf_{param_x}_x_{param_y}.png"
                fig.tight_layout()
                fig.savefig(baf_path)
                plt.close(fig)
                generated.append(baf_path)
            except Exception:
                pass

            try:
                _, crit_masked = _grid_to_array(catastrophic_grid)
                fig = plt.figure(figsize=(7.0, 5.2))
                im = plt.imshow(crit_masked, origin="lower", aspect="auto", vmin=0.0, vmax=1.0, cmap="magma")
                plt.colorbar(im, label="catastrophic probability")
                plt.xticks(range(len(x_values)), [f"{v:.3g}" for v in x_values], rotation=30, ha="right")
                plt.yticks(range(len(y_values)), [f"{v:.3g}" for v in y_values])
                plt.xlabel(param_x)
                plt.ylabel(param_y)
                plt.title(f"2D interaction surface: catastrophic probability ({param_x} × {param_y})")
                crit_path = figures_dir / f"interaction_catastrophic_{param_x}_x_{param_y}.png"
                fig.tight_layout()
                fig.savefig(crit_path)
                plt.close(fig)
                generated.append(crit_path)
            except Exception:
                pass

    return generated


def generate_report(
    rows: list[dict[str, Any]],
    summary: AnalysisSummary,
    reports_dir: str | Path,
    *,
    censoring_audit: dict[str, Any] | None = None,
    sensitivity_ranking: str = "q_then_abs_r",
) -> tuple[Path, Path, list[Path]]:
    output_dir = Path(reports_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    figures = _save_plots(rows, output_dir / "figures", interaction_surfaces=summary.interaction_surfaces)

    top_worst = summary.scenario_ranking[:3]
    ranking_metric = str(summary.overall.get("scenario_ranking_metric", "auc_normalized_mean"))
    ranking_metric_labels = {
        "auc_normalized_mean": "Mean auc_normalized (normalized)",
        "peak_fire_fraction_mean": "Mean peak_fire_fraction (normalized)",
        "auc_mean": "Mean AUC (absolute)",
        "baf_mean": "Mean burned area fraction (absolute, point estimate)",
        "risk_score_mean": "Mean composite risk score (normalized)",
    }
    ranking_metric_label = ranking_metric_labels.get(ranking_metric, f"Mean {ranking_metric}")
    top_worst_abs_baf = sorted(
        ((name, float(stats.get("baf_mean_all", 0.0))) for name, stats in summary.by_scenario.items()),
        key=lambda item: item[1],
        reverse=True,
    )[:3]
    top_worst_abs_baf_with_ci = sorted(
        (
            (
                name,
                float(stats.get("baf_mean_all", 0.0)),
                float(stats.get("baf_mean_ci_low", 0.0)),
                float(stats.get("baf_mean_ci_high", 0.0)),
            )
            for name, stats in summary.by_scenario.items()
        ),
        key=lambda item: item[1],
        reverse=True,
    )[:3]
    top_worst_conservative_baf = sorted(
        (
            (
                name,
                float(stats.get("baf_mean_all", 0.0)),
                float(stats.get("baf_mean_ci_low", 0.0)),
                float(stats.get("baf_mean_ci_high", 0.0)),
            )
            for name, stats in summary.by_scenario.items()
        ),
        key=lambda item: item[3],
        reverse=True,
    )[:3]
    top_worst_abs_auc = sorted(
        ((name, float(stats.get("auc_mean", 0.0))) for name, stats in summary.by_scenario.items()),
        key=lambda item: item[1],
        reverse=True,
    )[:3]
    top_worst_norm_peak = sorted(
        ((name, float(stats.get("peak_fire_fraction_mean", 0.0))) for name, stats in summary.by_scenario.items()),
        key=lambda item: item[1],
        reverse=True,
    )[:3]
    top_worst_composite_risk = sorted(
        (
            (
                name,
                float(stats.get("risk_score_mean", 0.0)),
                float(stats.get("risk_score_mean_ci_low", 0.0)),
                float(stats.get("risk_score_mean_ci_high", 0.0)),
            )
            for name, stats in summary.by_scenario.items()
        ),
        key=lambda item: item[1],
        reverse=True,
    )[:3]
    top_continuous_corr_uncontrolled = _sort_correlations(
        summary.continuous_param_correlations,
        ranking_mode=sensitivity_ranking,
        top_n=5,
    )
    top_continuous_corr_controlled = _sort_correlations(
        summary.continuous_param_correlations_controlled,
        ranking_mode=sensitivity_ranking,
        top_n=5,
    )
    top_binary_effects = summary.binary_param_effects[:5]
    top_pairwise_baf = summary.scenario_pairwise_significance.get("baf", [])[:5]
    top_pairwise_auc_norm = summary.scenario_pairwise_significance.get("auc_normalized", [])[:5]
    sorted_scenario_names = sorted(summary.by_scenario.keys())
    sorted_family_names = sorted(summary.correlations_by_family_diagnostics.keys())
    elevated_censoring = [
        (name, float(stats.get("censored_share", 0.0)))
        for name, stats in summary.by_scenario.items()
        if float(stats.get("censored_share", 0.0)) >= 0.06
    ]
    elevated_censoring.sort(key=lambda item: item[1], reverse=True)
    overall_surv_probs = dict(summary.overall.get("time_to_extinguish_survival_probabilities", {}))
    horizon_200_key = "200"
    top_persistent_by_200 = sorted(
        (
            (
                name,
                float(stats.get("time_to_extinguish_survival_probabilities", {}).get(horizon_200_key, 0.0)),
                float(stats.get("time_to_extinguish_survival_median", 0.0)),
                bool(stats.get("time_to_extinguish_survival_median_reached", False)),
            )
            for name, stats in summary.by_scenario.items()
        ),
        key=lambda item: item[1],
        reverse=True,
    )[:3]

    md_path = output_dir / "summary.md"
    html_path = output_dir / "summary.html"

    md_lines = [
        "# Forest fire experiments report",
        "",
        "## Overall",
        f"- Total runs: {summary.overall['runs_total']}",
        (
            "- Mean burned area fraction (all / uncensored): "
            f"{summary.overall['baf_mean_all']:.4f} / {summary.overall['baf_mean_uncensored']:.4f}"
        ),
        (
            "- Mean auc_normalized (all / uncensored): "
            f"{summary.overall['auc_normalized_mean_all']:.4f} / {summary.overall['auc_normalized_mean_uncensored']:.4f}"
        ),
        (
            "- Mean time_to_extinguish (all / uncensored): "
            f"{summary.overall['time_to_extinguish_mean_all']:.4f} / {summary.overall['time_to_extinguish_mean_uncensored']:.4f}"
        ),
        (
            "- Survival median time_to_extinguish (KM, right-censored by max_steps): "
            f"{summary.overall['time_to_extinguish_survival_median']:.4f} "
            f"(reached={summary.overall['time_to_extinguish_survival_median_reached']})"
        ),
        (
            "- Survival probability P(TTE > 200): "
            f"{float(overall_surv_probs.get('200', 0.0)):.4f}"
        ),
        (
            "- Critical share (all / uncensored): "
            f"{summary.overall['critical_mean_all']:.4f} / {summary.overall['critical_mean_uncensored']:.4f}"
        ),
        (
            "- BAF quantiles p25/p50/p75/p95: "
            f"{summary.overall['baf_p25']:.4f} / {summary.overall['baf_p50']:.4f} / "
            f"{summary.overall['baf_p75']:.4f} / {summary.overall['baf_p95']:.4f}"
        ),
        f"- Burned area p95/p99: {summary.overall['baf_p95']:.4f} / {summary.overall['baf_p99']:.4f}",
        f"- Critical BAF threshold used: {summary.overall['critical_baf_threshold']:.4f}",
        (
            f"- Catastrophic probability (baf >= {summary.overall['critical_baf_threshold']:.4f}): "
            f"{summary.overall['catastrophic_probability']:.4f}"
        ),
        f"- Scenario ranking metric: {summary.overall['scenario_ranking_metric']}",
        (
            f"- Censored runs (truncated by max_steps): {summary.overall['censored_runs_count']} "
            f"({summary.overall['censored_runs_share']:.4f})"
        ),
        (
            "- Pairwise significance tests: "
            f"{summary.overall.get('pairwise_significance_tests', {}).get('baf', {}).get('significant_bh_005', 0)} "
            f"/ {summary.overall.get('pairwise_significance_tests', {}).get('baf', {}).get('pairs_total', 0)} "
            "significant pairs for baf; "
            f"{summary.overall.get('pairwise_significance_tests', {}).get('auc_normalized', {}).get('significant_bh_005', 0)} "
            f"/ {summary.overall.get('pairwise_significance_tests', {}).get('auc_normalized', {}).get('pairs_total', 0)} "
            "for auc_normalized (BH q<=0.05)."
        ),
        (
            "- Note: censored runs can bias metrics: fire_duration and AUC are typically underestimated, "
            "while BAF-related risk can be understated when fire is still active at truncation."
        ),
        "",
        f"## Worst scenarios by {ranking_metric_label}",
    ]
    for name, score in top_worst:
        md_lines.append(f"- {name}: {score:.4f}")

    if censoring_audit:
        md_lines.append("")
        md_lines.append("## Censoring max_steps bias audit")
        md_lines.append(
            "- Target rule: "
            f"censored_share < {float(censoring_audit.get('target_censored_share', 0.0)):.4f}"
        )
        md_lines.append(f"- Initial max_steps: {int(censoring_audit.get('initial_max_steps', 0))}")
        md_lines.append(f"- Final max_steps: {int(censoring_audit.get('final_max_steps', 0))}")
        md_lines.append(f"- Stop reason: {str(censoring_audit.get('stop_reason', 'n/a'))}")
        for round_info in censoring_audit.get("rounds", []):
            md_lines.append(
                "### Round "
                f"{int(round_info.get('round', 0))}: max_steps "
                f"{int(round_info.get('from_max_steps', 0))} -> {int(round_info.get('to_max_steps', 0))}"
            )
            md_lines.append(
                f"- Re-run scenarios: {', '.join(round_info.get('rerun_scenarios', [])) or 'none'}"
            )
            for scenario_delta in round_info.get("scenario_deltas", []):
                md_lines.append(
                    "- "
                    f"{scenario_delta['scenario']}: censored_share "
                    f"{float(scenario_delta['before_censored_share']):.4f} -> "
                    f"{float(scenario_delta['after_censored_share']):.4f}; "
                    f"baf_mean_all {float(scenario_delta['before_baf_mean_all']):.4f} -> "
                    f"{float(scenario_delta['after_baf_mean_all']):.4f}; "
                    f"auc_normalized_mean_all {float(scenario_delta['before_auc_normalized_mean_all']):.4f} -> "
                    f"{float(scenario_delta['after_auc_normalized_mean_all']):.4f}"
                )

    md_lines.append("")
    md_lines.append("## Absolute KPI ranking")
    md_lines.append("### Mean burned area fraction (absolute, point estimate)")
    for name, score in top_worst_abs_baf:
        md_lines.append(f"- {name}: {score:.4f}")
    md_lines.append("### KPI comparison by scenario (all / uncensored)")
    for name in sorted_scenario_names:
        stats = summary.by_scenario[name]
        censoring_note = (
            " ⚠️ reliability: time_to_extinguish/AUC may be less reliable; consider larger max_steps."
            if float(stats.get("censored_share", 0.0)) >= 0.06
            else ""
        )
        md_lines.append(
            "- "
            f"{name}: baf={stats['baf_mean_all']:.4f}/{stats['baf_mean_uncensored']:.4f}, "
            f"auc_normalized={stats['auc_normalized_mean_all']:.4f}/{stats['auc_normalized_mean_uncensored']:.4f}, "
            f"time_to_extinguish={stats['time_to_extinguish_mean_all']:.4f}/{stats['time_to_extinguish_mean_uncensored']:.4f}, "
            f"critical={stats['critical_mean_all']:.4f}/{stats['critical_mean_uncensored']:.4f}, "
            f"censored_share={stats['censored_share']:.4f}, "
            f"baf_q(p25/p50/p75/p95)={stats['baf_p25']:.4f}/{stats['baf_p50']:.4f}/{stats['baf_p75']:.4f}/{stats['baf_p95']:.4f}"
            f"{censoring_note}"
        )
    if elevated_censoring:
        md_lines.append("### Censoring reliability flags")
        md_lines.append(
            "- Scenarios with censored_share >= 0.06 should be interpreted with care for time_to_extinguish/AUC."
        )
        for name, share in elevated_censoring:
            md_lines.append(f"- {name}: censored_share={share:.4f}")
    md_lines.append("### Time-to-extinguish survival KPI (right-censored by max_steps)")
    md_lines.append(
        "- Interpret time via survival metrics (KM): median reflects extinction-time distribution robustly under censoring."
    )
    md_lines.append(
        f"- Overall median TTE: {summary.overall['time_to_extinguish_survival_median']:.4f} "
        f"(reached={summary.overall['time_to_extinguish_survival_median_reached']}, "
        f"lower_bound={summary.overall['time_to_extinguish_survival_median_lower_bound']:.4f})"
    )
    md_lines.append(
        f"- Overall P(TTE > 200): {float(overall_surv_probs.get('200', 0.0)):.4f}"
    )
    md_lines.append("- Highest persistence scenarios by P(TTE > 200):")
    for name, surv_200, median_tte, median_reached in top_persistent_by_200:
        md_lines.append(
            f"- {name}: P(TTE>200)={surv_200:.4f}, median={median_tte:.4f} (reached={median_reached})"
        )
    md_lines.append("### Mean burned area fraction (95% bootstrap CI)")
    for name, baf_mean, ci_low, ci_high in top_worst_abs_baf_with_ci:
        md_lines.append(f"- {name}: {baf_mean:.4f} (95% CI: {ci_low:.4f}..{ci_high:.4f})")
    md_lines.append("### Conservative risk ranking (mean BAF upper 95% CI bound)")
    for name, baf_mean, ci_low, ci_high in top_worst_conservative_baf:
        md_lines.append(f"- {name}: upper_ci={ci_high:.4f} (mean={baf_mean:.4f}, 95% CI: {ci_low:.4f}..{ci_high:.4f})")
    md_lines.append("### Mean AUC (absolute)")
    for name, score in top_worst_abs_auc:
        md_lines.append(f"- {name}: {score:.4f}")

    md_lines.append("")
    md_lines.append("## Normalized KPI ranking")
    md_lines.append("### Mean peak_fire_fraction (normalized)")
    for name, score in top_worst_norm_peak:
        md_lines.append(f"- {name}: {score:.4f}")
    md_lines.append("")
    md_lines.append("## Composite risk ranking")
    md_lines.append("### Mean composite risk score (normalized, 95% bootstrap CI)")
    for name, score, ci_low, ci_high in top_worst_composite_risk:
        md_lines.append(f"- {name}: {score:.4f} (95% CI: {ci_low:.4f}..{ci_high:.4f})")
    md_lines.append(f"### {ranking_metric_label}")
    for name, score in top_worst:
        md_lines.append(f"- {name}: {score:.4f}")

    md_lines.append("")
    md_lines.append("## Scenario pairwise significance tests")
    md_lines.append(
        f"- Method: two-sided permutation test on mean differences "
        f"({summary.overall.get('pairwise_significance_permutations', 0)} resamples), "
        "Benjamini–Hochberg correction, and Cliff's delta effect size."
    )
    md_lines.append("### baf")
    for item in top_pairwise_baf:
        md_lines.append(
            "- "
            f"{item['scenario_a']} vs {item['scenario_b']}: "
            f"mean_diff={float(item['mean_diff']):.4f}, "
            f"p={float(item['p_value']):.4f}, q={float(item['p_value_adj']):.4f}, "
            f"significant={bool(item['significant_bh_005'])}, "
            f"cliffs_delta={float(item['effect_cliffs_delta']):.4f} ({item['effect_label']})"
        )
    md_lines.append("### auc_normalized")
    for item in top_pairwise_auc_norm:
        md_lines.append(
            "- "
            f"{item['scenario_a']} vs {item['scenario_b']}: "
            f"mean_diff={float(item['mean_diff']):.4f}, "
            f"p={float(item['p_value']):.4f}, q={float(item['p_value_adj']):.4f}, "
            f"significant={bool(item['significant_bh_005'])}, "
            f"cliffs_delta={float(item['effect_cliffs_delta']):.4f} ({item['effect_label']})"
        )

    md_lines.append("")
    md_lines.append("## Global parameter sensitivity")
    md_lines.append(
        "- Purpose: estimates the overall influence of simultaneously varied parameters and their interactions "
        "across the experiment design. Use this separately from OFAT sensitivity, which reports local one-factor trends."
    )
    md_lines.append(
        "- Report inputs: continuous_param_correlations, binary_param_effects, and interaction_surface summaries "
        "computed from the full run table."
    )
    md_lines.append("### continuous_param_correlations (uncontrolled)")
    md_lines.append("- Note: these are global Pearson correlations for continuous params only.")
    for item in top_continuous_corr_uncontrolled:
        md_lines.append(
            "- "
            f"{item['param_key']} vs {item['metric_key']}: "
            f"r={float(item['r']):.4f}, 95% CI {float(item['r_ci_low']):.4f}..{float(item['r_ci_high']):.4f}, "
            f"p={_format_p_value(float(item['p_value']))}, q={_format_p_value(float(item['q_value']))}, "
            f"q<=0.05={bool(item['q_le_005'])}"
        )
    md_lines.append("")
    md_lines.append("### continuous_param_correlations (controlled by scenario)")
    md_lines.append("- Method: within-scenario demeaning (scenario fixed-effects style).")
    for item in top_continuous_corr_controlled:
        md_lines.append(
            "- "
            f"{item['param_key']} vs {item['metric_key']}: "
            f"r={float(item['r']):.4f}, 95% CI {float(item['r_ci_low']):.4f}..{float(item['r_ci_high']):.4f}, "
            f"p={_format_p_value(float(item['p_value']))}, q={_format_p_value(float(item['q_value']))}, "
            f"q<=0.05={bool(item['q_le_005'])}"
        )
    md_lines.append("")
    md_lines.append("### binary_param_effects")
    md_lines.append("- For binary params: mean(True)-mean(False), plus point-biserial correlation with 95% CI.")
    for pkey, mkey, mean_diff, corr, ci_low, ci_high in top_binary_effects:
        md_lines.append(
            f"- {pkey} vs {mkey}: mean_diff={mean_diff:.4f}, point_biserial_r={corr:.4f}, "
            f"95% CI {ci_low:.4f}..{ci_high:.4f}"
        )
    md_lines.append("")
    md_lines.append("## Scenario-local top parameter-metric correlations")
    for scenario_name in sorted_scenario_names:
        scenario_corr = summary.correlations_by_scenario.get(scenario_name)
        diag = summary.correlations_by_scenario_diagnostics.get(scenario_name, {})
        runs = int(diag.get("runs", 0))
        non_constant_param_count = int(diag.get("non_constant_param_count", 0))
        total_param_count = int(diag.get("total_param_count", 0))
        min_runs = int(diag.get("min_runs_required", 5))
        constant_param_keys = list(diag.get("constant_param_keys", []))
        md_lines.append(f"### {scenario_name}")
        if scenario_corr:
            if non_constant_param_count == 0:
                md_lines.append(
                    f"- ⚠️ Correlation is weakly identified: all param_* are constant "
                    f"({runs} runs, varying params: 0/{total_param_count})."
                )
            for item in _sort_correlations(scenario_corr, ranking_mode=sensitivity_ranking, top_n=5):
                md_lines.append(
                    "- "
                    f"{item['param_key']} vs {item['metric_key']}: "
                    f"r={float(item['r']):.4f}, 95% CI {float(item['r_ci_low']):.4f}..{float(item['r_ci_high']):.4f}, "
                    f"p={_format_p_value(float(item['p_value']))}, q={_format_p_value(float(item['q_value']))}, "
                    f"q<=0.05={bool(item['q_le_005'])}"
                )
        else:
            md_lines.append(
                (
                    "- Not enough information for per-scenario correlation estimation "
                    f"(runs: {runs}, minimum: {min_runs}, varying params: "
                    f"{non_constant_param_count}/{total_param_count})."
                )
            )
        if constant_param_keys:
            shown_keys = ", ".join(constant_param_keys[:5])
            suffix = "..." if len(constant_param_keys) > 5 else ""
            md_lines.append(
                f"- ⚠️ Constant param_* in this scenario ({len(constant_param_keys)}): {shown_keys}{suffix}"
            )

    md_lines.append("")
    md_lines.append("## OFAT sensitivity (local one-factor trends)")
    md_lines.append(
        "- Purpose: estimates local trends around fixed base scenarios by changing one parameter at a time. "
        "Do not interpret OFAT slopes as global parameter importance when multiple parameters vary together."
    )
    md_lines.append(
        "- Grouping rule: OFAT scenarios are grouped by axis `<base> / <varied_param>` "
        "(e.g. `transition_low_humidity / humidity`)."
    )
    md_lines.append("- Non-OFAT scenarios are excluded from this OFAT sensitivity section.")
    md_lines.append("- For each OFAT axis: Pearson correlation and linear slope with 95% bootstrap CI.")
    for family_name in sorted_family_names:
        family_corr = summary.correlations_by_family.get(family_name)
        diag = summary.correlations_by_family_diagnostics.get(family_name, {})
        runs = int(diag.get("runs", 0))
        non_constant_param_count = int(diag.get("non_constant_param_count", 0))
        total_param_count = int(diag.get("total_param_count", 0))
        min_runs = int(diag.get("min_runs_required", 5))
        md_lines.append(f"### {family_name}")
        if bool(diag.get("ofat_excluded", False)):
            md_lines.append("- Excluded: scenario name does not match OFAT naming convention.")
            continue
        if family_corr:
            for item in _sort_correlations(family_corr, ranking_mode=sensitivity_ranking, top_n=5):
                md_lines.append(
                    f"- {item['param_key']} vs {item['metric_key']}: "
                    f"r={float(item['r']):.4f} (95% CI {float(item['r_ci_low']):.4f}..{float(item['r_ci_high']):.4f}), "
                    f"p={_format_p_value(float(item['p_value']))}, q={_format_p_value(float(item['q_value']))}, "
                    f"q<=0.05={bool(item['q_le_005'])}, "
                    f"slope={float(item['slope']):.4f} (95% CI {float(item['slope_ci_low']):.4f}..{float(item['slope_ci_high']):.4f})"
                )
        else:
            md_lines.append(
                (
                    "- Not enough information for family-level sensitivity estimation "
                    f"(runs: {runs}, minimum: {min_runs}, varying params: "
                    f"{non_constant_param_count}/{total_param_count})."
                )
            )

    if summary.interaction_surfaces:
        md_lines.append("")
        md_lines.append("### 2D sensitivity (interaction surface)")
        md_lines.append(
            "- Built from two most influential continuous params for `baf` (by |r| in global correlations) "
            "as the interaction_surface part of global sensitivity."
        )
        for surface in summary.interaction_surfaces:
            score = float(surface.get("interaction_score_baf", 0.0))
            if score >= 0.20:
                level = "strong"
            elif score >= 0.08:
                level = "moderate"
            else:
                level = "weak"
            md_lines.append(
                "- Pair "
                f"{surface.get('param_x', 'param_x')} × {surface.get('param_y', 'param_y')}: "
                f"coverage={float(surface.get('cell_coverage', 0.0)):.4f} "
                f"({int(surface.get('cells_observed', 0))}/{int(surface.get('cells_total', 0))} cells), "
                f"interaction_score_baf={score:.4f} ({level})."
            )
            md_lines.append(
                "- OFAT comparison hint: if OFAT curves looked near-linear but interaction_score is moderate/strong, "
                "this suggests non-additive effects between the two parameters."
            )

    if figures:
        md_lines.append("")
        md_lines.append("## Figures")
        figure_notes = {
            "baf_hist": "Global BAF histogram across all scenarios; dashed lines mark per-scenario means.",
            "scenario_baf_boxplot": (
                "Per-scenario BAF boxplots for core scenarios only (median, IQR, outliers). "
                "OFAT variants are shown separately."
            ),
            "scenario_baf_boxplot_ofat": "Separate BAF boxplots for OFAT subscenarios to avoid overcrowding.",
            "scenario_baf_hist_grid": (
                "Small-multiple histograms with fixed BAF bins and per-panel y-scale: "
                "each panel shows one scenario distribution."
            ),
            "scenario_baf_mean_iqr": "Scenario mean BAF with interquartile range as asymmetric error bars.",
            "scenario_baf_mean_ofat_curves": "OFAT sensitivity curves: mean BAF vs varied parameter value by base scenario.",
            "interaction_mean_baf": "2D interaction heatmap of mean BAF for top influential parameter pair.",
            "interaction_catastrophic": "2D interaction heatmap of catastrophic probability for top influential parameter pair.",
        }
        for fig_path in figures:
            rel = fig_path.relative_to(output_dir)
            stem = fig_path.stem
            note = figure_notes.get(stem, "")
            if not note:
                for prefix, text in figure_notes.items():
                    if stem.startswith(prefix):
                        note = text
                        break
            if note:
                md_lines.append(f"- {fig_path.stem}: {note}")
            md_lines.append(f"![{fig_path.stem}]({rel.as_posix()})")

    md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    html_lines = [
        "<html><head><meta charset='utf-8'><title>Forest fire experiments report</title></head><body>",
        "<h1>Forest fire experiments report</h1>",
        "<h2>Overall</h2>",
        "<ul>",
        f"<li>Total runs: {summary.overall['runs_total']}</li>",
        (
            "<li>Mean burned area fraction (all / uncensored): "
            f"{summary.overall['baf_mean_all']:.4f} / {summary.overall['baf_mean_uncensored']:.4f}</li>"
        ),
        (
            "<li>Mean auc_normalized (all / uncensored): "
            f"{summary.overall['auc_normalized_mean_all']:.4f} / {summary.overall['auc_normalized_mean_uncensored']:.4f}</li>"
        ),
        (
            "<li>Mean time_to_extinguish (all / uncensored): "
            f"{summary.overall['time_to_extinguish_mean_all']:.4f} / "
            f"{summary.overall['time_to_extinguish_mean_uncensored']:.4f}</li>"
        ),
        (
            "<li>Survival median time_to_extinguish (KM, right-censored by max_steps): "
            f"{summary.overall['time_to_extinguish_survival_median']:.4f} "
            f"(reached={summary.overall['time_to_extinguish_survival_median_reached']})</li>"
        ),
        (
            "<li>Survival probability P(TTE &gt; 200): "
            f"{float(overall_surv_probs.get('200', 0.0)):.4f}</li>"
        ),
        (
            "<li>Critical share (all / uncensored): "
            f"{summary.overall['critical_mean_all']:.4f} / {summary.overall['critical_mean_uncensored']:.4f}</li>"
        ),
        (
            "<li>BAF quantiles p25/p50/p75/p95: "
            f"{summary.overall['baf_p25']:.4f} / {summary.overall['baf_p50']:.4f} / "
            f"{summary.overall['baf_p75']:.4f} / {summary.overall['baf_p95']:.4f}</li>"
        ),
        f"<li>Burned area p95/p99: {summary.overall['baf_p95']:.4f} / {summary.overall['baf_p99']:.4f}</li>",
        f"<li>Critical BAF threshold used: {summary.overall['critical_baf_threshold']:.4f}</li>",
        (
            f"<li>Catastrophic probability (baf &gt;= {summary.overall['critical_baf_threshold']:.4f}): "
            f"{summary.overall['catastrophic_probability']:.4f}</li>"
        ),
        f"<li>Scenario ranking metric: {summary.overall['scenario_ranking_metric']}</li>",
        (
            f"<li>Censored runs (truncated by max_steps): {summary.overall['censored_runs_count']} "
            f"({summary.overall['censored_runs_share']:.4f})</li>"
        ),
        (
            "<li>Pairwise significance tests: "
            f"{summary.overall.get('pairwise_significance_tests', {}).get('baf', {}).get('significant_bh_005', 0)} "
            f"/ {summary.overall.get('pairwise_significance_tests', {}).get('baf', {}).get('pairs_total', 0)} "
            "significant pairs for baf; "
            f"{summary.overall.get('pairwise_significance_tests', {}).get('auc_normalized', {}).get('significant_bh_005', 0)} "
            f"/ {summary.overall.get('pairwise_significance_tests', {}).get('auc_normalized', {}).get('pairs_total', 0)} "
            "for auc_normalized (BH q&lt;=0.05).</li>"
        ),
        (
            "<li>Note: censored runs can bias metrics: fire_duration and AUC are typically underestimated, "
            "while BAF-related risk can be understated when fire is still active at truncation.</li>"
        ),
        "</ul>",
        f"<h2>Worst scenarios by {ranking_metric_label}</h2><ol>",
    ]
    for name, score in top_worst:
        html_lines.append(f"<li>{name}: {score:.4f}</li>")
    html_lines.append("</ol>")
    if censoring_audit:
        html_lines.append("<h2>Censoring max_steps bias audit</h2><ul>")
        html_lines.append(
            "<li>Target rule: censored_share &lt; "
            f"{float(censoring_audit.get('target_censored_share', 0.0)):.4f}</li>"
        )
        html_lines.append(f"<li>Initial max_steps: {int(censoring_audit.get('initial_max_steps', 0))}</li>")
        html_lines.append(f"<li>Final max_steps: {int(censoring_audit.get('final_max_steps', 0))}</li>")
        html_lines.append(f"<li>Stop reason: {str(censoring_audit.get('stop_reason', 'n/a'))}</li>")
        html_lines.append("</ul>")
        for round_info in censoring_audit.get("rounds", []):
            html_lines.append(
                "<h3>Round "
                f"{int(round_info.get('round', 0))}: max_steps "
                f"{int(round_info.get('from_max_steps', 0))} -&gt; {int(round_info.get('to_max_steps', 0))}</h3>"
            )
            html_lines.append(
                "<p>Re-run scenarios: "
                f"{', '.join(round_info.get('rerun_scenarios', [])) or 'none'}</p>"
            )
            html_lines.append("<ul>")
            for scenario_delta in round_info.get("scenario_deltas", []):
                html_lines.append(
                    "<li>"
                    f"{scenario_delta['scenario']}: censored_share "
                    f"{float(scenario_delta['before_censored_share']):.4f} -&gt; "
                    f"{float(scenario_delta['after_censored_share']):.4f}; "
                    f"baf_mean_all {float(scenario_delta['before_baf_mean_all']):.4f} -&gt; "
                    f"{float(scenario_delta['after_baf_mean_all']):.4f}; "
                    f"auc_normalized_mean_all {float(scenario_delta['before_auc_normalized_mean_all']):.4f} -&gt; "
                    f"{float(scenario_delta['after_auc_normalized_mean_all']):.4f}"
                    "</li>"
                )
            html_lines.append("</ul>")
    html_lines.append("<h2>Absolute KPI ranking</h2>")
    html_lines.append("<h3>Mean burned area fraction (absolute, point estimate)</h3><ol>")
    for name, score in top_worst_abs_baf:
        html_lines.append(f"<li>{name}: {score:.4f}</li>")
    html_lines.append("</ol><h3>KPI comparison by scenario (all / uncensored)</h3><ul>")
    for name in sorted_scenario_names:
        stats = summary.by_scenario[name]
        censoring_note = (
            " ⚠️ reliability: time_to_extinguish/AUC may be less reliable; consider larger max_steps."
            if float(stats.get("censored_share", 0.0)) >= 0.06
            else ""
        )
        html_lines.append(
            "<li>"
            f"{name}: baf={stats['baf_mean_all']:.4f}/{stats['baf_mean_uncensored']:.4f}, "
            f"auc_normalized={stats['auc_normalized_mean_all']:.4f}/{stats['auc_normalized_mean_uncensored']:.4f}, "
            f"time_to_extinguish={stats['time_to_extinguish_mean_all']:.4f}/{stats['time_to_extinguish_mean_uncensored']:.4f}, "
            f"critical={stats['critical_mean_all']:.4f}/{stats['critical_mean_uncensored']:.4f}, "
            f"censored_share={stats['censored_share']:.4f}, "
            f"baf_q(p25/p50/p75/p95)={stats['baf_p25']:.4f}/{stats['baf_p50']:.4f}/{stats['baf_p75']:.4f}/{stats['baf_p95']:.4f}"
            f"{censoring_note}</li>"
        )
    html_lines.append("</ul>")
    if elevated_censoring:
        html_lines.append("<h3>Censoring reliability flags</h3>")
        html_lines.append(
            "<p>Scenarios with censored_share &gt;= 0.06 should be interpreted with care for time_to_extinguish/AUC.</p>"
        )
        html_lines.append("<ul>")
        for name, share in elevated_censoring:
            html_lines.append(f"<li>{name}: censored_share={share:.4f}</li>")
        html_lines.append("</ul>")
    html_lines.append("<h3>Time-to-extinguish survival KPI (right-censored by max_steps)</h3><ul>")
    html_lines.append(
        "<li>Interpret time via survival metrics (KM): median reflects extinction-time distribution robustly under censoring.</li>"
    )
    html_lines.append(
        "<li>Overall median TTE: "
        f"{summary.overall['time_to_extinguish_survival_median']:.4f} "
        f"(reached={summary.overall['time_to_extinguish_survival_median_reached']}, "
        f"lower_bound={summary.overall['time_to_extinguish_survival_median_lower_bound']:.4f})</li>"
    )
    html_lines.append(
        "<li>Overall P(TTE &gt; 200): "
        f"{float(overall_surv_probs.get('200', 0.0)):.4f}</li>"
    )
    html_lines.append("<li>Highest persistence scenarios by P(TTE &gt; 200):</li><ul>")
    for name, surv_200, median_tte, median_reached in top_persistent_by_200:
        html_lines.append(
            f"<li>{name}: P(TTE&gt;200)={surv_200:.4f}, median={median_tte:.4f} (reached={median_reached})</li>"
        )
    html_lines.append("</ul></ul>")
    html_lines.append("<h3>Mean burned area fraction (95% bootstrap CI)</h3><ol>")
    for name, baf_mean, ci_low, ci_high in top_worst_abs_baf_with_ci:
        html_lines.append(f"<li>{name}: {baf_mean:.4f} (95% CI: {ci_low:.4f}..{ci_high:.4f})</li>")
    html_lines.append("</ol><h3>Conservative risk ranking (mean BAF upper 95% CI bound)</h3><ol>")
    for name, baf_mean, ci_low, ci_high in top_worst_conservative_baf:
        html_lines.append(
            f"<li>{name}: upper_ci={ci_high:.4f} (mean={baf_mean:.4f}, 95% CI: {ci_low:.4f}..{ci_high:.4f})</li>"
        )
    html_lines.append("</ol><h3>Mean AUC (absolute)</h3><ol>")
    for name, score in top_worst_abs_auc:
        html_lines.append(f"<li>{name}: {score:.4f}</li>")
    html_lines.append("</ol>")
    html_lines.append("<h2>Normalized KPI ranking</h2>")
    html_lines.append("<h3>Mean peak_fire_fraction (normalized)</h3><ol>")
    for name, score in top_worst_norm_peak:
        html_lines.append(f"<li>{name}: {score:.4f}</li>")
    html_lines.append("</ol>")
    html_lines.append("<h2>Composite risk ranking</h2>")
    html_lines.append("<h3>Mean composite risk score (normalized, 95% bootstrap CI)</h3><ol>")
    for name, score, ci_low, ci_high in top_worst_composite_risk:
        html_lines.append(f"<li>{name}: {score:.4f} (95% CI: {ci_low:.4f}..{ci_high:.4f})</li>")
    html_lines.append(f"</ol><h3>{ranking_metric_label}</h3><ol>")
    for name, score in top_worst:
        html_lines.append(f"<li>{name}: {score:.4f}</li>")
    html_lines.append("</ol><h2>Scenario pairwise significance tests</h2>")
    html_lines.append(
        "<p>Method: two-sided permutation test on mean differences "
        f"({summary.overall.get('pairwise_significance_permutations', 0)} resamples), "
        "Benjamini–Hochberg correction, and Cliff's delta effect size.</p>"
    )
    html_lines.append("<h3>baf</h3><ul>")
    for item in top_pairwise_baf:
        html_lines.append(
            "<li>"
            f"{item['scenario_a']} vs {item['scenario_b']}: "
            f"mean_diff={float(item['mean_diff']):.4f}, "
            f"p={float(item['p_value']):.4f}, q={float(item['p_value_adj']):.4f}, "
            f"significant={bool(item['significant_bh_005'])}, "
            f"cliffs_delta={float(item['effect_cliffs_delta']):.4f} ({item['effect_label']})"
            "</li>"
        )
    html_lines.append("</ul><h3>auc_normalized</h3><ul>")
    for item in top_pairwise_auc_norm:
        html_lines.append(
            "<li>"
            f"{item['scenario_a']} vs {item['scenario_b']}: "
            f"mean_diff={float(item['mean_diff']):.4f}, "
            f"p={float(item['p_value']):.4f}, q={float(item['p_value_adj']):.4f}, "
            f"significant={bool(item['significant_bh_005'])}, "
            f"cliffs_delta={float(item['effect_cliffs_delta']):.4f} ({item['effect_label']})"
            "</li>"
        )
    html_lines.append("</ul>")
    html_lines.append("<h2>Global parameter sensitivity</h2>")
    html_lines.append(
        "<p>Purpose: estimates the overall influence of simultaneously varied parameters and their interactions "
        "across the experiment design. Use this separately from OFAT sensitivity, which reports local one-factor trends.</p>"
    )
    html_lines.append(
        "<p>Report inputs: continuous_param_correlations, binary_param_effects, and interaction_surface summaries "
        "computed from the full run table.</p>"
    )
    html_lines.append("<h3>continuous_param_correlations (uncontrolled)</h3>")
    html_lines.append(
        "<p>Note: global Pearson correlations for continuous params; includes r, CI, p, BH q, and q&lt;=0.05 flag."
        f" Ranking mode: {sensitivity_ranking}.</p><ul>"
    )
    for item in top_continuous_corr_uncontrolled:
        html_lines.append(
            "<li>"
            f"{item['param_key']} vs {item['metric_key']}: "
            f"r={float(item['r']):.4f}, 95% CI {float(item['r_ci_low']):.4f}..{float(item['r_ci_high']):.4f}, "
            f"p={_format_p_value(float(item['p_value']))}, q={_format_p_value(float(item['q_value']))}, "
            f"q&lt;=0.05={bool(item['q_le_005'])}</li>"
        )
    html_lines.append("</ul>")
    html_lines.append("<h3>continuous_param_correlations (controlled by scenario)</h3>")
    html_lines.append(f"<p>Method: within-scenario demeaning (scenario fixed-effects style). Ranking mode: {sensitivity_ranking}.</p><ul>")
    for item in top_continuous_corr_controlled:
        html_lines.append(
            "<li>"
            f"{item['param_key']} vs {item['metric_key']}: "
            f"r={float(item['r']):.4f}, 95% CI {float(item['r_ci_low']):.4f}..{float(item['r_ci_high']):.4f}, "
            f"p={_format_p_value(float(item['p_value']))}, q={_format_p_value(float(item['q_value']))}, "
            f"q&lt;=0.05={bool(item['q_le_005'])}</li>"
        )
    html_lines.append("</ul>")
    html_lines.append("<h3>binary_param_effects</h3>")
    html_lines.append(
        "<p>For binary params: mean(True)-mean(False), plus point-biserial correlation with 95% CI.</p><ul>"
    )
    for pkey, mkey, mean_diff, corr, ci_low, ci_high in top_binary_effects:
        html_lines.append(
            f"<li>{pkey} vs {mkey}: mean_diff={mean_diff:.4f}, "
            f"point_biserial_r={corr:.4f}, 95% CI {ci_low:.4f}..{ci_high:.4f}</li>"
        )
    html_lines.append("</ul>")
    html_lines.append("<h2>Scenario-local top parameter-metric correlations</h2>")
    for scenario_name in sorted_scenario_names:
        scenario_corr = summary.correlations_by_scenario.get(scenario_name)
        diag = summary.correlations_by_scenario_diagnostics.get(scenario_name, {})
        runs = int(diag.get("runs", 0))
        non_constant_param_count = int(diag.get("non_constant_param_count", 0))
        total_param_count = int(diag.get("total_param_count", 0))
        min_runs = int(diag.get("min_runs_required", 5))
        constant_param_keys = list(diag.get("constant_param_keys", []))
        html_lines.append(f"<h3>{scenario_name}</h3>")
        if scenario_corr:
            if non_constant_param_count == 0:
                html_lines.append(
                    "<p>⚠️ Correlation is weakly identified: all param_* are constant "
                    f"({runs} runs, varying params: 0/{total_param_count}).</p>"
                )
            html_lines.append("<ul>")
            for item in _sort_correlations(scenario_corr, ranking_mode=sensitivity_ranking, top_n=5):
                html_lines.append(
                    "<li>"
                    f"{item['param_key']} vs {item['metric_key']}: "
                    f"r={float(item['r']):.4f}, 95% CI {float(item['r_ci_low']):.4f}..{float(item['r_ci_high']):.4f}, "
                    f"p={_format_p_value(float(item['p_value']))}, q={_format_p_value(float(item['q_value']))}, "
                    f"q&lt;=0.05={bool(item['q_le_005'])}</li>"
                )
            html_lines.append("</ul>")
        else:
            html_lines.append(
                (
                    "<p>Not enough information for per-scenario correlation estimation "
                    f"(runs: {runs}, minimum: {min_runs}, varying params: "
                    f"{non_constant_param_count}/{total_param_count}).</p>"
                )
            )
        if constant_param_keys:
            shown_keys = ", ".join(constant_param_keys[:5])
            suffix = "..." if len(constant_param_keys) > 5 else ""
            html_lines.append(
                "<p>⚠️ Constant param_* in this scenario "
                f"({len(constant_param_keys)}): {shown_keys}{suffix}</p>"
            )

    html_lines.append("<h2>OFAT sensitivity (local one-factor trends)</h2>")
    html_lines.append(
        "<p>Purpose: estimates local trends around fixed base scenarios by changing one parameter at a time. "
        "Do not interpret OFAT slopes as global parameter importance when multiple parameters vary together.</p>"
    )
    html_lines.append(
        "<p>Grouping rule: OFAT scenarios are grouped by axis "
        "<code>&lt;base&gt; / &lt;varied_param&gt;</code> "
        "(e.g. <code>transition_low_humidity / humidity</code>).</p>"
    )
    html_lines.append("<p>Non-OFAT scenarios are excluded from this OFAT sensitivity section.</p>")
    html_lines.append("<p>For each OFAT axis: Pearson correlation and linear slope with 95% bootstrap CI.</p>")
    for family_name in sorted_family_names:
        family_corr = summary.correlations_by_family.get(family_name)
        diag = summary.correlations_by_family_diagnostics.get(family_name, {})
        runs = int(diag.get("runs", 0))
        non_constant_param_count = int(diag.get("non_constant_param_count", 0))
        total_param_count = int(diag.get("total_param_count", 0))
        min_runs = int(diag.get("min_runs_required", 5))
        html_lines.append(f"<h3>{family_name}</h3>")
        if bool(diag.get("ofat_excluded", False)):
            html_lines.append("<p>Excluded: scenario name does not match OFAT naming convention.</p>")
            continue
        if family_corr:
            html_lines.append("<ul>")
            for item in _sort_correlations(family_corr, ranking_mode=sensitivity_ranking, top_n=5):
                html_lines.append(
                    f"<li>{item['param_key']} vs {item['metric_key']}: "
                    f"r={float(item['r']):.4f} (95% CI {float(item['r_ci_low']):.4f}..{float(item['r_ci_high']):.4f}), "
                    f"p={_format_p_value(float(item['p_value']))}, q={_format_p_value(float(item['q_value']))}, "
                    f"q&lt;=0.05={bool(item['q_le_005'])}, "
                    f"slope={float(item['slope']):.4f} (95% CI {float(item['slope_ci_low']):.4f}..{float(item['slope_ci_high']):.4f})</li>"
                )
            html_lines.append("</ul>")
        else:
            html_lines.append(
                (
                    "<p>Not enough information for family-level sensitivity estimation "
                    f"(runs: {runs}, minimum: {min_runs}, varying params: "
                    f"{non_constant_param_count}/{total_param_count}).</p>"
                )
            )

    if summary.interaction_surfaces:
        html_lines.append("<h3>2D sensitivity (interaction surface)</h3>")
        html_lines.append(
            "<p>Built from two most influential continuous params for <code>baf</code> "
            "(by absolute global correlation) as the interaction_surface part of global sensitivity.</p>"
        )
        html_lines.append("<ul>")
        for surface in summary.interaction_surfaces:
            score = float(surface.get("interaction_score_baf", 0.0))
            if score >= 0.20:
                level = "strong"
            elif score >= 0.08:
                level = "moderate"
            else:
                level = "weak"
            html_lines.append(
                "<li>Pair "
                f"{surface.get('param_x', 'param_x')} × {surface.get('param_y', 'param_y')}: "
                f"coverage={float(surface.get('cell_coverage', 0.0)):.4f} "
                f"({int(surface.get('cells_observed', 0))}/{int(surface.get('cells_total', 0))} cells), "
                f"interaction_score_baf={score:.4f} ({level}).</li>"
            )
        html_lines.append("</ul>")
        html_lines.append(
            "<p>OFAT comparison hint: if OFAT curves look near-linear but interaction score is moderate/strong, "
            "this indicates non-additive interaction effects.</p>"
        )

    if figures:
        html_lines.append("<h2>Figures</h2>")
        figure_notes = {
            "baf_hist": "Global BAF histogram across all scenarios; dashed lines mark per-scenario means.",
            "scenario_baf_boxplot": "Per-scenario BAF boxplots for core scenarios only (median, IQR, outliers).",
            "scenario_baf_boxplot_ofat": "Separate BAF boxplots for OFAT subscenarios to avoid overcrowding.",
            "scenario_baf_hist_grid": (
                "Small-multiple histograms with fixed BAF bins and per-panel y-scale: "
                "each panel shows one scenario distribution."
            ),
            "scenario_baf_mean_iqr": "Scenario mean BAF with interquartile range as asymmetric error bars.",
            "scenario_baf_mean_ofat_curves": "OFAT sensitivity curves: mean BAF vs varied parameter value by base scenario.",
            "interaction_mean_baf": "2D interaction heatmap of mean BAF for top influential parameter pair.",
            "interaction_catastrophic": "2D interaction heatmap of catastrophic probability for top influential parameter pair.",
        }
        for fig_path in figures:
            rel = fig_path.relative_to(output_dir)
            stem = fig_path.stem
            note = figure_notes.get(stem, "")
            if not note:
                for prefix, text in figure_notes.items():
                    if stem.startswith(prefix):
                        note = text
                        break
            caption = f"<figcaption>{note}</figcaption>" if note else ""
            html_lines.append(
                f"<figure><img src='{rel.as_posix()}' alt='{fig_path.stem}' width='760'>{caption}</figure>"
            )

    html_lines.append("</body></html>")
    html_path.write_text("\n".join(html_lines) + "\n", encoding="utf-8")

    return md_path, html_path, figures
