const DATA_URL = "assets/generated/presentation-data.json";
const ROUTES = ["overview", "dataset", "perturbations", "metrics", "explorer", "predictors", "evidence"];
const formatNumber = new Intl.NumberFormat("en-US");
const percent = (value, digits = 1) => `${(value * 100).toFixed(digits)}%`;
const escapeHtml = (value) => String(value)
  .replaceAll("&", "&amp;")
  .replaceAll("<", "&lt;")
  .replaceAll(">", "&gt;")
  .replaceAll('"', "&quot;")
  .replaceAll("'", "&#039;");

let evidence;
let explorerType = "P1";
let explorerIndex = 0;

function card(title, subtitle, body, className = "") {
  return `<article class="card ${className}">
    <div class="card-header"><h3>${escapeHtml(title)}</h3>${subtitle ? `<p>${escapeHtml(subtitle)}</p>` : ""}</div>
    ${body}
  </article>`;
}

function statTile(label, value, hint = "") {
  return `<div class="stat-tile"><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong>${hint ? `<small>${escapeHtml(hint)}</small>` : ""}</div>`;
}

function safetyNote() {
  return `<article class="card limitations"><div class="card-header"><h3>Scientific interpretation boundary</h3></div>
    <ul><li>Every score and metric shown here was produced by the deterministic software smoke-test dummy.</li><li>These values validate software flow only; they do not measure biological or predictor reliability.</li><li>All five scientific predictors remain not integrated until a retained real score is verified.</li></ul></article>`;
}

function overviewView() {
  return `
    <article class="card hero-card">
      <div><span class="badge badge-accent">Component 03 — AOP-BCS</span><h3>Physicochemical faithfulness audit for antioxidant peptide predictors</h3><p>A predictor-independent framework that tests whether model scores respond consistently to controlled single-residue perturbations.</p></div>
      <div class="hero-status"><span class="badge badge-warning">Software pilot complete</span><span>Dataset: ${escapeHtml(evidence.provenance.datasetVersion)}</span><span>Evidence date: ${escapeHtml(evidence.evidenceDate)}</span></div>
    </article>
    ${card("Pilot at a glance", "Counts read from the versioned PP1 run manifest.", `<div class="stat-grid">
      ${statTile("Pilot peptides", formatNumber.format(evidence.overview.pilotSubjects), "coverage-selected")}
      ${statTile("Pilot perturbations", formatNumber.format(evidence.overview.pilotVariants), "P1 + P2 + P3")}
      ${statTile("Full eligible subjects", formatNumber.format(evidence.overview.fullEligibleSubjects), "redox-filtered")}
      ${statTile("Full valid variants", formatNumber.format(evidence.overview.fullVariants), "zero rejected")}
    </div>`)}
    ${card("AOP-BCS workflow", "The same frozen workflow will be rerun for each verified real predictor.", `<ol class="pipeline-list">
      <li><span>01</span>Prepare audit subjects</li><li><span>02</span>Generate P1/P2/P3</li><li><span>03</span>Validate each edit</li><li><span>04</span>Score and cache</li><li><span>05</span>Calculate ΔScore</li><li><span>06</span>Aggregate IR/FSR/BCS</li>
    </ol>`)}
    ${card("Scientific status", "Technical reproducibility and scientific validation are separate claims.", `<div class="stat-grid">
      ${statTile("Perturbation pipeline", "Verified", "10,036 accepted variants")}
      ${statTile("Metric pipeline", "Verified", "dummy smoke test")}
      ${statTile("Real predictors", "0 integrated", "handoff and runtime work pending")}
      ${statTile("Scientific conclusion", "Not established", "no real scores yet")}
    </div>`)}
    ${safetyNote()}`;
}

function datasetView() {
  const maximum = evidence.datasetFunnel[0].count;
  const bars = evidence.datasetFunnel.map((stage) => `<div class="bar-row"><div class="bar-label"><strong>${escapeHtml(stage.label)}</strong><small>${escapeHtml(stage.detail)}</small></div><div class="bar-track"><span style="width:${Math.max(5, stage.count / maximum * 100)}%"></span></div><strong>${formatNumber.format(stage.count)}</strong></div>`).join("");
  const rows = evidence.datasetFunnel.map((stage, index) => `<tr><th scope="row">${index + 1}. ${escapeHtml(stage.label)}</th><td class="number-cell">${formatNumber.format(stage.count)}</td><td>${escapeHtml(stage.detail)}</td></tr>`).join("");
  return `
    ${card("Audit-dataset preparation", "Versioned counts from cleaning, CD-HIT, eligibility, and pilot reports.", `<div class="bar-list">${bars}</div>`)}
    <div class="card-grid">
      ${card("Pilot coverage", "Coverage-first selection using fixed seed 42.", `<dl class="definition-grid"><div><dt>Length range</dt><dd>${evidence.coverage.lengthRange}</dd></div><div><dt>Distinct lengths</dt><dd>${evidence.coverage.distinctLengths}</dd></div><div><dt>Redox residues</dt><dd>${evidence.coverage.redoxResidues.join(" · ")}</dd></div><div><dt>Evidence tiers</dt><dd>${evidence.coverage.evidenceTiers.join(" and ")}</dd></div></dl>`)}
      ${card("Count quality control", "No subject exceeds the prespecified 20% PP1 dominance flag.", `<div class="stat-grid"><div class="stat-tile"><span>Maximum subject share</span><strong>${percent(evidence.coverage.maximumVariantShare)}</strong><small>below 20%</small></div><div class="stat-tile"><span>Missing scores</span><strong>${evidence.provenance.missingScores}</strong><small>pilot rows</small></div></div>`)}
    </div>
    ${card("Dataset stages", "Traceable preparation summary.", `<div class="table-wrap"><table><thead><tr><th>Stage</th><th>Records</th><th>Rule/output</th></tr></thead><tbody>${rows}</tbody></table></div>`)}
    <div class="callout success"><strong>Quality gate passed</strong><p>All 20 pilot subjects have at least one valid perturbation and all P1/P2/P3 groups are represented.</p></div>`;
}

function perturbationsView() {
  const mutation = { P1: "WYHMC → A", P2: "L → I", P3: "G → K" };
  const cards = evidence.perturbations.map((item) => card(`${item.id} — ${item.title}`, item.subtitle, `<span class="mutation-code">${mutation[item.id]}</span><h4>${escapeHtml(item.question)}</h4><p>${escapeHtml(item.rule)}</p><div class="counts"><span><strong>${formatNumber.format(item.pilotCount)}</strong> pilot variants</span><span><strong>${formatNumber.format(item.fullCount)}</strong> full variants</span></div>`, "perturbation-card")).join("");
  return `
    <div class="card-grid three-grid">${cards}</div>
    ${card("Frozen perturbation configuration", "Loaded from the C3 run manifest and research configuration.", `<dl class="definition-grid"><div><dt>Redox set</dt><dd>${evidence.configuration.redoxResidues.join(", ")}</dd></div><div><dt>Master seed</dt><dd>${evidence.configuration.seed}</dd></div><div><dt>P2 minimum BLOSUM62</dt><dd>≥ ${evidence.configuration.blosumMinimum}</dd></div><div><dt>Primary response threshold</dt><dd>δ = ${evidence.configuration.primaryDelta}</dd></div></dl>`)}
    ${card("Automatic validation", "Required for every accepted variant.", `<div class="card-grid"><div class="callout"><strong>Structural checks</strong><p>Exactly one declared position changes and sequence length remains unchanged.</p></div><div class="callout"><strong>Rule-specific checks</strong><p>P1 redox-to-A, P2 eligible BLOSUM62 edit, and P3 seeded non-self substitution.</p></div></div>`)}
    <div class="callout success"><strong>Production generation passed</strong><p>${formatNumber.format(evidence.overview.fullVariants)} accepted variants with zero rejected records.</p></div>`;
}

function metricsView() {
  const metricRows = [
    ["IR", evidence.metrics.invarianceRate, `${evidence.metrics.invariantCount}/${evidence.metrics.invariantDenominator}`, "P2 edits with |ΔScore| < δ"],
    ["FSR", evidence.metrics.falseSensitivityRate, `${evidence.metrics.insufficientCount}/${evidence.metrics.insufficientDenominator}`, "P1 edits with |ΔScore| < δ"],
    ["BCS", evidence.metrics.preliminaryBcs, "IR × (1 − FSR)", "Combined behavioural consistency"],
    ["PFR", evidence.metrics.overallPfr, `${evidence.metrics.flipCount}/${evidence.metrics.flipDenominator}`, "Prediction flips across all edits"],
  ];
  const tiles = metricRows.map(([name, value, count, hint]) => card(name, hint, `<div class="metric-value"><strong>${percent(value)}</strong><span>${escapeHtml(count)}</span></div><div class="meter"><span style="width:${value * 100}%"></span></div>`)).join("");
  const sensitivityRows = evidence.sensitivity.map((row) => `<tr><th scope="row">${row.delta.toFixed(2)} ${row.primary ? '<span class="badge badge-success">Primary</span>' : ""}</th><td>${row.ir.toFixed(3)}</td><td>${row.fsr.toFixed(3)}</td><td>${row.bcs.toFixed(3)}</td></tr>`).join("");
  const figureNames = ["Absolute ΔScore distributions", "Original vs perturbed examples", "IR / FSR / BCS summary", "Prediction-flip comparison"];
  const figures = evidence.figures.map((figure, index) => `<figure class="card figure-card"><div class="card-header"><h3>${figureNames[index]}</h3></div><img src="${escapeHtml(figure.file)}" alt="${figureNames[index]} dummy software-pilot figure" loading="lazy" /><figcaption>SHA-256: <code>${figure.sha256.slice(0, 16)}…</code></figcaption></figure>`).join("");
  return `
    <div class="testing-banner"><strong>DUMMY PREDICTOR METRICS</strong><span>These values demonstrate the calculation pipeline only.</span></div>
    <div class="stat-grid">${tiles}</div>
    ${card("Delta-threshold sensitivity", "Primary δ = 0.05; strict comparison uses |ΔScore| < δ.", `<div class="table-wrap"><table><thead><tr><th>Delta</th><th>IR</th><th>FSR</th><th>BCS</th></tr></thead><tbody>${sensitivityRows}</tbody></table></div>`)}
    <div class="figure-grid">${figures}</div>
    ${safetyNote()}`;
}

function sequenceMarkup(sequence, position, className) {
  return [...sequence].map((residue, index) => `<span class="residue ${index + 1 === position ? className : ""}">${escapeHtml(residue)}</span>`).join("");
}

function explorerView() {
  const options = evidence.perturbations.map((row) => `<option value="${row.id}" ${row.id === explorerType ? "selected" : ""}>${row.id} — ${escapeHtml(row.title)}</option>`).join("");
  return `
    ${card("Variant explorer", "Inspect the six manually reviewed examples retained in the Task 3.33 artifact.", `<div class="filter-bar"><label class="field">Perturbation type<select id="explorer-type">${options}</select></label><div class="pager"><button class="button" id="previous-example" type="button">Previous</button><span id="explorer-position"></span><button class="button" id="next-example" type="button">Next</button></div></div>`)}
    <div id="explorer-detail"></div>
    ${safetyNote()}`;
}

function renderExplorerDetail() {
  const examples = evidence.examples.filter((row) => row.perturbation_type === explorerType);
  explorerIndex = ((explorerIndex % examples.length) + examples.length) % examples.length;
  const row = examples[explorerIndex];
  const methodMetadata = explorerType === "P2" ? `BLOSUM62 score ${row.blosum62_score}` : explorerType === "P3" ? `Master seed ${row.random_seed}` : "Redox residue replaced by alanine";
  document.querySelector("#explorer-position").textContent = `${explorerIndex + 1} of ${examples.length}`;
  document.querySelector("#explorer-detail").innerHTML = `
    ${card(`${row.mutation} · ${row.sequence_id}`, row.variant_id, `<div class="card-grid"><div><p><strong>Original sequence</strong></p><div class="sequence-box">${sequenceMarkup(row.original_sequence, row.position, "changed-from")}</div></div><div><p><strong>Perturbed sequence</strong></p><div class="sequence-box">${sequenceMarkup(row.perturbed_sequence, row.position, "changed-to")}</div></div></div><div class="stat-grid" style="margin-top:1.25rem">${statTile("Position", `${row.position} of ${row.original_sequence.length}`)}${statTile("Substitution", `${row.original_residue} → ${row.substituted_residue}`)}${statTile("Method metadata", methodMetadata)}${statTile("Inspection", row.inspection_status, "one-position edit verified")}</div>`)}
    ${card("Dummy score comparison", "Software-pipeline evidence only.", `<div class="score-grid">${statTile("Original score", row.original_score.toFixed(4))}${statTile("Perturbed score", row.perturbed_score.toFixed(4))}${statTile("DeltaScore", `${row.delta_score >= 0 ? "+" : ""}${row.delta_score.toFixed(4)}`)}</div>`)}
  `;
}

function predictorsView() {
  const rows = evidence.predictors.map((row) => `<tr class="predictor-row"><td class="number-cell">${String(row.order).padStart(2, "0")}</td><th scope="row">${escapeHtml(row.name)}<p>${escapeHtml(row.rationale)}</p></th><td><span class="badge ${row.tier === "primary" ? "badge-accent" : ""}">${escapeHtml(row.tier)}</span></td><td>${escapeHtml(row.readiness.replaceAll("-", " ").replaceAll("_", " "))}</td><td><span class="badge badge-danger">Not integrated</span></td></tr>`).join("");
  return `
    ${card("Predictor integration status", "A predictor stays not integrated until C3 retains a verified finite real score and its runtime/model evidence.", `<div class="table-wrap"><table><thead><tr><th>Order</th><th>Predictor</th><th>Tier</th><th>Readiness</th><th>Status</th></tr></thead><tbody>${rows}</tbody></table></div>`)}
    <div class="card-grid">
      ${card("PP1 minimum viable set", "Priority is based on reproducibility and access readiness.", `<ol><li>AOPxSVM</li><li>AnOxPePred</li><li>PU-AOP after the Component 2 handoff</li></ol>`)}
      ${card("PU-AOP dependency", "Component 2 handoff remains pending.", `<p>Required: frozen model selection, checkpoint and hash, preprocessing lineage, inference entry point, score semantics, dependencies, and a reference sequence with its expected score.</p><span class="badge badge-warning">C3 will not guess the model</span>`)}
    </div>
    ${safetyNote()}`;
}

function evidenceView() {
  const provenanceRows = [
    ["Run ID", evidence.provenance.runId], ["Run date", evidence.provenance.runDate], ["Dataset", evidence.provenance.datasetVersion],
    ["Predictor", evidence.provenance.predictorVersion], ["Code commit", evidence.provenance.codeCommit], ["Validation", evidence.provenance.validationStatus],
  ].map(([label, value]) => `<div><span>${label}</span><code>${escapeHtml(value)}</code></div>`).join("");
  const artifacts = evidence.provenance.sourceArtifacts.map((row) => `<tr><th scope="row">${escapeHtml(row.label)}</th><td><code>${escapeHtml(row.path)}</code></td><td><code>${row.sha256.slice(0, 12)}…</code></td><td><span class="badge badge-success">present</span></td></tr>`).join("");
  return `
    ${card("Research evidence & reproducibility", "This dashboard reads a deterministic snapshot generated from versioned C3 reports.", `<div class="stat-grid">${statTile("Source reports", evidence.provenance.sourceArtifacts.length)}${statTile("Generated figures", evidence.figures.length)}${statTile("Validation", evidence.provenance.validationStatus)}${statTile("Missing pilot scores", evidence.provenance.missingScores)}</div>`)}
    ${card("Run provenance", "Frozen software-pilot identity.", `<div class="provenance-grid">${provenanceRows}</div>`)}
    ${card("Tracked source reports", "Checksums are regenerated and verified before the local dashboard is served.", `<div class="table-wrap"><table><thead><tr><th>Category</th><th>File</th><th>SHA-256</th><th>Present</th></tr></thead><tbody>${artifacts}</tbody></table></div>`)}
    ${card("Current limitations", "Open scientific dependencies remain visible.", `<ul><li>No real predictor has produced a retained score through the C3 interface.</li><li>PU-AOP depends on a frozen Component 2 handoff.</li><li>The current IR, FSR, BCS, PFR, and ΔScore values have no biological interpretation.</li><li>The KernelSHAP backend and full faithfulness experiment remain later work.</li></ul>`, "limitations")}`;
}

const viewRenderers = { overview: overviewView, dataset: datasetView, perturbations: perturbationsView, metrics: metricsView, explorer: explorerView, predictors: predictorsView, evidence: evidenceView };

function currentRoute() {
  const route = location.hash.replace(/^#/, "");
  return ROUTES.includes(route) ? route : "overview";
}

function renderRoute() {
  if (!evidence) return;
  const route = currentRoute();
  document.querySelectorAll("#component-tabs a").forEach((link) => {
    const active = link.dataset.route === route;
    link.classList.toggle("active", active);
    if (active) link.setAttribute("aria-current", "page"); else link.removeAttribute("aria-current");
  });
  document.querySelector("#dashboard-view").innerHTML = viewRenderers[route]();
  if (route === "explorer") {
    renderExplorerDetail();
    document.querySelector("#explorer-type").addEventListener("change", (event) => { explorerType = event.target.value; explorerIndex = 0; renderExplorerDetail(); });
    document.querySelector("#previous-example").addEventListener("click", () => { explorerIndex -= 1; renderExplorerDetail(); });
    document.querySelector("#next-example").addEventListener("click", () => { explorerIndex += 1; renderExplorerDetail(); });
  }
  document.querySelector("#main-content").focus({ preventScroll: true });
}

function initialiseShell() {
  const sidebar = document.querySelector("#sidebar");
  const overlay = document.querySelector("#nav-overlay");
  const menuButton = document.querySelector("#menu-button");
  const closeMenu = () => { sidebar.classList.remove("open"); overlay.classList.remove("open"); menuButton.setAttribute("aria-expanded", "false"); };
  menuButton.addEventListener("click", () => {
    const open = sidebar.classList.toggle("open");
    overlay.classList.toggle("open", open);
    menuButton.setAttribute("aria-expanded", String(open));
  });
  overlay.addEventListener("click", closeMenu);
  document.querySelector("#component-tabs").addEventListener("click", closeMenu);

  const setTheme = (theme) => { document.documentElement.dataset.theme = theme; localStorage.setItem("plantaox-theme", theme); };
  setTheme(localStorage.getItem("plantaox-theme") === "dark" ? "dark" : "light");
  document.querySelector("#theme-button").addEventListener("click", () => setTheme(document.documentElement.dataset.theme === "dark" ? "light" : "dark"));
  addEventListener("hashchange", renderRoute);
}

initialiseShell();
fetch(DATA_URL)
  .then((response) => { if (!response.ok) throw new Error(`HTTP ${response.status}`); return response.json(); })
  .then((data) => { evidence = data; renderRoute(); })
  .catch((error) => { document.querySelector("#dashboard-view").innerHTML = `<article class="card error-card"><h3>Could not load Component 3 evidence</h3><p>${escapeHtml(error.message)}</p><code>Run npm run generate</code></article>`; });
