"""Set up new pilot projects and export results from the isolated local server DB.

Does not touch existing projects or connect storage with a sync operation.
"""
import argparse
import json
import os
import sys
from pathlib import Path

from .common import ROOT, PILOT, read_json, write_json, sha


def setup_django(runtime):
    runtime=Path(runtime).resolve()
    if not runtime.is_relative_to(ROOT/'.pilot-runtime'):
        raise ValueError('Label Studio runtime must be inside .pilot-runtime')
    scratch=runtime/'tmp'
    scratch.mkdir(parents=True,exist_ok=True)
    os.environ['SQLITE_TMPDIR']=str(scratch)
    os.environ['TMP']=str(scratch)
    os.environ['TEMP']=str(scratch)
    import tempfile
    tempfile.tempdir=str(scratch)
    import label_studio
    sys.path.insert(0,str(Path(label_studio.__file__).parent))
    os.environ['DJANGO_SETTINGS_MODULE']='core.settings.label_studio'
    os.environ['LABEL_STUDIO_BASE_DATA_DIR']=str(runtime)
    os.environ['LABEL_STUDIO_LOCAL_FILES_DOCUMENT_ROOT']=str(ROOT)
    os.environ['LABEL_STUDIO_LOCAL_FILES_SERVING_ENABLED']='true'
    os.environ['LABEL_STUDIO_SENTRY_DSN']=''
    os.environ['LABEL_STUDIO_FRONTEND_SENTRY_DSN']=''
    os.environ['LABEL_STUDIO_ANALYTICS_ENABLED']='false'
    import django
    django.setup()


def api_client(user):
    from rest_framework.test import APIClient
    client=APIClient()
    client.force_authenticate(user=user)
    return client


def response_json(response, expected=(200,201)):
    if response.status_code not in expected:
        raise ValueError(f'Label Studio HTTP {response.status_code}: {response.content.decode()[:1500]}')
    content=b''.join(response.streaming_content) if response.streaming else response.content
    return json.loads(content)


def create_project(client,title,config,assisted=False):
    return response_json(client.post('/api/projects/',{
        'title':title, 'label_config':config, 'show_collab_predictions':assisted,
        'show_annotation_history':False,'evaluate_predictions_automatically':False,
        'enable_empty_annotation':False,'maximum_annotations':2,
        'description':'CampNet Guideline v1.0. Independent humans first. Experimental predictions are not gold.',
    },format='json'))


def import_once(client,project,tasks):
    from tasks.models import Task
    existing=list(Task.objects.filter(project_id=project).values('id','data'))
    incoming={t['data']['task_id']:t for t in tasks}
    if len(incoming)!=len(tasks):
        raise ValueError('Duplicate stable task IDs in import')
    seen={}
    for old in existing:
        key=old['data'].get('task_id')
        if key in seen or key not in incoming or old['data']!=incoming[key]['data']:
            raise ValueError('Existing project data differs or contains duplicate IDs; use a new project')
        seen[key]=old['id']
    missing=[t for t in tasks if t['data']['task_id'] not in seen]
    if missing:
        response_json(client.post(f'/api/projects/{project}/import?return_task_ids=true',missing,format='json'))
    return list(Task.objects.filter(project_id=project).order_by('id').values_list('id',flat=True))


def storage(client,project,images):
    return response_json(client.post('/api/storages/localfiles/',{
        'project':project,'path':str(Path(images).resolve()),'title':'Pilot image access (do not sync)',
        'use_blob_urls':True,'regex_filter':'.*\\.(jpg|png)$',
    },format='json'))


def setup_projects(pilot=PILOT, runtime=ROOT/'.pilot-runtime/label-studio'):
    setup_django(runtime)
    from users.models import User
    user=User.objects.filter(is_active=True).exclude(active_organization=None).order_by('id').first()
    if not user:
        raise ValueError('Create your pilot account at http://localhost:8081 first, then run setup again.')
    client=api_client(user)
    pilot=Path(pilot)
    # Pin the full import/config hash. Re-running never appends duplicate tasks or silently replaces predictions.
    registry_path=Path(runtime)/'pilot-projects.json'
    registry=read_json(registry_path) if registry_path.exists() else {}
    for key,source in [('stage_a_manual','stage_a_manual'),('manual','manual'),('assisted','assisted')]:
        config=(pilot/'config'/f'{key}.xml').read_text(encoding='utf-8')
        tasks=read_json(pilot/'imports'/f'{source}.json')
        fingerprint=sha(config+str(tasks))
        old=registry.get(key)
        if old and old['fingerprint']!=fingerprint:
            raise ValueError(f'{key} input changed; export old project and use a fresh runtime to avoid overwriting decisions')
        if not old:
            created=create_project(client,'CampNet 17 — '+key,config,key=='assisted')
            old={'project_id':created['id'],'fingerprint':fingerprint}
            registry[key]=old
            write_json(registry_path,registry)
        pid=old['project_id']
        import_once(client,pid,tasks)
        if key!='stage_a_manual':
            from io_storages.localfiles.models import LocalFilesImportStorage
            if not LocalFilesImportStorage.objects.filter(project_id=pid).exists():
                storage(client,pid,pilot/'images')
        print(f'{key}: http://localhost:8081/projects/{pid}/data')
    return registry


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['setup','export'])
    parser.add_argument('--runtime',type=Path,default=ROOT/'.pilot-runtime/label-studio')
    parser.add_argument('--pilot',type=Path,default=PILOT)
    parser.add_argument('--project',type=int)
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    if args.command=='setup':
        setup_projects(pilot=args.pilot,runtime=args.runtime)
    else:
        if not args.project or not args.output:
            parser.error('export needs --project and --output')
        setup_django(args.runtime)
        from projects.models import Project
        project=Project.objects.get(pk=args.project)
        client=api_client(project.created_by)
        result=response_json(client.get(f'/api/projects/{args.project}/export?exportType=JSON&download_all_tasks=true'))
        write_json(args.output,result)
        print(f'Exported {len(result)} native tasks to {args.output}')


if __name__=='__main__':
    try:
        main()
    except ValueError as exc:
        print(str(exc),file=sys.stderr)
        raise SystemExit(2)
