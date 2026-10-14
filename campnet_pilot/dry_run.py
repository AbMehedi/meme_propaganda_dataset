"""Real Label Studio API save/export tests using a separate disposable database."""
import io
import uuid
from copy import deepcopy
from pathlib import Path

from .common import ROOT,PILOT,read_json,write_json,sha
from .labelstudio import setup_django,api_client,response_json,create_project,import_once,storage
from .config import make_config
from .fixtures import cases,choice,base_result,evidence
from .export import normalize_decision


def main():
    runtime=ROOT/'.pilot-runtime'/('dry-run-'+uuid.uuid4().hex[:8])
    setup_django(runtime)
    from django.core.management import call_command
    call_command('migrate',interactive=False,verbosity=0,stdout=io.StringIO())
    from users.models import User
    from organizations.models import Organization
    from tasks.models import Task,Prediction
    from core.label_config import validate_label_config
    user=User.objects.create_user(email='synthetic@campnet.invalid',password=None)
    org=Organization.create_organization(created_by=user,title='SYNTHETIC SOFTWARE CHECKS')
    user.active_organization=org;user.save()
    client=api_client(user)
    manual=read_json(PILOT/'imports/manual.json')
    manifest=read_json(PILOT/'manifest.json')
    checks=[]
    for name in ('stage_a_manual','manual','assisted'):
        validate_label_config((PILOT/'config'/f'{name}.xml').read_text(encoding='utf-8'))
        checks.append(name+': installed Label Studio XML validation passed')
    p=create_project(client,'TEST ONLY — real 17 clean imports',make_config())
    ids=import_once(client,p['id'],manual)
    assert len(ids)==17 and import_once(client,p['id'],manual)==ids
    assert Prediction.objects.filter(task__project_id=p['id']).count()==0
    storage(client,p['id'],PILOT/'images')
    # Local image endpoint needs a real authenticated session, not API force_authenticate.
    client.force_login(user)
    image_response=client.get(manual[0]['data']['image']+'&task='+str(ids[0]))
    assert image_response.status_code==200, image_response.status_code
    image_bytes=b''.join(image_response.streaming_content) if image_response.streaming else image_response.content
    assert sha(image_bytes)==manual[0]['data']['image_sha256']
    checks += ['17 actual manual imports; zero predictions','Repeated import kept exactly 17 tasks',
               'Authenticated local image serving returned original checksum']
    fixtures=cases(manual[0])
    testp=create_project(client,'TEST ONLY — synthetic manual workflow',make_config())
    testids=import_once(client,testp['id'],[{'data':c['data']} for c in fixtures])
    for tid,case in zip(testids,fixtures):
        response_json(client.post(f'/api/tasks/{tid}/annotations/',{'result':case['result']},format='json'))
    exported=response_json(client.get(f'/api/projects/{testp["id"]}/export?exportType=JSON&download_all_tasks=true'))
    write_json(PILOT/'dry_run/manual_native_export.json',exported)
    normalized=[]
    for task in exported:
        for annotation in task['annotations']:
            value=normalize_decision(task['data'],annotation)
            assert value['valid'],value['validation_errors']
            normalized.append(value)
    assert len(normalized)==8
    write_json(PILOT/'dry_run/manual_normalized.json',normalized)
    checks.append('8 synthetic manual cases saved and exported with intact evidence/Unicode offsets')
    # Separate Stage A verifies no image or predictions and keeps decisions immutable by project separation.
    stagea=read_json(PILOT/'imports/stage_a_manual.json')
    assert all('image' not in t['data'] and not t.get('predictions') for t in stagea)
    a=create_project(client,'TEST ONLY — Stage A',make_config('A'))
    assert len(import_once(client,a['id'],stagea))==17
    checks.append('17 blind Stage A tasks imported with no image or predictions')
    assisted=create_project(client,'TEST ONLY — synthetic assisted workflow',make_config('B',True),True)
    assisted_tasks=[]
    for action in ('ACCEPTED','EDITED','REJECTED'):
        c=deepcopy(fixtures[0])
        c['data'].update(task_id='SYNTHETIC-'+action,annotation_mode='assisted',model_notice='SYNTHETIC MODEL PREDICTION — not real inference')
        assisted_tasks.append({'data':c['data'],'predictions':[{'model_version':'synthetic-test-only-v1','result':c['result']}]})
    aid=import_once(client,assisted['id'],assisted_tasks)
    original={p.id:deepcopy(p.result) for p in Prediction.objects.filter(task__project_id=assisted['id'])}
    for tid,action in zip(aid,('ACCEPTED','EDITED','REJECTED')):
        pred=Prediction.objects.get(task_id=tid)
        data=Task.objects.get(pk=tid).data
        result=deepcopy(pred.result)
        if action=='EDITED':
            result=base_result(['T02'])+evidence(data,'T02',quote='জাতির শত্রু')
        elif action=='REJECTED':
            result=base_result([])
        result.append(choice('model_review',[action]))
        saved=response_json(client.post(f'/api/tasks/{tid}/annotations/',{'result':result,'parent_prediction':pred.id},format='json'))
        # Editing existing annotations uses a supported API patch.
        response_json(client.patch(f'/api/annotations/{saved["id"]}/',{'result':result},format='json'))
    exp=response_json(client.get(f'/api/projects/{assisted["id"]}/export?exportType=JSON&download_all_tasks=true'))
    write_json(PILOT/'dry_run/assisted_native_export.json',exp)
    assisted_norm=[]
    for task in exp:
        assert len(task['predictions'])==1 and len(task['annotations'])==1
        norm=normalize_decision(task['data'],task['annotations'][0])
        assert norm['valid'],norm['validation_errors']
        assisted_norm.append(norm)
    assert all(p.result==original[p.id] for p in Prediction.objects.filter(task__project_id=assisted['id']))
    write_json(PILOT/'dry_run/assisted_normalized.json',assisted_norm)
    checks.append('Synthetic predictions imported, accepted/edited/rejected, patched and exported separately from human decisions; originals unchanged')
    result={'label_studio_version':__import__('label_studio').__version__,'checks_passed':checks,
            'manual_synthetic_cases':[c['name'] for c in fixtures],
            'assisted_actions':['ACCEPTED','EDITED','REJECTED'],'research_annotations_created':0,
            'browser_ui_tested':False,'screenshots':[],
            'ui_checks_pending':['visual layout and font rendering','mouse highlight/box creation','image zoom',
                                'prediction display/copy/edit/reject using browser controls','Submit button interaction'],
            'runtime':str(runtime.relative_to(ROOT))}
    write_json(PILOT/'dry_run/results.json',result)
    print('\n'.join(checks))


if __name__=='__main__':
    main()
