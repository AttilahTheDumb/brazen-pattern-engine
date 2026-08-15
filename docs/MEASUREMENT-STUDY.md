# 24-session repeatability study template

The fillable templates are:

- `examples/repeatability-study.template.json` — canonical JSON shape consumed by the engine/UI;
- `examples/repeatability-study.template.csv` — spreadsheet-friendly capture sheet;
- `examples/synthetic-subject-178cm-101cm.json` — synthetic single-subject exemplar for interface testing;
- `examples/synthetic-repeatability-178cm-101cm-6-subjects.json` — complete synthetic 24-session fixture for end-to-end UI testing;
- `app/static/repeatability-study.template.json` — the browser-download copy.

The template contains exactly:

- 6 subjects;
- 2 measurers;
- 2 separately re-landmarked sessions per subject/measurer pair;
- 25 raw measurements per session;
- 24 total sessions.

## How to fill it

1. Validate the measurement protocol with the pattern cutter first.
2. Replace every `null` value with the raw millimetre reading. Do not average, round, correct or derive values during capture.
3. Set `landmarksConfirmed` to `true` only after the landmarks are marked and confirmed.
4. Set `conditions.reLandmarkingCompleted` to `true` for every duplicate session after full re-landmarking.
5. Record the controlled time, clothing, breathing, footwear, tape and any unusual notes.
6. Obtain approval for the low-TEM policy before filling `maxRelativeTemPct` or passing `--max-relative-tem-pct`.
7. Run the completed JSON through the Measurement floor view or:

```bash
bpe repeatability completed-study.json repeatability-output.json --max-relative-tem-pct 1.5
```

`1.5` is an example only, not an approved project threshold. The engine intentionally refuses to classify measurements as `PRIMARY` or freeze a tolerance budget until the policy is explicit.

The template is a capture scaffold, not measurement evidence. The evidence comes from the controlled physical sessions.
