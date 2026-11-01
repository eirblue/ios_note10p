"""v82 native memory nonzero decoded add arguments; no successful-add claim."""
import hashlib
from pathlib import Path
import re

HERE=Path(__file__).resolve().parent
KIND='native-memory-observation'
PROFILE=KIND+'-v1'
STAGE='native_linux_memory_scan_nonzero_add_arguments'
CAPACITY=16
FIELDS=('native_memory_stage','native_memory_capacity','raw_input_binding','native_relative_placement_admitted')
SOURCES=('native_memory_observation.py','native_memory_observation.c','native_memory_composition.c',
         'build_native_memory_observation.py','test_native_memory_observation.py','native_memory_fixture.c',
         'early_fdt_binding.py')
API_PINS={
    'drivers/of/fdt.c':'e655d0f3902e4559932a8c262177a74623468caeda04b338c2de81d992593b34',
    'include/linux/of.h':'d9127c18db73393fe07ac50e801c8c1898b8d4b41366c5ca5d14c8244ef8bcdb',
    'arch/arm64/include/asm/memory.h':'e1e7ba2b6574a490b265560250ad7678628925211841c505e4966bd0f3be8baa',
}


def require(value,message):
    if not value:raise ValueError(message)


def replace_one(raw,old,new):
    require(raw.count(old)==1,'unique native memory hook anchor required')
    return raw.replace(old,new)


def overlay_fdt(raw):
    require(hashlib.sha256(raw).hexdigest()==API_PINS['drivers/of/fdt.c'],'pinned native scanner differs')
    start=raw.index(b'int __init of_scan_flat_dt(');end=raw.index(b'\n}\n',start)+3
    original=raw[start:end];part=original
    part=replace_one(part,b'\tint offset, rc = 0, depth = -1;\n',b'\tint offset, rc = 0, depth = -1;\n'
        b'#ifdef CONFIG_NOTE10_NATIVE_MEMORY_OBSERVATION\n'
        b'\tbool n10_memory_scan = it == early_init_dt_scan_memory;\n'
        b'\tif (n10_memory_scan)\n'
        b'\t\tn10_memory_begin(dt_root_addr_cells, dt_root_size_cells);\n'
        b'#endif\n')
    part=replace_one(part,b'\tif (!blob)\n\t\treturn 0;\n',b'\tif (!blob) {\n'
        b'#ifdef CONFIG_NOTE10_NATIVE_MEMORY_OBSERVATION\n'
        b'\t\tif (n10_memory_scan)\n\t\t\tn10_memory_end(1, 0, 0, 0);\n'
        b'#endif\n\t\treturn 0;\n\t}\n')
    part=replace_one(part,b'\treturn rc;\n',b'#ifdef CONFIG_NOTE10_NATIVE_MEMORY_OBSERVATION\n'
        b'\tif (n10_memory_scan)\n\t\tn10_memory_end(0, offset, depth, rc);\n'
        b'#endif\n\treturn rc;\n')
    declarations=(b'#ifdef CONFIG_NOTE10_NATIVE_MEMORY_OBSERVATION\n'
        b'extern void __init n10_memory_begin(int address_cells, int size_cells);\n'
        b'extern void __init n10_memory_row(u64 base, u64 size, u32 flags);\n'
        b'extern void __init n10_memory_end(int missing_blob, int offset, int depth, int rc);\n'
        b'#endif\n\n')
    raw=raw[:start]+declarations+part+raw[end:]
    start=raw.index(b'int __init early_init_dt_scan_memory(');end=raw.index(b'\n}\n',start)+3
    original=raw[start:end];part=original
    part=replace_one(part,b'\tbool hotpluggable;\n',b'\tbool hotpluggable;\n'
        b'#ifdef CONFIG_NOTE10_NATIVE_MEMORY_OBSERVATION\n\tunsigned int n10_memory_source;\n#endif\n')
    anchor=b'\treg = of_get_flat_dt_prop(node, "linux,usable-memory", &l);\n'
    part=replace_one(part,anchor,anchor+b'#ifdef CONFIG_NOTE10_NATIVE_MEMORY_OBSERVATION\n'
        b'\tn10_memory_source = reg ? 2U : 1U;\n#endif\n')
    anchor=b'\t\tearly_init_dt_add_memory_arch(base, size);\n'
    part=replace_one(part,anchor,b'#ifdef CONFIG_NOTE10_NATIVE_MEMORY_OBSERVATION\n'
        b'\t\tn10_memory_row(base, size, n10_memory_source | (hotpluggable ? 4U : 0U));\n'
        b'#endif\n'+anchor)
    return raw[:start]+part+raw[end:]


def install(source,identity):
    from builtin_init_route import install as baseline_install
    source=Path(source)
    for name,pin in API_PINS.items():
        require(hashlib.sha256((source/name).read_bytes()).hexdigest()==pin,'pinned native memory source differs: '+name)
    fdt=overlay_fdt((source/'drivers/of/fdt.c').read_bytes())
    result=baseline_install(source,identity)
    replacements={'drivers/misc/note10_sha256_kat.c':(HERE/'native_memory_composition.c').read_bytes(),
                  'drivers/misc/native_memory_observation.c':(HERE/'native_memory_observation.c').read_bytes(),
                  'drivers/of/fdt.c':fdt}
    config=source/'drivers/misc/note10_sha256_kat.Kconfig'
    config.write_bytes(config.read_bytes()+b"""
config NOTE10_NATIVE_MEMORY_OBSERVATION
\tbool "Note10 native Linux memory decoded-argument observation"
\tdepends on ARM64 && OF_FLATTREE && HAVE_MEMBLOCK && NOTE10_SHA256_KAT_RECOVERY && NOTE10_BUILTIN_INIT_ROUTE
\tdefault n
\thelp
\t  Retains at most16 already-decoded nonzero add arguments. No new scan,
\t  allocation, digest, successful-addition, ownership or XNU claim.
""")
    for name,data in replacements.items():(source/name).write_bytes(data)
    return {name:hashlib.sha256((source/name).read_bytes()).hexdigest() for name in (*result,*replacements)}


def linked_footprint(system_map,object_symbols,image_memory_bytes,text_offset,flags):
    wanted={'_text','_end','__bss_start','__bss_stop','n10_memory'};values={}
    for line in system_map.splitlines():
        parts=line.split()
        if len(parts)==3 and parts[2] in wanted:
            require(parts[2] not in values,'duplicate native state symbol');values[parts[2]]=int(parts[0],16)
    sizes=[int(parts[1],16) for line in object_symbols.splitlines()
           if len(parts:=line.split())==4 and parts[2].lower()=='b' and parts[3]=='n10_memory']
    require(set(values)==wanted and len(sizes)==1 and 384<=sizes[0]<=512 and
            values['_text']<values['__bss_start']<=values['n10_memory'] and
            values['n10_memory']+sizes[0]<=values['__bss_stop']<=values['_end'] and
            type(image_memory_bytes) is int and image_memory_bytes==values['_end']-values['_text'],
            'native permanent state/linked footprint unavailable')
    return dict(native_state_bytes=sizes[0],linked_kernel_bytes=image_memory_bytes,
        bss_start_offset=values['__bss_start']-values['_text'],bss_end_offset=values['__bss_stop']-values['_text'],
        native_state_offset=values['n10_memory']-values['_text'],image_text_offset=text_offset,image_flags=flags)


def relative_admission(result,lines,footprint,*,elf,archive,raw_inputs):
    from early_fdt_binding import ACCEPTED_BASELINE,placement_config_sha256,fixed_route_relation
    # Only this exact new task symbol is additional to established task/path exclusions.
    config=[line for line in lines if not line.startswith('CONFIG_NOTE10_NATIVE_MEMORY_OBSERVATION=') and
            line!='# CONFIG_NOTE10_NATIVE_MEMORY_OBSERVATION is not set']
    relation=None
    try:relation=fixed_route_relation(elf,archive,result,raw_inputs)
    except ValueError:pass
    checks=dict(native_scope=result.get('native_memory_stage')==STAGE and result.get('native_memory_capacity')==CAPACITY and
            'CONFIG_NOTE10_NATIVE_MEMORY_OBSERVATION=y' in lines and not
            {'CONFIG_NOTE10_EARLY_FDT_BINDING=y','CONFIG_NOTE10_CPU_AFFINITY_BINDING=y','CONFIG_NOTE10_SHA256_STREAM_STATE=y'}&set(lines),
        linked_span_contained=type(footprint.get('linked_kernel_bytes')) is int and
            0<footprint['linked_kernel_bytes']<=ACCEPTED_BASELINE['linked_kernel_bytes'],
        file_bytes_contained=type(result.get('image_bytes')) is int and
            0<result['image_bytes']<=ACCEPTED_BASELINE['image_file_bytes'],
        same_header_load_contract=footprint.get('image_text_offset')==ACCEPTED_BASELINE['header']['text_offset'] and
            footprint.get('image_flags')==ACCEPTED_BASELINE['header']['flags'],
        same_placement_configuration=placement_config_sha256(config)==ACCEPTED_BASELINE['config_sha256'],
        same_builtin_recovery_route=all(result.get('source_sha256',{}).get(k)==v for k,v in ACCEPTED_BASELINE['route_sources'].items()) and
            result.get('guarded_init_main_sha256')==ACCEPTED_BASELINE['route_artifacts']['guarded_init_main_sha256'] and relation is not None,
        supported_backend={'CONFIG_HAVE_MEMBLOCK=y','CONFIG_OF_FLATTREE=y','CONFIG_ARM64_4K_PAGES=y'}.issubset(lines),
        bounded_permanent_state=type(footprint.get('native_state_bytes')) is int and 384<=footprint['native_state_bytes']<=512)
    return dict(eligible=all(checks.values()),checks=checks,route_relation=relation,
        baseline_source_head=ACCEPTED_BASELINE['source_head'],claim='no new relative linked coverage under unchanged normal Linux loader contract',
        observed_runtime_base=False,absolute_FDT_extent_known=False,global_RAM_ownership=False)


def input_binding(result,lines,*,elf,archive,raw_inputs):
    require(result.get('version')=='v82' and result.get('diagnostic_kind')==KIND and result.get('raw_input_binding') is False and
            result.get('native_memory_stage')==STAGE and result.get('native_memory_capacity')==CAPACITY and
            re.fullmatch('[0-9a-f]{40}',result.get('ci_context',{}).get('GITHUB_SHA','')),
            'closed new native Image/source scope required')
    require('CONFIG_NOTE10_NATIVE_MEMORY_OBSERVATION=y' in lines and not
        {'CONFIG_NOTE10_EARLY_FDT_BINDING=y','CONFIG_NOTE10_CPU_AFFINITY_BINDING=y','CONFIG_NOTE10_SHA256_STREAM_STATE=y'}&set(lines),
        'native-only callback configuration required')
    for name in SOURCES:
        require(result.get('source_sha256',{}).get('note10/device_test/'+name)==hashlib.sha256((HERE/name).read_bytes()).hexdigest(),
                'new native Image source differs: '+name)
    admission=relative_admission(result,lines,result['native_memory_footprint'],elf=elf,archive=archive,raw_inputs=raw_inputs)
    require(result.get('native_relative_placement')==admission and admission['eligible'],'native relative placement unresolved')
    return dict(native_memory_stage=STAGE,native_memory_capacity=CAPACITY,raw_input_binding=False,native_relative_placement_admitted=True)


def decode(text,identity,cycle):
    from decode_reservation import checksum
    require(type(text) is str and len(text)<=16*1024*1024 and re.fullmatch('[0-9a-f]{32}',identity) and re.fullmatch('[0-9a-f]{32}',cycle),
            'bounded native log/identity required')
    lines=[line for line in text.splitlines() if 'N10MEMARGS1' in line]
    require(2<=len(lines)<=CAPACITY+2,'bounded native BEGIN/ROW/END required')
    begin_keys=('id','cycle','kind','stage','ac','sc','capacity','attempted','raw_binding')
    row_keys=('id','cycle','kind','ordinal','base','size','source','hotplug')
    end_keys=('id','cycle','kind','seen','stored','dropped','flags','ended','offset','depth','rc','complete','raw_binding','add_success','reservations','ownership')
    records=[];boots=set()
    for line in lines:
        match=re.search(r'N10BOOTLINK2 boot=([0-9a-f]{32}) N10MEMARGS1 ([^\r\n\x00]{1,383}) checksum=([0-9a-f]{8})$',line)
        require(match is not None and match[1]!='0'*32,'native associated frame format')
        body=match[2];require(body.isascii() and checksum(body.encode())==int(match[3],16),'native checksum differs')
        pairs=[word.split('=') for word in body.split(' ')]
        require(all(len(pair)==2 for pair in pairs),'native field shape')
        row=dict(pairs);keys=tuple(pair[0] for pair in pairs)
        require(keys==(begin_keys if row.get('kind')=='begin' else row_keys if row.get('kind')=='row' else end_keys if row.get('kind')=='end' else ()),
                'closed native schema/order required')
        require(row['id']==identity and row['cycle']==cycle,'native build/cycle differs')
        boots.add(match[1]);records.append(row)
    require(len(boots)==1,'one native boot identity required')
    begin,end=records[0],records[-1]
    require(begin['kind']=='begin' and end['kind']=='end' and all(row['kind']=='row' for row in records[1:-1]) and
            begin['stage']==STAGE and begin['capacity']=='16' and begin['attempted'] in ('0','1') and
            begin['raw_binding']==end['raw_binding']==end['add_success']==end['reservations']==end['ownership']=='0',
            'native stage/order/nonclaim differs')
    def unsigned(value):
        require(re.fullmatch('0|[1-9][0-9]{0,9}',value) and int(value)<=0xffffffff,'native uint32 field');return int(value)
    def signed(value):
        require(re.fullmatch('0|-?[1-9][0-9]{0,9}',value) and -2**31<=int(value)<2**31,'native int32 field');return int(value)
    ac,sc=signed(begin['ac']),signed(begin['sc']);seen,stored,dropped=(unsigned(end[k]) for k in ('seen','stored','dropped'))
    require(re.fullmatch('[0-9a-f]{8}',end['flags']),'native flags format');flags=int(end['flags'],16)
    require(flags&~127==0 and stored<=CAPACITY and len(records)==stored+2 and end['ended'] in ('0','1') and end['complete'] in ('0','1'),
            'native count/status fields')
    offset,depth,rc=(signed(end[k]) for k in ('offset','depth','rc'))
    if not flags&8:require(seen==stored+dropped and stored==min(seen,CAPACITY),'native stored/drop relation')
    require(not dropped or flags&1,'native overflow flag missing')
    require((ac in (1,2) and sc in (1,2)) or flags&(4|64),'native unsupported widths not labelled')
    root_close=end['ended']=='1' and offset>=0 and depth<0 and rc==0
    complete=not flags and begin['attempted']=='1' and root_close
    require(int(end['complete'])==int(complete),'native completion claim differs')
    rows=[]
    for i,row in enumerate(records[1:-1]):
        require(row['ordinal']==str(i) and re.fullmatch('[0-9a-f]{16}',row['base']) and re.fullmatch('[0-9a-f]{16}',row['size']) and
                int(row['size'],16)>0 and row['source'] in ('1','2') and row['hotplug'] in ('0','1'),
                'native argument row/order differs')
        rows.append(dict(ordinal=i,base=int(row['base'],16),size=int(row['size'],16),
                         source='linux,usable-memory' if row['source']=='2' else 'reg',hotpluggable=row['hotplug']=='1'))
    return dict(observed=True,passed=complete,boot_identity=next(iter(boots)),stage=STAGE,rows=rows,
        native_address_cells=ac,native_size_cells=sc,seen=seen,stored=stored,dropped=dropped,flags=flags,
        native_exit=dict(offset=offset,depth=depth,rc=rc),argument_stream_complete=complete,
        native_walk_returned_at_root_close=root_close,full_FDT_validity_known=False,explicit_root_cells_known=False,
        architecture_normalized=False,memblock_add_success_known=False,raw_input_binding=False,
        snapshot_digest_binding=False,reservations_complete=False,global_RAM_ownership=False,free_RAM_known=False,
        current_Linux_occupancy_known=False,apple_memory_map=False,handoff_ready=False,deployment_ready=False,xnu_executed=False)


def decode_selected(data,banner,identity,cycle):
    from builtin_init_profile import decode as baseline_decode
    def selected(text,rid):
        observed=decode(text,rid,cycle)
        require(observed['passed'],'native argument stream incomplete flags='+str(observed['flags']))
        return observed
    clipped,observed=baseline_decode(data,banner,identity,cycle,digest_decoder=selected,digest_marker=b'N10MEMARGS1')
    require(observed['kat']['boot_identity']==observed['boot_identity'],'native/route/recovery boot differs')
    return clipped,observed
