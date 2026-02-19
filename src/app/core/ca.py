from __future__ import annotations
import numpy as np
from dataclasses import dataclass

EMPTY, TREE, BURNING = 0, 1, 2


@dataclass
class CAConfig:
    width: int = 200
    height: int = 200

    p: float = 0.01                 # ріст (базовий)
    f: float = 0.001                # блискавка
    lightning_enabled: bool = True  # Variant C

    # Humidity: 0.0 = дуже сухо, 1.0 = дуже волого
    humidity: float = 0.0

    # Wind
    wind_enabled: bool = False
    wind_dir: str = "E"             # N, NE, E, SE, S, SW, W, NW
    wind_strength: float = 0.6      # 0..1

    init_tree_density: float = 0.6
    seed: int | None = None


class ForestFireCA:
    # Moore directions only (8 сусідів)
    _DIRS = [
        (-1, -1), (-1, 0), (-1, 1),
        (0, -1),           (0, 1),
        (1, -1),  (1, 0),  (1, 1),
    ]

    _WIND_DIRS = {
        "N": (-1, 0),
        "NE": (-1, 1),
        "E": (0, 1),
        "SE": (1, 1),
        "S": (1, 0),
        "SW": (1, -1),
        "W": (0, -1),
        "NW": (-1, -1),
    }

    def __init__(self, cfg: CAConfig):
        self.cfg = cfg
        self.rng = np.random.default_rng(cfg.seed)
        self.grid = np.where(
            self.rng.random((cfg.height, cfg.width)) < cfg.init_tree_density,
            TREE,
            EMPTY
        ).astype(np.uint8)
        self.step_count = 0

    def reset(self):
        cfg = self.cfg
        self.grid = np.where(
            self.rng.random((cfg.height, cfg.width)) < cfg.init_tree_density,
            TREE,
            EMPTY
        ).astype(np.uint8)
        self.step_count = 0

    def ignite(self, row: int, col: int):
        """Ручне займання кліком. Дозволяємо підпал лише клітин з деревом."""
        if 0 <= row < self.cfg.height and 0 <= col < self.cfg.width:
            if self.grid[row, col] == TREE:
                self.grid[row, col] = BURNING

    def _shift_no_wrap(self, mask: np.ndarray, dx: int, dy: int) -> np.ndarray:
        """
        Аналог np.roll, але БЕЗ wrap-around.
        out[i,j] = mask[i-dx, j-dy] якщо індекси в межах, інакше 0/False.
        """
        h, w = mask.shape
        out = np.zeros_like(mask, dtype=mask.dtype)

        xs0 = max(0, -dx)
        xs1 = h - max(0, dx)
        ys0 = max(0, -dy)
        ys1 = w - max(0, dy)

        xd0 = max(0, dx)
        yd0 = max(0, dy)

        out[xd0:xd0 + (xs1 - xs0), yd0:yd0 + (ys1 - ys0)] = mask[xs0:xs1, ys0:ys1]
        return out

    def _spread_prob(self, dx: int, dy: int) -> float:
        """
        Базова ймовірність займання від палаючого сусіда в напрямку (dx,dy) source->target
        з урахуванням ВІТРУ. Вологість застосовуємо в step().
        """
        if not self.cfg.wind_enabled or self.cfg.wind_strength <= 0:
            return 1.0

        wx, wy = self._WIND_DIRS.get(self.cfg.wind_dir, (0, 1))

        d_norm = (dx * dx + dy * dy) ** 0.5
        w_norm = (wx * wx + wy * wy) ** 0.5
        dot = (dx * wx + dy * wy) / (d_norm * w_norm)  # [-1..1]

        s = float(self.cfg.wind_strength)
        p = 1.0 - s * (1.0 - dot) / 2.0
        return float(np.clip(p, 0.0, 1.0))

    def step(self):
        g = self.grid
        burning = (g == BURNING)
        tree = (g == TREE)
        empty = (g == EMPTY)

        # Humidity: чим більша вологість, тим менше "сухість"
        humidity = float(np.clip(self.cfg.humidity, 0.0, 1.0))
        dryness = 1.0 - humidity  # 1 = сухо, 0 = дуже волого

        # Rule 2 (Moore + wind + humidity, без wrap-around)
        ignite_from_neighbors = np.zeros_like(tree, dtype=bool)

        for dx, dy in self._DIRS:
            src_burning = self._shift_no_wrap(burning, dx, dy)
            candidates = tree & src_burning
            if not candidates.any():
                continue

            p_wind = self._spread_prob(dx, dy)
            p_eff = p_wind * dryness  # <- вологість зменшує поширення

            if p_eff >= 1.0:
                ignite_from_neighbors |= candidates
            elif p_eff > 0.0:
                ignite_from_neighbors |= candidates & (self.rng.random(g.shape) < p_eff)

        # Rule 3 (lightning, Variant C) + humidity
        f_eff = (self.cfg.f if self.cfg.lightning_enabled else 0.0) * dryness
        if f_eff > 0.0:
            lightning = self.rng.random(g.shape) < f_eff
        else:
            lightning = np.zeros_like(tree, dtype=bool)

        ignite = ignite_from_neighbors | (tree & lightning)

        # Rule 1 (growth) + humidity (NEW)
        # p_eff = p * (0.5 + humidity): в посуху рост гірший, у вологу — кращий
        p_eff = float(np.clip(self.cfg.p * (0.5 + humidity), 0.0, 1.0))
        grow = empty & (self.rng.random(g.shape) < p_eff)

        # Rule 4 (burning -> empty)
        next_g = np.full(g.shape, EMPTY, dtype=np.uint8)
        next_g[tree & ~ignite] = TREE
        next_g[grow] = TREE
        next_g[ignite] = BURNING

        self.grid = next_g
        self.step_count += 1
        return self.grid
