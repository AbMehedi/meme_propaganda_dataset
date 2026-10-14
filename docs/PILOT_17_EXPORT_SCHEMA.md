# CampNet evidence export contract — campnet-evidence-1

The native Label Studio JSON is the lossless audit source. Keep it alongside the
normalized JSON produced by `python -m campnet_pilot.export`. Normalized decisions
are not adjudicated gold; `is_gold` always remains false in this tool.

## Identity and provenance

| Field | Meaning |
|---|---|
| `schema_version` | `campnet-evidence-1` |
| `task_id`, `image_id`, `post_id` | Stable IDs from the pilot manifest; native LS integer task IDs are local only |
| `stage` | `A` text-only or `B` full-post |
| `origin` | `human` or `model_prediction`; never merged |
| `annotation_id`, `reviewer` | Native ID and `completed_by` metadata; synthetic dry-run users are not research annotators |
| `model_version`, `parent_prediction` | Proposal version and review link when provided by LS |
| `model_review_action` | `ACCEPTED`, `EDITED`, `REJECTED`, `NOT_AVAILABLE`, or null outside assisted review |
| `ocr_version`, `ocr_sha256`, `caption_sha256`, `image_sha256` | Exact content/version checks; compare against pinned pilot manifest |
| `raw_result` | Unmodified native result entries, retained for audit |

The isolated `manifest.json` joins IDs to `source_key`, `post_url`, timestamp,
split group, image paths/dimensions, original machine OCR, author-corrected OCR,
provenance and missing-data flags. Source metadata is not part of the annotator view.

## Decision

`status` is `COMPLETE`, `UNRESOLVED`, or `EXCLUDE`. `has_core_technique` is true or
false only for a complete decision; otherwise null. `techniques` contains T01–T07
only. `No Propaganda Technique` is an explicitly confirmed empty set, not a label.
It is incompatible with positive techniques or unresolved/excluded status.

`watchlist` contains W01/W02/W03/other_candidate separately. `out_of_taxonomy` is
true when such a candidate is recorded. Its evidence belongs in `post_note` for
this pilot and is not silently promoted into core technique instances.
`review_flags` and `post_note` preserve missing-context/readability/adjudication
information. `cancelled` marks skipped records; they cannot become complete data.

`valid` means software integrity checks passed, not that the annotation is correct.
`validation_errors` lists unresolved problems. No automatic repair of conflicting
contribution judgments or stale offsets occurs. Invalid records remain in output.

## Technique instances and evidence association

Each `instances[]` entry has:

- `instance_id`, e.g. `T03-1`; generated from the selected technique and user-entered number.
- `technique_id` and the exact guideline `technique_name`.
- `visual_contribution`: REQUIRED / REINFORCING / NOT_USED / UNRESOLVED.
- `text_sufficient`: true / false / null.
- `evidence_channels`: CAPTION / EMBEDDED_TEXT / NON_TEXT_VISUAL / TYPOGRAPHY_LAYOUT.
- `target`: visible/named target or null, never inferred from facial identity.
- `confidence`: human aid 1–3; null for unreviewed model suggestions.
- `evidence[]`: all linked text and visual evidence records.

Within one native result, the LS region ID links a span/box to its per-region
controls. Across regions, `(technique_id, instance_number)` links evidence to the
same instance. Multiple boxes and disjoint/overlapping spans are allowed. Repeated
instances of the same technique use different numbers. For a region supporting two
techniques, create separate labeled region records over the same area and explain
each mechanism. This implementation does not silently merge them by geometry.

Every region has an explanation (`reason`). Combined evidence uses the same
instance number and explains the word/picture relationship in the region reason.
Regions linked to one instance must agree on visual contribution/text sufficiency.
The first region's human confidence/target are the instance summary; all original
per-region entries are retained in `raw_result`.

Every normalized evidence record also includes its own `target`, `confidence`,
`visual_contribution`, and `text_sufficient`. These preserve each mark's answers
even when linked marks differ in target wording or confidence. Instance summaries
continue to use the first valid mark's target and confidence.

`evidence_region_count`, `exported_region_count`, and `unexported_region_ids` make
incomplete marks explicit. A malformed mark cannot create an empty instance.
Invalid raw fields remain in `raw_result`; no incomplete record becomes gold.
The validator checks every known UI control's name, type, target, allowed options,
and region association, and lists all missing required fields for a mark together.
These are export checks; Label Studio's Submit checks required fields but does not
enforce all cross-field consistency rules.

## Text evidence

```json
{
  "region_id": "T01-1-ocr",
  "type": "TEXT",
  "channel": "EMBEDDED_TEXT",
  "start": 5,
  "end": 10,
  "quote": "ঘৃণ্য",
  "text_sha256": "checksum-of-the-entire-displayed-channel",
  "text_version": "author-corrected-sha256:source-file-checksum",
  "offset_unit": "unicode_code_point",
  "reason": "The word gives an emotionally negative judgment."
}
```

This example illustrates the schema, not a selected-image annotation. Offsets
must be computed from the actual channel. The exporter validates zero-based,
half-open `[start,end)` Unicode code-point indices and `text[start:end] == quote`.
Native LS browser offsets are UTF-16; conversion rejects an offset through a
surrogate pair. Emoji, Bangla combining marks and newlines stay unchanged. Do not
use byte or grapheme counts. Canonical OCR must be re-frozen and spans reviewed
if the text changes; a matching quote in a different revision is insufficient.

## Visual evidence

`type=VISUAL`, `kind`/`channel` NON_TEXT_VISUAL or TYPOGRAPHY_LAYOUT, `scope` LOCAL
or GLOBAL, and `box=[x_min,y_min,x_max,y_max]` normalized to `[0,1]` on the frozen,
orientation-verified original image. Native LS percent rectangles are converted;
empty/out-of-bounds/rotated boxes and mismatched image dimensions are rejected.
GLOBAL requires a full-image rectangle and a reason explaining global composition.

`grounding_verified=true` means a human-origin geometry record passed software
validation, not that an adjudicator verified its persuasive interpretation.
`supervision_available` is false for unresolved visual contribution or model
geometry. Model visual descriptions in preannotation logs have `regions=null`,
`grounding_verified=false`, and `supervision_available=false`; they are not boxes.
They remain suggestions in the assisted task until a human marks real regions.

## Consistency checks and scope

NOT_USED requires text evidence, true text sufficiency and no visual evidence.
REQUIRED requires visual evidence and false text sufficiency. REINFORCING requires
both kinds of evidence and true text sufficiency. Contradictions require review.
T01/T06 require linguistic evidence; T07 requires a non-textual visual mechanism.
The software cannot prove that a persuasive interpretation is correct.

The export keeps both native predictions and human decisions. Human records failing
validation cause exit code 2. Incomplete model predictions remain audit records and
never block saving the independent human export merely because the model did not
provide a human confidence rating or a grounded box.
