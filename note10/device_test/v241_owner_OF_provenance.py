"""Fixed OF/owner caller provenance; reused same-Image helpers, no runtime bound."""
from pathlib import Path, PurePosixPath
import json
import re
import subprocess
import v238_of_frame_property as property_reader
import v240_native_prepare as guarded
p=property_reader.p
outlined=property_reader.retained
require,sha=p.require,p.sha
SOURCE_GUARDS,CONFIG,LIMITS=property_reader.SOURCE_GUARDS,property_reader.CONFIG,property_reader.LIMITS
BUNDLE_CAP,TEXT_CAP=property_reader.BUNDLE_CAP,property_reader.TEXT_CAP
RAW_SCHEMA='note10-v241-OF-owner-property-raw-v1'
SCHEMA='note10-v241-OF-owner-property-evidence-v1'
SELECTED_RAW_SCHEMA='note10-v241-OF-owner-outlined-raw-v1'
OWNER_OBJECT='arch/arm64/mm/init.o'
OWNER_CALLERS=('n233_capture_cpu_node_consistency','n233_clear_consistency')
OBJECT,C_NAMES,PUBLIC,STATIC=property_reader.OBJECT,property_reader.C_NAMES,property_reader.PUBLIC,property_reader.STATIC
property_target,c_symbol,local_joins=property_reader.property_target,property_reader.c_symbol,property_reader.local_joins
reaches_static,property_command,sp_evidence=property_reader.reaches_static,property_reader.property_command,property_reader.sp_evidence


def partition(raw_primary,primary,stack_data,nm,guarded_raw,target):
    table=p.linked_symbols(nm);first=next(iter(p.NEW_OBJECTS));root=raw_primary['tools'][0]['argv'][-1][:-len(first)-1]
    verified=guarded.verify_guarded(guarded_raw,target,nm,stack_data,root)
    owner_proofs={};owner_sections={}
    for caller,proof in primary['assembly'].items():
        outlined_records=[record for edge in proof['external_transfers']for record in edge['resolved_records']if record['name'].startswith('OUTLINED_FUNCTION_')]
        if not outlined_records or caller in outlined.ANCHORS:continue
        require(caller in OWNER_CALLERS,'unsupported non-OF outlined caller')
        require(caller in table and len(table[caller])==1,'one actual owner caller definition required')
        item=stack_data['objects'][OWNER_OBJECT]
        proven=p.object_proof(OWNER_OBJECT,item,(caller,),{caller:table[caller][0]})[caller]
        require(primary['object_provenance'][caller]==proven and proven['translation_unit']==target['owner_TU']['translation_unit'],'same command/SU/ELF owner caller required')
        local=[]
        for line in item['elf_sections_and_symbols'].splitlines():
            row=re.match(r'^\s*\d+:\s+([0-9a-fA-F]+)\s+(\d+|0x[0-9a-fA-F]+)\s+FUNC\s+(LOCAL|GLOBAL)\s+DEFAULT\s+(\d+)\s+(\S+)\s*$',line)
            if row and row[5]==caller:local.append(row.groups())
        require(len(local)==1,'one actual owner caller input section required')
        index=local[0][3];deltas={row['linked_address']-row['address']for row in target['function_provenance'].values()if row['section_index']==index}
        require(len(deltas)==1 and proven['linked_address']-proven['object_address']==next(iter(deltas)),'owner caller must use measured same-input-section translation')
        owner_sections[caller]=dict(section_index=index,linked_minus_object_address=next(iter(deltas)))
        require(proof==p.transfers(raw_primary['assembly'][caller],proof['symbol'],table),'actual primary owner body/transfer identity required')
        owner_proofs[caller]=proof
    # A local analysis view is used only for the unchanged nine-anchor OF join.
    # The complete primary and all nm rows remain untouched in raw/result evidence.
    OF_view={**primary,'assembly':{name:primary['assembly'][name]for name in outlined.ANCHORS}}
    OF=outlined.outline_joins(raw_primary,OF_view,nm)
    records=guarded.owner_local_records(stack_data,target,owner_proofs);reused={};joins=[]
    raw_sha=sha((json.dumps(guarded_raw,indent=2,sort_keys=True)+'\n').encode())
    for caller,proof in owner_proofs.items():
        for edge in proof['external_transfers']:
            for record in edge['resolved_records']:
                if not record['name'].startswith('OUTLINED_FUNCTION_'):continue
                original=[row for row in table[record['name']]if all(row[k]==record[k]for k in ('kind','address','bytes','ordinal'))]
                key='owner-outlined@'+format(record['address'],'016x')+':'+str(record['bytes'])
                require(record['offset']==0 and len(original)==1 and (record['address'],record['bytes'])in records and key in verified['direct_owner_local_bodies'],'exact already captured owner entry/ordinal required')
                body=verified['direct_owner_local_bodies'][key];symbol=body['symbol']
                require(symbol['address']==record['address']and symbol['bytes']==record['bytes']and record['name']in symbol['aliases'],'owner helper must bind exact captured extent')
                reused[key]=body
                helper_frame=guarded.stream_candidate.frames(stack_data['objects'][OWNER_OBJECT]['stack_usage'])[record['name']]['bytes']
                require(0<=helper_frame<=8192,'bounded measured owner-helper static SU required')
                joins.append(dict(caller=caller,call_site=edge['address'],target=edge['target'],mnemonic=edge['mnemonic'],nm_record=dict(name=record['name'],**original[0]),
                    owner_object=OWNER_OBJECT,owner_input_section=owner_sections[caller],translation_unit=target['owner_TU']['translation_unit'],guarded_body_key=key,guarded_raw_sha256=raw_sha,body_sha256=body['disassembly_sha256'],
                    helper_compiler_static_frame_bytes=helper_frame,helper_static_frame_is_not_own_stack_proof=True,zero_own_stack_inferred_from_SU=False))
    return dict(OF=OF,owner_reuse=joins,owner_reused_bodies=reused)


def finish_selected(raw,stack_data,primary,guarded_raw,guard_target):
    require(set(raw)=={'schema','primary','outlined_assembly','tools','owner_reuse'}and raw['schema']==SELECTED_RAW_SCHEMA,'exact bounded outlined bundle required')
    nm=stack_data['linked_nm'];table=p.linked_symbols(nm);domains=partition(raw['primary'],primary,stack_data,nm,guarded_raw,guard_target);joins=domains['OF']
    require(raw['owner_reuse']==domains['owner_reuse'],'exact explicit owner reuse records required')
    helpers=joins['helpers'];identities={row['identity']for row in helpers}
    require(set(raw['outlined_assembly'])==identities and len(raw['tools'])==13,'exact thirteen captured helper bodies required')
    # Same object root as the already authenticated primary readelf/objdump commands.
    target=next(iter(p.NEW_OBJECTS));object_argv=raw['primary']['tools'][0]['argv'];root=object_argv[-1][:-len(target)-1]
    classified={}
    for row,tool in zip(helpers,raw['tools']):
        text=raw['outlined_assembly'][row['identity']]
        require(set(tool)=={'argv','returncode','stdout_sha256','stderr'}and tool['returncode']==0 and type(tool['stderr'])is str and
            tool['argv']==outlined.helper_command(root+'/vmlinux',row['symbol'])and tool['stdout_sha256']==sha(text.encode()),'actual same-Image helper argv/text binding required')
        classified[row['identity']]=outlined.classify_leaf(text,row['symbol'],table,row['compiler_static_frame_bytes'])
    strcmp=primary['assembly']['strcmp']['symbol']
    aliases=primary['assembly']['strcmp']['alias_records']
    require({'strcmp','__pi_strcmp'}<={row['name']for row in aliases}and all(row['address']==strcmp['address']and row['bytes']==strcmp['bytes']for row in aliases),
        'strcmp/__pi_strcmp must bind the already captured same body')
    strcmp_leaf=outlined.classify_leaf(raw['primary']['assembly']['strcmp'],strcmp,table,None)
    expanded={(row['symbol']['address'],row['symbol']['bytes'])for row in (*primary['assembly'].values(),*classified.values(),*domains['owner_reused_bodies'].values())}
    remaining={}
    for row in (*primary['assembly'].values(),*classified.values(),*domains['owner_reused_bodies'].values(),strcmp_leaf):
        for edge in row['external_transfers']:
            for record in edge['resolved_records']:
                if (record['address'],record['bytes'])not in expanded or record['name']in p.SCHEDULER:
                    remaining[(record['name'],record['address'],record['bytes'],record['ordinal'])]=record
    return dict(schema='note10-v241-OF-owner-outlined-evidence-v1',primary=primary,owner_reuse=domains['owner_reuse'],owner_reused_bodies=domains['owner_reused_bodies'],outlined_input_section_join=joins,outlined_bodies=classified,strcmp_same_body_leaf=strcmp_leaf,
        outlined_capture_count=13,additional_object_reads=0,additional_nm_dumps=0,additional_strcmp_dumps=0,recursive_expansion=False,
        unexpanded_external_records=list(remaining.values()),
        unexpanded_scheduler_boundaries=list(p.SCHEDULER),per_function_proof_is_not_a_chain_bound=True,**LIMITS)


def collect_selected(objects,stack_data,nm,save,guarded_raw,guard_target):
    raw=dict(schema=SELECTED_RAW_SCHEMA,primary=None,outlined_assembly={},tools=[],owner_reuse=[])
    def save_primary(item):raw['primary']=item;save(raw)
    primary=p.collect(objects,stack_data,nm,save_primary)
    domains=partition(raw['primary'],primary,stack_data,nm,guarded_raw,guard_target);joins=domains['OF'];raw['owner_reuse']=domains['owner_reuse'];save(raw)
    for row in joins['helpers']:
        argv=outlined.helper_command(Path(objects)/'vmlinux',row['symbol'])
        done=subprocess.run(argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=False,timeout=120)
        require(len(done.stdout)<=TEXT_CAP and len(done.stderr)<=65536,'bounded outlined tool text required')
        raw['tools'].append(dict(argv=argv,returncode=done.returncode,stdout_sha256=sha(done.stdout),stderr=done.stderr.decode(errors='replace')))
        raw['outlined_assembly'][row['identity']]=done.stdout.decode();save(raw)
        require(done.returncode==0,'outlined capture failed; raw diagnostic retained')
    return finish_selected(raw,dict(objects=stack_data['objects'],linked_nm=nm),primary,guarded_raw,guard_target)


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
        **{'retained:'+name:row for name,row in old['outlined_bodies'].items()},
        **{'owner:'+name:row for name,row in old['owner_reused_bodies'].items()},**C_proofs,**local_proofs}
    expanded={(row['symbol']['address'],row['symbol']['bytes'])for row in all_bodies.values()};remaining={}
    for proof in all_bodies.values():
        for edge in proof['external_transfers']:
            for record in edge['resolved_records']:
                if (record['address'],record['bytes'])not in expanded or record['name']in p.SCHEDULER or record['offset']!=0:
                    remaining[(record['name'],record['address'],record['bytes'],record['ordinal'],record['offset'])]=record
    return dict(schema=SCHEMA,retained=old,borrowed_slot_evidence=sp_evidence(raw['retained'],old),**frontier,
        unexpanded_external_records=list(remaining.values()),unresolved_or_indirect_present=any(row['unknown_control_transfers']or any(edge['unresolved']for edge in row['external_transfers'])for row in all_bodies.values()),
        unexpanded_scheduler_boundaries=list(p.SCHEDULER),whole_query_peak_proven=False,**LIMITS)


def verify(raw,stack_data,guarded_raw,target):
    require(type(raw)is dict and raw.get('schema')==RAW_SCHEMA,'fresh241 OF/owner raw schema required')
    primary=p.verify(raw['retained']['primary'],stack_data)
    selected=finish_selected(raw['retained'],stack_data,primary,guarded_raw,target)
    return finish(raw,stack_data,selected)


def collect(objects,stack_data,nm,save,guarded_raw,guard_target):
    objects=Path(objects);raw=dict(schema=RAW_SCHEMA,retained=None,property_object={},assembly={},tools=[])
    def save_old(item):raw['retained']=item;save(raw)
    old=collect_selected(objects,stack_data,nm,save_old,guarded_raw,guard_target)
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
