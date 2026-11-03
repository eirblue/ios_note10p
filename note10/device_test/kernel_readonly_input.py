"""Distinct kernel-readonly candidate: offline preparation is not growth authorization."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import linux_data_carrier as data

KIND='kernel-readonly-candidate'
SCHEMA='n10-kernel-readonly-candidate-v1'
MODE='kernel-readonly-candidate-v1'
CAPACITY=4440064
ALIGN=16
DESCRIPTOR_BYTES=80
DESCRIPTOR_CLASS=2
BUDGET=59768832
MAGIC=b'N10KROINPUTV2!!!'
DESCRIPTOR=MAGIC+struct.pack('<IIQQ',2,80,CAPACITY,0)+bytes(40)
SLOT='n10_kernel_readonly_input'
DESC='n10_kernel_readonly_descriptor'
WORKFLOW='.github/workflows/note10-linux-data-carrier.yml'
SOURCES=('kernel_readonly_input.py','kernel_readonly_input.h','build_kernel_readonly_input.py',
    'kernel_readonly_input_fixture.c','test_v105_kernel_readonly.py')
API_PINS=data.API_PINS
PRODUCER_FIELDS=('data_input_kind','kernel_readonly_schema','kernel_readonly_slot','kernel_readonly_linked_bytes',
    'kernel_readonly_image_bytes','kernel_readonly_requires_ack')
COMPACT_FIELDS=('kernel_readonly_compact_sha256','kernel_readonly_compact_bytes','kernel_readonly_compact_manifest_sha256')
FIELDS=(*PRODUCER_FIELDS,*COMPACT_FIELDS)
OLD_BYTES=10962166
STREAM_BYTES=4437203
PAYLOAD_BYTES=19136512
COMPACT_SCHEMA='n10-kernel-readonly-compact-v1'
HISTORICAL_HEAD='e49ccf7fe46eb92b32c0b425a2e4da5fe667f9b4'
HISTORICAL_BUILDER_SHA256='64d5b765604bfe3f4df0869ab088345e6de461006e125f78933e53e04cc36983'
SPAN_KIND='kernel-readonly-span-pc'
SPAN_SCHEMA='n10-kernel-readonly-span-v1'
SPAN_SOURCES=('kernel_readonly_span.h','kernel_readonly_span_fixture.c','test_v106_kernel_readonly_span.py','build_kernel_readonly_span_pc.py')
PACKING_SCHEMA='n10-kernel-readonly-compact-external-v1'
PACKING_FIELDS=('kernel_readonly_packing_revision','kernel_readonly_external_choice','kernel_readonly_packing_host','kernel_readonly_reused_variant')
IO_EVENTS=[]


def event(operation,**counts):
    IO_EVENTS.append(dict(operation=operation,scope='named private input/Image I/O only; constant/source-code hashes and existing common gates are additional',**counts))


def install(source,identity):
    source=Path(source);original=(source/'arch/arm64/kernel/setup.c').read_bytes()
    result=data.install(source,identity)
    (source/'arch/arm64/kernel/setup.c').write_bytes(original)
    result['arch/arm64/kernel/setup.c']=data.sha(original)
    composition=(data.HERE/'linux_data_carrier_composition.c').read_bytes()
    old=b'#define N10_DATA_COMPARE_EVIDENCE 1'
    data.require(composition.count(old)==1,'unique candidate late composition required')
    composition=composition.replace(old,b'#ifdef CONFIG_NOTE10_KERNEL_READONLY_INPUT\n#define N10_DATA_KERNEL_READONLY 1\n#ifdef CONFIG_NOTE10_KERNEL_READONLY_SPAN_PC\n#define N10_DATA_KERNEL_SPAN_PC 1\n#endif\n#else\n'+old+b'\n#endif',1)
    config=source/'drivers/misc/note10_sha256_kat.Kconfig'
    config.write_bytes(config.read_bytes()+b'\nconfig NOTE10_KERNEL_READONLY_INPUT\n\tbool "Note10 kernel readonly candidate; new growth scope required"\n\tdepends on NOTE10_DATA_CARRIER\n\tdefault n\n\nconfig NOTE10_KERNEL_READONLY_SPAN_PC\n\tbool "Note10 PC-only logical kernel-span precondition"\n\tdepends on NOTE10_KERNEL_READONLY_INPUT\n\tdefault n\n')
    for name,raw in (('drivers/misc/note10_sha256_kat.c',composition),
        ('drivers/misc/kernel_readonly_input.h',(data.HERE/'kernel_readonly_input.h').read_bytes()),
        ('drivers/misc/kernel_readonly_span.h',(data.HERE/'kernel_readonly_span.h').read_bytes())):
        (source/name).write_bytes(raw);result[name]=data.sha(raw)
    result['drivers/misc/note10_sha256_kat.Kconfig']=data.sha(config.read_bytes())
    return result


def slot_metadata(raw,system_map,object_symbols,object_sections,object_table):
    data.require(type(raw) is bytes and raw.count(DESCRIPTOR)==1,'one exact generic readonly descriptor required')
    names={'_text','_end','__start_rodata','__init_begin',SLOT,DESC}
    values={}
    for line in system_map.splitlines():
        row=line.split()
        if len(row)==3 and row[2] in names:
            data.require(row[2] not in values,'duplicate readonly linked symbol')
            values[row[2]]=int(row[0],16)
    data.require(set(values)==names,'readonly linked symbol bounds missing')
    records={}
    for symbol,section,size in ((SLOT,'.rodata.n10_kernel_readonly_input',CAPACITY),
                                (DESC,'.rodata.n10_kernel_readonly_descriptor',DESCRIPTOR_BYTES)):
        symbols=[row for line in object_symbols.splitlines() if len(row:=line.split())==4 and row[3]==symbol]
        sections=re.findall(r'\[\s*(\d+)\]\s+'+re.escape(section)+r'\s+PROGBITS\s+[0-9a-fA-F]+\s+[0-9a-fA-F]+\s+([0-9a-fA-F]+)\s+\S+\s+([A-Za-z]+)\s+\d+\s+\d+\s+(\d+)',object_sections)
        table=[row for line in object_table.splitlines() if len(row:=line.split())==8 and row[7]==symbol]
        data.require(len(symbols)==len(sections)==len(table)==1 and int(symbols[0][1],16)==size and
            int(symbols[0][0],16)==0 and symbols[0][2].lower()=='r' and
            int(sections[0][1],16)==size and 'A' in sections[0][2] and
            not {'W','X'} & set(sections[0][2]) and int(sections[0][3])>=ALIGN and
            table[0][3:6]==['OBJECT','LOCAL','DEFAULT'] and table[0][6]==sections[0][0] and
            int(table[0][1],16)==0 and
            int(table[0][2],16 if table[0][2].startswith('0x') else 10)==size,'actual readonly nonexecuting compiler section required')
        start=values[symbol];offset=start-values['_text']
        data.require(start%ALIGN==0 and values['_text']<values['__start_rodata']<=start and
            start+size<=values['__init_begin']<=values['_end'] and 0<=offset<=len(raw)-size,
            'readonly linked/file extent differs')
        want=bytes(CAPACITY) if symbol==SLOT else DESCRIPTOR
        data.require(raw[offset:offset+size]==want,'generic readonly file preimage differs')
        records[symbol]=dict(symbol=symbol,section=section,offset=offset,bytes=size,
            alignment=ALIGN,readonly_flags=sections[0][2],preimage_sha256=data.sha(want),
            object_section_index=int(sections[0][0]),object_symbol_offset=0)
    a,b=records[SLOT],records[DESC]
    data.require(a['offset']+a['bytes']<=b['offset'] or b['offset']+b['bytes']<=a['offset'],
        'readonly descriptor/input overlap')
    return dict(schema=SCHEMA,source=MODE,capacity=CAPACITY,descriptor_bytes=DESCRIPTOR_BYTES,
        slot=a,descriptor=b,generic=True,patched=False,permanent_input_bytes=CAPACITY,
        permanent_descriptor_bytes=DESCRIPTOR_BYTES,physical_ready=False,descriptor_class=2,boot_page=2048)


def metadata_contract(slot,image_bytes):
    keys={'schema','source','capacity','descriptor_bytes','slot','descriptor','generic','patched',
        'permanent_input_bytes','permanent_descriptor_bytes','physical_ready','descriptor_class','boot_page'}
    data.require(type(slot) is dict and set(slot)==keys and slot['schema']==SCHEMA and
        slot['source']==MODE and type(slot['descriptor_class']) is int and slot['descriptor_class']==2 and
        type(slot['boot_page']) is int and slot['boot_page']==2048 and type(slot['capacity']) is int and slot['capacity']==CAPACITY and
        type(slot['descriptor_bytes']) is int and slot['descriptor_bytes']==80 and
        slot['generic'] is True and slot['patched'] is False and slot['physical_ready'] is False and
        slot['permanent_input_bytes']==CAPACITY and slot['permanent_descriptor_bytes']==80 and
        type(image_bytes) is int and image_bytes>CAPACITY+80,'closed generic kernel readonly slot metadata required')
    for key,symbol,section,size,preimage in (
        ('slot',SLOT,'.rodata.n10_kernel_readonly_input',CAPACITY,data.sha(bytes(CAPACITY))),
        ('descriptor',DESC,'.rodata.n10_kernel_readonly_descriptor',80,data.sha(DESCRIPTOR))):
        row=slot[key]
        data.require(type(row) is dict and set(row)=={'symbol','section','offset','bytes','alignment','readonly_flags','preimage_sha256','object_section_index','object_symbol_offset'} and
            row['symbol']==symbol and row['section']==section and type(row['bytes']) is int and row['bytes']==size and
            type(row['offset']) is int and row['offset']>=0 and row['offset']%ALIGN==0 and
            row['offset']+size<=image_bytes and type(row['alignment']) is int and row['alignment']==ALIGN and
            type(row['readonly_flags']) is str and 'A' in row['readonly_flags'] and
            not {'W','X'} & set(row['readonly_flags']) and row['preimage_sha256']==preimage and
            type(row['object_section_index']) is int and row['object_section_index']>0 and
            type(row['object_symbol_offset']) is int and row['object_symbol_offset']==0,
            'closed candidate readonly extent provenance differs')
    a,b=slot['slot'],slot['descriptor']
    data.require(a['offset']+a['bytes']<=b['offset'] or b['offset']+b['bytes']<=a['offset'],
        'candidate readonly metadata overlap')
    return True




def producer_contract(result,source,*,producing_sources=None,historical_origin=None):
    ci=result.get('ci_context',{})
    if historical_origin is not None:
        data.require(historical_origin==source==HISTORICAL_HEAD and producing_sources is None,'exact retained readonly origin only')
        from sha256_kat_device_profile import V105_CANDIDATE_ORIGIN_PINS
        producing_sources={key:value for key,value in V105_CANDIDATE_ORIGIN_PINS.items() if key in
            {'note10/device_test/'+name for name in (*SOURCES,'linux_data_carrier.c','linux_data_carrier_composition.c','build_builtin_init_image.py')}}
        # Exact e49 builder pin from the already authenticated accepted CI
        # source closure, outside profile56. New live builders stay strict.
        producing_sources['note10/device_test/build_builtin_init_image.py']=HISTORICAL_BUILDER_SHA256
    else:
        data.require(source!=HISTORICAL_HEAD,'retained candidate cannot construct a new producer')
    pins=producing_sources if producing_sources is not None else {
        'note10/device_test/'+name:data.sha((data.HERE/name).read_bytes()) for name in
        (*SOURCES,'linux_data_carrier.c','linux_data_carrier_composition.c','build_builtin_init_image.py')}
    metadata_contract(result.get('kernel_readonly_slot'),result.get('image_bytes'))
    span=result.get('data_footprint',{}).get('linked_kernel_bytes')
    data.require(result.get('version')=='v105' and result.get('diagnostic_kind')==KIND and
        result.get('data_input_kind')==KIND and result.get('kernel_readonly_schema')==SCHEMA and
        result.get('kernel_readonly_requires_ack') is True and result.get('kernel_readonly_default_enabled') is False and
        result.get('passed') is True and result.get('Image_built') is True and result.get('BOOT_built') is False and
        result.get('PC_only') is False and result.get('physical_ready') is False and result.get('deployment_ready') is False and
        result.get('device_authorized') is False and result.get('device_operations')==[] and
        result.get('data_expectation_mode')==MODE and result.get('data_expectation_slot')==result.get('kernel_readonly_slot') and
        result.get('image_expectation_patched') is False and
        result.get('external_initrd_capture') is False and result.get('input_capture_source')=='late-kernel-readonly-class2' and
        result.get('permanent_input_storage_bytes')==CAPACITY and result.get('permanent_descriptor_bytes')==80 and
        type(span) is int and 0<span<=BUDGET and result.get('kernel_readonly_linked_bytes')==span and
        result.get('kernel_readonly_image_bytes')==result.get('image_bytes') and
        type(result.get('data_footprint',{}).get('data_state_bytes')) is int and 0<result['data_footprint']['data_state_bytes']<=128 and
        result.get('settings',{}).get('NOTE10_KERNEL_READONLY_INPUT')=='y' and
        result.get('settings',{}).get('NOTE10_KERNEL_READONLY_SPAN_PC')!='y' and
        all(result.get('settings',{}).get(key)=='n' for key in
            ('NOTE10_READONLY_INPUT_PC','NOTE10_OWNED_CONTIGUOUS_STAGING','NOTE10_CURRENT_OWNED_STAGING')) and
        not any(key in result for key in ('readonly_input_schema','readonly_input_slot','readonly_pc_contract',
            'data_compare_schema','data_input_range_schema','data_early_prefix_schema','kernel_readonly_span_schema',*data.GROWTH_FIELDS)) and
        re.fullmatch('[0-9a-f]{40}',source or '') and source!='e32ec501551b74b4cca5618ea25245f012656f29' and ci.get('GITHUB_SHA')==ci.get('GITHUB_WORKFLOW_SHA')==source and
        ci.get('GITHUB_JOB')=='linux-data-carrier' and ci.get('GITHUB_REPOSITORY')=='eirblue/ios_note10p' and
        ci.get('GITHUB_WORKFLOW_REF')=='eirblue/ios_note10p/'+WORKFLOW+'@refs/heads/main' and
        all(re.fullmatch('[1-9][0-9]*',ci.get(key,'') or '') for key in ('GITHUB_RUN_ID','GITHUB_RUN_ATTEMPT')) and
        type(pins) is dict and all(result.get('source_sha256',{}).get(key)==value and re.fullmatch('[0-9a-f]{64}',value or '')
            for key,value in pins.items()) and all('note10/device_test/'+name in pins for name in
            (*SOURCES,'linux_data_carrier.c','linux_data_carrier_composition.c','build_builtin_init_image.py')),
        'distinct generic kernel-readonly candidate/source/budget required')
    return dict(candidate_only=True,physical_ready=False,requires_new_kernel_growth_scope=True,
        global_RAM_ownership=False,hardware_mapping_attested=False,linked_budget=BUDGET)



def span_footprint(system_map,footprint,slot,*,slot_symbol=SLOT,descriptor_symbol=DESC):
    names={'_text','_stext','_end',slot_symbol,descriptor_symbol};values={}
    for line in system_map.splitlines():
        row=line.split()
        if len(row)==3 and row[2] in names:
            data.require(row[2] not in values,'duplicate PC span symbol')
            values[row[2]]=int(row[0],16)
    data.require(set(values)==names,'PC span symbols missing')
    text,start,end=values['_text'],values['_stext'],values['_end']
    data.require(0<text<=start<end and end-text==footprint['linked_kernel_bytes']<=BUDGET,
        'PC span linked domain differs')
    for key,symbol in (('slot',slot_symbol),('descriptor',descriptor_symbol)):
        extent=slot[key]
        data.require(values[symbol]==text+extent['offset'] and start<=values[symbol] and
            values[symbol]+extent['bytes']<=end,'PC span full linked containment differs')
    return dict(schema=SPAN_SCHEMA,kernel_bytes=end-start,text_prefix_bytes=start-text,
        slot_contained=True,descriptor_contained=True,disjoint=True,
        source='linked-kernel',phase='pre_descriptor',hardware=False,ownership=False)


def span_producer_contract(result,source,*,producing_sources=None):
    required=(*SOURCES,*SPAN_SOURCES,'linux_data_carrier.c','linux_data_carrier_composition.c','build_builtin_init_image.py')
    pins=producing_sources if producing_sources is not None else {
        'note10/device_test/'+name:data.sha((data.HERE/name).read_bytes()) for name in required}
    metadata_contract(result.get('kernel_readonly_slot'),result.get('image_bytes'))
    ci=result.get('ci_context',{});footprint=result.get('data_footprint',{});span=result.get('kernel_readonly_span',{})
    data.require(type(span) is dict and set(span)=={'schema','kernel_bytes','text_prefix_bytes','slot_contained',
        'descriptor_contained','disjoint','source','phase','hardware','ownership'} and span['schema']==SPAN_SCHEMA and
        type(span['kernel_bytes']) is int and 0<span['kernel_bytes']<=BUDGET and
        type(span['text_prefix_bytes']) is int and span['text_prefix_bytes']>=0 and
        span['kernel_bytes']+span['text_prefix_bytes']==footprint.get('linked_kernel_bytes') and
        all(span[key] is True for key in ('slot_contained','descriptor_contained','disjoint')) and
        span['hardware'] is False and span['ownership'] is False and span['source']=='linked-kernel' and
        span['phase']=='pre_descriptor','closed new PC linked span metadata required')
    linked=footprint.get('linked_kernel_bytes')
    data.require(result.get('version')=='v106' and result.get('diagnostic_kind')==SPAN_KIND and
        result.get('data_input_kind')==KIND and result.get('kernel_readonly_schema')==SCHEMA and
        result.get('kernel_readonly_span_schema')==SPAN_SCHEMA and result.get('kernel_readonly_span_default_enabled') is False and
        result.get('kernel_readonly_default_enabled') is False and result.get('kernel_readonly_requires_ack') is True and
        result.get('passed') is True and result.get('Image_built') is True and result.get('BOOT_built') is False and
        result.get('PC_only') is True and result.get('physical_ready') is False and result.get('deployment_ready') is False and
        result.get('device_authorized') is False and result.get('device_operations')==[] and
        result.get('data_expectation_mode')==MODE and result.get('data_expectation_slot')==result['kernel_readonly_slot'] and
        result.get('image_expectation_patched') is False and result.get('external_initrd_capture') is False and
        result.get('input_capture_source')=='late-kernel-readonly-class2' and
        result.get('permanent_input_storage_bytes')==CAPACITY and result.get('permanent_descriptor_bytes')==80 and
        result.get('additional_linked_storage_bytes')==CAPACITY+80 and type(linked) is int and 0<linked<=BUDGET and
        result.get('kernel_readonly_linked_bytes')==linked and result.get('kernel_readonly_image_bytes')==result.get('image_bytes') and
        type(footprint.get('data_state_bytes')) is int and 0<footprint['data_state_bytes']<=128 and
        all(result.get('settings',{}).get(key)=='y' for key in ('NOTE10_KERNEL_READONLY_INPUT','NOTE10_KERNEL_READONLY_SPAN_PC')) and
        all(result.get('settings',{}).get(key)=='n' for key in ('NOTE10_READONLY_INPUT_PC','NOTE10_OWNED_CONTIGUOUS_STAGING','NOTE10_CURRENT_OWNED_STAGING')) and
        not any(key in result for key in ('readonly_input_schema','readonly_input_slot','readonly_pc_contract',
            'data_compare_schema','data_input_range_schema','data_early_prefix_schema',*data.GROWTH_FIELDS)) and
        re.fullmatch('[0-9a-f]{40}',source or '') and source!=HISTORICAL_HEAD and
        ci.get('GITHUB_SHA')==ci.get('GITHUB_WORKFLOW_SHA')==source and ci.get('GITHUB_JOB')=='linux-data-carrier' and
        ci.get('GITHUB_REPOSITORY')=='eirblue/ios_note10p' and
        ci.get('GITHUB_WORKFLOW_REF')=='eirblue/ios_note10p/'+WORKFLOW+'@refs/heads/main' and
        all(re.fullmatch('[1-9][0-9]*',ci.get(key,'') or '') for key in ('GITHUB_RUN_ID','GITHUB_RUN_ATTEMPT')) and
        type(pins) is dict and all('note10/device_test/'+name in pins for name in required) and
        all(re.fullmatch('[0-9a-f]{64}',value or '') and result.get('source_sha256',{}).get(key)==value for key,value in pins.items()),
        'distinct new PC span producer/source required')
    for key in ('slot','descriptor'):
        extent=result['kernel_readonly_slot'][key]
        data.require(span['text_prefix_bytes']<=extent['offset'] and extent['offset']+extent['bytes']<=linked,
            'PC span slot metadata differs')
    return dict(PC_only=True,physical_ready=False,logical_source_only=True,hardware_mapping_attested=False,
        global_RAM_ownership=False,linked_budget=BUDGET,span_scalar_bytes=16,outcome_bytes=128,
        permanent_metadata_bytes=footprint['data_state_bytes'],additional_readonly_storage_bytes=CAPACITY+80)


SPAN_KEYS=('id','cycle','kind','source','phase','state','attempted','kernel_checked','kernel_bytes',
    'extents_checked','slot_contained','descriptor_contained','disjoint','admission_called','reasons','ownership','hardware','executed')


def decode_span(text,identity,cycle,boot,expected_kernel_bytes):
    from decode_reservation import checksum
    data.require(type(expected_kernel_bytes) is int and 0<expected_kernel_bytes<=BUDGET,'bound PC span length required')
    selected=[]
    for line in text.splitlines():
        if 'N10DATASPAN' not in line:continue
        match=re.fullmatch(r'.*?N10BOOTLINK2 boot=([0-9a-f]{32}) N10DATASPAN1 (.+) checksum=([0-9a-f]{8})',line)
        data.require(match is not None,'malformed PC span frame')
        observed,body,digest=match.groups()
        data.require(observed==boot and len(body.encode('ascii'))<=415 and checksum(body.encode('ascii'))==int(digest,16),'PC span frame binding differs')
        tokens=body.split(' ')
        data.require(len(tokens)==len(SPAN_KEYS) and all(token.count('=')==1 for token in tokens),'closed PC span fields required')
        row=dict(token.split('=') for token in tokens)
        data.require(tuple(row)==SPAN_KEYS and row['id']==identity and row['cycle']==cycle and row['kind']=='span' and
            row['source']=='linked-kernel' and row['phase']=='pre_descriptor' and
            row['ownership']==row['hardware']==row['executed']=='0' and re.fullmatch('[0-9a-f]{8}',row['reasons']),
            'PC span scalar domain differs')
        reasons=int(row['reasons'],16)
        data.require(all(row[key] in ('0','1') for key in ('attempted','kernel_checked','extents_checked','admission_called')) and
            all(row[key] in ('0','1','na') for key in ('slot_contained','descriptor_contained','disjoint')),
            'PC span flags differ')
        kernel_checked=row['kernel_checked']=='1';extents=row['extents_checked']=='1'
        if kernel_checked:
            data.require(re.fullmatch('[1-9][0-9]*',row['kernel_bytes']) and int(row['kernel_bytes'])==expected_kernel_bytes,'PC span linked length differs')
        else:data.require(row['kernel_bytes']=='na' and not extents,'PC span unavailable length differs')
        if row['state']=='checked':
            data.require(reasons==0 and all(row[key]=='1' for key in ('attempted','kernel_checked','extents_checked','slot_contained','descriptor_contained','disjoint','admission_called')),'PC span checked flags differ')
        elif row['state']=='not_reached':
            data.require(reasons==1 and not kernel_checked and all(row[key]=='0' for key in ('attempted','extents_checked','admission_called')) and
                all(row[key]=='na' for key in ('slot_contained','descriptor_contained','disjoint')),'PC span not-reached flags differ')
        elif row['state']=='refused':
            data.require(row['attempted']=='1' and row['admission_called']=='0','PC span refused attempt differs')
            if not kernel_checked:data.require(reasons in (2,64),'PC span kernel refusal differs')
            elif not extents:data.require(reasons in (4,8,128),'PC span extent refusal differs')
            else:
                data.require(all(row[key] in ('0','1') for key in ('slot_contained','descriptor_contained','disjoint')),'PC span checked extents missing')
                want=(16 if row['slot_contained']=='0' or row['descriptor_contained']=='0' else 0)|(32 if row['disjoint']=='0' else 0)
                data.require(reasons==want and want!=0,'PC span relation refusal differs')
            if not extents:data.require(all(row[key]=='na' for key in ('slot_contained','descriptor_contained','disjoint')),'PC span unavailable relation differs')
        else:data.require(False,'unknown PC span state')
        selected.append(dict(row,boot_identity=observed,kernel_bytes=int(row['kernel_bytes']) if kernel_checked else None,
            reasons=reasons,logical_source_only=True,hardware_mapping_attested=False,global_RAM_ownership=False))
    data.require(len(selected)==1,'exactly one PC span companion required')
    return selected[0]


def decode_span_selected(raw,banner,identity,cycle,*,expected):
    from builtin_init_profile import decode as baseline_decode
    span_producer_contract(expected,expected.get('ci_context',{}).get('GITHUB_SHA'))
    bound=expected['kernel_readonly_span']['kernel_bytes']
    components=dict(pid1_validation='not_checked',return_validation='not_checked',return_boot_association='not_checked',
        functional_acceptance=False,hardware_return_proven_by_frames=False)
    def selected(text,rid):
        row=data.decode(text,rid,cycle,_source_class=MODE)
        components['kernel_readonly_data']=row;components['data_phase']=data.functional_phase(row['status'])
        components['structural_presence']=data.structural_presence(text,rid,cycle,row['boot_identity'])
        data.require(not any(marker in text for marker in ('N10DATA1 ','N10DATAPC','N10DATACMP','N10DATARANGE','N10DATAEARLY','N10DATAGROWTH')),
            'PC span cannot claim external or other PC companions')
        components['kernel_readonly_span']=decode_span(text,rid,cycle,row['boot_identity'],bound)
        data.require(row['carrier']==CAPACITY and row['logical'] in (0,CAPACITY),'PC readonly extent differs')
        data.require(False,'PC-only span observation cannot authorize functional or physical acceptance')
    try:
        baseline_decode(raw,banner,identity,cycle,digest_decoder=selected,digest_marker=b'N10DATARO1',component_evidence=components)
    except ValueError as error:
        raise data.ComponentObservationError(error,components) from error
    raise ValueError('PC-only span observation cannot be accepted')

def input_binding(result,lines,*,elf,archive,raw_inputs,historical_origin=None):
    from early_fdt_binding import fixed_route_relation
    producer_contract(result,result.get('ci_context',{}).get('GITHUB_SHA'),historical_origin=historical_origin)
    data.require('CONFIG_NOTE10_KERNEL_READONLY_INPUT=y' in lines and
        not {'CONFIG_NOTE10_READONLY_INPUT_PC=y','CONFIG_NOTE10_OWNED_CONTIGUOUS_STAGING=y',
             'CONFIG_NOTE10_CURRENT_OWNED_STAGING=y'} & set(lines),'distinct readonly source configuration required')
    fixed_route_relation(elf,archive,result,raw_inputs)
    return dict(data_carrier_stage=data.STAGE,data_relative_placement_admitted=False,raw_input_binding=False,
        data_expectation_mode=MODE,data_expectation_slot=result['kernel_readonly_slot'],image_expectation_patched=False,
        **{key:result[key] for key in PRODUCER_FIELDS})


def is_candidate(row):
    return row.get('data_input_kind')==KIND or row.get('diagnostic_kind')==KIND or row.get('data_expectation_mode')==MODE or any(key in row for key in (*FIELDS,*PACKING_FIELDS))


def candidate_scope(row,*,require_compact=True):
    metadata_contract(row.get('kernel_readonly_slot'),row.get('kernel_readonly_image_bytes'))
    data.require(row.get('device_profile')==data.PROFILE and row.get('data_input_kind')==KIND and row.get('kernel_readonly_schema')==SCHEMA and
        row.get('data_expectation_mode')==MODE and row.get('data_expectation_slot')==row.get('kernel_readonly_slot') and
        row.get('kernel_readonly_requires_ack') is True and
        row.get('source_head')!='e32ec501551b74b4cca5618ea25245f012656f29' and
        row.get('host_profile_source_head')!='e32ec501551b74b4cca5618ea25245f012656f29' and type(row.get('kernel_readonly_linked_bytes')) is int and
        0<row['kernel_readonly_linked_bytes']<=BUDGET and row.get('data_carrier_stage')==data.STAGE and
        row.get('data_relative_placement_admitted') is False and row.get('raw_input_binding') is False and
        type(row.get('image_expectation_patched')) is bool and not any(key in row for key in
            ('readonly_input_schema','readonly_input_slot','readonly_pc_contract','data_compare_schema',
             'data_input_range_schema','data_linked_kernel_bytes','data_early_prefix_schema','kernel_readonly_span_schema',*data.GROWTH_FIELDS)),
        'closed kernel-readonly profile/source class required')
    if require_compact:
        data.require(row.get('kernel_readonly_compact_bytes')==CAPACITY and
            all(re.fullmatch('[0-9a-f]{64}',row.get(key,'') or '') and row[key]!='0'*64 for key in
                ('kernel_readonly_compact_sha256','kernel_readonly_compact_manifest_sha256')),
            'authenticated compact candidate identity required')
    packing_scope(row)
    return True


def require_device_scope(row,ack_kernel_readonly_growth=False,type3_context=None):
    from class3_native_origin import stage_selected
    if stage_selected(row):
        from type3_admission import require_device_scope
        return require_device_scope(row,ack_kernel_readonly_growth,type3_context)
    from readonly_stage_witness import refuse
    refuse(row)
    # The original PC domain remains forbidden even when candidate flags/ACK are forged.
    data.require(row.get('PC_only') is not True and row.get('data_expectation_mode')!='kernel-readonly-slot-v1' and row.get('version')!='v103' and row.get('diagnostic_kind') not in
        ('readonly-input-pc','owned-contiguous-staging-pc','current-owned-staging-pc',SPAN_KIND) and not any(key in row for key in
        ('readonly_input_schema','readonly_input_slot','readonly_pc_contract','kernel_readonly_span_schema')),'PC-only source is permanently forbidden on device')
    from kernel_readonly_span_candidate import is_candidate as is_type3, require_device_scope as require_type3
    if is_type3(row):return require_type3(row,ack_kernel_readonly_growth,type3_context)
    if is_candidate(row):
        data.require(row.get('device_profile')==data.PROFILE and row.get('data_input_kind')==KIND and row.get('kernel_readonly_schema')==SCHEMA and
            row.get('data_expectation_mode')==MODE and row.get('kernel_readonly_requires_ack') is True and
            row.get('kernel_readonly_slot',{}).get('descriptor_class')==2 and
            row.get('kernel_readonly_slot',{}).get('schema')==SCHEMA,
            'explicit new readonly source class required before device scope')
        data.require(ack_kernel_readonly_growth is True,
            'new kernel RAM growth scope requires --ack-kernel-readonly-growth before any device query/action')
    return True


def compact_bytes(raw):
    data.require(type(raw) is bytes and len(raw)==OLD_BYTES and raw[:8]==b'N10DATA1' and
        struct.unpack_from('<HHI',raw,8)==(1,128,0) and struct.unpack_from('<QQQQ',raw,16)==
        (OLD_BYTES,128,STREAM_BYTES,PAYLOAD_BYTES) and raw[112:128]==bytes(16) and
        raw[128]==0x5d and struct.unpack_from('<IQ',raw,129)==(1<<23,PAYLOAD_BYTES) and
        raw[128+STREAM_BYTES:]==bytes(OLD_BYTES-128-STREAM_BYTES),'fixed retained container/header/zero padding required')
    stream=raw[128:128+STREAM_BYTES]
    data.require(data.sha(stream)==raw[48:80].hex() and raw[80:112]!=bytes(32),'retained stream/payload digest fields required')
    # No compression, decoder or payload materialization. Logical field16 only.
    header=raw[:16]+CAPACITY.to_bytes(8,'little')+raw[24:128]
    return header+stream+bytes(CAPACITY-128-STREAM_BYTES)


def compact_metadata(raw,source_fields):
    return dict(schema=COMPACT_SCHEMA,source_manifest_sha256=source_fields['data_manifest_sha256'],
        source_carrier_sha256=source_fields['data_carrier_sha256'],source_carrier_bytes=OLD_BYTES,
        compact_sha256=data.sha(raw),compact_bytes=CAPACITY,stream_bytes=STREAM_BYTES,stream_sha256=raw[48:80].hex(),
        payload_bytes=PAYLOAD_BYTES,payload_sha256=raw[80:112].hex(),header_bytes=128,zero_padding_bytes=2733,
        decoder_calls=0,recompressions=0,device_operations=[],physical_ready=False)


def validate_compact(raw,manifest_raw,source_fields=None):
    data.require(type(raw) is bytes and len(raw)==CAPACITY and type(manifest_raw) is bytes and
        0<len(manifest_raw)<=65536,'bounded compact bytes/manifest required')
    meta=json.loads(manifest_raw)
    keys={'schema','source_manifest_sha256','source_carrier_sha256','source_carrier_bytes','compact_sha256','compact_bytes',
        'stream_bytes','stream_sha256','payload_bytes','payload_sha256','header_bytes','zero_padding_bytes','decoder_calls',
        'recompressions','device_operations','physical_ready'}
    data.require(type(meta) is dict and set(meta)==keys and meta['schema']==COMPACT_SCHEMA and
        re.fullmatch('[0-9a-f]{64}',meta.get('source_manifest_sha256','')) and meta['source_carrier_bytes']==OLD_BYTES and
        re.fullmatch('[0-9a-f]{64}',meta.get('source_carrier_sha256','')) and
        all(type(meta[key]) is int for key in ('source_carrier_bytes','compact_bytes','stream_bytes','payload_bytes',
            'header_bytes','zero_padding_bytes','decoder_calls','recompressions')) and
        meta['compact_bytes']==len(raw)==CAPACITY and meta['compact_sha256']==data.sha(raw) and
        meta['stream_bytes']==STREAM_BYTES and meta['payload_bytes']==PAYLOAD_BYTES and meta['header_bytes']==128 and
        meta['zero_padding_bytes']==2733 and meta['decoder_calls']==meta['recompressions']==0 and
        meta['device_operations']==[] and meta['physical_ready'] is False and raw[:8]==b'N10DATA1' and
        struct.unpack_from('<HHI',raw,8)==(1,128,0) and struct.unpack_from('<QQQQ',raw,16)==
        (CAPACITY,128,STREAM_BYTES,PAYLOAD_BYTES) and raw[112:128]==bytes(16) and raw[128]==0x5d and
        struct.unpack_from('<IQ',raw,129)==(1<<23,PAYLOAD_BYTES) and
        raw[128+STREAM_BYTES:]==bytes(2733) and data.sha(raw[128:128+STREAM_BYTES])==meta['stream_sha256']==raw[48:80].hex() and
        meta['payload_sha256']==raw[80:112].hex() and re.fullmatch('[0-9a-f]{64}',meta['payload_sha256']) and
        meta['payload_sha256']!='0'*64,'closed compact derivative differs')
    if source_fields is not None:
        data.require(meta['source_manifest_sha256']==source_fields['data_manifest_sha256'] and
            meta['source_carrier_sha256']==source_fields['data_carrier_sha256'] and
            meta['payload_sha256']==source_fields['data_payload_sha256'] and
            source_fields['data_carrier_bytes']==OLD_BYTES and source_fields['data_payload_bytes']==PAYLOAD_BYTES,
            'compact derivative and unchanged external carrier differ')
    return dict(kernel_readonly_compact_sha256=meta['compact_sha256'],kernel_readonly_compact_bytes=CAPACITY,
        kernel_readonly_compact_manifest_sha256=data.sha(manifest_raw))


def derive(source_manifest,expected,output):
    from sha256_kat_device_profile import private
    source_manifest=private(source_manifest);output=private(output)
    data.require(re.fullmatch('[0-9a-f]{64}',expected or '') and source_manifest.name=='carrier-manifest.json' and not output.exists(),
        'exact retained source manifest and fresh offline derivative output required')
    manifest_raw=data.bounded_private_read(source_manifest,2*1024*1024)
    data.require(data.sha(manifest_raw)==expected,'retained reviewed manifest pin differs')
    raw=data.bounded_private_read(source_manifest.parent/'carrier.data',OLD_BYTES)
    fields=data.private_input_record(manifest_raw,raw)
    data.require(fields['data_manifest_sha256']==expected and fields['data_carrier_bytes']==OLD_BYTES and
        fields['data_payload_bytes']==PAYLOAD_BYTES,'retained v95 source tuple required')
    compact=compact_bytes(raw);meta=compact_metadata(compact,fields)
    data.require(meta['payload_sha256']==fields['data_payload_sha256'],'preserved payload digest differs')
    output.mkdir(parents=True)
    compact_manifest=(json.dumps(meta,sort_keys=True,indent=2)+'\n').encode()
    (output/'kernel-readonly.data').write_bytes(compact)
    (output/'compact-manifest.json').write_bytes(compact_manifest)
    event('one_compact_derivation',source_file_reads=2,source_bytes_read=len(raw)+len(manifest_raw),
        source_manifest_hashes=2,source_full_carrier_hashes=2,stream_hashes=1,new_compact_hashes=1,new_compact_manifest_hashes=1,
        compact_files_written=1,compact_bytes_written=CAPACITY,metadata_files_written=2,logical_header_copy_bytes=128,
        logical_stream_copy_bytes=STREAM_BYTES,zero_padding_emitted=2733,decoder_calls=0,recompressions=0,
        note='Logical copy sizes, not a claim about internal Python memcpy counts; JSON result/manifest writes are additional metadata I/O')
    result=dict(fields,compact_manifest=str(output/'compact-manifest.json'),
        compact_manifest_sha256=data.sha(compact_manifest),compact_metadata=meta,
        schema='v105-offline-compact-transaction-v1',IO_events=list(IO_EVENTS),physical_operations=[])
    (output/'derive-result.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


def attach_compact(root,manifest_path,expected,source_fields):
    from sha256_kat_device_profile import private
    root=private(root);manifest_path=private(manifest_path)
    data.require(manifest_path.name=='compact-manifest.json' and re.fullmatch('[0-9a-f]{64}',expected or ''),'exact compact manifest pin required')
    meta=data.bounded_private_read(manifest_path,65536);data.require(data.sha(meta)==expected,'compact manifest changed')
    raw=data.bounded_private_read(manifest_path.parent/'kernel-readonly.data',CAPACITY)
    fields=validate_compact(raw,meta,source_fields)
    for name,value in (('kernel-readonly.data',raw),('kernel-readonly-compact.json',meta)):
        with (root/name).open('xb') as target:target.write(value)
    event('attach_compact',file_reads=2,bytes_read=len(raw)+len(meta),compact_hashes=1,stream_hashes=1,
        manifest_hashes=2,files_copied=2,bytes_written=len(raw)+len(meta),decoder_calls=0)
    return fields


def read_compact(root,source_fields):
    root=Path(root)
    meta=data.bounded_private_read(root/'kernel-readonly-compact.json',65536)
    raw=data.bounded_private_read(root/'kernel-readonly.data',CAPACITY)
    fields=validate_compact(raw,meta,source_fields)
    event('intrinsic_compact_validation',file_reads=2,bytes_read=len(raw)+len(meta),compact_hashes=1,stream_hashes=1,manifest_hashes=1,decoder_calls=0)
    return raw,fields


def compact_fields(root,source_fields):
    return read_compact(root,source_fields)[1]


def patch_image(raw,report,token,cycle_slot,compact):
    candidate_scope(report)
    data.require(report.get('image_expectation_patched') is False and report.get('image_sha256')==data.sha(raw) and
        len(raw)==report['kernel_readonly_image_bytes'] and len(compact)==CAPACITY and
        data.sha(compact)==report['kernel_readonly_compact_sha256'],'generic Image and compact identity required')
    record=report['kernel_readonly_slot'];slot=record['slot'];desc=record['descriptor']
    data.require(raw.count(DESCRIPTOR)==1 and raw[desc['offset']:desc['offset']+80]==DESCRIPTOR and
        raw[slot['offset']:slot['offset']+CAPACITY]==bytes(CAPACITY) and type(cycle_slot) is bytes and len(cycle_slot)==32 and
        raw.count(cycle_slot+b'\0')==1 and re.fullmatch('[0-9a-f]{32}',token or ''),'exact new class generic preimages/cycle required')
    cycle=raw.index(cycle_slot+b'\0')
    data.require(all(cycle+32<=part['offset'] or part['offset']+part['bytes']<=cycle for part in (slot,desc)),
        'readonly input/descriptor/cycle extents must be disjoint')
    result=bytearray(raw)
    result[slot['offset']:slot['offset']+CAPACITY]=compact
    result[desc['offset']+32:desc['offset']+72]=CAPACITY.to_bytes(8,'little')+bytes.fromhex(report['kernel_readonly_compact_sha256'])
    result[cycle:cycle+32]=token.encode('ascii')
    data.require(len(result)==len(raw),'fixed Image length required')
    event('pure_intrinsic_Image_patch',generic_image_hashes=1,compact_hashes=1,input_slot_bytes=CAPACITY,
        descriptor_expected_logical_bytes=40,cycle_bytes=32,file_writes=0,
        note='Caller performs the necessary variant write; validation may repeat pure expected-byte construction without another derivation')
    return bytes(result)


def decode_selected(raw,banner,identity,cycle,*,expected):
    from builtin_init_profile import decode as baseline_decode
    candidate_scope(expected)
    data.require(expected.get('image_expectation_patched') is True,'runtime requires the intrinsically patched readonly variant')
    components=dict(pid1_validation='not_checked',return_validation='not_checked',return_boot_association='not_checked',
        functional_acceptance=False,hardware_return_proven_by_frames=False)
    def selected(text,rid):
        data.require(not any(marker in text for marker in ('N10DATA1 ','N10DATAPC','N10DATACMP','N10DATARANGE','N10DATAEARLY','N10DATAGROWTH')),
            'readonly candidate cannot claim external/PC probe companions')
        row=data.decode(text,rid,cycle,_source_class=MODE)
        components['kernel_readonly_data']=row;components['data_phase']=data.functional_phase(row['status'])
        components['structural_presence']=data.structural_presence(text,rid,cycle,row['boot_identity'])
        data.require(row['carrier']==CAPACITY and row['logical'] in (0,CAPACITY),'fixed readonly extent required')
        data.require_functional(row,report_phase=True)
        data.require(row['logical']==expected['kernel_readonly_compact_bytes'] and
            row['payload']==row['written']==expected['data_payload_bytes'] and row['digest']==expected['data_payload_sha256'],
            'readonly decoded package identity differs')
        return row
    try:
        clipped,observed=baseline_decode(raw,banner,identity,cycle,digest_decoder=selected,digest_marker=b'N10DATARO1',component_evidence=components)
        data.require(observed['kat']['boot_identity']==observed['boot_identity'],'readonly recovery/PID1 boot differs')
    except ValueError as error:
        raise data.ComponentObservationError(error,components) from error
    return clipped,observed


def packing_scope(row):
    present=any(key in row for key in PACKING_FIELDS)
    if not present:return None
    from sha256_kat_device_profile import packing_host_origin
    data.require(all(key in row for key in PACKING_FIELDS) and row['kernel_readonly_packing_revision']==PACKING_SCHEMA and
        row['kernel_readonly_external_choice']=='compact-v1' and row.get('source_head')==HISTORICAL_HEAD and
        row.get('host_profile_source_head')==HISTORICAL_HEAD,'exact retained class2 compact-external revision required')
    host=row['kernel_readonly_packing_host'];reuse=row['kernel_readonly_reused_variant']
    data.require(type(host) is dict and set(host)=={'host_profile_source_head','host_profile_source_sha256'} and
        host==packing_host_origin(host),'new or authenticated retained packing host identity differs')
    keys={'template','template_profile_sha256','source_variant','source_report_sha256','source_image_sha256','cycle',
          'operator_receipt','operator_receipt_sha256'}
    data.require(type(reuse) is dict and set(reuse)==keys and re.fullmatch('[0-9a-f]{32}',reuse.get('cycle','')) and
        all(re.fullmatch('[0-9a-f]{64}',reuse.get(key,'')) for key in
            ('template_profile_sha256','source_report_sha256','source_image_sha256','operator_receipt_sha256')),
        'closed retained materialization pins required')
    return dict(choice='compact-v1',old_external_bytes=OLD_BYTES,new_external_bytes=CAPACITY,
        external_sha256=row['kernel_readonly_compact_sha256'],encoding='N10DATA1-raw',addresses_or_flags_changed=False)


def read_external(root,row):
    if row.get('kernel_readonly_external_choice')=='compact-v1':
        packing_scope(row)
        raw,fields=read_compact(root,row)
        data.require(fields=={key:row[key] for key in COMPACT_FIELDS},'compact external input differs')
        return raw
    return data.bounded_private_read(Path(root)/'carrier.data',64*1024*1024)


def reuse_metadata(generic,original,operator,reuse,template_report_sha256):
    data.require(generic.get('source_head')==generic.get('host_profile_source_head')==HISTORICAL_HEAD and
        generic.get('data_input_kind')==KIND and generic.get('image_expectation_patched') is False,
        'frozen generic e49 candidate required')
    cycle=reuse['cycle']
    expected=dict(generic,auto_cycle_variant=True,auto_cycle_token=cycle,auto_cycle_template=reuse['template'],
        auto_cycle_template_report_sha256=template_report_sha256,auto_cycle_template_image_sha256=generic['image_sha256'],
        image_sha256=reuse['source_image_sha256'],image_expectation_patched=True)
    data.require(original==expected,'retained materialization report differs outside original patches')
    data.require(operator.get('schema')=='v105-offline-preparation-operator-receipt-v1' and
        operator.get('status')=='stopped_on_plan_prepare_failure' and operator.get('source_head')==HISTORICAL_HEAD and
        operator.get('template',{}).get('exit_code')==0 and operator['template'].get('invocation_count')==1 and
        operator['template'].get('path')==reuse['template'] and operator['template'].get('build_result_sha256')==template_report_sha256 and
        operator.get('plan',{}).get('exit_code')==1 and operator['plan'].get('invocation_count')==1 and
        operator['plan'].get('exact_failure')=='Prototype exceeds actual boot partition' and
        operator['plan'].get('plan_json_exists') is False and operator['plan'].get('partial_cycle_packages_exist') is False,
        'exact unfinished packing failure authority required')
    return expected


def authenticate_reuse(reuse):
    from sha256_kat_device_profile import private,read,sha,validate_template
    template=private(reuse['template']);source=private(reuse['source_variant']);receipt=private(reuse['operator_receipt'])
    data.require(source.name=='kernel-build' and source.parent.name=='cycle-01' and
        not (source.parent.parent/'plan.json').exists() and not (source.parent/'boot.img').exists() and
        not (source.parent/'packages').exists(),'only unfinished original packing may resume')
    data.require(sha(template/'device-profile.json')==reuse['template_profile_sha256'] and
        sha(source/'build-result.json')==reuse['source_report_sha256'] and sha(receipt)==reuse['operator_receipt_sha256'],
        'reviewed frozen template/report/operator pins differ')
    validate_template(template)
    generic=read(template/'build-result.json');original=read(source/'build-result.json');operator=read(receipt)
    original_root=Path(operator['plan']['output_directory'])
    if not original_root.is_absolute():original_root=data.HERE.parents[1]/original_root
    data.require(private(original_root)==source.parent.parent,'failed plan origin path differs')
    reuse_metadata(generic,original,operator,reuse,sha(template/'build-result.json'))
    data.require(sha(source/'Image')==reuse['source_image_sha256'] and
        sha(source/'handoff.config')==original['effective_config_sha256'],'already-materialized Image/config changed')
    event('authenticate_completed_materialization',materialized_Image_hashes=1,materialize_calls=0,repatch_calls=0,
        note='Template validation keeps its existing intrinsic I/O; no expected patched Image is reconstructed')
    return original


def validate_resumed_variant(root,token,template=None):
    from sha256_kat_device_profile import private,read,sha
    root=private(root);report=read(root/'build-result.json');candidate_scope(report)
    reuse=report['kernel_readonly_reused_variant']
    data.require(token==reuse['cycle'] and (template is None or private(template)==private(reuse['template'])),
        'resumed cycle/template binding differs')
    original=authenticate_reuse(reuse)
    expected=dict(original,**{key:report[key] for key in PACKING_FIELDS})
    data.require(report==expected and sha(root/'Image')==reuse['source_image_sha256'] and
        sha(root/'handoff.config')==original['effective_config_sha256'],'resumed wrapper changed immutable kernel/config/report')
    fields=compact_fields(root,report)
    data.require(fields=={key:report[key] for key in COMPACT_FIELDS},'resumed compact input changed')
    return report


def resume_pack(*,template,template_profile_sha256,materialized,materialized_report_sha256,materialized_image_sha256,
    operator_receipt,operator_receipt_sha256,backup,twrp,mkbootimg,current_packages,output,host_source_head):
    import shutil
    from sha256_kat_device_profile import private,read,sha,host_binding,save,validate_plan
    from prepare_linux_boot import prepare
    from build_boot_test_packages import build
    from stage_phase2 import verify_packages
    template=private(template);materialized=private(materialized);output=private(output);backup=private(backup)
    current_packages=private(current_packages)
    data.require(not output.exists() and not output.is_relative_to(materialized.parent.parent) and
        not output.is_relative_to(template) and not output.is_relative_to(materialized) and
        not template.is_relative_to(output) and not materialized.is_relative_to(output),'fresh disjoint revision output required')
    source=read(materialized/'build-result.json')
    reuse=dict(template=str(template),template_profile_sha256=template_profile_sha256,source_variant=str(materialized),
        source_report_sha256=materialized_report_sha256,source_image_sha256=materialized_image_sha256,
        cycle=source.get('auto_cycle_token'),operator_receipt=str(private(operator_receipt)),operator_receipt_sha256=operator_receipt_sha256)
    original=authenticate_reuse(reuse)
    packing_host=host_binding(host_source_head)
    records=verify_packages(current_packages);current=next(row for row in records if row['mode']=='diagnostic')
    revision=dict(zip(PACKING_FIELDS,(PACKING_SCHEMA,'compact-v1',packing_host,reuse)))
    report=dict(original,**revision);candidate_scope(report)
    output.mkdir(parents=True);folder=output/'cycle-01';folder.mkdir();target=folder/'kernel-build';target.mkdir()
    # Bit-identical copies only. No template creation, materialize(), patch_image(),
    # derivation, compression, decoder, archive replay or original-directory write.
    for name in ('Image','handoff.config','kernel-readonly.data','kernel-readonly-compact.json'):
        shutil.copyfile(materialized/name,target/name)
    save(target/'build-result.json',report)
    boot=folder/'boot.img';prepare(backup,target,Path(twrp),Path(mkbootimg),boot,reuse['cycle'])
    packages=folder/'packages';build(backup,boot,packages,current_packages)
    generic=read(template/'build-result.json')
    stage=dict(index=1,cycle=reuse['cycle'],kernel_build=str(target),image_sha256=original['image_sha256'],
        build_result_sha256=sha(target/'build-result.json'),packages=str(packages),package_result_sha256=sha(packages/'package-result.json'))
    plan=dict(schema=1,kind='note10-bounded-auto-cycle',device_profile=generic['device_profile'],kernel_build=str(template),backup=str(backup),
        backup_manifest_sha256=sha(backup/'backup-manifest.json'),build_result_sha256=sha(template/'build-result.json'),
        image_sha256=generic['image_sha256'],identity=generic['build_evidence_id'],current_packages=str(current_packages),
        current_package_result_sha256=sha(current_packages/'package-result.json'),reference_twrp=str(Path(twrp).resolve()),
        mkbootimg=str(Path(mkbootimg).resolve()),minimum_battery=10,return_timeout_seconds=240,stages=[stage],
        current_boot_payload_sha256=current['payload_sha256'],**revision)
    save(output/'plan.json',plan);validate_plan(output/'plan.json',sha(output/'plan.json'))
    event('resume_unfinished_packing',new_derivations=0,new_templates=0,new_materializations=0,new_repatches=0,
        immutable_files_copied=4,BOOT_packings=1,package_pair_builds=1,device_queries=0)
    return dict(plan=str(output/'plan.json'),plan_sha256=sha(output/'plan.json'),external_choice=packing_scope(report),
        native_source_head=HISTORICAL_HEAD,original_profile_host_head=HISTORICAL_HEAD,executing_host=packing_host,
        materialized_Image_sha256=materialized_image_sha256,IO_events=list(IO_EVENTS),device_operations=[],physical_scope_pending=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='command',required=True)
    d=sub.add_parser('derive');d.add_argument('--source-manifest',type=Path,required=True)
    d.add_argument('--source-manifest-sha256',required=True);d.add_argument('--output',type=Path,required=True)
    r=sub.add_parser('resume-pack')
    for key in ('template','materialized','operator-receipt','backup','twrp','mkbootimg','current-packages','output'):
        r.add_argument('--'+key,type=Path,required=True)
    for key in ('template-profile-sha256','materialized-report-sha256','materialized-image-sha256','operator-receipt-sha256','host-source-head'):
        r.add_argument('--'+key,required=True)
    args=vars(parser.parse_args());command=args.pop('command')
    if command=='derive':result=derive(args['source_manifest'],args['source_manifest_sha256'],args['output'])
    else:result=resume_pack(**args)
    print(json.dumps(result,indent=2))
