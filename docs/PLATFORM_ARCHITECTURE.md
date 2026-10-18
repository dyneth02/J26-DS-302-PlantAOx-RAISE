# PlantAOx-RAISE — Platform Architecture

This describes the shared full-stack foundation built for the PP1 demonstration.
Component 02 (PU-AOP) is the only implemented research module; the architecture
is designed so C1, C3 and C4 can be added later without touching C2's code.

## Shape: modular monolith

One FastAPI backend, one React frontend, one repository. No microservices, no
separate databases, no plugin runtime — a new component is a new directory plus
one line of router/route registration.

```
backend/
  app/
    main.py                 # FastAPI app: CORS, exception handlers, router mount
    core/
      config.py             # Settings: repo_root, data paths, CORS origins
      errors.py             # ArtifactUnavailableError (-> 503), ResourceNotFoundError (-> 404)
      plantaox_bridge.py     # Makes src/plantaox importable from uvicorn
    api/v1/
      router.py             # Composition root: mounts health + every component's router
      health.py             # /health, /components (component registry)
      c2_pu/                # One router module per C2 endpoint group
        router.py
        overview.py, fr1.py, fr2.py, fr3.py, fr4.py, artifacts.py
    schemas/
      common.py             # ComponentInfo, HealthResponse (shared, not C2-specific)
      c2_pu.py               # C2's own response models
    services/
      c2_pu/
        artifacts.py         # Generic read-only JSON/CSV loaders + path resolution
        overview.py, fr1.py, fr2.py, fr3.py, fr4.py, curriculum.py, status.py

frontend/
  src/
    app/
      router.tsx             # Composition root: mounts PlatformOverviewPage + every component's routes
      pages/                 # Platform-level pages (not owned by any component)
    components/
      layout/                # AppShell, Sidebar, Header — shared chrome
      ui/                    # Card, Badge — shared primitives
      research/              # DataState, LimitationsPanel — shared research UX
    config/
      components.ts          # Static component registry (nav + overview cards)
    features/
      c2-pu/                 # Everything Component 02 owns
        pages/, components/, services/, types/, routes.tsx
    lib/
      api/                   # Shared fetch client + useApi hook
```

## Request flow (C2 example)

1. `GET /api/v1/c2/fr4/evaluation` hits `api/v1/c2_pu/fr4.py` (thin route handler).
2. The handler calls `services/c2_pu/fr4.get_fr4_evaluation()`.
3. The service reads `data/processed/c2_pu/fr4_baseline_comparison_fold0.csv` and
   `fr4_baseline_evaluation_fold0.json` via `services/c2_pu/artifacts.py` (generic,
   read-only JSON/CSV loaders — never write, never recompute a result the research
   pipeline already produced).
4. The service shapes the raw research JSON/CSV into a typed `Fr4EvaluationResponse`
   (`schemas/c2_pu.py`) and returns it. Deeply nested per-model blocks whose shape is
   owned by the research side are passed through as `dict`, not reshaped.
5. If an artifact is missing (e.g. a Git-ignored checkpoint absent on this checkout),
   `artifacts.py` raises `ArtifactUnavailableError`, which a global exception handler
   in `core/errors.py` turns into a `503` with a clear diagnostic — never a silently
   substituted mock value.
6. The frontend's `features/c2-pu/services/api.ts` calls this endpoint via the shared
   `apiGet` client. `useApi` tracks loading/success/error state; `DataState` renders a
   skeleton, a distinct "artifact unavailable" panel for 503s, or the real content.

## Why reuse `src/plantaox/c2_pu/*` instead of reimplementing

The backend never reimplements descriptor formulas, the C3 fold-challenge selection
rule, or checkpoint-loading logic. It imports the accepted, tested implementations
directly (`plantaox.c2_pu.curation.c3.load_fold_challenges`,
`plantaox.c2_pu.common.descriptors.compute_descriptors`, etc.) via
`core/plantaox_bridge.py`, which puts `src/` on `sys.path` so `import plantaox...`
works under uvicorn the same way it already does under pytest
(`pyproject.toml`'s `pythonpath = ["src", "."]`).

## Read-only / frozen-artifact contract

- Nothing under `backend/` writes to `data/processed/c2_pu/`, `data/interim/c2_pu/`,
  or any frozen checkpoint. There are no write/POST endpoints over accepted artifacts.
- `fr3_feature_cache_manifest.json` and a few other accepted JSON files embed an
  **absolute path from the machine that produced them**. `artifacts.resolve_repo_relative`
  re-anchors these onto the *current* checkout's repo root rather than trusting the
  embedded prefix — do not add a second path-resolution helper that trusts it.
- `GET /api/v1/c2/artifacts/status` is an **existence-only** check across the
  170-file inventory (no SHA-256 recomputation on every request — several hundred MB
  of checkpoints would make that slow). The authoritative byte-for-byte check is
  `python -m plantaox.c2_pu.pp1_freeze verify`, run manually/offline (see
  `PP1_DASHBOARD_SETUP.md`).

## Explicitly out of scope for this PP1 build

- **C1 (AOP-ProCon), C3 (AOP-BCS), C4 (PlantAOP-Screen)**: shown in the shared shell
  and `/api/v1/components` as `not_integrated`. No dashboards, no sample data, no
  endpoints.
- **Live model inference ("Level B")**: the dashboard surfaces the *accepted,
  already-computed* FR4 evaluation/curriculum results. It does not load a `.pt`/
  `.joblib` checkpoint and run new inference at request time — that would need a
  stricter review of checkpoint-loading correctness than this PP1 build covers.
  `services/c2_pu` has no dependency on `plantaox.c2_pu.models` / `run_recorder` for
  this reason; everything it reads is a precomputed, accepted result.
