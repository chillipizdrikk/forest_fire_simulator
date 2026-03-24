"""Cell state constants for the forest fire cellular automata model."""

EMPTY = 0
TREE_DECID = 1
TREE_CONIF = 2

BURNING1 = 3
BURNING2 = 4
BURNING3 = 5

BARRIER = 6
BURNT = 7

# Backward compatibility alias for older UI code.
BURNING = BURNING1

TREE_STATES = (TREE_DECID, TREE_CONIF)
BURNING_STATES = (BURNING1, BURNING2, BURNING3)
