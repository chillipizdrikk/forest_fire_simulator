from __future__ import annotations

import numpy as np


_COMPONENT_DIRS_8 = (
    (-1, -1), (-1, 0), (-1, 1),
    (0, -1),           (0, 1),
    (1, -1),  (1, 0),  (1, 1),
)


def burned_spatial_metrics(burnt_mask: np.ndarray) -> dict[str, int | float]:
    mask = np.asarray(burnt_mask, dtype=bool)
    if mask.ndim != 2:
        raise ValueError("burnt_mask must be a 2D array")

    burnt_area = int(np.count_nonzero(mask))
    if burnt_area == 0:
        return {
            "burned_components": 0,
            "largest_cluster_share": 0.0,
            "shape_complexity": 0.0,
        }

    visited = np.zeros_like(mask, dtype=bool)
    components = 0
    largest_component = 0
    h, w = mask.shape

    for row in range(h):
        for col in range(w):
            if not mask[row, col] or visited[row, col]:
                continue

            components += 1
            stack = [(row, col)]
            visited[row, col] = True
            component_size = 0

            while stack:
                cr, cc = stack.pop()
                component_size += 1
                for dr, dc in _COMPONENT_DIRS_8:
                    nr = cr + dr
                    nc = cc + dc
                    if nr < 0 or nr >= h or nc < 0 or nc >= w:
                        continue
                    if not mask[nr, nc] or visited[nr, nc]:
                        continue
                    visited[nr, nc] = True
                    stack.append((nr, nc))

            largest_component = max(largest_component, component_size)

    perimeter = 0
    for row in range(h):
        for col in range(w):
            if not mask[row, col]:
                continue
            if row == 0 or not mask[row - 1, col]:
                perimeter += 1
            if row == h - 1 or not mask[row + 1, col]:
                perimeter += 1
            if col == 0 or not mask[row, col - 1]:
                perimeter += 1
            if col == w - 1 or not mask[row, col + 1]:
                perimeter += 1

    return {
        "burned_components": int(components),
        "largest_cluster_share": float(largest_component / burnt_area),
        "shape_complexity": float(perimeter / burnt_area),
    }
