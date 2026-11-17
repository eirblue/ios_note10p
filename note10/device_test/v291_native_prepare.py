"""291 Linux-epoch observed inventory and early draft; no terminal authority."""
import json
import subprocess
from pathlib import Path
import v290_native_prepare as retained
p,require,sha,bind=retained.p,retained.require,retained.sha,retained.bind
metadata=retained.metadata
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
WORKFLOW='.github/workflows/note10-v291-native-prepare.yml';JOB='v291-native-prepare'
BUILD_SCHEMA='note10-v291-observed-draft-PC-build-v1'
CONTEXT_SCHEMA='note10-v291-observed-draft-PC-public-input-v1'
MANIFEST_SCHEMA='note10-v291-observed-draft-PC-sealed-members-v1'
# Watchdog276, CPU290 and storage290 formats keep their existing semantics.
CAPTURE_SCHEMA,TARGET_SCHEMA=retained.CAPTURE_SCHEMA,retained.TARGET_SCHEMA
decode_binding=retained.decode_binding
verify_metadata,verify_storage=retained.verify_metadata,retained.verify_storage
NEW_FILES=('v291_observed_draft_metadata.h','v291_observed_draft_metadata.c','v291_observed_draft_metadata.inc',
 'v291_observed_draft_metadata_fixture.c','test_v291_observed_draft_metadata.py','v291_native_prepare.py')
ADDED_MEMBERS=('draft-evidence.json','draft-object.o','draft-object.cmd','draft-object.su','draft-object-elf.log')
SUCCESS_MEMBERS=(*retained.SUCCESS_MEMBERS,*ADDED_MEMBERS);METADATA_TYPES=retained.METADATA_TYPES
DRAFT_TARGET='arch/arm64/mm/v291_observed_draft_metadata.o'
DRAFT_CORE=('n291_classify','n291_encode_early','n291_encode_inventory','n291_layout_witness')
DRAFT_OWNER=('n291_prepare_draft_locked','n291_collect_locked','n291_status')
DRAFT_NAMES=(*DRAFT_CORE,*DRAFT_OWNER)
DRAFT_ABI={'n291_size_header':40,'n291_size_observation':432,'n291_header_pool_offset':45016,'n291_packet_offset':256}
DRAFT_CALL=b'''        if(!error)error=n291_prepare_draft_locked((struct n290_storage *)N290_STORAGE,N279_SEAL,prepared,&n210_destination,context,
            &n210_result,ctx,(struct n285_workspace *)n226_source_pool,sizeof(struct n285_workspace));
'''

def source_pins():
    value=retained.source_pins();value.pop(retained.WORKFLOW)
    value.update({'note10/device_test/'+n:sha(p.ordinary(HERE/n))for n in NEW_FILES})
    value[WORKFLOW]=sha(p.ordinary(ROOT/WORKFLOW));return value

def public_context(head,passed):
    p.hexid(head,40)
    require(set(passed)=={'passed','groups','variants','assertions','result_sha256'}and passed['passed']is True and
        tuple(passed[k]for k in('groups','variants','assertions'))==(1,1,1),'new291 grouped draft only')
    p.hexid(passed['result_sha256'])
    return dict(schema=CONTEXT_SCHEMA,source_head=head,source_sha256=source_pins(),new_fixture_PASS=passed,old_tests_replayed=False,PC_only=True,hardware_ready=False)

def owner_overlay(raw):
    include=b'#include "v290_preparation_storage.inc"\n'
    require(raw.count(include)==raw.count(retained.STORAGE_CALL)==1 and b'n291_'not in raw,'exact post-storage owner seam')
    changed=raw.replace(include,include+b'#include "v291_observed_draft_metadata.inc"\n',1).replace(retained.STORAGE_CALL,retained.STORAGE_CALL+DRAFT_CALL,1)
    require(changed.count(DRAFT_CALL)==1 and changed.index(retained.SEAL_CALL)<changed.index(retained.STORAGE_CALL)<changed.index(DRAFT_CALL)<changed.index(b'stats->error='),'one real locked draft caller after storage')
    return changed

def install_binding(source,buffers):
    value=retained.install_binding(source,buffers);owner=source/'arch/arm64/mm/v226_source_stream_kernel.c'
    after=owner_overlay(p.ordinary(owner));owner.write_bytes(after)
    value['compiler_inputs']['arch/arm64/mm/v226_source_stream_kernel.c']['after_sha256']=sha(after)
    copied={}
    for name in NEW_FILES[:3]:
        target=source/'arch/arm64/mm'/name;require(not target.exists(),'fresh291 input')
        raw=buffers['note10/device_test/'+name];target.write_bytes(raw);copied[str(target.relative_to(source))]=sha(raw)
    make=source/'arch/arm64/mm/Makefile';old=p.ordinary(make)
    line=b'obj-$(CONFIG_NOTE10_V210_NATIVE_PREPARE) += v291_observed_draft_metadata.o\n'
    require(b'v291_observed_draft_metadata'not in old and old.endswith(b'\n'),'one new pure draft TU');make.write_bytes(old+line)
    for key in('current_owner_seal','current_cpu_metadata','preparation_storage'):
        value[key].update(owner_after_sha256=sha(after),Kbuild_after_sha256=sha(old+line))
    value['observed_draft_binding']=dict(owner_after_sha256=sha(after),Kbuild_after_sha256=sha(old+line),copied=copied,
        header_pool_offset=45016,header_bytes=40,inventory_record_offset=256,inventory_capacity=512,
        workspace_bytes=24576,existing_pool_bytes=49152,existing_destination_bytes=33554432,
        new_BSS_bytes=0,new_pool_bytes=0,new_reservation_bytes=0,terminal_transfer=False)
    return value

def inventory_metadata(entries,passed):
    require(len(SUCCESS_MEMBERS)==len(set(SUCCESS_MEMBERS))==58,'fixed58 inventory')
    allowed=set(SUCCESS_MEMBERS)-{'members.json'}
    require(type(passed)is bool and type(entries)is list and 0<len(entries)<=57 and all(type(row)is dict and set(row)==set(METADATA_TYPES)and all(type(row[k])is kind for k,kind in METADATA_TYPES.items())for row in entries),'bounded exact metadata types')
    sizes={row['name']:row['bytes']for row in entries}
    require(len(sizes)==len(entries)and 'result.json'in sizes and set(sizes)<=allowed and(not passed or set(sizes)==allowed),'closed new inventory')
    require(all(row['regular']and not row['symlink']and 0<row['bytes']<=67108864 for row in entries)and sum(sizes.values())<=134217728,'unchanged transport caps');return sizes

def verify_draft(raw,linked):
    require(raw['schema']=='note10-v291-observed-draft-raw-v1'and raw['complete']is True and raw['linked_nm_sha256']==sha(linked.encode())and set(raw['bodies'])==set(DRAFT_NAMES),'fresh exact draft capture')
    binding=raw['compiler_input_binding']
    expected={'arch/arm64/mm/'+name:raw['source_sha256']['note10/device_test/'+name]for name in NEW_FILES[:3]}
    require(binding['copied']==expected and binding['header_pool_offset']==45016 and binding['header_bytes']==40 and
        binding['inventory_record_offset']==256 and binding['inventory_capacity']==512 and binding['workspace_bytes']==24576 and
        binding['existing_pool_bytes']==49152 and binding['existing_destination_bytes']==33554432 and
        binding['new_BSS_bytes']==binding['new_pool_bytes']==binding['new_reservation_bytes']==0 and binding['terminal_transfer']is False,'source-owned exact draft placement')
    scoped=metadata.seal_base;table=scoped.scoped.reader.linked_symbols(linked)
    targets={metadata.OWNER_TARGET:('n226_ingest_prepared_locked',*DRAFT_OWNER),DRAFT_TARGET:DRAFT_CORE}
    require(set(raw['objects'])==set(targets),'two exact affected draft TUs')
    contexts={target:scoped.provenance(target,roots,raw['objects'][target],table)for target,roots in targets.items()}
    abi=scoped.scoped.object_symbols(raw['objects'][DRAFT_TARGET]['nm'])
    require(all(len(abi[n])==1 and abi[n][0][1]=='A'and int(abi[n][0][2],16)==v for n,v in DRAFT_ABI.items()),'actual draft ABI')
    obj=metadata.retained._ENV['metadata_object_evidence'](raw['objects'][DRAFT_TARGET]['elf'],raw['objects'][DRAFT_TARGET]['usage'])
    require(obj['writable_section_bytes']==0,'draft TU writable0')
    frames={};frontiers=[]
    for name,item in raw['bodies'].items():
        record=item['record'];require(record['name']==name and len(table.get(name,()))==1 and record==dict(name=name,**table[name][0],offset=0),'exact new linked identity')
        target=DRAFT_TARGET if name in DRAFT_CORE else metadata.OWNER_TARGET
        context,_,reader=contexts[target];source=reader(context,record,False)
        require(source['section_index']in context['deltas']and source['object_address']+context['deltas'][source['section_index']]==record['address'],'actual new source/section/entry')
        symbol=scoped.scoped.symbol_extent(table,name,record,False);proof=scoped.scoped.scoped_transfers(item['body'],symbol,table)
        require(not proof['unknown_control_transfers'],'direct new transfers only')
        require(0<=source['frame']['bytes']<=4096,'new source-coupled static SU cap4096')
        frames[name]=dict(source=source,static_SU_bytes=source['frame']['bytes'],callee_peaks_included=False)
        for edge in proof['external_transfers']:
            require(edge['mnemonic']in('b','bl')and not edge['unresolved']and edge['resolved_records']and all(r['offset']==0 for r in edge['resolved_records']),'direct exact new edge')
            if not any(r['name']in DRAFT_NAMES for r in edge['resolved_records']):frontiers.append(dict(caller=name,edge=edge,peak_bytes=None))
    record=raw['owner']['record'];require(record['name']=='n226_ingest_prepared_locked'and len(table[record['name']])==1 and record==dict(name=record['name'],**table[record['name']][0],offset=0),'fresh connected owner')
    symbol=scoped.scoped.symbol_extent(table,record['name'],record,False)
    edges=scoped.scoped.scoped_transfers(raw['owner']['body'],symbol,table)['external_transfers']
    storage=[e for e in edges if any(r['name']=='n290_prepare_storage_locked'for r in e['resolved_records'])]
    draft=[e for e in edges if any(r['name']=='n291_prepare_draft_locked'for r in e['resolved_records'])]
    require(len(storage)==len(draft)==1 and storage[0]['address']<draft[0]['address'],'actual unique storage-before-draft BL')
    require(sum(v['static_SU_bytes']for v in frames.values())<=8192,'new selected static SU sum cap8192')
    frontiers.sort(key=lambda row:json.dumps(row,sort_keys=True,separators=(',',':')))
    value=dict(schema='note10-v291-observed-draft-target-v1',**{k:raw[k]for k in('source_head','run_id','build_evidence_id','source_sha256')},ABI=DRAFT_ABI,
        frames=frames,actual_owner_callers=1,storage_before_draft=True,new_TU_writable_bytes=0,existing_pool_bytes=49152,
        existing_destination_bytes=33554432,new_pool_bytes=0,new_reservation_bytes=0,explicit_unclosed_boundaries=frontiers,
        whole_stack_bound_proven=False,own_SP_instruction_proof=False,runtime_inventory_observed=False,
        CPU_epoch='earlier-guarded-source-sample',OF_epoch='later-locked-firmware-declaration-snapshot',
        final_CPU_qualified=False,physical_DRAM_qualified=False,independent_return_qualified=False,
        adapter_record_installed=False,authoritative_ADT=False,terminal_transfer=False,hardware_ready=False,physical_ready=False)
    return json.loads(json.dumps(value))

def collect_binding(objects,out,result,run,linked):
    value=retained.collect_binding(objects,out,result,run,linked)
    base=json.loads(p.ordinary(out/'cpu-metadata-evidence.json',16777216));binding=result['preparation']['watchdog_binding']['observed_draft_binding']
    raw=dict(schema='note10-v291-observed-draft-raw-v1',**{k:result[k]for k in('source_head','run_id','build_evidence_id','source_sha256')},complete=False,
        linked_nm_sha256=sha(linked.encode()),compiler_input_binding=binding,objects={metadata.OWNER_TARGET:base['objects'][metadata.OWNER_TARGET]},bodies={},tools=[])
    def persist():
        require(len(json.dumps(raw).encode())<=8388608,'bounded draft evidence');p.save(out/'draft-evidence.json',raw)
    def capture(argv):
        done=subprocess.run(list(map(str,argv)),stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=120)
        raw['tools'].append(dict(argv=list(map(str,argv)),returncode=done.returncode,stdout_sha256=sha(done.stdout)));persist()
        require(done.returncode==0 and 0<len(done.stdout)<=8388608 and len(done.stderr)<=65536,'bounded draft tool');return done.stdout.decode()
    try:
        table=metadata.seal_base.scoped.reader.linked_symbols(linked);rel=Path(DRAFT_TARGET)
        command=p.ordinary(objects/rel.with_name('.'+rel.name+'.cmd'))
        usage=p.ordinary(objects/metadata.stream_candidate.compiler_stack_path(command,DRAFT_TARGET)).decode()
        raw['objects'][DRAFT_TARGET]=dict(command=command.decode(),command_sha256=sha(command),usage=usage,usage_sha256=sha(usage.encode()),
            nm=capture(['aarch64-linux-gnu-nm','--format=posix','--print-size',objects/DRAFT_TARGET]),
            elf=capture(['aarch64-linux-gnu-readelf','--wide','--sections','--symbols',objects/DRAFT_TARGET]),object_sha256=sha(p.ordinary(objects/DRAFT_TARGET,67108864)))
        for name in DRAFT_NAMES:
            require(len(table.get(name,()))==1,'unique new draft root');record=dict(name=name,**table[name][0],offset=0)
            raw['bodies'][name]=dict(record=record,body=capture(['aarch64-linux-gnu-objdump','-d','--disassemble-zeroes','--start-address='+hex(record['address']),'--stop-address='+hex(record['address']+record['bytes']),objects/'vmlinux']))
        raw['owner']=next(dict(record=base['records'][i],body=body)for i,body in base['bodies'].items()if base['records'][i]['name']=='n226_ingest_prepared_locked')
        context=metadata.seal_base.provenance(metadata.OWNER_TARGET,('n226_ingest_prepared_locked',),raw['objects'][metadata.OWNER_TARGET],table)[0]
        source=Path(context['TU']['translation_unit']).parent
        require(sha(p.ordinary(source/'v226_source_stream_kernel.c'))==binding['owner_after_sha256']and sha(p.ordinary(source/'Makefile'))==binding['Kbuild_after_sha256'],'actual draft owner/Kbuild')
        for path,digest in binding['copied'].items():require(sha(p.ordinary(source/Path(path).name))==digest,'actual draft compiler input')
        (out/'draft-object.o').write_bytes(p.ordinary(objects/DRAFT_TARGET,67108864));(out/'draft-object.cmd').write_bytes(command)
        (out/'draft-object.su').write_text(usage);(out/'draft-object-elf.log').write_text(raw['objects'][DRAFT_TARGET]['elf'])
        raw['complete']=True;persist();result['observed_draft_target']=verify_draft(raw,linked)
        result.update(draft_runtime_callers=1,runtime_inventory_observed=False,hardware_ready=False,physical_ready=False);return value
    except BaseException as error:
        raw.update(complete=False,rejection=str(error)[:2048]);persist();raise

_code_bind=retained._code_bind
_ENV={**retained._ENV,**{name:globals()[name]for name in('WORKFLOW','JOB','BUILD_SCHEMA','CONTEXT_SCHEMA','MANIFEST_SCHEMA','SUCCESS_MEMBERS','source_pins','public_context','install_binding','collect_binding')}}
run_build=_code_bind(retained.run_build,_ENV,{'note10/private/v290-ci-native-prepare':'note10/private/v291-ci-native-prepare','v290':'v291','"-v290-preparation-storage"':'"-v291-observed-draft"'})
seal=bind(retained.seal,{**retained.seal.__globals__,**_ENV,'inventory_metadata':inventory_metadata})
_ENV.update(run_build=run_build,seal=seal)
main=bind(retained.main,_ENV)

def audit_api():
    require(run_build.__globals__['install_binding']is install_binding and run_build.__globals__['collect_binding']is collect_binding and
        main.__globals__['seal']is seal and seal.__globals__['inventory_metadata']is inventory_metadata,'new connected build/capture/seal callbacks')
    require(CAPTURE_SCHEMA==retained.CAPTURE_SCHEMA and TARGET_SCHEMA==retained.TARGET_SCHEMA and verify_metadata is retained.verify_metadata and verify_storage is retained.verify_storage,'unchanged component format domains')

if __name__=='__main__':main()
