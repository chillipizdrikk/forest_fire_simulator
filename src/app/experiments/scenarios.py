from __future__ import annotations

from dataclasses import dataclass
import importlib
import json
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ScenarioDefinition:
    name: str
    params: dict[str, Any]


def _parse_scalar(raw: str) -> Any:
    text = raw.strip()
    if text == "{}":
        return {}
    if text == "[]":
        return []
    if text in ("true", "True"):
        return True
    if text in ("false", "False"):
        return False
    if text in ("null", "None", "~"):
        return None
    if text.startswith(("'", '"')) and text.endswith(("'", '"')) and len(text) >= 2:
        return text[1:-1]
    try:
        return int(text)
    except ValueError:
        pass
    try:
        return float(text)
    except ValueError:
        return text


def _load_with_stdlib_fallback(raw_text: str) -> dict[str, Any]:
    """
    Minimal YAML subset parser for project `scenarios.yaml` files when PyYAML is unavailable.
    Supports:
    - top-level mappings
    - nested mappings with 2-space indentation
    - list items under `scenarios` in form:
      - name: ...
        params:
          key: value
    """
    result: dict[str, Any] = {}
    lines = [line.rstrip() for line in raw_text.splitlines() if line.strip() and not line.strip().startswith("#")]
    idx = 0
    while idx < len(lines):
        line = lines[idx]
        if line.startswith("defaults:"):
            defaults: dict[str, Any] = {}
            idx += 1
            while idx < len(lines) and lines[idx].startswith("  ") and not lines[idx].startswith("  - "):
                key, value = lines[idx].strip().split(":", maxsplit=1)
                defaults[key.strip()] = _parse_scalar(value)
                idx += 1
            result["defaults"] = defaults
            continue
        if line.startswith("scenarios:"):
            scenarios: list[dict[str, Any]] = []
            idx += 1
            while idx < len(lines) and lines[idx].startswith("  - "):
                item_line = lines[idx][4:]
                scenario: dict[str, Any] = {}
                if ":" in item_line:
                    key, value = item_line.split(":", maxsplit=1)
                    scenario[key.strip()] = _parse_scalar(value)
                idx += 1
                while idx < len(lines) and lines[idx].startswith("    "):
                    inner = lines[idx].strip()
                    if inner.endswith(":"):
                        block_key = inner[:-1].strip()
                        idx += 1
                        nested: dict[str, Any] = {}
                        while idx < len(lines) and lines[idx].startswith("      "):
                            n_key, n_val = lines[idx].strip().split(":", maxsplit=1)
                            nested[n_key.strip()] = _parse_scalar(n_val)
                            idx += 1
                        scenario[block_key] = nested
                    else:
                        in_key, in_val = inner.split(":", maxsplit=1)
                        scenario[in_key.strip()] = _parse_scalar(in_val)
                        idx += 1
                scenarios.append(scenario)
            result["scenarios"] = scenarios
            continue
        idx += 1
    return result


def load_scenarios(path: str | Path) -> tuple[dict[str, Any], list[ScenarioDefinition]]:
    raw_text = Path(path).read_text(encoding="utf-8")

    try:
        yaml_module = importlib.import_module("yaml")
        content = yaml_module.safe_load(raw_text)
    except ModuleNotFoundError:
        try:
            content = json.loads(raw_text)
        except json.JSONDecodeError:
            content = _load_with_stdlib_fallback(raw_text)

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
