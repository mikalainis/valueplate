# Value Plate

## Starting a dev session

The devcontainer (`.devcontainer/devcontainer.json`) automatically starts both dev servers when you attach to the Codespace:

- **plan-engine** (FastAPI) on port 8000 — `plan-engine/.venv/bin/uvicorn app.main:app --reload --port 8000`
- **frontend** (Vite) on port 5173 — `npm run dev` in `frontend/`

This happens via `postAttachCommand`, which runs `scripts/dev-start.sh`. Dependencies (`frontend/node_modules` and `plan-engine/.venv`) are installed once via `postCreateCommand` when the container is first created.

Logs are written to `logs/plan-engine.log` and `logs/frontend.log` in the repo root (gitignored).

### Running it manually

```bash
scripts/dev-start.sh
```

The script skips starting a server if its port (8000 or 5173) is already in use, so it's safe to re-run.

### Restarting a server

Find and kill the process on the relevant port, then re-run the script:

```bash
# plan-engine
fuser -k 8000/tcp
# frontend
fuser -k 5173/tcp

scripts/dev-start.sh
```

Or tail the logs while it's running:

```bash
tail -f logs/plan-engine.log
tail -f logs/frontend.log
```
