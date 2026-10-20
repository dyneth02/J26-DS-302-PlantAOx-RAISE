# AOP-BCS React dashboard

This is the standalone Component 3 dashboard. It mirrors the shared PlantAOx-RAISE frontend architecture while remaining entirely inside `c3_aop_bcs`, as required by the component edit boundary.

## Stack and structure

- React 19 and TypeScript
- Vite 8
- Tailwind CSS 4
- React Router route objects
- feature-local pages, components, services, hooks, types, and routes
- reusable layout and research-state components
- Vitest and Testing Library

```text
frontend/
├── scripts/start-dev.mjs
├── src/
│   ├── app/router.tsx
│   ├── components/{layout,research,ui}/
│   ├── features/c3-aop-bcs/
│   │   ├── components/
│   │   ├── hooks/
│   │   ├── pages/
│   │   ├── services/
│   │   ├── types/
│   │   └── routes.tsx
│   ├── lib/api/
│   ├── styles/
│   └── main.tsx
├── vite.config.ts
└── vitest.config.ts
```

## Run locally

From `src/plantaox/c3_aop_bcs/frontend`:

```powershell
npm install
npm run dev
```

Open `http://127.0.0.1:4313`. The command starts:

- the C3 FastAPI evidence backend on `http://127.0.0.1:4314`;
- the Vite React frontend on `http://127.0.0.1:4313`;
- a Vite proxy from `/api` to the backend.

The header should show **Backend connected**. API checks are available at `/api/v1/c3/health`, `/api/v1/c3/dashboard`, and the section and figure routes.

## Validate

```powershell
npm test
npm run build
```

The dashboard includes Overview, Dataset, Perturbations, Pilot metrics, Variant explorer, Predictors, and Evidence routes. It reads the existing C3 API contract and does not duplicate scientific data in frontend source files.

## Scientific boundary

Current IR, FSR, BCS, PFR, score, and DeltaScore values come from the deterministic software smoke-test dummy. They demonstrate software behavior only and are not scientific AOP results. A real predictor is not shown as integrated until a finite real score and its evidence pass the C3 integration gate.

## Shared-platform boundary

The shared repository-level `frontend/` and other components are read-only for this task. This application reproduces their architecture and dashboard patterns inside the C3-owned directory. Registering C3 in the shared root router later requires a separately authorized repository-wide integration change.
