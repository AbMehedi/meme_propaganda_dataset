import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PILOT = ROOT / 'pilot_17'
TECHNIQUES = {
    'T01': 'Loaded Language', 'T02': 'Name Calling / Labeling',
    'T03': 'Smears', 'T04': 'Appeal to Fear / Prejudice',
    'T05': 'Exaggeration / Minimisation', 'T06': 'Slogans',
    'T07': 'Appeal to Strong Emotions',
}
CHANNELS = ('CAPTION', 'EMBEDDED_TEXT', 'NON_TEXT_VISUAL', 'TYPOGRAPHY_LAYOUT')
ROLES = ('REQUIRED', 'REINFORCING', 'NOT_USED', 'UNRESOLVED')


def sha(data):
    return hashlib.sha256(data if isinstance(data, bytes) else data.encode('utf-8')).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')


def read_csv(path):
    with Path(path).open(encoding='utf-8-sig', newline='') as f:
        rows = list(csv.DictReader(f))
    if any(None in r or any(v is None for v in r.values()) for r in rows):
        raise ValueError(f'Malformed CSV: {path}')
    return rows


def indexed(rows, field='image_id'):
    result = {}
    for row in rows:
        key = row[field]
        if not key or key in result:
            raise ValueError(f'Empty or duplicate {field}: {key}')
        result[key] = row
    return result


def technique(value):
    code = value.split(' — ', 1)[0]
    if code not in TECHNIQUES:
        raise ValueError(f'Unknown core technique: {value}')
    return code


def cp_to_utf16(text, offset):
    if type(offset) is not int or not 0 <= offset <= len(text):
        raise ValueError('Invalid code-point offset')
    return len(text[:offset].encode('utf-16-le')) // 2


def utf16_to_cp(text, offset):
    if type(offset) is not int or offset < 0:
        raise ValueError('Invalid UTF-16 offset')
    raw = text.encode('utf-16-le')
    if offset * 2 > len(raw):
        raise ValueError('UTF-16 offset outside text')
    try:
        return len(raw[:offset * 2].decode('utf-16-le'))
    except UnicodeDecodeError as exc:
        raise ValueError('Offset splits a surrogate pair') from exc
