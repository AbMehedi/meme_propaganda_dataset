"""Generate supported Label Studio controls, shared by tests and real projects."""
from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, indent, tostring
from .common import TECHNIQUES, ROLES


def make_config(stage='B', assisted=False):
    root = Element('View')
    SubElement(root, 'Style').text = '''
      .campnet {font-family: "Nirmala UI", "Noto Sans Bengali", sans-serif; font-size:17px; line-height:1.7;}
      .campnet .content {display:flex; flex-wrap:wrap; gap:24px; align-items:flex-start;}
      .campnet .pane {flex:1; min-width:340px; padding:16px; background:#f7f9fc; border-radius:8px;}
      .campnet .evidence {padding:16px; border:2px solid #aac4df; border-radius:8px; margin:16px 0;}
    '''
    page = SubElement(root, 'View', {'className': 'campnet'})
    def header(parent, text, size='4'):
        SubElement(parent, 'Header', value=text, size=size)
    def choices(parent, name, target, values, multiple=False, per=False, required=False):
        attrs = dict(name=name, toName=target, choice='multiple' if multiple else 'single',
                     showInline='true')
        if per:
            attrs['perRegion'] = 'true'
        if required:
            attrs['required'] = 'true'
        control = SubElement(parent, 'Choices', attrs)
        for value in values:
            SubElement(control, 'Choice', value=value)
    def area(parent, name, target, placeholder, per=False, required=False, rows='2'):
        attrs = dict(name=name,toName=target,rows=rows,placeholder=placeholder,
                     editable='true',maxSubmissions='1')
        if per:
            attrs['perRegion'] = 'true'
        if required:
            attrs['required'] = 'true'
        SubElement(parent, 'TextArea', attrs)
    def labels(parent, tag, name, target):
        control = SubElement(parent, tag, name=name, toName=target, choice='single')
        for code, title in TECHNIQUES.items():
            # Values stay stable IDs; label names and definitions appear in training material.
            SubElement(control, 'Label', value=code, hint=title)
    def details(parent, obj, prefix, visual=False):
        view = SubElement(parent, 'View', {'visibleWhen':'region-selected', 'whenTagName':obj, 'className':'evidence'})
        header(view, 'Explain the selected evidence')
        header(view, 'Instance number: use the same number for words and picture areas that support the same claim.', '5')
        area(view, prefix+'_instance', obj, '1 (use 2 for a separate claim of the same technique)', True, True, '1')
        header(view, 'Why does this evidence match the technique?', '5')
        area(view,prefix+'_reason',obj,'Describe the persuasive use. For combined evidence, explain how the words and picture work together.',True,True)
        header(view, 'Target named or depicted in this post (optional)', '5')
        area(view,prefix+'_target',obj,'Leave empty if the target is unknown.',True,False,'1')
        if stage == 'B':
            header(view,'Picture’s role for this technique instance','5')
            choices(view,prefix+'_role',obj,ROLES,per=True,required=True)
            header(view,'Can the words alone support this same instance?','5')
            choices(view,prefix+'_sufficient',obj,['true','false','unknown'],per=True,required=True)
        header(view,'Confidence: 1 = uncertain; 2 = borderline; 3 = clear evidence','5')
        choices(view,prefix+'_confidence',obj,['1','2','3'],per=True,required=True)
        if visual:
            header(view,'Kind of picture evidence','5')
            choices(view,prefix+'_kind',obj,['NON_TEXT_VISUAL','TYPOGRAPHY_LAYOUT'],per=True,required=True)
            header(view,'Area: choose GLOBAL only for whole-image composition; draw the full-image box and explain why.','5')
            choices(view,prefix+'_scope',obj,['LOCAL','GLOBAL'],per=True,required=True)
    header(page, 'CampNet — ' + ('read the text first' if stage == 'A' else 'review the full post'), '2')
    header(page,'Choose a technique only when you can point to evidence in this post. Highlight the words or mark the image area that supports your choice. Explain why it matches the technique.','5')
    if stage == 'A':
        header(page,'Save this decision before seeing the image. Do not change it later to match your full-post decision.','5')
    else:
        header(page,'Make a fresh decision. A famous face, flag, or emotional photograph needs a clear persuasive use. Use image zoom to inspect small details.','5')
    if assisted:
        header(page,'EXPERIMENTAL MODEL SUGGESTIONS — check, change, or reject them. These are not human labels.','4')
        SubElement(page,'Text',name='model_notice',value='$model_notice')
    content = SubElement(page,'View',{'className':'content'})
    if stage == 'B':
        image = SubElement(content,'View',{'className':'pane'})
        labels(image,'RectangleLabels','visual_evidence','image')
        SubElement(image,'Image',name='image',value='$image',zoom='true',zoomControl='true',rotateControl='false')
        details(image,'image','visual',True)
    text = SubElement(content,'View',{'className':'pane'})
    for obj, title in [('caption','Original post caption'),('ocr','Checked words inside the image')]:
        header(text,title)
        SubElement(text,'Text',name=obj+'_notice',value='$'+obj+'_notice')
        labels(text,'Labels',obj+'_spans',obj)
        SubElement(text,'Text',name=obj,value='$'+obj,granularity='symbol')
        details(text,obj,obj)
    header(page,'Techniques supported by the evidence')
    choices(page,'techniques','caption',list(TECHNIQUES),multiple=True)
    header(page,' | '.join(k+' — '+v for k,v in TECHNIQUES.items()),'5')
    header(page,'Is your decision complete?')
    choices(page,'status','caption',['COMPLETE','UNRESOLVED','EXCLUDE'],required=True)
    choices(page,'no_technique','caption',['No Propaganda Technique'],multiple=True)
    header(page,'Choose No Propaganda Technique only after complete review with no core technique selected. If you cannot decide, choose UNRESOLVED.','5')
    choices(page,'review_flags','caption',['UNREADABLE_TEXT','MISSING_CONTEXT','OCR_REVIEW','ADJUDICATION','UNCERTAIN_VISUAL_CONTRIBUTION'],multiple=True)
    choices(page,'watchlist','caption',['W01','W02','W03','other_candidate'],multiple=True)
    header(page,'Post note: explain none, missing information, uncertainty, quotation, satire, or watchlist evidence.','5')
    area(page,'post_note','caption','For unresolved or excluded posts, say why. For no technique, explain your decision.',required=True)
    if assisted:
        choices(page,'model_review','caption',['ACCEPTED','EDITED','REJECTED','NOT_AVAILABLE'],required=True)
    indent(root, space='  ')
    return tostring(root,encoding='unicode')+'\n'


def write_configs(output):
    output=Path(output)
    output.mkdir(parents=True,exist_ok=True)
    for name, stage, assisted in [('stage_a_manual','A',False),('manual','B',False),('assisted','B',True)]:
        (output/(name+'.xml')).write_text(make_config(stage,assisted),encoding='utf-8')
