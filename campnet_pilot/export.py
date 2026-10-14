"""Normalize native Label Studio JSON; invalid records remain explicit audit records."""
import argparse
import math
from collections import defaultdict

from .common import PILOT, TECHNIQUES, ROLES, read_json, write_json, sha, technique, utf16_to_cp
from .config import result_contract


def normalize_decision(data, decision, origin='human', canonical=None):
    errors = []
    results = decision.get('result', [])
    if not isinstance(results,list):
        errors.append('Annotation result must be a list of saved fields')
        results=[]
    stage=data.get('stage')
    if stage not in ('A','B'):
        errors.append('Missing or invalid annotation stage')
    contract=result_contract(stage if stage in ('A','B') else 'B',
                             data.get('annotation_mode')=='assisted' and stage!='A')
    fields, regions = {}, defaultdict(dict)
    for index,r in enumerate(results):
        if not isinstance(r,dict):
            errors.append(f'Result {index}: expected a saved field object')
            continue
        name = r.get('from_name', '')
        spec=contract.get(name) if isinstance(name,str) else None
        if spec is None:
            errors.append(f'Unknown or unavailable form field: {name}')
            continue
        if r.get('type')!=spec['type'] or r.get('to_name')!=spec['target']:
            errors.append(f'{name}: wrong field type or target (expected {spec["type"]} → {spec["target"]})')
            continue
        key={'textarea':'text','choices':'choices','labels':'labels','rectanglelabels':'rectanglelabels'}[spec['type']]
        value=r.get('value')
        vals=value.get(key) if isinstance(value,dict) else None
        if not isinstance(vals,list) or any(not isinstance(v,str) for v in vals):
            errors.append(f'{name}: saved {key} must be a list of strings')
            continue
        if (not spec['multiple'] and len(vals)!=1) or len(set(vals))!=len(vals):
            errors.append(f'{name}: expected one answer, or found duplicate answers')
            continue
        if spec['values'] and any(v not in spec['values'] for v in vals):
            errors.append(f'{name}: contains an unknown option')
            continue
        if spec['per_region']:
            rid=r.get('id')
            if not isinstance(rid,str) or not rid:
                errors.append(f'{name}: evidence region lacks a stable ID')
                continue
            region = regions[rid]
            if name in region:
                errors.append('Duplicate region control ' + name)
            region[name] = r
        else:
            if name in fields:
                errors.append('Duplicate post control ' + name)
            fields[name] = r
    def values(mapping, name, key):
        return mapping.get(name, {}).get('value', {}).get(key, [])
    def one(mapping, name, key='choices'):
        v = values(mapping, name, key)
        if not isinstance(v, list) or len(v) != 1:
            return None
        return v[0]
    for field, hash_field in [('ocr','ocr_sha256'),('caption','caption_sha256')]:
        if sha(data.get(field,'')) != data.get(hash_field):
            errors.append(field + ': canonical text checksum mismatch')
    if canonical:
        for key in ('image_id','post_id','image_sha256','ocr_version','ocr_sha256','caption_sha256','ocr','caption'):
            if data.get(key) != canonical.get(key):
                errors.append('Task differs from pinned manifest: ' + key)
    status = one(fields,'status')
    if status not in ('COMPLETE','UNRESOLVED','EXCLUDE'):
        errors.append('Missing or invalid post status')
    selected = []
    for value in values(fields,'techniques','choices'):
        try:
            selected.append(technique(value))
        except ValueError as exc:
            errors.append(str(exc))
    if len(set(selected)) != len(selected):
        errors.append('Duplicate selected technique')
    no_technique = bool(values(fields,'no_technique','choices'))
    if no_technique and (selected or status != 'COMPLETE'):
        errors.append('No Propaganda Technique conflicts with techniques or unresolved/excluded status')
    if status == 'COMPLETE' and not selected and not no_technique:
        errors.append('Complete empty core set needs explicit No Propaganda Technique confirmation')
    note = one(fields,'post_note','text')
    if not isinstance(note,str) or not note.strip():
        errors.append('Post note is required')
    instances = {}
    for rid, parts in regions.items():
        try:
            if not rid:
                raise ValueError('Evidence region lacks a stable ID')
            anchors = [(n,parts[n]) for n in ('caption_spans','ocr_spans','visual_evidence') if n in parts]
            if len(anchors) != 1:
                raise ValueError('Region must have exactly one text/rectangle anchor')
            name, anchor = anchors[0]
            prefix = {'caption_spans':'caption','ocr_spans':'ocr','visual_evidence':'visual'}[name]
            target = 'image' if prefix == 'visual' else prefix
            wrong=[n for n in parts if not n.startswith(prefix+'_')]
            if wrong:
                raise ValueError('Fields belong to another evidence channel: '+', '.join(wrong))
            missing=[n for n,spec in contract.items() if n.startswith(prefix+'_') and spec['required'] and
                     not (origin!='human' and n.endswith('_confidence')) and
                     (n not in parts or (spec['type']=='textarea' and not one(parts,n,'text').strip()))]
            if missing:
                for n in missing:
                    errors.append(f'Region {rid}: {contract[n]["message"]}')
                continue
            if anchor.get('to_name') != target:
                raise ValueError('Evidence has wrong to_name')
            kind = 'rectanglelabels' if prefix=='visual' else 'labels'
            if anchor.get('type') != kind:
                raise ValueError('Evidence has wrong result type')
            labels = anchor['value'].get(kind,[])
            if len(labels) != 1:
                raise ValueError('One technique label required per evidence region')
            code = technique(labels[0])
            number = one(parts,prefix+'_instance','text')
            if not isinstance(number,str) or not number.isascii() or not number.isdigit() or int(number)<1:
                raise ValueError('Use a positive instance number on each region')
            instance_id = code + '-' + str(int(number))
            reason = one(parts,prefix+'_reason','text')
            if not isinstance(reason,str) or not reason.strip():
                raise ValueError('Evidence explanation required')
            role = 'NOT_USED' if data.get('stage')=='A' else one(parts,prefix+'_role')
            suff = 'true' if data.get('stage')=='A' else one(parts,prefix+'_sufficient')
            confidence = one(parts,prefix+'_confidence')
            if role not in ROLES or suff not in ('true','false','unknown') or (origin=='human' and confidence not in ('1','2','3')):
                raise ValueError('Missing/invalid contribution, text sufficiency, or confidence')
            sufficient = {'true':True,'false':False,'unknown':None}[suff]
            value = anchor['value']
            if prefix != 'visual':
                text = data[prefix]
                start,end = utf16_to_cp(text,value['start']),utf16_to_cp(text,value['end'])
                quote = value['text']
                if not quote or start>=end or text[start:end]!=quote:
                    raise ValueError('Quote does not match exact canonical text/offsets')
                channel = 'CAPTION' if prefix=='caption' else 'EMBEDDED_TEXT'
                evidence = {'region_id':rid,'type':'TEXT','channel':channel,'start':start,'end':end,
                            'quote':quote,'text_sha256':data[prefix+'_sha256'],
                            'text_version':data['ocr_version'] if prefix=='ocr' else 'caption-sha256:'+data['caption_sha256'],
                            'offset_unit':'unicode_code_point','reason':reason}
            else:
                if data.get('stage')=='A':
                    raise ValueError('Image evidence is forbidden in blind text Stage A')
                x,y,w,h = [value[k]/100 for k in ('x','y','width','height')]
                if not all(math.isfinite(v) for v in (x,y,w,h)) or not (0<=x<1 and 0<=y<1 and w>0 and h>0 and x+w<=1.000001 and y+h<=1.000001):
                    raise ValueError('Rectangle outside image or empty')
                if value.get('rotation',0)!=0 or anchor.get('image_rotation',0)!=0:
                    raise ValueError('Rotated boxes require explicit conversion')
                if [anchor.get('original_width'),anchor.get('original_height')] != [data.get('width'),data.get('height')]:
                    raise ValueError('Rectangle dimensions differ from canonical image')
                scope = one(parts,'visual_scope')
                channel = one(parts,'visual_kind')
                if scope not in ('LOCAL','GLOBAL') or channel not in ('NON_TEXT_VISUAL','TYPOGRAPHY_LAYOUT'):
                    raise ValueError('Missing/invalid visual scope or kind')
                if scope=='GLOBAL' and any(abs(a-b)>0.005 for a,b in zip((x,y,w,h),(0,0,1,1))):
                    raise ValueError('GLOBAL requires a full-image rectangle')
                evidence={'region_id':rid,'type':'VISUAL','channel':channel,'kind':channel,
                          'scope':scope,'box':[x,y,min(1,x+w),min(1,y+h)],'reason':reason,
                          'grounding_verified':origin=='human','supervision_available':origin=='human' and role!='UNRESOLVED'}
            target_name=one(parts,prefix+'_target','text')
            target_name=target_name.strip() or None if isinstance(target_name,str) else None
            confidence_value=int(confidence) if confidence in ('1','2','3') else None
            # Keep each mark's metadata as well as the instance summary. Linked marks
            # may have different confidence/target answers; raw_result remains lossless.
            evidence.update(target=target_name,confidence=confidence_value,
                            visual_contribution=role,text_sufficient=sufficient)
            instance=instances.get(instance_id)
            if instance and (instance['visual_contribution'],instance['text_sufficient'])!=(role,sufficient):
                raise ValueError('Linked regions disagree on picture role/text sufficiency')
            if instance is None:
                instance={'instance_id':instance_id,'technique_id':code,'technique_name':TECHNIQUES[code],
                          'visual_contribution':role,'text_sufficient':sufficient,'evidence':[],
                          'evidence_channels':[],'target':target_name,'confidence':confidence_value}
                instances[instance_id]=instance
            instance['evidence'].append(evidence)
            if channel not in instance['evidence_channels']:
                instance['evidence_channels'].append(channel)
        except (KeyError,ValueError,TypeError) as exc:
            errors.append(f'Region {rid}: {exc}')
    evidenced = {i['technique_id'] for i in instances.values()}
    if evidenced != set(selected):
        errors.append(f'Technique/evidence mismatch: selected={sorted(set(selected))}, evidenced={sorted(evidenced)}')
    for instance in instances.values():
        channels=instance['evidence_channels']
        text = any(c in channels for c in ('CAPTION','EMBEDDED_TEXT'))
        visual = any(c in channels for c in ('NON_TEXT_VISUAL','TYPOGRAPHY_LAYOUT'))
        role,suff=instance['visual_contribution'],instance['text_sufficient']
        reasons=[]
        if role=='NOT_USED' and (not text or visual or suff is not True):
            reasons.append('NOT_USED requires text evidence, true sufficiency, and no visual evidence')
        if role=='REQUIRED' and (not visual or suff is not False):
            reasons.append('REQUIRED requires visual evidence and false text sufficiency')
        if role=='REINFORCING' and (not visual or not text or suff is not True):
            reasons.append('REINFORCING requires both channels and true text sufficiency')
        if instance['technique_id'] in ('T01','T06') and not text:
            reasons.append('This technique needs linguistic evidence')
        if instance['technique_id']=='T07' and 'NON_TEXT_VISUAL' not in channels:
            reasons.append('T07 needs a non-textual visual emotional mechanism')
        errors.extend(instance['instance_id']+': '+r for r in reasons)
    watchlist=values(fields,'watchlist','choices')
    if any(v not in ('W01','W02','W03','other_candidate') for v in watchlist):
        errors.append('Invalid watchlist candidate')
    flags=values(fields,'review_flags','choices')
    if any(v not in ('UNREADABLE_TEXT','MISSING_CONTEXT','OCR_REVIEW','ADJUDICATION','UNCERTAIN_VISUAL_CONTRIBUTION') for v in flags):
        errors.append('Invalid review flag')
    review=one(fields,'model_review')
    if data.get('annotation_mode')=='assisted' and origin=='human' and review not in ('ACCEPTED','EDITED','REJECTED','NOT_AVAILABLE'):
        errors.append('Assisted annotation needs model review action')
    return {'schema_version':'campnet-evidence-1','task_id':data.get('task_id'),'image_id':data.get('image_id'),
            'post_id':data.get('post_id'),'stage':data.get('stage'),'origin':origin,
            'annotation_id':decision.get('id'),'reviewer':decision.get('completed_by'),
            'model_version':decision.get('model_version'),'parent_prediction':decision.get('parent_prediction'),
            'model_review_action':review,'ocr_version':data.get('ocr_version'),'ocr_sha256':data.get('ocr_sha256'),
            'caption_sha256':data.get('caption_sha256'),'image_sha256':data.get('image_sha256'),
            'status':status,'has_core_technique':bool(selected) if status=='COMPLETE' else None,
            'techniques':selected,'instances':list(instances.values()),'watchlist':watchlist,
            'out_of_taxonomy':bool(watchlist),'review_flags':flags,
            'post_note':note,'valid':not errors,'validation_errors':errors,'is_gold':False,
            'raw_result':decision.get('result',[]),
            'evidence_region_count':len(regions),
            'exported_region_count':sum(len(i['evidence']) for i in instances.values()),
            'unexported_region_ids':sorted(set(regions)-{e['region_id'] for i in instances.values() for e in i['evidence']})}


def normalize_export(tasks, manifest):
    by_id={r['image_id']:r for r in manifest}
    output=[]
    for task in tasks:
        data=task['data']
        canonical=by_id.get(data.get('image_id'))
        for key,origin in [('annotations','human'),('predictions','model_prediction')]:
            for decision in task.get(key,[]):
                result=normalize_decision(data,decision,origin,canonical)
                if canonical is None:
                    result['validation_errors'].append('Image ID absent from pilot manifest')
                    result['valid']=False
                result['cancelled']=decision.get('was_cancelled',False)
                if result['cancelled']:
                    result['valid']=False
                    result['validation_errors'].append('Cancelled/skipped annotation is not a completed decision')
                output.append(result)
    return output


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('input');p.add_argument('--output',required=True)
    p.add_argument('--manifest',default=PILOT/'manifest.json')
    args=p.parse_args()
    result=normalize_export(read_json(args.input),read_json(args.manifest))
    write_json(args.output,result)
    invalid=sum(not r['valid'] and r['origin']=='human' for r in result)
    print(f'{len(result)} decisions exported; {invalid} invalid human records; no records promoted to gold. Predictions remain provisional.')
    if invalid:
        raise SystemExit(2)


if __name__=='__main__':
    main()
