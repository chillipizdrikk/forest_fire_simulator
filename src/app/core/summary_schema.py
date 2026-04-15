from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

AggregateTrend = Literal["higher_is_better", "higher_is_worse", "context_dependent"]


@dataclass(frozen=True)
class AggregateDefinition:
    key: str
    level: Literal["scenario", "overall"]
    formula: str
    units: str
    valid_range: str
    interpretation: AggregateTrend


SCENARIO_AGGREGATES_SCHEMA: dict[str, AggregateDefinition] = {
    "baf_mean_all": AggregateDefinition(
        key="baf_mean_all",
        level="scenario",
        formula="середнє baf по всіх прогонах сценарію",
        units="частка [0..1]",
        valid_range="0.0..1.0",
        interpretation="higher_is_worse",
    ),
    "baf_mean_uncensored": AggregateDefinition(
        key="baf_mean_uncensored",
        level="scenario",
        formula="середнє baf лише для прогонів без truncated_by_max_steps=True",
        units="частка [0..1]",
        valid_range="0.0..1.0",
        interpretation="higher_is_worse",
    ),
    "baf_mean_ci_low": AggregateDefinition(
        key="baf_mean_ci_low",
        level="scenario",
        formula="нижня межа 95% bootstrap CI для baf_mean_all",
        units="частка [0..1]",
        valid_range="0.0..1.0",
        interpretation="context_dependent",
    ),
    "baf_mean_ci_high": AggregateDefinition(
        key="baf_mean_ci_high",
        level="scenario",
        formula="верхня межа 95% bootstrap CI для baf_mean_all",
        units="частка [0..1]",
        valid_range="0.0..1.0",
        interpretation="context_dependent",
    ),
    "auc_normalized_mean_all": AggregateDefinition(
        key="auc_normalized_mean_all",
        level="scenario",
        formula="середнє auc_normalized по всіх прогонах сценарію",
        units="частка [0..1]",
        valid_range="0.0..1.0",
        interpretation="higher_is_worse",
    ),
    "auc_normalized_mean_uncensored": AggregateDefinition(
        key="auc_normalized_mean_uncensored",
        level="scenario",
        formula="середнє auc_normalized лише для uncensored-прогонів",
        units="частка [0..1]",
        valid_range="0.0..1.0",
        interpretation="higher_is_worse",
    ),
    "time_to_extinguish_mean_all": AggregateDefinition(
        key="time_to_extinguish_mean_all",
        level="scenario",
        formula="середнє time_to_extinguish по всіх прогонах сценарію",
        units="кроки",
        valid_range=">= 0",
        interpretation="higher_is_worse",
    ),
    "time_to_extinguish_mean_uncensored": AggregateDefinition(
        key="time_to_extinguish_mean_uncensored",
        level="scenario",
        formula="середнє time_to_extinguish лише для ignited+uncensored-прогонів",
        units="кроки",
        valid_range=">= 0",
        interpretation="higher_is_worse",
    ),
    "critical_mean_all": AggregateDefinition(
        key="critical_mean_all",
        level="scenario",
        formula="частка прогонів, де critical=True, по всіх прогонах сценарію",
        units="частка [0..1]",
        valid_range="0.0..1.0",
        interpretation="higher_is_worse",
    ),
    "critical_mean_uncensored": AggregateDefinition(
        key="critical_mean_uncensored",
        level="scenario",
        formula="частка прогонів, де critical=True, лише для uncensored-прогонів",
        units="частка [0..1]",
        valid_range="0.0..1.0",
        interpretation="higher_is_worse",
    ),
    "risk_score_mean": AggregateDefinition(
        key="risk_score_mean",
        level="scenario",
        formula="середнє risk_score_run по ignited-прогонах сценарію",
        units="частка [0..1]",
        valid_range="0.0..1.0",
        interpretation="higher_is_worse",
    ),
    "risk_score_mean_uncensored": AggregateDefinition(
        key="risk_score_mean_uncensored",
        level="scenario",
        formula="середнє risk_score_run лише для ignited+uncensored-прогонів сценарію",
        units="частка [0..1]",
        valid_range="0.0..1.0",
        interpretation="higher_is_worse",
    ),
    "risk_score_mean_ci_low": AggregateDefinition(
        key="risk_score_mean_ci_low",
        level="scenario",
        formula="нижня межа 95% bootstrap CI для risk_score_mean",
        units="частка [0..1]",
        valid_range="0.0..1.0",
        interpretation="context_dependent",
    ),
    "risk_score_mean_ci_high": AggregateDefinition(
        key="risk_score_mean_ci_high",
        level="scenario",
        formula="верхня межа 95% bootstrap CI для risk_score_mean",
        units="частка [0..1]",
        valid_range="0.0..1.0",
        interpretation="context_dependent",
    ),
}


OVERALL_AGGREGATES_SCHEMA: dict[str, AggregateDefinition] = {
    "baf_mean_all": AggregateDefinition(
        key="baf_mean_all",
        level="overall",
        formula="середнє baf по всіх прогонах експерименту",
        units="частка [0..1]",
        valid_range="0.0..1.0",
        interpretation="higher_is_worse",
    ),
    "baf_mean_uncensored": AggregateDefinition(
        key="baf_mean_uncensored",
        level="overall",
        formula="середнє baf по uncensored-прогонах експерименту",
        units="частка [0..1]",
        valid_range="0.0..1.0",
        interpretation="higher_is_worse",
    ),
    "auc_normalized_mean_all": AggregateDefinition(
        key="auc_normalized_mean_all",
        level="overall",
        formula="середнє auc_normalized по всіх прогонах експерименту",
        units="частка [0..1]",
        valid_range="0.0..1.0",
        interpretation="higher_is_worse",
    ),
    "auc_normalized_mean_uncensored": AggregateDefinition(
        key="auc_normalized_mean_uncensored",
        level="overall",
        formula="середнє auc_normalized по uncensored-прогонах експерименту",
        units="частка [0..1]",
        valid_range="0.0..1.0",
        interpretation="higher_is_worse",
    ),
    "critical_mean_all": AggregateDefinition(
        key="critical_mean_all",
        level="overall",
        formula="частка прогонів з critical=True по всьому експерименту",
        units="частка [0..1]",
        valid_range="0.0..1.0",
        interpretation="higher_is_worse",
    ),
    "critical_mean_uncensored": AggregateDefinition(
        key="critical_mean_uncensored",
        level="overall",
        formula="частка прогонів з critical=True лише для uncensored-прогонів",
        units="частка [0..1]",
        valid_range="0.0..1.0",
        interpretation="higher_is_worse",
    ),
}

