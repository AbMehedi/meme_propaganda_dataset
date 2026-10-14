"""Optional real-browser regression check. Uses an isolated runtime and synthetic tasks.

Install playwright in the venv; uses installed Chrome headlessly. No real annotations
are created or altered. Run: python -m campnet_pilot.browser_check
"""
import io
import os
import socket
import subprocess
import sys
import time
import uuid
from copy import deepcopy

from .common import ROOT, PILOT, read_json, write_json
from .config import make_config
from .export import normalize_decision
from .fixtures import cases
from .labelstudio import setup_django, api_client, create_project, import_once, response_json


def main():
    from playwright.sync_api import sync_playwright
    runtime=ROOT/'.pilot-runtime'/('browser-check-'+uuid.uuid4().hex[:8])
    setup_django(runtime)
    from django.core.management import call_command
    from users.models import User
    from organizations.models import Organization
    call_command('migrate',interactive=False,verbosity=0,stdout=io.StringIO())
    password=uuid.uuid4().hex
    user=User.objects.create_user(email='browser-check@campnet.invalid',password=password)
    org=Organization.create_organization(created_by=user,title='SYNTHETIC BROWSER CHECK')
    user.active_organization=org;user.save()
    client=api_client(user)
    c=deepcopy(cases(read_json(PILOT/'imports/manual.json')[0])[3])
    c['data'].update(stage='A',annotation_mode='manual',caption_notice='',ocr_notice='')
    c['data'].pop('image',None)
    project=create_project(client,'TEST ONLY — browser form',make_config('A'))
    tid=import_once(client,project['id'],[{'data':c['data']}])[0]
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    base=f'http://127.0.0.1:{port}'
    env=os.environ.copy()
    env['LABEL_STUDIO_HOST']=base
    log=(runtime/'server.log').open('w',encoding='utf-8')
    import label_studio
    from pathlib import Path
    manage=Path(label_studio.__file__).parent/'manage.py'
    process=subprocess.Popen([sys.executable,str(manage),'runserver',f'127.0.0.1:{port}','--noreload'],
                             env=env,stdout=log,stderr=subprocess.STDOUT,
                             creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    try:
        import requests
        for _ in range(100):
            try:
                if requests.get(base+'/user/login/',timeout=1).status_code==200:break
            except requests.RequestException:pass
            if process.poll() is not None:raise RuntimeError('Test server stopped; see '+str(runtime/'server.log'))
            time.sleep(.3)
        with sync_playwright() as pw:
            browser=pw.chromium.launch(channel='chrome',headless=True)
            context=browser.new_context(viewport={'width':1600,'height':1000})
            page=context.new_page()
            try:
                page.goto(base+'/user/login/')
                page.locator('input[name=email]').fill(user.email)
                page.locator('input[name=password]').fill(password)
                page.get_by_role('button',name='Log In',exact=True).click()
                page.wait_for_url(base+'/',timeout=30000)
                page.goto(f'{base}/projects/{project["id"]}/data?task={tid}')
                page.locator('#ocr-reading').wait_for(timeout=45000)
                page.screenshot(path=str(runtime/'initial.png'),full_page=True,timeout=15000)
                def highlight(code,quote):
                    page.locator('.source').get_by_text(code+' · '+{'T01':'Loaded Language','T02':'Name Calling / Labeling'}[code],exact=True).last.click()
                    reading=page.locator('#ocr-reading')
                    reading.scroll_into_view_if_needed()
                    box=reading.evaluate('''(el,quote) => {
                        const walk=document.createTreeWalker(el,NodeFilter.SHOW_TEXT); let node;
                        while(node=walk.nextNode()) { const start=node.textContent.indexOf(quote);
                          if(start<0) continue;
                          const range=document.createRange(); range.setStart(node,start); range.setEnd(node,start+quote.length);
                          const r=range.getBoundingClientRect(); return {x:r.x,y:r.y,width:r.width,height:r.height};
                        } throw new Error('Quote not found in a text node');
                    }''',quote)
                    page.mouse.move(box['x']+1,box['y']+box['height']/2)
                    page.mouse.down()
                    page.mouse.move(box['x']+box['width']-1,box['y']+box['height']/2,steps=12)
                    page.mouse.up()
                    # LS creates a mark without selecting it. Open it as an annotator does.
                    page.mouse.click(box['x']+box['width']/2,box['y']+box['height']/2)
                    page.locator('#ocr-details').wait_for(state='visible')
                highlight('T01','ঘৃণ্য')
                panel=page.locator('#ocr-details')
                panel.get_by_placeholder('Type 1 for the first claim').fill('1')
                # Required fields must be visible, and Submit must name the missing reason.
                page.get_by_role('button',name='Submit',exact=True).click()
                page.get_by_text('Step 2 — Image-text highlight: write a reason in the evidence panel.',exact=True).wait_for()
                page.get_by_role('button',name='OK',exact=True).click()
                panel.get_by_placeholder('These words / this picture use [technique] because…').fill('SYNTHETIC: emotionally judgmental wording.')
                panel.get_by_text('3 · Clear evidence',exact=True).click()
                panel.get_by_placeholder('Named person or group; leave blank if unknown').fill('Synthetic target')
                # Switch marks without Add, then verify both answers survive submission.
                highlight('T02','জাতির শত্রু')
                panel.get_by_placeholder('Type 1 for the first claim').fill('1')
                panel.get_by_placeholder('These words / this picture use [technique] because…').fill('SYNTHETIC: a judgmental label.')
                panel.get_by_text('2 · Borderline, but supported',exact=True).click()
                finish=page.locator('.campnet > .card').last
                finish.get_by_text('T01 · Loaded Language',exact=True).click()
                finish.get_by_text('T02 · Name Calling / Labeling',exact=True).click()
                finish.get_by_text('Complete — I can make a decision',exact=True).click()
                finish.get_by_placeholder('Summarize your decision. If unsure, say what needs checking.').fill('SYNTHETIC browser regression only.')
                page.screenshot(path=str(runtime/'filled.png'),full_page=True,timeout=15000)
                with page.expect_response(lambda r:'/annotations' in r.url and r.request.method=='POST') as saved:
                    page.get_by_role('button',name='Submit',exact=True).click()
                assert saved.value.ok,saved.value.text()
                exported=response_json(client.get(f'/api/projects/{project["id"]}/export?exportType=JSON&download_all_tasks=true'))
                annotation=exported[0]['annotations'][0]
                normalized=normalize_decision(c['data'],annotation)
                write_json(runtime/'normalized.json',normalized)
                assert normalized['valid'],normalized['validation_errors']
                assert normalized['exported_region_count']==2
                assert normalized['instances'][0]['evidence'][0]['target']=='Synthetic target'
                write_json(runtime/'results.json',{'passed':True,'checks':['real mouse highlighting',
                    'required panel visible','missing reason message','switch marks without Add',
                    'two techniques saved','target/confidence preserved','native export validates'],
                    'research_annotations_created':0})
                print('Browser checks passed. Artifacts: '+str(runtime))
            except Exception:
                page.screenshot(path=str(runtime/'failure.png'),full_page=True,timeout=15000)
                (runtime/'failure.html').write_text(page.content(),encoding='utf-8')
                print('Browser failure artifacts: '+str(runtime))
                raise
            finally:
                browser.close()
    finally:
        process.terminate()
        try:process.wait(timeout=10)
        except subprocess.TimeoutExpired:process.kill();process.wait(timeout=5)
        log.close()


if __name__=='__main__':
    main()
