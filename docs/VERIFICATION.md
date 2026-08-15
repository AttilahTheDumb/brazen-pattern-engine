# Verification record

This file records reproducible local verification, not physical-fit approval.

## Build checks

- `python -m pip install -e .` — PASS
- `python -m pytest` — PASS (39 tests)
- `python -m compileall -q src tests app` — PASS
- Local console server on `127.0.0.1:8788` — PASS
- `/api/health` and static HTML/CSS/JS delivery — PASS
- Pattern Studio browser flow: draw points, close contour, save/reload persistence, new piece — PASS
- Authored geometry hash/SVG API — PASS
- Downstream API: curves, seam allowance, grading, comparison, constraints and DXF-style inspection export — PASS
- Synthetic repeatability fixture — correctly rejected from evidence analysis with HTTP 400
- Public bind without `BRAZEN_API_SECRET` — correctly refused
- Protected API: missing/wrong token `401`; valid token reaches authenticated engine success

## Review lanes

- Codebase composition/LOC: run `pygount --format=summary --folders-to-skip=.git,node_modules,venv,.venv,__pycache__,dist,build,.pytest_cache .` from the repository root.
- Autonomous-loop review: no autonomous worker/acceptance loop is shipped in this repository. The core has no shell execution, no network client, no model call, no unattended commit/merge path, and no agent prompt package. Any future loop must be reviewed as a separate security boundary with negative probes.
- Design-system extraction: not run against a source website. The console is an original UI, not an extraction of an existing public design system.
- Product/design review: Pattern Studio is now a shipped original UI surface; responsive black-box acceptance covers desktop/mobile interaction and the current public static build.
- Production readiness: local console is conditionally ready for controlled use; public static UI is deployed, while the protected Render API remains a deployment gate.

## What this proves

The tests and UI checks prove deterministic software behaviour, fail-closed data/geometry guards, responsive layout, and local engine integration. They do not prove measurement repeatability, leather suitability, body fit, manufacturing export correctness, rights, commercial readiness, or public API deployment.
