from __future__ import annotations

import pytest

np = pytest.importorskip("numpy")

from src.app.core.spatial_metrics import burned_spatial_metrics


def test_burned_spatial_metrics_returns_zeroes_for_empty_mask() -> None:
    mask = np.zeros((3, 3), dtype=bool)

    result = burned_spatial_metrics(mask)

    assert result == {
        "burned_components": 0,
        "largest_cluster_share": 0.0,
        "shape_complexity": 0.0,
    }


def test_burned_spatial_metrics_handles_two_disconnected_clusters() -> None:
    mask = np.array(
        [
            [1, 1, 0, 0],
            [1, 1, 0, 0],
            [0, 0, 0, 1],
            [0, 0, 0, 0],
        ],
        dtype=bool,
    )

    result = burned_spatial_metrics(mask)

    assert result["burned_components"] == 2
    assert result["largest_cluster_share"] == pytest.approx(4 / 5)
    assert result["shape_complexity"] == pytest.approx(12 / 5)


def test_burned_spatial_metrics_uses_8_connectivity_for_components() -> None:
    mask = np.array([[1, 0], [0, 1]], dtype=bool)

    result = burned_spatial_metrics(mask)

    assert result["burned_components"] == 1
    assert result["largest_cluster_share"] == 1.0
    assert result["shape_complexity"] == pytest.approx(4.0)
