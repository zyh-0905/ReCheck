# ReCheck — ICASSP-format research working draft (R16)

**This is a complete AI-generated research working draft, NOT a file certified for direct conference submission.**
The user reports that author evidence review is complete. This does not establish original author composition of the manuscript. Actual author names and affiliations remain placeholders. The applicable ICASSP 2027 LLM policy and remaining author tasks are recorded in `author_handoff/FINALIZATION_ZH.md`.

## Read and compile
- `main.tex`: complete English working draft with linked evidence, tables and figure.
- `author_manuscript.tex`: scaffold for the actual authors' original text, preserving reusable tables and citations.
- `authors.tex`: author placeholders; do not infer names from account handles.
- `references.tex`: numbered bibliography used for compilation; `references.bib` supplies editable bibliographic metadata.
- `figures/model_counts.pdf`: embedded-font vector figure; SVG and PNG are provided for editing/viewing.

With an existing TeX installation, run `python build.py` from this directory (or open `main.tex` in Overleaf). To compile the original-author scaffold use `python build.py author_manuscript.tex`. No model key or paid call is used. The source does not auto-download software. Both commands disable shell escape.

## Scientific scope
The paper is a retrospective empirical audit, not an agent-planning algorithm. It retains 64 full-progress/effect conflicts (62 calendar effects, two missing creations) within 576 saved records from six repeated templates. It does not claim a benchmark-wide error rate, a new model ranking, a causal judge failure mechanism, or an improvement in agent success. Setting/contact negative coverage and scripted temporal controls are distinct evidence sets.

## Template provenance and status
`spconf.sty` is an inherited transcription of official definitions, checked against the current Paper Kit's web-readable style. It is NOT a byte-identical downloaded official template archive. Its content area and column definitions were not altered to squeeze pages. Official template retrieval through container downloads failed; this is disclosed rather than hidden.
The working PDF has five US-Letter pages; all technical content ends by page four and page five contains references only. It has a 144-word abstract and five index terms. Body/table/figure-label base sizes are 10/9/9 pt; mathematical scripts follow normal TeX sizing. All PDF fonts are embedded. Local inspection is not an official submission-system acceptance.

## Author finalization
Author-composed prose, real names/affiliations/contact details, any required funding/ethics disclosures, and ORCID validation are still needed for an actual submission. Removing the working-draft marker or paraphrasing AI-generated text does not by itself satisfy the conference policy. Do not post or submit this package automatically.

## Source rules
Official submission policy: https://cmsworkshops.com/ICASSP2027/papers.php
Official Paper Kit: https://cmsworkshops.com/ICASSP2027/papers/paper_kit.php
Checked 2026-09-15. The paper does not assert public availability of our own artifacts at a repository which has not been updated.
