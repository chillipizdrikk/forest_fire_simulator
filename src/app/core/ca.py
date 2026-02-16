from __future__ import annotations
import numpy as np
from dataclasses import dataclass

EMPTY, TREE, BURNING = 0, 1, 2

@dataclass
class CAConfig:
    width: int = 200
    height: int = 200
    p: float = 0.01       # ріст
    f: float = 0.001      # блискавка
    neighborhood: str = "moore"  # "moore" (8) або "von_neumann" (4)
    init_tree_density: float = 0.6
    seed: int | None = None

class ForestFireCA:
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

    def _burning_neighbors(self, burning_mask: np.ndarray) -> np.ndarray:
        """Повертає bool-матрицю: чи є палаючий сусід."""
        if self.cfg.neighborhood == "von_neumann":
            shifts = [(-1,0), (1,0), (0,-1), (0,1)]
        else:  # moore
            shifts = [(dx, dy) for dx in (-1,0,1) for dy in (-1,0,1) if not (dx==0 and dy==0)]

        neigh = np.zeros_like(burning_mask, dtype=np.uint8)
        for dx, dy in shifts:
            neigh |= np.roll(np.roll(burning_mask, dx, axis=0), dy, axis=1)
        return neigh.astype(bool)

    def step(self):
        g = self.grid
        burning = (g == BURNING)
        tree = (g == TREE)
        empty = (g == EMPTY)

        has_burning_neighbor = self._burning_neighbors(burning)

        # Правило 3: блискавка
        lightning = self.rng.random(g.shape) < self.cfg.f

        # Правило 2 + 3: займання
        ignite = tree & (has_burning_neighbor | lightning)

        # Правило 1: ріст
        grow = empty & (self.rng.random(g.shape) < self.cfg.p)

        # Правило 4: burning -> empty
        next_g = np.full(g.shape, EMPTY, dtype=np.uint8)
        next_g[tree & ~ignite] = TREE
        next_g[grow] = TREE
        next_g[ignite] = BURNING

        self.grid = next_g
        self.step_count += 1
        return self.grid


