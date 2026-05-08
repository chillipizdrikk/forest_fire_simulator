from __future__ import annotations

from pathlib import Path
from typing import Any

import re


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
    ofat_labels = [
        label for label in labels_all if _parse_ofat_scenario_name(label) is not None
    ]
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
                plt.axvline(
                    sum(local) / len(local),
                    linestyle="--",
                    linewidth=1.2,
                    alpha=0.7,
                    label=f"{label} mean",
                )
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
        fig, axes = plt.subplots(
            rows_n,
            cols,
            figsize=(4.6 * cols, 3.2 * rows_n),
            squeeze=False,
            sharex=True,
            sharey=False,
        )
        fixed_bins = [idx / 20 for idx in range(21)]
        for idx, label in enumerate(labels):
            ax = axes[idx // cols][idx % cols]
            local = grouped[label]
            ax.hist(
                local,
                bins=fixed_bins,
                color="#6bbf83",
                edgecolor="#f5f5f5",
                alpha=0.95,
                linewidth=0.8,
            )
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
        plt.errorbar(
            x, means, yerr=[lower_err, upper_err], fmt="o", capsize=4, color="#1f4e79"
        )
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
            ofat_by_base_and_param.setdefault((base_name, param_name), []).append(
                (value, local_mean)
            )

        if ofat_by_base_and_param:
            base_names = sorted({base for base, _ in ofat_by_base_and_param.keys()})
            fig, axes = plt.subplots(
                len(base_names),
                1,
                figsize=(8.4, max(3.2, 3.0 * len(base_names))),
                squeeze=False,
                sharey=True,
            )
            colors = {
                "humidity": "#2b8cbe",
                "wind_strength": "#e34a33",
                "temperature_c": "#31a354",
            }
            for row_index, base_name in enumerate(base_names):
                ax = axes[row_index][0]
                for param_name in ("humidity", "wind_strength", "temperature_c"):
                    pairs = sorted(
                        ofat_by_base_and_param.get((base_name, param_name), []),
                        key=lambda item: item[0],
                    )
                    if not pairs:
                        continue
                    xs = [item[0] for item in pairs]
                    ys = [item[1] for item in pairs]
                    ax.plot(
                        xs,
                        ys,
                        marker="o",
                        linewidth=1.8,
                        label=param_name,
                        color=colors[param_name],
                    )
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
            if (
                not x_values
                or not y_values
                or not mean_baf_grid
                or not catastrophic_grid
            ):
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
                im = plt.imshow(
                    baf_masked,
                    origin="lower",
                    aspect="auto",
                    vmin=0.0,
                    vmax=1.0,
                    cmap="YlOrRd",
                )
                plt.colorbar(im, label="mean baf")
                plt.xticks(
                    range(len(x_values)),
                    [f"{v:.3g}" for v in x_values],
                    rotation=30,
                    ha="right",
                )
                plt.yticks(range(len(y_values)), [f"{v:.3g}" for v in y_values])
                plt.xlabel(param_x)
                plt.ylabel(param_y)
                plt.title(f"2D interaction surface: mean BAF ({param_x} × {param_y})")
                baf_path = (
                    figures_dir / f"interaction_mean_baf_{param_x}_x_{param_y}.png"
                )
                fig.tight_layout()
                fig.savefig(baf_path)
                plt.close(fig)
                generated.append(baf_path)
            except Exception:
                pass

            try:
                _, crit_masked = _grid_to_array(catastrophic_grid)
                fig = plt.figure(figsize=(7.0, 5.2))
                im = plt.imshow(
                    crit_masked,
                    origin="lower",
                    aspect="auto",
                    vmin=0.0,
                    vmax=1.0,
                    cmap="magma",
                )
                plt.colorbar(im, label="catastrophic probability")
                plt.xticks(
                    range(len(x_values)),
                    [f"{v:.3g}" for v in x_values],
                    rotation=30,
                    ha="right",
                )
                plt.yticks(range(len(y_values)), [f"{v:.3g}" for v in y_values])
                plt.xlabel(param_x)
                plt.ylabel(param_y)
                plt.title(
                    f"2D interaction surface: catastrophic probability ({param_x} × {param_y})"
                )
                crit_path = (
                    figures_dir / f"interaction_catastrophic_{param_x}_x_{param_y}.png"
                )
                fig.tight_layout()
                fig.savefig(crit_path)
                plt.close(fig)
                generated.append(crit_path)
            except Exception:
                pass

    return generated
