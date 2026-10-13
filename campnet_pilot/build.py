"""Derive the fixed selection from explicit exclusions, not a new sample."""
import shutil
import sqlite3
from collections import Counter
from pathlib import Path
from urllib.parse import quote

from PIL import Image

from .common import ROOT, PILOT, indexed, read_csv, read_json, sha, write_json


def build_pilot(manifest=ROOT / 'data/manifest.csv', selection=ROOT / 'pilot_20_audit.csv',
                corrected=ROOT / 'ocr_corrected_20.csv', draft=ROOT / 'ocr_draft_20.csv',
                output=PILOT, images_root=ROOT):
    output, images_root = Path(output).resolve(), Path(images_root).resolve()
    # Isolated output only: never let an output overlap frozen images or inputs.
    if output == ROOT or output.is_relative_to(ROOT / 'data') or not output.is_relative_to(ROOT):
        raise ValueError('Pilot output must be a separate directory inside this repository')
    report = {'schema_version': 'campnet-pilot-1', 'errors': [], 'warnings': [],
              'excluded': [], 'empty_ocr': [], 'selected_count': 0}
    errors = report['errors']
    try:
        all_rows = read_csv(manifest)
        rows, choices = indexed(all_rows), indexed(read_csv(selection))
        corrections, drafts = indexed(read_csv(corrected)), indexed(read_csv(draft))
        if set(corrections) != set(choices):
            raise ValueError('Corrected OCR/selection IDs differ; missing=' + str(sorted(set(choices)-set(corrections)))
                             + '; extra=' + str(sorted(set(corrections)-set(choices))))
        included = []
        for key, choice in choices.items():
            if corrections[key]['ocr_corrected'].strip() == '#excluded':
                report['excluded'].append({'image_id': key, 'reason': 'Explicit #excluded in corrected OCR'})
            else:
                included.append(choice)
        report['selected_count'] = len(included)
        if len(included) != 17:
            raise ValueError(f'Expected exactly 17 selected IDs, found {len(included)}; no resampling performed')
        post_counts = Counter(r['post_id'] for r in all_rows)
        ocr_version = 'author-corrected-sha256:' + sha(Path(corrected).read_bytes())
        input_hashes = {str(Path(p).resolve().relative_to(ROOT)): sha(Path(p).read_bytes())
                        for p in [manifest, selection, corrected, draft, ROOT / 'data/camp_rg.db',
                                  ROOT / 'docs/CampNet_Annotation_Guideline_v1.md']}
        records = []
        for choice in included:
            key = choice['image_id']
            try:
                row = rows[key]
                if row['post_id'] != choice['post_id'] or row['sha256'] != choice['sha256']:
                    raise ValueError('Selection identity/hash differs from frozen manifest')
                if post_counts[row['post_id']] != 1:
                    raise ValueError('Not a single-image post')
                rel = Path(row['relative_path'])
                source = (images_root / rel).resolve()
                if rel.is_absolute() or not source.is_relative_to(images_root):
                    raise ValueError('Unsafe image path')
                if sha(source.read_bytes()) != row['sha256']:
                    raise ValueError('Image checksum differs from freeze')
                with Image.open(source) as im:
                    im.verify()
                with Image.open(source) as im:
                    im.load()
                    if im.getexif().get(274, 1) != 1:
                        raise ValueError('Image requires an explicit orientation-corrected derivative')
                    size = list(im.size)
                if size != [int(row['width']), int(row['height'])]:
                    raise ValueError('Image dimensions differ from freeze')
                if key not in drafts:
                    raise ValueError('Original OCR record missing')
                text = corrections[key]['ocr_corrected']  # Do not strip or normalize canonical text.
                status = 'AUTHOR_VERIFIED' if text.strip() else 'AUTHOR_VERIFIED_EMPTY'
                if not text.strip():
                    report['empty_ocr'].append({'image_id': key, 'status': status,
                        'basis': 'Review CSV permits empty only after image inspection; not machine OCR failure'})
                flags = [] if row['caption_clean'].strip() else ['CAPTION_MISSING']
                if not text.strip():
                    flags.append('REVIEWED_EMPTY_OCR')
                records.append({
                    'task_id': 'campnet17-' + key, 'image_id': key, 'post_id': row['post_id'],
                    'pilot_order': int(choice['pilot_order']), 'source_key': row['source_key'],
                    'post_url': row['post_url'], 'timestamp_utc': row['timestamp_utc'],
                    'split_group': row['split_group'], 'source_relative_path': rel.as_posix(),
                    'image_path': 'images/' + source.name, 'image_sha256': row['sha256'],
                    'width': size[0], 'height': size[1], 'caption': row['caption_clean'],
                    'caption_sha256': sha(row['caption_clean']), 'ocr': text,
                    'ocr_sha256': sha(text), 'ocr_original': drafts[key]['ocr_draft'],
                    'ocr_version': ocr_version, 'ocr_status': status, 'flags': flags,
                    'ocr_provenance': {'corrected_file': str(Path(corrected).relative_to(ROOT)),
                                       'original_file': str(Path(draft).relative_to(ROOT)),
                                       'reviewer_identity': None, 'review_timestamp': None},
                })
            except (KeyError, ValueError, OSError) as exc:
                errors.append(f'{key}: {exc}')
        if errors:
            raise ValueError('Image/OCR validation failed')
        # Read-only DB connection observes WAL; hash alone is not a freeze guarantee.
        db = ROOT / 'data/camp_rg.db'
        with sqlite3.connect(db.as_uri() + '?mode=ro', uri=True) as conn:
            tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")]
            report['database_tables'] = tables
            report['database_counts'] = {t: conn.execute('SELECT COUNT(*) FROM "' + t.replace('"','""') + '"').fetchone()[0]
                                         for t in tables if not t.startswith('sqlite_')}
            for record in records:
                actual=conn.execute('SELECT post_id, sha256, width, height FROM image WHERE image_id=?',
                                    (record['image_id'],)).fetchone()
                expected=(record['post_id'],record['image_sha256'],record['width'],record['height'])
                if actual!=expected:
                    raise ValueError('Frozen DB/manifest image mismatch: '+record['image_id'])
                post=conn.execute('SELECT caption_clean,post_url FROM post WHERE post_id=?',
                                  (record['post_id'],)).fetchone()
                if post!=(record['caption'],record['post_url']):
                    raise ValueError('Frozen DB/manifest caption or source mismatch: '+record['image_id'])
            report['database_records_matched']=len(records)
        fingerprint = sha(str(sorted(input_hashes.items())))
        existing = output / 'validation.json'
        if existing.exists() and read_json(existing).get('input_fingerprint') not in (None, fingerprint):
            raise ValueError('Inputs changed: choose a NEW --output-dir to protect existing text spans/predictions')
        expected = {r['image_path'].split('/')[-1] for r in records}
        if (output / 'images').exists():
            extras = {p.name for p in (output/'images').iterdir()} - expected
            if extras:
                raise ValueError('Unexpected files in isolated image directory: ' + str(sorted(extras)))
        (output / 'images').mkdir(parents=True, exist_ok=True)
        manual, text_only = [], []
        for r in records:
            shutil.copyfile(images_root / r['source_relative_path'], output / r['image_path'])
            image_url = '/data/local-files/?d=' + quote((output / r['image_path']).relative_to(ROOT).as_posix(), safe='/')
            # Audit-only source metadata stays in the manifest, never the labeling view.
            data = {k: r[k] for k in ('task_id','image_id','post_id','ocr','ocr_original','caption',
                                      'ocr_sha256','caption_sha256','ocr_version','ocr_status','flags',
                                      'ocr_provenance','image_sha256','width','height')}
            data['item_id'] = r['image_id']
            data['caption_notice'] = '' if r['caption'].strip() else 'No original caption is available.'
            data['ocr_notice'] = '' if r['ocr'].strip() else 'The author reviewed this image and left its transcription empty.'
            manual.append({'data': {**data, 'image': image_url, 'stage': 'B', 'annotation_mode': 'manual'}})
            text_only.append({'data': {**data, 'stage': 'A', 'annotation_mode': 'manual'}})
        write_json(output / 'manifest.json', records)
        write_json(output / 'selection.json', {'selected_ids': [r['image_id'] for r in records], 'excluded': report['excluded']})
        write_json(output / 'imports/manual.json', manual)
        write_json(output / 'imports/stage_a_manual.json', text_only)
        assisted_path = output / 'imports/assisted.json'
        if not assisted_path.exists():
            write_json(assisted_path, [{'data': {**t['data'], 'annotation_mode': 'assisted',
                       'model_notice': 'No model suggestions are available yet.'}, 'predictions': []} for t in manual])
        report.update(input_hashes=input_hashes, input_fingerprint=fingerprint,
                      ocr_version=ocr_version, valid_images=len(records), duplicate_ids=[], missing_images=[],
                      unmatched_ocr=[], frozen_database_written=False)
        write_json(output / 'validation.json', report)
        from .config import write_configs
        write_configs(output / 'config')
        print(f'Validated {len(records)} images; {len(report["excluded"])} explicit exclusions; {len(report["empty_ocr"])} reviewed empty OCR.')
        return report
    except (ValueError, OSError, KeyError, sqlite3.Error) as exc:
        errors.append(str(exc))
        write_json(output.parent / (output.name + '_build_failure.json'), report)
        raise ValueError('; '.join(errors)) from exc
