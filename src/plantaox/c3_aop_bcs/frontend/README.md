# AOP-BCS research dashboard

This is the standalone Component 3 dashboard and its C3-owned FastAPI backend. Both remain inside `c3_aop_bcs` because the shared application router, component registry, and shared UI package are outside the permitted C3 edit scope.

The dashboard deliberately follows the existing PlantAOx-RAISE frontend patterns:

- persistent platform sidebar and compact application header;
- component-level tab navigation;
- teal/slate shared colour variables and light/dark themes;
- compact bordered cards, uppercase card headers, badges, and stat tiles;
- responsive tables, charts, explorer controls, evidence panels, and limitation notices;
- mobile navigation at the shared `760px` breakpoint.

## Evidence boundary

All content is generated from versioned Component 3 artifacts. Current IR, FSR, BCS, PFR, score, and DeltaScore values use the deterministic software smoke-test dummy. They verify the pipeline only and are **not scientific AOP results**. Every real predictor remains `not_integrated` until a finite real score and its evidence pass the C3 integration gate.

## Run locally

Use the repository virtual environment after installing the dependencies declared in the root `pyproject.toml`. Node.js is used only as the convenient one-command launcher and for frontend validation.

```powershell
cd src/plantaox/c3_aop_bcs/frontend
npm test
npm run dev
```

Open `http://127.0.0.1:4313`.

`npm run dev` starts Uvicorn and serves both the dashboard and `/api/v1/c3/*` from the same origin. The header must show **Backend connected**. Useful API checks are:

- `GET /api/v1/c3/health`
- `GET /api/v1/c3/dashboard`
- `GET /api/v1/c3/sections/{overview|dataset|perturbations|metrics|explorer|predictors|evidence}`
- `GET /api/v1/c3/figures/{filename}`

To use another port in PowerShell:

```powershell
$env:C3_FRONTEND_PORT = 4400
npm run dev
```

## Dashboard views

- **Overview** — objective, pilot counts, workflow, scientific status, and limitations.
- **Dataset** — preparation funnel, pilot coverage, dominance review, and stage table.
- **Perturbations** — P1/P2/P3 rules, counts, frozen configuration, and validation.
- **Pilot metrics** — dummy-only IR, FSR, BCS, PFR, threshold sensitivity, and figures.
- **Variant explorer** — six manually inspected P1/P2/P3 examples with mutation and score details.
- **Predictors** — priorities, readiness, integration status, and PU-AOP dependency.
- **Evidence** — run provenance, source-report checksums, and current limitations.

## Data and validation

The FastAPI backend reads and validates 12 authoritative C3 JSON reports on request and serves the original four C3 SVG figures through allow-listed routes. The browser does not use the generated JSON snapshot at runtime. `npm run generate` remains a deterministic offline cross-check and creates `assets/generated/presentation-data.json` for validation only.

`npm run validate` checks:

- scientific/testing classification and pilot counts;
- all seven dashboard routes and renderers;
- shared PlantAOx design tokens and mobile breakpoint;
- interactive explorer and hash navigation hooks;
- predictor integration status;
- copied-figure checksums;
- absence of external page resources;
- C3-only working-tree scope.

## Files

- `index.html` — shared-style dashboard shell, sidebar, header, and tab navigation.
- `styles.css` — PlantAOx-aligned tokens, cards, tables, controls, and responsive layout.
- `app.js` — seven dashboard views, routing, theme, navigation, and perturbation explorer.
- `../dashboard_backend.py` — live artifact adapter, `/api/v1/c3` routes, and same-origin dashboard server.
- `scripts/generate-data.mjs` — deterministic C3 artifact adapter.
- `scripts/validate.mjs` — content, design, interaction, provenance, checksum, and scope checks.
- `scripts/start-backend.mjs` — cross-platform launcher for the repository virtual environment and Uvicorn.

## Shared application boundary

The module exports a reusable FastAPI `router`, so the shared API can later include it under `/api/v1/c3`. That registration requires editing the repository-wide backend router and frontend component registry, which this task intentionally does not do because the authorized scope is limited to `c3_aop_bcs`. The standalone C3 application is fully functional without those edits.
