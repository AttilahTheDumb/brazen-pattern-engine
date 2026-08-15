"""Deterministic downstream design operations for authored geometry.

These operations are software artefacts only. They do not establish body fit,
leather behaviour, manufacturing approval, or a validated drafting rule set.
"""
from __future__ import annotations

from dataclasses import replace
from math import hypot
from typing import Mapping

from .errors import GateFailure, ValidationError
from .geometry import Pattern, PatternPiece, Point, Polyline


def _line_intersection(a: tuple[float, float], b: tuple[float, float], c: tuple[float, float], d: tuple[float, float]) -> tuple[float, float]:
    x1, y1 = a; x2, y2 = b; x3, y3 = c; x4, y4 = d
    den = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    if abs(den) < 1e-9:
        return b
    det1 = x1 * y2 - y1 * x2
    det2 = x3 * y4 - y3 * x4
    return ((det1 * (x3 - x4) - (x1 - x2) * det2) / den, (det1 * (y3 - y4) - (y1 - y2) * det2) / den)


def _offset_contour(contour: Polyline, allowance_mm: float) -> Polyline:
    if not contour.closed:
        raise GateFailure(f"{contour.name}: seam allowance requires a closed contour")
    if contour.controls and any(in_handle or out_handle for in_handle, out_handle in contour.controls):
        raise GateFailure(f"{contour.name}: curve-preserving seam allowance is not available; flatten or use a straight contour")
    if allowance_mm <= 0:
        raise ValidationError("seam allowance must be > 0")
    points = [(float(point.x), float(point.y)) for point in contour.points]
    area = float(contour.area_mm2())
    outward_sign = 1.0 if area > 0 else -1.0
    lines: list[tuple[tuple[float, float], tuple[float, float]]] = []
    for index, start in enumerate(points):
        end = points[(index + 1) % len(points)]
        dx, dy = end[0] - start[0], end[1] - start[1]
        length = hypot(dx, dy)
        if length == 0:
            raise ValidationError(f"{contour.name}: zero-length edge")
        nx, ny = outward_sign * dy / length, outward_sign * -dx / length
        offset = (nx * allowance_mm, ny * allowance_mm)
        lines.append(((start[0] + offset[0], start[1] + offset[1]), (end[0] + offset[0], end[1] + offset[1])))
    result: list[Point] = []
    for index in range(len(points)):
        previous = lines[(index - 1) % len(lines)]
        current = lines[index]
        x, y = _line_intersection(previous[0], previous[1], current[0], current[1])
        result.append(Point(round(x, 1), round(y, 1)))
    return Polyline(contour.name, tuple(result), True)


def apply_seam_allowance(pattern: Pattern, *, allowance_mm: float, contour_names: set[str] | None = None) -> Pattern:
    """Return a deterministic inspection pattern with an explicit seam offset."""
    contours: list[PatternPiece] = []
    for piece in pattern.pieces:
        updated = tuple(_offset_contour(contour, allowance_mm) if contour_names is None or contour.name in contour_names else contour for contour in piece.contours)
        contours.append(replace(piece, contours=updated))
    return replace(pattern, pieces=tuple(contours))


def grade_pattern(pattern: Pattern, increments: Mapping[str, Mapping[str, float]]) -> Pattern:
    """Translate pieces by explicit x/y size increments; no anthropometric grading is inferred."""
    updated: list[PatternPiece] = []
    for piece in pattern.pieces:
        rule = increments.get(piece.piece_id, {})
        dx, dy = float(rule.get("xMm", 0)), float(rule.get("yMm", 0))
        if not all(map(lambda value: abs(value) < 1e6, (dx, dy))):
            raise ValidationError(f"{piece.piece_id}: grading increment is out of bounds")
        contours = []
        for contour in piece.contours:
            translated = tuple(Point(float(point.x) + dx, float(point.y) + dy) for point in contour.points)
            controls = tuple((Point(float(in_handle.x) + dx, float(in_handle.y) + dy) if in_handle else None, Point(float(out_handle.x) + dx, float(out_handle.y) + dy) if out_handle else None) for in_handle, out_handle in contour.controls) if contour.controls else ()
            contours.append(Polyline(contour.name, translated, contour.closed, controls))
        updated.append(replace(piece, contours=tuple(contours)))
    return replace(pattern, pieces=tuple(updated))


def grade_table(pattern: Pattern, sizes: Mapping[str, Mapping[str, Mapping[str, float]]]) -> dict[str, Pattern]:
    if not isinstance(sizes, Mapping) or not sizes:
        raise ValidationError("grade table requires at least one named size")
    return {str(size): grade_pattern(pattern, rules) for size, rules in sorted(sizes.items())}


def smooth_contour(pattern: Pattern, *, piece_id: str, contour_name: str, tension: float = 0.25) -> Pattern:
    """Add deterministic cubic Bézier handles to one closed contour."""
    if not 0 < tension <= 1:
        raise ValidationError("curve tension must be > 0 and <= 1")
    updated: list[PatternPiece] = []
    found = False
    for piece in pattern.pieces:
        contours: list[Polyline] = []
        for contour in piece.contours:
            if piece.piece_id != piece_id or contour.name != contour_name:
                contours.append(contour)
                continue
            if not contour.closed:
                raise GateFailure(f"{piece_id}/{contour_name}: smoothing requires a closed contour")
            found = True
            points = contour.points
            controls: list[tuple[Point, Point]] = []
            for index, point in enumerate(points):
                previous = points[(index - 1) % len(points)]
                following = points[(index + 1) % len(points)]
                dx = (float(following.x) - float(previous.x)) * tension
                dy = (float(following.y) - float(previous.y)) * tension
                controls.append((Point(float(point.x) - dx, float(point.y) - dy), Point(float(point.x) + dx, float(point.y) + dy)))
            contours.append(replace(contour, controls=tuple(controls)))
        updated.append(replace(piece, contours=tuple(contours)))
    if not found:
        raise ValidationError(f"contour not found: {piece_id}/{contour_name}")
    return replace(pattern, pieces=tuple(updated))


def compare_patterns(reference: Pattern, candidate: Pattern, *, tolerance_mm: float) -> dict[str, object]:
    if tolerance_mm < 0:
        raise ValidationError("comparison tolerance must be >= 0")
    reference_pieces = {piece.piece_id: piece for piece in reference.pieces}
    candidate_pieces = {piece.piece_id: piece for piece in candidate.pieces}
    missing = sorted(set(reference_pieces) - set(candidate_pieces))
    extra = sorted(set(candidate_pieces) - set(reference_pieces))
    deltas: list[float] = []
    structural: list[str] = [*(f"missing piece: {piece}" for piece in missing), *(f"extra piece: {piece}" for piece in extra)]
    for piece_id in sorted(set(reference_pieces) & set(candidate_pieces)):
        ref_contours = {contour.name: contour for contour in reference_pieces[piece_id].contours}
        cand_contours = {contour.name: contour for contour in candidate_pieces[piece_id].contours}
        structural.extend(f"missing contour: {piece_id}/{name}" for name in sorted(set(ref_contours) - set(cand_contours)))
        structural.extend(f"extra contour: {piece_id}/{name}" for name in sorted(set(cand_contours) - set(ref_contours)))
        for name in sorted(set(ref_contours) & set(cand_contours)):
            ref, cand = ref_contours[name], cand_contours[name]
            if ref.closed != cand.closed or len(ref.points) != len(cand.points):
                structural.append(f"shape mismatch: {piece_id}/{name}")
                continue
            deltas.extend(hypot(float(a.x - b.x), float(a.y - b.y)) for a, b in zip(ref.points, cand.points))
    max_delta = round(max(deltas, default=0.0), 6)
    return {"status": "PASS" if not structural and max_delta <= tolerance_mm else "FAIL", "toleranceMm": tolerance_mm, "maxPointDeltaMm": max_delta, "structuralErrors": structural, "comparedPoints": len(deltas)}


def pattern_to_dxf(pattern: Pattern) -> str:
    """Emit a deterministic R12-style polyline file labelled inspection-only."""
    pattern.validate_closed_contours()
    lines = ["0", "SECTION", "2", "HEADER", "9", "$COMMENT", "1", "BRAZEN INSPECTION ONLY - NOT MANUFACTURING APPROVAL; CURVES FLATTENED TO POLYLINE", "0", "ENDSEC", "0", "SECTION", "2", "ENTITIES"]
    for piece in sorted(pattern.pieces, key=lambda item: item.piece_id):
        for contour in sorted(piece.contours, key=lambda item: item.name):
            lines += ["0", "POLYLINE", "8", piece.piece_id, "66", "1", "70", "1"]
            export_points = contour._sampled_points()
            for point in export_points:
                lines += ["0", "VERTEX", "8", piece.piece_id, "10", f"{float(point.x):.1f}", "20", f"{float(point.y):.1f}", "30", "0.0"]
            first = export_points[0]
            lines += ["0", "VERTEX", "8", piece.piece_id, "10", f"{float(first.x):.1f}", "20", f"{float(first.y):.1f}", "30", "0.0", "0", "SEQEND"]
    lines += ["0", "ENDSEC", "0", "EOF", ""]
    return "\n".join(lines)
