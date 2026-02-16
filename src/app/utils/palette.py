import numpy as np

EMPTY, TREE, BURNING = 0, 1, 2

# Можеш змінити на свої кольори; головне — uint8
PALETTE = np.array([
    [15, 15, 15],      # EMPTY
    [34, 139, 34],     # TREE
    [255, 69, 0],      # BURNING
], dtype=np.uint8)
