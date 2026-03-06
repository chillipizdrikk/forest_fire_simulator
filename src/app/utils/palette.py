import numpy as np

# 0..7: EMPTY, TREE_DECID, TREE_CONIF, BURNING1, BURNING2, BURNING3, BARRIER, BURNT
PALETTE = np.array([
    [15, 15, 15],       # EMPTY
    [46, 160, 67],      # TREE_DECID
    [20, 110, 55],      # TREE_CONIF

    [255, 90, 0],       # BURNING1 (найяскравіше)
    [220, 60, 0],       # BURNING2
    [170, 40, 0],       # BURNING3 (найслабше)

    [160, 160, 160],    # BARRIER
    [95, 65, 40],       # BURNT
], dtype=np.uint8)