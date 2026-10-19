from __future__ import annotations

from backend.app.schemas.c1_procon import HeroStat, OverviewResponse, PipelineStep, ScientificCaveats
from backend.app.services.c1_procon.artifacts import read_json
from backend.app.services.c1_procon.dataset import get_dataset
from backend.app.services.c1_procon.probe import get_probe
from backend.app.services.c1_procon.retrieval import get_retrieval

RESEARCH_TITLE = "AOP-ProCon: Leak-Controlled Benchmark and Evaluation of Contrastive Retrieval for Antioxidant Peptides"
OBJECTIVE = (
    "Build a leak-controlled, multi-label (FRS / MC / FRS;MC / GEN), provenance-tracked benchmark of plant "
    "antioxidant peptides, and test honestly whether a contrastive head on frozen ESM-2 embeddings adds mechanism "
    "information beyond untrained embeddings, amino-acid composition, length and data source."
)

PIPELINE_STEPS = [
    PipelineStep(step=1, title="Dataset curation", status="complete", notebook="STEP01_V2_Dataset_Curation_FINAL",
                 summary="Four public databases merged into one multi-label benchmark; homology groups; strict evidence."),
    PipelineStep(step=2, title="Descriptors and embeddings", status="complete", notebook="STEP02_V2_Descriptors_Embeddings_FIXED",
                 summary="14 descriptors and frozen ESM-2 embeddings at four sizes (35M, 150M, 650M, 3B)."),
    PipelineStep(step=3, title="Positive pairs", status="complete", notebook="STEP03_V2_Positive_Pairs_FIXED",
                 summary="Same-mechanism pairs in three evidence modes, with random and physico-chemical controls."),
    PipelineStep(step=4, title="Contrastive training", status="complete", notebook="STEP04_V2_Training_FIXED",
                 summary="15 contrastive heads and a collapse report."),
    PipelineStep(step=5, title="Evaluation", status="complete", notebook="STEP05_V2_Evaluation_FIXED",
                 summary="MC retrieval against baselines, paired confidence intervals, repeated grouped-CV probe."),
    PipelineStep(step=6, title="Seeds, scale, reverse fold", status="complete", notebook="STEP06_V2_Seeds_Scale_Reverse",
                 summary="5 recipes x 5 seeds, four model sizes, and the reverse fold direction."),
    PipelineStep(step=7, title="Release package", status="complete", notebook="STEP07_V2_Release_Package",
                 summary="Hash-verified release with an integration contract for Components 2-4."),
    PipelineStep(step=8, title="Confound controls", status="complete", notebook="STEP08_Confound_Controls",
                 summary="Source, length, split-design and data-size controls."),
]

KNOWN_LIMITATIONS = [
    "Only 104 MC-active peptides (75 from a single source) and 49 retrieval queries: small differences are not detectable.",
    "Labels combine assay-level and database-level evidence; no external validation set exists yet.",
    "Every FRS-only peptide comes from one database, so data source alone already separates the classes (AUROC 0.64).",
    "Tripeptides (36% of the data) cannot be grouped by sequence similarity reliably, so some leakage risk remains.",
    "Bootstrap confidence intervals keep the fitted models fixed and therefore understate the true uncertainty.",
    "The probe scores are not activity or safety predictors; GEN means mechanism not established, not inactive.",
]


def get_overview() -> OverviewResponse:
    manifest = read_json("step1_manifest.json")
    dataset = get_dataset()
    retrieval = get_retrieval()
    probe = get_probe()

    counts = {
        "peptides": sum(item.count for item in dataset.label_counts),
        "homology_groups": int(manifest["counts"]["homology_groups"]),
        "strict_pool": dataset.strict_pool["peptides"],
        "strict_mc_active": dataset.strict_pool["mc_active"],
        "strict_frs_only": dataset.strict_pool["frs_only"],
        "trained_runs": retrieval.trained_runs_total,
    }

    ap = {r.representation: r.ap for r in retrieval.representations}
    grouped = {p.features: p.auroc for p in probe.grouped}
    findings = [
        (
            f"Retrieval: no trained head beats the untrained embedding ({retrieval.trained_runs_above_untrained} of "
            f"{retrieval.trained_runs_total} trained runs above it); length-only AP {ap['LENGTH']:.3f} and untrained "
            f"ESM-2 650M AP {ap['RAW 650M']:.3f} are higher than the main trained model ({ap['Primary']:.3f}); "
            f"a random ranking scores {retrieval.chance_ap:.3f}."
        ),
        (
            f"Probe: ESM-2 650M reaches fold-mean AUROC {grouped['ESM-2 650M']:.2f}, while the single feature 'data source' "
            f"reaches {grouped['SOURCE']:.2f}; composition + length + source reaches {grouped['AAC-20 + LENGTH + SOURCE']:.2f}."
        ),
        (
            "Leakage: random (leaky) folds inflate AUROC by "
            + ", ".join(f"{k} +{v:.2f}" for k, v in probe.leakage_inflation.items())
            + "."
        ),
        "After source, length and homology controls, no ESM-2-specific mechanism signal remains (Step 8).",
    ]

    hero_stats = [
        HeroStat(
            value=f"{counts['peptides']:,}",
            label="unique peptides",
            hint=f"{counts['homology_groups']} similarity groups; none is split between train and test",
        ),
        HeroStat(
            value=f"{retrieval.trained_runs_above_untrained} of {retrieval.trained_runs_total}",
            label="trained runs beat the untrained embedding",
            hint="5 training recipes x 5 random seeds",
        ),
        HeroStat(
            value=f"{grouped['SOURCE']:.2f} vs {grouped['ESM-2 650M']:.2f}",
            label="data source alone vs ESM-2 (AUROC)",
            hint="a hidden shortcut explains as much as the AI model",
        ),
        HeroStat(
            value=f"+{max(probe.leakage_inflation.values()):.2f}",
            label="score inflation from leaky splits",
            hint="random folds make the same model look better than it is",
        ),
    ]

    return OverviewResponse(
        research_title=RESEARCH_TITLE,
        objective=OBJECTIVE,
        benchmark_fingerprint=dataset.fingerprint,
        counts=counts,
        label_counts={item.label: item.count for item in dataset.label_counts},
        pipeline_steps=PIPELINE_STEPS,
        hero_stats=hero_stats,
        headline_findings=findings,
        caveats=ScientificCaveats(
            technical_status="Pipeline Steps 1-8 complete; every notebook asserts the dataset fingerprint and SHA-256 of its inputs.",
            scientific_status="Negative result for the contrastive head; positive result for the leak-controlled benchmark and evaluation protocol.",
            known_limitations=KNOWN_LIMITATIONS,
        ),
    )
