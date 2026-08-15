from brazen_pattern_engine.cli import _pattern
from brazen_pattern_engine.constraints import evaluate_constraints


def pattern():
    return _pattern({"compilerVersion": "compiler-v0.1", "pieces": [{"pieceId": "front", "blockVersion": "draft-0.1", "contours": [{"name": "outer", "closed": True, "points": [{"xMm": 0, "yMm": 0}, {"xMm": 100, "yMm": 0}, {"xMm": 100, "yMm": 200}, {"xMm": 0, "yMm": 200}]}], "seamGroups": {}}]})


def test_dimension_constraint_passes_against_authored_geometry():
    result = evaluate_constraints(pattern(), [{"pieceId": "front", "contour": "outer", "fromIndex": 0, "toIndex": 1, "kind": "distance", "valueMm": 100, "toleranceMm": 0.1}])
    assert result["status"] == "PASS"
    assert result["constraints"][0]["actualMm"] == 100.0


def test_dimension_constraint_fails_closed_when_outside_tolerance():
    result = evaluate_constraints(pattern(), [{"pieceId": "front", "contour": "outer", "fromIndex": 0, "toIndex": 1, "kind": "distance", "valueMm": 101, "toleranceMm": 0.1}])
    assert result["status"] == "FAIL"
    assert result["constraints"][0]["status"] == "FAIL"


def test_dimension_constraint_can_bind_to_explicit_measurement_profile():
    result = evaluate_constraints(pattern(), [{"pieceId": "front", "contour": "outer", "fromIndex": 0, "toIndex": 1, "kind": "distance", "measurementId": "G_CHEST", "toleranceMm": 0.1}], {"G_CHEST": 100})
    assert result["status"] == "PASS"
    assert result["constraints"][0]["source"] == "measurement:G_CHEST"