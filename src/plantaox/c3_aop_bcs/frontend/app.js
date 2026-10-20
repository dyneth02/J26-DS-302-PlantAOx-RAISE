const dataUrl = "assets/generated/presentation-data.json";
let data;
let activeType = "P1";
let activeExampleIndex = 0;

const number = new Intl.NumberFormat("en-US");
const percent = (value, digits = 1) => `${(value * 100).toFixed(digits)}%`;
const escapeHtml = (value) => String(value)
  .replaceAll("&", "&amp;")
  .replaceAll("<", "&lt;")
  .replaceAll(">", "&gt;")
  .replaceAll('"', "&quot;")
  .replaceAll("'", "&#039;");

async function loadPresentation() {
  const response = await fetch(dataUrl);
  if (!response.ok) throw new Error(`Unable to load presentation evidence (${response.status}).`);
  data = await response.json();
  renderPresentation();
}

function renderPresentation() {
  renderHeroStats();
  renderDatasetFunnel();
  renderCoverage();
  renderPerturbations();
  renderPipeline();
  renderMetrics();
  renderSensitivity();
  renderFigures();
  renderVariantExplorer();
  renderPredictors();
  renderProvenance();
  document.querySelector("#footer-version").textContent = `${data.presentationId} · evidence ${data.evidenceDate}`;
}

function renderHeroStats() {
  const stats = [
    [number.format(data.overview.pilotSubjects), "pilot peptides", "coverage-selected"],
    [number.format(data.overview.pilotVariants), "pilot perturbations", "P1 + P2 + P3"],
    [number.format(data.overview.fullVariants), "full valid variants", "0 rejected"],
    [String(data.configuration.seed), "master seed", "reproducible P3"],
  ];
  document.querySelector("#hero-stats").innerHTML = stats.map(([value, label, hint]) => `
    <div class="hero-stat"><strong>${value}</strong><span>${label}</span><small>${hint}</small></div>
  `).join("");
}

function renderDatasetFunnel() {
  const maximum = data.datasetFunnel[0].count;
  document.querySelector("#dataset-funnel").innerHTML = data.datasetFunnel.map((stage, index) => {
    const width = 32 + (stage.count / maximum) * 68;
    return `<article class="funnel-stage" style="--funnel-width:${width}%">
      <div class="funnel-index">${String(index + 1).padStart(2, "0")}</div>
      <div class="funnel-copy"><strong>${escapeHtml(stage.label)}</strong><small>${escapeHtml(stage.detail)}</small></div>
      <div class="funnel-bar"><span></span></div>
      <b>${number.format(stage.count)}</b>
    </article>`;
  }).join("");
}

function renderCoverage() {
  const facts = [
    ["Length range", data.coverage.lengthRange],
    ["Distinct lengths", data.coverage.distinctLengths],
    ["Redox set", data.coverage.redoxResidues.join(" · ")],
    ["Max subject share", percent(data.coverage.maximumVariantShare)],
  ];
  document.querySelector("#coverage-facts").innerHTML = facts.map(([label, value]) => `<div><dt>${label}</dt><dd>${value}</dd></div>`).join("");
}

function renderPerturbations() {
  const examples = { P1: "WYHMC → A", P2: "L → I", P3: "G → K" };
  document.querySelector("#perturbation-cards").innerHTML = data.perturbations.map((item) => `
    <article class="perturbation-card ${item.tone}">
      <div class="perturbation-top"><span>${item.id}</span><small>${escapeHtml(item.subtitle)}</small></div>
      <div class="mutation-demo">${examples[item.id]}</div>
      <h3>${escapeHtml(item.title)}</h3>
      <p class="question">${escapeHtml(item.question)}</p>
      <p class="rule">${escapeHtml(item.rule)}</p>
      <div class="count-row"><span><strong>${number.format(item.pilotCount)}</strong> pilot</span><span><strong>${number.format(item.fullCount)}</strong> full</span></div>
    </article>
  `).join("");
}

function renderPipeline() {
  const steps = [
    ["01", "Annotated peptide"], ["02", "Generate P1 / P2 / P3"], ["03", "Validate one-residue edit"],
    ["04", "Score & cache"], ["05", "Calculate ΔScore"], ["06", "Aggregate IR / FSR / BCS"],
  ];
  document.querySelector("#pipeline-band").innerHTML = steps.map(([index, label], i) => `
    <div class="pipeline-step"><span>${index}</span><strong>${label}</strong></div>${i < steps.length - 1 ? '<i aria-hidden="true">→</i>' : ""}
  `).join("");
}

function renderMetrics() {
  const metrics = [
    { key: "IR", value: data.metrics.invarianceRate, count: `${data.metrics.invariantCount}/${data.metrics.invariantDenominator}`, label: "Invariance rate", description: "P2 edits below δ", tone: "teal" },
    { key: "FSR", value: data.metrics.falseSensitivityRate, count: `${data.metrics.insufficientCount}/${data.metrics.insufficientDenominator}`, label: "False sensitivity rate", description: "P1 edits below δ", tone: "coral" },
    { key: "BCS", value: data.metrics.preliminaryBcs, count: "IR × (1 − FSR)", label: "Preliminary BCS", description: "Combined consistency", tone: "violet" },
    { key: "PFR", value: data.metrics.overallPfr, count: `${data.metrics.flipCount}/${data.metrics.flipDenominator}`, label: "Prediction flip rate", description: "All pilot edits", tone: "amber" },
  ];
  document.querySelector("#metric-scorecard").innerHTML = metrics.map((metric) => `
    <article class="metric-card ${metric.tone}">
      <div class="metric-head"><span>${metric.key}</span><small>${metric.count}</small></div>
      <strong>${percent(metric.value)}</strong>
      <h3>${metric.label}</h3><p>${metric.description}</p>
      <div class="metric-meter"><span style="width:${metric.value * 100}%"></span></div>
    </article>
  `).join("");
}

function renderSensitivity() {
  const max = Math.max(...data.sensitivity.map((row) => row.bcs));
  document.querySelector("#sensitivity-chart").innerHTML = data.sensitivity.map((row) => `
    <div class="sensitivity-row ${row.primary ? "primary" : ""}">
      <div><strong>δ ${row.delta.toFixed(2)}</strong>${row.primary ? "<span>primary</span>" : ""}</div>
      <div class="sensitivity-track"><i style="width:${(row.bcs / max) * 100}%"></i></div>
      <b>${row.bcs.toFixed(3)}</b>
    </div>
  `).join("");
}

function renderFigures() {
  const labels = ["|ΔScore| distributions", "Score examples", "IR / FSR / BCS", "Prediction flips"];
  document.querySelector("#figure-grid").innerHTML = data.figures.map((figure, index) => `
    <figure class="result-figure">
      <div><span class="eyebrow">Generated evidence ${String(index + 1).padStart(2, "0")}</span><strong>${labels[index]}</strong></div>
      <img src="${escapeHtml(figure.file)}" alt="${labels[index]} pilot software-testing figure" loading="lazy" />
      <figcaption>Source checksum <code>${figure.sha256.slice(0, 12)}…</code></figcaption>
    </figure>
  `).join("");
}

function sequenceMarkup(sequence, position, role) {
  return [...sequence].map((residue, index) => {
    const mutated = index + 1 === position;
    return `<span class="residue ${mutated ? `mutated ${role}` : ""}"><i>${index + 1}</i>${escapeHtml(residue)}</span>`;
  }).join("");
}

function renderVariantExplorer() {
  const examples = data.examples.filter((row) => row.perturbation_type === activeType);
  activeExampleIndex = ((activeExampleIndex % examples.length) + examples.length) % examples.length;
  const example = examples[activeExampleIndex];
  const extra = activeType === "P2"
    ? `<div><dt>BLOSUM62 score</dt><dd>${example.blosum62_score}</dd></div>`
    : activeType === "P3"
      ? `<div><dt>Master seed</dt><dd>${example.random_seed}</dd></div>`
      : `<div><dt>Rule</dt><dd>Redox residue → A</dd></div>`;
  document.querySelector("#example-position").textContent = `${activeExampleIndex + 1} / ${examples.length}`;
  document.querySelector("#variant-explorer").innerHTML = `
    <div class="explorer-title"><div><span class="pill pill-${activeType.toLowerCase()}">${activeType}</span><h3>${escapeHtml(example.mutation)}</h3></div><code>${escapeHtml(example.variant_id)}</code></div>
    <div class="sequence-compare">
      <div><label>Original sequence</label><div class="sequence-line">${sequenceMarkup(example.original_sequence, example.position, "before")}</div></div>
      <div class="sequence-arrow" aria-hidden="true">↓</div>
      <div><label>Perturbed sequence</label><div class="sequence-line">${sequenceMarkup(example.perturbed_sequence, example.position, "after")}</div></div>
    </div>
    <dl class="variant-facts">
      <div><dt>Position</dt><dd>${example.position} of ${example.original_sequence.length}</dd></div>
      <div><dt>Substitution</dt><dd>${escapeHtml(example.original_residue)} → ${escapeHtml(example.substituted_residue)}</dd></div>
      ${extra}
      <div><dt>Validation</dt><dd><span class="pass-dot"></span>${escapeHtml(example.inspection_status)}</dd></div>
    </dl>
    <div class="score-comparison">
      <div><span>Original dummy score</span><strong>${example.original_score.toFixed(4)}</strong></div>
      <i>−</i>
      <div><span>Perturbed dummy score</span><strong>${example.perturbed_score.toFixed(4)}</strong></div>
      <i>=</i>
      <div class="delta"><span>ΔScore</span><strong>${example.delta_score >= 0 ? "+" : ""}${example.delta_score.toFixed(4)}</strong></div>
    </div>
    <p class="explorer-warning">Dummy software score for pipeline validation only. No biological interpretation.</p>
  `;
}

function renderPredictors() {
  const readinessLabel = (value) => value.replaceAll("-", " ").replaceAll("_", " ");
  document.querySelector("#predictor-list").innerHTML = data.predictors.map((predictor) => `
    <article class="predictor-row">
      <div class="predictor-order">${String(predictor.order).padStart(2, "0")}</div>
      <div class="predictor-copy"><div><h3>${escapeHtml(predictor.name)}</h3><span class="pill ${predictor.tier === "primary" ? "pill-accent" : ""}">${predictor.tier}</span></div><p>${escapeHtml(predictor.rationale)}</p></div>
      <div class="readiness-state"><span>${escapeHtml(readinessLabel(predictor.readiness))}</span><strong>Not integrated</strong></div>
    </article>
  `).join("");
}

function renderProvenance() {
  const rows = [
    ["Run", data.provenance.runId], ["Date", data.provenance.runDate], ["Dataset", data.provenance.datasetVersion],
    ["Predictor", data.provenance.predictorVersion], ["Code commit", data.provenance.codeCommit], ["Validation", data.provenance.validationStatus],
  ];
  document.querySelector("#provenance-grid").innerHTML = rows.map(([label, value]) => `<div><span>${label}</span><code>${escapeHtml(value)}</code></div>`).join("");
}

function setType(type) {
  activeType = type;
  activeExampleIndex = 0;
  document.querySelectorAll("#variant-filter button").forEach((button) => button.classList.toggle("active", button.dataset.type === type));
  renderVariantExplorer();
}

function initialiseControls() {
  document.querySelector("#variant-filter").addEventListener("click", (event) => {
    const button = event.target.closest("button[data-type]");
    if (button) setType(button.dataset.type);
  });
  document.querySelector("#previous-example").addEventListener("click", () => { activeExampleIndex -= 1; renderVariantExplorer(); });
  document.querySelector("#next-example").addEventListener("click", () => { activeExampleIndex += 1; renderVariantExplorer(); });

  const sidebar = document.querySelector("#sidebar");
  const menuToggle = document.querySelector("#menu-toggle");
  const scrim = document.querySelector("#nav-scrim");
  const closeMenu = () => { sidebar.classList.remove("open"); scrim.classList.remove("open"); menuToggle.setAttribute("aria-expanded", "false"); };
  menuToggle.addEventListener("click", () => {
    const open = sidebar.classList.toggle("open");
    scrim.classList.toggle("open", open);
    menuToggle.setAttribute("aria-expanded", String(open));
  });
  scrim.addEventListener("click", closeMenu);
  document.querySelector("#section-nav").addEventListener("click", closeMenu);

  const setTheme = (theme) => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem("plantaox-theme", theme);
  };
  setTheme(localStorage.getItem("plantaox-theme") === "dark" ? "dark" : "light");
  const toggleTheme = () => setTheme(document.documentElement.dataset.theme === "dark" ? "light" : "dark");
  document.querySelector("#theme-toggle").addEventListener("click", toggleTheme);
  document.querySelector("#theme-toggle-mobile").addEventListener("click", toggleTheme);

  document.querySelector("#presentation-toggle").addEventListener("click", async (event) => {
    document.body.classList.toggle("presentation-mode");
    event.currentTarget.textContent = document.body.classList.contains("presentation-mode") ? "Exit presentation mode" : "Presentation mode";
  });

  const links = [...document.querySelectorAll("#section-nav a")];
  const observer = new IntersectionObserver((entries) => {
    const visible = entries.filter((entry) => entry.isIntersecting).sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
    if (!visible) return;
    links.forEach((link) => link.classList.toggle("active", link.hash === `#${visible.target.id}`));
  }, { rootMargin: "-20% 0px -60%", threshold: [0.05, 0.25] });
  document.querySelectorAll("[data-section]").forEach((section) => observer.observe(section));
}

initialiseControls();
loadPresentation().catch((error) => {
  document.querySelector("#main-content").innerHTML = `<section class="load-error"><h1>Presentation evidence could not be loaded.</h1><p>${escapeHtml(error.message)}</p><code>Run: npm run generate</code></section>`;
});
