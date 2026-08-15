from brazen_pattern_engine.cli import _pattern
from brazen_pattern_engine.project import build_project_document, project_hash, validate_project_document


def pattern():
    return _pattern({"compilerVersion": "compiler-v0.1", "pieces": [{"pieceId": "front", "blockVersion": "draft-0.1", "contours": [{"name": "outer", "closed": True, "points": [{"xMm": 0, "yMm": 0}, {"xMm": 100, "yMm": 0}, {"xMm": 100, "yMm": 200}, {"xMm": 0, "yMm": 200}]}], "seamGroups": {}}]})


def test_project_document_has_provenance_and_stable_hash():
    document = build_project_document(pattern(), project_id="project-01", project_name="Front")
    assert validate_project_document(document)["status"] == "PASS"
    assert document["documentType"] == "brazen.pattern.project"
    assert document["units"] == "mm"
    assert project_hash(document) == project_hash(document)


def test_project_document_rejects_unknown_top_level_fields():
    document = build_project_document(pattern(), project_id="project-01", project_name="Front")
    document["surprise"] = True
    assert validate_project_document(document)["status"] == "FAIL"