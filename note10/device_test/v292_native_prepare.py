"""292 real cooperative-return admission snapshot; PC build only."""
import json
import subprocess
from pathlib import Path
import v291_native_prepare as retained
p,require,sha,bind=retained.p,retained.require,retained.sha,retained.bind
metadata=retained.metadata
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
WORKFLOW='.github/workflows/note10-v292-native-prepare.yml';JOB='v292-native-prepare'
BUILD_SCHEMA='note10-v292-return-admission-PC-build-v1'
CONTEXT_SCHEMA='note10-v292-return-admission-PC-public-input-v1'
MANIFEST_SCHEMA='note10-v292-return-admission-PC-sealed-members-v1'
CAPTURE_SCHEMA,TARGET_SCHEMA=retained.CAPTURE_SCHEMA,retained.TARGET_SCHEMA
decode_binding=retained.decode_binding
verify_metadata,verify_storage,verify_draft=retained.verify_metadata,retained.verify_storage,retained.verify_draft
NEW_FILES=('v292_return_admission.inc','v292_return_admission_fixture.c','test_v292_return_admission.py','v292_native_prepare.py')
ADDED_MEMBERS=('return-admission-evidence.json','return-admission-object.o')
SUCCESS_MEMBERS=(*retained.SUCCESS_MEMBERS,*ADDED_MEMBERS);METADATA_TYPES=retained.METADATA_TYPES
RETURN_TARGET='drivers/misc/v154_linux_return.o'
RETURN_SOURCE='drivers/misc/v154_linux_return.c'
RETURN_INCLUDE='drivers/misc/v292_return_admission.inc'
OLD_FUNCTION=b'int n210_linux_context(struct n210_context *out)\n{\n    memset(out,0,sizeof(*out));\n    memcpy(out->build,N154_BUILD_ID,32);\n    memcpy(out->boot,n10_boot_id,32);\n    memcpy(out->cycle,(const void *)n10_cycle,32);\n    out->return_armed=READ_ONCE(n154_arm_result)==0;\n    return out->return_armed?0:-EAGAIN;\n}\n'

def source_pins():
    value=retained.source_pins();value.pop(retained.WORKFLOW)
    value.update({'note10/device_test/'+n:sha(p.ordinary(HERE/n))for n in NEW_FILES})
    value[WORKFLOW]=sha(p.ordinary(ROOT/WORKFLOW));return value

def public_context(head,passed):
    p.hexid(head,40)
    require(set(passed)=={'passed','groups','variants','assertions','result_sha256'}and passed['passed']is True and
        tuple(passed[k]for k in('groups','variants','assertions'))==(1,1,1),'new292 return-admission conjunction only')
    p.hexid(passed['result_sha256'])
    return dict(schema=CONTEXT_SCHEMA,source_head=head,source_sha256=source_pins(),new_fixture_PASS=passed,old_tests_replayed=False,PC_only=True,hardware_ready=False)

def return_overlay(raw):
    require(raw.count(OLD_FUNCTION)==1 and b'v292_return_admission'not in raw,'exact generated context accessor once')
    return raw.replace(OLD_FUNCTION,b'#include "v292_return_admission.inc"\n',1)

def install_binding(source,buffers):
    value=retained.install_binding(source,buffers);target=source/RETURN_SOURCE
    before=p.ordinary(target);after=return_overlay(before);target.write_bytes(after)
    include=source/RETURN_INCLUDE;require(not include.exists(),'fresh292 include')
    raw=buffers['note10/device_test/v292_return_admission.inc'];include.write_bytes(raw)
    value['return_admission_binding']=dict(source_path=RETURN_SOURCE,before_sha256=sha(before),after_sha256=sha(after),
        include_path=RETURN_INCLUDE,include_sha256=sha(raw),original_function_sha256=sha(OLD_FUNCTION),
        new_writable_globals_declared=0,new_pool_bytes=0,new_reservation_bytes=0,worker_modified=False,independent_return=False)
    return value

def inventory_metadata(entries,passed):
    require(len(SUCCESS_MEMBERS)==len(set(SUCCESS_MEMBERS))==60,'fixed60 inventory')
    allowed=set(SUCCESS_MEMBERS)-{'members.json'}
    require(type(passed)is bool and type(entries)is list and 0<len(entries)<=59 and all(type(row)is dict and set(row)==set(METADATA_TYPES)and all(type(row[k])is kind for k,kind in METADATA_TYPES.items())for row in entries),'bounded exact metadata types')
    sizes={row['name']:row['bytes']for row in entries}
    require(len(sizes)==len(entries)and 'result.json'in sizes and set(sizes)<=allowed and(not passed or set(sizes)==allowed),'closed new inventory')
    require(all(row['regular']and not row['symlink']and 0<row['bytes']<=67108864 for row in entries)and sum(sizes.values())<=134217728,'unchanged transport caps');return sizes

def verify_return(raw,linked):
    require(raw['schema']=='note10-v292-return-admission-raw-v1'and raw['complete']is True and raw['linked_nm_sha256']==sha(linked.encode()),'fresh return capture')
    binding=raw['compiler_input_binding']
    require(binding['source_path']==RETURN_SOURCE and binding['include_path']==RETURN_INCLUDE and
        binding['include_sha256']==raw['source_sha256']['note10/device_test/v292_return_admission.inc']and
        binding['original_function_sha256']==sha(OLD_FUNCTION)and binding['new_writable_globals_declared']==binding['new_pool_bytes']==binding['new_reservation_bytes']==0 and
        binding['worker_modified']is binding['independent_return']is False,'actual return source-only delta')
    scoped=metadata.seal_base;table=scoped.scoped.reader.linked_symbols(linked)
    require(set(raw['objects'])=={RETURN_TARGET,metadata.OWNER_TARGET},'two exact affected provenance objects')
    target_context,_,target_reader=scoped.provenance(RETURN_TARGET,('n210_linux_context',),raw['objects'][RETURN_TARGET],table)
    record=raw['target']['record']
    require(record['name']=='n210_linux_context'and len(table.get(record['name'],()))==1 and record==dict(name=record['name'],**table[record['name']][0],offset=0),'exact linked return accessor')
    origin=target_reader(target_context,record,False)
    require(origin['section_index']in target_context['deltas']and origin['object_address']+target_context['deltas'][origin['section_index']]==record['address']and 0<=origin['frame']['bytes']<=4096,'actual source/section/static SU')
    symbol=scoped.scoped.symbol_extent(table,record['name'],record,False)
    edges=scoped.scoped.scoped_transfers(raw['target']['body'],symbol,table)
    require(not edges['unknown_control_transfers'],'direct accessor transfers only')
    caller=raw['caller']['record'];require(caller['name']=='n217_owner'and len(table.get(caller['name'],()))==1 and caller==dict(name=caller['name'],**table[caller['name']][0],offset=0),'actual per-page owner caller')
    owner_context,_,owner_reader=scoped.provenance(metadata.OWNER_TARGET,('n217_owner',),raw['objects'][metadata.OWNER_TARGET],table)
    owned=owner_reader(owner_context,caller,False)
    require(owned['section_index']in owner_context['deltas']and owned['object_address']+owner_context['deltas'][owned['section_index']]==caller['address'],'fresh caller source provenance')
    csymbol=scoped.scoped.symbol_extent(table,caller['name'],caller,False)
    calls=scoped.scoped.scoped_transfers(raw['caller']['body'],csymbol,table)['external_transfers']
    selected=[e for e in calls if any(r['name']=='n210_linux_context'for r in e['resolved_records'])]
    require(len(selected)==1 and selected[0]['mnemonic']=='bl'and not selected[0]['unresolved']and all(r['offset']==0 for r in selected[0]['resolved_records']),'one actual owner-to-context BL')
    frontiers=[]
    for edge in edges['external_transfers']:
        require(edge['mnemonic']in('b','bl')and not edge['unresolved']and edge['resolved_records']and all(r['offset']==0 for r in edge['resolved_records']),'exact direct accessor boundary')
        frontiers.append(dict(caller='n210_linux_context',edge=edge,peak_bytes=None))
    frontiers.sort(key=lambda row:json.dumps(row,sort_keys=True,separators=(',',':')))
    value=dict(schema='note10-v292-return-admission-target-v1',**{k:raw[k]for k in('source_head','run_id','build_evidence_id','source_sha256')},
        source=origin,actual_page_owner_callers=1,caller_source=owned,caller_edge=selected[0],static_SU_bytes=origin['frame']['bytes'],
        explicit_unclosed_boundaries=frontiers,new_writable_globals_declared=0,new_pool_bytes=0,new_reservation_bytes=0,
        worker_modified=False,admission_kind='instantaneous-cooperative-snapshot',linearizable_future_lease=False,
        runtime_snapshot_observed=False,worker_progress_proven=False,independent_return_qualified=False,whole_stack_bound_proven=False,
        final_CPU_qualified=False,authoritative_ADT=False,terminal_transfer=False,hardware_ready=False,physical_ready=False)
    return json.loads(json.dumps(value))

def collect_binding(objects,out,result,run,linked):
    value=retained.collect_binding(objects,out,result,run,linked)
    stack=json.loads(p.ordinary(out/'stack-evidence.json',8388608));base=json.loads(p.ordinary(out/'cpu-metadata-evidence.json',16777216))
    binding=result['preparation']['watchdog_binding']['return_admission_binding'];old=stack['objects'][RETURN_TARGET]
    raw=dict(schema='note10-v292-return-admission-raw-v1',**{k:result[k]for k in('source_head','run_id','build_evidence_id','source_sha256')},complete=False,
        linked_nm_sha256=sha(linked.encode()),compiler_input_binding=binding,objects={metadata.OWNER_TARGET:base['objects'][metadata.OWNER_TARGET]},tools=[])
    def persist():
        require(len(json.dumps(raw).encode())<=8388608,'bounded return evidence');p.save(out/'return-admission-evidence.json',raw)
    def capture(argv):
        done=subprocess.run(list(map(str,argv)),stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=120)
        raw['tools'].append(dict(argv=list(map(str,argv)),returncode=done.returncode,stdout_sha256=sha(done.stdout)));persist()
        require(done.returncode==0 and 0<len(done.stdout)<=8388608 and len(done.stderr)<=65536,'bounded return tool');return done.stdout.decode()
    try:
        table=metadata.seal_base.scoped.reader.linked_symbols(linked)
        # Reuse command/SU/readelf already captured by this same fresh build.
        raw['objects'][RETURN_TARGET]=dict(command=old['command'],command_sha256=old['command_sha256'],usage=old['stack_usage'],usage_sha256=old['stack_sha256'],
            elf=old['elf_sections_and_symbols'],nm=capture(['aarch64-linux-gnu-nm','--format=posix','--print-size',objects/RETURN_TARGET]),
            object_sha256=result['object_evidence'][RETURN_TARGET]['object_sha256'])
        name='n210_linux_context';require(len(table.get(name,()))==1,'unique current accessor');record=dict(name=name,**table[name][0],offset=0)
        raw['target']=dict(record=record,body=capture(['aarch64-linux-gnu-objdump','-d','--disassemble-zeroes','--start-address='+hex(record['address']),'--stop-address='+hex(record['address']+record['bytes']),objects/'vmlinux']))
        raw['caller']=next(dict(record=base['records'][i],body=body)for i,body in base['bodies'].items()if base['records'][i]['name']=='n217_owner')
        context=metadata.seal_base.provenance(RETURN_TARGET,('n210_linux_context',),raw['objects'][RETURN_TARGET],table)[0]
        source=Path(context['TU']['translation_unit'])
        require(sha(p.ordinary(source))==binding['after_sha256']and sha(p.ordinary(source.parent/'v292_return_admission.inc'))==binding['include_sha256'],'actual return compiler source/include')
        obj=p.ordinary(objects/RETURN_TARGET,67108864);require(sha(obj)==raw['objects'][RETURN_TARGET]['object_sha256'],'same fresh return object')
        (out/'return-admission-object.o').write_bytes(obj)
        raw['complete']=True;persist();result['return_admission_target']=verify_return(raw,linked)
        result.update(return_snapshot_runtime_observed=False,independent_return_qualified=False,hardware_ready=False,physical_ready=False);return value
    except BaseException as error:
        raw.update(complete=False,rejection=str(error)[:2048]);persist();raise

_code_bind=retained._code_bind
_ENV={**retained._ENV,**{name:globals()[name]for name in('WORKFLOW','JOB','BUILD_SCHEMA','CONTEXT_SCHEMA','MANIFEST_SCHEMA','SUCCESS_MEMBERS','source_pins','public_context','install_binding','collect_binding')}}
run_build=_code_bind(retained.run_build,_ENV,{'note10/private/v291-ci-native-prepare':'note10/private/v292-ci-native-prepare','v291':'v292','"-v291-observed-draft"':'"-v292-return-admission"'})
seal=bind(retained.seal,{**retained.seal.__globals__,**_ENV,'inventory_metadata':inventory_metadata})
_ENV.update(run_build=run_build,seal=seal)
main=bind(retained.main,_ENV)

def audit_api():
    require(run_build.__globals__['install_binding']is install_binding and run_build.__globals__['collect_binding']is collect_binding and
        main.__globals__['seal']is seal and seal.__globals__['inventory_metadata']is inventory_metadata,'actual new return source/capture callbacks')
    require(CAPTURE_SCHEMA==retained.CAPTURE_SCHEMA and TARGET_SCHEMA==retained.TARGET_SCHEMA and verify_metadata is retained.verify_metadata and
        verify_storage is retained.verify_storage and verify_draft is retained.verify_draft,'unchanged component format domains')

if __name__=='__main__':main()
