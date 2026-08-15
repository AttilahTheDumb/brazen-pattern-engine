"""Explicit dimensional constraints for authored geometry."""
from __future__ import annotations

import math
from math import hypot
from typing import Mapping, Sequence

from .errors import ValidationError
from .geometry import Pattern


def evaluate_constraints(pattern: Pattern, constraints: Sequence[dict[str, object]], measurement_values: Mapping[str, float] | None = None) -> dict[str, object]:
    if not isinstance(constraints, (list, tuple)):
        raise ValidationError("constraints must be an array")
    if not constraints:
        raise ValidationError("constraints must contain at least one assertion")
    pattern.validate_closed_contours()
    if measurement_values is not None and not isinstance(measurement_values, Mapping):
        raise ValidationError("measurementValues must be an object")
    pieces = {piece.piece_id: piece for piece in pattern.pieces}

    results: list[dict[str, object]] = []
    for index, constraint in enumerate(constraints):
        if not isinstance(constraint, dict):
            raise ValidationError(f"constraint {index} must be an object")
        piece_id = constraint.get("pieceId")
        contour_name = constraint.get("contour")
        kind = constraint.get("kind", "distance")
        from_index = constraint.get("fromIndex")
        to_index = constraint.get("toIndex")
        expected = constraint.get("valueMm")
        measurement_id = constraint.get("measurementId")
        source = "literal"
        if measurement_id is not None:
            if not isinstance(measurement_id, str) or not measurement_values or measurement_id not in measurement_values:
                raise ValidationError(f"constraint {index}: measurement binding does not resolve")
            expected = measurement_values[measurement_id]
            source = f"measurement:{measurement_id}"
        tolerance = constraint.get("toleranceMm", 0.1)
        if not isinstance(piece_id, str) or not isinstance(contour_name, str) or not isinstance(kind, str):
            raise ValidationError(f"constraint {index}: pieceId, contour and kind are required strings")
        if expected is None or not isinstance(expected, (int, float)) or isinstance(expected, bool) or not math.isfinite(float(expected)):
            raise ValidationError(f"constraint {index}: valueMm or measurement value must be finite")
        if not isinstance(tolerance, (int, float)) or isinstance(tolerance, bool) or not math.isfinite(float(tolerance)) or tolerance < 0:
            raise ValidationError(f"constraint {index}: toleranceMm must be finite and >= 0")
        if kind not in {"distance", "horizontal", "vertical"}:
            raise ValidationError(f"constraint {index}: unsupported kind {kind}")
        if not isinstance(from_index, int) or isinstance(from_index, bool) or not isinstance(to_index, int) or isinstance(to_index, bool):
            raise ValidationError(f"constraint {index}: point indexes must be integers")
        piece = pieces.get(piece_id)
        contour = next((item for item in piece.contours if item.name == contour_name), None) if piece else None
        if contour is None or from_index < 0 or to_index < 0 or from_index >= len(contour.points) or to_index >= len(contour.points):
            raise ValidationError(f"constraint {index}: point reference does not resolve")
        first, second = contour.points[from_index], contour.points[to_index]
        dx, dy = float(second.x - first.x), float(second.y - first.y)
        actual = hypot(dx, dy) if kind == "distance" else abs(dx if kind == "horizontal" else dy)
        delta = abs(actual - float(expected))
        results.append({"index": index, "pieceId": piece_id, "contour": contour_name, "kind": kind, "actualMm": round(actual, 6), "expectedMm": float(expected), "toleranceMm": float(tolerance), "deltaMm": round(delta, 6), "source": source, "status": "PASS" if delta <= float(tolerance) else "FAIL"})
    return {"status": "PASS" if all(item["status"] == "PASS" for item in results) else "FAIL", "constraints": results, "count": len(results)}
