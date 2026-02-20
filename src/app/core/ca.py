from __future__ import annotations
import numpy as np
from dataclasses import dataclass

# States
EMPTY = 0
TREE_DECID = 1   # листяні
TREE_CONIF = 2   # хвойні
BURNING = 3
BARRIER = 4      # NEW: бар’єр (дорога/вода/мінералізована смуга)

TREE_STATES = (TREE_DECID, TREE_CONIF)


@dataclass
class CAConfig:
    width: int = 200
    height: int = 200

    p: float = 0.01                 # ріст (базовий)
    f: float = 0.001                # блискавка
    lightning_enabled: bool = True  # Variant C

    # Humidity: 0.0 = сухо, 1.0 = волого
    humidity: float = 0.0

    # Wind
    wind_enabled: bool = False
    wind_dir: str = "E"
    wind_strength: float = 0.6

    init_tree_density: float = 0.6
    seed: int | None = None

    # Vegetation
    conifer_ratio: float = 0.5
    flamm_decid: float = 0.85
    flamm_conif: float = 1.00


class ForestFireCA:
    # Moore (8 neighbors)
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
        self.grid = self._make_initial_grid()
        self.step_count = 0

    def _make_initial_grid(self) -> np.ndarray:
        cfg = self.cfg
        h, w = cfg.height, cfg.width
        grid = np.full((h, w), EMPTY, dtype=np.uint8)

        has_tree = self.rng.random((h, w)) < float(np.clip(cfg.init_tree_density, 0.0, 1.0))
        conif_ratio = float(np.clip(cfg.conifer_ratio, 0.0, 1.0))
        is_conif = has_tree & (self.rng.random((h, w)) < conif_ratio)
        is_decid = has_tree & ~is_conif

        grid[is_decid] = TREE_DECID
        grid[is_conif] = TREE_CONIF
        return grid

    def reset(self):
        self.grid = self._make_initial_grid()
        self.step_count = 0

    def ignite(self, row: int, col: int):
        """Підпал тільки на деревах."""
        if 0 <= row < self.cfg.height and 0 <= col < self.cfg.width:
            if int(self.grid[row, col]) in TREE_STATES:
                self.grid[row, col] = BURNING

    def toggle_barrier(self, row: int, col: int):
        """Правий клік: ставимо/знімаємо бар’єр. Не ставимо поверх BURNING."""
        if 0 <= row < self.cfg.height and 0 <= col < self.cfg.width:
            v = int(self.grid[row, col])
            if v == BARRIER:
                self.grid[row, col] = EMPTY
            elif v != BURNING:
                self.grid[row, col] = BARRIER

    def _shift_no_wrap(self, mask: np.ndarray, dx: int, dy: int) -> np.ndarray:
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

    def _spread_prob_wind(self, dx: int, dy: int) -> float:
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
        decid = (g == TREE_DECID)
        conif = (g == TREE_CONIF)
        is_tree = decid | conif
        empty = (g == EMPTY)
        barrier = (g == BARRIER)

        humidity = float(np.clip(self.cfg.humidity, 0.0, 1.0))
        dryness = 1.0 - humidity

        # Flammability per cell
        flamm = np.zeros(g.shape, dtype=np.float32)
        flamm[decid] = float(np.clip(self.cfg.flamm_decid, 0.0, 5.0))
        flamm[conif] = float(np.clip(self.cfg.flamm_conif, 0.0, 5.0))

        # Rule 2: ignite from neighbors (wind + humidity + vegetation)
        ignite_from_neighbors = np.zeros_like(is_tree, dtype=bool)
        for dx, dy in self._DIRS:
            src_burning = self._shift_no_wrap(burning, dx, dy)
            candidates = is_tree & src_burning
            if not candidates.any():
                continue

            p_wind = self._spread_prob_wind(dx, dy)
            p_eff = np.clip(p_wind * dryness * flamm, 0.0, 1.0).astype(np.float32)
            ignite_from_neighbors |= candidates & (self.rng.random(g.shape) < p_eff)

        # Rule 3: lightning (also affected by humidity + vegetation)
        f_base = self.cfg.f if self.cfg.lightning_enabled else 0.0
        f_eff = float(np.clip(f_base * dryness, 0.0, 1.0))
        if f_eff > 0.0:
            p_light = np.clip(f_eff * flamm, 0.0, 1.0).astype(np.float32)
            ignite_lightning = is_tree & (self.rng.random(g.shape) < p_light)
        else:
            ignite_lightning = np.zeros_like(is_tree, dtype=bool)

        ignite = ignite_from_neighbors | ignite_lightning

        # Rule 1: growth (humidity affects growth), but NOT on barriers
        p_eff = float(np.clip(self.cfg.p * (0.5 + humidity), 0.0, 1.0))
        grow = empty & (self.rng.random(g.shape) < p_eff)

        conif_ratio = float(np.clip(self.cfg.conifer_ratio, 0.0, 1.0))
        grow_conif = grow & (self.rng.random(g.shape) < conif_ratio)
        grow_decid = grow & ~grow_conif

        # Build next grid:
        next_g = np.full(g.shape, EMPTY, dtype=np.uint8)

        # Preserve barriers ALWAYS
        next_g[barrier] = BARRIER

        # Trees that didn't ignite keep their type
        next_g[decid & ~ignite] = TREE_DECID
        next_g[conif & ~ignite] = TREE_CONIF

        # Growth (only on empty, so won't overwrite barriers)
        next_g[grow_decid] = TREE_DECID
        next_g[grow_conif] = TREE_CONIF

        # Ignitions -> burning (won't affect barriers, since ignite only for trees)
        next_g[ignite] = BURNING

        self.grid = next_g
        self.step_count += 1
        return self.grid
