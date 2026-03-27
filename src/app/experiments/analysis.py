from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from random import Random
from statistics import mean
from typing import Any


@dataclass(frozen=True)
class AnalysisSummary:
    overall: dict[str, Any]
    by_scenario: dict[str, dict[str, Any]]
    scenario_ranking: list[tuple[str, float]]
    correlations: list[tuple[str, str, float]]


def _percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = int((len(ordered) - 1) * q)
    return float(ordered[idx])


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


def analyze_results(rows: list[dict[str, Any]], *, ranking_metric: str = "auc_normalized_mean") -> AnalysisSummary:
    by_scenario: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_scenario.setdefault(str(row["scenario"]), []).append(row)

    baf_values = [float(row.get("baf", 0.0)) for row in rows]
    overall = {
        "runs_total": len(rows),
        "baf_mean": float(mean(baf_values)) if baf_values else 0.0,
        "baf_p95": _percentile(baf_values, 0.95),
        "baf_p99": _percentile(baf_values, 0.99),
        "catastrophic_probability": float(sum(v >= 0.8 for v in baf_values) / len(baf_values)) if baf_values else 0.0,
        "scenario_ranking_metric": ranking_metric,
    }

    scenario_stats: dict[str, dict[str, Any]] = {}
    for scenario_name, items in by_scenario.items():
        local_baf = [float(item.get("baf", 0.0)) for item in items]
        local_peak = [float(item.get("peak_fire_size", 0.0)) for item in items]
        local_auc = [float(item.get("auc", 0.0)) for item in items]
        local_peak_norm = [float(item.get("peak_fire_fraction", 0.0)) for item in items]
        local_auc_norm = [float(item.get("auc_normalized", 0.0)) for item in items]
        baf_mean_ci_low, baf_mean_ci_high = _bootstrap_mean_ci(local_baf, confidence=0.95)
        scenario_stats[scenario_name] = {
            "runs": len(items),
            "baf_mean": float(mean(local_baf)) if local_baf else 0.0,
            "baf_mean_ci_low": baf_mean_ci_low,
            "baf_mean_ci_high": baf_mean_ci_high,
            "baf_p95": _percentile(local_baf, 0.95),
            "peak_fire_size_mean": float(mean(local_peak)) if local_peak else 0.0,
            "auc_mean": float(mean(local_auc)) if local_auc else 0.0,
            "peak_fire_fraction_mean": float(mean(local_peak_norm)) if local_peak_norm else 0.0,
            "auc_normalized_mean": float(mean(local_auc_norm)) if local_auc_norm else 0.0,
            "critical_count": int(sum(bool(item.get("critical", False)) for item in items)),
            "max_spread_rate_mean": float(mean(float(item.get("max_spread_rate", 0.0)) for item in items)),
            "time_to_extinguish_mean": float(mean(float(item.get("time_to_extinguish", 0.0)) for item in items)),
        }

    ranking = sorted(
        ((name, float(stats.get(ranking_metric, 0.0))) for name, stats in scenario_stats.items()),
        key=lambda x: x[1],
        reverse=True,
    )

    correlations: list[tuple[str, str, float]] = []
    numeric_param_keys = sorted({key for row in rows for key in row if key.startswith("param_") and isinstance(row[key], (int, float))})
    metric_keys = ["baf", "peak_fire_size", "fire_duration", "max_spread_rate", "time_to_extinguish"]

    for pkey in numeric_param_keys:
        px = [float(row.get(pkey, 0.0)) for row in rows]
        p_mean = mean(px) if px else 0.0
        p_std = (sum((x - p_mean) ** 2 for x in px) / len(px)) ** 0.5 if px else 0.0
        if p_std == 0:
            continue
        for mkey in metric_keys:
            my = [float(row.get(mkey, 0.0)) for row in rows]
            m_mean = mean(my) if my else 0.0
            m_std = (sum((y - m_mean) ** 2 for y in my) / len(my)) ** 0.5 if my else 0.0
            if m_std == 0:
                continue
            cov = sum((x - p_mean) * (y - m_mean) for x, y in zip(px, my)) / len(px)
            corr = cov / (p_std * m_std)
            correlations.append((pkey, mkey, float(corr)))

    correlations.sort(key=lambda item: abs(item[2]), reverse=True)
    return AnalysisSummary(overall=overall, by_scenario=scenario_stats, scenario_ranking=ranking, correlations=correlations[:10])


def _save_plots(rows: list[dict[str, Any]], figures_dir: Path) -> list[Path]:
    figures_dir.mkdir(parents=True, exist_ok=True)
    generated: list[Path] = []
    try:
        import matplotlib.pyplot as plt
    except Exception:
        return generated

    baf_values = [float(r.get("baf", 0.0)) for r in rows]
    fig = plt.figure(figsize=(6, 4))
    plt.hist(baf_values, bins=20)
    plt.title("Distribution of burned area fraction")
    plt.xlabel("baf")
    plt.ylabel("count")
    hist_path = figures_dir / "baf_hist.png"
    fig.tight_layout()
    fig.savefig(hist_path)
    plt.close(fig)
    generated.append(hist_path)

    grouped: dict[str, list[float]] = {}
    for row in rows:
        grouped.setdefault(str(row["scenario"]), []).append(float(row.get("baf", 0.0)))

    labels = sorted(grouped.keys())
    values = [grouped[label] for label in labels]
    if values:
        fig = plt.figure(figsize=(7, 4))
        plt.boxplot(values, tick_labels=labels)
        plt.title("Scenario comparison by burned area fraction")
        plt.ylabel("baf")
        box_path = figures_dir / "scenario_baf_boxplot.png"
        fig.tight_layout()
        fig.savefig(box_path)
        plt.close(fig)
        generated.append(box_path)

    return generated


def generate_report(rows: list[dict[str, Any]], summary: AnalysisSummary, reports_dir: str | Path) -> tuple[Path, Path, list[Path]]:
    output_dir = Path(reports_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    figures = _save_plots(rows, output_dir / "figures")

    top_worst = summary.scenario_ranking[:3]
    top_worst_abs_baf = sorted(
        ((name, float(stats.get("baf_mean", 0.0))) for name, stats in summary.by_scenario.items()),
        key=lambda item: item[1],
        reverse=True,
    )[:3]
    top_worst_abs_baf_with_ci = sorted(
        (
            (
                name,
                float(stats.get("baf_mean", 0.0)),
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
                float(stats.get("baf_mean", 0.0)),
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
    top_corr = summary.correlations[:5]

    md_path = output_dir / "summary.md"
    html_path = output_dir / "summary.html"

    md_lines = [
        "# Forest fire experiments report",
        "",
        "## Overall",
        f"- Total runs: {summary.overall['runs_total']}",
        f"- Mean burned area fraction: {summary.overall['baf_mean']:.4f}",
        f"- Burned area p95/p99: {summary.overall['baf_p95']:.4f} / {summary.overall['baf_p99']:.4f}",
        f"- Catastrophic probability (baf >= 0.8): {summary.overall['catastrophic_probability']:.4f}",
        f"- Scenario ranking metric: {summary.overall['scenario_ranking_metric']}",
        "",
        "## Worst scenarios by normalized AUC (mean)",
    ]
    for name, score in top_worst:
        md_lines.append(f"- {name}: {score:.4f}")

    md_lines.append("")
    md_lines.append("## Absolute KPI ranking")
    md_lines.append("### Mean burned area fraction (absolute, point estimate)")
    for name, score in top_worst_abs_baf:
        md_lines.append(f"- {name}: {score:.4f}")
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
    md_lines.append("### Mean auc_normalized (normalized)")
    for name, score in top_worst:
        md_lines.append(f"- {name}: {score:.4f}")

    md_lines.append("")
    md_lines.append("## Top parameter-metric correlations")
    for pkey, mkey, corr in top_corr:
        md_lines.append(f"- {pkey} vs {mkey}: {corr:.4f}")

    if figures:
        md_lines.append("")
        md_lines.append("## Figures")
        for fig_path in figures:
            rel = fig_path.relative_to(output_dir)
            md_lines.append(f"![{fig_path.stem}]({rel.as_posix()})")

    md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    html_lines = [
        "<html><head><meta charset='utf-8'><title>Forest fire experiments report</title></head><body>",
        "<h1>Forest fire experiments report</h1>",
        "<h2>Overall</h2>",
        "<ul>",
        f"<li>Total runs: {summary.overall['runs_total']}</li>",
        f"<li>Mean burned area fraction: {summary.overall['baf_mean']:.4f}</li>",
        f"<li>Burned area p95/p99: {summary.overall['baf_p95']:.4f} / {summary.overall['baf_p99']:.4f}</li>",
        f"<li>Catastrophic probability (baf &gt;= 0.8): {summary.overall['catastrophic_probability']:.4f}</li>",
        f"<li>Scenario ranking metric: {summary.overall['scenario_ranking_metric']}</li>",
        "</ul>",
        "<h2>Worst scenarios by normalized AUC</h2><ol>",
    ]
    for name, score in top_worst:
        html_lines.append(f"<li>{name}: {score:.4f}</li>")
    html_lines.append("</ol>")
    html_lines.append("<h2>Absolute KPI ranking</h2>")
    html_lines.append("<h3>Mean burned area fraction (absolute, point estimate)</h3><ol>")
    for name, score in top_worst_abs_baf:
        html_lines.append(f"<li>{name}: {score:.4f}</li>")
    html_lines.append("</ol><h3>Mean burned area fraction (95% bootstrap CI)</h3><ol>")
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
    html_lines.append("</ol><h3>Mean auc_normalized (normalized)</h3><ol>")
    for name, score in top_worst:
        html_lines.append(f"<li>{name}: {score:.4f}</li>")
    html_lines.append("</ol><h2>Top parameter-metric correlations</h2><ul>")
    for pkey, mkey, corr in top_corr:
        html_lines.append(f"<li>{pkey} vs {mkey}: {corr:.4f}</li>")
    html_lines.append("</ul>")

    if figures:
        html_lines.append("<h2>Figures</h2>")
        for fig_path in figures:
            rel = fig_path.relative_to(output_dir)
            html_lines.append(f"<figure><img src='{rel.as_posix()}' alt='{fig_path.stem}' width='600'></figure>")

    html_lines.append("</body></html>")
    html_path.write_text("\n".join(html_lines) + "\n", encoding="utf-8")

    return md_path, html_path, figures
