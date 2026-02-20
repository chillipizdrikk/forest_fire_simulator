import numpy as np

# 0..4: EMPTY, TREE_DECID, TREE_CONIF, BURNING, BARRIER
PALETTE = np.array([
    [15, 15, 15],       # EMPTY
    [46, 160, 67],      # TREE_DECID
    [20, 110, 55],      # TREE_CONIF
    [255, 69, 0],       # BURNING
    [160, 160, 160],    # BARRIER (сірий)
], dtype=np.uint8)


