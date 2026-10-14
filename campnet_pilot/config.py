"""Single source for the pilot forms. Result names stay compatible with saved work."""
import argparse
from functools import lru_cache
from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, fromstring, indent, tostring
from .common import PILOT, TECHNIQUES, ROLES

GUIDE = {
    'T01': 'Emotional words add praise or blame beyond a plain description.',
    'T02': 'A judgmental name is given to a person or group.',
    'T03': 'An accusation or degrading connection attacks a reputation.',
    'T04': 'A threat or prejudice pushes the reader to support or reject something.',
    'T05': 'The message inflates or plays down scale, certainty, or importance. “All” alone is not enough.',
    'T06': 'A memorable phrase rallies support or action. A short sentence alone is not enough.',
    'T07': 'A picture creates strong emotion to support a position. Assess this only in Stage B.',
}
DISPLAY = {
    **{k: k+' · '+v for k,v in TECHNIQUES.items()},
    'COMPLETE': 'Complete — I can make a decision',
    'UNRESOLVED': 'Needs review — I am unsure',
    'EXCLUDE': 'Exclude — this item cannot be used',
    'No Propaganda Technique': 'No technique — I reviewed the whole item and found none',
    'NOT_USED': 'Not used — words provide the evidence',
    'REINFORCING': 'Adds support — words already support it',
    'REQUIRED': 'Needed — words alone do not support it',
    'true': 'Yes', 'false': 'No', 'unknown': 'Unsure',
    '1': '1 · Unsure', '2': '2 · Borderline, but supported', '3': '3 · Clear evidence',
    'NON_TEXT_VISUAL': 'Picture content: person, object, action, or symbol',
    'TYPOGRAPHY_LAYOUT': 'Text appearance: size, style, or layout',
    'LOCAL': 'This specific area', 'GLOBAL': 'The whole picture (box must cover it all)',
    'UNREADABLE_TEXT': 'Some words are unreadable', 'MISSING_CONTEXT': 'Important context is missing',
    'OCR_REVIEW': 'The copied image text may be wrong', 'ADJUDICATION': 'I need a reviewer',
    'UNCERTAIN_VISUAL_CONTRIBUTION': 'The picture’s contribution is unclear',
    'W01': 'W01 · Flag-waving / group identity', 'W02': 'W02 · Transfer',
    'W03': 'W03 · Glittering generalities / virtue', 'other_candidate': 'Another technique',
    'ACCEPTED': 'Accepted', 'EDITED': 'Changed it', 'REJECTED': 'Rejected it',
    'NOT_AVAILABLE': 'No suggestion was available',
}


def make_config(stage='B', assisted=False):
    if stage not in ('A','B') or (stage=='A' and assisted):
        raise ValueError('Use manual Stage A or manual/assisted Stage B')
    root = Element('View')
    SubElement(root, 'Style').text = '''
      .campnet {font-family:"Nirmala UI","Noto Sans Bengali",sans-serif; font-size:16px; line-height:1.55; color:#172b4d;}
      .campnet .content {display:flex; flex-wrap:wrap; gap:18px; align-items:flex-start;}
      .campnet .source {flex:2 1 420px; min-width:0;}
      .campnet .inspector {flex:1 1 310px; min-width:0; position:sticky; top:12px; padding:14px; border:2px solid #527db0; border-radius:8px; background:#f6f9ff;}
      .campnet .card {padding:14px; border:1px solid #d5deea; border-radius:8px; margin:12px 0; background:#fff;}
      .campnet .reading {padding:14px; border:1px solid #c6d2e2; border-radius:6px; font-size:20px; line-height:1.8; margin-top:10px; overflow-wrap:anywhere;}
      .campnet .hint {color:#52647c; margin:6px 0 12px;}
      .campnet .field {margin:12px 0;}
      .campnet .warning {padding:10px; background:#fff3d6; border-left:4px solid #cb8c13; margin:10px 0;}
      .campnet textarea {font-family:inherit; font-size:16px;}
      @media (max-width:1050px) {.campnet .inspector {position:static;}}
    '''
    page = SubElement(root, 'View', {'className': 'campnet'})
    def header(parent, text, size='4'):
        style = 'font-size:19px; font-weight:600; margin:0 0 8px;' if size!='5' else 'font-size:inherit; font-weight:400; line-height:inherit; margin:4px 0;'
        SubElement(parent, 'Header', value=text, size=size, style=style)
    def hint(parent, text):
        header(SubElement(parent,'View',className='hint'),text,'5')
    def field(parent, text):
        view=SubElement(parent,'View',className='field')
        header(view,text,'5')
        return view
    def choices(parent, name, target, values, multiple=False, per=False, required=False):
        attrs = dict(name=name, toName=target, choice='multiple' if multiple else 'single',
                     showInline='false')
        if per:
            attrs['perRegion'] = 'true'
        if required:
            attrs['required'] = 'true'
            attrs['requiredMessage'] = required if isinstance(required,str) else 'Complete '+name+' for the selected mark in Step 2.'
        control = SubElement(parent, 'Choices', attrs)
        for value in values:
            SubElement(control, 'Choice', value=value, html=DISPLAY.get(value,value))
    def area(parent, name, target, placeholder, per=False, required=False, rows='2'):
        attrs = dict(name=name,toName=target,rows=rows,placeholder=placeholder,
                     editable='true',transcription='true',maxSubmissions='1',showSubmitButton='false')
        if per:
            attrs['perRegion'] = 'true'
        if required:
            attrs['required'] = 'true'
            attrs['requiredMessage'] = required if isinstance(required,str) else 'Complete '+name+' for the selected mark in Step 2.'
        SubElement(parent, 'TextArea', attrs)
    def labels(parent, tag, name, target):
        control = SubElement(parent, tag, name=name, toName=target, choice='single')
        if tag=='RectangleLabels':
            control.set('canRotate','false')
        for (code, title),color in zip(TECHNIQUES.items(),('#dbeafe','#ede9fe','#fce7f3','#ffedd5','#fef3c7','#ccfbf1','#e2e8f0')):
            text=DISPLAY[code]+(' (Stage B only)' if stage=='A' and code=='T07' else '')
            SubElement(control, 'Label', value=code, html=text, hint=GUIDE[code], background=color)
    def details(parent, obj, prefix, visual=False):
        # LS 1.23.2 checks area.labeling.from_name.name: this must be the CONTROL,
        # not the object name. Using obj hides all required fields even on selection.
        anchor='visual_evidence' if visual else obj+'_spans'
        view = SubElement(parent, 'View', visibleWhen='region-selected', whenTagName=anchor, className='evidence', idAttr=prefix+'-details')
        title={'caption':'Caption highlight','ocr':'Image-text highlight','visual':'Picture box'}[prefix]
        header(view,title)
        hint(view,'These answers belong to the selected mark. Repeat for every mark. * = required.')
        prompt='Step 2 — '+title+': '
        area(field(view,'Why does this evidence fit the technique? *'),prefix+'_reason',obj,
             'These words / this picture use [technique] because…',True,prompt+'write a reason in the evidence panel.','3')
        choices(field(view,'How sure are you? *'),prefix+'_confidence',obj,['3','2','1'],per=True,
                required=prompt+'choose your confidence in the evidence panel.')
        area(field(view,'Claim number *'), prefix+'_instance', obj, 'Type 1 for the first claim', True,
             prompt+'enter a claim number (usually 1) in the evidence panel.', '1')
        hint(view,'Usually enter 1. Use 2 only for a separate claim of the SAME technique. Related marks use the same technique and number.')
        if stage == 'B':
            choices(field(view,'How does the picture help this claim? *'),prefix+'_role',obj,ROLES,per=True,required=prompt+'choose how the picture helps.')
            choices(field(view,'Do the words alone support this claim? *'),prefix+'_sufficient',obj,['true','false','unknown'],per=True,required=prompt+'answer whether words alone support the claim.')
            hint(view,'Not used / Adds support → Yes. Needed → No. Use the same answers for related marks.')
        if visual:
            choices(field(view,'What is inside the box? *'),prefix+'_kind',obj,['NON_TEXT_VISUAL','TYPOGRAPHY_LAYOUT'],per=True,required=prompt+'choose the kind of picture evidence.')
            choices(field(view,'How much of the picture matters? *'),prefix+'_scope',obj,['LOCAL','GLOBAL'],per=True,required=prompt+'choose a specific area or the whole picture.')
        area(field(view,'Who or what is targeted? (optional)'),prefix+'_target',obj,'Named person or group; leave blank if unknown',True,False,'1')
    header(page, 'CampNet · ' + ('Stage A: text only' if stage == 'A' else 'Stage B: full post'), '2')
    header(page,'1. Mark evidence → 2. Explain each mark → 3. Finish and Submit','5')
    hint(page,'Choose a technique, then drag over the supporting words. Click a mark to answer its questions. Write in Bangla or English.')
    if stage == 'A':
        hint(page,'Keep the image closed during Stage A. Judge persuasive use, not whether a claim is true.')
    else:
        hint(page,'Review the full post afresh. For picture evidence, draw the smallest useful box. Printed words are text evidence.')
    if assisted:
        header(page,'EXPERIMENTAL MODEL SUGGESTIONS — check, change, or reject them. These are not human labels.','4')
        SubElement(page,'Text',name='model_notice',value='$model_notice')
    guide=SubElement(SubElement(page,'Collapse'),'Panel',value='Technique guide — open when needed')
    for code,title in TECHNIQUES.items():
        header(guide,DISPLAY[code]+': '+GUIDE[code],'5')
    hint(guide,'Check whether the post supports, neutrally quotes, or rejects a message. Two techniques need two explanations, even when they use the same words.')
    content = SubElement(page,'View',{'className':'content'})
    text = SubElement(content,'View',{'className':'source'})
    header(text,'1. Read and mark the evidence')
    for obj, title in [('caption','Original post caption'),('ocr','Checked words inside the image')]:
        card=SubElement(text,'View',className='card')
        header(card,title)
        SubElement(card,'Text',name=obj+'_notice',value='$'+obj+'_notice')
        labels(card,'Labels',obj+'_spans',obj)
        reading=SubElement(card,'View',className='reading',idAttr=obj+'-reading')
        SubElement(reading,'Text',name=obj,value='$'+obj,granularity='symbol')
    if stage == 'B':
        image=SubElement(text,'View',className='card')
        header(image,'Picture')
        labels(image,'RectangleLabels','visual_evidence','image')
        SubElement(image,'Image',name='image',value='$image',zoom='true',zoomControl='true',rotateControl='false')
    inspector=SubElement(content,'View',className='inspector',idAttr='evidence-panel')
    header(inspector,'2. Explain the selected mark')
    empty=SubElement(inspector,'View',visibleWhen='no-region-selected')
    hint(empty,'Click a highlighted phrase or a box. Its questions appear here. You can also click it in the Regions list on the right.')
    details(inspector,'caption','caption')
    details(inspector,'ocr','ocr')
    if stage=='B':
        details(inspector,'image','visual',True)
    hint(inspector,'Type your answers directly. They are kept when you select another mark and saved with Submit.')
    finish=SubElement(page,'View',className='card')
    header(finish,'3. Finish the review')
    header(finish,'Tick the techniques used in your marks. This list is separate from highlighting.','5')
    choices(finish,'techniques','caption',list(TECHNIQUES),multiple=True)
    choices(finish,'no_technique','caption',['No Propaganda Technique'],multiple=True)
    hint(finish,'Choose techniques OR “No technique”. If unsure, choose “Needs review” below.')
    if stage=='A':
        warning=SubElement(finish,'View',visibleWhen='choice-selected',whenTagName='techniques',whenChoiceValue='T07',className='warning')
        header(warning,'T07 needs picture evidence. Remove it from Stage A and assess it in Stage B.','5')
    conflict=SubElement(finish,'View',visibleWhen='choice-selected',whenTagName='no_technique',whenChoiceValue='No Propaganda Technique')
    warning=SubElement(conflict,'View',visibleWhen='choice-selected',whenTagName='techniques',whenChoiceValue=','.join(TECHNIQUES),className='warning')
    header(warning,'You selected techniques and “No technique”. Clear the answer that does not apply.','5')
    choices(field(finish,'Review status *'),'status','caption',['COMPLETE','UNRESOLVED','EXCLUDE'],required='Step 3 — choose a review status.')
    area(field(finish,'Final note *'),'post_note','caption','Summarize your decision. If unsure, say what needs checking.',required='Step 3 — write a final note under Review status.')
    optional=SubElement(SubElement(finish,'Collapse'),'Panel',value='Optional: report a problem or another technique')
    choices(optional,'review_flags','caption',['UNREADABLE_TEXT','MISSING_CONTEXT','OCR_REVIEW','ADJUDICATION','UNCERTAIN_VISUAL_CONTRIBUTION'],multiple=True)
    choices(optional,'watchlist','caption',['W01','W02','W03','other_candidate'],multiple=True)
    hint(optional,'Explain any problem or additional technique in the final note. Do not open the image during Stage A to check OCR.')
    if assisted:
        choices(field(finish,'What did you do with the model suggestion? *'),'model_review','caption',['ACCEPTED','EDITED','REJECTED','NOT_AVAILABLE'],required='Step 3 — choose how you reviewed the model suggestion.')
    hint(finish,'Before Submit: each mark has a reason, confidence, and claim number; the technique list matches your marks; status and final note are filled in. A missing-field message names what to fix.')
    indent(root, space='  ')
    return tostring(root,encoding='unicode')+'\n'


def write_configs(output):
    output=Path(output)
    output.mkdir(parents=True,exist_ok=True)
    for name, stage, assisted in [('stage_a_manual','A',False),('manual','B',False),('assisted','B',True)]:
        (output/(name+'.xml')).write_text(make_config(stage,assisted),encoding='utf-8')


@lru_cache(maxsize=3)
def result_contract(stage, assisted=False):
    """Every form control and its serialized shape, used by the export validator."""
    controls={}
    for node in fromstring(make_config(stage,assisted)).iter():
        if node.tag not in ('Labels','RectangleLabels','Choices','TextArea'):
            continue
        controls[node.attrib['name']]={
            'type':node.tag.lower(), 'target':node.attrib['toName'],
            'per_region':node.attrib.get('perRegion')=='true' or node.tag in ('Labels','RectangleLabels'),
            'required':node.attrib.get('required')=='true',
            'message':node.attrib.get('requiredMessage'),
            'multiple':node.attrib.get('choice')=='multiple',
            'values':tuple(child.attrib['value'] for child in node if child.tag in ('Label','Choice')),
        }
    return controls


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=PILOT/'config')
    write_configs(parser.parse_args().output)
