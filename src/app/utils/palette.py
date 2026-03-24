import numpy as np

# 0..7: EMPTY, TREE_DECID, TREE_CONIF, BURNING1, BURNING2, BURNING3, BARRIER, BURNT
PALETTE = np.array([
    [9, 14, 23],        # EMPTY
    [70, 176, 96],      # TREE_DECID
    [28, 120, 73],      # TREE_CONIF
    [255, 132, 41],     # BURNING1
    [234, 88, 12],      # BURNING2
    [180, 52, 23],      # BURNING3
    [148, 163, 184],    # BARRIER
    [110, 76, 52],      # BURNT
], dtype=np.uint8)
