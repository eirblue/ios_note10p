"""One bounded layer of actual-address OF outlined bodies; no runtime/lookup bound."""
from pathlib import Path, PurePosixPath
import re
import subprocess
import v236_nm_multiplicity as retained

require,sha=retained.require,retained.sha
SOURCE_GUARDS,CONFIG,LIMITS=retained.SOURCE_GUARDS,retained.CONFIG,retained.LIMITS
BUNDLE_CAP,TEXT_CAP=retained.BUNDLE_CAP,retained.TEXT_CAP
SCHEMA='note10-v237-address-bound-outlined-evidence-v1'
RAW_SCHEMA='note10-v237-address-bound-outlined-raw-v1'
OBJECT='drivers/of/base.o'
OUTLINED_NAMES=tuple('OUTLINED_FUNCTION_'+str(n)for n in (0,1,2,4,5,7,9,12,13,15,18,22,23))
ANCHORS=(*retained.NEW_OBJECTS[OBJECT],'__of_find_property')
HELPER_CAP=256


def of_functions(elf):
    sections={};functions={}
    for line in elf.splitlines():
        section=re.match(r'^\s*\[\s*(\d+)\]\s+(\S+)\s+\S+\s+[0-9a-fA-F]+\s+[0-9a-fA-F]+\s+[0-9a-fA-F]+\s+[0-9a-fA-F]+\s+([A-Z]+)\s+',line)
        if section:sections[section[1]]=(section[2],section[3])
        row=re.match(r'^\s*\d+:\s+([0-9a-fA-F]+)\s+(\d+|0x[0-9a-fA-F]+)\s+FUNC\s+(LOCAL|GLOBAL|WEAK)\s+DEFAULT\s+(\d+)\s+(\S+)\s*$',line)
        if row and row[5]in (*ANCHORS,*OUTLINED_NAMES):
            require(row[5]not in functions,'one local input-section function record required')
            functions[row[5]]=dict(address=int(row[1],16),bytes=int(row[2],16 if row[2].startswith('0x')else 10),binding=row[3],section_index=row[4])
    require(set(functions)==set((*ANCHORS,*OUTLINED_NAMES)),'exact nine anchors and thirteen local helpers required')
    return sections,functions


def outline_joins(raw_primary,primary,nm):
    """Join one input section, measured anchor translation, and actual edge records."""
    table=retained.linked_symbols(nm);item=raw_primary['objects'][OBJECT]
    tu=retained.translation_unit(item['command'].encode(),OBJECT)
    frames=retained.stream.frames(item['stack_usage']);sections,functions=of_functions(item['elf_sections_and_symbols'])
    anchors={name:row for name,row in primary['object_provenance'].items()if row['object']==OBJECT}
    require(set(anchors)==set(ANCHORS),'exact already-proved OF anchors required')
    indices={functions[name]['section_index']for name in ANCHORS};require(len(indices)==1,'all OF anchors must share one input section')
    index=next(iter(indices));require(index in sections,'anchor input section required');section,flags=sections[index]
    require(section=='.text'and'A'in flags and'X'in flags and'W'not in flags,'one non-init executable OF input section required')
    deltas=set()
    for name,row in anchors.items():
        local=functions[name];linked=retained.selected_symbol(table,name)
        require(row['object_address']==local['address']and row['bytes']==local['bytes']==linked['bytes']and
            row['linked_address']==linked['address']and row['section']==section,'anchor ELF/object/linked record join required')
        deltas.add(row['linked_address']-row['object_address'])
    require(len(deltas)==1,'one measured same-input-section link translation required')
    delta=next(iter(deltas));targets={};calls={}
    for caller,row in primary['assembly'].items():
        for edge in row['external_transfers']:
            for record in edge['resolved_records']:
                if not record['name'].startswith('OUTLINED_FUNCTION_'):continue
                require(caller in ANCHORS and record['name']in OUTLINED_NAMES and record['offset']==0,
                    'only reviewed direct OF helper entry records may be expanded')
                key=(record['name'],record['address'],record['bytes'],record['ordinal'])
                targets[key]=record
                calls.setdefault(key,[]).append(dict(caller=caller,address=edge['address'],mnemonic=edge['mnemonic'],target=edge['target']))
    require(len(targets)==13 and {key[0]for key in targets}==set(OUTLINED_NAMES),'exact thirteen direct helper identities required')
    joins=[]
    for key,record in sorted(targets.items(),key=lambda pair:pair[0][1]):
        name,address,size,ordinal=key;local=functions[name]
        original=[row for row in table[name]if row['address']==address and row['bytes']==size and row['ordinal']==ordinal and row['kind']==record['kind']]
        require(len(original)==1 and record['kind']=='t'and local['binding']=='LOCAL'and local['section_index']==index and
            local['bytes']==size and local['address']+delta==address and 0<size<=HELPER_CAP and size%4==address%4==0,
            'exact edge-selected local nm/ELF extent and same-section translation required')
        require(name in frames and frames[name]['source']==tu['translation_unit']and frames[name]['kind']=='static'and 0<=frames[name]['bytes']<=8192,
            'actual same-TU static helper frame required; missing/dynamic is not zero')
        aliases=sorted({n for n,rows in table.items()for row in rows if row['address']==address and row['bytes']==size})
        require(name in aliases and len(aliases)<=32,'actual bounded same-extent helper aliases required')
        joins.append(dict(identity=name+'@'+format(address,'016x')+':'+str(ordinal),symbol=dict(symbol=name,address=address,bytes=size,aliases=aliases),
            nm_record=dict(name=name,**original[0]),object_address=local['address'],section_index=index,section=section,
            translation_unit=tu['translation_unit'],compiler_static_frame_bytes=frames[name]['bytes'],call_sites=calls[key]))
    return dict(anchors=anchors,section_index=index,section=section,linked_minus_object_address=delta,helpers=joins)


def helper_command(vmlinux,symbol):
    path=PurePosixPath(str(vmlinux));address,size=symbol['address'],symbol['bytes'];aliases=symbol['aliases']
    require(path.is_absolute()and str(path)==str(vmlinux)and '..'not in path.parts and path.name=='vmlinux','canonical same-vmlinux POSIX path required')
    require(set(symbol)=={'symbol','address','bytes','aliases'}and symbol['symbol']in OUTLINED_NAMES and type(address)is type(size)is int and
        0<address<1<<64 and 0<size<=HELPER_CAP and address%4==size%4==0 and address+size<1<<64 and
        type(aliases)is list and symbol['symbol']in aliases and len(aliases)==len(set(aliases))<=32,
        'one bounded actual-address reviewed helper symbol required')
    return ['aarch64-linux-gnu-objdump','-d','--disassemble-zeroes','--start-address='+hex(address),'--stop-address='+hex(address+size),str(path)]


def classify_leaf(raw,symbol,table,compiler_frame):
    require(symbol['symbol']in (*OUTLINED_NAMES,'strcmp')and
        (compiler_frame is None if symbol['symbol']=='strcmp'else type(compiler_frame)is int and 0<=compiler_frame<=8192),
        'only reviewed helper/static-frame or same-body strcmp classification allowed')
    # The retained complete-extent/control-transfer reader runs on actual instructions.
    proof=retained.transfers(raw,symbol,table);uses_sp=False
    for line in raw.splitlines():
        instruction=re.fullmatch(r'\s*[0-9a-fA-F]+:\s+[0-9a-fA-F]{8}\s+(.+)',line)
        if instruction and re.search(r'\b(?:sp|wsp)\b',instruction[1].split('//',1)[0].lower()):uses_sp=True
    reasons=[]
    if uses_sp:reasons.append('actual instruction references SP')
    if proof['external_transfers']:reasons.append('call or external transfer remains')
    if proof['unknown_control_transfers']:reasons.append('unknown or indirect transfer remains')
    if compiler_frame not in (None,0):reasons.append('compiler reports a nonzero own frame')
    return dict(**proof,compiler_static_frame_bytes=compiler_frame,zero_own_stack_proven=not reasons,
        own_stack_bytes=0 if not reasons else None,classification='strict-zero-own-stack'if not reasons else'unknown',reasons=reasons,
        whole_lookup_bound_proven=False)


def finish(raw,stack_data,primary):
    require(set(raw)=={'schema','primary','outlined_assembly','tools'}and raw['schema']==RAW_SCHEMA,'exact bounded outlined bundle required')
    nm=stack_data['linked_nm'];table=retained.linked_symbols(nm);joins=outline_joins(raw['primary'],primary,nm)
    helpers=joins['helpers'];identities={row['identity']for row in helpers}
    require(set(raw['outlined_assembly'])==identities and len(raw['tools'])==13,'exact thirteen captured helper bodies required')
    # Same object root as the already authenticated primary readelf/objdump commands.
    target=next(iter(retained.NEW_OBJECTS));object_argv=raw['primary']['tools'][0]['argv'];root=object_argv[-1][:-len(target)-1]
    classified={}
    for row,tool in zip(helpers,raw['tools']):
        text=raw['outlined_assembly'][row['identity']]
        require(set(tool)=={'argv','returncode','stdout_sha256','stderr'}and tool['returncode']==0 and type(tool['stderr'])is str and
            tool['argv']==helper_command(root+'/vmlinux',row['symbol'])and tool['stdout_sha256']==sha(text.encode()),'actual same-Image helper argv/text binding required')
        classified[row['identity']]=classify_leaf(text,row['symbol'],table,row['compiler_static_frame_bytes'])
    strcmp=primary['assembly']['strcmp']['symbol']
    aliases=primary['assembly']['strcmp']['alias_records']
    require({'strcmp','__pi_strcmp'}<={row['name']for row in aliases}and all(row['address']==strcmp['address']and row['bytes']==strcmp['bytes']for row in aliases),
        'strcmp/__pi_strcmp must bind the already captured same body')
    strcmp_leaf=classify_leaf(raw['primary']['assembly']['strcmp'],strcmp,table,None)
    expanded={(row['symbol']['address'],row['symbol']['bytes'])for row in (*primary['assembly'].values(),*classified.values())}
    remaining={}
    for row in (*primary['assembly'].values(),*classified.values(),strcmp_leaf):
        for edge in row['external_transfers']:
            for record in edge['resolved_records']:
                if (record['address'],record['bytes'])not in expanded or record['name']in retained.SCHEDULER:
                    remaining[(record['name'],record['address'],record['bytes'],record['ordinal'])]=record
    return dict(schema=SCHEMA,primary=primary,outlined_input_section_join=joins,outlined_bodies=classified,strcmp_same_body_leaf=strcmp_leaf,
        outlined_capture_count=13,additional_object_reads=0,additional_nm_dumps=0,additional_strcmp_dumps=0,recursive_expansion=False,
        unexpanded_external_records=list(remaining.values()),
        unexpanded_scheduler_boundaries=list(retained.SCHEDULER),per_function_proof_is_not_a_chain_bound=True,**LIMITS)


def verify(raw,stack_data):
    require(type(raw)is dict and raw.get('schema')==RAW_SCHEMA,'fresh237 outlined raw schema required')
    primary=retained.verify(raw['primary'],stack_data)
    return finish(raw,stack_data,primary)


def collect(objects,stack_data,nm,save):
    raw=dict(schema=RAW_SCHEMA,primary=None,outlined_assembly={},tools=[])
    def save_primary(item):raw['primary']=item;save(raw)
    primary=retained.collect(objects,stack_data,nm,save_primary)
    joins=outline_joins(raw['primary'],primary,nm)
    for row in joins['helpers']:
        argv=helper_command(Path(objects)/'vmlinux',row['symbol'])
        done=subprocess.run(argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=False,timeout=120)
        require(len(done.stdout)<=TEXT_CAP and len(done.stderr)<=65536,'bounded outlined tool text required')
        raw['tools'].append(dict(argv=argv,returncode=done.returncode,stdout_sha256=sha(done.stdout),stderr=done.stderr.decode(errors='replace')))
        raw['outlined_assembly'][row['identity']]=done.stdout.decode();save(raw)
        require(done.returncode==0,'outlined capture failed; raw diagnostic retained')
    return finish(raw,dict(objects=stack_data['objects'],linked_nm=nm),primary)
