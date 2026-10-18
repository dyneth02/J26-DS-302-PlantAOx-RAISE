# PP1 Dashboard — Setup & Startup (Windows / PowerShell)

Covers installing, configuring, and running the PlantAOx-RAISE PP1 demonstration
(backend + frontend) for Component 02 (PU-AOP). Written for PowerShell since that's
this project's primary shell; a Bash-equivalent is noted where it differs.

## Prerequisites

- Python 3.11 (`.python-version` pins `3.11`), with the project's existing `.venv`.
- Node.js 18+ (scaffolded and tested against Node 22).
- The **Git-ignored** C2 feature caches / checkpoints present under
  `data/interim/c2_pu/` (56 files, ~39 MB). These are *not* recoverable from Git
  alone — see `src/plantaox/c2_pu/docs/C2_PP1_HANDOVER.md` for the authoritative
  recovery copy location. Without these, FR3/FR4/curriculum/evidence endpoints
  return a `503 artifact_unavailable` (the dashboard degrades gracefully, but
  those pages won't show data).

## 1. Install backend dependencies

The `.venv` already has `fastapi`, `uvicorn`, `pydantic`, `biopython`, and the ML
stack installed, but `pyproject.toml` now declares them explicitly. From a fresh
checkout:

```powershell
$py = (Resolve-Path '.venv\Scripts\python.exe').Path
& $py -m pip install -e .[dev]
```

(`[dev]` adds `pytest` + `httpx`, needed for `tests/backend/`.)

## 2. Install frontend dependencies

```powershell
cd frontend
npm install
cd ..
```

## 3. Start the backend (FastAPI)

```powershell
$py = (Resolve-Path '.venv\Scripts\python.exe').Path
& $py -m uvicorn backend.app.main:app --reload --port 8000
```

- API docs: http://localhost:8000/docs
- Health check: http://localhost:8000/api/v1/health

No `PYTHONPATH` export is needed — `backend/app/core/plantaox_bridge.py` puts
`src/` on `sys.path` itself.

## 4. Start the frontend (React/Vite)

In a second terminal:

```powershell
cd frontend
npm run dev
```

- App: http://localhost:5173
- `/api/*` requests are proxied to `http://localhost:8000` by Vite's dev server
  (`frontend/vite.config.ts`) — no CORS configuration needed in development beyond
  what `backend/app/main.py` already sets for direct cross-origin calls.

## 5. Verify offline readiness

With no internet connection, both servers should start and the full Component 02
dashboard (Overview → FR1 → FR2 → FR3 → FR4 → Curriculum → Evidence) should load,
since every page reads local files only. The only external-looking resource is the
system/UI font stack — no CDN scripts, fonts, or icons are loaded (Lucide icons are
bundled via `lucide-react`, Recharts is bundled via `recharts`).

## 6. Run tests

Backend:

```powershell
$py = (Resolve-Path '.venv\Scripts\python.exe').Path
& $py -m pytest tests/backend -q
```

Frontend:

```powershell
cd frontend
npm test
npm run build   # TypeScript check + production bundle
cd ..
```

## 7. Re-verify frozen-artifact integrity (optional, offline, read-only)

The dashboard's `/api/v1/c2/artifacts/status` endpoint (Evidence page) does a fast
existence-only check across the 170-file inventory. For the authoritative
byte-for-byte SHA-256 re-verification (what the research side runs before any
freeze decision), run the project's own verifier directly — **do not** run this as
part of the web app; it's a separate, heavier, offline check:

```powershell
$py = (Resolve-Path '.venv\Scripts\python.exe').Path
$env:PYTHONPATH = (Resolve-Path 'src').Path
& $py -m plantaox.c2_pu.pp1_freeze verify --manifest data/processed/c2_pu/C2_PP1_FREEZE_MANIFEST.json
```

Expect `PASS`, 170 inventory records, a 9356×495 fold-0 feature cache, 2000
fold-0 C3 rows, and zero external-control/training overlap.

## 8. Clean shutdown

- Frontend: `Ctrl+C` in the `npm run dev` terminal.
- Backend: `Ctrl+C` in the `uvicorn` terminal (plain `Ctrl+C` is sufficient;
  uvicorn shuts down its workers gracefully).
- Neither process writes to disk, so there's no lock file or state to clean up.

## Troubleshooting

- **A C2 page shows "Artifact unavailable in this checkout"**: expected if the
  Git-ignored `data/interim/c2_pu/` caches/checkpoints aren't present on this
  machine. Recover them per `C2_PP1_HANDOVER.md`, or accept that FR3/FR4/
  curriculum/evidence won't have data on this checkout (FR1/FR2 read only
  Git-tracked frozen manifests and will still work).
- **`ModuleNotFoundError: No module named 'backend.app'` when running pytest**:
  don't add an `__init__.py` to `tests/backend/` — pytest's rootdir inference will
  treat `tests/` as the `backend` package's root and shadow the real one.
- **CORS error in the browser console**: you're probably hitting
  `http://localhost:8000` directly from a frontend origin other than
  `http://localhost:5173`/`127.0.0.1:5173`. Either use the Vite proxy (recommended,
  just call `/api/...` relative paths as the app already does) or add your origin
  to `PLANTAOX_CORS_ORIGINS` (comma-separated) before starting uvicorn.
