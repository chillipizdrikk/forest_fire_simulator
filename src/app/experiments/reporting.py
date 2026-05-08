from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from src.app.experiments.analysis import _format_p_value, _sort_correlations
from src.app.experiments.plots import _save_plots

if TYPE_CHECKING:
    from src.app.experiments.analysis import AnalysisSummary


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
    figures = _save_plots(
        rows, output_dir / "figures", interaction_surfaces=summary.interaction_surfaces
    )

    top_worst = summary.scenario_ranking[:3]
    ranking_metric = str(
        summary.overall.get("scenario_ranking_metric", "auc_normalized_mean")
    )
    ranking_metric_labels = {
        "auc_normalized_mean": "Mean auc_normalized (normalized)",
        "peak_fire_fraction_mean": "Mean peak_fire_fraction (normalized)",
        "auc_mean": "Mean AUC (absolute)",
        "baf_mean": "Mean burned area fraction (absolute, point estimate)",
        "risk_score_mean": "Mean composite risk score (normalized)",
    }
    ranking_metric_label = ranking_metric_labels.get(
        ranking_metric, f"Mean {ranking_metric}"
    )
    top_worst_abs_baf = sorted(
        (
            (name, float(stats.get("baf_mean_all", 0.0)))
            for name, stats in summary.by_scenario.items()
        ),
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
        (
            (name, float(stats.get("auc_mean", 0.0)))
            for name, stats in summary.by_scenario.items()
        ),
        key=lambda item: item[1],
        reverse=True,
    )[:3]
    top_worst_norm_peak = sorted(
        (
            (name, float(stats.get("peak_fire_fraction_mean", 0.0)))
            for name, stats in summary.by_scenario.items()
        ),
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
    top_pairwise_auc_norm = summary.scenario_pairwise_significance.get(
        "auc_normalized", []
    )[:5]
    sorted_scenario_names = sorted(summary.by_scenario.keys())
    sorted_family_names = sorted(summary.correlations_by_family_diagnostics.keys())
    elevated_censoring = [
        (name, float(stats.get("censored_share", 0.0)))
        for name, stats in summary.by_scenario.items()
        if float(stats.get("censored_share", 0.0)) >= 0.06
    ]
    elevated_censoring.sort(key=lambda item: item[1], reverse=True)
    overall_surv_probs = dict(
        summary.overall.get("time_to_extinguish_survival_probabilities", {})
    )
    horizon_200_key = "200"
    top_persistent_by_200 = sorted(
        (
            (
                name,
                float(
                    stats.get("time_to_extinguish_survival_probabilities", {}).get(
                        horizon_200_key, 0.0
                    )
                ),
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
        md_lines.append(
            f"- Initial max_steps: {int(censoring_audit.get('initial_max_steps', 0))}"
        )
        md_lines.append(
            f"- Final max_steps: {int(censoring_audit.get('final_max_steps', 0))}"
        )
        md_lines.append(
            f"- Stop reason: {str(censoring_audit.get('stop_reason', 'n/a'))}"
        )
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
        md_lines.append(
            f"- {name}: {baf_mean:.4f} (95% CI: {ci_low:.4f}..{ci_high:.4f})"
        )
    md_lines.append("### Conservative risk ranking (mean BAF upper 95% CI bound)")
    for name, baf_mean, ci_low, ci_high in top_worst_conservative_baf:
        md_lines.append(
            f"- {name}: upper_ci={ci_high:.4f} (mean={baf_mean:.4f}, 95% CI: {ci_low:.4f}..{ci_high:.4f})"
        )
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
    md_lines.append(
        "- Note: these are global Pearson correlations for continuous params only."
    )
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
    md_lines.append(
        "- Method: within-scenario demeaning (scenario fixed-effects style)."
    )
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
    md_lines.append(
        "- For binary params: mean(True)-mean(False), plus point-biserial correlation with 95% CI."
    )
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
            for item in _sort_correlations(
                scenario_corr, ranking_mode=sensitivity_ranking, top_n=5
            ):
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
    md_lines.append(
        "- Non-OFAT scenarios are excluded from this OFAT sensitivity section."
    )
    md_lines.append(
        "- For each OFAT axis: Pearson correlation and linear slope with 95% bootstrap CI."
    )
    for family_name in sorted_family_names:
        family_corr = summary.correlations_by_family.get(family_name)
        diag = summary.correlations_by_family_diagnostics.get(family_name, {})
        runs = int(diag.get("runs", 0))
        non_constant_param_count = int(diag.get("non_constant_param_count", 0))
        total_param_count = int(diag.get("total_param_count", 0))
        min_runs = int(diag.get("min_runs_required", 5))
        md_lines.append(f"### {family_name}")
        if bool(diag.get("ofat_excluded", False)):
            md_lines.append(
                "- Excluded: scenario name does not match OFAT naming convention."
            )
            continue
        if family_corr:
            for item in _sort_correlations(
                family_corr, ranking_mode=sensitivity_ranking, top_n=5
            ):
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
        html_lines.append(
            f"<li>Initial max_steps: {int(censoring_audit.get('initial_max_steps', 0))}</li>"
        )
        html_lines.append(
            f"<li>Final max_steps: {int(censoring_audit.get('final_max_steps', 0))}</li>"
        )
        html_lines.append(
            f"<li>Stop reason: {str(censoring_audit.get('stop_reason', 'n/a'))}</li>"
        )
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
    html_lines.append(
        "<h3>Mean burned area fraction (absolute, point estimate)</h3><ol>"
    )
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
    html_lines.append(
        "<h3>Time-to-extinguish survival KPI (right-censored by max_steps)</h3><ul>"
    )
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
        html_lines.append(
            f"<li>{name}: {baf_mean:.4f} (95% CI: {ci_low:.4f}..{ci_high:.4f})</li>"
        )
    html_lines.append(
        "</ol><h3>Conservative risk ranking (mean BAF upper 95% CI bound)</h3><ol>"
    )
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
    html_lines.append(
        "<h3>Mean composite risk score (normalized, 95% bootstrap CI)</h3><ol>"
    )
    for name, score, ci_low, ci_high in top_worst_composite_risk:
        html_lines.append(
            f"<li>{name}: {score:.4f} (95% CI: {ci_low:.4f}..{ci_high:.4f})</li>"
        )
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
    html_lines.append(
        f"<p>Method: within-scenario demeaning (scenario fixed-effects style). Ranking mode: {sensitivity_ranking}.</p><ul>"
    )
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
            for item in _sort_correlations(
                scenario_corr, ranking_mode=sensitivity_ranking, top_n=5
            ):
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
    html_lines.append(
        "<p>Non-OFAT scenarios are excluded from this OFAT sensitivity section.</p>"
    )
    html_lines.append(
        "<p>For each OFAT axis: Pearson correlation and linear slope with 95% bootstrap CI.</p>"
    )
    for family_name in sorted_family_names:
        family_corr = summary.correlations_by_family.get(family_name)
        diag = summary.correlations_by_family_diagnostics.get(family_name, {})
        runs = int(diag.get("runs", 0))
        non_constant_param_count = int(diag.get("non_constant_param_count", 0))
        total_param_count = int(diag.get("total_param_count", 0))
        min_runs = int(diag.get("min_runs_required", 5))
        html_lines.append(f"<h3>{family_name}</h3>")
        if bool(diag.get("ofat_excluded", False)):
            html_lines.append(
                "<p>Excluded: scenario name does not match OFAT naming convention.</p>"
            )
            continue
        if family_corr:
            html_lines.append("<ul>")
            for item in _sort_correlations(
                family_corr, ranking_mode=sensitivity_ranking, top_n=5
            ):
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
