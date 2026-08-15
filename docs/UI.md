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
- **Measurement floor** — load a study JSON, supply the approved low-TEM policy, and run the real repeatability engine.
- **Fit corrections** — load or use the sample record and run the real fail-closed validator.
- **Geometry lab** — load explicit pattern JSON, compute the real SHA-256 hash, render the real inspection SVG, and download it as an inspection artefact.

## API

- `GET /api/health`
- `GET /api/sample`
- `POST /api/validate-fit`
- `POST /api/hash-pattern`
- `POST /api/repeatability`

The server delegates to `src/brazen_pattern_engine`; it does not reimplement validation or geometry logic.
