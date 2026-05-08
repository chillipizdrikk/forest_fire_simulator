from __future__ import annotations

import pytest

np = pytest.importorskip("numpy")

from src.app.core.config import CAConfig
from src.app.core.constants import BURNING1, TREE_DECID
from src.app.core.engine import ForestFireCA


class ConstantRandom:
    def __init__(self, value: float):
        self.value = value

    def random(self, shape=None):
        if shape is None:
            return self.value
        return np.full(shape, self.value, dtype=np.float64)


def make_two_cell_fire(*, wind_enabled: bool) -> ForestFireCA:
    ca = ForestFireCA(
        CAConfig(
            width=2,
            height=1,
            init_tree_density=0.0,
            humidity=0.0,
            temperature_c=25.0,
            lightning_enabled=False,
            rain_enabled=False,
            wind_enabled=wind_enabled,
            wind_dir="E",
            wind_strength=0.8,
            seed=123,
        )
    )
    ca.grid[0, 0] = BURNING1
    ca.grid[0, 1] = TREE_DECID
    ca.start_run_tracking()
    return ca


def test_downwind_multiplier_is_not_weaker_than_no_wind() -> None:
    no_wind = make_two_cell_fire(wind_enabled=False)
    wind = make_two_cell_fire(wind_enabled=True)

    assert no_wind._spread_prob_wind(0, 1) == pytest.approx(1.0)
    assert wind._spread_prob_wind(0, 1) >= no_wind._spread_prob_wind(0, 1)
    assert wind._spread_prob_wind(0, 1) > 1.0


def test_downwind_spread_can_exceed_no_wind_with_same_random_threshold() -> None:
    no_wind = make_two_cell_fire(wind_enabled=False)
    wind = make_two_cell_fire(wind_enabled=True)

    no_wind.rng = ConstantRandom(0.9)
    wind.rng = ConstantRandom(0.9)

    no_wind.step()
    wind.step()

    assert no_wind.grid[0, 1] == TREE_DECID
    assert wind.grid[0, 1] == BURNING1
