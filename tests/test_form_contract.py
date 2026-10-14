"""Regression coverage for invisible required fields and lost evidence metadata."""
import unittest
from copy import deepcopy
from xml.etree.ElementTree import fromstring

from campnet_pilot.common import PILOT, read_json
from campnet_pilot.config import make_config, result_contract
from campnet_pilot.export import normalize_decision
from campnet_pilot.fixtures import area, cases
from campnet_pilot.labelstudio import control_signature


class FormContractTests(unittest.TestCase):
    def setUp(self):
        self.cases=cases(read_json(PILOT/'imports/manual.json')[0])

    def test_bundled_forms_match_generator_and_visible_control_names(self):
        for name,stage,assisted in [('stage_a_manual','A',False),('manual','B',False),('assisted','B',True)]:
            config=make_config(stage,assisted)
            self.assertEqual((PILOT/'config'/f'{name}.xml').read_text(encoding='utf-8'),config)
            tree=fromstring(config)
            controls={n.attrib['name']:n for n in tree.iter() if n.tag in ('Labels','RectangleLabels')}
            for view in tree.iter('View'):
                if view.attrib.get('visibleWhen')=='region-selected':
                    anchor=controls[view.attrib['whenTagName']]
                    for n in view.iter():
                        if n.attrib.get('perRegion')=='true':
                            self.assertEqual(n.attrib['toName'],anchor.attrib['toName'])
            if stage=='A':
                self.assertFalse(list(tree.iter('Image')))
            for node in tree.iter('TextArea'):
                self.assertEqual(node.attrib['transcription'],'true')
                self.assertEqual(node.attrib['showSubmitButton'],'false')

    def test_all_required_mark_fields_reported_together(self):
        c=deepcopy(self.cases[0])
        c['result']=[r for r in c['result'] if r['from_name'] not in ('ocr_instance','ocr_reason','ocr_confidence')]
        n=normalize_decision(c['data'],{'result':c['result']})
        self.assertFalse(n['valid'])
        errors=' '.join(n['validation_errors'])
        for text in ('claim number','reason','confidence'):
            self.assertIn(text,errors)
        self.assertEqual(n['evidence_region_count'],1)
        self.assertEqual(n['exported_region_count'],0)
        self.assertEqual(n['unexported_region_ids'],['T01-1-ocr'])

    def test_target_and_confidence_preserved_for_every_linked_mark(self):
        c=deepcopy(self.cases[2])
        c['result'] += [area('ocr_target','Named group','T07-1-ocr','ocr'),
                        area('visual_target','Depicted group','T07-1-visual','image')]
        next(r for r in c['result'] if r['from_name']=='visual_confidence')['value']['choices']=['2']
        n=normalize_decision(c['data'],{'result':c['result']})
        self.assertTrue(n['valid'],n['validation_errors'])
        text,picture=n['instances'][0]['evidence']
        self.assertEqual((text['target'],text['confidence']),('Named group',3))
        self.assertEqual((picture['target'],picture['confidence']),('Depicted group',2))
        self.assertEqual(n['evidence_region_count'],n['exported_region_count'])
        self.assertEqual(n['unexported_region_ids'],[])

    def test_invalid_quote_does_not_create_empty_instance(self):
        c=deepcopy(self.cases[0])
        next(r for r in c['result'] if r['type']=='labels')['value']['text']='invented'
        n=normalize_decision(c['data'],{'result':c['result']})
        self.assertFalse(n['valid'])
        self.assertEqual(n['instances'],[])
        self.assertEqual(n['unexported_region_ids'],['T01-1-ocr'])

    def test_wrong_field_target_type_unknown_entity_and_orphans_rejected(self):
        for mutation in ('target','type','unknown','orphan','malformed','option'):
            with self.subTest(mutation=mutation):
                c=deepcopy(self.cases[0])
                reason=next(r for r in c['result'] if r['from_name']=='ocr_reason')
                if mutation=='target':reason['to_name']='caption'
                if mutation=='type':reason['type']='choices'
                if mutation=='unknown':reason['from_name']='ocr_unrecognized'
                if mutation=='orphan':reason['id']='orphan-mark'
                if mutation=='malformed':reason['value']['text']='not a list'
                if mutation=='option':next(r for r in c['result'] if r['from_name']=='status')['value']['choices']=['MADE_UP']
                n=normalize_decision(c['data'],{'result':c['result']})
                self.assertFalse(n['valid'])
                self.assertEqual(n['raw_result'],c['result'])

    def test_contract_covers_all_expected_entities(self):
        contract=result_contract('B',True)
        expected={'techniques','no_technique','status','post_note','review_flags','watchlist','model_review'}
        for p in ('caption','ocr','visual'):
            expected.update(p+'_'+s for s in ('instance','reason','target','confidence','role','sufficient'))
        expected.update(('caption_spans','ocr_spans','visual_evidence','visual_kind','visual_scope'))
        self.assertEqual(set(contract),expected)

    def test_layout_update_signature_preserves_all_stored_entities(self):
        config=make_config('A')
        self.assertEqual(control_signature(config),control_signature(config.replace('Claim number *','Claim ID *')))
        self.assertNotEqual(control_signature(config),control_signature(config.replace('name="ocr_reason"','name="new_reason"')))


if __name__=='__main__':
    unittest.main()
