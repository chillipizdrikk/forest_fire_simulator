from __future__ import annotations

import pytest

pytest.importorskip("numpy")

from src.app.core.config import CAConfig
from src.app.core.engine import ForestFireCA


def run_simulation(
    ca: ForestFireCA,
    *,
    max_steps: int,
    ignite_at: tuple[int, int] | None = None,
    wait_for_fire_start: bool = False,
) -> dict[str, object]:
    if ignite_at is not None:
        ca.ignite(*ignite_at)

    fire_started = ca.has_active_fire()
    for _ in range(max_steps):
        if fire_started and not ca.has_active_fire():
            break
        if not wait_for_fire_start and not ca.has_active_fire():
            break

        ca.step()
        ca.finalize_run_metrics()
        fire_started = fire_started or ca.has_active_fire()

        if not wait_for_fire_start and fire_started and not ca.has_active_fire():
            break

    ca.finalize_run_metrics()
    return ca.metrics_payload()


def assert_payload_invariants(payload: dict[str, object], step_count: int) -> None:
    burning_cells_t = payload["burning_cells_t"]
    metrics = payload["metrics"]

    assert isinstance(burning_cells_t, list)
    assert len(burning_cells_t) == step_count + 1

    peak_fire_size = metrics["peak_fire_size"]
    auc = metrics["auc"]
    baf = metrics["baf"]

    assert peak_fire_size >= 0
    assert auc >= peak_fire_size
    assert 0.0 <= baf <= 1.0


def test_metrics_payload_invariants_no_rain_golden_scenario() -> None:
    ca = ForestFireCA(
        CAConfig(
            width=1,
            height=1,
            init_tree_density=1.0,
            conifer_ratio=0.0,
            lightning_enabled=False,
            rain_enabled=False,
            seed=7,
        )
    )

    payload = run_simulation(ca, max_steps=10, ignite_at=(0, 0))

    assert_payload_invariants(payload, ca.step_count)
    assert payload["burning_cells_t"] == [0, 1, 1, 0]
    assert payload["metrics"] == {
        "baf": 1.0,
        "peak_fire_size": 1,
        "time_to_peak": 1,
        "fire_duration": 2,
        "auc": 2,
        "burned_components": 1,
        "largest_cluster_share": 1.0,
        "shape_complexity": 4.0,
    }


def test_metrics_payload_invariants_rain_golden_scenario() -> None:
    ca = ForestFireCA(
        CAConfig(
            width=3,
            height=3,
            init_tree_density=1.0,
            lightning_enabled=False,
            rain_enabled=True,
            rain_intensity=0.8,
            seed=17,
        )
    )

    payload = run_simulation(ca, max_steps=8, ignite_at=None)

    assert_payload_invariants(payload, ca.step_count)
    assert payload["burning_cells_t"] == [0]
    assert payload["metrics"] == {
        "baf": 0.0,
        "peak_fire_size": 0,
        "time_to_peak": 0,
        "fire_duration": 0,
        "auc": 0,
        "burned_components": 0,
        "largest_cluster_share": 0.0,
        "shape_complexity": 0.0,
    }


def test_metrics_payload_invariants_lightning_golden_scenario() -> None:
    ca = ForestFireCA(
        CAConfig(
            width=1,
            height=1,
            init_tree_density=1.0,
            conifer_ratio=0.0,
            lightning_enabled=True,
            f=1.0,
            lightning_max_strikes_per_event=1,
            lightning_cooldown_steps=0,
            rain_enabled=False,
            seed=23,
        )
    )

    payload = run_simulation(ca, max_steps=10, wait_for_fire_start=True)

    assert_payload_invariants(payload, ca.step_count)
    assert payload["burning_cells_t"] == [0, 1, 1, 1, 0]
    assert payload["metrics"] == {
        "baf": 1.0,
        "peak_fire_size": 1,
        "time_to_peak": 1,
        "fire_duration": 3,
        "auc": 3,
        "burned_components": 1,
        "largest_cluster_share": 1.0,
        "shape_complexity": 4.0,
    }