from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

MetricTrend = Literal["higher_is_better", "higher_is_worse", "context_dependent"]


@dataclass(frozen=True)
class MetricDefinition:
    key: str
    formula: str
    units: str
    valid_range: str
    interpretation: MetricTrend
    scope: Literal["core", "derived"]


RUN_METRICS_SCHEMA: dict[str, MetricDefinition] = {
    "baf": MetricDefinition(
        key="baf",
        formula="min(1.0, final_counts['burnt'] / initial_tree_cells), якщо initial_tree_cells > 0, інакше 0.0",
        units="частка [0..1]",
        valid_range="0.0..1.0",
        interpretation="higher_is_worse",
        scope="core",
    ),
    "peak_fire_size": MetricDefinition(
        key="peak_fire_size",
        formula="max(burning_cells_t)",
        units="клітини",
        valid_range=">= 0",
        interpretation="higher_is_worse",
        scope="core",
    ),
    "time_to_peak": MetricDefinition(
        key="time_to_peak",
        formula="індекс першого входження max(burning_cells_t)",
        units="кроки (0-based індекс)",
        valid_range=">= 0",
        interpretation="context_dependent",
        scope="core",
    ),
    "fire_duration": MetricDefinition(
        key="fire_duration",
        formula="кількість кроків, де burning_cells_t[t] > 0",
        units="кроки",
        valid_range=">= 0",
        interpretation="higher_is_worse",
        scope="core",
    ),
    "auc": MetricDefinition(
        key="auc",
        formula="sum(burning_cells_t)",
        units="клітино-кроки",
        valid_range=">= 0",
        interpretation="higher_is_worse",
        scope="core",
    ),
    "burned_components": MetricDefinition(
        key="burned_components",
        formula="кількість 8-зв'язних компонент у бінарній масці вигорілих клітин burnt_mask",
        units="компоненти",
        valid_range=">= 0 (ціле)",
        interpretation="context_dependent",
        scope="core",
    ),
    "largest_cluster_share": MetricDefinition(
        key="largest_cluster_share",
        formula=(
            "largest_component_area / burnt_area, якщо burnt_area > 0, інакше 0.0; "
            "largest_component_area рахується для найбільшої 8-зв'язної компоненти"
        ),
        units="частка [0..1]",
        valid_range="0.0..1.0",
        interpretation="context_dependent",
        scope="core",
    ),
    "shape_complexity": MetricDefinition(
        key="shape_complexity",
        formula=(
            "perimeter_4n / burnt_area, якщо burnt_area > 0, інакше 0.0; "
            "perimeter_4n — кількість відкритих 4-сусідніх ребер у burnt_mask"
        ),
        units="безрозмірна (периметр/площа)",
        valid_range="0.0..4.0",
        interpretation="higher_is_worse",
        scope="core",
    ),
    "peak_fire_fraction": MetricDefinition(
        key="peak_fire_fraction",
        formula="peak_fire_size / initial_tree_cells, якщо initial_tree_cells > 0, інакше 0.0",
        units="частка [0..1]",
        valid_range="0.0..1.0",
        interpretation="higher_is_worse",
        scope="derived",
    ),
    "auc_normalized": MetricDefinition(
        key="auc_normalized",
        formula="auc / (initial_tree_cells * len(burning_cells_t)), якщо знаменник > 0, інакше 0.0 (де len(burning_cells_t) включає t0)",
        units="частка [0..1]",
        valid_range="0.0..1.0",
        interpretation="higher_is_worse",
        scope="derived",
    ),
    "time_to_extinguish": MetricDefinition(
        key="time_to_extinguish",
        formula=(
            "перший індекс t після старту вогню, де burning_cells_t[t] == 0; "
            "якщо загоряння не було — 0; якщо не згасло — останній індекс"
        ),
        units="кроки (0-based індекс)",
        valid_range=">= 0",
        interpretation="higher_is_worse",
        scope="derived",
    ),
    "max_spread_rate": MetricDefinition(
        key="max_spread_rate",
        formula="max(0, max_t(burning_cells_t[t] - burning_cells_t[t-1]))",
        units="клітини/крок",
        valid_range=">= 0",
        interpretation="higher_is_worse",
        scope="derived",
    ),
    "steps_total": MetricDefinition(
        key="steps_total",
        formula="фактична кількість виконаних кроків симуляції",
        units="кроки",
        valid_range=">= 0",
        interpretation="context_dependent",
        scope="derived",
    ),
    "steps_total_or_fire_horizon": MetricDefinition(
        key="steps_total_or_fire_horizon",
        formula="нормалізатор часової шкали для auc_normalized у часових точках (за замовчуванням len(burning_cells_t), що включає t0; або зафіксований fire_horizon у тих самих одиницях)",
        units="часові точки (t0..tT)",
        valid_range=">= 0 (ціле)",
        interpretation="context_dependent",
        scope="derived",
    ),
    "auc_normalization_denominator": MetricDefinition(
        key="auc_normalization_denominator",
        formula="initial_tree_cells * len(burning_cells_t) (або initial_tree_cells * steps_total_or_fire_horizon, якщо використано фіксований горизонт у часових точках)",
        units="клітини * часові точки",
        valid_range=">= 0 (ціле)",
        interpretation="context_dependent",
        scope="derived",
    ),
    "critical": MetricDefinition(
        key="critical",
        formula="baf >= critical_baf_threshold",
        units="булеве значення",
        valid_range="{true, false}",
        interpretation="higher_is_worse",
        scope="derived",
    ),
}

# Backward-compatible alias for existing imports.
METRICS_SCHEMA = RUN_METRICS_SCHEMA


def metrics_keys(*, scope: Literal["all", "core", "derived"] = "all") -> list[str]:
    if scope == "all":
        return list(RUN_METRICS_SCHEMA.keys())
    return [key for key, definition in RUN_METRICS_SCHEMA.items() if definition.scope == scope]
