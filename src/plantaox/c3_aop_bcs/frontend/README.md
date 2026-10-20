# AOP-BCS PP1 progress presentation

This is the standalone Component 3 presentation frontend. It deliberately lives inside `c3_aop_bcs` because the shared React application and the other component frontends are outside the permitted edit scope.

The interface follows the shared PlantAOx-RAISE visual language—teal research accents, slate surfaces, bordered cards, evidence badges, compact provenance, responsive navigation, and explicit limitation states—without changing the shared frontend.

## Evidence boundary

All content is generated from versioned Component 3 artifacts. The current IR, FSR, BCS, PFR, score, and DeltaScore values use the deterministic software smoke-test dummy. They verify the pipeline only and are **not scientific AOP results**. All real predictors remain not integrated until a real finite score and its retained evidence pass the C3 integration gate.

## Run locally

Node.js is the only runtime dependency; there are no third-party packages to install.

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

## Data flow

`npm run generate` reads 12 authoritative C3 JSON reports and copies four checksum-verified C3 SVG figures into `assets/generated/`. It writes one deterministic browser snapshot, `presentation-data.json`, containing:

- dataset funnel and pilot coverage;
- full and pilot P1/P2/P3 counts;
- dummy-only IR, FSR, BCS, PFR, and threshold sensitivity;
- six manually inspected real-artifact variants;
- frozen predictor priority/readiness records;
- run metadata and source checksums.

`npm run validate` confirms the evidence classification, counts, example coverage, predictor status, required narrative sections, mobile CSS, interaction hooks, copied-figure checksums, and that every current working-tree change remains under a path containing `c3_aop_bcs`.

## Presentation controls

- Use the left navigation—or the mobile menu—to move between the eight narrative sections.
- Select P1, P2, or P3 in the variant explorer and use the arrow controls to inspect both verified examples.
- Use **Presentation mode** for a wider projected layout.
- Use the half-circle control to switch between light and dark themes.
- The page includes a skip link, semantic landmarks, focus-visible states, reduced-motion support, and responsive layouts down to narrow mobile screens.

## Files

- `index.html` — semantic presentation structure.
- `styles.css` — standalone PlantAOx-aligned design system and responsive layout.
- `app.js` — rendering, navigation, theme, presentation mode, and perturbation explorer.
- `scripts/generate-data.mjs` — deterministic C3 artifact adapter.
- `scripts/validate.mjs` — content, provenance, interaction, responsive, checksum, and scope checks.
- `scripts/serve.mjs` — dependency-free local HTTP server.
