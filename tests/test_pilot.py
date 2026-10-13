import csv
import json
import tempfile
import unittest
import base64
import contextlib
import io
import shutil
from unittest.mock import patch
from copy import deepcopy
from pathlib import Path

from campnet_pilot.common import ROOT,PILOT,read_json,read_csv,indexed,sha,cp_to_utf16,utf16_to_cp
from campnet_pilot.build import build_pilot
from campnet_pilot.fixtures import cases,choice
from campnet_pilot.export import normalize_decision,normalize_export
from campnet_pilot.preannotate import validate_proposal,prediction_result


class PilotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manual=read_json(PILOT/'imports/manual.json')
        cls.manifest=read_json(PILOT/'manifest.json')
        cls.fixtures=cases(cls.manual[0])

    def test_exact_selection_and_latest_ocr(self):
        source=indexed(read_csv(ROOT/'ocr_corrected_20.csv'))
        selected={k for k,v in source.items() if v['ocr_corrected'].strip()!='#excluded'}
        self.assertEqual(len(selected),17)
        self.assertEqual({r['image_id'] for r in self.manifest},selected)
        self.assertEqual(len(list((PILOT/'images').iterdir())),17)
        for r in self.manifest:
            self.assertEqual(r['ocr'],source[r['image_id']]['ocr_corrected'])
            self.assertEqual(r['ocr_sha256'],sha(r['ocr']))
            self.assertEqual(r['image_sha256'],sha((PILOT/r['image_path']).read_bytes()))
        empty=[r for r in self.manifest if not r['ocr'].strip()]
        self.assertEqual(len(empty),1)
        self.assertEqual(empty[0]['ocr_status'],'AUTHOR_VERIFIED_EMPTY')

    def test_manual_blindness_and_assisted_parity(self):
        assisted=read_json(PILOT/'imports/assisted.json')
        a=read_json(PILOT/'imports/stage_a_manual.json')
        self.assertEqual(len(assisted),17)
        for m,s,t in zip(self.manual,assisted,a):
            self.assertFalse(m.get('predictions'))
            self.assertNotIn('model_notice',m['data'])
            self.assertNotIn('image',t['data'])
            self.assertFalse(t.get('predictions'))
            for key in ('task_id','image_id','post_id','ocr','ocr_version','ocr_sha256','caption'):
                self.assertEqual(m['data'][key],s['data'][key])
                self.assertEqual(m['data'][key],t['data'][key])

    def test_unicode_roundtrip_and_surrogate_rejection(self):
        text='😀 বাংলা ক্ষি।\n👩\u200d🔬 ঘৃণ্য'
        for cp in range(len(text)+1):
            self.assertEqual(utf16_to_cp(text,cp_to_utf16(text,cp)),cp)
        with self.assertRaises(ValueError):utf16_to_cp(text,1)
        with self.assertRaises(ValueError):utf16_to_cp(text,999)
        with self.assertRaises(ValueError):cp_to_utf16(text,-1)

    def test_eight_manual_cases(self):
        for case in self.fixtures:
            with self.subTest(case=case['name']):
                n=normalize_decision(case['data'],{'result':case['result']})
                self.assertTrue(n['valid'],n['validation_errors'])
                self.assertFalse(n['is_gold'])
                for i in n['instances']:
                    for e in i['evidence']:
                        if e['type']=='TEXT':
                            text=case['data']['ocr' if e['channel']=='EMBEDDED_TEXT' else 'caption']
                            self.assertEqual(text[e['start']:e['end']],e['quote'])

    def test_bangla_after_emoji_has_codepoint_offset(self):
        c=self.fixtures[0]
        n=normalize_decision(c['data'],{'result':c['result']})
        e=n['instances'][0]['evidence'][0]
        self.assertEqual(e['start'],c['data']['ocr'].index('ঘৃণ্য'))
        anchor=next(r for r in c['result'] if r['type']=='labels')
        self.assertEqual(anchor['value']['start'],e['start']+1)

    def test_no_technique_cannot_mean_uncertain_or_positive(self):
        for index in (0,5):
            c=deepcopy(self.fixtures[index]);c['result'].append(choice('no_technique',['No Propaganda Technique']))
            self.assertFalse(normalize_decision(c['data'],{'result':c['result']})['valid'])

    def test_repeated_instances_stay_separate(self):
        c=self.fixtures[7]
        n=normalize_decision(c['data'],{'result':c['result']})
        self.assertEqual([i['instance_id'] for i in n['instances']],['T01-1','T01-2'])

    def test_combined_evidence_link_preserved(self):
        c=self.fixtures[2]
        n=normalize_decision(c['data'],{'result':c['result']})
        self.assertEqual(len(n['instances']),1)
        self.assertEqual(len(n['instances'][0]['evidence']),2)
        self.assertEqual(set(n['instances'][0]['evidence_channels']),{'EMBEDDED_TEXT','NON_TEXT_VISUAL'})

    def test_changed_text_version_and_wrong_quote_rejected(self):
        c=deepcopy(self.fixtures[0]);c['data']['ocr']+='changed'
        self.assertFalse(normalize_decision(c['data'],{'result':c['result']})['valid'])
        c=deepcopy(self.fixtures[0]);next(r for r in c['result'] if r['type']=='labels')['value']['text']='invented'
        self.assertFalse(normalize_decision(c['data'],{'result':c['result']})['valid'])

    def test_invalid_geometry_and_role_conflicts(self):
        c=deepcopy(self.fixtures[1]);next(r for r in c['result'] if r['type']=='rectanglelabels')['value']['width']=150
        self.assertFalse(normalize_decision(c['data'],{'result':c['result']})['valid'])
        c=deepcopy(self.fixtures[2]);next(r for r in c['result'] if r['from_name']=='visual_role')['value']['choices']=['NOT_USED']
        self.assertFalse(normalize_decision(c['data'],{'result':c['result']})['valid'])

    def test_missing_evidence_not_silently_accepted(self):
        c=deepcopy(self.fixtures[0]);c['result']=[r for r in c['result'] if not r['from_name'].startswith('ocr_')]
        self.assertFalse(normalize_decision(c['data'],{'result':c['result']})['valid'])

    def proposal(self):
        c=self.fixtures[0]
        return {'image_id':c['data']['image_id'],'status':'COMPLETE','note':'Synthetic proposal only.',
                'watchlist':[],'review_flags':[], 'instances':[{
                    'instance_id':'T01-1','technique_id':'T01','rationale':'Emotionally evaluative wording.',
                    'evidence_channels':['EMBEDDED_TEXT'],'text_evidence':[{'channel':'EMBEDDED_TEXT','quote':'ঘৃণ্য','start':None,'end':None}],
                    'visual_evidence':[],'visual_contribution':'NOT_USED','text_sufficient':True}]}

    def test_model_quotes_validate_and_prediction_is_separate(self):
        c=self.fixtures[0];p,errors=validate_proposal(self.proposal(),c['data'])
        self.assertEqual(errors,[])
        self.assertEqual(p['instances'][0]['text_evidence'][0]['start'],c['data']['ocr'].index('ঘৃণ্য'))
        results=prediction_result(p,c['data'])
        self.assertFalse(any(r['type']=='rectanglelabels' for r in results))
        self.assertFalse(any(r['from_name'].endswith('_confidence') for r in results))

    def test_model_invented_and_ambiguous_quotes_rejected(self):
        p=self.proposal();p['instances'][0]['text_evidence'][0]['quote']='not in OCR'
        self.assertTrue(validate_proposal(p,self.fixtures[0]['data'])[1])
        data=deepcopy(self.fixtures[0]['data']);data['ocr']+=' ঘৃণ্য'
        self.assertTrue(validate_proposal(self.proposal(),data)[1])

    def test_wrong_model_identity_and_taxonomy(self):
        p=self.proposal();p['image_id']='wrong'
        self.assertTrue(validate_proposal(p,self.fixtures[0]['data'])[1])
        p=self.proposal();p['instances'][0]['technique_id']='T99'
        self.assertTrue(validate_proposal(p,self.fixtures[0]['data'])[1])

    def test_model_coordinates_never_become_verified_grounding(self):
        p=self.proposal();i=p['instances'][0]
        i.update(instance_id='T07-1',technique_id='T07',visual_contribution='REQUIRED',text_sufficient=False)
        i['evidence_channels'].append('NON_TEXT_VISUAL')
        i['visual_evidence']=[{'kind':'NON_TEXT_VISUAL','scope':'GLOBAL','description':'Synthetic distress paired with a call for support.','regions':None}]
        parsed,errors=validate_proposal(p,self.fixtures[0]['data'])
        self.assertFalse(errors)
        self.assertFalse(parsed['instances'][0]['visual_evidence'][0]['grounding_verified'])
        i['visual_evidence'][0]['box']=[0,0,1,1]
        self.assertTrue(validate_proposal(p,self.fixtures[0]['data'])[1])

    def test_manifest_mismatch_and_cancelled_decision_fail_export(self):
        task=deepcopy(self.manual[0]);task['annotations']=[{'result':self.fixtures[4]['result'],'was_cancelled':True}]
        task['data']['ocr_version']='stale'
        n=normalize_export([task],self.manifest)[0]
        self.assertFalse(n['valid'])
        self.assertTrue(n['cancelled'])

    def test_duplicate_ids_and_selection_fail_closed(self):
        with self.assertRaises(ValueError):indexed([{'image_id':'x'},{'image_id':'x'}])
        (ROOT/'.pilot-runtime').mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT/'.pilot-runtime') as temp:
            path=Path(temp)/'corrections.csv'
            rows=read_csv(ROOT/'ocr_corrected_20.csv')
            rows[1]['ocr_corrected']='#excluded'
            with path.open('w',encoding='utf-8',newline='') as f:
                writer=csv.DictWriter(f,fieldnames=['image_id','ocr_corrected']);writer.writeheader();writer.writerows(rows)
            output=Path(temp)/'pilot'
            with self.assertRaisesRegex(ValueError,'exactly 17'):
                build_pilot(corrected=path,output=output)
            self.assertFalse((output/'imports/manual.json').exists())

    def test_input_immutability(self):
        for path,digest in read_json(PILOT/'validation.json')['input_hashes'].items():
            self.assertEqual(sha((ROOT/path).read_bytes()),digest,path)

    def test_runner_sends_actual_images_and_audits_bounded_retry(self):
        from campnet_pilot.preannotate import main
        calls=[]
        class Reply:
            status_code=200
            def __init__(self,value):
                self.value=value;self.text=json.dumps(value)
            def raise_for_status(self):pass
            def json(self):return self.value
        class Session:
            headers={}
            def post(self,url,json=None,timeout=None):
                if url.endswith('/api/show'):
                    return Reply({'capabilities':['vision','completion']})
                calls.append(json)
                if len(calls)==1:
                    return Reply({'done':True,'message':{'content':'malformed JSON'}})
                supplied=__import__('json').loads(json['messages'][1]['content'].split('\n',1)[1])
                proposal={'image_id':supplied['image_id'],'status':'COMPLETE','instances':[],
                          'watchlist':[],'review_flags':[],'note':'SYNTHETIC MOCK RESPONSE ONLY'}
                return Reply({'done':True,'done_reason':'stop','model':'synthetic-test',
                              'message':{'content':__import__('json').dumps(proposal)}})
        with tempfile.TemporaryDirectory(dir=ROOT/'.pilot-runtime') as temp:
            output=Path(temp)/'pilot'
            (output/'imports').mkdir(parents=True);(output/'images').mkdir()
            shutil.copyfile(PILOT/'manifest.json',output/'manifest.json')
            shutil.copyfile(PILOT/'imports/manual.json',output/'imports/manual.json')
            for record in self.manifest:
                shutil.copyfile(PILOT/record['image_path'],output/record['image_path'])
            with patch('sys.argv',['runner','--pilot',str(output),'--model','synthetic-test','--retries','1']), \
                 patch('campnet_pilot.preannotate.requests.Session',Session),contextlib.redirect_stdout(io.StringIO()):
                main()
            latest=read_json(output/'preannotation/latest.json')
            self.assertEqual(latest['completed'],17)
            self.assertEqual(len(calls),18)
            manifest={r['image_id']:r for r in self.manifest}
            for call in calls:
                msg=call['messages'][1];supplied=json.loads(msg['content'].split('\n',1)[1])
                expected=manifest[supplied['image_id']]
                self.assertEqual(sha(base64.b64decode(msg['images'][0])),expected['image_sha256'])
                self.assertEqual(supplied['ocr'],expected['ocr'])
                self.assertNotIn('source_key',supplied)
            attempts=list((ROOT/latest['output']/'raw').glob('*.json'))
            self.assertEqual(len(attempts),18)
            self.assertTrue(any(read_json(p)['validation_errors'] for p in attempts))
            assisted=read_json(output/'imports/assisted.json')
            self.assertTrue(all(len(t['predictions'])==1 and 'annotations' not in t for t in assisted))


if __name__=='__main__':
    unittest.main(verbosity=2)
