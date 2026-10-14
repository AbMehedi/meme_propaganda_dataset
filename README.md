# CampNet Label Studio starter

Post-freeze annotation tooling, based on the latest 17-image pilot and annotator UI.
The bundled pilot includes checked OCR, three explicit exclusions, 17 original
images, task imports, annotation configurations, and provenance. Model suggestions
are experimental, not gold labels. The full frozen dataset is not part of this tree.

## Install and start (Windows PowerShell)

Use Python 3.11. Run from this checkout:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\start_pilot_label_studio.ps1
```

Open http://localhost:8081 and create your local account. In a second terminal:

```powershell
.\.venv\Scripts\python.exe -m campnet_pilot.labelstudio setup
```

This loads the three bundled projects and grants access to their pilot images.
The launcher stores accounts and annotations in ignored `.pilot-runtime/label-studio`.
No rebuild or frozen database is needed to annotate the bundled pilot. Export and
back up your runtime before changing pilot revisions. Do not sync local image
storage: the JSON tasks already reference each image.

See [the pilot workflow](docs/PILOT_17_WORKFLOW.md) for independent Stage A/B
annotation, export, model assistance and revision handling, and the
[annotation guideline](docs/CampNet_Annotation_Guideline_v1.md) for evidence rules.
The older [20-image instructions](README_CampNet_Label_Studio_Starter.md) describe
historical work; their full-data prerequisites must be restored separately.

## Frozen data and OCR

The latest author-corrected `ocr_corrected_20.csv`, draft, raw polygon records and
review page are retained. Do not normalize or overwrite corrected text after
annotation: Unicode offsets and text hashes must remain stable.

To rebuild or regenerate OCR, copy your preserved frozen `data/manifest.csv`,
`data/camp_rg.db` and `data/images/` into this checkout's ignored `data/` directory.
Keep the originals unchanged. Then run:

```powershell
.\.venv\Scripts\python.exe build_label_studio_tasks.py pilot17
```

The builder reads the database in read-only mode and checks image hashes, dimensions,
selection identities and OCR. Changed inputs require a new output directory.
Optional OCR regeneration uses a separate environment with `requirements-ocr.txt`
and `prepare_ocr_review.py`; it regenerates the machine draft, not human corrections.
The historical OCR review HTML needs those 20 source images under `data/images/`.
Model settings in `.env.example` are examples; export environment variables explicitly.

## Validation

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m campnet_pilot.dry_run
```

Unit tests check the pilot, exact OCR, hashes, Unicode spans and export rules.
Two full-freeze tests skip when local source data is absent. The API dry run creates
a separate disposable runtime, validates Label Studio XML, checks real image serving,
and exercises synthetic save/export and assisted review. It does not create research
annotations. Browser layout and mouse interactions still require manual inspection.

See [cleanup provenance](docs/CLEANUP_REPORT.md) for branch scope and preservation.
