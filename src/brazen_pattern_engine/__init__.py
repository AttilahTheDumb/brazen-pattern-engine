"""Brazen Pattern Engine: deterministic measurement and geometry foundations."""

from .errors import ValidationError
from .measurements import (
    MeasurementSession,
    RepeatabilityStudy,
    ToleranceBudget,
    classify_measurement,
    derive_measurements,
    tolerance_budget_from_study,
)
from .fit_corrections import validate_fit_correction, is_trainable_correction
from .geometry import Pattern, PatternPiece, Point, Polyline

__all__ = [
    "MeasurementSession",
    "Pattern",
    "PatternPiece",
    "Point",
    "Polyline",
    "RepeatabilityStudy",
    "ToleranceBudget",
    "ValidationError",
    "classify_measurement",
    "derive_measurements",
    "is_trainable_correction",
    "tolerance_budget_from_study",
    "validate_fit_correction",
]
