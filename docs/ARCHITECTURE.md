# Architecture and phase gates

## Source precedence

The attached Brazen Pattern Engine orchestration brief is normative for this repository. This document records the software interpretation only; it does not override the pattern cutter, leather specialist, or physical fitting gates.

## Current boundary

The repository is a Phase 0 software foundation. It accepts raw, confirmed measurement sessions; derives protocol-defined values; computes repeatability statistics; fixes a tolerance budget only when primary measurements exist; validates fit-correction records; and manipulates explicit geometry deterministically.

It deliberately does **not** infer drafting rules, body fit, leather behaviour, seam allowance compensation, or manufacturing readiness. There is no measurement study, leather review, digitised gold block, or physical prototype yet.

## Authority chain

1. Joseph owns product/business decisions.
2. The professional pattern cutter owns physical fit assessment.
3. A paid leather goods patternmaker must review cloth-derived logic before Phase 1.
4. Software validates contracts and geometry gates.
5. No model, compiler, or verifier is allowed to cast a physical-fit vote.

## Software boundary

```text
raw measurement session
  -> protocol-defined derivations
  -> repeatability/TEM analysis
  -> tolerance budget
  -> explicit validated block/geometry specification
  -> deterministic canonical geometry + content hash + inspection SVG

fit observation + correction record
  -> schema/cross-field validation
  -> provisional/verified lifecycle
  -> trainable only if all hard gates pass
```

The body-to-pattern drafting function is intentionally absent until a hand-drafted reference block and its documented leather-reviewed logic exist.

## Binary gates

- landmark confirmation before analysis;
- minimum repeatability design: six subjects, two measurers, two sessions;
- finite positive measurements;
- shoulder slope triangle validity;
- primary classification from measured reliability, not a fixed promise;
- no tolerance budget without primary inter-measurer TEM;
- closed, non-zero-area contours;
- seam correspondence within the supplied tolerance;
- canonical hash reproducibility;
- fit correction delta and noise-floor consistency;
- verified subsequent record, non-ambiguous target, and non-toile status before aggregation.

There is no composite score and no `fit=True` result.

## Phase gates still open

- **Phase 0 human gate:** validate protocol; execute 24-session repeatability study; classify all measurements; fix the three tolerance constants.
- **Phase 1 human gate:** engage leather specialist; draft and physically validate one reference block; digitise it and document drafting logic.
- **Phase 2 software gate:** implement and test reproduction against the digitised reference within measured input tolerance; require bit-identical recompilation.
- **Phase 3 physical gate:** three new bodies, each acceptable after no more than one correction round, with records conforming to the schema.
- **Phase 4–7:** operations, manufacturing exports, validated parameter ranges, then optional sketch interpretation.

## Explicit unresolved architecture questions

- How the pattern cutter defines the drafting rules from the validated gold block.
- Leather-specific thickness consumption at folds, joins, and seam constructions.
- The source geometry/format used for digitised reference blocks.
- The exact seam correspondence model for curves and notches.
- Whether DXF requirements need an external geometry library after Phase 2.

These are escalations, not assumptions to be filled by code.
