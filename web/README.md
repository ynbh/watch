# Watch Web

Minimal FastAPI web wrapper for the TMDB keyboard-first UI.

## Env vars

- `TMDB_READ_ACCESS_TOKEN` - TMDB read access token
- `WATCH_WEB_PASSWORD` - shared login password
- `WATCH_WEB_SESSION_SECRET` - session cookie secret (random string)

## Run locally

```bash
uvicorn web.app.main:app --reload
```

Then visit `http://localhost:8000` and log in.
