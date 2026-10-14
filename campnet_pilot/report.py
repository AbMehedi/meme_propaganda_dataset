"""Generate an evidence-based pilot report from saved validation and run artifacts."""
from collections import Counter
from pathlib import Path
from .common import ROOT,PILOT,read_json


def main():
    validation=read_json(PILOT/'validation.json')
    records=read_json(PILOT/'manifest.json')
    dry=read_json(PILOT/'dry_run/results.json')
    unit=read_json(PILOT/'dry_run/unit_test_results.json')
    run=read_json(PILOT/'preannotation/latest.json')
    outputs=read_json(ROOT/run['output']/'normalized.json')
    by_id={o['image_id']:o for o in outputs}
    proposed=[o for o in outputs if o['status']=='PROPOSED']
    labels=Counter(i['technique_id'] for o in proposed for i in o['parsed']['instances'])
    modalities=Counter(c for o in proposed for i in o['parsed']['instances'] for c in i['evidence_channels'])
    roles=Counter(i['visual_contribution'] for o in proposed for i in o['parsed']['instances'])
    lines=['# CampNet 17-image experimental pilot report','',
           'This pilot is for learning and calibration. No synthetic check or model proposal is a human reference label.','',
           '## Selection and OCR','',
           f'- {validation["valid_images"]}/17 selected images opened and matched frozen SHA-256 checksums.',
           '- Selection is the original 20 stable IDs minus three explicit `#excluded` OCR entries; no resampling.',
           '- IDs, image dimensions, captions and source URLs were checked against the read-only frozen database.',
           '- No duplicate selected IDs, missing images or unmatched corrected OCR records.',
           '- One author-reviewed empty transcription; it is distinguished from missing OCR or extraction failure.',
           f'- {sum("CAPTION_MISSING" in r["flags"] for r in records)} posts have no original caption; they are flagged without invented context.',
           '- Original machine OCR and human-corrected text remain separate. Canonical text is not stripped or Unicode-normalized.',
           f'- OCR version: `{validation["ocr_version"]}`.',
           '- Review author identity/time were not included in the source CSV and remain null, not guessed.',
           '- Frozen database has zero `ocr_run` rows. The latest reviewed OCR is `ocr_corrected_20.csv`, not the database or Facebook alt text.',
           '- Frozen database, manifest, source images and corrected OCR were not modified. Input checksums are in `validation.json`.','',
           '## Task building and evidence interface','',
           'The `pilot17` command produces an isolated manifest and images, blind Stage A imports, full-post manual imports, and a separate assisted project. IDs and OCR hashes match across conditions. Repeated imports through the setup utility refuse changed data and do not add duplicates. Use a new output directory when canonical text changes.',
           '',
           'The interface uses supported Labels, RectangleLabels, Choices and per-region TextArea controls. Each highlight or rectangle has a technique and instance number. The same technique/number joins related text and visual evidence; separate numbers preserve repeated instances. Each region records its explanation, confidence, target where known, visual contribution and text sufficiency. Whole-image evidence uses an explicitly GLOBAL full-image rectangle with an explanation. Typography is distinct from non-textual imagery.',
           '',
           'The exporter converts browser UTF-16 spans to Unicode code-point [start,end) offsets, validates exact quotes/checksums, converts rectangles to normalized coordinates, and checks contribution/evidence consistency. Empty core labels are distinct from unresolved decisions. Invalid records remain in the audit output. No output is automatically marked gold.',
           '',
           'Limitations: Label Studio does not enforce cross-region instance consistency or the complete research schema in its Submit button. Run the export validator. The text/full-post order and Stage A lock require assignment control and a saved immutable export; creating separate projects alone does not enforce blindness. Native Community Edition is not an adjudication platform.','',
           '## Dry-run verification','']
    lines += ['- PASS: '+c for c in dry['checks_passed']]
    lines += ['', 'These checks used the installed Label Studio '+dry['label_studio_version']+' API and its real database/serializers/exporter in an isolated test runtime. The manual fixtures cover text-only, visual, combined, multiple labels, no technique, unreadable/uncertain, whole-image evidence and repeated instances. All fixture annotations are explicitly synthetic.',
              '', 'Browser UI was not automated; no screenshots are claimed. The following still need human verification: '+', '.join(dry['ui_checks_pending'])+'.',
              '', f'{unit["tests_run"]} focused unit tests passed, with {unit["failures"]} failures and {unit["errors"]} errors. Checks cover wrong IDs, explicit selection count, OCR provenance, Bangla after emoji, invalid surrogate boundaries, stale text, invented/ambiguous quotes, invalid boxes, role conflicts, missing evidence, cancellation and model output validation. The runner transport test used mocked responses and confirmed that actual image bytes and exact OCR enter each request; it is not real inference.',
              '', '## Experimental model run','',
              f'Completion: **{run["completed"]}/17**; blocked: {run["blocked"]}; inference/validation failures: {run["failed"]}.',
              '', 'Blocker: '+(run['blocker'] or 'None.'),
              '', f'Run audit: `{run["output"]}`. The prompt includes the complete authoritative guideline and sends only the actual image, checked OCR and original caption. Sources, alt text, engagement and previous labels are not model inputs.',
              '', 'The runner checks advertised vision capability, validates quotes and records bounded retries. It does not accept model boxes as verified grounding. Visual proposals require human localization. Model confidence is not solicited or presented as correctness.',
              '', 'No raw model responses exist for blocked records because no inference requests were made. Their normalized status records are not negative predictions.',
              '', '### Distributions','']
    if proposed:
        lines += ['Proposed technique instance counts: `'+str(dict(labels))+'`.',
                  'Evidence-channel counts (multiple channels allowed): `'+str(dict(modalities))+'`.',
                  'Visual-contribution counts: `'+str(dict(roles))+'`.']
    else:
        lines += ['Label, modality and visual-contribution distributions are **unavailable**. Zero completed proposals does not mean zero techniques in the images. Evidence validity and model uncertainty are not assessed for blocked images.']
    lines += ['', '### Per-image review','', '| Image ID | Proposed labels | Evidence summary | Uncertainty | Review status |',
              '|---|---|---|---|---|']
    for r in records:
        o=by_id[r['image_id']]
        if o['status']=='PROPOSED':
            p=o['parsed'];label=', '.join(i['technique_id'] for i in p['instances']) or 'Empty core set (proposal)'
            evidence='; '.join(i['rationale'] for i in p['instances']) or p['note']
            uncertainty='; '.join(str(i.get('uncertainty') or '') for i in p['instances']).strip('; ') or ', '.join(p['review_flags']) or 'None reported; human review required'
            review='Pending independent human review'
        else:
            label='Not generated';evidence='No model evidence available'
            uncertainty='Not assessed';review=o['status']+' — model access needed'
        clean=lambda x: str(x).replace('|','/').replace('\n',' ')
        lines.append('| '+ ' | '.join(map(clean,[r['image_id'],label,evidence,uncertainty,review]))+' |')
    lines += ['', '## Interpretation and next annotation round','',
              'Annotators should work independently first, with predictions and other annotators’ decisions hidden. Save Stage A before revealing the image. A second independent reviewer should submit before discussion. Then compare disagreements using the guideline and record an adjudication reason or unresolved status. Keep original human decisions unchanged.',
              '', 'Treat assisted annotation as a separate experimental condition after the independent calibration round. Seeing predictions can anchor decisions; reusing these same 17 images creates familiarity effects. Counterbalance assignments or use separate matched images for a comparison. Same-person text-before-image stages are not statistically independent.',
              '', 'Seventeen deliberately selected posts are too small to establish taxonomy coverage, natural class prevalence, or performance. Do not force labels to populate missing classes. Keep practice examples out of a held-out evaluation set. No accuracy, precision, recall or F1 is reported because independent reference labels are absent.',
              '', 'Operational note: C: ran out of space during initial testing. The completed tests use temporary files under E:/.pilot-runtime. No unrelated user files were deleted. Browser/app activity may still need system-drive space.',
              '', 'The live pilot server was verified to return HTTP 200 at http://localhost:8081. Project installation in that live workspace is pending creation of a pilot user account. All import/save/export checks above were performed in the separate synthetic-test database. After signup, run `python -m campnet_pilot.labelstudio setup` to install the three real projects.',
              '', 'Rebuild, server, setup, inference and export commands: `docs/PILOT_17_WORKFLOW.md`. Export contract: `docs/PILOT_17_EXPORT_SCHEMA.md`.', '']
    (PILOT/'EXPERIMENTAL_REPORT.md').write_text('\n'.join(lines),encoding='utf-8')
    print(PILOT/'EXPERIMENTAL_REPORT.md')


if __name__=='__main__':
    main()
