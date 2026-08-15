"""Fail-closed validation for the normative fit-correction record."""

from __future__ import annotations

import datetime as dt
import math
import re
from collections.abc import Mapping

from .errors import ValidationError

_RECORD = re.compile(r"^FC-[0-9]{5}$")
_VERSION = re.compile(r"^[A-Za-z0-9-]+-v[0-9]+\.[0-9]+$")
_ALLOWED_STATUSES = {"provisional", "verified", "superseded", "rejected"}
_ALLOWED_TARGETS = {"block", "garment", "ambiguous"}
_TOP_LEVEL_FIELDS = {
    "recordId", "createdAt", "schemaVersion", "subjectId", "measurementSessionId",
    "morphology", "blockVersion", "garmentVersion", "correctionTarget", "material",
    "construction", "prototype", "observations", "corrections", "assessedBy",
    "wearTest", "verification", "status",
}
_MATERIAL_CLASSES = {
    "calico_toile", "cotton_drill", "wool_suiting", "lambskin", "goatskin",
    "calfskin", "veg_tan", "chrome_tan", "bonded_composite", "other",
}
_OBSERVATION_REGIONS = {
    "centre_front", "centre_back", "left_shoulder", "right_shoulder", "left_armhole",
    "right_armhole", "left_side_seam", "right_side_seam", "neckline_front",
    "neckline_back", "chest_front", "upper_back", "waist_front", "waist_back",
    "hem", "closure",
}
_OBSERVATION_SYMPTOMS = {
    "drag_lines_diagonal", "drag_lines_horizontal", "drag_lines_vertical", "gaping",
    "bubbling_excess", "binding_tight", "riding_up", "dropping_down", "twisting",
    "collapsing", "standing_away", "seam_not_vertical", "seam_not_horizontal",
    "hem_not_level", "insufficient_movement", "hardware_fouling", "correct_no_issue",
}
_SEVERITIES = {"marginal", "moderate", "severe"}
_UNITS = {"mm", "deg", "ratio", "count"}


def validate_fit_correction(record: Mapping[str, object], *, tolerance_fit_mm: float) -> list[str]:
    errors: list[str] = []
    if not isinstance(record, Mapping):
        return ["record must be an object"]
    unknown = sorted(set(record) - _TOP_LEVEL_FIELDS)
    errors.extend(f"unknown top-level field: {name}" for name in unknown)
    _required(record, ["recordId", "createdAt", "subjectId", "measurementSessionId", "blockVersion", "material", "construction", "prototype", "observations", "assessedBy"], errors)
    if not isinstance(tolerance_fit_mm, (int, float)) or tolerance_fit_mm <= 0 or not math.isfinite(tolerance_fit_mm):
        errors.append("tolerance_fit_mm must be finite and > 0")
    if "recordId" in record and (not isinstance(record["recordId"], str) or not _RECORD.fullmatch(record["recordId"])):
        errors.append("recordId must match FC-00000")
    if "schemaVersion" in record and record["schemaVersion"] != "0.1":
        errors.append("schemaVersion must be 0.1")
    if "createdAt" in record:
        try:
            dt.datetime.fromisoformat(str(record["createdAt"]).replace("Z", "+00:00"))
        except ValueError:
            errors.append("createdAt must be an ISO-8601 date-time")
    if "subjectId" in record and (not isinstance(record["subjectId"], str) or not record["subjectId"] or any(ch.isspace() for ch in record["subjectId"])):
        errors.append("subjectId must be a stable pseudonymous non-whitespace ID")
    if "blockVersion" in record and (not isinstance(record["blockVersion"], str) or not _VERSION.fullmatch(record["blockVersion"])):
        errors.append("blockVersion has invalid version format")
    if record.get("garmentVersion") is not None and (not isinstance(record["garmentVersion"], str) or not _VERSION.fullmatch(record["garmentVersion"])):
        errors.append("garmentVersion has invalid version format")
    target = record.get("correctionTarget")
    if target is None:
        errors.append("correctionTarget is required for eligibility")
    elif target not in _ALLOWED_TARGETS:
        errors.append("correctionTarget is invalid")
    if target == "block" and record.get("garmentVersion") is not None:
        errors.append("block corrections with a garmentVersion are ambiguous")
    status = record.get("status", "provisional")
    if status not in _ALLOWED_STATUSES:
        errors.append("status is invalid")
    material = record.get("material")
    if not isinstance(material, Mapping) or material.get("class") is None or not isinstance(material.get("thicknessMm"), (int, float)):
        errors.append("material.class and material.thicknessMm are required")
    else:
        if material.get("class") not in _MATERIAL_CLASSES:
            errors.append("material.class is invalid")
        if not math.isfinite(float(material["thicknessMm"])) or not 0.1 <= float(material["thicknessMm"]) <= 10:
            errors.append("material.thicknessMm must be between 0.1 and 10")
        if "isToile" not in material:
            errors.append("material.isToile is required for eligibility")
        elif not isinstance(material["isToile"], bool):
            errors.append("material.isToile must be boolean")
    prototype = record.get("prototype")
    if not isinstance(prototype, Mapping) or not prototype.get("patternHash") or not prototype.get("compilerVersion"):
        errors.append("prototype.patternHash and prototype.compilerVersion are required")
    observations = record.get("observations")
    if not isinstance(observations, list) or len(observations) < 1:
        errors.append("observations must contain at least one entry")
    else:
        for i, observation in enumerate(observations):
            if not isinstance(observation, Mapping):
                errors.append(f"observations[{i}] must be an object")
                continue
            if observation.get("region") not in _OBSERVATION_REGIONS:
                errors.append(f"observations[{i}].region is invalid")
            if observation.get("symptom") not in _OBSERVATION_SYMPTOMS:
                errors.append(f"observations[{i}].symptom is invalid")
            if observation.get("severity") not in _SEVERITIES:
                errors.append(f"observations[{i}].severity is invalid")
    corrections = record.get("corrections", [])
    if not isinstance(corrections, list):
        errors.append("corrections must be an array")
        corrections = []
    for i, correction in enumerate(corrections):
        _validate_correction(correction, i, len(observations) if isinstance(observations, list) else 0, tolerance_fit_mm, errors)
    verification = record.get("verification")
    if status == "verified":
        if not isinstance(verification, Mapping) or not verification.get("verifiedByRecordId"):
            errors.append("verified records require verification.verifiedByRecordId")
        elif not isinstance(verification.get("verifiedByRecordId"), str) or not _RECORD.fullmatch(verification["verifiedByRecordId"]):
            errors.append("verification.verifiedByRecordId must match FC-00000")
        if verification and verification.get("verifiedByRecordId") == record.get("recordId"):
            errors.append("a record cannot verify itself")
    if target == "ambiguous" and status == "verified":
        errors.append("ambiguous corrections cannot be verified for aggregation")
    if isinstance(material, Mapping) and material.get("isToile") is True and status == "verified":
        errors.append("toile corrections cannot be verified as final-material evidence")
    return errors


def _required(record: Mapping[str, object], names: list[str], errors: list[str]) -> None:
    for name in names:
        if name not in record:
            errors.append(f"missing required field: {name}")


def _validate_correction(correction: object, index: int, observation_count: int, tolerance_fit_mm: float, errors: list[str]) -> None:
    prefix = f"corrections[{index}]"
    if not isinstance(correction, Mapping):
        errors.append(f"{prefix} must be an object")
        return
    for field in ("parameter", "generatedValue", "correctedValue", "unit", "addressesObservations"):
        if field not in correction:
            errors.append(f"{prefix}.{field} is required")
    if not isinstance(correction.get("parameter"), str) or not correction.get("parameter"):
        errors.append(f"{prefix}.parameter must name a versioned parameter")
    generated = correction.get("generatedValue")
    corrected = correction.get("correctedValue")
    if not isinstance(generated, (int, float)) or isinstance(generated, bool) or not math.isfinite(float(generated)):
        errors.append(f"{prefix}.generatedValue must be finite")
    if not isinstance(corrected, (int, float)) or isinstance(corrected, bool) or not math.isfinite(float(corrected)):
        errors.append(f"{prefix}.correctedValue must be finite")
    if isinstance(generated, (int, float)) and isinstance(corrected, (int, float)):
        expected = float(corrected) - float(generated)
        if "deltaValue" in correction:
            supplied_delta = correction["deltaValue"]
            if not isinstance(supplied_delta, (int, float)) or isinstance(supplied_delta, bool) or not math.isfinite(float(supplied_delta)):
                errors.append(f"{prefix}.deltaValue must be finite")
            elif abs(float(supplied_delta) - expected) > 1e-9:
                errors.append(f"{prefix}.deltaValue does not equal correctedValue-generatedValue")
        if "exceedsNoiseFloor" in correction:
            flag = correction["exceedsNoiseFloor"]
            if not isinstance(flag, bool):
                errors.append(f"{prefix}.exceedsNoiseFloor must be boolean")
            elif flag != (abs(expected) >= tolerance_fit_mm):
                errors.append(f"{prefix}.exceedsNoiseFloor is not the computed noise-floor result")
    if correction.get("unit") not in _UNITS:
        errors.append(f"{prefix}.unit is invalid")
    elif correction.get("unit") != "mm":
        errors.append(f"{prefix}.unit has no configured noise floor; only mm corrections are trainable in v0.1")
    addresses = correction.get("addressesObservations")
    if not isinstance(addresses, list) or not addresses:
        errors.append(f"{prefix}.addressesObservations must contain at least one index")
    elif any(not isinstance(x, int) or isinstance(x, bool) or x < 0 or x >= observation_count for x in addresses):
        errors.append(f"{prefix}.addressesObservations contains an invalid observation index")


def is_trainable_correction(record: Mapping[str, object], *, tolerance_fit_mm: float) -> bool:
    """Only verified, non-ambiguous, non-toile, above-noise-floor records train/aggregate."""
    errors = validate_fit_correction(record, tolerance_fit_mm=tolerance_fit_mm)
    if errors:
        return False
    if record.get("status") != "verified" or record.get("correctionTarget") == "ambiguous":
        return False
    verification = record.get("verification")
    if not isinstance(verification, Mapping) or verification.get("outcome") != "resolved":
        return False
    if not record.get("corrections"):
        return False
    for correction in record.get("corrections", []):
        delta = float(correction["correctedValue"]) - float(correction["generatedValue"])
        if abs(delta) < tolerance_fit_mm:
            return False
    return True
