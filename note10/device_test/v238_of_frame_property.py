"""Borrowed caller slots and one bounded property frontier; no query/runtime bound."""
from pathlib import Path, PurePosixPath
import re
import subprocess
import v237_outlined_evidence as retained

p=retained.retained
require,sha=p.require,p.sha
CONFIG,LIMITS=retained.CONFIG,retained.LIMITS
BUNDLE_CAP,TEXT_CAP=retained.BUNDLE_CAP,retained.TEXT_CAP
SOURCE_GUARDS={**retained.SOURCE_GUARDS,'drivers/of/property.c':'2ce1a02d386d775368a9bfe1dd81eb47e1ba25a43afbcba03af6bf440dfac2ed'}
SCHEMA='note10-v238-OF-frame-property-evidence-v1'
RAW_SCHEMA='note10-v238-OF-frame-property-raw-v1'
SP_HELPERS={'OUTLINED_FUNCTION_0':'of_find_property','OUTLINED_FUNCTION_9':'of_get_cpu_node',
    'OUTLINED_FUNCTION_12':'__of_find_property','OUTLINED_FUNCTION_13':'of_find_node_by_type'}
OBJECT='drivers/of/property.o'
PUBLIC='of_property_read_variable_u32_array'
STATIC='of_find_property_value_of_size'
C_NAMES=(PUBLIC,STATIC)
LOCAL_CAP=16
LOCAL_BYTES=256


def instructions(raw,proof):
    require(sha(raw.encode())==proof['disassembly_sha256'],'same captured instruction text required')
    rows=[]
    for line in raw.splitlines():
        row=re.fullmatch(r'\s*([0-9a-fA-F]+):\s+[0-9a-fA-F]{8}\s+(.+)',line)
        if row:
            text=row[2].lower().split('//',1)[0].strip();parts=text.split(None,1)
            rows.append((int(row[1],16),parts[0],parts[1]if len(parts)==2 else''))
    symbol=proof['symbol']
    require(rows and len(rows)*4==symbol['bytes']and all(row[0]==symbol['address']+4*i for i,row in enumerate(rows)),
        'complete same-extent frame instructions required')
    return rows


def stack_access(op,operands):
    reg=r'x(?:[0-9]|[12][0-9]|30)'
    match=re.fullmatch('('+reg+r')(?:,\s*('+reg+r'))?,\s*\[sp(?:,\s*#(\d+))?\]',operands)
    if op not in ('ldr','ldp','str','stp')or not match:return None
    pair=op in ('ldp','stp')
    if pair!=(match[2]is not None):return None
    start=int(match[3]or'0');return start,start+(16 if pair else 8)


def borrowed_helper(raw,proof):
    rows=instructions(raw,proof);reasons=[];reads=[]
    for i,(_,op,args)in enumerate(rows):
        if op=='ret'and args in ('','x30')and i==len(rows)-1:continue
        if op=='mov'and re.fullmatch(r'x(?:[0-9]|1[0-9]|2[0-8]),\s*x(?:[0-9]|[12][0-9]|30)',args):continue
        interval=stack_access(op,args)
        if op in ('ldr','ldp')and interval is not None and not re.search(r'\bx(?:29|30)\b',args.split('[',1)[0]):reads.append(list(interval));continue
        reasons.append('unsupported borrowed-slot instruction: '+op+' '+args)
    if proof['external_transfers']or proof['unknown_control_transfers']:reasons.append('helper control transfer not closed')
    if rows[-1][1]!='ret':reasons.append('ordinary final return required')
    known=not reasons
    return dict(understood=known,SP_delta_bytes=0 if known else None,additional_below_entry_SP_depth_bytes=0 if known else None,
        read_intervals=reads,read_extent_max_bytes=max((end for _,end in reads),default=0),reasons=reasons,
        zero_own_stack_proven=False,own_allocation_bytes_inferred=False,classification='borrowed-caller-slots'if known else'unknown')


def caller_coverage(raw,proof,frame_bytes,call_sites,helper_symbol,effect):
    rows=instructions(raw,proof);reasons=[];first,last=rows[0],rows[-1]
    if not call_sites:reasons.append('actual helper call site required')
    allocate=re.fullmatch(r'x29,\s*x30,\s*\[sp,\s*#-(\d+)\]!',first[2])if first[1]=='stp'else None
    release=re.fullmatch(r'x29,\s*x30,\s*\[sp\],\s*#(\d+)',rows[-2][2])if len(rows)>1 and rows[-2][1]=='ldp'else None
    size=int(allocate[1])if allocate else None
    if not(allocate and release and size==int(release[1])==frame_bytes and 0<size<=8192 and size%16==0 and last[1]=='ret'and last[2]in ('','x30')):
        reasons.append('matching first allocation/final deallocation/static frame required')
    for i,(address,op,args)in enumerate(rows):
        if i in (0,len(rows)-2,len(rows)-1):continue
        if re.search(r'\b(?:sp|wsp)\b',args):
            interval=stack_access(op,args)
            if not(op=='mov'and re.fullmatch(r'x29,\s*sp',args))and not(interval is not None and size is not None and 0<=interval[0]<interval[1]<=size):
                reasons.append('unsupported or outside-frame SP access')
        direct=op in ('b','cbz','cbnz','tbz','tbnz')or op.startswith('b.')
        if direct:
            literal=re.sub(r'<[^>]+>','',args).split(',')[-1].strip()
            if not re.fullmatch(r'(?:0x)?[0-9a-f]+',literal):reasons.append('unknown caller branch target');continue
            target=int(literal,16)
            if target<=first[0]or target>=last[0]or not any(row[0]==target for row in rows):
                reasons.append('allocation reentry, skipped deallocation, or external tail')
        if op=='bl':
            literal=re.sub(r'<[^>]+>','',args).strip()
            if re.fullmatch(r'(?:0x)?[0-9a-f]+',literal)and first[0]<=int(literal,16)<=last[0]:
                reasons.append('internal BL is outside the normal C-entry shape')
        if op=='ret':reasons.append('early return bypasses deallocation')
    if proof['unknown_control_transfers']:reasons.append('unknown caller control transfer')
    if any(edge['unresolved']for edge in proof['external_transfers']):reasons.append('unresolved caller transfer')
    if any(record['offset']!=0 for edge in proof['external_transfers']if edge['mnemonic']=='bl'for record in edge['resolved_records']):
        reasons.append('C call into a non-entry offset')
    for site in call_sites:
        found=[(i,row)for i,row in enumerate(rows)if row[0]==site['address']]
        if len(found)!=1:reasons.append('helper call site absent');continue
        i,(_,op,args)=found[0];literal=re.sub(r'<[^>]+>','',args).strip()
        if not(0<i<len(rows)-2 and op=='bl'and re.fullmatch(r'(?:0x)?[0-9a-f]+',literal)and int(literal,16)==helper_symbol['address']):
            reasons.append('helper BL must be inside the allocated stable frame')
    if not effect['understood']:reasons.append('helper SP effect unknown')
    if size is None or effect['read_extent_max_bytes']>size:reasons.append('helper load exceeds caller frame')
    return dict(proven=not reasons,caller_frame_bytes=size,compiler_static_frame_bytes=frame_bytes,reasons=reasons,
        normal_function_entry_assumed=True,other_C_calls_return_with_ABI_SP=True,other_C_call_peak_not_proven=True,
        whole_query_stack_bound_proven=False)


def sp_evidence(raw_old,old):
    rows={row['symbol']['symbol']:row for row in old['outlined_input_section_join']['helpers']};result={}
    for name,caller in SP_HELPERS.items():
        row=rows[name];identity=row['identity'];body=old['outlined_bodies'][identity]
        require(row['call_sites']and all(site['caller']==caller for site in row['call_sites']),'exact reviewed helper/caller pair required')
        effect=borrowed_helper(raw_old['outlined_assembly'][identity],body)
        coverage=caller_coverage(raw_old['primary']['assembly'][caller],old['primary']['assembly'][caller],
            old['primary']['object_provenance'][caller]['frame_bytes'],row['call_sites'],row['symbol'],effect)
        result[name]=dict(identity=identity,compiler_helper_frame_bytes=row['compiler_static_frame_bytes'],effect=effect,caller=caller,caller_coverage=coverage,
            previous237_classification_unchanged=body['classification'])
    return result


def property_functions(elf):
    sections={};functions={}
    for line in elf.splitlines():
        section=re.match(r'^\s*\[\s*(\d+)\]\s+(\S+)\s+\S+\s+[0-9a-fA-F]+\s+[0-9a-fA-F]+\s+[0-9a-fA-F]+\s+[0-9a-fA-F]+\s+([A-Z]+)\s+',line)
        if section:sections[section[1]]=(section[2],section[3])
        row=re.match(r'^\s*\d+:\s+([0-9a-fA-F]+)\s+(\d+|0x[0-9a-fA-F]+)\s+FUNC\s+(LOCAL|GLOBAL|WEAK)\s+DEFAULT\s+(\d+)\s+(\S+)\s*$',line)
        if row and(row[5]in C_NAMES or re.fullmatch(r'OUTLINED_FUNCTION_\d+',row[5])):
            require(row[5]not in functions,'unique property-object function required')
            functions[row[5]]=dict(address=int(row[1],16),bytes=int(row[2],16 if row[2].startswith('0x')else 10),binding=row[3],section_index=row[4])
    require(set(C_NAMES)<=set(functions),'both source C anchors required');return sections,functions


def c_symbol(table,name):
    require(name in C_NAMES and name in table and len(table[name])==1,'one actual property C symbol required')
    row=table[name][0]
    require(row['kind']==('T'if name==PUBLIC else't')and 0<row['address']<1<<64 and 0<row['bytes']<=8192 and row['address']%4==row['bytes']%4==0,
        'actual typed bounded property C extent required')
    aliases=sorted({n for n,rows in table.items()for r in rows if r['address']==row['address']and r['bytes']==row['bytes']})
    return dict(symbol=name,address=row['address'],bytes=row['bytes'],aliases=aliases)


def property_target(item,table):
    selected={name:table[name][0]for name in C_NAMES if name in table and len(table[name])==1}
    require(set(selected)==set(C_NAMES),'unambiguous property source anchors required')
    for name in C_NAMES:c_symbol(table,name)
    proof=p.object_proof(OBJECT,item,C_NAMES,selected);sections,functions=property_functions(item['elf_sections_and_symbols'])
    indices={functions[name]['section_index']for name in C_NAMES};deltas={proof[name]['linked_address']-proof[name]['object_address']for name in C_NAMES}
    require(len(indices)==len(deltas)==1,'one measured property input-section translation required')
    index=next(iter(indices));section,flags=sections[index]
    require(section=='.text'and'A'in flags and'X'in flags and'W'not in flags,'non-init property text section required')
    return dict(C_anchors=proof,section_index=index,section=section,linked_minus_object_address=next(iter(deltas))),functions


def reaches_static(proofs,table):
    wanted=table[STATIC][0]
    return any(record['name']==STATIC and all(record[key]==wanted[key]for key in ('kind','address','bytes','ordinal'))and record['offset']==0
        for proof in proofs.values()for edge in proof['external_transfers']for record in edge['resolved_records'])


def local_joins(item,target,functions,C_proofs,table):
    frames=p.stream.frames(item['stack_usage']);tu=p.translation_unit(item['command'].encode(),OBJECT)['translation_unit'];groups={}
    for caller,proof in C_proofs.items():
        for edge in proof['external_transfers']:
            for record in edge['resolved_records']:
                name=record['name']
                if not re.fullmatch(r'OUTLINED_FUNCTION_\d+',name):continue
                require(name in functions,'direct outlined exit must belong to property object')
                local=functions[name]
                require(record['kind']=='t'and record['offset']==0 and local['binding']=='LOCAL'and local['section_index']==target['section_index']and
                    local['address']+target['linked_minus_object_address']==record['address']and local['bytes']==record['bytes']and
                    0<record['bytes']<=LOCAL_BYTES and record['address']%4==record['bytes']%4==0,
                    'exact property-local edge/object/section/extent join required')
                original=[row for row in table[name]if all(row[key]==record[key]for key in ('kind','address','bytes','ordinal'))]
                require(len(original)==1 and name in frames and frames[name]['source']==tu and frames[name]['kind']=='static'and 0<=frames[name]['bytes']<=8192,
                    'actual local ordinal and static same-TU frame required')
                key=(record['address'],record['bytes']);group=groups.setdefault(key,dict(records={},call_sites=[]))
                group['records'][(name,record['ordinal'])]=dict(name=name,**original[0],compiler_static_frame_bytes=frames[name]['bytes'])
                group['call_sites'].append(dict(caller=caller,address=edge['address'],target=edge['target'],mnemonic=edge['mnemonic']))
    require(len(groups)<=LOCAL_CAP,'bounded direct property-local frontier required')
    result={}
    for(address,size),group in sorted(groups.items()):
        records=list(group['records'].values());name=min(row['name']for row in records)
        aliases=sorted({n for n,rows in table.items()for row in rows if row['address']==address and row['bytes']==size})
        key='outlined@'+format(address,'016x')+':'+str(size)
        result[key]=dict(symbol=dict(symbol=name,address=address,bytes=size,aliases=aliases),records=records,call_sites=group['call_sites'])
    return result


def property_command(vmlinux,symbol,local_names=()):
    path=PurePosixPath(str(vmlinux));address,size=symbol['address'],symbol['bytes'];aliases=symbol['aliases'];name=symbol['symbol']
    require(path.is_absolute()and str(path)==str(vmlinux)and '..'not in path.parts and path.name=='vmlinux','canonical same-vmlinux path required')
    require(name in C_NAMES or(name in local_names and re.fullmatch(r'OUTLINED_FUNCTION_\d+',name)),'only source-bound property frontier allowed')
    require(set(symbol)=={'symbol','address','bytes','aliases'}and type(address)is type(size)is int and 0<address<1<<64 and
        0<size<=(8192 if name in C_NAMES else LOCAL_BYTES)and address%4==size%4==0 and address+size<1<<64 and
        type(aliases)is list and name in aliases and len(aliases)==len(set(aliases))<=32,'bounded actual property extent/aliases required')
    return ['aarch64-linux-gnu-objdump','-d','--disassemble-zeroes','--start-address='+hex(address),'--stop-address='+hex(address+size),str(path)]


def property_evidence(raw,stack_data,expected_objects_root):
    require(set(raw)=={'schema','retained','property_object','assembly','tools'}and raw['schema']==RAW_SCHEMA,'exact property frontier raw bundle required')
    table=p.linked_symbols(stack_data['linked_nm']);target,functions=property_target(raw['property_object'],table)
    require(PUBLIC in raw['assembly'],'public property body required')
    C_proofs={PUBLIC:p.transfers(raw['assembly'][PUBLIC],c_symbol(table,PUBLIC),table)}
    public_locals=local_joins(raw['property_object'],target,functions,C_proofs,table)
    initial_locals={key:p.transfers(raw['assembly'][key],row['symbol'],table)for key,row in public_locals.items()}
    need_static=reaches_static({**C_proofs,**initial_locals},table)
    require((STATIC in raw['assembly'])==need_static,'static C body only when actually reached')
    if need_static:C_proofs[STATIC]=p.transfers(raw['assembly'][STATIC],c_symbol(table,STATIC),table)
    locals_all=local_joins(raw['property_object'],target,functions,C_proofs,table)
    require(set(raw['assembly'])==set(C_proofs)|set(locals_all),'exact C/direct-local capture frontier required')
    local_proofs={key:(initial_locals[key]if key in initial_locals else p.transfers(raw['assembly'][key],row['symbol'],table))for key,row in locals_all.items()}
    require(len(raw['tools'])==1+len(raw['assembly']),'one tool per new object/body required')
    tools={tool['capture_id']:tool for tool in raw['tools']};require(len(tools)==len(raw['tools']),'no duplicate capture ids')
    object_tool=tools['object'];argv=object_tool['argv'];require(len(argv)==5 and argv[:4]==['aarch64-linux-gnu-readelf','--wide','--sections','--symbols']and argv[-1].endswith('/'+OBJECT),'property object argv required')
    root=argv[-1][:-len(OBJECT)-1]
    require(root==expected_objects_root,'property root must equal validated retained same-Image object root')
    expected={'object':(argv,raw['property_object']['elf_sections_and_symbols'])}
    for name in C_proofs:expected[name]=(property_command(root+'/vmlinux',c_symbol(table,name)),raw['assembly'][name])
    for key,row in locals_all.items():expected[key]=(property_command(root+'/vmlinux',row['symbol'],tuple(r['name']for r in row['records'])),raw['assembly'][key])
    require(set(tools)==set(expected),'exact bounded property tool inventory required')
    for key,(wanted,text)in expected.items():
        tool=tools[key];require(set(tool)=={'capture_id','argv','returncode','stdout_sha256','stderr'}and tool['argv']==wanted and tool['returncode']==0 and
            type(tool['stderr'])is str and tool['stdout_sha256']==sha(text.encode()),'actual property tool/text binding required')
    return dict(property_input_section=target,property_C_bodies=C_proofs,property_local_joins=locals_all,property_local_bodies=local_proofs,
        static_C_body_captured=need_static,additional_property_object_reads=1,additional_nm_dumps=0,additional_old_helper_dumps=0,
        recursive_expansion=False,property_local_SP_effect_proven=False)


def finish(raw,stack_data,old):
    primary_target=next(iter(p.NEW_OBJECTS));primary_argv=raw['retained']['primary']['tools'][0]['argv']
    # Retained237 verify/collect has already validated this primary argv/root.
    expected_root=primary_argv[-1][:-len(primary_target)-1]
    frontier=property_evidence(raw,stack_data,expected_root);C_proofs=frontier['property_C_bodies'];local_proofs=frontier['property_local_bodies']
    all_bodies={**{'primary:'+name:row for name,row in old['primary']['assembly'].items()},
        **{'retained:'+name:row for name,row in old['outlined_bodies'].items()},**C_proofs,**local_proofs}
    expanded={(row['symbol']['address'],row['symbol']['bytes'])for row in all_bodies.values()};remaining={}
    for proof in all_bodies.values():
        for edge in proof['external_transfers']:
            for record in edge['resolved_records']:
                if (record['address'],record['bytes'])not in expanded or record['name']in p.SCHEDULER or record['offset']!=0:
                    remaining[(record['name'],record['address'],record['bytes'],record['ordinal'],record['offset'])]=record
    return dict(schema=SCHEMA,retained=old,borrowed_slot_evidence=sp_evidence(raw['retained'],old),**frontier,
        unexpanded_external_records=list(remaining.values()),unresolved_or_indirect_present=any(row['unknown_control_transfers']or any(edge['unresolved']for edge in row['external_transfers'])for row in all_bodies.values()),
        unexpanded_scheduler_boundaries=list(p.SCHEDULER),whole_query_peak_proven=False,**LIMITS)


def verify(raw,stack_data):
    require(type(raw)is dict and raw.get('schema')==RAW_SCHEMA,'fresh238 property raw schema required')
    return finish(raw,stack_data,retained.verify(raw['retained'],stack_data))


def collect(objects,stack_data,nm,save):
    objects=Path(objects);raw=dict(schema=RAW_SCHEMA,retained=None,property_object={},assembly={},tools=[])
    def save_old(item):raw['retained']=item;save(raw)
    old=retained.collect(objects,stack_data,nm,save_old)
    def capture(key,argv):
        done=subprocess.run(list(map(str,argv)),stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=False,timeout=120)
        require(len(done.stdout)<=TEXT_CAP and len(done.stderr)<=65536,'bounded property tool text required')
        text=done.stdout.decode();raw['tools'].append(dict(capture_id=key,argv=list(map(str,argv)),returncode=done.returncode,stdout_sha256=sha(done.stdout),stderr=done.stderr.decode(errors='replace')))
        if key=='object':raw['property_object']['elf_sections_and_symbols']=text
        else:raw['assembly'][key]=text
        save(raw);require(done.returncode==0,'property capture failed; raw evidence retained');return text
    path=PurePosixPath(OBJECT);cmd=(objects/str(path.with_name('.'+path.name+'.cmd'))).read_bytes()
    require(len(cmd)<=TEXT_CAP,'bounded property command required');raw['property_object']=dict(command=cmd.decode(),command_sha256=sha(cmd));save(raw)
    relative=p.stream.compiler_stack_path(cmd,OBJECT);usage=(objects/relative).read_text();require(len(usage.encode())<=TEXT_CAP,'bounded property SU required')
    raw['property_object'].update(stack_usage=usage,stack_sha256=sha(usage.encode()),stack_relative=str(relative));save(raw)
    elf=capture('object',['aarch64-linux-gnu-readelf','--wide','--sections','--symbols',objects/OBJECT]);raw['property_object']['elf_evidence_sha256']=sha(elf.encode());save(raw)
    table=p.linked_symbols(nm);target,functions=property_target(raw['property_object'],table)
    capture(PUBLIC,property_command(objects/'vmlinux',c_symbol(table,PUBLIC)))
    C_proofs={PUBLIC:p.transfers(raw['assembly'][PUBLIC],c_symbol(table,PUBLIC),table)}
    def capture_locals():
        joined=local_joins(raw['property_object'],target,functions,C_proofs,table);proofs={}
        for key,row in joined.items():
            if key not in raw['assembly']:capture(key,property_command(objects/'vmlinux',row['symbol'],tuple(r['name']for r in row['records'])))
            proofs[key]=p.transfers(raw['assembly'][key],row['symbol'],table)
        return proofs
    locals_public=capture_locals()
    if reaches_static({**C_proofs,**locals_public},table):
        capture(STATIC,property_command(objects/'vmlinux',c_symbol(table,STATIC)))
        C_proofs[STATIC]=p.transfers(raw['assembly'][STATIC],c_symbol(table,STATIC),table);capture_locals()
    return finish(raw,dict(objects=stack_data['objects'],linked_nm=nm),old)
