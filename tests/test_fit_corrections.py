from brazen_pattern_engine.fit_corrections import is_trainable_correction, validate_fit_correction


def record(**overrides):
    value = {
        "recordId": "FC-00001",
        "createdAt": "2026-08-15T10:00:00Z",
        "schemaVersion": "0.1",
        "subjectId": "subject-001",
        "measurementSessionId": "session-001",
        "blockVersion": "JosephBlock-v0.3",
        "garmentVersion": None,
        "correctionTarget": "block",
        "material": {"class": "calico_toile", "thicknessMm": 0.5, "isToile": False},
        "construction": {},
        "prototype": {"patternHash": "a" * 64, "compilerVersion": "compiler-v0.1"},
        "observations": [{"region": "left_shoulder", "symptom": "gaping", "severity": "moderate"}],
        "corrections": [{"parameter": "block.armscyeDepthMm", "generatedValue": 10.0, "correctedValue": 20.0, "deltaValue": 10.0, "unit": "mm", "addressesObservations": [0], "exceedsNoiseFloor": True}],
        "assessedBy": {"role": "pattern_cutter", "personId": "pc-001", "experienceWithMaterial": "familiar"},
        "verification": {"verifiedByRecordId": "FC-00002", "outcome": "resolved"},
        "status": "verified",
    }
    value.update(overrides)
    return value


def test_verified_record_is_trainable_only_above_floor():
    assert validate_fit_correction(record(), tolerance_fit_mm=10) == []
    assert is_trainable_correction(record(), tolerance_fit_mm=10)


def test_delta_and_noise_floor_are_not_user_assertions():
    bad = record(corrections=[{"parameter": "block.x", "generatedValue": 10, "correctedValue": 10.5, "deltaValue": 99, "unit": "mm", "addressesObservations": [0], "exceedsNoiseFloor": True}])
    errors = validate_fit_correction(bad, tolerance_fit_mm=10)
    assert any("deltaValue" in e for e in errors)
    assert any("exceedsNoiseFloor" in e for e in errors)
    assert not is_trainable_correction(bad, tolerance_fit_mm=10)


def test_ambiguous_and_self_verified_records_fail_closed():
    ambiguous = record(correctionTarget="ambiguous")
    assert any("ambiguous" in e for e in validate_fit_correction(ambiguous, tolerance_fit_mm=10))
    self_verified = record(verification={"verifiedByRecordId": "FC-00001", "outcome": "resolved"})
    assert any("cannot verify itself" in e for e in validate_fit_correction(self_verified, tolerance_fit_mm=10))


def test_toile_is_not_final_verified_evidence():
    toile = record(material={"class": "calico_toile", "thicknessMm": 0.5, "isToile": True})
    assert any("toile" in e for e in validate_fit_correction(toile, tolerance_fit_mm=10))
    assert not is_trainable_correction(toile, tolerance_fit_mm=10)


def test_schema_enums_and_unknown_fields_fail_closed():
    invalid = record(extraField="must not pass", observations=[{"region": "not-a-region", "symptom": "gaping", "severity": "moderate"}])
    errors = validate_fit_correction(invalid, tolerance_fit_mm=10)
    assert any("unknown top-level" in e for e in errors)
    assert any("region is invalid" in e for e in errors)


def test_non_mm_corrections_are_not_trainable_without_unit_specific_noise_floors():
    invalid = record(corrections=[{"parameter": "block.shoulderSlopeLeftDeg", "generatedValue": 10, "correctedValue": 20, "deltaValue": 10, "unit": "deg", "addressesObservations": [0], "exceedsNoiseFloor": True}])
    errors = validate_fit_correction(invalid, tolerance_fit_mm=10)
    assert any("no configured noise floor" in e for e in errors)
    assert not is_trainable_correction(invalid, tolerance_fit_mm=10)


def test_only_resolved_verified_records_are_trainable():
    partial = record(verification={"verifiedByRecordId": "FC-00002", "outcome": "partially_resolved"})
    assert validate_fit_correction(partial, tolerance_fit_mm=10) == []
    assert not is_trainable_correction(partial, tolerance_fit_mm=10)


def test_trainability_requires_explicit_target_and_material_classification():
    invalid = record()
    invalid.pop("correctionTarget")
    invalid["material"] = {"class": "calico_toile", "thicknessMm": 0.5}
    errors = validate_fit_correction(invalid, tolerance_fit_mm=10)
    assert any("correctionTarget is required" in e for e in errors)
    assert any("material.isToile is required" in e for e in errors)
    assert not is_trainable_correction(invalid, tolerance_fit_mm=10)


def test_noise_floor_flag_must_be_a_boolean():
    invalid = record(corrections=[{"parameter": "block.armscyeDepthMm", "generatedValue": 10, "correctedValue": 20, "deltaValue": 10, "unit": "mm", "addressesObservations": [0], "exceedsNoiseFloor": "false"}])
    errors = validate_fit_correction(invalid, tolerance_fit_mm=10)
    assert any("exceedsNoiseFloor must be boolean" in e for e in errors)
    assert not is_trainable_correction(invalid, tolerance_fit_mm=10)
