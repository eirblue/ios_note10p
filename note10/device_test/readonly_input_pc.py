"""Closed generic readonly kernel input candidate. PC-only, never physical-ready."""
from pathlib import Path
import re
import struct
import linux_data_carrier as data

KIND='readonly-input-pc'
SCHEMA='n10-kernel-readonly-input-pc-v1'
MODE='kernel-readonly-slot-v1'
CAPACITY=4440064
ALIGN=16
DESCRIPTOR_BYTES=80
MAGIC=b'N10ROINPUTPCV1!!'
DESCRIPTOR=MAGIC+struct.pack('<IIQQ',1,DESCRIPTOR_BYTES,CAPACITY,0)+bytes(40)
SLOT='n10_readonly_input'
DESC='n10_readonly_descriptor'
WORKFLOW='.github/workflows/note10-linux-data-carrier.yml'
SOURCES=('readonly_input_pc.py','readonly_input_pc.h','build_readonly_input_pc.py',
    'readonly_input_pc_fixture.c','test_v103_readonly_input_pc.py')
API_PINS=data.API_PINS


def install(source,identity):
    source=Path(source)
    original=(source/'arch/arm64/kernel/setup.c').read_bytes()
    result=data.install(source,identity)
    # PC source has no postpaging external-input hook or RAM query.
    (source/'arch/arm64/kernel/setup.c').write_bytes(original)
    result['arch/arm64/kernel/setup.c']=data.sha(original)
    composition=(data.HERE/'linux_data_carrier_composition.c').read_bytes()
    old=b'#define N10_DATA_COMPARE_EVIDENCE 1'
    data.require(composition.count(old)==1,'closed PC composition seam required')
    composition=composition.replace(old,b'#ifdef CONFIG_NOTE10_READONLY_INPUT_PC\n#define N10_DATA_READONLY_PC 1\n#else\n'+old+b'\n#endif',1)
    config=source/'drivers/misc/note10_sha256_kat.Kconfig'
    config.write_bytes(config.read_bytes()+b'\nconfig NOTE10_READONLY_INPUT_PC\n\tbool "Note10 PC-only readonly kernel input"\n\tdepends on NOTE10_DATA_CARRIER\n\tdefault n\n\thelp\n\t  Adds a generic 4440064-byte readonly slot. No physical admission.\n')
    for name,raw in (('drivers/misc/note10_sha256_kat.c',composition),
        ('drivers/misc/readonly_input_pc.h',(data.HERE/'readonly_input_pc.h').read_bytes())):
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
    for symbol,section,size in ((SLOT,'.rodata.n10_readonly_input',CAPACITY),
                                (DESC,'.rodata.n10_readonly_descriptor',DESCRIPTOR_BYTES)):
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
        permanent_descriptor_bytes=DESCRIPTOR_BYTES,physical_ready=False)


def metadata_contract(slot,image_bytes):
    keys={'schema','source','capacity','descriptor_bytes','slot','descriptor','generic','patched',
        'permanent_input_bytes','permanent_descriptor_bytes','physical_ready'}
    data.require(type(slot) is dict and set(slot)==keys and slot['schema']==SCHEMA and
        slot['source']==MODE and type(slot['capacity']) is int and slot['capacity']==CAPACITY and
        type(slot['descriptor_bytes']) is int and slot['descriptor_bytes']==80 and
        slot['generic'] is True and slot['patched'] is False and slot['physical_ready'] is False and
        slot['permanent_input_bytes']==CAPACITY and slot['permanent_descriptor_bytes']==80 and
        type(image_bytes) is int and image_bytes>CAPACITY+80,'closed generic PC slot metadata required')
    for key,symbol,section,size,preimage in (
        ('slot',SLOT,'.rodata.n10_readonly_input',CAPACITY,data.sha(bytes(CAPACITY))),
        ('descriptor',DESC,'.rodata.n10_readonly_descriptor',80,data.sha(DESCRIPTOR))):
        row=slot[key]
        data.require(type(row) is dict and set(row)=={'symbol','section','offset','bytes','alignment','readonly_flags','preimage_sha256','object_section_index','object_symbol_offset'} and
            row['symbol']==symbol and row['section']==section and type(row['bytes']) is int and row['bytes']==size and
            type(row['offset']) is int and row['offset']>=0 and row['offset']%ALIGN==0 and
            row['offset']+size<=image_bytes and type(row['alignment']) is int and row['alignment']==ALIGN and
            type(row['readonly_flags']) is str and 'A' in row['readonly_flags'] and
            not {'W','X'} & set(row['readonly_flags']) and row['preimage_sha256']==preimage and
            type(row['object_section_index']) is int and row['object_section_index']>0 and
            type(row['object_symbol_offset']) is int and row['object_symbol_offset']==0,
            'closed PC readonly extent provenance differs')
    a,b=slot['slot'],slot['descriptor']
    data.require(a['offset']+a['bytes']<=b['offset'] or b['offset']+b['bytes']<=a['offset'],
        'PC readonly metadata overlap')
    return True


def pc_contract(result,source,*,producing_sources=None):
    ci=result.get('ci_context',{})
    pins=producing_sources if producing_sources is not None else {
        'note10/device_test/'+n:data.sha((data.HERE/n).read_bytes()) for n in
        (*SOURCES,'linux_data_carrier.c','linux_data_carrier_composition.c','build_builtin_init_image.py')}
    slot=result.get('readonly_input_slot',{})
    metadata_contract(slot,result.get('image_bytes'))
    data.require(result.get('passed') is True and result.get('Image_built') is True and
        result.get('BOOT_built') is False and result.get('version')=='v103' and
        result.get('diagnostic_kind')==KIND and result.get('PC_only') is True and
        result.get('physical_ready') is False and result.get('deployment_ready') is False and
        result.get('device_authorized') is False and result.get('device_operations')==[] and
        result.get('readonly_input_schema')==SCHEMA and result.get('data_expectation_mode')==MODE and
        result.get('readonly_default_enabled') is False and
        result.get('settings',{}).get('NOTE10_READONLY_INPUT_PC')=='y' and
        result.get('settings',{}).get('NOTE10_OWNED_CONTIGUOUS_STAGING')=='n' and
        result.get('settings',{}).get('NOTE10_CURRENT_OWNED_STAGING')=='n' and
        result.get('external_initrd_capture') is False and
        result.get('input_capture_source')=='late-kernel-readonly-slot-only' and slot.get('schema')==SCHEMA and
        slot.get('capacity')==CAPACITY and slot.get('generic') is True and slot.get('patched') is False and
        result.get('permanent_input_storage_bytes')==CAPACITY and
        result.get('permanent_descriptor_bytes')==DESCRIPTOR_BYTES and
        type(result.get('data_footprint',{}).get('data_state_bytes')) is int and
        0<result['data_footprint']['data_state_bytes']<=128 and
        re.fullmatch('[0-9a-f]{40}',source or '') and
        ci.get('GITHUB_SHA')==ci.get('GITHUB_WORKFLOW_SHA')==source and
        ci.get('GITHUB_JOB')=='linux-data-carrier' and ci.get('GITHUB_REPOSITORY')=='eirblue/ios_note10p' and
        ci.get('GITHUB_WORKFLOW_REF')=='eirblue/ios_note10p/'+WORKFLOW+'@refs/heads/main' and
        all(re.fullmatch('[1-9][0-9]*',ci.get(k,'') or '') for k in ('GITHUB_RUN_ID','GITHUB_RUN_ATTEMPT')) and
        type(pins) is dict and pins and all(re.fullmatch('[0-9a-f]{64}',v or '') and
            result.get('source_sha256',{}).get(k)==v for k,v in pins.items()),
        'closed readonly PC producer/source context differs')
    data.require(all('note10/device_test/'+n in pins for n in
        (*SOURCES,'linux_data_carrier.c','linux_data_carrier_composition.c','build_builtin_init_image.py')),
        'readonly PC source closure incomplete')
    return dict(PC_only=True,physical_ready=False,global_RAM_ownership=False,
        permanent_input_storage_bytes=CAPACITY,permanent_descriptor_bytes=DESCRIPTOR_BYTES,
        source=MODE,generic_unpatched=True,runtime_executed=False)
