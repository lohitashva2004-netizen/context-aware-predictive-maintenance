"""Core analytics for the context-aware predictive maintenance system."""

from .config import CLASSES, FEATURES, THRESHOLDS
from .rules import classify_reading, dominant_fault

__all__ = ["CLASSES", "FEATURES", "THRESHOLDS", "classify_reading", "dominant_fault"]
__version__ = "1.0.0"
