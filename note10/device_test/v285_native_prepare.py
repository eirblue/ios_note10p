"""285 PC-only current-owner metadata preparation; no hardware-ready claim."""
import json
import re
import subprocess
from collections import deque
from pathlib import Path
from types import SimpleNamespace
import v283_native_prepare as retained
import v279_native_prepare as seal_base
import v277_native_prepare as watchdog
import v275_native_prepare as frame_core
import v281_native_prepare as frame_forms

p,require,sha,bind=retained.p,retained.require,retained.sha,retained.bind
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
WORKFLOW='.github/workflows/note10-v285-native-prepare.yml';JOB='v285-native-prepare'
BUILD_SCHEMA='note10-v285-CPU-metadata-PC-build-v1'
CONTEXT_SCHEMA='note10-v285-CPU-metadata-PC-public-input-v1'
MANIFEST_SCHEMA='note10-v285-CPU-metadata-PC-sealed-members-v1'
CAPTURE_SCHEMA,TARGET_SCHEMA=watchdog.CAPTURE_SCHEMA,watchdog.TARGET_SCHEMA
decode_binding=watchdog.decode_binding
NEW_FILES=('v285_current_cpu_metadata.h','v285_current_cpu_metadata.c','v285_current_cpu_metadata.inc',
           'v285_current_cpu_metadata_fixture.c','v285_native_prepare.py','test_v285_current_cpu_metadata.py')
ADDED_MEMBERS=('cpu-metadata-evidence.json','cpu-metadata-object.o','cpu-metadata-object.cmd',
               'cpu-metadata-object.su','cpu-metadata-object-elf.log')
SUCCESS_MEMBERS=(*retained.SUCCESS_MEMBERS,*ADDED_MEMBERS)
METADATA_TYPES=retained.METADATA_TYPES
NEW_NAMES=('n285_snapshot_of_locked','n285_find_property_locked','n285_prepare_metadata','n285_encode_cpu_adt',
           'n285_put_property','n285_write_pages','n285_readback_pages','n285_layout_witness')
OLD_NAMES=('n226_ingest_prepared_locked','n278_seal_once','n279_layout_witness','n210_request_valid',
           'n210_receipt_matches','n209_decode_payload','n209_layout_bounds','little','magic','nonzero','equal','hex32','extent','bcmp')
PROJECTION_NAMES=('n230_project_metadata','n230_span','n230_overlap','n230_copy','n10_rt_validate_adt',
                  'n10_rt_serialize_boot_args','n10_rt_serialize_record')
RT_NAMES=('zero_bytes','copy_bytes','add64','overlap','pointer_overlap','pointer_span','same','le32','put16',
          'put32','put64','name_byte','gic_name','take','adt_node','command_ok')
IO_NAMES=('n217_owner','n217_page_io','n217_write_destination','n217_read_destination')
NAMED=(*NEW_NAMES,*OLD_NAMES,*PROJECTION_NAMES,*RT_NAMES,*IO_NAMES)
NAMED_CAP,OUTLINED_CAP,EXTENT_CAP=49,30,79
OWNER_TARGET='arch/arm64/mm/init.o';NEW_TARGET='arch/arm64/mm/v285_current_cpu_metadata.o'
TARGETS={OWNER_TARGET:(seal_base.OWNER,'n279_layout_witness'),NEW_TARGET:('n285_prepare_metadata','n285_layout_witness'),
         seal_base.SEAL_TARGET:('n278_seal_once',),'arch/arm64/mm/v230_boot_metadata.o':('n230_project_metadata',),
         'arch/arm64/mm/v230_runtime_relocation.o':('n10_rt_validate_adt','n10_rt_serialize_boot_args','n10_rt_serialize_record'),
         'lib/string.o':('bcmp',)}
BOUNDARY_CALLERS={'n226_ingest_prepared_locked','n285_snapshot_of_locked','n217_owner','n217_page_io','n278_seal_once'}
ABI={'n285_size_workspace':24576,'n285_align_workspace':8,'n285_offset_snapshot':18208,'n285_offset_readback':20480}
DONE=b' done:\n'
AFTER_END=b'''    if(!error){
        memset(n226_source_pool,0,N226_WORKSPACE_BYTES);
        error=n285_snapshot_of_locked(&((struct n285_workspace *)n226_source_pool)->snapshot,
            (const struct n231_cpu_observation *)(n226_source_pool+N231_POOL_OFFSET),
            (const struct n233_cpu_node_consistency *)(n226_source_pool+N233_POOL_OFFSET),
            (const struct n240_query_receipt *)(n226_source_pool+N240_POOL_OFFSET));
        if(!error)error=n285_prepare_metadata(prepared,&n210_destination,context,ctx,
            (struct n285_workspace *)n226_source_pool,N226_WORKSPACE_BYTES);
        if(!error)error=n278_seal_once(N279_SEAL,prepared,&n210_destination,context,
            n210_result.descriptor_sha256,&n210_result,n210_spent,&n217_kernel_state);
    }
    if(error&&N279_SEAL->phase==N278_EMPTY)N279_SEAL->phase=N278_REFUSED;
'''

def source_pins():
    value=retained.source_pins();value.pop(retained.WORKFLOW)
    value.update({'note10/device_test/'+n:sha(p.ordinary(HERE/n))for n in NEW_FILES})
    value[WORKFLOW]=sha(p.ordinary(ROOT/WORKFLOW));return value

def public_context(head,passed):
    p.hexid(head,40)
    require(set(passed)=={'passed','groups','variants','assertions','result_sha256'} and passed['passed']is True and
            tuple(passed[k]for k in ('groups','variants','assertions'))==(1,4,4),'new285 host4 only')
    p.hexid(passed['result_sha256'])
    return dict(schema=CONTEXT_SCHEMA,source_head=head,source_sha256=source_pins(),new_fixture_PASS=passed,
                old_tests_replayed=False,PC_only=True,hardware_ready=False)

def owner_overlay(raw):
    require(raw.count(seal_base.CALL)==1 and raw.count(DONE)==1 and
            raw.count(b'n226_codec_end(ctx);')==1 and b'n285_'not in raw,'exact old success/end seams')
    guard=b'    if(n217_kernel_state.spent)return -EALREADY;'
    clear=b'    memset(n226_source_pool,0,sizeof(n226_source_pool));'
    require(raw.count(guard)==raw.count(clear)==1 and raw.index(guard)<raw.index(clear)<raw.index(seal_base.CALL),
            'shared spent precedes clear')
    changed=raw.replace(b'#include "v279_current_owner_seal.inc"\n',
                        b'#include "v279_current_owner_seal.inc"\n#include "v285_current_cpu_metadata.inc"\n',1)
    require(changed!=raw,'one owner-local snapshot include')
    changed=changed.replace(seal_base.CALL,b'',1).replace(b'n226_codec_end(ctx);',b'',1)
    changed=changed.replace(DONE,DONE+b'    n226_codec_end(ctx);\n'+AFTER_END,1)
    require(changed.count(b'n278_seal_once(')==1 and changed.count(b'n226_codec_end(ctx);')==1 and
            changed.index(b'n226_codec_end(ctx);')<changed.index(b'error=n285_prepare_metadata(')<
            changed.index(b'error=n278_seal_once(')<changed.index(b'stats->error='), 'final seal before pure cleanup')
    return changed

def install_binding(source,buffers):
    value=seal_base.install_binding(source,buffers)
    owner=source/'arch/arm64/mm/v226_source_stream_kernel.c';before=p.ordinary(owner);after=owner_overlay(before)
    owner.write_bytes(after)
    value['compiler_inputs']['arch/arm64/mm/v226_source_stream_kernel.c']['after_sha256']=sha(after)
    value['current_owner_seal']['owner_after_sha256']=sha(after)
    copied={}
    for name in NEW_FILES[:3]:
        target=source/'arch/arm64/mm'/name;require(not target.exists(),'fresh285 source input')
        target.write_bytes(buffers['note10/device_test/'+name]);copied[str(target.relative_to(source))]=sha(p.ordinary(target))
    make=source/'arch/arm64/mm/Makefile';old=p.ordinary(make)
    line=b'obj-$(CONFIG_NOTE10_V210_NATIVE_PREPARE) += v285_current_cpu_metadata.o\n'
    require(b'v285_current_cpu_metadata'not in old and old.endswith(b'\n'),'one new readonly metadata TU')
    make.write_bytes(old+line);value['current_owner_seal']['Kbuild_after_sha256']=sha(old+line)
    value['current_cpu_metadata']=dict(owner_path=str(owner.relative_to(source)),owner_after_sha256=sha(after),
        copied=copied,Kbuild_after_sha256=sha(old+line),seal_after_readback=True,new_BSS_bytes=0,new_pool_bytes=0,
        scratch_interval=[0,24576],freed_workspace_interval=[0,42312],adapter_record_installed=False)
    return value

def inventory_metadata(entries,passed):
    require(len(SUCCESS_MEMBERS)==len(set(SUCCESS_MEMBERS))==48 and 'members.json'in SUCCESS_MEMBERS,'fixed48 post schema')
    allowed=set(SUCCESS_MEMBERS)-{'members.json'}
    require(len(allowed)==47 and type(passed)is bool and type(entries)is list and 0<len(entries)<=47,'bounded47 pre schema')
    require(all(type(row)is dict and set(row)==set(METADATA_TYPES)and
            all(type(row[k])is kind for k,kind in METADATA_TYPES.items())for row in entries),'exact metadata row types')
    sizes={row['name']:row['bytes']for row in entries}
    require(len(sizes)==len(entries)and 'result.json'in sizes and set(sizes)<=allowed and
            (not passed or set(sizes)==allowed),'closed success/diagnostic inventory')
    require(all(row['regular']and not row['symlink']and 0<row['bytes']<=67108864 for row in entries)and
            sum(sizes.values())<=134217728,'unchanged file/total bounds')
    return sizes

stack_once=bind(retained.stack_once,{**retained.stack_once.__globals__,'_STACK':{}})
stream_candidate=SimpleNamespace(**{**vars(retained.stream_candidate),'verify_stack_evidence':stack_once})
_base_frame=bind(frame_core.own_frame,{**frame_core.own_frame.__globals__,'ROOTS':NAMED})
_frame_env={**frame_forms.own_frame.__globals__,'NAMED':NAMED,'retained':SimpleNamespace(own_frame=_base_frame)}
own_frame=bind(frame_forms.own_frame,_frame_env)

def verify_metadata(raw,linked):
    require(raw['schema']=='note10-v285-CPU-metadata-raw-v1'and raw['complete']is True,'complete new metadata capture')
    require(raw['profile'].get('LTO_NONE')=='y'and raw['profile'].get('LTO','n')=='n','actual LTO_NONE')
    table=seal_base.scoped.reader.linked_symbols(linked)
    require(raw['linked_nm_sha256']==sha(linked.encode())and len(NAMED)==len(set(NAMED))==49,'exact linked input/domain')
    require(set(raw['objects'])==set(TARGETS)and set(raw['records'])==set(raw['bodies'])and
            0<len(raw['bodies'])<=79,'bounded object/body inventory')
    contexts={}
    for target,roots in TARGETS.items():
        item=raw['objects'][target]
        contexts[target]=seal_base.provenance(target,roots,item,table)
    item=raw['objects'][NEW_TARGET]
    abi=seal_base.scoped.object_symbols(item['nm'])
    require(all(len(abi[n])==1 and abi[n][0][1]=='A'and int(abi[n][0][2],16)==v for n,v in ABI.items()),'actual workspace ABI')
    obj=retained._ENV['metadata_object_evidence'](item['elf'],item['usage'])
    require(obj['writable_section_bytes']==0,'new metadata TU writable0')
    frames={};frontiers=[];outlined=0;core_sum=0;metadata_callers=seal_callers=0
    for ident,body in raw['bodies'].items():
        record=raw['records'][ident];name=record['name'];outline=bool(re.fullmatch(r'OUTLINED_FUNCTION_\d+',name))
        require(name in NAMED or outline,'fixed named/outline domain')
        require(sum(record==dict(name=name,**row,offset=0)for row in table.get(name,()))==1,
                'exact linked record including local ordinal and zero offset')
        symbol=seal_base.scoped.symbol_extent(table,name,record,outline)
        require(ident==format(symbol['address'],'016x')+':'+str(symbol['bytes']),'exact selected extent')
        joined=[]
        for target,(context,roots,reader)in contexts.items():
            try:
                item=reader(context,record,outline);index=item['section_index']
                require(index in context['deltas']and item['object_address']+context['deltas'][index]==record['address'],
                        'same actual source section/linked entry')
                joined.append(item)
            except ValueError:pass
        require(len(joined)==1,'unique source/TU/ELF/SU provenance')
        proof=seal_base.scoped.scoped_transfers(body,symbol,table)
        require(not proof['unknown_control_transfers']or name in BOUNDARY_CALLERS,'no unknown new-core transfers')
        if proof['unknown_control_transfers']:
            frontiers.append(dict(caller=name,unknown_control_transfers=proof['unknown_control_transfers'],peak_bytes=None))
        certificate=None
        # New core only. Lock/owner/old recursive validator frontiers stay unknown.
        if name in NEW_NAMES and name!='n285_snapshot_of_locked':
            rows=seal_base.scoped.flow.parse_body(body,proof)
            external={e['address']:'captured-callee-boundary'for e in proof['external_transfers']}
            certificate=own_frame(name,rows,external,joined[0]['frame']['bytes'],outline,
                                  frame_forms.instruction_words(body))
            core_sum+=certificate['own_peak_bytes']
        if outline:
            outlined+=1
            require(outlined<=30,'strict neutral outline cap')
            # Preserve generic strict neutrality, never apply caller-slot restore here.
            neutral=seal_base.scoped.own_frame(name,seal_base.scoped.flow.parse_body(body,proof),
                {e['address']:'exact-boundary'for e in proof['external_transfers']},0,True)
            require(neutral['neutral_outlined']is True,'new selected outlined helper strictly neutral')
        for edge in proof['external_transfers']:
            records=edge['resolved_records']
            require(edge['mnemonic']in('bl','b')and not edge['unresolved']and records and
                    all(r['offset']==0 for r in records),'direct exact selected edge')
            targets={(r['address'],r['bytes'])for r in records}
            require(len(targets)==1,'unambiguous edge extent')
            if name=='n226_ingest_prepared_locked':
                if any(r['name']=='n285_prepare_metadata'for r in records):metadata_callers+=1
                if any(r['name']=='n278_seal_once'for r in records):seal_callers+=1
            target=next(iter(targets));key=format(target[0],'016x')+':'+str(target[1])
            if key not in raw['bodies']:
                require(name in BOUNDARY_CALLERS or all(r['name']in('memcpy','__memcpy','__pi_memcpy',
                    'memset','__memset','__pi_memset','memcmp','__pi_memcmp')for r in records),'declared source-owned boundary')
                frontiers.append(dict(caller=name,edge=edge,peak_bytes=None))
        frames[ident]=dict(name=name,source=joined[0],frame_certificate=certificate,edges=proof['external_transfers'])
    require(0<core_sum<=8192 and outlined<=30 and metadata_callers==seal_callers==1,
            'new core frames and exact actual owner callsites')
    value=dict(schema='note10-v285-CPU-metadata-target-v1',**{k:raw[k]for k in ('source_head','run_id','build_evidence_id','source_sha256')},
        ABI=ABI,named_cap=49,outlined_cap=30,aggregate_cap=79,selected_extents=len(frames),outlined_extents=outlined,
        selected_metadata_core_frame_proven=True,selected_metadata_core_static_sum=core_sum,frames=frames,
        uncertified_new_boundary_functions=['n285_snapshot_of_locked'],
        explicit_unclosed_boundaries=frontiers,frontdoor_whole_stack_closed=False,whole_stack_bound_proven=False,
        seal_after_readback=True,adapter_record_installed=False,new_BSS_bytes=0,new_pool_bytes=0,
        same_boot_FDT_verified=False,observed_running_at_sample_only=True,complete_boot_tree=False,handoff_ready=False,
        actual_mandatory_metadata_callers=metadata_callers,actual_final_seal_callers=seal_callers,
        authoritative_ADT=False,hardware_ready=False,physical_ready=False,XNU=False)
    return json.loads(json.dumps(value))  # JSON report keys have the same type on reception.

def collect_binding(objects,out,result,run,linked):
    value=watchdog.collect_binding(objects,out,result,run,linked)
    binding=result['preparation']['watchdog_binding']['current_cpu_metadata']
    raw=dict(schema='note10-v285-CPU-metadata-raw-v1',**{k:result[k]for k in ('source_head','run_id','build_evidence_id','source_sha256')},
        complete=False,linked_nm_sha256=sha(linked.encode()),compiler_input_binding=binding,
        profile=result['effective_profile'],objects={},bodies={},records={},tools=[])
    def persist():
        require(len(json.dumps(raw).encode())<=16777216,'bounded metadata evidence');p.save(out/'cpu-metadata-evidence.json',raw)
    def capture(argv):
        done=subprocess.run(list(map(str,argv)),stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=120)
        raw['tools'].append(dict(argv=list(map(str,argv)),returncode=done.returncode,stdout_sha256=sha(done.stdout)));persist()
        require(done.returncode==0 and 0<len(done.stdout)<=8388608 and len(done.stderr)<=65536,'bounded metadata tool')
        return done.stdout.decode()
    try:
        table=seal_base.scoped.reader.linked_symbols(linked);contexts={}
        for target,roots in TARGETS.items():
            rel=Path(target);command=p.ordinary(objects/rel.with_name('.'+rel.name+'.cmd'))
            usage=p.ordinary(objects/stream_candidate.compiler_stack_path(command,target)).decode()
            item=dict(command=command.decode(),command_sha256=sha(command),usage=usage,usage_sha256=sha(usage.encode()),
                nm=capture(['aarch64-linux-gnu-nm','--format=posix','--print-size',objects/target]),
                elf=capture(['aarch64-linux-gnu-readelf','--wide','--sections','--symbols',objects/target]),
                object_sha256=sha(p.ordinary(objects/target,67108864)))
            raw['objects'][target]=item;contexts[target]=seal_base.provenance(target,roots,item,table)
            if target in (NEW_TARGET,seal_base.SEAL_TARGET):
                stem='cpu-metadata-object'if target==NEW_TARGET else'seal-object'
                (out/(stem+'.o')).write_bytes(p.ordinary(objects/target,67108864))
                (out/(stem+'.cmd')).write_bytes(command);(out/(stem+'.su')).write_text(usage)
                (out/(stem+'-elf.log')).write_text(item['elf'])
        source=Path(contexts[OWNER_TARGET][0]['TU']['translation_unit']).parent
        require(sha(p.ordinary(source/'v226_source_stream_kernel.c'))==binding['owner_after_sha256']and
                sha(p.ordinary(source/'Makefile'))==binding['Kbuild_after_sha256'],'actual metadata owner/Kbuild source')
        for path,digest in binding['copied'].items():require(sha(p.ordinary(source/Path(path).name))==digest,'actual new compiler input')
        pending=deque()
        for name in ('n226_ingest_prepared_locked','n279_layout_witness','n285_prepare_metadata','n285_layout_witness'):
            require(name in table and len(table[name])==1,'unique public proof root')
            pending.append(dict(name=name,**table[name][0],offset=0))
        while pending:
            record=pending.popleft();name=record['name'];key=(record['address'],record['bytes']);ident=format(key[0],'016x')+':'+str(key[1])
            if ident in raw['bodies']:continue
            require(len(raw['bodies'])<79,'fixed aggregate capture79')
            symbol=seal_base.scoped.symbol_extent(table,name,record,bool(re.fullmatch(r'OUTLINED_FUNCTION_\d+',name)))
            text=capture(['aarch64-linux-gnu-objdump','-d','--disassemble-zeroes','--start-address='+hex(key[0]),'--stop-address='+hex(sum(key)),objects/'vmlinux'])
            raw['bodies'][ident]=text;raw['records'][ident]=record;persist()
            proof=seal_base.scoped.scoped_transfers(text,symbol,table)
            for edge in proof['external_transfers']:
                records=edge['resolved_records']
                if records and len({(r['address'],r['bytes'])for r in records})==1:
                    selected=[r for r in records if r['name']in NAMED or re.fullmatch(r'OUTLINED_FUNCTION_\d+',r['name'])]
                    if name=='n278_seal_once':continue  # Retained validator frontier, not an old proof replay.
                    if name=='n226_ingest_prepared_locked':selected=[r for r in selected if r['name']in
                        ('n285_snapshot_of_locked','n285_prepare_metadata','n278_seal_once')]
                    if selected:pending.append(selected[0])
        raw['complete']=True;persist()
        proof=verify_metadata(raw,linked);result['current_cpu_metadata_target']=proof
        result.update(metadata_runtime_callers=1,metadata_destination_writes=True,metadata_physical_authority=False,
            metadata_projection_revision='v285',frontdoor_whole_stack_closed=False,hardware_ready=False,physical_ready=False)
        result['metadata_projection_compile'].update(runtime_callers=1,destination_writes=True,
            synthetic_metadata_only=False,live_owner_verified=False)
        # Preserve the established member inventory with honest current source data,
        # not an old seal proof replay or a counterfeit closed-frontier certificate.
        p.save(out/'seal-evidence.json',dict(schema='note10-v285-seal-frontier-v1',**{k:raw[k]for k in
            ('source_head','run_id','build_evidence_id','source_sha256')},complete=True,frontier_closed=False,
            metadata_evidence_sha256=sha(p.ordinary(out/'cpu-metadata-evidence.json',16777216)),hardware_ready=False))
        result['current_owner_seal_target']=dict(schema='note10-v285-seal-order-PC-target-v1',seal_after_readback=True,
            source_coupled_N226_success=True,frontier_closed=False,whole_stack_bound_proven=False,hardware_ready=False)
        return value
    except BaseException as error:
        raw.update(complete=False,rejection=str(error)[:2048]);persist();raise

_ENV={**retained._ENV,**{n:globals()[n]for n in ('WORKFLOW','JOB','BUILD_SCHEMA','CONTEXT_SCHEMA','MANIFEST_SCHEMA',
    'SUCCESS_MEMBERS','source_pins','public_context','install_binding','collect_binding','stream_candidate')}}
run_build=retained._bind(retained.run_build,_ENV,{'note10/private/v283-ci-native-prepare':'note10/private/v285-ci-native-prepare',
    'v283':'v285','"-v283-seal-inventory"':'"-v285-current-owner-cpu-metadata"'})
_SEAL_ENV={**retained.seal.__globals__,**_ENV,'inventory_metadata':inventory_metadata}
seal=bind(retained.seal,_SEAL_ENV)
_ENV.update(run_build=run_build,seal=seal)
main=bind(retained.main,_ENV)

def audit_api():
    require(CAPTURE_SCHEMA==watchdog.CAPTURE_SCHEMA and TARGET_SCHEMA==watchdog.TARGET_SCHEMA and
            callable(source_pins)and callable(public_context)and callable(decode_binding),'actual retained consumer exports')
    require(run_build.__globals__['install_binding']is install_binding and
            run_build.__globals__['collect_binding']is collect_binding and
            main.__globals__['seal']is seal and seal.__globals__['inventory_metadata']is inventory_metadata,
            'actual fresh callback namespaces')

if __name__=='__main__':main()
