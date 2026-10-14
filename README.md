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
New annotators should start with the [three-step quick start](docs/ANNOTATOR_QUICK_START.md).
The older [20-image instructions](README_CampNet_Label_Studio_Starter.md) describe
historical work; their full-data prerequisites must be restored separately.

## Update the forms in existing pilot projects

The source of all three pilot forms is `campnet_pilot/config.py`. Regenerate the
XML after editing it, then apply the compatible layout update:

```powershell
.\.venv\Scripts\python.exe -m campnet_pilot.config
.\.venv\Scripts\python.exe -m campnet_pilot.labelstudio update-ui --check
.\.venv\Scripts\python.exe -m campnet_pilot.labelstudio update-ui
```

The updater checks stored field identities and task data, backs up the runtime
database and old forms under `.pilot-runtime/ui-backups`, and updates registered
projects without replacing tasks, annotations, drafts, or predictions. Refresh the
browser after the update. Changed annotation entities require a separate migration;
this command only permits compatible form updates.

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

For the optional browser regression check, install `playwright` in the venv and
have Google Chrome installed, then run `python -m campnet_pilot.browser_check`
using that venv. It uses an isolated database and headless Chrome with synthetic
tasks. Screenshots and native export checks are saved in `.pilot-runtime/browser-check-*`.

See [cleanup provenance](docs/CLEANUP_REPORT.md) for branch scope and preservation.
