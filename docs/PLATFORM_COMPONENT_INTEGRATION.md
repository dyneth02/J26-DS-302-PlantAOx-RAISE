# Integrating a new component (C1 / C3 / C4) into the shared platform

This is written for whoever integrates the next component (e.g. C3 / AOP-BCS).
It assumes you've read `PLATFORM_ARCHITECTURE.md`. You should not need to modify
any file under `backend/app/**/c2_pu/` or `frontend/src/features/c2-pu/` to do
any of this.

## 1. Backend: add your router

Create `backend/app/api/v1/<your_component>/` mirroring `c2_pu/`:

```
backend/app/api/v1/c3_aop_bcs/
  router.py          # APIRouter(prefix="/c3", tags=["c3-aop-bcs"])
  overview.py         # one module per endpoint group, same pattern as c2_pu/fr1.py etc.
```

Put your artifact-reading logic in `backend/app/services/c3_aop_bcs/`, not in the
route handlers — route handlers should stay thin (parse path/query params, call a
service function, return its typed response). See `services/c2_pu/artifacts.py` for
the generic read-only JSON/CSV loader pattern; copy its shape (raise
`ArtifactUnavailableError` for a missing/corrupt artifact, `ResourceNotFoundError`
for an unknown id) rather than inventing new exception types.

Register your router in `backend/app/api/v1/router.py`:

```python
from backend.app.api.v1.c3_aop_bcs.router import router as c3_aop_bcs_router
router.include_router(c3_aop_bcs_router)
```

That's the only change to a file outside your own directory.

### Schemas

Define your own Pydantic models in `backend/app/schemas/c3_aop_bcs.py`. Do **not**
reuse C2's `Fr4EvaluationResponse`/etc. even if a shape looks similar — C1/C2/C3/C4
have different data contracts, metrics, and evaluation semantics, and a shared
schema that assumes otherwise will silently mismatch the moment one component's
contract changes. Shared schemas (`schemas/common.py`) are for genuinely
cross-component concerns only (`ComponentInfo`, `HealthResponse`).

### Updating your entry in the component registry

Flip your component's entry in `backend/app/api/v1/health.py`'s `COMPONENTS` list:

```python
ComponentInfo(
    id="c3_aop_bcs",
    code="C3",
    title="AOP-BCS",
    owner_note="...",
    status="implemented",   # was "not_integrated"
    base_path="/api/v1/c3",
),
```

## 2. Frontend: add your feature directory

Create `frontend/src/features/c3-aop-bcs/` mirroring `c2-pu/`:

```
features/c3-aop-bcs/
  types/index.ts       # Hand-written types matching your backend schemas
  services/api.ts       # Thin wrapper over the shared apiGet() client
  components/           # Your section nav, any component-local widgets
  pages/                 # One page per dashboard section
  routes.tsx             # Exports a RouteObject[] — see c2-pu/routes.tsx
```

Your `routes.tsx` should export a `RouteObject[]` the same shape as
`c2PuRoutes` in `features/c2-pu/routes.tsx`. Register it in
`frontend/src/app/router.tsx`:

```tsx
import { c3AopBcsRoutes } from "@/features/c3-aop-bcs/routes";
// ...
children: [
  { index: true, element: <PlatformOverviewPage /> },
  { path: "not-integrated/:componentId", element: <NotIntegratedPage /> },
  ...c2PuRoutes,
  ...c3AopBcsRoutes,   // <- your one line
],
```

Flip your entry in `frontend/src/config/components.ts`:

```ts
{
  id: "c3_aop_bcs",
  code: "C3",
  title: "AOP-BCS",
  shortTitle: "C3 — AOP-BCS",
  ownerNote: "...",
  status: "implemented",   // was "not_integrated"
  basePath: "/c3",          // was null
},
```

The sidebar automatically picks this up (it renders from `COMPONENT_REGISTRY`)
— no sidebar code changes needed.

### Shared UI you should reuse, not reimplement

- `components/ui/Card.tsx`, `Badge.tsx` — layout primitives.
- `components/research/DataState.tsx` — wraps `useApi`'s loading/error/success
  states, including a distinct panel for a `503 artifact_unavailable` response.
  Use this instead of writing your own loading spinner / error message.
- `components/research/LimitationsPanel.tsx` — the "known limitations" warning
  box used on every C2 page. If your component has documented scientific
  limitations (it should), surface them the same way.
- `lib/api/client.ts` (`apiGet`) / `lib/api/useApi.ts` (`useApi`) — the shared
  fetch wrapper and data-fetching hook. Every component's `services/api.ts`
  should call `apiGet`, not raw `fetch`, so error shapes stay consistent.

## 3. Error-state conventions (both sides)

- Backend: a missing/unreadable/corrupt accepted artifact → raise
  `ArtifactUnavailableError` from your service function → the registered handler
  turns it into `503 {"error": "artifact_unavailable", "detail": "...", "artifact_path": "..."}`.
  An unknown id (fold, peptide, sample) the client asked for → raise
  `ResourceNotFoundError` → `404`. Never catch either and substitute mock data.
- Frontend: render both through `<DataState state={...} render={...} />`. Don't
  write a second loading/error UI — if `DataState` doesn't fit your page's layout,
  extend it rather than bypassing it, so the "artifact unavailable" messaging stays
  consistent across every component.

## 4. Artifact provenance rules

- Never accept a filesystem path from a request. Route handlers only ever take
  validated ids (fold number, peptide id, etc.); your service resolves those to a
  path internally.
- If your artifacts include any that embed an absolute path from the producing
  machine (check your own manifests — C2's `fr3_feature_cache_manifest.json` does
  this), re-anchor it onto the current repo root the way
  `services/c2_pu/artifacts.resolve_repo_relative` does. Don't trust the embedded
  absolute prefix.
- Don't fabricate a result when an artifact is missing. A `503` with a clear
  message is correct; a plausible-looking mock number is not.
- Follow your own component's scientific-interpretation rules exactly as C2's
  `docs/AGENTS.md` does for C2 (e.g. never call an unlabeled/assumed-negative pool
  "negative" in UI copy or docstrings if that's not an established fact for your
  component either).

## 5. Testing expectations

- Backend: `tests/backend/` already has a working pattern
  (`tests/backend/test_c2_pu_api.py`, `test_error_handling.py`) using
  `httpx.AsyncClient` + `ASGITransport` against the real FastAPI `app` object, plus
  a monkeypatch-based test for the 503 path. Add `tests/backend/test_<your_component>_api.py`
  the same way. **Do not** name a test file/dir `backend` itself without checking —
  pytest's package-rootdir inference treats a directory with `__init__.py` named
  the same as a real top-level package as that package's root, which previously
  shadowed the real `backend/` package here. Keep `tests/backend/` free of an
  `__init__.py`.
- Frontend: add `<YourPage>.test.tsx` next to the page, following
  `features/c2-pu/pages/Fr4Page.test.tsx` (mock `global.fetch`, assert the
  scientific-caveat text actually renders — don't just assert the page doesn't
  crash).
- Run `npm run build` (TypeScript + production bundle) and
  `python -m pytest tests/backend -q` before considering your component done.

## Minimal illustrative example

A fictitious "C3 overview" endpoint, following the pattern exactly — this is
illustrative wiring only, not real C3 data:

```python
# backend/app/services/c3_aop_bcs/overview.py
from backend.app.services.c3_aop_bcs.artifacts import load_processed_json

def get_overview() -> dict:
    manifest = load_processed_json("c3_freeze_manifest.json")  # whatever C3 actually freezes
    return {"freeze_id": manifest["release"]["id"], "status": manifest["release"]["decision"]}
```

```python
# backend/app/api/v1/c3_aop_bcs/overview.py
from fastapi import APIRouter
from backend.app.services.c3_aop_bcs.overview import get_overview

router = APIRouter()

@router.get("/overview")
def overview():
    return get_overview()
```
