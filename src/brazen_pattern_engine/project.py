"""Versioned project envelope and provenance helpers."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Mapping

from .canonical import sha256_json
from .geometry import Pattern

DOCUMENT_TYPE = "brazen.pattern.project"
SCHEMA_VERSION = "1.0"
_ALLOWED_TOP_LEVEL = {"documentType", "schemaVersion", "projectId", "projectName", "units", "geometry", "provenance", "revision", "constraints", "seamAllowance", "grading", "referenceComparison", "exports", "extensions"}


def build_project_document(pattern: Pattern, *, project_id: str, project_name: str, provenance: Mapping[str, object] | None = None, revision_id: str = "rev-0001", parent_revision_id: str | None = None) -> dict[str, object]:
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    return {
        "documentType": DOCUMENT_TYPE,
        "schemaVersion": SCHEMA_VERSION,
        "projectId": project_id,
        "projectName": project_name,
        "units": "mm",
        "geometry": pattern.to_dict(),
        "provenance": dict(provenance or {"status": "user-authored", "source": "local-browser", "physicalEvidence": False}),
        "revision": {"revisionId": revision_id, "parentRevisionId": parent_revision_id, "createdAt": now},
        "constraints": {"schemaVersion": SCHEMA_VERSION, "mode": "assert", "items": []},
        "seamAllowance": {"schemaVersion": SCHEMA_VERSION, "rules": []},
        "grading": {"schemaVersion": SCHEMA_VERSION, "baseSize": None, "sizes": []},
        "referenceComparison": None,
        "exports": [],
    }


def validate_project_document(document: Mapping[str, object]) -> dict[str, object]:
    errors: list[str] = []
    if not isinstance(document, Mapping):
        return {"status": "FAIL", "errors": ["project document must be an object"]}
    unknown = sorted(set(document) - _ALLOWED_TOP_LEVEL)
    errors.extend(f"unknown top-level field: {field}" for field in unknown)
    for field in ("documentType", "schemaVersion", "projectId", "projectName", "units"):
        if not isinstance(document.get(field), str) or not document[field]:
            errors.append(f"{field} is required")
    if document.get("documentType") != DOCUMENT_TYPE:
        errors.append("documentType must be brazen.pattern.project")
    if document.get("schemaVersion") != SCHEMA_VERSION:
        errors.append("schemaVersion must be 1.0")
    if document.get("units") != "mm":
        errors.append("units must be mm")
    if not isinstance(document.get("geometry"), Mapping) or not isinstance(document.get("geometry", {}).get("pieces"), list):
        errors.append("geometry.pieces must be an array")
    provenance = document.get("provenance")
    if not isinstance(provenance, Mapping) or not isinstance(provenance.get("status"), str):
        errors.append("provenance.status is required")
    revision = document.get("revision")
    if not isinstance(revision, Mapping) or not isinstance(revision.get("revisionId"), str):
        errors.append("revision.revisionId is required")
    return {"status": "PASS" if not errors else "FAIL", "errors": errors}


def project_hash(document: Mapping[str, object]) -> str:
    validation = validate_project_document(document)
    if validation["status"] != "PASS":
        raise ValueError("cannot hash invalid project document: " + "; ".join(validation["errors"]))
    return sha256_json(document)
