"""Set up new pilot projects and export results from the isolated local server DB.

Setup never replaces existing projects. update-ui backs up the runtime and updates
compatible form layouts without changing tasks, annotations, drafts or predictions.
"""
import argparse
import json
import os
import sys
from pathlib import Path
from datetime import datetime, timezone
from xml.etree.ElementTree import fromstring

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


def control_signature(config):
    """Layout/copy may change; stored control identities and options must not."""
    return {n.attrib['name']:(n.tag,n.attrib.get('toName'),n.attrib.get('perRegion','false'),
            tuple(sorted(c.attrib['value'] for c in n if c.tag in ('Label','Choice'))))
            for n in fromstring(config).iter() if n.tag in ('Text','Image','Labels','RectangleLabels','Choices','TextArea')}


def update_ui(pilot=PILOT, runtime=ROOT/'.pilot-runtime/label-studio', check=False):
    """Apply a compatible layout update to the registered projects, with a DB backup."""
    setup_django(runtime)
    from django.conf import settings
    from django.db import transaction
    from projects.models import Project
    from tasks.models import Task
    from core.label_config import validate_label_config
    import sqlite3
    runtime=Path(runtime).resolve()
    registry_path=runtime/'pilot-projects.json'
    if not registry_path.exists():
        raise ValueError('No registered pilot projects. Run setup first.')
    registry=read_json(registry_path)
    plan=[]
    for key,entry in registry.items():
        if key not in ('stage_a_manual','manual','assisted'):
            raise ValueError('Unknown registered project: '+key)
        project=Project.objects.get(pk=entry['project_id'])
        config=(Path(pilot)/'config'/f'{key}.xml').read_text(encoding='utf-8')
        tasks=read_json(Path(pilot)/'imports'/f'{key}.json')
        validate_label_config(config)
        if control_signature(project.label_config)!=control_signature(config):
            raise ValueError(f'{key}: form entities changed; a layout-only update cannot migrate them')
        expected={t['data']['task_id']:t['data'] for t in tasks}
        actual=list(Task.objects.filter(project=project).values_list('data',flat=True))
        if len(actual)!=len(expected) or any(d!=expected.get(d.get('task_id')) for d in actual):
            raise ValueError(f'{key}: existing tasks differ from the pinned import')
        plan.append((key,project,config,sha(config+str(tasks))))
    if check:
        print('Compatible UI update: '+', '.join(key for key,_,_,_ in plan))
        return None
    if all(p.label_config==c and registry[k]['fingerprint']==f for k,p,c,f in plan):
        print('All registered forms are already current.')
        return None
    backup=ROOT/'.pilot-runtime/ui-backups'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    backup.mkdir(parents=True)
    database=Path(settings.DATABASES['default']['NAME']).resolve()
    if settings.DATABASES['default']['ENGINE']!='django.db.backends.sqlite3' or not database.is_relative_to(runtime):
        raise ValueError('UI update expects the local SQLite runtime')
    with sqlite3.connect(database.as_uri()+'?mode=ro',uri=True) as source, sqlite3.connect(backup/'label-studio.sqlite3') as dest:
        source.backup(dest)
    write_json(backup/'pilot-projects.json',registry)
    for key,project,_,_ in plan:
        (backup/(key+'.xml')).write_text(project.label_config,encoding='utf-8')
    with transaction.atomic():
        for key,project,config,fingerprint in plan:
            response_json(api_client(project.created_by).patch(f'/api/projects/{project.pk}/',
                          {'label_config':config},format='json'))
            registry[key]['fingerprint']=fingerprint
    temporary=registry_path.with_suffix('.pending.json')
    write_json(temporary,registry)
    temporary.replace(registry_path)
    print('Updated all registered forms. Tasks, annotations, drafts and predictions were preserved.')
    print('Backup: '+str(backup))
    return backup


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['setup','export','update-ui'])
    parser.add_argument('--runtime',type=Path,default=ROOT/'.pilot-runtime/label-studio')
    parser.add_argument('--pilot',type=Path,default=PILOT)
    parser.add_argument('--project',type=int)
    parser.add_argument('--output',type=Path)
    parser.add_argument('--check',action='store_true',help='Validate an update-ui plan without changing projects')
    args=parser.parse_args()
    if args.command=='setup':
        setup_projects(pilot=args.pilot,runtime=args.runtime)
    elif args.command=='update-ui':
        update_ui(pilot=args.pilot,runtime=args.runtime,check=args.check)
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
