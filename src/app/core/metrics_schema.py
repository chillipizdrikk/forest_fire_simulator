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


METRICS_SCHEMA: dict[str, MetricDefinition] = {
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
        formula="auc / (initial_tree_cells * steps_total_or_fire_horizon), якщо знаменник > 0, інакше 0.0",
        units="частка [0..1]",
        valid_range="0.0..1.0",
        interpretation="higher_is_worse",
        scope="derived",
    ),
    "time_to_extinguish": MetricDefinition(
        key="time_to_extinguish",
        formula="перший індекс t після старту вогню, де burning_cells_t[t] == 0; якщо не згасло — останній індекс",
        units="кроки (0-based індекс)",
        valid_range=">= 0",
        interpretation="higher_is_worse",
        scope="derived",
    ),
    "max_spread_rate": MetricDefinition(
        key="max_spread_rate",
        formula="max_t(burning_cells_t[t] - burning_cells_t[t-1])",
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
        formula="нормалізатор часової шкали для auc_normalized (або фактичні steps_total, або зафіксований fire_horizon)",
        units="кроки",
        valid_range=">= 0",
        interpretation="context_dependent",
        scope="derived",
    ),
    "auc_normalization_denominator": MetricDefinition(
        key="auc_normalization_denominator",
        formula="initial_tree_cells * steps_total_or_fire_horizon",
        units="клітини * кроки",
        valid_range=">= 0",
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


def metrics_keys(*, scope: Literal["all", "core", "derived"] = "all") -> list[str]:
    if scope == "all":
        return list(METRICS_SCHEMA.keys())
    return [key for key, definition in METRICS_SCHEMA.items() if definition.scope == scope]
