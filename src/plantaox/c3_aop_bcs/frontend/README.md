# AOP-BCS research dashboard

This is the standalone Component 3 dashboard. It remains inside `c3_aop_bcs` because the shared application router, component registry, and shared UI package are outside the permitted C3 edit scope.

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

Node.js is the only runtime dependency; no package installation is required.

```powershell
cd src/plantaox/c3_aop_bcs/frontend
npm test
npm run dev
```

Open `http://127.0.0.1:4313`.

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

`npm run generate` reads 12 authoritative C3 JSON reports, copies four checksum-verified C3 SVG figures, and writes `assets/generated/presentation-data.json` as the deterministic browser snapshot.

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
- `scripts/generate-data.mjs` — deterministic C3 artifact adapter.
- `scripts/validate.mjs` — content, design, interaction, provenance, checksum, and scope checks.
- `scripts/serve.mjs` — dependency-free local HTTP server.
