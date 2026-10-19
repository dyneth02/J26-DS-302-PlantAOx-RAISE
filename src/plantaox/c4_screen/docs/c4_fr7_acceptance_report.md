# C4 FR7 Evidence Card Acceptance

**Status:** PASS for generated MOCK cards and abstention formatting.

- Output: `data/interim/c4_screen/cards.json`; top lists contain Tier 1/2; RED/Tier 3 candidates appear in abstained lists with CS=0.
- Cards preserve sequence, peptide ID, plant, parent provenance, descriptors, mock signal values/source, tier/d_AD, CS/rank, length-bin BCS and C4-provisional flag.
- Injected demonstration case is tagged in card/manifest output and remains a mock example.
- UI/dashboard provenance and mock disclosures: `data/interim/c4_screen/c4_dashboard.html`.
- This acceptance verifies schema/algorithm behavior only; mock card rankings are not biological evidence.
