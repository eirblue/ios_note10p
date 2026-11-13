"""Six new pure source/object/Image join predicates; no binary input reads."""
from copy import deepcopy
import struct


def run(p):
    record=dict(name='preempt_schedule',kind='T',address=0x1000,bytes=8,ordinal=10)
    target=dict(name='preempt_schedule_common',kind='t',address=0x1010,bytes=4,ordinal=11)
    function=dict(name=record['name'],section=2,value=0,bytes=8,data=struct.pack('<II',0xd503201f,0x94000000).hex(),relocations=[dict(offset=4,type=283,addend=0,target=dict(name=target['name'],type=2,section=2,value=16,bytes=4))])
    original=struct.pack('<II',0xd503201f,0x94000003);frame=dict(bytes=16,kind='static');records=[record,target]
    wrong_relocation=deepcopy(function);wrong_relocation['relocations'][0]['type']=257
    cases=[('valid-body-relocation-static-SU',function,original,record,frame,True),
        ('wrong-original-nm-ordinal',function,original,{**record,'ordinal':99},frame,False),
        ('nonrelocation-byte-mismatch',function,b'\0'*4+original[4:],record,frame,False),
        ('relocated-target-mismatch',function,original[:4]+struct.pack('<I',0x94000004),record,frame,False),
        ('dynamic-SU',function,original,record,{**frame,'kind':'dynamic'},False),
        ('unknown-relocation',wrong_relocation,original,record,frame,False)]
    progress=dict(groups=1,variants=6,assertions=6,attempted_variants=0,completed_variants=0,completed_assertions=0,host_processes=0,old_tests_replayed=0,case_names=[])
    try:
        for index,(name,item,body,symbol,usage,accepted)in enumerate(cases,1):
            progress.update(attempted_variants=index,failing_case_index=index,failing_case_name=name)
            try:proof=p.join_function(item,body,symbol,records,0x1000,usage)
            except ValueError:
                if accepted:raise
            else:
                if not accepted or proof['machine_body_equivalent']is not True:raise AssertionError('wrong join acceptance')
            progress['completed_variants']+=1;progress['completed_assertions']+=1;progress['case_names'].append(name)
        progress.update(failing_case_index=None,failing_case_name=None);return progress
    except BaseException as error:error.fixture_progress=progress;raise
