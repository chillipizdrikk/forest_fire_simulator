from __future__ import annotations

from dataclasses import dataclass
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
    correlations: list[tuple[str, str, float, float, float]]
    controlled_correlations: list[tuple[str, str, float, float, float]]
    correlations_by_scenario: dict[str, list[tuple[str, str, float, float, float]]]
    correlations_by_scenario_diagnostics: dict[str, dict[str, Any]]
    correlations_by_family: dict[str, list[tuple[str, str, float, float, float, float, float, float]]]
    correlations_by_family_diagnostics: dict[str, dict[str, Any]]


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


def _mean_metric(rows: list[dict[str, Any]], key: str) -> float:
    values = [float(row.get(key, 0.0)) for row in rows]
    return float(mean(values)) if values else 0.0


def _critical_share(rows: list[dict[str, Any]]) -> float:
    return float(sum(bool(row.get("critical", False)) for row in rows) / len(rows)) if rows else 0.0


def analyze_results(
    rows: list[dict[str, Any]],
    *,
    ranking_metric: str = "auc_normalized_mean",
    critical_baf_threshold: float = 0.8,
    correlation_top_n: int = 10,
    scenario_correlation_min_runs: int = 5,
) -> AnalysisSummary:
    uncensored_all = _uncensored_rows(rows)
    global_tte_rows = uncensored_all if uncensored_all else rows
    global_tte_values = [float(row.get("time_to_extinguish", 0.0)) for row in global_tte_rows]
    global_tte_norm = _normalize_01(global_tte_values)
    global_tte_norm_by_run_id = {
        str(row.get("run_id", f"row_{idx}")): norm for idx, (row, norm) in enumerate(zip(global_tte_rows, global_tte_norm))
    }

    by_scenario: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_scenario.setdefault(str(row["scenario"]), []).append(row)

    baf_values = [float(row.get("baf", 0.0)) for row in rows]
    censored_runs_count = int(sum(bool(row.get("truncated_by_max_steps", False)) for row in rows))
    censored_runs_share = float(censored_runs_count / len(rows)) if rows else 0.0
    tte_min = min(global_tte_values) if global_tte_values else 0.0
    tte_max = max(global_tte_values) if global_tte_values else 0.0
    tte_span = tte_max - tte_min
    for row in rows:
        run_id = str(row.get("run_id", ""))
        if run_id in global_tte_norm_by_run_id:
            row["time_to_extinguish_global_norm"] = float(global_tte_norm_by_run_id[run_id])
            continue
        if tte_span == 0.0:
            row["time_to_extinguish_global_norm"] = 0.0
            continue
        tte_value = float(row.get("time_to_extinguish", 0.0))
        row["time_to_extinguish_global_norm"] = _clamp_01((tte_value - tte_min) / tte_span)
    overall = {
        "runs_total": len(rows),
        "baf_mean": float(mean(baf_values)) if baf_values else 0.0,
        "baf_mean_all": float(mean(baf_values)) if baf_values else 0.0,
        "baf_mean_uncensored": _mean_metric(uncensored_all, "baf"),
        "auc_normalized_mean": _mean_metric(rows, "auc_normalized"),
        "auc_normalized_mean_all": _mean_metric(rows, "auc_normalized"),
        "auc_normalized_mean_uncensored": _mean_metric(uncensored_all, "auc_normalized"),
        "time_to_extinguish_mean": _mean_metric(rows, "time_to_extinguish"),
        "time_to_extinguish_mean_all": _mean_metric(rows, "time_to_extinguish"),
        "time_to_extinguish_mean_uncensored": _mean_metric(uncensored_all, "time_to_extinguish"),
        "critical_mean_all": _critical_share(rows),
        "critical_mean_uncensored": _critical_share(uncensored_all),
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
        "time_to_extinguish_norm_scope": "uncensored_only" if uncensored_all else "all_runs",
        "time_to_extinguish_global_min": tte_min,
        "time_to_extinguish_global_max": tte_max,
    }

    scenario_stats: dict[str, dict[str, Any]] = {}
    for scenario_name, items in by_scenario.items():
        local_baf = [float(item.get("baf", 0.0)) for item in items]
        local_peak = [float(item.get("peak_fire_size", 0.0)) for item in items]
        local_auc = [float(item.get("auc", 0.0)) for item in items]
        local_peak_norm = [float(item.get("peak_fire_fraction", 0.0)) for item in items]
        local_auc_norm = [float(item.get("auc_normalized", 0.0)) for item in items]
        uncensored_items = _uncensored_rows(items)
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
            for baf, auc_norm, peak_norm, tte_global_norm in zip(
                local_baf, local_auc_norm, local_peak_norm, run_tte_global_norm
            )
        ]
        run_risk_scores_uncensored = [
            score
            for item, score in zip(items, run_risk_scores)
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
            "critical_count": int(sum(bool(item.get("critical", False)) for item in items)),
            "critical_mean_all": _critical_share(items),
            "critical_mean_uncensored": _critical_share(uncensored_items),
            "censored_share": float(sum(bool(item.get("truncated_by_max_steps", False)) for item in items) / len(items)),
            "max_spread_rate_mean": float(mean(float(item.get("max_spread_rate", 0.0)) for item in items)),
            "time_to_extinguish_mean": float(mean(float(item.get("time_to_extinguish", 0.0)) for item in items)),
            "time_to_extinguish_mean_all": float(mean(float(item.get("time_to_extinguish", 0.0)) for item in items)),
            "time_to_extinguish_mean_uncensored": _mean_metric(uncensored_items, "time_to_extinguish"),
            "risk_score_mean": float(mean(run_risk_scores)) if run_risk_scores else 0.0,
            "risk_score_mean_uncensored": (
                float(mean(run_risk_scores_uncensored)) if run_risk_scores_uncensored else 0.0
            ),
            "risk_score_mean_ci_low": risk_mean_ci_low,
            "risk_score_mean_ci_high": risk_mean_ci_high,
        }

    ranking = sorted(
        ((name, float(stats.get(ranking_metric, 0.0))) for name, stats in scenario_stats.items()),
        key=lambda x: x[1],
        reverse=True,
    )

    numeric_param_keys = sorted({key for row in rows for key in row if key.startswith("param_") and isinstance(row[key], (int, float))})
    metric_keys = ["baf", "peak_fire_size", "fire_duration", "max_spread_rate", "time_to_extinguish"]
    correlations = _collect_top_correlations(rows, numeric_param_keys, metric_keys, top_n=correlation_top_n)
    controlled_correlations = _collect_controlled_top_correlations(
        rows,
        by_scenario,
        numeric_param_keys,
        metric_keys,
        top_n=correlation_top_n,
    )
    correlations_by_scenario: dict[str, list[tuple[str, str, float, float, float]]] = {}
    correlations_by_scenario_diagnostics: dict[str, dict[str, Any]] = {}
    for scenario_name, scenario_rows in by_scenario.items():
        non_constant_params = _count_non_constant_params(scenario_rows, numeric_param_keys)
        constant_params = [pkey for pkey in numeric_param_keys if pkey not in non_constant_params]
        correlations_by_scenario_diagnostics[scenario_name] = {
            "runs": len(scenario_rows),
            "min_runs_required": scenario_correlation_min_runs,
            "non_constant_param_count": len(non_constant_params),
            "total_param_count": len(numeric_param_keys),
            "constant_param_keys": constant_params,
        }
        if len(scenario_rows) < scenario_correlation_min_runs:
            continue
        correlations_by_scenario[scenario_name] = _collect_top_correlations(
            scenario_rows,
            numeric_param_keys,
            metric_keys,
            top_n=correlation_top_n,
        )

    family_rows: dict[tuple[str, str], list[dict[str, Any]]] = {}
    non_ofat_family_rows: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        scenario_name = str(row.get("scenario", ""))
        parsed = _parse_ofat_scenario_name(scenario_name)
        if parsed:
            base_name, varied_param_name, _ = parsed
            family_rows.setdefault((base_name, varied_param_name), []).append(row)
        else:
            non_ofat_family_rows.setdefault(scenario_name, []).append(row)

    family_metric_keys = ["baf", "auc_normalized", "time_to_extinguish"]
    correlations_by_family: dict[str, list[tuple[str, str, float, float, float, float, float, float]]] = {}
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

        family_corrs: list[tuple[str, str, float, float, float, float, float, float]] = []
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
                family_corrs.append(
                    (pkey, mkey, corr, corr_ci_low, corr_ci_high, slope, slope_ci_low, slope_ci_high)
                )
        family_corrs.sort(key=lambda item: abs(item[2]), reverse=True)
        if family_corrs:
            correlations_by_family[family_name] = family_corrs[:correlation_top_n]

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
        correlations=correlations,
        controlled_correlations=controlled_correlations,
        correlations_by_scenario=correlations_by_scenario,
        correlations_by_scenario_diagnostics=correlations_by_scenario_diagnostics,
        correlations_by_family=correlations_by_family,
        correlations_by_family_diagnostics=correlations_by_family_diagnostics,
    )


def _collect_top_correlations(
    rows: list[dict[str, Any]],
    numeric_param_keys: list[str],
    metric_keys: list[str],
    *,
    top_n: int,
) -> list[tuple[str, str, float, float, float]]:
    correlations: list[tuple[str, str, float, float, float]] = []
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
            correlations.append((pkey, mkey, corr, ci_low, ci_high))
    correlations.sort(key=lambda item: abs(item[2]), reverse=True)
    return correlations[:top_n]


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
) -> list[tuple[str, str, float, float, float]]:
    scenario_means: dict[str, dict[str, float]] = {}
    keys_for_demean = numeric_param_keys + metric_keys
    for scenario_name, scenario_rows in by_scenario.items():
        scenario_means[scenario_name] = {}
        for key in keys_for_demean:
            values = [float(row.get(key, 0.0)) for row in scenario_rows]
            scenario_means[scenario_name][key] = float(mean(values)) if values else 0.0

    correlations: list[tuple[str, str, float, float, float]] = []
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
            correlations.append((pkey, mkey, corr, ci_low, ci_high))

    correlations.sort(key=lambda item: abs(item[2]), reverse=True)
    return correlations[:top_n]


def _parse_ofat_scenario_name(name: str) -> tuple[str, str, float] | None:
    """Parse OFAT names '<base>_<param>_<value_token>' with humidity encoded as percent."""
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

    value = numeric_value / 100.0 if param_name == "humidity" else numeric_value
    return base_name, param_name, value


def _save_plots(rows: list[dict[str, Any]], figures_dir: Path) -> list[Path]:
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

    return generated


def generate_report(rows: list[dict[str, Any]], summary: AnalysisSummary, reports_dir: str | Path) -> tuple[Path, Path, list[Path]]:
    output_dir = Path(reports_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    figures = _save_plots(rows, output_dir / "figures")

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
    top_corr_uncontrolled = summary.correlations[:5]
    top_corr_controlled = summary.controlled_correlations[:5]
    sorted_scenario_names = sorted(summary.by_scenario.keys())
    sorted_family_names = sorted(summary.correlations_by_family_diagnostics.keys())
    elevated_censoring = [
        (name, float(stats.get("censored_share", 0.0)))
        for name, stats in summary.by_scenario.items()
        if float(stats.get("censored_share", 0.0)) >= 0.06
    ]
    elevated_censoring.sort(key=lambda item: item[1], reverse=True)

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
            "- Note: censored runs can bias metrics: fire_duration and AUC are typically underestimated, "
            "while BAF-related risk can be understated when fire is still active at truncation."
        ),
        "",
        f"## Worst scenarios by {ranking_metric_label}",
    ]
    for name, score in top_worst:
        md_lines.append(f"- {name}: {score:.4f}")

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
    md_lines.append("## Top parameter-metric correlations (uncontrolled)")
    md_lines.append("- Note: these are global correlations without controlling for scenario.")
    for pkey, mkey, corr, ci_low, ci_high in top_corr_uncontrolled:
        md_lines.append(f"- {pkey} vs {mkey}: r={corr:.4f}, 95% CI {ci_low:.4f}..{ci_high:.4f}")
    md_lines.append("")
    md_lines.append("## Top parameter-metric correlations (controlled by scenario)")
    md_lines.append("- Method: within-scenario demeaning (scenario fixed-effects style).")
    for pkey, mkey, corr, ci_low, ci_high in top_corr_controlled:
        md_lines.append(f"- {pkey} vs {mkey}: r={corr:.4f}, 95% CI {ci_low:.4f}..{ci_high:.4f}")
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
            for pkey, mkey, corr, ci_low, ci_high in scenario_corr[:5]:
                md_lines.append(f"- {pkey} vs {mkey}: r={corr:.4f}, 95% CI {ci_low:.4f}..{ci_high:.4f}")
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
    md_lines.append("## Family-level parameter sensitivity (OFAT-aware)")
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
            for pkey, mkey, corr, corr_ci_low, corr_ci_high, slope, slope_ci_low, slope_ci_high in family_corr[:5]:
                md_lines.append(
                    f"- {pkey} vs {mkey}: r={corr:.4f} (95% CI {corr_ci_low:.4f}..{corr_ci_high:.4f}), "
                    f"slope={slope:.4f} (95% CI {slope_ci_low:.4f}..{slope_ci_high:.4f})"
                )
        else:
            md_lines.append(
                (
                    "- Not enough information for family-level sensitivity estimation "
                    f"(runs: {runs}, minimum: {min_runs}, varying params: "
                    f"{non_constant_param_count}/{total_param_count})."
                )
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
        }
        for fig_path in figures:
            rel = fig_path.relative_to(output_dir)
            note = figure_notes.get(fig_path.stem, "")
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
            "<li>Note: censored runs can bias metrics: fire_duration and AUC are typically underestimated, "
            "while BAF-related risk can be understated when fire is still active at truncation.</li>"
        ),
        "</ul>",
        f"<h2>Worst scenarios by {ranking_metric_label}</h2><ol>",
    ]
    for name, score in top_worst:
        html_lines.append(f"<li>{name}: {score:.4f}</li>")
    html_lines.append("</ol>")
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
    html_lines.append("</ol><h2>Top parameter-metric correlations (uncontrolled)</h2>")
    html_lines.append("<p>Note: these are global correlations without controlling for scenario.</p><ul>")
    for pkey, mkey, corr, ci_low, ci_high in top_corr_uncontrolled:
        html_lines.append(f"<li>{pkey} vs {mkey}: r={corr:.4f}, 95% CI {ci_low:.4f}..{ci_high:.4f}</li>")
    html_lines.append("</ul>")
    html_lines.append("<h2>Top parameter-metric correlations (controlled by scenario)</h2>")
    html_lines.append("<p>Method: within-scenario demeaning (scenario fixed-effects style).</p><ul>")
    for pkey, mkey, corr, ci_low, ci_high in top_corr_controlled:
        html_lines.append(f"<li>{pkey} vs {mkey}: r={corr:.4f}, 95% CI {ci_low:.4f}..{ci_high:.4f}</li>")
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
            for pkey, mkey, corr, ci_low, ci_high in scenario_corr[:5]:
                html_lines.append(f"<li>{pkey} vs {mkey}: r={corr:.4f}, 95% CI {ci_low:.4f}..{ci_high:.4f}</li>")
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

    html_lines.append("<h2>Family-level parameter sensitivity (OFAT-aware)</h2>")
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
            for pkey, mkey, corr, corr_ci_low, corr_ci_high, slope, slope_ci_low, slope_ci_high in family_corr[:5]:
                html_lines.append(
                    f"<li>{pkey} vs {mkey}: r={corr:.4f} (95% CI {corr_ci_low:.4f}..{corr_ci_high:.4f}), "
                    f"slope={slope:.4f} (95% CI {slope_ci_low:.4f}..{slope_ci_high:.4f})</li>"
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
        }
        for fig_path in figures:
            rel = fig_path.relative_to(output_dir)
            note = figure_notes.get(fig_path.stem, "")
            caption = f"<figcaption>{note}</figcaption>" if note else ""
            html_lines.append(
                f"<figure><img src='{rel.as_posix()}' alt='{fig_path.stem}' width='760'>{caption}</figure>"
            )

    html_lines.append("</body></html>")
    html_path.write_text("\n".join(html_lines) + "\n", encoding="utf-8")

    return md_path, html_path, figures
