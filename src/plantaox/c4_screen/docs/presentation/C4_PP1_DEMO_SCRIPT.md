# C4 PP1 Demo Script (5 minutes)

**Demo data notice:** The reference cloud and all three Function B signal sources are MOCK. State this aloud before showing any score or card. This demo is not biological evidence.

| Time | On-screen action | Talking point |
|---|---|---|
| 0:00–0:35 | Open `data/interim/c4_screen/c4_dashboard.html` in a browser; point to the permanent mock ribbon. | The prototype generates and prioritizes peptide candidates, but cloud and signals are synthetic placeholders. |
| 0:35–1:20 | Open Pipeline; compare four plants and funnel counts with `../planning/PP1_NUMBERS.md`. | Counts are measured from reviewed UniProt entries through sequential pepsin pH 1.3 then trypsin, length/composition filters, and exact dedup. |
| 1:20–2:20 | Open AD view; show one plant histogram and t1/t2 lines, tier fractions, and length bins. Toggle mean-centering sensitivity if available. | Distances and tiers are relative to the 500-row MOCK cloud. Sensitivity is labelled; baseline thresholds were not tuned. |
| 2:20–3:20 | Open evidence cards; select the highest-ranked soybean card `MAHQWV` and read its mock source chips and descriptors. | CS is a deterministic combination for pipeline demonstration. It is not a measured activity probability. |
| 3:20–4:10 | Open Abstained; show rice `AGMEEVDMDEEVRPEF` as Tier 3 / CS=0 and the injected-demo mark. | The injected high-probability case demonstrates that out-of-domain Tier 3 candidates are abstained. |
| 4:10–5:00 | Open About/limitations; finish on the roadmap and explain real cloud staging. | A 912-row provisional C2-derived sequence list is staged for Colab embedding; until validated, production remains MOCK. |

## Startup and fallback

From PowerShell at the repository root:

```powershell
$env:PYTHONPATH = (Resolve-Path .\src).Path
.\.venv\Scripts\python.exe -m plantaox.c4_screen.run all --reuse-inputs --signals dummy
Start-Process .\data\interim\c4_screen\c4_dashboard.html
```

The static HTML dashboard is the offline fallback and does not require an API server. If browser opening fails, use the slide tables in `../planning/PP1_NUMBERS.md`; do not present a screenshot or fabricated number as a live result. The modern frontend/backend is maintained separately and is outside this C4 freeze scope.
