from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class ScenarioDefinition:
    name: str
    params: dict[str, Any]


def load_scenarios(path: str | Path) -> tuple[dict[str, Any], list[ScenarioDefinition]]:
    content = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(content, dict):
        raise ValueError("Scenario file must contain a mapping at root")

    defaults = content.get("defaults", {})
    if not isinstance(defaults, dict):
        raise ValueError("defaults must be a mapping")

    raw_scenarios = content.get("scenarios", [])
    if not isinstance(raw_scenarios, list):
        raise ValueError("scenarios must be a list")

    scenarios: list[ScenarioDefinition] = []
    for index, raw in enumerate(raw_scenarios):
        if not isinstance(raw, dict):
            raise ValueError(f"scenarios[{index}] must be a mapping")
        name = raw.get("name")
        params = raw.get("params", {})
        if not isinstance(name, str) or not name.strip():
            raise ValueError(f"scenarios[{index}] requires non-empty name")
        if not isinstance(params, dict):
            raise ValueError(f"scenarios[{index}].params must be a mapping")
        scenarios.append(ScenarioDefinition(name=name.strip(), params=params))

    if not scenarios:
        raise ValueError("At least one scenario must be defined")

    return defaults, scenarios
