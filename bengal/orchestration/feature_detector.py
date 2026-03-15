"""
Feature detection for CSS optimization.

Re-exports from bengal.utils.feature_detection for backward compatibility.
Core imports from utils; orchestration consumers may use this module.
"""

from bengal.utils.feature_detection import (
    FeatureDetector,
    detect_site_features,
)

__all__ = ["FeatureDetector", "detect_site_features"]
