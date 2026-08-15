from brazen_pattern_engine.errors import GateFailure
from brazen_pattern_engine.geometry import Pattern, PatternPiece, Point, Polyline, pattern_to_svg


def square(name, x=0):
    return Polyline(name, (Point(x, 0), Point(x + 100, 0), Point(x + 100, 200), Point(x, 200)))


def make_pattern(reverse=False):
    left = PatternPiece("left", "Block-v1.0", (square("seam", 0),), {"seam": "centre"})
    right = PatternPiece("right", "Block-v1.0", (square("seam", 0),), {"seam": "centre"})
    pieces = (right, left) if reverse else (left, right)
    return Pattern("compiler-v0.1", pieces)


def test_geometry_is_quantised_and_hash_is_order_independent():
    point = Point(1.04, 2.06)
    assert point.to_dict() == {"xMm": "1.0", "yMm": "2.1"}
    assert point.x_ticks == 10
    assert point.y_ticks == 21
    assert make_pattern().content_hash() == make_pattern(True).content_hash()


def test_closed_contours_and_seam_correspondence_pass():
    pattern = make_pattern()
    pattern.validate_closed_contours()
    pattern.validate_seam_correspondence(tolerance_mm=0.1)
    assert len(pattern.content_hash()) == 64


def test_open_contour_is_a_binary_gate():
    pattern = Pattern("compiler-v0.1", (PatternPiece("left", "Block-v1.0", (Polyline("seam", (Point(0, 0), Point(100, 0), Point(100, 100)), closed=False),)),))
    try:
        pattern.validate_closed_contours()
    except GateFailure as exc:
        assert "not closed" in str(exc)
    else:
        raise AssertionError("open contour should fail")


def test_seam_mismatch_fails():
    left = PatternPiece("left", "Block-v1.0", (square("seam"),), {"seam": "join"})
    right = PatternPiece("right", "Block-v1.0", (Polyline("seam", (Point(0, 0), Point(90, 0), Point(90, 200), Point(0, 200))),), {"seam": "join"})
    pattern = Pattern("compiler-v0.1", (left, right))
    try:
        pattern.validate_seam_correspondence(tolerance_mm=0.1)
    except GateFailure as exc:
        assert "exceeds" in str(exc)
    else:
        raise AssertionError("seam mismatch should fail")


def test_duplicate_contour_names_fail():
    try:
        PatternPiece("left", "Block-v1.0", (square("outer"), square("outer")))
    except ValueError as exc:
        assert "contour names" in str(exc)
    else:
        raise AssertionError("duplicate contour names should fail")


def test_duplicate_closing_vertex_and_bow_tie_fail():
    try:
        Polyline("duplicate", (Point(0, 0), Point(10, 0), Point(10, 10), Point(0, 0)))
    except ValueError as exc:
        assert "closing" in str(exc)
    else:
        raise AssertionError("duplicate closing vertex should fail")
    try:
        Polyline("bow-tie", (Point(0, 0), Point(10, 10), Point(0, 10), Point(10, 0)))
    except ValueError as exc:
        assert "intersect" in str(exc)
    else:
        raise AssertionError("self-intersecting contour should fail")


def test_rendered_curve_self_intersection_is_rejected():
    points = (Point(0, 0), Point(100, 0), Point(100, 100), Point(0, 100))
    controls = (
        (Point(-63.4, -125.7), Point(54.3, -153.9)),
        (Point(12.9, -48.4), Point(-159.1, 2.7)),
        (Point(-166.5, -23.9), Point(-154.9, -147.3)),
        (Point(-27.2, 117.7), Point(-135.4, -99.6)),
    )
    try:
        Polyline("curved-crossing", points, True, controls)
    except ValueError as exc:
        assert "rendered curve self-intersects" in str(exc)
    else:
        raise AssertionError("rendered self-intersecting curve should fail")


def test_svg_preserves_negative_bounds_and_escapes_identifiers():
    piece = PatternPiece("left<&", "Block-v1.0", (Polyline("outer<&", (Point(-10, -20), Point(0, -20), Point(0, 0), Point(-10, 0))),))
    svg = pattern_to_svg(Pattern("compiler-v0.1", (piece,)))
    assert 'viewBox="-10.0 -20.0 10.0 20.0"' in svg
    assert 'data-piece="left&lt;&amp;"' in svg
    assert '<path ' in svg and ' Z"' in svg
