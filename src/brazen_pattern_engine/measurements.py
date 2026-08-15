"""Raw measurement sessions, derived values, TEM and tolerance budgeting."""

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass, field
from datetime import datetime
from types import MappingProxyType
from typing import Iterable, Mapping

from .errors import ValidationError

PRIMARY = "PRIMARY"
DERIVED = "DERIVED"
DIAGNOSTIC = "DIAGNOSTIC"
PROVISIONAL_DERIVED = "PROVISIONAL-DERIVED"
DERIVED_IDS = {"A_SLOPE_L", "A_SLOPE_R", "ASYM_SHOULDER", "ASYM_LENGTH_F", "BALANCE", "TORSO_RATIO", "H_SHOULDER_TOTAL"}

REQUIRED_PROTOCOL_IDS = {
    "STATURE", "G_NECK", "G_CHEST", "G_SCYE", "G_WAIST", "G_HHIP", "G_HIP",
    "G_ARMSCYE_L", "G_ARMSCYE_R", "G_BICEP_L", "G_BICEP_R", "V_CB_WAIST",
    "V_CF_WAIST", "V_SCYE_DEPTH", "V_NP_WAIST_F_L", "V_NP_WAIST_F_R",
    "V_NP_WAIST_B_L", "V_NP_WAIST_B_R", "V_SIDE", "V_SHOULDER_DROP_L",
    "V_SHOULDER_DROP_R", "H_ACROSS_BACK", "H_ACROSS_CHEST", "H_SHOULDER_L",
    "H_SHOULDER_R",
}


@dataclass(frozen=True)
class MeasurementSession:
    session_id: str
    subject_id: str
    measurer_id: str
    created_at: str
    conditions: Mapping[str, str]
    values_mm: Mapping[str, float]
    landmarks_confirmed: bool = False
    notes: str = ""

    def __post_init__(self) -> None:
        for name, value in self.values_mm.items():
            if not isinstance(name, str) or not name:
                raise ValidationError("measurement IDs must be non-empty strings", path="values_mm")
            if name not in REQUIRED_PROTOCOL_IDS:
                raise ValidationError("raw session contains unknown or derived measurement ID", path=f"values_mm.{name}")
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValidationError("raw measurement must be a finite number", path=f"values_mm.{name}")
            if value <= 0:
                raise ValidationError("raw measurement must be > 0", path=f"values_mm.{name}")
        if not self.session_id or not self.subject_id or not self.measurer_id:
            raise ValidationError("session_id, subject_id and measurer_id are required")
        try:
            timestamp = datetime.fromisoformat(self.created_at.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValidationError("created_at must be an ISO-8601 timestamp") from exc
        if timestamp.tzinfo is None or timestamp.utcoffset() is None:
            raise ValidationError("created_at must include a timezone offset")
        if not self.landmarks_confirmed:
            raise ValidationError("landmarks_confirmed must be true before a session enters analysis")
        object.__setattr__(self, "conditions", MappingProxyType(dict(self.conditions)))
        object.__setattr__(self, "values_mm", MappingProxyType(dict(self.values_mm)))

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> "MeasurementSession":
        try:
            landmarks_confirmed = data.get("landmarksConfirmed", False)
            if not isinstance(landmarks_confirmed, bool):
                raise ValidationError("landmarksConfirmed must be boolean")
            values = data["valuesMm"]
            conditions = data.get("conditions", {})
            if not isinstance(values, Mapping) or not isinstance(conditions, Mapping):
                raise ValidationError("valuesMm and conditions must be objects")
            return cls(
                session_id=str(data["sessionId"]),
                subject_id=str(data["subjectId"]),
                measurer_id=str(data["measurerId"]),
                created_at=str(data["createdAt"]),
                conditions=dict(conditions),
                values_mm=dict(values),
                landmarks_confirmed=landmarks_confirmed,
                notes=str(data.get("notes", "")),
            )
        except KeyError as exc:
            raise ValidationError(f"missing required field {exc.args[0]}") from exc

    def to_dict(self) -> dict[str, object]:
        return {
            "sessionId": self.session_id,
            "subjectId": self.subject_id,
            "measurerId": self.measurer_id,
            "createdAt": self.created_at,
            "conditions": dict(self.conditions),
            "valuesMm": dict(self.values_mm),
            "landmarksConfirmed": self.landmarks_confirmed,
            "notes": self.notes,
        }


def derive_measurements(values_mm: Mapping[str, float]) -> dict[str, float]:
    """Calculate only protocol-defined derivations; never mutate raw inputs."""
    out: dict[str, float] = {}
    try:
        out["A_SLOPE_L"] = math.degrees(math.asin(values_mm["V_SHOULDER_DROP_L"] / values_mm["H_SHOULDER_L"]))
        out["A_SLOPE_R"] = math.degrees(math.asin(values_mm["V_SHOULDER_DROP_R"] / values_mm["H_SHOULDER_R"]))
    except KeyError:
        pass
    except ValueError as exc:
        raise ValidationError("shoulder drop cannot exceed straight-line shoulder length") from exc
    if "A_SLOPE_L" in out and "A_SLOPE_R" in out:
        out["ASYM_SHOULDER"] = out["A_SLOPE_L"] - out["A_SLOPE_R"]
    if "V_NP_WAIST_F_L" in values_mm and "V_NP_WAIST_F_R" in values_mm:
        out["ASYM_LENGTH_F"] = values_mm["V_NP_WAIST_F_L"] - values_mm["V_NP_WAIST_F_R"]
    if "V_CF_WAIST" in values_mm and "V_CB_WAIST" in values_mm:
        out["BALANCE"] = values_mm["V_CF_WAIST"] - values_mm["V_CB_WAIST"]
    if "V_CB_WAIST" in values_mm and "STATURE" in values_mm:
        out["TORSO_RATIO"] = values_mm["V_CB_WAIST"] / values_mm["STATURE"]
    return out


def classify_measurement(
    reliability: float | None,
    relative_tem_pct: float | None = None,
    *,
    max_relative_tem_pct: float | None = None,
    provisional: bool = False,
) -> str:
    if provisional:
        return PROVISIONAL_DERIVED
    if (
        reliability is not None
        and reliability >= 0.95
        and relative_tem_pct is not None
        and max_relative_tem_pct is not None
        and relative_tem_pct <= max_relative_tem_pct
    ):
        return PRIMARY
    return DIAGNOSTIC


@dataclass(frozen=True)
class MeasurementResult:
    measurement_id: str
    mean_mm: float
    intra_tem_mm: float | None
    inter_tem_mm: float | None
    relative_tem_pct: float | None
    reliability: float | None
    classification: str


@dataclass(frozen=True)
class RepeatabilityStudy:
    """A complete study is 6 subjects × 2 measurers × 2 sessions at minimum."""

    sessions: tuple[MeasurementSession, ...]

    def __post_init__(self) -> None:
        if len({s.subject_id for s in self.sessions}) < 6:
            raise ValidationError("repeatability study requires at least 6 subjects")
        if len({s.session_id for s in self.sessions}) != len(self.sessions):
            raise ValidationError("session IDs must be unique")
        measurers = {s.measurer_id for s in self.sessions}
        if len(measurers) != 2:
            raise ValidationError("repeatability study v0.1 requires exactly 2 measurers")
        measurement_ids = {frozenset(s.values_mm) for s in self.sessions}
        if len(measurement_ids) != 1:
            raise ValidationError("every session must contain the same measurement IDs")
        if next(iter(measurement_ids)) != frozenset(REQUIRED_PROTOCOL_IDS):
            raise ValidationError("every session must contain the complete 25-measurement protocol set")
        if any(s.conditions.get("reLandmarkingCompleted") is not True for s in self.sessions):
            raise ValidationError("every repeatability session must record re-landmarking completion")
        for subject in {s.subject_id for s in self.sessions}:
            rows = [s for s in self.sessions if s.subject_id == subject]
            if len({s.measurer_id for s in rows}) < 2:
                raise ValidationError(f"subject {subject} lacks two measurers")
            for measurer in measurers:
                count = sum(1 for x in rows if x.measurer_id == measurer)
                if count != 2:
                    raise ValidationError(f"subject {subject} requires exactly two sessions for {measurer}")

    def results(self, *, max_relative_tem_pct: float | None = None) -> list[MeasurementResult]:
        if max_relative_tem_pct is not None and (not math.isfinite(max_relative_tem_pct) or max_relative_tem_pct <= 0):
            raise ValidationError("max_relative_tem_pct must be finite and > 0")
        ids = sorted({k for s in self.sessions for k in s.values_mm})
        subjects = sorted({s.subject_id for s in self.sessions})
        out: list[MeasurementResult] = []
        for measurement_id in ids:
            values = [s.values_mm[measurement_id] for s in self.sessions if measurement_id in s.values_mm]
            if not values:
                continue
            by_subject_measurer_raw: dict[tuple[str, str], list[tuple[str, float]]] = {}
            by_subject: dict[str, list[MeasurementSession]] = {}
            for session in self.sessions:
                if measurement_id in session.values_mm:
                    by_subject_measurer_raw.setdefault((session.subject_id, session.measurer_id), []).append((session.session_id, session.values_mm[measurement_id]))
                    by_subject.setdefault(session.subject_id, []).append(session)
            by_subject_measurer = {
                key: [value for _, value in sorted(rows, key=lambda row: row[0])]
                for key, rows in by_subject_measurer_raw.items()
            }
            subject_means = [
                statistics.fmean(session.values_mm[measurement_id] for session in by_subject[subject])
                for subject in subjects
            ]
            intra_diffs = []
            for pair in by_subject_measurer.values():
                if len(pair) >= 2:
                    intra_diffs.append(pair[1] - pair[0])
            inter_diffs = []
            for subject in subjects:
                measurer_means = [
                    statistics.fmean(by_subject_measurer[(subject, measurer)])
                    for measurer in sorted({s.measurer_id for s in self.sessions})
                ]
                inter_diffs.append(measurer_means[1] - measurer_means[0])
            intra = _tem(intra_diffs)
            inter = _tem(inter_diffs)
            mean = statistics.fmean(values)
            sd = statistics.stdev(subject_means) if len(subject_means) > 1 else None
            reliability = (1 - (inter * inter / (sd * sd))) if inter is not None and sd and sd > 0 else None
            relative = (inter / mean * 100) if inter is not None and mean else None
            out.append(MeasurementResult(
                measurement_id,
                mean,
                intra,
                inter,
                relative,
                reliability,
                classify_measurement(reliability, relative, max_relative_tem_pct=max_relative_tem_pct),
            ))
        return out


def _tem(differences: Iterable[float]) -> float | None:
    diffs = list(differences)
    if not diffs:
        return None
    return math.sqrt(sum(d * d for d in diffs) / (2 * len(diffs)))


@dataclass(frozen=True)
class ToleranceBudget:
    input_mm: float
    geometric_mm: float = 0.1
    fit_mm: float = field(init=False)

    def __post_init__(self) -> None:
        if not math.isfinite(self.input_mm) or self.input_mm <= 0:
            raise ValidationError("input tolerance must be finite and > 0")
        if not math.isclose(self.geometric_mm, 0.1, rel_tol=0.0, abs_tol=1e-12):
            raise ValidationError("geometric tolerance is fixed at 0.1mm by protocol v0.1")
        object.__setattr__(self, "fit_mm", 2 * self.input_mm)


def tolerance_budget_from_study(study: RepeatabilityStudy, *, max_relative_tem_pct: float | None = None) -> ToleranceBudget:
    results = study.results(max_relative_tem_pct=max_relative_tem_pct)
    primary_inter = [r.inter_tem_mm for r in results if r.classification == PRIMARY and r.inter_tem_mm is not None]
    if not primary_inter:
        raise ValidationError("cannot fix tolerance budget: no PRIMARY measurements with inter-measurer TEM")
    return ToleranceBudget(max(primary_inter))
