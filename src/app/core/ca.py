"""Backward-compatible public API for the core simulation package."""

from src.app.core.config import CAConfig
from src.app.core.constants import (
    BARRIER,
    BURNING,
    BURNING1,
    BURNING2,
    BURNING3,
    BURNING_STATES,
    BURNT,
    EMPTY,
    TREE_CONIF,
    TREE_DECID,
    TREE_STATES,
)
from src.app.core.engine import ForestFireCA

__all__ = [
    "CAConfig",
    "ForestFireCA",
    "EMPTY",
    "TREE_DECID",
    "TREE_CONIF",
    "BURNING",
    "BURNING1",
    "BURNING2",
    "BURNING3",
    "BARRIER",
    "BURNT",
    "TREE_STATES",
    "BURNING_STATES",
]
