# Component 4 Data and Output Contracts

## Current input inventory

The four official query results below were downloaded unchanged on 19 October 2026 (Asia/Colombo) and are retained at `data/raw/c4_screen/proteomes/source_downloads/`. Canonical plant-named copies are at `data/raw/c4_screen/proteomes/<plant>.fasta`; these are byte-identical. Each query uses the plant taxonomy ID and `reviewed:true`. UniProt response headers confirmed release `2026_03` (release date 02 September 2026); the header checks for the four exact queries returned 18 October 2026 19:36–19:37 UTC. The count is the number of FASTA header lines (`>`), i.e. reviewed protein records, not generated peptide candidates.

| File | Taxonomy/query | Protein records | Bytes | SHA-256 |
|---|---|---:|---:|---|
| `proteomes/source_downloads/uniprot_reviewed_3847_glycine_max.fasta` | *Glycine max*, 3847 | 439 | 194,033 | `AD2C96C599CBD327A957BCB86ACE1C678A7F2EBC1D339ACEAA51FB79D48C24A7` |
| `proteomes/source_downloads/uniprot_reviewed_39947_oryza_sativa_japonica.fasta` | *Oryza sativa* subsp. *japonica*, 39947 | 4,197 | 2,480,333 | `D2D3939436DBD26CC328CF45145263AB67551F4D63279DB624477FB3A0A55FFB` |
| `proteomes/source_downloads/uniprot_reviewed_3708_brassica_napus.fasta` | *Brassica napus*, 3708 | 159 | 66,781 | `7C98D4D0CD93FBC25A75F8B76B8A43E6FE1BCAFA7443CFF8C2F57A4BC13160EF` |
| `proteomes/source_downloads/uniprot_reviewed_4146_olea_europaea.fasta` | *Olea europaea*, 4146 | 110 | 24,630 | `ECF93A4676A8AE137228B22C4D423211E79325E6ACB5C629CA0770E6D1407456` |

The exact query URLs are:

- Soybean: <https://rest.uniprot.org/uniprotkb/stream?compressed=false&format=fasta&query=%28taxonomy_id%3A3847%29+AND+%28reviewed%3Atrue%29>
- Rice: <https://rest.uniprot.org/uniprotkb/stream?compressed=false&format=fasta&query=%28taxonomy_id%3A39947%29+AND+%28reviewed%3Atrue%29>
- Rapeseed: <https://rest.uniprot.org/uniprotkb/stream?compressed=false&format=fasta&query=%28taxonomy_id%3A3708%29+AND+%28reviewed%3Atrue%29>
- Olive: <https://rest.uniprot.org/uniprotkb/stream?compressed=false&format=fasta&query=%28taxonomy_id%3A4146%29+AND+%28reviewed%3Atrue%29>

Each downloaded file has the same byte size and SHA-256 as the corresponding pre-existing `soybean.txt`, `rice.txt`, `rapeseed.txt`, or `olive.txt`. The old files therefore match these official query results byte-for-byte. The observed input counts are far below the proposal's 5,000–50,000 *candidate-peptide* estimate for three plants; protein-record counts are not directly comparable to post-digestion, post-deduplication peptide counts. Keep all four target plants in scope and revisit the candidate estimate after the FR1 funnel is implemented and measured.

The tracked checksum manifest is [`SCREEN_PP1_CHECKSUMS.sha256`](SCREEN_PP1_Checksums.sha256). From the repository root, verify the local FASTA files with `sha256sum -c src/plantaox/c4_screen/docs/SCREEN_PP1_CHECKSUMS.sha256` or an equivalent SHA-256 checker on Windows. Raw files under `data/raw/` and NumPy `.npy` matrices are intentionally ignored by Git; commit provenance, schema/shape, and hashes instead. The four C4 FASTAs remain in the local working tree but are not tracked in Git. The ignore rule does not remove previously tracked prototype `.npy` files, which remain under version control because prototype scripts reference them.

## Required provenance registry

Before using an input for candidate generation, record one row per source artifact with:

- plant scientific/common name, taxonomy ID, and proteome/reference-proteome identifier where applicable;
- UniProt query URL or API parameters, reviewed-status filter, retrieval timestamp, and data release;
- original source filename, byte size, SHA-256, and repository-relative path;
- parser/version, total records, accepted records, exclusions by reason, and sequence alphabet/length checks;
- immutable raw-input policy and any transformation lineage.

Do not replace a frozen raw file in place. A changed source or query creates a new version and updated registry entry.

## Planned artifact registry

Names below are recommendations aligned to the PP1 inventory. Implementations may use established shared-repository conventions, but must not create duplicate artifacts for the same logical data.

| Artifact | Suggested location/name | Minimum contents |
|---|---|---|
| Data registry | `data/processed/c4_screen/c4_data_registry.csv` | Provenance fields above plus parsed counts and status |
| Candidate tables | `data/processed/c4_screen/c4_candidates_<plant>.parquet` | Stable candidate ID, sequence, plant, descriptors, full provenance |
| Combined candidate table | `data/processed/c4_screen/c4_candidates.parquet` | Same schema across plants; no silent field loss |
| Candidate FASTA | `data/processed/c4_screen/c4_candidates.fasta` | Stable IDs and parsable provenance annotations for C1/C2 handoff |
| Funnel summary | `data/processed/c4_screen/c4_funnel_summary.csv` | Counts by plant and processing stage, with exclusion counts |
| Embeddings | `data/processed/c4_screen/c4_esm2_t33_650M.npy` plus ID map | N×1280 numeric matrix aligned to explicit stable ID ordering |
| Embedding manifest | `data/processed/c4_screen/c4_embedding_manifest.json` | Model/weights, recipe, software, dtype, shape, row-ID hash, source hash |
| Reference cloud | Versioned cloud matrix and metadata | Sequence IDs, evidence/source labels, model recipe, provenance, split/exclusion checks |
| AD parameters | `data/processed/c4_screen/ad_params.json` | Cloud ID/hash, centroid/calibration recipe, mean/std convention, thresholds, fit date/version |
| Tier table | `data/processed/c4_screen/c4_ad_tiers.parquet` | Candidate ID, distance, tier, parameter version, reference mode |
| Signal inputs | Contract-versioned C1/C2/C3 files | Candidate key, signal, source/model version, generation metadata, missingness/status |
| Dummy manifest | `data/processed/c4_screen/DUMMY_MANIFEST.json` | Generator/version, seed, deterministic fixture description, hashes, explicit dummy flag |
| Ranking | `data/processed/c4_screen/c4_ranking.parquet` | Signals, normalized AD term, weights, score, tier, stable rank, provenance links |
| Evidence cards | `data/processed/c4_screen/cards.json` | Candidate evidence, signal sources, tier/flag, BCS context, dummy/provisional labels |
| Run summary | `data/processed/c4_screen/summary.json` | Config and input hashes, software/model versions, counts, warnings and output hashes |
| PP1 freeze | `data/processed/c4_screen/c4_pp1_freeze_manifest.json` | Frozen input/output hashes and exact run/config/environment identifiers |

The paths are proposed; no listed processed artifact is currently present.

## Stable identifiers and joins

Candidate tables need a stable peptide ID derived from a documented sequence hash, while provenance remains a one-to-many relation. Plant membership must be retained because an identical peptide may originate from multiple plants. Signal joins must use a stable candidate key, assert uniqueness at the declared grain, and report unmatched/duplicate rows. Never join by row position alone.

## Serialization and missingness

Choose schemas explicitly and version them. Use nullable fields for genuinely missing signals, plus a reason/status field; do not replace missing probabilities or similarities with zero. Separate the following states:

- signal measured and valid;
- signal missing or failed;
- intentionally dummy-generated;
- candidate abstained (Tier 3).

Record numeric dtype, units/ranges, null policy, sort order, and tie behavior in the schema. Validate finite values and preserve source columns through every join.

## Data separation

The AD reference set is used for reference geometry/calibration. The evaluation-positive set is used only for final metric computation. Enforce and archive the agreed homology filter between C1/C2 training data and held-out evaluation positives; also prove reference/evaluation disjointness. No held-out labels may influence threshold fitting, ranking weights, score normalization, or model selection.
