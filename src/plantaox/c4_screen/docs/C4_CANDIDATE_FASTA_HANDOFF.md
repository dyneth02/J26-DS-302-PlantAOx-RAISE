# Candidate FASTA handoff message (draft; not sent)

**To:** C1 and C2 component owners  
**Subject:** C4 candidate FASTA for sequence-key scoring

Hi, I have prepared the Component 4 PlantAOP-Screen candidate FASTA for downstream scoring. It contains 152,259 globally unique candidate sequences from the four reviewed plant proteomes, with sequence IDs generated from stable peptide hashes.

- File: `data/interim/c4_screen/candidates.fasta`
- SHA-256: `bcf23050ebdcba94940043ad4b959d3659f9a7bc2c6734de401453479e96b3c7`
- Companion provenance and descriptor table: `data/interim/c4_screen/candidates.parquet`
- Interface contract: [`C4_Interface_Spec_v0.1_PROVISIONAL.md`](C4_Interface_Spec_v0.1_PROVISIONAL.md) (sequence string is the C4-proposed join key; schema remains provisional where marked)

Please return candidate signal files with one row per sequence, preserving the sequence string and a clear `source` label. The current C4 signal integration is mock-only; this message is a draft and has not been sent.
