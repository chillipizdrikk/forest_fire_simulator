from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
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


def analyze_results(rows: list[dict[str, Any]]) -> AnalysisSummary:
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
    }

    scenario_stats: dict[str, dict[str, Any]] = {}
    for scenario_name, items in by_scenario.items():
        local_baf = [float(item.get("baf", 0.0)) for item in items]
        scenario_stats[scenario_name] = {
            "runs": len(items),
            "baf_mean": float(mean(local_baf)) if local_baf else 0.0,
            "baf_p95": _percentile(local_baf, 0.95),
            "critical_count": int(sum(bool(item.get("critical", False)) for item in items)),
            "max_spread_rate_mean": float(mean(float(item.get("max_spread_rate", 0.0)) for item in items)),
            "time_to_extinguish_mean": float(mean(float(item.get("time_to_extinguish", 0.0)) for item in items)),
        }

    ranking = sorted(
        ((name, stats["baf_mean"]) for name, stats in scenario_stats.items()),
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
        "",
        "## Worst scenarios by mean burned area",
    ]
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
        "</ul>",
        "<h2>Worst scenarios</h2><ol>",
    ]
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
