# CampNet 17-image pilot

The current workflow uses the author's latest `ocr_corrected_20.csv`. Three
`#excluded` records are explicitly excluded, leaving the fixed 17 selected images.
The authoritative rules are in [CampNet Annotation Guideline v1](CampNet_Annotation_Guideline_v1.md),
with the short training codebook at the repository root. No taxonomy was replaced.

Run the following commands in PowerShell from the repository root. The installed
environment used for verification is Python 3.11.9, Label Studio 1.23.2, Label Studio
SDK 2.1.2, Pillow 12.3.0 and requests 2.34.2. Browser automation was unavailable.

## Rebuild the pilot

```powershell
.\.venv\Scripts\python.exe .\build_label_studio_tasks.py pilot17
```

Outputs live in `pilot_17/`: exactly 17 images in `images/`, 17 records in
`manifest.json`, the explicit selection/exclusions, validation hashes, configs,
and three imports:

- `imports/stage_a_manual.json`: blind text and caption; no image or prediction.
- `imports/manual.json`: full post; no model predictions.
- `imports/assisted.json`: the same 17 images/OCR; predictions only when inference succeeds.

The manifest holds source references and original/corrected OCR separately.
Publisher metadata and alt text are not shown by the labeling configuration.
An empty reviewed transcription is marked `AUTHOR_VERIFIED_EMPTY`; a missing OCR
record is an error. Whitespace and Unicode in canonical text are preserved.

The corrected CSV has no reviewer identity or timestamp, so those provenance fields
are null. A content hash identifies the exact OCR revision. A changed input hash
requires a new output directory, e.g. `pilot17 --output-dir pilot_17_revision2`,
so existing spans and predictions cannot silently attach to a new text version.
The other command-line tools accept the default pilot; pass `--pilot` to the model
runner and `--manifest` to the exporter for another revision. For project setup,
use `--pilot` as shown below. Keep each revision in its own Label Studio runtime.

The old `build`, `preview`, `select`, and `audit-ocr` commands remain for historical
work. They are not the recommended 17-image workflow. A verified legacy build now
respects explicit `#excluded` rows and preserves exact transcription whitespace.

## Launch and load Label Studio

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\start_pilot_label_studio.ps1
```

Open [the pilot server](http://localhost:8081). This uses a separate database under
`.pilot-runtime/label-studio`, not the frozen research database or previous Label
Studio workspace. Create a pilot account if the server asks you to sign up.
Then run:

```powershell
.\.venv\Scripts\python.exe -m campnet_pilot.labelstudio setup
```

This creates Stage A manual, Stage B manual, and experimental assisted projects
with the actual XML config and local-image storage permissions. It prints project
links. Repeating setup leaves the same 17 tasks per project. It refuses changed
import/config fingerprints; it never silently overwrites an annotation or prediction.
If project setup was interrupted, rerun it to import missing tasks.

For a new pilot revision, use:

```powershell
.\.venv\Scripts\python.exe -m campnet_pilot.labelstudio setup --pilot .\pilot_17_revision2 --runtime .\.pilot-runtime\revision2
```

Initialize and launch the matching Label Studio runtime before this command. The
default launcher targets the original pilot runtime; advanced users can pass
Label Studio's `--data-dir` explicitly for a separate revision.

If creating projects manually, paste `pilot_17/config/stage_a_manual.xml`,
`manual.xml`, or `assisted.xml` into the matching project. Import each JSON once.
Plain Label Studio UI imports do not deduplicate our stable IDs: use the setup
utility for repeatability. For image projects add Local Files source storage at
the absolute `pilot_17/images` path. Save the connection **without syncing**.
The document root is the repository root, with URLs like
`/data/local-files/?d=pilot_17/images/<image_id>.jpg`.

## Instructions for annotators

Choose a technique only when you can point to evidence in this post. Highlight the
words or mark the image area that supports your choice. Explain why it matches
the technique. A face, flag, or emotional picture needs a clear persuasive use.

1. Read the short codebook. Practice on its fictional teaching examples.
2. Complete Stage A first. Read only the original caption and checked image text.
   Select a technique's label and highlight the smallest useful words. Open the
   highlight's evidence fields and give it instance number `1` and a reason.
3. Save and export Stage A before assigning or opening Stage B. Keep that export
   as the locked first decision. Do not edit Stage A after seeing the image.
4. In Stage B, make a fresh decision. You may add or remove techniques. Zoom the
   image to inspect it. Draw the smallest useful box for localized picture evidence.
5. Give each evidence region a technique and instance number. For example, use
   `T03` and `1` on the words and both picture areas supporting the same attack.
   Use `T03` and `2` for a separate attack. Enter the same picture role/text
   sufficiency on linked regions. Explain how the evidence works together.
6. For meaningful whole-image composition, draw a full-image rectangle, choose
   `GLOBAL`, and explain why a smaller area cannot capture the mechanism. Select
   `TYPOGRAPHY_LAYOUT` for text appearance, not `NON_TEXT_VISUAL`.
7. Select the final core techniques. If none is supported after a complete review,
   select no core techniques, check `No Propaganda Technique`, set `COMPLETE`, and
   explain. Missing context or unreadable text should be `UNRESOLVED`, with flags
   and a reason. Out-of-scope posts use `EXCLUDE` with a reason.
8. A complete technique may still have `UNRESOLVED` picture contribution. Record
   that uncertainty; do not replace the resolved technique with an empty set.
9. Save/Submit. The coordinator exports and validates the records before discussion.

Picture roles retain the guideline's values: `REQUIRED`, `REINFORCING`, `NOT_USED`,
`UNRESOLVED`. Evidence channels are `CAPTION`, `EMBEDDED_TEXT`, `NON_TEXT_VISUAL`,
`TYPOGRAPHY_LAYOUT`. Annotator confidence 1–3 is an aid, not correctness probability.

Multiple highlights/boxes can support one instance. Repeated instances of the same
technique use different numbers. The exporter groups by technique plus instance
number and rejects contradictory fields. The UI cannot enforce all these rules
before Submit; the export validation is mandatory. Rectangles are supported;
polygons are not collected by this pilot interface.

Keep watchlist/out-of-taxonomy evidence in the post note with W01/W02/W03 or
`other_candidate`. These are not core labels. A core-empty watchlist post does
not mean it has no possible persuasive technique.

## Independent and assisted annotation

For calibration, both humans work independently with no model suggestions. Hide
other annotators' decisions. Community Edition project separation does not enforce
Stage A locking or assignment blindness: control access/work allocation and retain
the first exports. Do not distribute all project links to annotators at once.

Only use the assisted project for a separately identified experiment after the
independent first round. It clearly names the proposals as model-generated. Native
predictions are read-only; Label Studio copies them to a new human annotation for
editing. The human must confirm confidence, complete picture evidence, and record
`ACCEPTED`, `EDITED`, `REJECTED`, or `NOT_AVAILABLE`. Original proposals and human
decisions are exported separately. The validator never promotes either to gold.

Model visual descriptions are shown as suggestions; no boxes are invented. Humans
must draw the real regions, attach their technique/instance number, and explain
the persuasive use. Prediction records with missing spatial evidence remain
incomplete audit records, not region-supervision targets.

## Experimental vision run

No model/provider credentials or model name were configured at implementation time.
The recorded run is **0/17 completed, 17 blocked**, not 17 empty-label predictions.
No raw inference responses exist because no inference was sent.

The runner supports an existing Ollama REST endpoint and checks `/api/show` for
the `vision` capability before sending images. It does not download or choose a
model. Configure an installed vision model you are authorized to use:

```powershell
$env:CAMPNET_VLM_URL = 'http://localhost:11434'
$env:CAMPNET_VLM_MODEL = 'YOUR_INSTALLED_VISION_MODEL'
.\.venv\Scripts\python.exe -m campnet_pilot.preannotate --retries 2 --timeout 120
```

Use `CAMPNET_VLM_API_KEY` in the process environment if that endpoint needs bearer
authentication. Never paste credentials into code or command examples. Remote
endpoints require HTTPS. An optional repository `.env` needs `python-dotenv`
installed; process environment variables work without it.

The prompt is `prompts/campnet_preannotation_v1.md`, with the full current guideline
appended. It sends the actual image bytes, exact corrected OCR and original caption.
No stage-A proposals are inferred from an image-containing request. Logs in
`pilot_17/preannotation/<run-id>/` contain prompt/hash, requested and returned model
IDs, settings, timestamps, raw outputs, parsed evidence, validation failures and
bounded retries. Quotes must match the exact supplied text; ambiguous repeats are
unresolved. Model coordinates are not accepted as verified grounding.

On completion the runner updates the assisted import. An existing assisted project
is deliberately not rewritten: export it and create a fresh experiment project
for the new proposal run. The setup utility refuses a changed fingerprint.

## Export, validate and report

Use the project's actual numeric ID printed by setup (replace `2` below):

```powershell
.\.venv\Scripts\python.exe -m campnet_pilot.labelstudio export --project 2 --output .\pilot_17\exports\manual_native.json
.\.venv\Scripts\python.exe -m campnet_pilot.export .\pilot_17\exports\manual_native.json --output .\pilot_17\exports\manual_normalized.json
.\.venv\Scripts\python.exe -m campnet_pilot.report
```

The exporter returns exit code 2 for invalid human records and saves the errors
alongside each record. Missing human confidence/localization in a model prediction
does not make it a human annotation. See [the export contract](PILOT_17_EXPORT_SCHEMA.md).

Do not call the pilot gold until independent annotation and adjudication are
complete. Do not calculate accuracy/precision/recall/F1 without independent human
references. Predictive suggestions can anchor annotators; repeating the same images
also creates familiarity effects. Keep practice images out of held-out evaluation.

## Verification

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m campnet_pilot.dry_run
```

The integration check uses a new `.pilot-runtime/dry-run-*` database. It imports
real tasks, serves a verified image, saves eight synthetic manual cases and three
synthetic assisted accept/edit/reject cases, then exports and validates results.
It writes no research annotations. Reports/native exports are in
`pilot_17/dry_run/`. Its temporary files stay on the workspace drive because the
system drive ran out of space during initial verification.

The saved unit-test record reports 19 passing tests. One exercises the complete
17-item runner with mocked HTTP responses, including a malformed response and a
bounded retry. That is a software check, not actual model pre-annotation.

Browser interactions were not automated. Human checks still needed: fonts/layout,
mouse highlighting, drawing a box, zoom, prediction copying/editing and Submit.
No UI screenshots are provided as evidence of tests that did not happen.

Implementation references: [Label Studio predictions](https://labelstud.io/guide/predictions),
[per-region TextArea](https://labelstud.io/tags/textarea),
[choices](https://labelstud.io/tags/choices), [local storage](https://labelstud.io/guide/storage_local),
[Ollama vision requests](https://docs.ollama.com/capabilities/vision),
[Ollama chat API](https://docs.ollama.com/api/chat).
