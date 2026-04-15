from __future__ import annotations

import numpy as np


_COMPONENT_DIRS_8 = (
    (-1, -1), (-1, 0), (-1, 1),
    (0, -1),           (0, 1),
    (1, -1),  (1, 0),  (1, 1),
)


def _burned_perimeter(mask: np.ndarray) -> int:
    """Return perimeter using 4-neighbour exposed edges."""
    top_edges = np.count_nonzero(mask[0, :]) + np.count_nonzero(mask[1:, :] & ~mask[:-1, :])
    bottom_edges = np.count_nonzero(mask[-1, :]) + np.count_nonzero(mask[:-1, :] & ~mask[1:, :])
    left_edges = np.count_nonzero(mask[:, 0]) + np.count_nonzero(mask[:, 1:] & ~mask[:, :-1])
    right_edges = np.count_nonzero(mask[:, -1]) + np.count_nonzero(mask[:, :-1] & ~mask[:, 1:])
    return int(top_edges + bottom_edges + left_edges + right_edges)


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

    # Iterate only through burnt cells to reduce Python-level loop work.
    burnt_coords = np.argwhere(mask)

    # Fixed-size stacks avoid per-node tuple allocations in Python lists.
    stack_rows = np.empty(burnt_area, dtype=np.int32)
    stack_cols = np.empty(burnt_area, dtype=np.int32)

    for row, col in burnt_coords:
        if visited[row, col]:
            continue

        components += 1
        visited[row, col] = True
        component_size = 0
        stack_size = 1
        stack_rows[0] = row
        stack_cols[0] = col

        while stack_size:
            stack_size -= 1
            cr = stack_rows[stack_size]
            cc = stack_cols[stack_size]
            component_size += 1

            for dr, dc in _COMPONENT_DIRS_8:
                nr = cr + dr
                nc = cc + dc
                if nr < 0 or nr >= h or nc < 0 or nc >= w:
                    continue
                if not mask[nr, nc] or visited[nr, nc]:
                    continue
                visited[nr, nc] = True
                stack_rows[stack_size] = nr
                stack_cols[stack_size] = nc
                stack_size += 1

        largest_component = max(largest_component, component_size)

    perimeter = _burned_perimeter(mask)

    return {
        "burned_components": int(components),
        "largest_cluster_share": float(largest_component / burnt_area),
        "shape_complexity": float(perimeter / burnt_area),
    }
