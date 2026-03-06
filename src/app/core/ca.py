from __future__ import annotations
import numpy as np
from dataclasses import dataclass

# States
EMPTY = 0
TREE_DECID = 1
TREE_CONIF = 2

BURNING1 = 3  # сильне полум'я
BURNING2 = 4  # слабше полум'я
BURNING3 = 5  # тління/жар

BARRIER = 6
BURNT = 7

# Для сумісності з твоїм UI (він імпортує BURNING)
BURNING = BURNING1

TREE_STATES = (TREE_DECID, TREE_CONIF)
BURNING_STATES = (BURNING1, BURNING2, BURNING3)


@dataclass
class CAConfig:
    width: int = 200
    height: int = 200

    f: float = 0.001
    lightning_enabled: bool = True

    humidity: float = 0.0
    temperature_c: float = 25.0

    wind_enabled: bool = False
    wind_dir: str = "E"
    wind_strength: float = 0.6

    init_tree_density: float = 0.6
    seed: int | None = None

    conifer_ratio: float = 0.5
    flamm_decid: float = 0.85
    flamm_conif: float = 1.00

    # NEW: коефіцієнти інтенсивності стадій горіння
    burn_stage_factors: tuple[float, float, float] = (1.00, 0.55, 0.25)


class ForestFireCA:
    _DIRS = [
        (-1, -1), (-1, 0), (-1, 1),
        (0, -1),           (0, 1),
        (1, -1),  (1, 0),  (1, 1),
    ]

    _WIND_DIRS = {
        "N": (-1, 0), "NE": (-1, 1), "E": (0, 1), "SE": (1, 1),
        "S": (1, 0), "SW": (1, -1), "W": (0, -1), "NW": (-1, -1),
    }

    _T_MIN = -10.0
    _T_MAX = 40.0

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

    # ----------- Editing tools -----------

    def set_empty(self, row: int, col: int):
        if 0 <= row < self.cfg.height and 0 <= col < self.cfg.width:
            self.grid[row, col] = EMPTY

    def set_barrier(self, row: int, col: int, enabled: bool = True):
        """Ставимо/знімаємо бар’єр. Не ставимо поверх стадій горіння."""
        if 0 <= row < self.cfg.height and 0 <= col < self.cfg.width:
            v = int(self.grid[row, col])
            if enabled:
                if v not in BURNING_STATES:
                    self.grid[row, col] = BARRIER
            else:
                if v == BARRIER:
                    self.grid[row, col] = EMPTY

    def plant_decid(self, row: int, col: int):
        if 0 <= row < self.cfg.height and 0 <= col < self.cfg.width:
            if int(self.grid[row, col]) not in (BARRIER, *BURNING_STATES):
                self.grid[row, col] = TREE_DECID

    def plant_conif(self, row: int, col: int):
        if 0 <= row < self.cfg.height and 0 <= col < self.cfg.width:
            if int(self.grid[row, col]) not in (BARRIER, *BURNING_STATES):
                self.grid[row, col] = TREE_CONIF

    def ignite(self, row: int, col: int):
        """Підпал тільки на деревах. Стартуємо зі стадії BURNING1."""
        if 0 <= row < self.cfg.height and 0 <= col < self.cfg.width:
            if int(self.grid[row, col]) in TREE_STATES:
                self.grid[row, col] = BURNING1

    # ----------- Simulation internals -----------

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

    def _temp_norm(self) -> float:
        t = float(self.cfg.temperature_c)
        return float(np.clip((t - self._T_MIN) / (self._T_MAX - self._T_MIN), 0.0, 1.0))
    
    def has_active_fire(self) -> bool:
        """Чи є на полі хоча б одна клітинка в стадії горіння."""
        return bool(np.any(
            (self.grid == BURNING1) |
            (self.grid == BURNING2) |
            (self.grid == BURNING3)
        ))

    def step(self):
        g = self.grid

        b1 = (g == BURNING1)
        b2 = (g == BURNING2)
        b3 = (g == BURNING3)

        decid = (g == TREE_DECID)
        conif = (g == TREE_CONIF)
        is_tree = decid | conif

        barrier = (g == BARRIER)
        burnt = (g == BURNT)

        # Humidity + Temperature -> dryness_eff
        humidity = float(np.clip(self.cfg.humidity, 0.0, 1.0))
        dryness = 1.0 - humidity
        t_norm = self._temp_norm()
        temp_factor = 0.5 + t_norm
        dryness_eff = float(np.clip(dryness * temp_factor, 0.0, 1.0))

        # Flammability per cell
        flamm = np.zeros(g.shape, dtype=np.float32)
        flamm[decid] = float(np.clip(self.cfg.flamm_decid, 0.0, 5.0))
        flamm[conif] = float(np.clip(self.cfg.flamm_conif, 0.0, 5.0))

        # Stage factors
        s1, s2, s3 = self.cfg.burn_stage_factors
        s1 = float(np.clip(s1, 0.0, 1.0))
        s2 = float(np.clip(s2, 0.0, 1.0))
        s3 = float(np.clip(s3, 0.0, 1.0))

        # Rule 2: ignite from neighbors, але з урахуванням стадії джерела
        ignite_from_neighbors = np.zeros_like(is_tree, dtype=bool)

        for dx, dy in self._DIRS:
            src1 = self._shift_no_wrap(b1, dx, dy)
            src2 = self._shift_no_wrap(b2, dx, dy)
            src3 = self._shift_no_wrap(b3, dx, dy)

            # інтенсивність джерела в цій позиції (0, або s1/s2/s3)
            src_factor = (src1.astype(np.float32) * s1) + (src2.astype(np.float32) * s2) + (src3.astype(np.float32) * s3)

            candidates = is_tree & (src_factor > 0.0)
            if not candidates.any():
                continue

            p_wind = self._spread_prob_wind(dx, dy)
            p_eff = np.clip(p_wind * dryness_eff * flamm * src_factor, 0.0, 1.0).astype(np.float32)

            ignite_from_neighbors |= candidates & (self.rng.random(g.shape) < p_eff)

        # Rule 3: lightning -> завжди стартує з BURNING1
        f_base = self.cfg.f if self.cfg.lightning_enabled else 0.0
        f_eff = float(np.clip(f_base * dryness_eff, 0.0, 1.0))
        if f_eff > 0.0:
            p_light = np.clip(f_eff * flamm, 0.0, 1.0).astype(np.float32)
            ignite_lightning = is_tree & (self.rng.random(g.shape) < p_light)
        else:
            ignite_lightning = np.zeros_like(is_tree, dtype=bool)

        ignite = ignite_from_neighbors | ignite_lightning

        # Build next grid
        next_g = np.full(g.shape, EMPTY, dtype=np.uint8)

        next_g[barrier] = BARRIER
        next_g[burnt] = BURNT

        # прогресія горіння
        next_g[b3] = BURNT
        next_g[b2] = BURNING3
        next_g[b1] = BURNING2

        # дерева, які не загорілись
        next_g[decid & ~ignite] = TREE_DECID
        next_g[conif & ~ignite] = TREE_CONIF

        # нові займання
        next_g[ignite] = BURNING1

        self.grid = next_g
        self.step_count += 1
        return self.grid