"""PC-first class3 stage witness; no offline or device admission is provided."""
from pathlib import Path
import re
import kernel_readonly_span_candidate as ro3
import linux_data_carrier as data

KIND='kernel-readonly-stage-witness-candidate'
SCHEMA='n10-readonly-stage-witness-candidate-v1'
WIRE_SCHEMA='readonly-stage-witness-v1'
SELECTOR='v109-readonly-stage-witness-pc'
SOURCES=('readonly_stage_witness.py','readonly_stage_witness.h','readonly_stage_witness_fixture.c',
    'test_v109_readonly_stage_witness.py','retained_v108_origin.py')
EVENTS=('header_enter','header_ok','decode_called','decode_returned','api_ok','length_enter','length_ok',
    'hash_called','hash_returned','digest_enter','digest_ok','work_clear_called','work_clear_returned',
    'work_free_called','work_free_returned','output_clear_called','output_clear_returned','output_free_called',
    'output_free_returned','stream_ok')
ALL=(1<<len(EVENTS))-1
API_PINS=ro3.API_PINS

def selected(row):
    return any(row.get(key)==KIND for key in ('diagnostic_kind','data_input_kind','storage_input_kind')) or 'readonly_stage_schema' in row

def refuse(row):
    data.require(not selected(row),'new stage-witness candidate has no current offline/device admission')

def install(source,identity):
    result=ro3.install(source,identity);source=Path(source)
    target=source/'drivers/misc/note10_sha256_kat.c';raw=target.read_bytes()
    match=b'#define N10_DATA_KERNEL_READONLY_V3 1'
    data.require(raw.count(match)==1,'one class3 stage-witness route required')
    raw=raw.replace(match,match+b'\n#define N10_DATA_STAGE_WITNESS 1',1);target.write_bytes(raw)
    result['drivers/misc/note10_sha256_kat.c']=data.sha(raw)
    raw=(data.HERE/'readonly_stage_witness.h').read_bytes()
    (source/'drivers/misc/readonly_stage_witness.h').write_bytes(raw)
    result['drivers/misc/readonly_stage_witness.h']=data.sha(raw)
    return result

def decode(text,identity,cycle,*,expected_schema):
    from decode_reservation import checksum
    data.require(expected_schema==SCHEMA,'explicit new stage producer schema required')
    legacy=data.decode(text,identity,cycle,_source_class=ro3.MODE)
    lines=[line for line in text.splitlines() if 'N10DATASTAGE1' in line]
    data.require(len(lines)==1,'one stage companion required')
    match=re.search(r'N10BOOTLINK2 boot=([0-9a-f]{32}) N10DATASTAGE1 ([^\r\n\x00]{1,447}) checksum=([0-9a-f]{8})$',lines[0])
    data.require(match is not None and match[1]==legacy['boot_identity'] and
        checksum(match[2].encode('ascii'))==int(match[3],16),'stage boot/checksum differs')
    expected=f'id={identity} cycle={cycle} kind=stages schema={WIRE_SCHEMA} bits='
    data.require(match[2].startswith(expected),'stage identity/schema differs')
    suffix=match[2][len(expected):]
    fields=re.fullmatch(r'([0-9a-f]{8}) work_cleanup=(not_called|void_returned) output_cleanup=(not_called|void_returned) ownership=0 hardware=0 executed=0',suffix)
    data.require(fields is not None,'closed bounded stage companion required')
    text_cleanup=dict(work=fields[2],output=fields[3])
    bits=int(fields[1],16);data.require(not bits&~ALL,'unknown stage bits')
    flags={name:bool(bits&(1<<index)) for index,name in enumerate(EVENTS)}
    def implies(a,b):data.require(not flags[a] or flags[b],'contradictory stage sequence')
    for a,b in (('header_ok','header_enter'),('stream_ok','header_ok'),('decode_called','stream_ok'),
        ('api_ok','decode_returned'),('length_ok','length_enter'),('digest_enter','hash_returned'),('digest_ok','digest_enter')):
        implies(a,b)
    for a,b in (('decode_called','decode_returned'),('length_enter','api_ok'),('hash_called','length_ok'),('hash_returned','hash_called')):
        data.require(flags[a]==flags[b],'incomplete returned stage sequence')
    for resource in ('work','output'):
        for op in ('clear','free'):
            data.require(flags[f'{resource}_{op}_called']==flags[f'{resource}_{op}_returned'],'incomplete void cleanup call')
        implies(f'{resource}_free_called',f'{resource}_clear_returned')
        data.require(flags[f'{resource}_clear_called']==flags[f'{resource}_free_called'],'incomplete class3 cleanup')
        implies(f'{resource}_clear_called','stream_ok')
        implies('decode_called',f'{resource}_free_returned')
    data.require(legacy['calls']==int(flags['decode_called']),'stage/legacy decoder call differs')
    data.require(not flags['header_ok'] or legacy['stream']>0 and legacy['payload']>0,'stage/header counts differ')
    data.require(flags['header_enter']==(legacy['status'] in ('header','stream_hash','allocation','decode','payload_hash','ok')),
        'stage/legacy header phase differs')
    phase=legacy['status']
    if phase in ('unavailable','carrier_crypto','carrier_mismatch'):data.require(bits==0,'unreached stage evidence differs')
    elif phase=='header':data.require(not flags['header_ok'],'failed header cannot be accepted')
    elif phase=='stream_hash':data.require(flags['header_ok'] and not flags['stream_ok'],'failed stream evidence differs')
    elif phase=='allocation':data.require(flags['stream_ok'] and not flags['decode_called'],'allocation stage evidence differs')
    elif phase=='decode':data.require(flags['decode_called'] and not flags['length_ok'],'failed decode evidence differs')
    elif phase=='payload_hash':data.require(flags['length_ok'] and not flags['digest_ok'],'failed digest evidence differs')
    else:data.require(phase=='ok','unknown stage phase')
    data.require(flags['digest_ok']==(legacy['status']=='ok') and (legacy['status']!='ok' or bits==ALL and legacy['passed']),
        'stage/legacy successful outcome differs')
    cleanup={resource:'void_returned' if flags[f'{resource}_free_returned'] else 'not_called' for resource in ('work','output')}
    data.require(text_cleanup==cleanup,'stage textual cleanup contradicts call boundaries')
    return dict(schema=SCHEMA,boot_identity=match[1],bits=bits,events=flags,passed=bits==ALL,
        cleanup_result=cleanup,cleanup_semantics='void_call_boundaries_only',input_retained=legacy['retained'],global_RAM_ownership=False,
        hardware=False,xnu_executed=False)
