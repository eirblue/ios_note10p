"""Distinct type3 readonly span candidate. This first-use revision is PC only."""
import re
import struct
from pathlib import Path
import linux_data_carrier as data
import kernel_readonly_input as old

KIND='kernel-readonly-span-candidate'
SCHEMA='n10-kernel-readonly-span-candidate-v1'
MODE='kernel-readonly-span-candidate-v1'
CAPACITY=4440064
ALIGN=16
DESCRIPTOR_BYTES=80
BUDGET=59768832
MAGIC=b'N10KROINPUTV3!!!'
DESCRIPTOR=MAGIC+struct.pack('<IIQQ',3,80,CAPACITY,0)+bytes(40)
SLOT='n10_kernel_readonly3_input'
DESC='n10_kernel_readonly3_descriptor'
WORKFLOW=old.WORKFLOW
API_PINS=data.API_PINS
SOURCES=('kernel_readonly_span_candidate.py','kernel_readonly_span_candidate.h',
    'kernel_readonly_span_candidate_fixture.c','test_v107_readonly_span_candidate.py','build_kernel_readonly_span_candidate.py')
FIELDS=('kernel_readonly3_schema','kernel_readonly3_slot','kernel_readonly3_span_schema','kernel_readonly3_span',
    'kernel_readonly3_linked_bytes','kernel_readonly3_image_bytes','kernel_readonly3_requires_ack','kernel_readonly3_marker')


def install(source,identity):
    source=Path(source);original=(source/'arch/arm64/kernel/setup.c').read_bytes()
    result=data.install(source,identity)
    (source/'arch/arm64/kernel/setup.c').write_bytes(original)
    result['arch/arm64/kernel/setup.c']=data.sha(original)
    composition=(data.HERE/'linux_data_carrier_composition.c').read_bytes()
    match=b'#define N10_DATA_COMPARE_EVIDENCE 1'
    data.require(composition.count(match)==1,'unique type3 late composition required')
    composition=composition.replace(match,b'#ifdef CONFIG_NOTE10_KERNEL_READONLY_SPAN_CANDIDATE\n#define N10_DATA_KERNEL_READONLY 1\n#define N10_DATA_KERNEL_READONLY_V3 1\n#else\n'+match+b'\n#endif',1)
    config=source/'drivers/misc/note10_sha256_kat.Kconfig'
    config.write_bytes(config.read_bytes()+b'\nconfig NOTE10_KERNEL_READONLY_SPAN_CANDIDATE\n\tbool "Note10 distinct type3 readonly span candidate"\n\tdepends on NOTE10_DATA_CARRIER\n\tdefault n\n')
    for name,raw in (('drivers/misc/note10_sha256_kat.c',composition),
        ('drivers/misc/kernel_readonly_span.h',(data.HERE/'kernel_readonly_span.h').read_bytes()),
        ('drivers/misc/kernel_readonly_span_candidate.h',(data.HERE/'kernel_readonly_span_candidate.h').read_bytes())):
        (source/name).write_bytes(raw);result[name]=data.sha(raw)
    result['drivers/misc/note10_sha256_kat.Kconfig']=data.sha(config.read_bytes())
    return result


def slot_metadata(raw,system_map,object_symbols,object_sections,object_table):
    data.require(not any(name in object_symbols or name in object_sections for name in
        ('n10_kernel_readonly_input','n10_kernel_readonly_descriptor','.rodata.n10_kernel_readonly_input','.rodata.n10_kernel_readonly_descriptor','n10_readonly_input','n10_readonly_descriptor')),
        'type3 must contain one slot/descriptor without class2 or PC storage')
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
    for symbol,section,size in ((SLOT,'.rodata.n10_kernel_readonly3_input',CAPACITY),
                                (DESC,'.rodata.n10_kernel_readonly3_descriptor',DESCRIPTOR_BYTES)):
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
        permanent_descriptor_bytes=DESCRIPTOR_BYTES,physical_ready=False,descriptor_class=3,boot_page=2048)


def metadata_contract(slot,image_bytes):
    keys={'schema','source','capacity','descriptor_bytes','slot','descriptor','generic','patched',
        'permanent_input_bytes','permanent_descriptor_bytes','physical_ready','descriptor_class','boot_page'}
    data.require(type(slot) is dict and set(slot)==keys and slot['schema']==SCHEMA and
        slot['source']==MODE and type(slot['descriptor_class']) is int and slot['descriptor_class']==3 and
        type(slot['boot_page']) is int and slot['boot_page']==2048 and type(slot['capacity']) is int and slot['capacity']==CAPACITY and
        type(slot['descriptor_bytes']) is int and slot['descriptor_bytes']==80 and
        slot['generic'] is True and slot['patched'] is False and slot['physical_ready'] is False and
        slot['permanent_input_bytes']==CAPACITY and slot['permanent_descriptor_bytes']==80 and
        type(image_bytes) is int and image_bytes>CAPACITY+80,'closed generic kernel readonly slot metadata required')
    for key,symbol,section,size,preimage in (
        ('slot',SLOT,'.rodata.n10_kernel_readonly3_input',CAPACITY,data.sha(bytes(CAPACITY))),
        ('descriptor',DESC,'.rodata.n10_kernel_readonly3_descriptor',80,data.sha(DESCRIPTOR))):
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
    data.require(a['object_section_index']!=b['object_section_index'],'distinct type3 compiler sections required')
    data.require(a['offset']+a['bytes']<=b['offset'] or b['offset']+b['bytes']<=a['offset'],
        'candidate readonly metadata overlap')
    return True


def span_metadata(system_map,footprint,slot):
    return old.span_footprint(system_map,footprint,slot,slot_symbol=SLOT,descriptor_symbol=DESC)


def producer_contract(result,source,*,producing_sources=None):
    required=(*SOURCES,'kernel_readonly_input.py','kernel_readonly_span.h','linux_data_carrier.py',
        'linux_data_carrier.c','linux_data_carrier_composition.c','build_builtin_init_image.py')
    pins=producing_sources if producing_sources is not None else {
        'note10/device_test/'+name:data.sha((data.HERE/name).read_bytes()) for name in required}
    metadata_contract(result.get('kernel_readonly3_slot'),result.get('image_bytes'))
    span=result.get('kernel_readonly3_span',{});footprint=result.get('data_footprint',{});ci=result.get('ci_context',{})
    linked=footprint.get('linked_kernel_bytes')
    data.require(type(span) is dict and set(span)=={'schema','kernel_bytes','text_prefix_bytes','slot_contained','descriptor_contained',
        'disjoint','source','phase','hardware','ownership'} and span['schema']==old.SPAN_SCHEMA and
        type(span['kernel_bytes']) is int and 0<span['kernel_bytes']<=BUDGET and type(span['text_prefix_bytes']) is int and
        span['text_prefix_bytes']>=0 and span['kernel_bytes']+span['text_prefix_bytes']==linked and
        all(span[key] is True for key in ('slot_contained','descriptor_contained','disjoint')) and
        span['hardware'] is False and span['ownership'] is False and span['source']=='linked-kernel' and span['phase']=='pre_descriptor',
        'closed type3 linked span metadata required')
    data.require(result.get('version')=='v107' and result.get('diagnostic_kind')==result.get('data_input_kind')==result.get('storage_input_kind')==KIND and
        result.get('kernel_readonly3_marker')=='N10DATARO3' and result.get('kernel_readonly3_schema')==SCHEMA and result.get('kernel_readonly3_span_schema')==old.SPAN_SCHEMA and
        result.get('kernel_readonly3_default_enabled') is False and result.get('kernel_readonly3_requires_ack') is True and
        result.get('passed') is True and result.get('Image_built') is True and result.get('BOOT_built') is False and
        result.get('PC_only') is False and result.get('PC_first_use') is True and result.get('physical_ready') is False and result.get('deployment_ready') is False and
        result.get('device_authorized') is False and result.get('device_operations')==[] and
        result.get('data_expectation_mode')==MODE and result.get('data_expectation_slot')==result['kernel_readonly3_slot'] and
        result.get('image_expectation_patched') is False and result.get('external_initrd_capture') is False and
        result.get('input_capture_source')=='late-kernel-readonly-span-class3' and
        result.get('permanent_input_storage_bytes')==CAPACITY and result.get('permanent_descriptor_bytes')==80 and
        result.get('additional_linked_storage_bytes')==CAPACITY+80 and result.get('class2_PC_storage_absent') is True and
        type(linked) is int and 0<linked<=BUDGET and result.get('kernel_readonly3_linked_bytes')==linked and
        result.get('kernel_readonly3_image_bytes')==result.get('image_bytes') and
        type(footprint.get('data_state_bytes')) is int and 0<footprint['data_state_bytes']<=128 and
        result.get('settings',{}).get('NOTE10_KERNEL_READONLY_SPAN_CANDIDATE')=='y' and
        all(result.get('settings',{}).get(key)=='n' for key in ('NOTE10_KERNEL_READONLY_INPUT','NOTE10_KERNEL_READONLY_SPAN_PC',
            'NOTE10_READONLY_INPUT_PC','NOTE10_OWNED_CONTIGUOUS_STAGING','NOTE10_CURRENT_OWNED_STAGING')) and
        not any(key in result for key in (*old.FIELDS[1:],'kernel_readonly_span_schema','readonly_input_schema','readonly_input_slot',
            'readonly_pc_contract','data_compare_schema','data_input_range_schema','data_early_prefix_schema',*data.GROWTH_FIELDS)) and
        re.fullmatch('[0-9a-f]{40}',source or '') and source not in (old.HISTORICAL_HEAD,'1fb2be6472ffd7c1c1544caf005b4db55fb07f68') and
        ci.get('GITHUB_SHA')==ci.get('GITHUB_WORKFLOW_SHA')==source and ci.get('GITHUB_JOB')=='linux-data-carrier' and
        ci.get('GITHUB_REPOSITORY')=='eirblue/ios_note10p' and ci.get('GITHUB_WORKFLOW_REF')=='eirblue/ios_note10p/'+WORKFLOW+'@refs/heads/main' and
        all(re.fullmatch('[1-9][0-9]*',ci.get(key,'') or '') for key in ('GITHUB_RUN_ID','GITHUB_RUN_ATTEMPT')) and
        type(pins) is dict and all('note10/device_test/'+name in pins for name in required) and
        all(re.fullmatch('[0-9a-f]{64}',value or '') and result.get('source_sha256',{}).get(key)==value for key,value in pins.items()),
        'distinct type3 PC-first-use producer/source required')
    for key in ('slot','descriptor'):
        extent=result['kernel_readonly3_slot'][key]
        data.require(span['text_prefix_bytes']<=extent['offset'] and extent['offset']+extent['bytes']<=linked,'type3 span extent differs')
    return dict(candidate_kind=KIND,storage_input_kind=KIND,descriptor_class=3,PC_first_use=True,physical_ready=False,
        slot_count=1,descriptor_count=1,additional_readonly_storage_bytes=CAPACITY+80,linked_budget=BUDGET,
        scalar_bytes=footprint['data_state_bytes'],range_scalar_bytes=16,temporary_outcome_bytes=128,
        hardware_mapping_attested=False,global_RAM_ownership=False,offline_composition_admitted=False)


def is_candidate(row):
    return row.get('diagnostic_kind')==KIND or row.get('data_input_kind')==KIND or row.get('data_expectation_mode')==MODE or any(key in row for key in FIELDS)


def require_device_scope(row,ack_kernel_readonly_growth=False):
    data.require(row.get('diagnostic_kind') not in ('readonly-input-pc',old.SPAN_KIND) and
        not any(key in row for key in ('readonly_input_schema','readonly_pc_contract','kernel_readonly_span_schema')),
        'old PC source cannot be promoted to type3')
    data.require(row.get('version')=='v107' and row.get('diagnostic_kind')==row.get('data_input_kind')==KIND and
        row.get('kernel_readonly3_schema')==SCHEMA and row.get('data_expectation_mode')==MODE and
        row.get('kernel_readonly3_slot',{}).get('descriptor_class')==3 and row.get('kernel_readonly3_slot',{}).get('schema')==SCHEMA and
        row.get('PC_only') is not True and row.get('image_expectation_patched') is True and ack_kernel_readonly_growth is True,
        'typed intrinsically patched type3 binding and explicit growth ACK required before any device query')
    # No generic ready flag substitutes for the future reviewed offline transaction.
    data.require(False,'type3 offline composition is not admitted in this PC-first-use revision')


def decode_selected(raw,banner,identity,cycle,*,expected):
    from builtin_init_profile import decode as baseline_decode
    producer_contract(expected,expected.get('ci_context',{}).get('GITHUB_SHA'))
    bound=expected['kernel_readonly3_span']['kernel_bytes']
    components=dict(pid1_validation='not_checked',return_validation='not_checked',return_boot_association='not_checked',
        functional_acceptance=False,hardware_return_proven_by_frames=False)
    def selected(text,rid):
        row=data.decode(text,rid,cycle,_source_class=MODE)
        components['kernel_readonly3_data']=row;components['data_phase']=data.functional_phase(row['status'])
        components['structural_presence']=data.structural_presence(text,rid,cycle,row['boot_identity'])
        data.require(not any(marker in text for marker in ('N10DATA1 ','N10DATARO1','N10DATAPC','N10DATACMP','N10DATARANGE','N10DATAEARLY','N10DATAGROWTH')),
            'type3 cannot claim class2, PC or external companions')
        components['kernel_readonly3_span']=old.decode_span(text,rid,cycle,row['boot_identity'],bound)
        data.require(row['carrier']==CAPACITY and row['logical'] in (0,CAPACITY),'type3 extent differs')
        data.require(False,'generic type3 PC observation cannot authorize functional or physical acceptance')
    try:baseline_decode(raw,banner,identity,cycle,digest_decoder=selected,digest_marker=b'N10DATARO3',component_evidence=components)
    except ValueError as error:raise data.ComponentObservationError(error,components) from error
    raise ValueError('generic type3 PC observation cannot be accepted')
