'''290 connected nonterminal current-owner storage preparation; PC build only.'''
import json
import subprocess
from pathlib import Path
import v288_native_prepare as retained
import v286_native_prepare as metadata
p,require,sha,bind=retained.p,retained.require,retained.sha,retained.bind
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
WORKFLOW='.github/workflows/note10-v290-native-prepare.yml';JOB='v290-native-prepare'
BUILD_SCHEMA='note10-v290-owned-storage-PC-build-v1'
CONTEXT_SCHEMA='note10-v290-owned-storage-PC-public-input-v1'
MANIFEST_SCHEMA='note10-v290-owned-storage-PC-sealed-members-v1'
CAPTURE_SCHEMA,TARGET_SCHEMA=retained.CAPTURE_SCHEMA,retained.TARGET_SCHEMA
decode_binding=retained.decode_binding
NEW_FILES=('v290_preparation_storage.h','v290_preparation_storage.c','v290_preparation_storage.inc',
 'v290_preparation_storage_fixture.c','test_v290_preparation_storage.py','v290_native_prepare.py')
ADDED_MEMBERS=('storage-evidence.json','storage-object.o','storage-object.cmd','storage-object.su','storage-object-elf.log')
SUCCESS_MEMBERS=(*retained.SUCCESS_MEMBERS,*ADDED_MEMBERS);METADATA_TYPES=metadata.METADATA_TYPES
STORAGE_TARGET='arch/arm64/mm/v290_preparation_storage.o'
STORAGE_NAMES=('n290_plan_storage','n290_prepare_storage_locked','n290_readback_zero','n290_layout_witness')
STORAGE_ABI={'n290_size_storage':160,'n290_align_storage':8,'n290_offset_digest':88,'n290_pool_offset':44896}
SEAL_CALL=b'''        if(!error)error=n278_seal_once(N279_SEAL,prepared,&n210_destination,context,
            n210_result.descriptor_sha256,&n210_result,n210_spent,&n217_kernel_state);
'''
STORAGE_CALL=b'''        if(!error)error=n290_prepare_storage_locked(N290_STORAGE,N279_SEAL,prepared,&n210_destination,context,
            &n210_result,ctx,((struct n285_workspace *)n226_source_pool)->readback,N217_CHUNK);
'''

def source_pins():
    value=retained.source_pins();value.pop(retained.WORKFLOW)
    value.update({'note10/device_test/'+n:sha(p.ordinary(HERE/n))for n in NEW_FILES})
    value[WORKFLOW]=sha(p.ordinary(ROOT/WORKFLOW));return value

def public_context(head,passed):
    p.hexid(head,40)
    require(set(passed)=={'passed','groups','variants','assertions','result_sha256'} and passed['passed'] is True and
      tuple(passed[k]for k in ('groups','variants','assertions'))==(1,1,1),'new290 storage conjunction only')
    p.hexid(passed['result_sha256'])
    return dict(schema=CONTEXT_SCHEMA,source_head=head,source_sha256=source_pins(),new_fixture_PASS=passed,old_tests_replayed=False,PC_only=True,hardware_ready=False)

def owner_overlay(raw):
    include=b'#include "v285_current_cpu_metadata.inc"\n'
    require(raw.count(include)==raw.count(SEAL_CALL)==1 and b'n290_'not in raw,'exact effective owner seam')
    guard=b'    if(n217_kernel_state.spent)return -EALREADY;';clear=b'    memset(n226_source_pool,0,sizeof(n226_source_pool));'
    require(raw.count(guard)==raw.count(clear)==1 and raw.index(guard)<raw.index(clear)<raw.index(SEAL_CALL),'spent before pool clear')
    changed=raw.replace(include,include+b'#include "v290_preparation_storage.inc"\n',1).replace(SEAL_CALL,SEAL_CALL+STORAGE_CALL,1)
    require(changed.count(b'error=n290_prepare_storage_locked(')==1 and changed.index(b'error=n285_prepare_metadata(')<changed.index(SEAL_CALL)<changed.index(STORAGE_CALL)<changed.index(b'stats->error='),'connected storage after readback/seal before cleanup')
    require(b'memzero_explicit(n226_source_pool,N226_WORKSPACE_BYTES)'in changed and b'memzero_explicit(n226_source_pool+N226_STAGE_OFFSET,N217_CHUNK)'in changed,'descriptor survives cleanup')
    return changed

def install_binding(source,buffers):
    value=retained.install_binding(source,buffers);owner=source/'arch/arm64/mm/v226_source_stream_kernel.c'
    after=owner_overlay(p.ordinary(owner));owner.write_bytes(after)
    value['compiler_inputs']['arch/arm64/mm/v226_source_stream_kernel.c']['after_sha256']=sha(after)
    for name in ('current_owner_seal','current_cpu_metadata'):value[name]['owner_after_sha256']=sha(after)
    copied={}
    for name in NEW_FILES[:3]:
        target=source/'arch/arm64/mm'/name;require(not target.exists(),'fresh290 input')
        raw=buffers['note10/device_test/'+name];target.write_bytes(raw);copied[str(target.relative_to(source))]=sha(raw)
    make=source/'arch/arm64/mm/Makefile';old=p.ordinary(make)
    line=b'obj-$(CONFIG_NOTE10_V210_NATIVE_PREPARE) += v290_preparation_storage.o\n'
    require(b'v290_preparation_storage'not in old and old.endswith(b'\n'),'single new storage TU');make.write_bytes(old+line)
    for name in ('current_owner_seal','current_cpu_metadata'):value[name]['Kbuild_after_sha256']=sha(old+line)
    value['preparation_storage']=dict(owner_after_sha256=sha(after),Kbuild_after_sha256=sha(old+line),copied=copied,pool_offset=44896,descriptor_bytes=160,new_BSS_bytes=0,new_pool_bytes=0,destination_bytes=33554432,destination_storage_bytes=49152,terminal_transfer=False)
    return value

def inventory_metadata(entries,passed):
    require(len(SUCCESS_MEMBERS)==len(set(SUCCESS_MEMBERS))==53,'fixed53 post schema')
    allowed=set(SUCCESS_MEMBERS)-{'members.json'}
    require(type(passed)is bool and type(entries)is list and 0<len(entries)<=52 and all(type(row)is dict and set(row)==set(METADATA_TYPES)and all(type(row[k])is kind for k,kind in METADATA_TYPES.items())for row in entries),'bounded exact metadata types')
    sizes={row['name']:row['bytes']for row in entries}
    require(len(sizes)==len(entries)and 'result.json'in sizes and set(sizes)<=allowed and(not passed or set(sizes)==allowed),'closed new inventory')
    require(all(row['regular']and not row['symlink']and 0<row['bytes']<=67108864 for row in entries)and sum(sizes.values())<=134217728,'unchanged transport caps');return sizes

_code_bind=retained._code_bind
_base_verify=_code_bind(retained.verify_metadata,dict(retained.verify_metadata.__globals__),{
 'note10-v288-CPU-metadata-raw-v1':'note10-v290-CPU-metadata-raw-v1','note10-v288-CPU-metadata-target-v1':'note10-v290-CPU-metadata-target-v1'})

def verify_metadata(raw,linked):
    value=_base_verify(raw,linked)
    # Unordered inventory only; retain every full row and duplicate.
    value['explicit_unclosed_boundaries'].sort(key=lambda row:json.dumps(row,sort_keys=True,separators=(',',':')))
    return value

_base_collect=_code_bind(retained.collect_binding,{**retained.collect_binding.__globals__,'verify_metadata':verify_metadata},{
 'note10-v288-CPU-metadata-raw-v1':'note10-v290-CPU-metadata-raw-v1','note10-v288-seal-frontier-v1':'note10-v290-seal-frontier-v1','note10-v288-seal-order-PC-target-v1':'note10-v290-seal-order-PC-target-v1'})

def verify_storage(raw,linked):
    require(raw['schema']=='note10-v290-storage-raw-v1'and raw['complete']is True and raw['linked_nm_sha256']==sha(linked.encode())and set(raw['bodies'])==set(STORAGE_NAMES),'fresh exact storage capture')
    binding=raw['compiler_input_binding']
    expected={'arch/arm64/mm/'+name:raw['source_sha256']['note10/device_test/'+name]for name in NEW_FILES[:3]}
    require(binding['copied']==expected and binding['pool_offset']==44896 and binding['descriptor_bytes']==160 and binding['new_BSS_bytes']==binding['new_pool_bytes']==0 and binding['destination_bytes']==33554432 and binding['destination_storage_bytes']==49152 and binding['terminal_transfer']is False,'exact generated source/storage binding')
    scoped=metadata.seal_base;table=scoped.scoped.reader.linked_symbols(linked)
    targets={metadata.OWNER_TARGET:('n226_ingest_prepared_locked','n290_prepare_storage_locked','n290_readback_zero'),STORAGE_TARGET:('n290_plan_storage','n290_layout_witness')}
    require(set(raw['objects'])==set(targets),'two exact storage TUs')
    contexts={target:scoped.provenance(target,roots,raw['objects'][target],table)for target,roots in targets.items()}
    abi=scoped.scoped.object_symbols(raw['objects'][STORAGE_TARGET]['nm'])
    require(all(len(abi[n])==1 and abi[n][0][1]=='A'and int(abi[n][0][2],16)==v for n,v in STORAGE_ABI.items()),'actual storage ABI')
    obj=metadata.retained._ENV['metadata_object_evidence'](raw['objects'][STORAGE_TARGET]['elf'],raw['objects'][STORAGE_TARGET]['usage'])
    require(obj['writable_section_bytes']==0,'storage TU writable0')
    frames={};frontiers=[]
    for name,item in raw['bodies'].items():
        record=item['record'];require(record['name']==name and len(table.get(name,()))==1 and record==dict(name=name,**table[name][0],offset=0),'exact storage linked identity')
        target=STORAGE_TARGET if name in('n290_plan_storage','n290_layout_witness')else metadata.OWNER_TARGET
        context,_,reader=contexts[target];source=reader(context,record,False)
        require(source['section_index']in context['deltas']and source['object_address']+context['deltas'][source['section_index']]==record['address'],'actual source/section/entry')
        symbol=scoped.scoped.symbol_extent(table,name,record,False)
        proof=scoped.scoped.scoped_transfers(item['body'],symbol,table)
        require(not proof['unknown_control_transfers'],'direct new core transfers only')
        require(0<=source['frame']['bytes']<=4096,'source-coupled static SU cap4096')
        frames[name]=dict(source=source,static_SU_bytes=source['frame']['bytes'],callee_peaks_included=False)
        for edge in proof['external_transfers']:
            require(edge['mnemonic']in('b','bl')and not edge['unresolved']and edge['resolved_records']and all(r['offset']==0 for r in edge['resolved_records']),'direct exact new edge')
            if not any(r['name']in STORAGE_NAMES for r in edge['resolved_records']):frontiers.append(dict(caller=name,edge=edge,peak_bytes=None))
    owner=raw['owner'];record=owner['record']
    require(record['name']=='n226_ingest_prepared_locked'and len(table[record['name']])==1 and record==dict(name=record['name'],**table[record['name']][0],offset=0),'actual owner identity')
    symbol=scoped.scoped.symbol_extent(table,record['name'],record,False)
    edges=scoped.scoped.scoped_transfers(owner['body'],symbol,table)['external_transfers']
    seal=[e for e in edges if any(r['name']=='n278_seal_once'for r in e['resolved_records'])]
    storage=[e for e in edges if any(r['name']=='n290_prepare_storage_locked'for r in e['resolved_records'])]
    require(len(seal)==len(storage)==1 and seal[0]['address']<storage[0]['address'],'unique actual post-seal storage call')
    require(sum(v['static_SU_bytes']for v in frames.values())<=8192,'new selected static SU sum cap8192')
    frontiers.sort(key=lambda row:json.dumps(row,sort_keys=True,separators=(',',':')))
    value=dict(schema='note10-v290-storage-target-v1',**{k:raw[k]for k in('source_head','run_id','build_evidence_id','source_sha256')},ABI=STORAGE_ABI,frames=frames,actual_owner_callers=1,seal_before_storage=True,new_TU_writable_bytes=0,existing_pool_bytes=49152,existing_destination_bytes=33554432,new_pool_bytes=0,new_reservation_bytes=0,compiled_storage_capacity_bytes=49152,runtime_storage_initialization_observed=False,explicit_unclosed_boundaries=frontiers,whole_stack_bound_proven=False,own_SP_instruction_proof=False,compiled_storage_phase='nonterminal-STORAGE_PREPARED',adapter_record_installed=False,final_metadata_qualified=False,terminal_transfer=False,authoritative_ADT=False,hardware_ready=False,physical_ready=False)
    return json.loads(json.dumps(value))

def collect_binding(objects,out,result,run,linked):
    value=_base_collect(objects,out,result,run,linked)
    base=json.loads(p.ordinary(out/'cpu-metadata-evidence.json',16777216));binding=result['preparation']['watchdog_binding']['preparation_storage']
    raw=dict(schema='note10-v290-storage-raw-v1',**{k:result[k]for k in('source_head','run_id','build_evidence_id','source_sha256')},complete=False,linked_nm_sha256=sha(linked.encode()),compiler_input_binding=binding,objects={metadata.OWNER_TARGET:base['objects'][metadata.OWNER_TARGET]},bodies={},tools=[])
    def persist():
        require(len(json.dumps(raw).encode())<=8388608,'bounded storage evidence');p.save(out/'storage-evidence.json',raw)
    def capture(argv):
        done=subprocess.run(list(map(str,argv)),stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=120)
        raw['tools'].append(dict(argv=list(map(str,argv)),returncode=done.returncode,stdout_sha256=sha(done.stdout)));persist()
        require(done.returncode==0 and 0<len(done.stdout)<=8388608 and len(done.stderr)<=65536,'bounded storage tool');return done.stdout.decode()
    try:
        table=metadata.seal_base.scoped.reader.linked_symbols(linked);rel=Path(STORAGE_TARGET)
        command=p.ordinary(objects/rel.with_name('.'+rel.name+'.cmd'))
        usage=p.ordinary(objects/metadata.stream_candidate.compiler_stack_path(command,STORAGE_TARGET)).decode()
        raw['objects'][STORAGE_TARGET]=dict(command=command.decode(),command_sha256=sha(command),usage=usage,usage_sha256=sha(usage.encode()),nm=capture(['aarch64-linux-gnu-nm','--format=posix','--print-size',objects/STORAGE_TARGET]),elf=capture(['aarch64-linux-gnu-readelf','--wide','--sections','--symbols',objects/STORAGE_TARGET]),object_sha256=sha(p.ordinary(objects/STORAGE_TARGET,67108864)))
        for name in STORAGE_NAMES:
            require(len(table.get(name,()))==1,'unique new source root');record=dict(name=name,**table[name][0],offset=0)
            raw['bodies'][name]=dict(record=record,body=capture(['aarch64-linux-gnu-objdump','-d','--disassemble-zeroes','--start-address='+hex(record['address']),'--stop-address='+hex(record['address']+record['bytes']),objects/'vmlinux']))
        raw['owner']=next(dict(record=base['records'][i],body=body)for i,body in base['bodies'].items()if base['records'][i]['name']=='n226_ingest_prepared_locked')
        context=metadata.seal_base.provenance(metadata.OWNER_TARGET,('n226_ingest_prepared_locked',),raw['objects'][metadata.OWNER_TARGET],table)[0]
        source=Path(context['TU']['translation_unit']).parent
        require(sha(p.ordinary(source/'v226_source_stream_kernel.c'))==binding['owner_after_sha256']and sha(p.ordinary(source/'Makefile'))==binding['Kbuild_after_sha256'],'actual storage owner/Kbuild')
        for path,digest in binding['copied'].items():require(sha(p.ordinary(source/Path(path).name))==digest,'actual storage compiler input')
        (out/'storage-object.o').write_bytes(p.ordinary(objects/STORAGE_TARGET,67108864));(out/'storage-object.cmd').write_bytes(command)
        (out/'storage-object.su').write_text(usage);(out/'storage-object-elf.log').write_text(raw['objects'][STORAGE_TARGET]['elf'])
        raw['complete']=True;persist();result['preparation_storage_target']=verify_storage(raw,linked)
        result.update(storage_runtime_callers=1,runtime_storage_initialization_observed=False,storage_phase_nonterminal=True,hardware_ready=False,physical_ready=False);return value
    except BaseException as error:
        raw.update(complete=False,rejection=str(error)[:2048]);persist();raise

_ENV={**retained._ENV,**{name:globals()[name]for name in('WORKFLOW','JOB','BUILD_SCHEMA','CONTEXT_SCHEMA','MANIFEST_SCHEMA','SUCCESS_MEMBERS','source_pins','public_context','install_binding','collect_binding')}}
run_build=_code_bind(retained.run_build,_ENV,{'note10/private/v288-ci-native-prepare':'note10/private/v290-ci-native-prepare','v288':'v290','"-v288-epilogue-window"':'"-v290-preparation-storage"'})
seal=bind(retained.seal,{**retained.seal.__globals__,**_ENV,'inventory_metadata':inventory_metadata})
_ENV.update(run_build=run_build,seal=seal)
main=bind(retained.main,_ENV)

def audit_api():
    require(run_build.__globals__['install_binding']is install_binding and run_build.__globals__['collect_binding']is collect_binding and main.__globals__['seal']is seal and seal.__globals__['inventory_metadata']is inventory_metadata,'real new build/capture/seal callbacks')
    require(CAPTURE_SCHEMA==retained.CAPTURE_SCHEMA and TARGET_SCHEMA==retained.TARGET_SCHEMA,'watchdog276 domain preserved')

if __name__=='__main__':main()
