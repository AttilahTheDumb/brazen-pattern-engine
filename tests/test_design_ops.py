from brazen_pattern_engine.cli import _pattern
from brazen_pattern_engine.design_ops import apply_seam_allowance, compare_patterns, grade_pattern, grade_table, pattern_to_dxf, smooth_contour


def rectangle(width=100, height=200):
    return _pattern({
        "compilerVersion": "compiler-v0.1",
        "pieces": [{"pieceId": "front", "blockVersion": "draft-0.1", "contours": [{
            "name": "outer", "closed": True,
            "points": [{"xMm": 0, "yMm": 0}, {"xMm": width, "yMm": 0}, {"xMm": width, "yMm": height}, {"xMm": 0, "yMm": height}],
        }], "seamGroups": {}}],
    })


def test_seam_allowance_offsets_closed_contour_deterministically():
    result = apply_seam_allowance(rectangle(), allowance_mm=10)
    points = result.pieces[0].contours[0].points
    assert [(float(p.x), float(p.y)) for p in points] == [(-10.0, -10.0), (110.0, -10.0), (110.0, 210.0), (-10.0, 210.0)]


def test_grading_applies_explicit_size_increment():
    result = grade_pattern(rectangle(), {"front": {"xMm": 5, "yMm": 8}})
    point = result.pieces[0].contours[0].points[1]
    assert (float(point.x), float(point.y)) == (105.0, 8.0)


def test_grade_table_returns_deterministic_named_size_variants():
    result = grade_table(rectangle(), {"S": {"front": {"xMm": -5, "yMm": -8}}, "L": {"front": {"xMm": 5, "yMm": 8}}})
    assert set(result) == {"S", "L"}
    assert float(result["L"].pieces[0].contours[0].points[1].x) == 105.0


def test_compare_reports_zero_for_identical_patterns():
    report = compare_patterns(rectangle(), rectangle(), tolerance_mm=0.1)
    assert report["status"] == "PASS"
    assert report["maxPointDeltaMm"] == 0.0


def test_dxf_export_is_explicitly_inspection_only():
    dxf = pattern_to_dxf(rectangle())
    assert "INSPECTION ONLY" in dxf
    assert "POLYLINE" in dxf and "VERTEX" in dxf


def test_smooth_contour_adds_cubic_handles_and_svg_curve_commands():
    result = smooth_contour(rectangle(), piece_id="front", contour_name="outer", tension=0.25)
    contour = result.pieces[0].contours[0]
    assert len(contour.controls) == 4
    assert any(handle is not None for pair in contour.controls for handle in pair)