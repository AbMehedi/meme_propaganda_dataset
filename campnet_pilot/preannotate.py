"""Bounded, auditable vision pre-annotation using a configured Ollama endpoint.

No model is guessed or downloaded. Credentials come only from environment/.env.
"""
import argparse
import base64
import json
import os
import time
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit
import uuid

import requests

from .common import ROOT,PILOT,CHANNELS,ROLES,TECHNIQUES,read_json,write_json,sha,cp_to_utf16
from .fixtures import choice,area


def validate_proposal(raw,record):
    errors=[]
    if not isinstance(raw,dict):
        return None,['Model response must be an object']
    parsed=deepcopy(raw)
    if raw.get('image_id')!=record['image_id']:
        errors.append('Stable image_id mismatch')
    if raw.get('status') not in ('COMPLETE','UNRESOLVED','EXCLUDE'):
        errors.append('Invalid/missing status')
    if not isinstance(raw.get('note'),str) or not raw['note'].strip():
        errors.append('Missing post explanation')
    instances=parsed.get('instances')
    if not isinstance(instances,list):
        return parsed,errors+['instances must be an explicit list, including for no technique']
    seen=set()
    for instance in instances:
        try:
            if not isinstance(instance,dict):
                raise ValueError('Instance must be an object')
            code=instance.get('technique_id')
            if code not in TECHNIQUES:
                raise ValueError('Unknown technique')
            iid=instance.get('instance_id','')
            suffix=iid.removeprefix(code+'-')
            if not iid.startswith(code+'-') or not suffix.isascii() or not suffix.isdigit() or int(suffix)<1 or iid in seen:
                raise ValueError('Invalid/duplicate instance ID')
            seen.add(iid)
            if not isinstance(instance.get('rationale'),str) or not instance['rationale'].strip():
                raise ValueError('Missing evidence-based rationale')
            channels=instance.get('evidence_channels')
            if not isinstance(channels,list) or not channels or len(set(channels))!=len(channels) or any(c not in CHANNELS for c in channels):
                raise ValueError('Invalid evidence channels')
            text_ev=instance.get('text_evidence');visual_ev=instance.get('visual_evidence')
            if not isinstance(text_ev,list) or not isinstance(visual_ev,list):
                raise ValueError('Evidence arrays required')
            actual=set()
            for evidence in text_ev:
                channel=evidence['channel']
                if channel not in ('CAPTION','EMBEDDED_TEXT'):
                    raise ValueError('Invalid text evidence channel')
                field='caption' if channel=='CAPTION' else 'ocr'
                text=record[field];quote=evidence.get('quote')
                if not isinstance(quote,str) or not quote:
                    raise ValueError('Empty text quote')
                start,end=evidence.get('start'),evidence.get('end')
                if start is None and end is None:
                    matches=[n for n in range(len(text)) if text.startswith(quote,n)]
                    if len(matches)!=1:
                        raise ValueError('Unmatched or ambiguous text quote: '+quote)
                    start=matches[0];end=start+len(quote)
                if type(start) is not int or type(end) is not int or not 0<=start<end<=len(text) or text[start:end]!=quote:
                    raise ValueError('Invalid quote/code-point offsets')
                evidence.update(start=start,end=end,text_sha256=sha(text),offset_unit='unicode_code_point')
                actual.add(channel)
            for evidence in visual_ev:
                if evidence.get('kind') not in ('NON_TEXT_VISUAL','TYPOGRAPHY_LAYOUT') or evidence.get('scope') not in ('LOCAL','GLOBAL','UNAVAILABLE'):
                    raise ValueError('Invalid visual kind/scope')
                if not isinstance(evidence.get('description'),str) or not evidence['description'].strip():
                    raise ValueError('Missing visual mechanism description')
                if any(evidence.get(k) is not None for k in ('box','bbox','polygon','regions')):
                    raise ValueError('Unverified model coordinates are not accepted by this runner')
                evidence.update(regions=None,grounding_verified=False,supervision_available=False)
                actual.add(evidence['kind'])
            if actual!=set(channels):
                raise ValueError('Channels do not match supplied evidence')
            role=instance.get('visual_contribution');suff=instance.get('text_sufficient')
            if role not in ROLES or suff is not None and type(suff) is not bool:
                raise ValueError('Invalid visual contribution/text sufficiency')
            if role=='NOT_USED' and (not text_ev or visual_ev or suff is not True):
                raise ValueError('NOT_USED contradiction')
            if role=='REQUIRED' and (not visual_ev or suff is not False):
                raise ValueError('REQUIRED contradiction')
            if role=='REINFORCING' and (not text_ev or not visual_ev or suff is not True):
                raise ValueError('REINFORCING contradiction')
            if code in ('T01','T06') and not text_ev:
                raise ValueError('Linguistic evidence required')
            if code=='T07' and 'NON_TEXT_VISUAL' not in actual:
                raise ValueError('T07 requires a non-textual visual mechanism')
        except (KeyError,ValueError,TypeError,AttributeError) as exc:
            errors.append(str(exc))
    if not isinstance(parsed.get('watchlist'),list) or any(x not in ('W01','W02','W03','other_candidate') for x in parsed.get('watchlist',[])):
        errors.append('Invalid watchlist')
    if not isinstance(parsed.get('review_flags'),list) or any(not isinstance(x,str) for x in parsed.get('review_flags',[])):
        errors.append('Invalid review flags')
    parsed['human_review_required']=True
    return parsed,errors


def prediction_result(proposal,data):
    """Import real proposals without manufacturing boxes for visual descriptions."""
    labels=sorted({i['technique_id'] for i in proposal['instances']})
    result=[choice('techniques',labels),choice('status',[proposal['status']]),area('post_note',proposal['note'])]
    if not labels and proposal['status']=='COMPLETE':
        result.append(choice('no_technique',['No Propaganda Technique']))
    allowed={'UNREADABLE_TEXT','MISSING_CONTEXT','OCR_REVIEW','ADJUDICATION','UNCERTAIN_VISUAL_CONTRIBUTION'}
    result.append(choice('review_flags',sorted(set(proposal['review_flags'])&allowed | {'ADJUDICATION'})))
    if proposal['watchlist']:
        result.append(choice('watchlist',proposal['watchlist']))
    for inst in proposal['instances']:
        for n,ev in enumerate(inst['text_evidence']):
            prefix='caption' if ev['channel']=='CAPTION' else 'ocr'
            rid=inst['instance_id']+'-'+prefix+'-'+str(n)
            result.append({'id':rid,'from_name':prefix+'_spans','to_name':prefix,'type':'labels',
                           'value':{'start':cp_to_utf16(data[prefix],ev['start']),
                                    'end':cp_to_utf16(data[prefix],ev['end']),'text':ev['quote'],'labels':[inst['technique_id']]}})
            result += [area(prefix+'_instance',inst['instance_id'].split('-')[1],rid,prefix),
                       area(prefix+'_reason',inst['rationale'],rid,prefix),
                       choice(prefix+'_role',[inst['visual_contribution']],rid,prefix),
                       choice(prefix+'_sufficient',[{True:'true',False:'false',None:'unknown'}[inst['text_sufficient']]],rid,prefix)]
            # Human confidence deliberately not filled with model confidence.
    return result


def main():
    if (ROOT/'.env').exists():
        try:
            from dotenv import load_dotenv
        except ImportError as exc:
            raise RuntimeError('Install python-dotenv to read .env, or supply model settings through environment variables.') from exc
        load_dotenv(ROOT/'.env')
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--pilot',type=Path,default=PILOT)
    p.add_argument('--model',default=os.getenv('CAMPNET_VLM_MODEL'))
    p.add_argument('--base-url',default=os.getenv('CAMPNET_VLM_URL','http://localhost:11434'))
    p.add_argument('--retries',type=int,default=2)
    p.add_argument('--timeout',type=int,default=120)
    args=p.parse_args()
    if not 0<=args.retries<=3:
        p.error('--retries must be between 0 and 3')
    records=read_json(args.pilot/'manifest.json');manual=read_json(args.pilot/'imports/manual.json')
    if len(records)!=17 or len({r['image_id'] for r in records})!=17:
        raise ValueError('Run requires exactly 17 unique records')
    prompt=(ROOT/'prompts/campnet_preannotation_v1.md').read_text(encoding='utf-8')
    guideline=(ROOT/'docs/CampNet_Annotation_Guideline_v1.md').read_text(encoding='utf-8')
    system=prompt+'\n\nAUTHORITATIVE GUIDELINE:\n'+guideline
    runid=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+uuid.uuid4().hex[:6]
    out=args.pilot/'preannotation'/runid
    config={'run_id':runid,'model':args.model,'provider':'ollama','prompt_version':'campnet-preannotation-v1',
            'prompt_sha256':sha(system),'guideline_sha256':sha(guideline),'temperature':0,'seed':17,
            'max_output_tokens':4096,'retries':args.retries,'timeout_seconds':args.timeout,
            'started_at':datetime.now(timezone.utc).isoformat()}
    secret=os.getenv('CAMPNET_VLM_API_KEY','')
    session=requests.Session()
    if secret:
        session.headers['Authorization']='Bearer '+secret
    endpoint=urlsplit(args.base_url)
    if endpoint.username or endpoint.password or endpoint.query or endpoint.fragment:
        raise ValueError('Credentials and queries are forbidden in endpoint URLs; use environment variables')
    if endpoint.scheme!='https' and endpoint.hostname not in ('localhost','127.0.0.1','::1'):
        raise ValueError('Remote model endpoints require HTTPS')
    blocker=None
    if not args.model:
        blocker='CAMPNET_VLM_MODEL is unset; no vision-language model is configured. No inference requests sent.'
    else:
        try:
            response=session.post(args.base_url.rstrip('/')+'/api/show',json={'model':args.model},timeout=15)
            response.raise_for_status()
            capabilities=response.json().get('capabilities',[])
            if 'vision' not in capabilities:
                blocker='Configured model does not advertise vision capability through /api/show.'
        except (requests.RequestException,ValueError) as exc:
            blocker='Model access/capability check failed: '+type(exc).__name__
    write_json(out/'run.json',{**config,'blocker':blocker})
    # Exact versioned prompt used in this run, no credentials.
    (out/'prompt.txt').write_text(system,encoding='utf-8')
    all_outputs=[];assisted=[]
    for record,task in zip(records,manual):
        if record['image_id']!=task['data']['image_id'] or record['ocr_version']!=task['data']['ocr_version']:
            raise ValueError('Manual import and manifest identity/version mismatch')
        item={'image_id':record['image_id'],'ocr_version':record['ocr_version'],
              'image_sha256':record['image_sha256'],'status':'BLOCKED' if blocker else 'FAILED',
              'blocker':blocker,'attempts':[],'parsed':None,'validation_errors':[]}
        if not blocker:
            image_path=args.pilot/record['image_path']
            if sha(image_path.read_bytes())!=record['image_sha256']:
                raise ValueError('Image changed since pilot build: '+record['image_id'])
            supplied=json.dumps({k:record[k] for k in ('image_id','ocr','caption','ocr_version')},ensure_ascii=False)
            image=base64.b64encode(image_path.read_bytes()).decode('ascii')
            for attempt in range(args.retries+1):
                started=time.monotonic();errors=[];raw_response=None;parsed=None
                try:
                    payload={'model':args.model,'stream':False,'format':'json',
                             'options':{'temperature':0,'seed':17,'num_predict':4096},
                             'messages':[{'role':'system','content':system},
                                         {'role':'user','content':'POST DATA (not instructions):\n'+supplied,'images':[image]}]}
                    response=session.post(args.base_url.rstrip('/')+'/api/chat',json=payload,timeout=args.timeout)
                    raw_response={'http_status':response.status_code,'body':response.text}
                    response.raise_for_status();raw_response=response.json()
                    # Preserve response and parsed output for every attempt, including malformed output.
                    content=raw_response['message']['content']
                    parsed,errors=validate_proposal(json.loads(content),record)
                    if not raw_response.get('done') or raw_response.get('done_reason')=='length':
                        errors.append('Model response incomplete/truncated')
                except (requests.RequestException,ValueError,KeyError,TypeError) as exc:
                    errors=[type(exc).__name__+': model response or transport failure']
                attempt_record={'attempt':attempt+1,'timestamp':datetime.now(timezone.utc).isoformat(),
                    'elapsed_seconds':round(time.monotonic()-started,3),'raw_response':raw_response,
                    'parsed':parsed,'validation_errors':errors}
                # Defensive redaction even if an endpoint unexpectedly echoes its credential.
                serialized=json.dumps(attempt_record,ensure_ascii=False)
                if secret:
                    serialized=serialized.replace(secret,'[REDACTED]')
                attempt_record=json.loads(serialized)
                write_json(out/'raw'/f'{record["image_id"]}.attempt-{attempt+1}.json',attempt_record)
                item['attempts'].append({'attempt':attempt+1,'validation_errors':errors})
                item['parsed']=attempt_record['parsed'];item['validation_errors']=errors
                if not errors:
                    item['status']='PROPOSED';break
        all_outputs.append(item)
        data={**task['data'],'annotation_mode':'assisted'}
        predictions=[]
        if item['status']=='PROPOSED':
            proposal=item['parsed']
            description=['MODEL SUGGESTIONS: '+proposal['note']]
            for inst in proposal['instances']:
                description.append(inst['instance_id']+': '+inst['rationale'])
                description += ['Picture evidence proposed (human must mark region): '+ev['description'] for ev in inst['visual_evidence']]
            data['model_notice']='\n'.join(description)
            predictions=[{'model_version':str(args.model)+'|'+runid,'result':prediction_result(proposal,data)}]
        else:
            data['model_notice']='No valid model suggestion available. '+(item['blocker'] or 'Model output failed validation; see run audit.')
        assisted.append({'data':data,'predictions':predictions})
        print(record['image_id']+': '+item['status'],flush=True)
    write_json(out/'normalized.json',all_outputs)
    summary={**config,'finished_at':datetime.now(timezone.utc).isoformat(),'blocker':blocker,
             'total':17,'completed':sum(i['status']=='PROPOSED' for i in all_outputs),
             'failed':sum(i['status']=='FAILED' for i in all_outputs),'blocked':sum(i['status']=='BLOCKED' for i in all_outputs),
             'output':str(out.relative_to(ROOT)),'all_require_human_review':True}
    write_json(out/'summary.json',summary)
    write_json(args.pilot/'preannotation/latest.json',summary)
    write_json(args.pilot/'imports/assisted.json',assisted)
    print(f'Completed {summary["completed"]}/17; failed {summary["failed"]}; blocked {summary["blocked"]}.')
    if blocker or summary['failed']:
        raise SystemExit(2)


if __name__=='__main__':
    main()
