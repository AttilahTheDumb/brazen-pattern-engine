# Brazen Pattern Engine

Deterministic engineering foundations for Brazen Wear's leather pattern project.

## What exists in v0.1

This repository implements the software-verifiable part of the project without making a physical-fit claim:

- raw capture mappings are frozen after validation; timestamp, boolean, derived-ID, and full-protocol gates fail closed;
- protocol-defined derived measurements, including shoulder slope from straight-line NP→ACR lengths and shoulder drops;
- repeatability-study calculations for intra/inter-measurer TEM, relative TEM, reliability, classification, and the tolerance budget;
- a fail-closed validator for the normative fit-correction record, including delta consistency, observation traceability, verification lifecycle, material/toile boundaries, and noise-floor eligibility;
- integer tenths-of-a-millimetre geometry coordinates with deterministic rounded segment lengths;
- repeatability analysis requires an explicit, approved low-TEM policy via `--max-relative-tem-pct`; without it, no measurement becomes `PRIMARY` and no tolerance budget is frozen;
- the CLI supports repeatability analysis, fit-record validation, pattern hashing, and inspection SVG export.

## Deliberate non-claims

This is **not** yet a body-to-pattern compiler, a production DXF exporter, a leather-fit predictor, or a customer-facing product. The PDF's gates still require:

1. pattern-cutter validation of the measurement protocol;
2. the 24-session repeatability study and fixed tolerance constants;
3. a leather goods patternmaker review before Phase 1;
4. a physically validated hand-drafted reference block;
5. digitisation of that reference and Phase 2 reproduction tests;
6. physical prototypes and human fit adjudication.

Software can prove internal consistency and deterministic reproduction. It cannot assert that a pattern fits a person.

## Run

```bash
python -m pytest
python -m compileall -q src tests
python -m brazen_pattern_engine.cli --help
```

## Local console UI

Start the local operations console:

```bash
python -m app.server
```

Open <http://127.0.0.1:8787>. If that port is occupied, use:

```bash
BRAZEN_PORT=8788 python -m app.server
```

The console binds to `127.0.0.1` by default, delegates to the real deterministic engine, and provides Overview, Measurement floor, Fit corrections and Geometry lab surfaces. It has no authentication and must not be exposed publicly without a separate deployment, identity and data-boundary decision.

The package is dependency-free at runtime. From the repository root, the CLI can be invoked with:

```bash
PYTHONPATH=src python -m brazen_pattern_engine.cli hash examples/pattern.json
PYTHONPATH=src python -m brazen_pattern_engine.cli svg examples/pattern.json -o /tmp/brazen-inspection.svg
PYTHONPATH=src python -m brazen_pattern_engine.cli validate-fit examples/fit-correction.json --tolerance-fit-mm 10
```

## Contracts

- Internal lengths are millimetres. Angles are degrees only where the protocol explicitly derives them.
- Raw sessions store values as received. Derived values are emitted separately by analysis.
- Tolerance values must come from measured repeatability. The default geometric precision is 0.1 mm; it is not a substitute for the input tolerance.
- Blocks and garments are represented as separate version fields. The current kernel only accepts explicit geometry; drafting rules are not invented before a validated reference block exists.
- A fit-correction record is trainable only when it is valid, verified by a subsequent record, non-ambiguous, non-toile, and every correction is at or above the computed fit noise floor.
- Pattern hashes cover canonicalised geometry and compiler version. Reordering input collections must not change the hash.

## CLI exit semantics

`PASS` is emitted only for the software gate being run. A passing hash, schema, or geometry check is not a physical-fit or manufacturing-readiness approval.

## Project state

Phase: **0, software foundation only**.

The absence of measurement data, leather review, a digitised gold block, physical prototypes, and a manufacturing acceptance run is an intentional and explicit blocker—not a missing fixture to fill with invented data.
