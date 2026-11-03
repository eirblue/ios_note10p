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
    composition=composition.replace(old,b'#ifdef CONFIG_NOTE10_KERNEL_READONLY_INPUT\n#define N10_DATA_KERNEL_READONLY 1\n#else\n'+old+b'\n#endif',1)
    config=source/'drivers/misc/note10_sha256_kat.Kconfig'
    config.write_bytes(config.read_bytes()+b'\nconfig NOTE10_KERNEL_READONLY_INPUT\n\tbool "Note10 kernel readonly candidate; new growth scope required"\n\tdepends on NOTE10_DATA_CARRIER\n\tdefault n\n')
    for name,raw in (('drivers/misc/note10_sha256_kat.c',composition),
        ('drivers/misc/kernel_readonly_input.h',(data.HERE/'kernel_readonly_input.h').read_bytes())):
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




def producer_contract(result,source,*,producing_sources=None):
    ci=result.get('ci_context',{})
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
        all(result.get('settings',{}).get(key)=='n' for key in
            ('NOTE10_READONLY_INPUT_PC','NOTE10_OWNED_CONTIGUOUS_STAGING','NOTE10_CURRENT_OWNED_STAGING')) and
        not any(key in result for key in ('readonly_input_schema','readonly_input_slot','readonly_pc_contract',
            'data_compare_schema','data_input_range_schema','data_early_prefix_schema',*data.GROWTH_FIELDS)) and
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


def input_binding(result,lines,*,elf,archive,raw_inputs):
    from early_fdt_binding import fixed_route_relation
    producer_contract(result,result.get('ci_context',{}).get('GITHUB_SHA'))
    data.require('CONFIG_NOTE10_KERNEL_READONLY_INPUT=y' in lines and
        not {'CONFIG_NOTE10_READONLY_INPUT_PC=y','CONFIG_NOTE10_OWNED_CONTIGUOUS_STAGING=y',
             'CONFIG_NOTE10_CURRENT_OWNED_STAGING=y'} & set(lines),'distinct readonly source configuration required')
    fixed_route_relation(elf,archive,result,raw_inputs)
    return dict(data_carrier_stage=data.STAGE,data_relative_placement_admitted=False,raw_input_binding=False,
        data_expectation_mode=MODE,data_expectation_slot=result['kernel_readonly_slot'],image_expectation_patched=False,
        **{key:result[key] for key in PRODUCER_FIELDS})


def is_candidate(row):
    return row.get('data_input_kind')==KIND or row.get('diagnostic_kind')==KIND or row.get('data_expectation_mode')==MODE or any(key in row for key in FIELDS)


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
             'data_input_range_schema','data_linked_kernel_bytes','data_early_prefix_schema',*data.GROWTH_FIELDS)),
        'closed kernel-readonly profile/source class required')
    if require_compact:
        data.require(row.get('kernel_readonly_compact_bytes')==CAPACITY and
            all(re.fullmatch('[0-9a-f]{64}',row.get(key,'') or '') and row[key]!='0'*64 for key in
                ('kernel_readonly_compact_sha256','kernel_readonly_compact_manifest_sha256')),
            'authenticated compact candidate identity required')
    return True


def require_device_scope(row,ack_kernel_readonly_growth=False):
    # The original PC domain remains forbidden even when candidate flags/ACK are forged.
    data.require(row.get('PC_only') is not True and row.get('data_expectation_mode')!='kernel-readonly-slot-v1' and row.get('version')!='v103' and row.get('diagnostic_kind') not in
        ('readonly-input-pc','owned-contiguous-staging-pc','current-owned-staging-pc') and not any(key in row for key in
        ('readonly_input_schema','readonly_input_slot','readonly_pc_contract')),'PC-only source is permanently forbidden on device')
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


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='command',required=True)
    d=sub.add_parser('derive');d.add_argument('--source-manifest',type=Path,required=True)
    d.add_argument('--source-manifest-sha256',required=True);d.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    print(json.dumps(derive(args.source_manifest,args.source_manifest_sha256,args.output),indent=2))
