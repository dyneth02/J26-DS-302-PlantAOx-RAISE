# AGENTS.md — Component 02 (PU-AOP)

Standing instructions for any AI coding agent (Codex, Claude Code, or similar) working in this part of the repository. Read this before touching any PU-AOP code, data, or docs. For background on *why* things are the way they are, read `PU_AOP_RESEARCH_CONTEXT.md`. For current task state, read `IMPLEMENTATION_STATUS.md`.

---

## Scope

- You are working on **Component 02 — PU-AOP** only. Do not modify files belonging to Components 1, 3, or 4 unless explicitly instructed in a given task, even if you notice something that looks related.
- If a task implies cross-component changes (e.g., the PROB_C2 handoff to Component 3/4 — FR7, a later milestone), stop and flag it rather than proceeding unprompted.

## Research constraints (non-negotiable)

1. **C1, C2, and C3 are unlabeled "assumption" pools, never confirmed negatives.** Never write code, comments, variable names, or report language that calls them "negatives" in the labeled-ground-truth sense. Correct framing: "assumed non-antioxidant," "unlabeled challenge pool," "negative-assumption set." This distinction is the methodological core of the PU-learning design — getting it wrong isn't a style issue, it's a correctness issue.
2. **The AnOxPePred experimentally-inactive subset is an external control, not training data.** Keep it in a separate file/variable path from C1/C2/C3 at all times. Never merge it into the unlabeled training pools.
3. **No claiming FR completion without acceptance evidence.** FR1 is only "done" when task 1.7's acceptance checklist passes. FR2 is only "done" when task 2.7's passes. Do not mark something complete in `IMPLEMENTATION_STATUS.md` or in any report because the code *runs* — it must pass the defined acceptance checks first (see Validation section below).
4. **Frozen artifacts stay frozen.** Once a split index, pool FASTA, or config is frozen (documented as such in `IMPLEMENTATION_STATUS.md`), do not regenerate or silently overwrite it. If a change is genuinely needed, create a new version with a new ID and log why the old one was superseded — never mutate in place.
5. **Reproducibility is mandatory, not a nice-to-have.** Every stochastic step (sampling, splitting, initialization) needs a fixed, logged seed. Every external data pull needs a provenance record (source URL, access date, version/commit hash, query used).
6. **Known filtering limitations are documented, not silently "fixed" forever.** The C1 bioactivity keyword filter has an accepted, documented residual error rate (see `PU_AOP_RESEARCH_CONTEXT.md` §7). Do not treat every newly-discovered edge case as a bug to chase indefinitely — check `IMPLEMENTATION_STATUS.md`'s known issues first. If something is already logged as an accepted limitation, add to the documentation, don't reopen an unbounded fix cycle without being asked.

## Implementation rules

1. **Use the canonical file/artifact names already established** in the Research Deliverable Registry table (in the Planner breakdown doc) — e.g. `data_registry.csv`, `aop_positives.parquet`, `stage_c1_decoys.fasta`, `cdhit_clusters.tsv`, `graphpart_splits.csv`. Do not invent parallel files or duplicate registries for the same purpose.
2. **String/keyword lists must be case-normalized at definition time**, not relied on to match case-sensitively at comparison time. A real bug already occurred from this (a blocklist entry added with a capital letter silently never matched). Use a pattern like `[kw.lower() for kw in [...]]` for any new or edited keyword list, and lowercase the comparison target too.
3. **When extending the bioactivity keyword blocklist** (in `PU_AOP_RESEARCH_CONTEXT.md` §5), add to the existing list — don't regenerate it from scratch, and don't remove existing entries without a logged reason in `IMPLEMENTATION_STATUS.md`'s decision log.
4. **Prefer UniProt's own controlled-vocabulary keywords** (`keyword:Toxin`, `keyword:Antioxidant`, etc., confirmed via the official keyword list) over free-text name matching wherever an equivalent keyword exists — it's more reliable than guessing peptide family names.
5. **Training-fold-only fitting:** any normalization, scaling, or centroid computation (e.g., the ESM-2 embedding centroid for C3 hard-challenge selection) must be fit on the training partition only and applied, not refit, elsewhere. This is a leakage-prevention rule, not a style preference.
6. **Don't bulk-download full databases when a filtered API query will do.** (E.g., UniRef50's full FASTA is ~13GB; a length+keyword-filtered REST query returns megabytes.) Check whether a targeted query exists before reaching for a full dump.

## Validation requirements

Before marking any task "complete" in `IMPLEMENTATION_STATUS.md`:

1. **Automated check on the FULL output artifact, not a sample.** A recurring pattern in this project was validating only small random previews (25 records) across many iterations rather than the full file. Automated checks must run against the complete final artifact before sign-off.
2. **A manual spot-check is still required even after automated filters pass.** Automated keyword/metadata filters have real, demonstrated coverage gaps. Pull a fresh random sample (new seed from the automated one, so it's not the same slice repeatedly) and have a human or a careful agent review names/descriptions for anything that looks like a missed category.
3. **Reproducibility check:** re-running the generation pipeline from raw/versioned inputs with the logged seed must reproduce the same output (same count, same records). If it doesn't, something is non-deterministic and must be found before sign-off.
4. **Leakage checks pass or are explicitly waived with a documented exception.** Never silently skip a homology/overlap check because it's inconvenient.
5. **Update the provenance log and `IMPLEMENTATION_STATUS.md` in the same change** that produces or modifies a dataset artifact — a dataset change without an updated log is treated as incomplete work, not just missing paperwork.
6. **Stopping rule for iterative quality work:** if three consecutive rounds of manual review find only increasingly rare/obscure issues (not a new systematic category), that is the signal to stop iterating, document the residual risk explicitly, and move on — not a signal to keep tightening the filter indefinitely. Flag this situation in `IMPLEMENTATION_STATUS.md` rather than deciding unilaterally to continue or stop.

## When in doubt

If a task's acceptance criteria, data source, or scope is ambiguous (e.g., the SwissProt-vs-UniRef50 conflict, see `PU_AOP_RESEARCH_CONTEXT.md` §4), make the most defensible documented choice, log it in `IMPLEMENTATION_STATUS.md`'s decision log with rationale, and flag it for supervisor confirmation rather than silently picking one and moving on without a trace.
