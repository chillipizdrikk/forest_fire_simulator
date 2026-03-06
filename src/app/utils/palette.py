import numpy as np

# 0..5: EMPTY, TREE_DECID, TREE_CONIF, BURNING, BARRIER, BURNT
PALETTE = np.array([
    [15, 15, 15],       # EMPTY
    [46, 160, 67],      # TREE_DECID
    [20, 110, 55],      # TREE_CONIF
    [255, 69, 0],       # BURNING
    [160, 160, 160],    # BARRIER
    [95, 65, 40],       # BURNT
], dtype=np.uint8)