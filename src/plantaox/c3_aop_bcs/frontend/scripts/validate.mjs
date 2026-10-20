import { createHash } from "node:crypto";
import { execFileSync } from "node:child_process";
import { readFile } from "node:fs/promises";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const scriptDirectory = dirname(fileURLToPath(import.meta.url));
const frontendDirectory = resolve(scriptDirectory, "..");
const repositoryRoot = resolve(frontendDirectory, "../../../../");
const data = JSON.parse(await readFile(join(frontendDirectory, "assets/generated/presentation-data.json"), "utf8"));
const html = await readFile(join(frontendDirectory, "index.html"), "utf8");
const css = await readFile(join(frontendDirectory, "styles.css"), "utf8");
const app = await readFile(join(frontendDirectory, "app.js"), "utf8");

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

assert(data.classification.software_testing_only === true, "Testing-only classification must be preserved.");
assert(data.classification.scientific_result === false, "Dummy evidence must not be marked scientific.");
assert(data.classification.real_predictor_scoring_completed === false, "Real scoring must remain pending.");
assert(data.overview.pilotSubjects === 20 && data.overview.pilotVariants === 449, "Pilot counts changed.");
assert(data.perturbations.map((row) => row.pilotCount).join(",") === "54,150,245", "P1/P2/P3 counts changed.");
assert(data.examples.length === 6, "Exactly six inspected examples are required.");
for (const type of ["P1", "P2", "P3"]) {
  assert(data.examples.filter((row) => row.perturbation_type === type).length === 2, `${type} must have two examples.`);
}
assert(data.predictors.every((row) => row.status === "not_integrated"), "No real predictor may be shown as integrated.");
assert(data.provenance.sourceArtifacts.every((row) => row.path.includes("c3_aop_bcs")), "A non-C3 source entered the snapshot.");
assert(html.includes("Software validation only") && html.includes("not scientific"), "Visible safety labels are missing.");
for (const section of ["overview", "problem", "data", "method", "results", "explorer", "readiness", "provenance"]) {
  assert(html.includes(`id="${section}"`), `Presentation section ${section} is missing.`);
}
assert(!/(https?:)?\/\//i.test(html), "The standalone page must not load external resources.");
assert(css.includes("@media (max-width: 760px)"), "Mobile layout rules are missing.");
assert(app.includes("renderVariantExplorer") && app.includes("IntersectionObserver"), "Interactive explorer or navigation is missing.");

for (const figure of data.figures) {
  const content = await readFile(join(frontendDirectory, figure.file));
  const digest = createHash("sha256").update(content).digest("hex");
  assert(digest === figure.sha256, `Copied figure checksum mismatch: ${figure.file}`);
  assert(figure.sourcePath.includes("c3_aop_bcs"), `Figure is outside C3: ${figure.sourcePath}`);
}

const statusEntries = execFileSync("git", ["status", "--porcelain=v1", "-z"], {
  cwd: repositoryRoot,
  encoding: "utf8",
}).split("\0").filter(Boolean);
const changedPaths = statusEntries.map((entry) => entry.slice(3).replaceAll("\\", "/"));
const outOfScope = changedPaths.filter((path) => !path.includes("c3_aop_bcs"));
assert(outOfScope.length === 0, `Out-of-scope working-tree changes detected: ${outOfScope.join(", ")}`);

console.log("PASS: presentation content, evidence boundary, interaction hooks, mobile rules, and copied-figure checksums validated.");
