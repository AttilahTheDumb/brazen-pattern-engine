# Public deployment handoff

## Static UI

GitHub Pages workflow: `.github/workflows/pages.yml`.

Expected URL after the first successful Pages deployment:

`https://attilahthedumb.github.io/brazen-pattern-engine/`

The workflow publishes only `app/static/`. It does not publish Python source or engine internals as a runtime.

## API

Render Blueprint: `render.yaml`.

Expected API URL:

`https://brazen-pattern-engine-api.onrender.com`

The Render service:

- binds to the platform-provided `PORT`;
- exposes only `/api/*` and no persistent user data store;
- uses a generated `BRAZEN_API_SECRET` in public mode;
- permits CORS only from the GitHub Pages origin;
- requires `Authorization: Bearer <secret>` for API operations; `/api/health` remains public for health checks.

The static UI never embeds the secret. The **Connect API** control stores a token only in the browser session and sends it over HTTPS to Render.

## Publish sequence

1. Create/push the GitHub repository.
2. Enable GitHub Pages using GitHub Actions.
3. Deploy the Render Blueprint from the repository.
4. Confirm the Render service URL and generated API secret.
5. Open the Pages URL and use **Connect API** with the Render secret.
6. Verify health, sample load, fit validation, pattern hashing and SVG preview from the public UI.

Do not publish the UI before the API is deployed, or it will display an offline/authentication state. Do not make the API unauthenticated.
