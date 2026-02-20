import numpy as np

# 0..3 відповідають ca.py: EMPTY, TREE_DECID, TREE_CONIF, BURNING
PALETTE = np.array([
    [15, 15, 15],       # EMPTY
    [46, 160, 67],      # TREE_DECID (листяні)
    [20, 110, 55],      # TREE_CONIF (хвойні)
    [255, 69, 0],       # BURNING
], dtype=np.uint8)