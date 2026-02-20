import numpy as np

EMPTY = 0
TREE_DECID = 1
TREE_CONIF = 2
BURNING = 3

# uint8, щоб швидко індексувалося PALETTE[grid]
PALETTE = np.array([
    [15, 15, 15],       # EMPTY
    [46, 160, 67],      # TREE_DECID (листяні) - світліше зелений
    [20, 110, 55],      # TREE_CONIF (хвойні)  - темніше зелений
    [255, 69, 0],       # BURNING
], dtype=np.uint8)

