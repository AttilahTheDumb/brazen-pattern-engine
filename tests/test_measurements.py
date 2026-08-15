from __future__ import annotations

import json
import math

import pytest

from brazen_pattern_engine.errors import ValidationError
from brazen_pattern_engine.measurements import (
    PRIMARY,
    MeasurementSession,
    REQUIRED_PROTOCOL_IDS,
    RepeatabilityStudy,
    derive_measurements,
    tolerance_budget_from_study,
)


def make_study() -> RepeatabilityStudy:
    sessions = []
    for subject_index in range(6):
        base = 880 + subject_index * 20
        for measurer_index, measurer in enumerate(("M1", "M2")):
            for session_index in range(2):
                offset = (measurer_index * 0.2) + (session_index * 0.1)
                sessions.append(MeasurementSession(
                    session_id=f"S{subject_index+1}-{measurer}-{session_index+1}",
                    subject_id=f"subject-{subject_index+1:03d}",
                    measurer_id=measurer,
                    created_at="2026-08-15T10:00:00+00:00",
                    conditions={"timeOfDay": "10:00", "clothing": "bare torso", "reLandmarkingCompleted": True},
                    values_mm={
                    measurement_id: (1750 + subject_index * 5 + offset if measurement_id == "STATURE" else base + offset)
                    for measurement_id in REQUIRED_PROTOCOL_IDS
                },
                    landmarks_confirmed=True,
                ))
    return RepeatabilityStudy(tuple(sessions))


def test_raw_values_survive_and_derived_values_are_separate():
    session = MeasurementSession(
        "S1", "subject-001", "M1", "2026-08-15T10:00:00Z", {},
        {"V_SHOULDER_DROP_L": 30.0, "H_SHOULDER_L": 150.0, "V_SHOULDER_DROP_R": 20.0, "H_SHOULDER_R": 140.0,
         "V_NP_WAIST_F_L": 500.0, "V_NP_WAIST_F_R": 496.0, "V_CF_WAIST": 510.0, "V_CB_WAIST": 500.0, "STATURE": 1800.0},
        landmarks_confirmed=True,
    )
    derived = derive_measurements(session.values_mm)
    assert session.values_mm["V_SHOULDER_DROP_L"] == 30.0
    assert math.isclose(derived["A_SLOPE_L"], math.degrees(math.asin(0.2)))
    assert derived["ASYM_LENGTH_F"] == 4.0
    assert derived["BALANCE"] == 10.0
    assert "A_SLOPE_L" not in session.values_mm


def test_repeatability_study_produces_primary_measurement_and_budget():
    study = make_study()
    results = {result.measurement_id: result for result in study.results(max_relative_tem_pct=1.5)}
    assert results["G_CHEST"].classification == PRIMARY
    assert results["G_CHEST"].inter_tem_mm is not None
    budget = tolerance_budget_from_study(study, max_relative_tem_pct=1.5)
    assert budget.input_mm > 0
    assert budget.fit_mm == 2 * budget.input_mm
    assert budget.geometric_mm == 0.1


def test_reliability_uses_between_subject_standard_deviation():
    study = make_study()
    result = {r.measurement_id: r for r in study.results(max_relative_tem_pct=1.5)}["G_CHEST"]
    subject_means = []
    for subject_index in range(6):
        base = 880 + subject_index * 20
        subject_means.append(base + 0.25)
    import statistics
    between_subject_sd = statistics.stdev(subject_means)
    expected = max(0.0, min(1.0, 1 - (result.inter_tem_mm ** 2 / between_subject_sd ** 2)))
    assert result.reliability == pytest.approx(expected)


def test_primary_classification_requires_an_explicit_low_tem_policy():
    study = make_study()
    assert all(result.classification != PRIMARY for result in study.results())
    with pytest.raises(ValidationError, match="no PRIMARY"):
        tolerance_budget_from_study(study)


def test_study_requires_minimum_design():
    session = MeasurementSession("S1", "subject-001", "M1", "2026-08-15T10:00:00Z", {}, {"G_CHEST": 900}, landmarks_confirmed=True)
    with pytest.raises(ValidationError, match="at least 6 subjects"):
        RepeatabilityStudy((session,))


def test_study_rejects_extra_duplicate_sessions_instead_of_silently_ignoring_them():
    study = make_study()
    extra = MeasurementSession(
        "S1-M1-3", "subject-001", "M1", "2026-08-15T10:00:00+00:00", {"reLandmarkingCompleted": True},
        {measurement_id: (1750.4 if measurement_id == "STATURE" else 880.4) for measurement_id in REQUIRED_PROTOCOL_IDS}, landmarks_confirmed=True,
    )
    with pytest.raises(ValidationError, match="exactly two"):
        RepeatabilityStudy(study.sessions + (extra,))


def test_invalid_shoulder_triangle_fails_closed():
    with pytest.raises(ValidationError, match="cannot exceed"):
        derive_measurements({"V_SHOULDER_DROP_L": 151, "H_SHOULDER_L": 150, "V_SHOULDER_DROP_R": 20, "H_SHOULDER_R": 140})


def test_raw_session_rejects_derived_ids_and_naive_timestamps():
    with pytest.raises(ValidationError, match="unknown or derived"):
        MeasurementSession("S1", "subject-001", "M1", "2026-08-15T10:00:00+00:00", {}, {"A_SLOPE_L": 10}, landmarks_confirmed=True)
    with pytest.raises(ValidationError, match="timezone"):
        MeasurementSession("S1", "subject-001", "M1", "2026-08-15T10:00:00", {}, {"G_CHEST": 900}, landmarks_confirmed=True)


def test_from_dict_does_not_coerce_string_booleans():
    with pytest.raises(ValidationError, match="landmarksConfirmed"):
        MeasurementSession.from_dict({
            "sessionId": "S1",
            "subjectId": "subject-001",
            "measurerId": "M1",
            "createdAt": "2026-08-15T10:00:00+00:00",
            "valuesMm": {"G_CHEST": 900},
            "landmarksConfirmed": "false",
        })


def test_captured_session_mappings_are_immutable():
    session = MeasurementSession("S1", "subject-001", "M1", "2026-08-15T10:00:00+00:00", {}, {"G_CHEST": 900}, landmarks_confirmed=True)
    with pytest.raises(TypeError):
        session.values_mm["G_CHEST"] = 901


def test_repeatability_requires_relandmarking_evidence():
    sessions = list(make_study().sessions)
    sessions[0] = MeasurementSession(
        sessions[0].session_id, sessions[0].subject_id, sessions[0].measurer_id,
        sessions[0].created_at, {}, sessions[0].values_mm, landmarks_confirmed=True,
    )
    with pytest.raises(ValidationError, match="re-landmarking"):
        RepeatabilityStudy(tuple(sessions))
