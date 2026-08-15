"""Small deterministic 2D geometry kernel; not a physical fit model."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from html import escape
from math import isqrt
from typing import Iterable, Mapping

from .canonical import canonical_json, decimal_mm, sha256_json
from .errors import GateFailure, ValidationError


def _cross(a: "Point", b: "Point", c: "Point") -> int:
    return (b.x_ticks - a.x_ticks) * (c.y_ticks - a.y_ticks) - (b.y_ticks - a.y_ticks) * (c.x_ticks - a.x_ticks)


def _on_segment(a: "Point", b: "Point", p: "Point") -> bool:
    return min(a.x_ticks, b.x_ticks) <= p.x_ticks <= max(a.x_ticks, b.x_ticks) and min(a.y_ticks, b.y_ticks) <= p.y_ticks <= max(a.y_ticks, b.y_ticks)


def _segments_intersect(a: "Point", b: "Point", c: "Point", d: "Point") -> bool:
    ab_c, ab_d = _cross(a, b, c), _cross(a, b, d)
    cd_a, cd_b = _cross(c, d, a), _cross(c, d, b)
    if ab_c == 0 and _on_segment(a, b, c):
        return True
    if ab_d == 0 and _on_segment(a, b, d):
        return True
    if cd_a == 0 and _on_segment(c, d, a):
        return True
    if cd_b == 0 and _on_segment(c, d, b):
        return True
    return (ab_c > 0) != (ab_d > 0) and (cd_a > 0) != (cd_b > 0)


def _rounded_segment_length_ticks(dx: int, dy: int) -> int:
    squared = dx * dx + dy * dy
    lower = isqrt(squared)
    # Round sqrt(squared) to the nearest integer tick, half-up.
    return lower + int(4 * squared >= (2 * lower + 1) ** 2)


@dataclass(frozen=True, order=True)
class Point:
    x_ticks: int
    y_ticks: int

    def __init__(self, x: int | float | str | Decimal, y: int | float | str | Decimal):
        object.__setattr__(self, "x_ticks", int(decimal_mm(x) * 10))
        object.__setattr__(self, "y_ticks", int(decimal_mm(y) * 10))

    @property
    def x(self) -> Decimal:
        return Decimal(self.x_ticks) / 10

    @property
    def y(self) -> Decimal:
        return Decimal(self.y_ticks) / 10

    def to_dict(self) -> dict[str, str]:
        return {"xMm": f"{self.x:.1f}", "yMm": f"{self.y:.1f}"}


@dataclass(frozen=True)
class Polyline:
    name: str
    points: tuple[Point, ...]
    closed: bool = True

    def __post_init__(self) -> None:
        if not self.name:
            raise ValidationError("path name is required")
        if len(self.points) < (3 if self.closed else 2):
            raise ValidationError("closed paths need at least 3 points")
        if any(a == b for a, b in zip(self.points, self.points[1:])):
            raise ValidationError(f"{self.name}: consecutive duplicate points are invalid")
        if self.closed and self.points[0] == self.points[-1]:
            raise ValidationError(f"{self.name}: duplicate closing vertex is invalid")
        if self.closed:
            edges = list(zip(self.points, self.points[1:] + (self.points[0],)))
            for first, (a, b) in enumerate(edges):
                for second, (c, d) in enumerate(edges[first + 1:], start=first + 1):
                    if second == first + 1 or (first == 0 and second == len(edges) - 1):
                        continue
                    if _segments_intersect(a, b, c, d):
                        raise ValidationError(f"{self.name}: non-adjacent edges intersect")
        if self.closed and self.area_mm2() == 0:
            raise ValidationError(f"{self.name}: zero-area contour is invalid")

    def area_mm2(self) -> Decimal:
        points = self.points + ((self.points[0],) if self.closed else ())
        area_ticks2 = sum((a.x_ticks * b.y_ticks - b.x_ticks * a.y_ticks for a, b in zip(points, points[1:])), 0)
        return Decimal(area_ticks2) / 200

    def length_mm(self) -> Decimal:
        points = self.points + ((self.points[0],) if self.closed else ())
        total = Decimal(0)
        for a, b in zip(points, points[1:]):
            dx, dy = b.x_ticks - a.x_ticks, b.y_ticks - a.y_ticks
            total += Decimal(_rounded_segment_length_ticks(dx, dy)) / 10
        return total

    def to_dict(self) -> dict[str, object]:
        return {"name": self.name, "closed": self.closed, "points": [p.to_dict() for p in self.points]}


@dataclass(frozen=True)
class PatternPiece:
    piece_id: str
    block_version: str
    contours: tuple[Polyline, ...]
    seam_groups: Mapping[str, str] = None

    def __post_init__(self) -> None:
        if not self.piece_id or not self.block_version:
            raise ValidationError("piece_id and block_version are required")
        if not self.contours:
            raise ValidationError("a pattern piece requires at least one contour")
        names = [contour.name for contour in self.contours]
        if len(names) != len(set(names)):
            raise ValidationError(f"{self.piece_id}: contour names must be unique")
        if self.seam_groups is None:
            object.__setattr__(self, "seam_groups", {})

    def to_dict(self) -> dict[str, object]:
        return {
            "pieceId": self.piece_id,
            "blockVersion": self.block_version,
            "contours": [c.to_dict() for c in sorted(self.contours, key=lambda c: c.name)],
            "seamGroups": {k: self.seam_groups[k] for k in sorted(self.seam_groups)},
        }


@dataclass(frozen=True)
class Pattern:
    compiler_version: str
    pieces: tuple[PatternPiece, ...]
    source_spec_version: str = "0.1"

    def __post_init__(self) -> None:
        ids = [p.piece_id for p in self.pieces]
        if not ids or len(ids) != len(set(ids)):
            raise ValidationError("pattern pieces must have unique IDs")

    def to_dict(self) -> dict[str, object]:
        return {
            "sourceSpecVersion": self.source_spec_version,
            "compilerVersion": self.compiler_version,
            "pieces": [p.to_dict() for p in sorted(self.pieces, key=lambda p: p.piece_id)],
        }

    def canonical_json(self) -> str:
        return canonical_json(self.to_dict())

    def content_hash(self) -> str:
        return sha256_json(self.to_dict())

    def validate_closed_contours(self) -> None:
        for piece in self.pieces:
            for contour in piece.contours:
                if not contour.closed:
                    raise GateFailure(f"{piece.piece_id}/{contour.name}: contour is not closed")
                if contour.area_mm2() == 0:
                    raise GateFailure(f"{piece.piece_id}/{contour.name}: contour has zero area")

    def validate_seam_correspondence(self, *, tolerance_mm: float) -> None:
        if tolerance_mm <= 0:
            raise ValidationError("seam tolerance must be > 0")
        seams: dict[str, list[Decimal]] = {}
        for piece in self.pieces:
            by_name = {c.name: c for c in piece.contours}
            for contour_name, group in piece.seam_groups.items():
                if contour_name not in by_name:
                    raise GateFailure(f"{piece.piece_id}: seam group references missing contour {contour_name}")
                seams.setdefault(group, []).append(by_name[contour_name].length_mm())
        for group, lengths in seams.items():
            if len(lengths) < 2:
                continue
            if max(lengths) - min(lengths) > decimal_mm(tolerance_mm):
                raise GateFailure(f"seam group {group}: correspondence exceeds {tolerance_mm}mm")


def pattern_to_svg(pattern: Pattern) -> str:
    """Export an inspection SVG in mm units; this is not Phase 5 manufacturing sign-off."""
    pattern.validate_closed_contours()
    all_points = [p for piece in pattern.pieces for contour in piece.contours for p in contour.points]
    min_x = min((p.x for p in all_points), default=Decimal(0))
    min_y = min((p.y for p in all_points), default=Decimal(0))
    max_x = max((p.x for p in all_points), default=Decimal(1))
    max_y = max((p.y for p in all_points), default=Decimal(1))
    width = max_x - min_x
    height = max_y - min_y
    paths = []
    for piece in sorted(pattern.pieces, key=lambda p: p.piece_id):
        for contour in sorted(piece.contours, key=lambda c: c.name):
            commands = " ".join(([f"M {contour.points[0].x:.1f} {contour.points[0].y:.1f}"] + [f"L {p.x:.1f} {p.y:.1f}" for p in contour.points[1:]] + (["Z"] if contour.closed else [])))
            piece_id = escape(piece.piece_id, quote=True)
            contour_name = escape(contour.name, quote=True)
            paths.append(f'<path data-piece="{piece_id}" data-contour="{contour_name}" d="{commands}" fill="none" stroke="black" stroke-width="0.2" />')
    body = "\n  ".join(paths)
    return f'<?xml version="1.0" encoding="UTF-8"?>\n<svg xmlns="http://www.w3.org/2000/svg" width="{width:.1f}mm" height="{height:.1f}mm" viewBox="{min_x:.1f} {min_y:.1f} {width:.1f} {height:.1f}">\n  <metadata>Brazen inspection export; not Phase 5 manufacturing approval; compiler {escape(pattern.compiler_version)}; hash {pattern.content_hash()}</metadata>\n  {body}\n</svg>\n'
