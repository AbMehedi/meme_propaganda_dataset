# CampNet 17-image experimental pilot report

This pilot is for learning and calibration. No synthetic check or model proposal is a human reference label.

## Selection and OCR

- 17/17 selected images opened and matched frozen SHA-256 checksums.
- Selection is the original 20 stable IDs minus three explicit `#excluded` OCR entries; no resampling.
- IDs, image dimensions, captions and source URLs were checked against the read-only frozen database.
- No duplicate selected IDs, missing images or unmatched corrected OCR records.
- One author-reviewed empty transcription; it is distinguished from missing OCR or extraction failure.
- 5 posts have no original caption; they are flagged without invented context.
- Original machine OCR and human-corrected text remain separate. Canonical text is not stripped or Unicode-normalized.
- OCR version: `author-corrected-sha256:26181b3325d8f5a3a1ed491768a938d65074d36f2ae6ebf6bba73b73b310dcdc`.
- Review author identity/time were not included in the source CSV and remain null, not guessed.
- Frozen database has zero `ocr_run` rows. The latest reviewed OCR is `ocr_corrected_20.csv`, not the database or Facebook alt text.
- Frozen database, manifest, source images and corrected OCR were not modified. Input checksums are in `validation.json`.

## Task building and evidence interface

The `pilot17` command produces an isolated manifest and images, blind Stage A imports, full-post manual imports, and a separate assisted project. IDs and OCR hashes match across conditions. Repeated imports through the setup utility refuse changed data and do not add duplicates. Use a new output directory when canonical text changes.

The interface uses supported Labels, RectangleLabels, Choices and per-region TextArea controls. Each highlight or rectangle has a technique and instance number. The same technique/number joins related text and visual evidence; separate numbers preserve repeated instances. Each region records its explanation, confidence, target where known, visual contribution and text sufficiency. Whole-image evidence uses an explicitly GLOBAL full-image rectangle with an explanation. Typography is distinct from non-textual imagery.

The exporter converts browser UTF-16 spans to Unicode code-point [start,end) offsets, validates exact quotes/checksums, converts rectangles to normalized coordinates, and checks contribution/evidence consistency. Empty core labels are distinct from unresolved decisions. Invalid records remain in the audit output. No output is automatically marked gold.

Limitations: Label Studio does not enforce cross-region instance consistency or the complete research schema in its Submit button. Run the export validator. The text/full-post order and Stage A lock require assignment control and a saved immutable export; creating separate projects alone does not enforce blindness. Native Community Edition is not an adjudication platform.

## Dry-run verification

- PASS: stage_a_manual: installed Label Studio XML validation passed
- PASS: manual: installed Label Studio XML validation passed
- PASS: assisted: installed Label Studio XML validation passed
- PASS: 17 actual manual imports; zero predictions
- PASS: Repeated import kept exactly 17 tasks
- PASS: Authenticated local image serving returned original checksum
- PASS: 8 synthetic manual cases saved and exported with intact evidence/Unicode offsets
- PASS: 17 blind Stage A tasks imported with no image or predictions
- PASS: Synthetic predictions imported, accepted/edited/rejected, patched and exported separately from human decisions; originals unchanged

These checks used the installed Label Studio 1.23.2 API and its real database/serializers/exporter in an isolated test runtime. The manual fixtures cover text-only, visual, combined, multiple labels, no technique, unreadable/uncertain, whole-image evidence and repeated instances. All fixture annotations are explicitly synthetic.

Browser UI was not automated; no screenshots are claimed. The following still need human verification: visual layout and font rendering, mouse highlight/box creation, image zoom, prediction display/copy/edit/reject using browser controls, Submit button interaction.

19 focused unit tests passed, with 0 failures and 0 errors. Checks cover wrong IDs, explicit selection count, OCR provenance, Bangla after emoji, invalid surrogate boundaries, stale text, invented/ambiguous quotes, invalid boxes, role conflicts, missing evidence, cancellation and model output validation. The runner transport test used mocked responses and confirmed that actual image bytes and exact OCR enter each request; it is not real inference.

## Experimental model run

Completion: **0/17**; blocked: 17; inference/validation failures: 0.

Blocker: CAMPNET_VLM_MODEL is unset; no vision-language model is configured. No inference requests sent.

Run audit: `pilot_17\preannotation\20261013T213905Z-4c040c`. The prompt includes the complete authoritative guideline and sends only the actual image, checked OCR and original caption. Sources, alt text, engagement and previous labels are not model inputs.

The runner checks advertised vision capability, validates quotes and records bounded retries. It does not accept model boxes as verified grounding. Visual proposals require human localization. Model confidence is not solicited or presented as correctness.

No raw model responses exist for blocked records because no inference requests were made. Their normalized status records are not negative predictions.

### Distributions

Label, modality and visual-contribution distributions are **unavailable**. Zero completed proposals does not mean zero techniques in the images. Evidence validity and model uncertainty are not assessed for blocked images.

### Per-image review

| Image ID | Proposed labels | Evidence summary | Uncertainty | Review status |
|---|---|---|---|---|
| 138766cdb6d5541fa0f13e958c9146ed | Not generated | No model evidence available | Not assessed | BLOCKED — model access needed |
| a3da98879a3d23f6645b4e349fe76b26 | Not generated | No model evidence available | Not assessed | BLOCKED — model access needed |
| 5620b386af75f3487349c5487a6a5500 | Not generated | No model evidence available | Not assessed | BLOCKED — model access needed |
| 868b5679de36fb9df85c7898ece298d5 | Not generated | No model evidence available | Not assessed | BLOCKED — model access needed |
| da1790a39c713c2f45f6141d1a6d4a7a | Not generated | No model evidence available | Not assessed | BLOCKED — model access needed |
| 4ca43d0fe5ff9b12941105ae3378e26e | Not generated | No model evidence available | Not assessed | BLOCKED — model access needed |
| 5c5cf50f8585bcc06f0ec419b798bd7a | Not generated | No model evidence available | Not assessed | BLOCKED — model access needed |
| 05e4d38af26351203819b6c79a2d6b7d | Not generated | No model evidence available | Not assessed | BLOCKED — model access needed |
| d48b60995b080dd77a582b99ab9871c2 | Not generated | No model evidence available | Not assessed | BLOCKED — model access needed |
| dfc319a63f4acaaa13939840ae35a115 | Not generated | No model evidence available | Not assessed | BLOCKED — model access needed |
| 755e9548155cd8048eefb249a2fca47f | Not generated | No model evidence available | Not assessed | BLOCKED — model access needed |
| a298de2014f664a4e2993ccb3d5be470 | Not generated | No model evidence available | Not assessed | BLOCKED — model access needed |
| 68705bbde7681de67744e5aaf04a24b3 | Not generated | No model evidence available | Not assessed | BLOCKED — model access needed |
| 595c546ce64096fb7b02a6a638eda3ea | Not generated | No model evidence available | Not assessed | BLOCKED — model access needed |
| 35ef2aad041f1482330758e0a16aa9e2 | Not generated | No model evidence available | Not assessed | BLOCKED — model access needed |
| 4382b143978c36408cdfb966b4be9a50 | Not generated | No model evidence available | Not assessed | BLOCKED — model access needed |
| ba069534340281fe3ea3c7677c6ed715 | Not generated | No model evidence available | Not assessed | BLOCKED — model access needed |

## Interpretation and next annotation round

Annotators should work independently first, with predictions and other annotators’ decisions hidden. Save Stage A before revealing the image. A second independent reviewer should submit before discussion. Then compare disagreements using the guideline and record an adjudication reason or unresolved status. Keep original human decisions unchanged.

Treat assisted annotation as a separate experimental condition after the independent calibration round. Seeing predictions can anchor decisions; reusing these same 17 images creates familiarity effects. Counterbalance assignments or use separate matched images for a comparison. Same-person text-before-image stages are not statistically independent.

Seventeen deliberately selected posts are too small to establish taxonomy coverage, natural class prevalence, or performance. Do not force labels to populate missing classes. Keep practice examples out of a held-out evaluation set. No accuracy, precision, recall or F1 is reported because independent reference labels are absent.

Operational note: C: ran out of space during initial testing. The completed tests use temporary files under E:/.pilot-runtime. No unrelated user files were deleted. Browser/app activity may still need system-drive space.

The live pilot server was verified to return HTTP 200 at http://localhost:8081. Project installation in that live workspace is pending creation of a pilot user account. All import/save/export checks above were performed in the separate synthetic-test database. After signup, run `python -m campnet_pilot.labelstudio setup` to install the three real projects.

Rebuild, server, setup, inference and export commands: `docs/PILOT_17_WORKFLOW.md`. Export contract: `docs/PILOT_17_EXPORT_SCHEMA.md`.
