"""
Member 3: State-Machine Logic Developer (Subham)
-----------------------------------------------
- Builds the gesture dictionary mapped to the 3D coordinates.
- Writes the continuous Euclidean distance calculations between specific coordinate nodes (e.g., Node 4 and Node 8).
- Sets the threshold flags to classify when spatial movements become actionable states like a "Pinch".
"""

from .member_3 import (
    GestureClassifier,
    GestureType,
    GestureDefinition,
    GESTURE_DICTIONARY,
)

__all__ = [
    "GestureClassifier",
    "GestureType",
    "GestureDefinition",
    "GESTURE_DICTIONARY",
]
