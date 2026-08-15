# Local console UI

The Brazen Pattern Engine console is an original local **Operate / Inspect** surface. It uses precision-dark surfaces and restrained green/amber signals inspired by Linear/Stripe's information hierarchy, without copying either product's interface.

## Start

```bash
python -m app.server
```

Open <http://127.0.0.1:8787>.

Optional:

```bash
BRAZEN_PORT=8788 python -m app.server
```

The server binds to `127.0.0.1` by default and has no authentication or public exposure. Do not publish it directly to the internet; it is a local engineering console and the project is still Phase 0.

## UI surfaces

- **Overview** — readiness ledger, software/physical gate state, local engine signal.
- **Pattern Studio** — draw explicit polygonal pattern pieces on a millimetre grid, move points, close contours, add pieces/contours, undo/redo, save/load local project JSON, and validate/hash authored geometry through the engine. This is software authoring and inspection, not fit or manufacturing approval.
- **Design operations** — apply deterministic cubic curve handles, seam allowance offsets, explicit grading translations, dimensional constraints, reference comparison and inspection-only DXF-style export. These operations do not infer drafting rules or manufacturing approval.
- **Measurement floor** — load a study JSON, supply the approved low-TEM policy, and run the real repeatability engine.
- **Fit corrections** — load or use the sample record and run the real fail-closed validator.
- **Reference block** — load a digitised hand-drafted block, validate closed geometry and hash it; no sample geometry is loaded and no fit claim is emitted.

## API

- `GET /api/health`
- `GET /api/sample`
- `POST /api/validate-fit`
- `POST /api/hash-pattern`
- `POST /api/repeatability`

The server delegates to `src/brazen_pattern_engine`; it does not reimplement validation or geometry logic.
