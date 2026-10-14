"""Synthetic software checks only. Never use these examples as research annotations."""
from copy import deepcopy
from .common import sha, cp_to_utf16


def choice(name,values,rid=None,target='caption'):
    return {'id':rid or name,'from_name':name,'to_name':target,'type':'choices','value':{'choices':values}}


def area(name,text,rid=None,target='caption'):
    return {'id':rid or name,'from_name':name,'to_name':target,'type':'textarea','value':{'text':[text]}}


def evidence(data,code='T01',quote='ঘৃণ্য',channel='ocr',number='1',role='NOT_USED',sufficient='true',visual=False,global_scope=False):
    prefix='visual' if visual else channel
    target='image' if visual else channel
    rid=f'{code}-{number}-{prefix}'
    reason='SYNTHETIC CHECK: observable evidence supports this fictional technique instance.'
    if visual:
        anchor={'id':rid,'from_name':'visual_evidence','to_name':'image','type':'rectanglelabels',
                'original_width':data['width'],'original_height':data['height'],'image_rotation':0,
                'value':{'x':0 if global_scope else 10,'y':0 if global_scope else 10,
                         'width':100 if global_scope else 30,'height':100 if global_scope else 40,
                         'rotation':0,'rectanglelabels':[code]}}
    else:
        start=data[channel].index(quote)
        anchor={'id':rid,'from_name':channel+'_spans','to_name':channel,'type':'labels',
                'value':{'start':cp_to_utf16(data[channel],start),
                         'end':cp_to_utf16(data[channel],start+len(quote)), 'text':quote,'labels':[code]}}
    result=[anchor,area(prefix+'_instance',number,rid,target),area(prefix+'_reason',reason,rid,target),
            choice(prefix+'_confidence',['3'],rid,target)]
    if data['stage']=='B':
        result += [choice(prefix+'_role',[role],rid,target),choice(prefix+'_sufficient',[sufficient],rid,target)]
    if visual:
        result += [choice('visual_kind',['NON_TEXT_VISUAL'],rid,target),
                   choice('visual_scope',['GLOBAL' if global_scope else 'LOCAL'],rid,target)]
    return result


def base_result(labels,status='COMPLETE',assisted=False):
    result=[choice('techniques',labels),choice('status',[status]),
            area('post_note','SYNTHETIC SOFTWARE CHECK ONLY: made-up evidence, not a human research annotation.')]
    if not labels and status=='COMPLETE':
        result.append(choice('no_technique',['No Propaganda Technique']))
    if status=='UNRESOLVED':
        result.append(choice('review_flags',['UNREADABLE_TEXT','ADJUDICATION']))
    if assisted:
        result.append(choice('model_review',['ACCEPTED']))
    return result


def cases(template):
    result=[]
    for i,name in enumerate(['text_only','visual','combined','multiple','none','unreadable','whole_image','repeated_instance']):
        data=deepcopy(template['data'])
        data.update(task_id='SYNTHETIC-'+name,image_id='SYNTHETIC-'+name,post_id='SYNTHETIC-'+name,
                    ocr='😀 এই ঘৃণ্য সিদ্ধান্ত। জাতির শত্রু। অন্যায় রুখে দাঁড়াও!',caption='Fictional software check only.',
                    ocr_version='synthetic-v1',synthetic=True)
        data['ocr_sha256']=sha(data['ocr']);data['caption_sha256']=sha(data['caption'])
        ev=[];labels=[];status='COMPLETE'
        if name=='text_only':
            labels=['T01'];ev=evidence(data)
        elif name in ('visual','whole_image'):
            labels=['T03'];ev=evidence(data,'T03',visual=True,role='REQUIRED',sufficient='false',global_scope=name=='whole_image')
        elif name=='combined':
            labels=['T07'];ev=evidence(data,'T07',role='REQUIRED',sufficient='false')+evidence(data,'T07',visual=True,role='REQUIRED',sufficient='false')
        elif name=='multiple':
            labels=['T01','T02'];ev=evidence(data)+evidence(data,'T02',quote='জাতির শত্রু')
        elif name=='unreadable':
            status='UNRESOLVED'
        elif name=='repeated_instance':
            labels=['T01'];ev=evidence(data)+evidence(data,quote='সিদ্ধান্ত',number='2')
        result.append({'name':name,'data':data,'result':base_result(labels,status)+ev})
    return result
