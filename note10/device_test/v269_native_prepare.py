"""One current watchdog probe-binding carrier; retained native266 bytes never enter CI."""
import argparse
import base64
import hashlib
import json
import os
import re
from pathlib import Path
import shutil
import subprocess
import sys
import uuid
import zipfile
import v241_native_prepare as original
import v268_native_prepare as baseline
import v267_coupled_carrier_bounds as capacity
from v241_native_prepare import (BASELINE208_IMAGE_BYTES, BASELINE208_LINKED_BYTES, BASELINE212_IMAGE_BYTES, BASELINE212_LINKED_BYTES, CPU_CONFIG, CPU_HEADERS, FALSE_CLAIMS, METADATA_OBJECTS, NODE_SOURCE_GUARDS, PID1_CAP, RETAINED211_PARSER_PASS, SLOT_BYTES, archive_helper, collect_guarded, footprint, generic, house, inspect_pid1, install, leaf_capture, metadata_object_evidence, metadata_symbols, node_config, node_target, observation_target, of_calls, owner, p, query_target, require, sha, stack_sidecar_relative, state_overlay, stream_candidate, tcs_guard)
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
WORKFLOW='.github/workflows/note10-v269-native-prepare.yml'
JOB='v269-native-prepare'
BUILD_SCHEMA='note10-v269-holder-carrier-build-v1'
CONTEXT_SCHEMA='note10-v269-holder-carrier-public-input-v1'
MANIFEST_SCHEMA='note10-v269-holder-carrier-sealed-members-v1'
SUCCESS_MEMBERS=(*original.SUCCESS_MEMBERS,'watchdog-evidence.json')
NEW_FILES=('v269_watchdog_binding.h','v269_watchdog_driver.inc','v269_watchdog_owner.inc','v269_watchdog_binding_fixture.c','test_v269_watchdog_binding.py','v269_native_prepare.py')

def source_pins():
    pins=baseline.source_pins();pins.pop(baseline.WORKFLOW)
    pins.update({'note10/device_test/'+n:sha(p.ordinary(HERE/n))for n in NEW_FILES})
    pins[WORKFLOW]=sha(p.ordinary(ROOT/WORKFLOW));return pins

def public_context(head,passed):
    p.hexid(head,40)
    require(type(passed)is dict and set(passed)=={'passed','groups','variants','assertions','result_sha256'}and passed['passed']is True and(passed['groups'],passed['variants'],passed['assertions'])==(1,12,12),'new three-boundary fixture PASS only')
    p.hexid(passed['result_sha256'])
    return dict(schema=CONTEXT_SCHEMA,source_head=head,source_sha256=source_pins(),new_fixture_PASS=passed,holder_bytes=capacity.SOURCE_CAP,CI_native_source_input_bytes=0)

def run_build(output,context,head):
    require(sys.platform=='linux' and context==public_context(head,context.get('new_fixture_PASS')),
            'exact new267 coupled-reader source context required')
    passed=context['new_fixture_PASS']
    p.hexid(passed['result_sha256']);p.hexid(head,40)
    require(all(os.environ.get(k)==v for k,v in {'GITHUB_SHA':head,'GITHUB_WORKFLOW_SHA':head,'GITHUB_REPOSITORY':'eirblue/ios_note10p',
            'GITHUB_JOB':JOB,'GITHUB_RUN_ATTEMPT':'1'}.items()) and os.environ.get('GITHUB_WORKFLOW_REF','').startswith('eirblue/ios_note10p/'+WORKFLOW+'@'),'exact fresh CI dispatch required')
    out=Path(output).resolve();require(out==ROOT/'note10/private/v269-ci-native-prepare','fixed CI output required')
    work=out.with_name(out.name+'-work');archive=out.with_name(out.name+'-source.tar.gz')
    require(not any(x.exists() for x in (out,work,archive)),'fresh one-use producer required')
    out.mkdir(parents=True);identity=uuid.uuid4().hex
    result=dict(schema=BUILD_SCHEMA,version='v269',producer_revision='v269',kernel_provider_revision='v233',guarded_query_revision='v240',host_fixture_binding_revision='v269',fixture_body_revision='v269',cpu_observation_revision='v231',cpu_stack_provenance_revision='v232',cpu_node_consistency_revision='v233',node_runtime_callers=1,node_runtime_observed=False,requires_fresh_direct_physical_consent=False,requires_fresh_source_run_CPU_ACK=True,atomic_interval_duration_unmeasured=True,scheduler_release_stack_bound_proven=False,compiled_observation_callers=1,cpu_observation_runtime_observed=False,FDT_bound=False,handoff_cpu_selected=False,post_shutdown=False,metadata_projection_revision='v230',metadata_runtime_callers=0,metadata_destination_writes=False,metadata_physical_authority=False,integration_revision='v221',wire_revision='v222',stack_path_revision='v223',metadata_interval_revision='v224',owner_state_revision='v225',source_stream_revision='v226',pool_section_revision='v228',leaf_capture_revision='v229',consumer_revision='v226',PID1_revision='v226',ingest_core_revision='v217',ingest_backend_revision='v219',hash_revision='v219',attribute_revision='v220',compiled_ingestion_callers=1,native_source_allocation_bytes=capacity.SOURCE_CAP+capacity.POOL_BYTES,native_source_allocation_observed=False,CI_native_source_input_bytes=0,hardware_authorized=False,requires_new_CPU_observation_scope=True,requires_new_native_RAM_approval=None,physical_scope_review_required=True,separate_owner_target_attempts=0,passed=False,source_head=head,
                source_sha256=context['source_sha256'],public_input=context,build_evidence_id=identity,
                run_id=int(os.environ['GITHUB_RUN_ID']),run_attempt=1,full_Image_build_attempts=0,target_PID1_compile_links=0,
                old_tests_replayed=0,execution_slot_enabled=False,native_kernel_bytes_in_Image=0,native_adapter_bytes_in_Image=0,
                reservation_bytes=33554432,reservation_delta_vs208=33554432,stages={},**FALSE_CLAIMS)
    def persist():p.save(out/'result.json',result)
    def run(argv,label,timeout=600):
        result['stages'][label]=dict(argv=list(map(str,argv)),status='started');persist()
        with (out/(label+'.log')).open('xb') as log:done=house.run_command(argv,log,timeout)
        result['stages'][label].update(status='completed',returncode=done.returncode);persist()
        if not (out/(label+'.log')).stat().st_size:(out/(label+'.log')).write_bytes(b'completed\n')
        require(done.returncode==0,'producer stage failed: '+label)
    persist()
    try:
        for name in ('clang-14','gcc','make','aarch64-linux-gnu-gcc','arm-linux-gnueabi-gcc','aarch64-linux-gnu-nm','aarch64-linux-gnu-readelf','aarch64-linux-gnu-objdump'):require(shutil.which(name)is not None,'required tool absent: '+name)
        archive_helper.acquire(archive)
        with archive.open('rb') as stream:archive_sha=hashlib.file_digest(stream,'sha256').hexdigest()
        require(archive.stat().st_size==p.ARCHIVE_BYTES and archive_sha==p.ARCHIVE_SHA,'exact stock source archive required')
        work.mkdir();source=archive_helper.extract(archive,work/'source');objects=work/'objects';objects.mkdir()
        result['stock_config_boundary_sha256']={}
        for name,expected in footprint.STOCK_GUARDS.items():
            original=p.ordinary(source/name);footprint.guard_source(original,expected);result['stock_config_boundary_sha256'][name]=sha(original)
        result['OF_call_source_sha256']={name:sha(p.ordinary(source/name))for name in of_calls.SOURCE_GUARDS}
        require(result['OF_call_source_sha256']==of_calls.SOURCE_GUARDS,'exact selected OF/string/locking sources required')
        result['node_API_source_sha256']={name:sha(p.ordinary(source/name))for name in NODE_SOURCE_GUARDS}
        require(result['node_API_source_sha256']==NODE_SOURCE_GUARDS,'exact pinned OF/map/lifetime source required')
        result['cpu_header_sha256']={name:sha(p.ordinary(source/name))for name in CPU_HEADERS}
        require(result['cpu_header_sha256']==CPU_HEADERS,'exact migration/register helper source required')
        buffers={name:p.ordinary(ROOT/name) for name in context['source_sha256']}
        result['preparation']=install(source,identity,buffers,RETAINED211_PARSER_PASS['parser_source_sha256'])
        capacity.install(source,result['preparation'],p.ordinary);result['preparation']['watchdog_binding']=install_binding(source,buffers);persist()
        require({name:sha(p.ordinary(source/name))for name in NODE_SOURCE_GUARDS}==NODE_SOURCE_GUARDS,'compiled OF/map API sources must remain unchanged after overlay')
        require({name:sha(p.ordinary(source/name))for name in of_calls.SOURCE_GUARDS}==of_calls.SOURCE_GUARDS,'selected source guards must survive unchanged overlay')
        compile_sources=[HERE/n for n in ('v226_native_prepare_pid1.c','native_prepare_core.c','native_parcel_core.c')]
        result['target_PID1_compile_links']=1;persist()
        run(['aarch64-linux-gnu-gcc','-std=c11','-Os','-ffreestanding','-fno-builtin','-fno-tree-loop-distribute-patterns','-fno-stack-protector',
             '-fno-pie','-no-pie','-nostdlib','-nodefaultlibs','-static','-Wl,-e,_start','-Wl,--build-id=none','-Wl,-z,max-page-size=4096',
             '-Wall','-Wextra','-Werror','-I',HERE,'-DN212_BUILD_ID="'+identity+'"',*compile_sources,'-o',out/'minimal-init.elf'],'01-pid1')
        run(['aarch64-linux-gnu-nm','--format=posix',out/'minimal-init.elf'],'01-pid1-symbols')
        init=p.ordinary(out/'minimal-init.elf',PID1_CAP);result['PID1_linkage']=inspect_pid1(init,p.ordinary(out/'01-pid1-symbols.log').decode())
        cpio,prefix=generic(init);(out/'initramfs.cpio').write_bytes(cpio)
        make=['make','-C',str(source),'O='+str(objects),'ARCH=arm64','CC=clang-14','CROSS_COMPILE=aarch64-linux-gnu-',
              'CLANG_TRIPLE=aarch64-linux-gnu-','CROSS_COMPILE_ARM32=arm-linux-gnueabi-','GCC_TOOLCHAIN_DIR=/usr/aarch64-linux-gnu/bin/',
              'HOSTCC=gcc','HOSTCFLAGS=-Wno-error=deprecated-declarations','KCFLAGS=-gdwarf-4 -fstack-usage '+ ' '.join(capacity.FLAGS)]
        run([*make,p.DEFCONFIG],'02-defconfig')
        baseline=house.config_values(p.ordinary(objects/'.config'))
        require(baseline.get('NOTE10_V210_NATIVE_PREPARE','n')=='n','new profile must be default off')
        settings=dict(house.SETTINGS,NOTE10_V210_NATIVE_PREPARE='y',KEXEC='n',KEXEC_FILE='n',CRYPTO_SHA256='y',
                      CRYPTO_USER_API_HASH='y',INITRAMFS_SOURCE='"'+str(out/'initramfs.cpio')+'"',LOCALVERSION='"-v269-watchdog-probe-binding"',**footprint.SETTINGS)
        edits=[]
        for key,value in settings.items():edits.extend(['--enable' if value=='y' else '--disable',key] if value in ('y','n') else ['--set-str',key,value[1:-1]] if value.startswith('"') else ['--set-val',key,value])
        run([source/'scripts/config','--file',objects/'.config',*edits],'03-settings');run([*make,'olddefconfig'],'04-config')
        config=p.ordinary(objects/'.config');values=house.config_values(config)
        critical=dict(p.REQUIRED_CONFIG,**settings)
        require(all(values.get(k,'n')==v for k,v in {'S3C2410_WATCHDOG':'y','WATCHDOG':'y','PREEMPT':'y','PREEMPT_COUNT':'y','DEBUG_SPINLOCK':'n','DEBUG_LOCK_ALLOC':'n'}.items()),'unchanged builtin watchdog/lock profile')
        result['effective_profile']=values;result['requested_settings']=settings;result['expected_critical']=critical
        result['configuration_mismatches']={k:dict(expected=v,actual=values.get(k,'n'))for k,v in critical.items()if values.get(k,'n')!=v}
        (out/'actual-effective.config').write_bytes(config);persist()
        for key,value in critical.items():require(values.get(key,'n')==value,'effective setting differs: '+key)
        require(not any(key.startswith('NOTE10_') and value!='n' and key not in settings for key,value in values.items()),'unselected profile forbidden')
        require(all(values.get(k,'n')==v for k,v in CPU_CONFIG.items()),'exact migration-safe CPU profile required')
        result['cpu_observation_config']={k:values.get(k,'n')for k in CPU_CONFIG}
        result['cpu_node_config']=node_config(values)
        result['OF_call_config']={k:values.get(k,'n')for k in of_calls.CONFIG}
        require(result['OF_call_config']==of_calls.CONFIG,'unchanged selected OF/locking config required; do not force settings')
        result['profile_guard']=footprint.effective(values,dict(p.REQUIRED_CONFIG,**settings))
        require(all(values.get(k,'n')==v for k,v in tcs_guard.REQUIRED_CONFIG.items()),'unchanged real sensor/PWM/flash profile required')
        result['tcs3407_config']={k:values.get(k,'n')for k in tcs_guard.REQUIRED_CONFIG}
        result['stock_effective_config_sha256']=sha(json.dumps(baseline,sort_keys=True,separators=(',',':')).encode())
        result['effective_delta_from_stock']={k:dict(before=baseline.get(k,'n'),after=values.get(k,'n')) for k in sorted(set(baseline)|set(values)) if baseline.get(k,'n')!=values.get(k,'n')}
        (out/'actual-effective.config').write_bytes(config);result['effective_profile']=values
        result['cmdline_policy']=sys.modules['builtin_init_route'].builtin_cmdline_policy(config.decode())
        result['full_Image_build_attempts']=1;persist();run([*make,'V=1','-j4','Image'],'05-Image',5400)
        raw=p.ordinary(objects/'arch/arm64/boot/Image',p.IMAGE_LIMIT);symbols=p.ordinary(objects/'System.map',16777216).decode()
        result.update(house.check_image(raw,cpio,identity,symbols,b'N226REQUEST'))
        result['profile_symbol_guard']=footprint.linked_symbols(symbols)
        table={row[2]:int(row[0],16) for line in symbols.splitlines() if len(row:=line.split())==3 and row[2] in ('_text','_end')}
        require(set(table)=={'_text','_end'} and 0<table['_end']-table['_text']<=p.IMAGE_LIMIT,'measured linked extent cap')
        result['linked_end_minus_text']=table['_end']-table['_text']
        result['Image_growth_vs212_bytes']=result['Image_bytes']-BASELINE212_IMAGE_BYTES
        result['linked_growth_vs212_bytes']=result['linked_extent']-BASELINE212_LINKED_BYTES
        result['Image_growth_vs208_bytes']=result['Image_bytes']-BASELINE208_IMAGE_BYTES
        result['linked_growth_vs208_bytes']=result['linked_extent']-BASELINE208_LINKED_BYTES
        result['slot_growth_vs212_bytes']=SLOT_BYTES-4096
        result['kernel_linked_reduction_vs212_bytes']=BASELINE212_LINKED_BYTES+(SLOT_BYTES-4096)-result['linked_extent']
        result['kernel_end_reduction_vs212_bytes']=BASELINE212_LINKED_BYTES+(SLOT_BYTES-4096)-result['linked_end_minus_text']
        result['slot_offset']=result['initramfs_offset']+prefix;result['slot_bytes']=SLOT_BYTES
        require(not any(raw[result['slot_offset']:result['slot_offset']+SLOT_BYTES]),'generic private slot must stay zero')
        result['object_evidence']={}
        for name in ('arch/arm64/mm/init.o','drivers/misc/v154_linux_return.o','init/initramfs.o','drivers/optics/tcs3407.o'):
            obj=p.ordinary(objects/name,67108864);cmdpath=Path(name).with_name('.'+Path(name).name+'.cmd');cmd=p.ordinary(objects/cmdpath)
            require(b'clang-14' in cmd and b'-DMODULE' not in cmd,'same Image builtin command required')
            result['object_evidence'][name]=dict(object_sha256=sha(obj),object_bytes=len(obj),command_sha256=sha(cmd))
            if name=='arch/arm64/mm/init.o':
                (out/'owner-init.o').write_bytes(obj);(out/'owner-init.cmd').write_bytes(cmd)
        owner_command=p.ordinary(out/'owner-init.cmd');stack_relative=stack_sidecar_relative(owner_command)
        stack=p.ordinary(objects/stack_relative);frames=owner.stack_frames(stack.decode());(out/'owner-init.su').write_bytes(stack)
        result['stack_sidecar']=dict(schema='note10-v223-owner-stack-sidecar-v1',relative_path=str(stack_relative),command_sha256=sha(owner_command),stack_sha256=sha(stack))
        run(['aarch64-linux-gnu-nm','--format=posix','--print-size',objects/'arch/arm64/mm/init.o'],'owner-symbols')
        sizes=owner.target_sizes(p.ordinary(out/'owner-symbols.log').decode())
        p.save(out/'target-sizes.json',dict(schema='note10-v241-target-type-sizes-v1',source_head=head,bytes=sizes,allocator_resident_sizes=False))
        p.save(out/'stack-frames.json',dict(schema='note10-v241-target-stack-frames-v1',source_head=head,bytes=frames,total_kernel_stack_bound=False))
        result['target_sizes']=sizes;result['stack_frames']=frames
        result['shared_owner_state']=state_overlay.shared_symbols(p.ordinary(out/'owner-symbols.log').decode(),sizes['state'])
        run(['aarch64-linux-gnu-readelf','--wide','--sections','--symbols',objects/'arch/arm64/mm/init.o'],'owner-sections')
        layout=capacity.target_layout(p.ordinary(out/'owner-symbols.log').decode(),p.ordinary(out/'owner-sections.log').decode(),symbols,len(raw),len(cpio))
        result['source_stream_layout']=layout;result['source_holder_offset']=layout['source_holder_offset'];result['source_holder_bytes']=layout['source_holder_bytes']
        require(not any(raw[layout['source_holder_offset']:layout['source_holder_offset']+layout['source_holder_bytes']]),'public CI source holder must remain all zero')
        require(values.get('HIGHMEM','n')=='n' and values.get('THREAD_INFO_IN_TASK')=='y' and values.get('KASAN','n')=='n' and
            values.get('DEBUG_LOCK_ALLOC','n')=='n' and values.get('DEBUG_VM','n')=='n' and values.get('DEBUG_VIRTUAL','n')=='n' and values.get('UBSAN','n')=='n' and values.get('GCOV_KERNEL','n')=='n' and values.get('VMAP_STACK')=='y','reviewed VMAP-aware stack/direct-page configuration required')
        stack_data=dict(schema='note10-v226-selected-stack-evidence-v1',objects={},assembly={})
        for target in stream_candidate.STACK_TARGETS:
            if target=='arch/arm64/mm/init.o':
                command=owner_command;usage_relative=stream_candidate.compiler_stack_path(command,target);usage=stack.decode()
                elf_evidence=p.ordinary(out/'owner-sections.log').decode()
            else:
                relative=Path(target);cmdpath=relative.with_name('.'+relative.name+'.cmd');command=p.ordinary(objects/cmdpath)
                usage_relative=stream_candidate.compiler_stack_path(command,target);usage=p.ordinary(objects/usage_relative).decode()
                label='stack-object-'+target.replace('/','-')[:-2]
                run(['aarch64-linux-gnu-readelf','--wide','--sections','--symbols',objects/target],label)
                elf_evidence=p.ordinary(out/(label+'.log')).decode()
            stack_data['objects'][target]=dict(command=command.decode(),command_sha256=sha(command),stack_usage=usage,stack_sha256=sha(usage.encode()),stack_relative=str(usage_relative),
                elf_sections_and_symbols=elf_evidence,elf_evidence_sha256=sha(elf_evidence.encode()))
        run(['aarch64-linux-gnu-nm','--format=posix','--print-size','--defined-only',objects/'vmlinux'],'leaf-symbols')
        leaf_symbol_raw=p.ordinary(out/'leaf-symbols.log',16777216)
        stack_data['assembly_symbols']=stream_candidate.leaf_symbols(leaf_symbol_raw.decode())
        stack_data['assembly_symbol_table_sha256']=sha(leaf_symbol_raw)
        for name in ('memcpy','memset','memcmp'):
            run(leaf_capture.command(objects/'vmlinux',stack_data['assembly_symbols'][name]),name+'-disassembly')
            stack_data['assembly'][name]=p.ordinary(out/(name+'-disassembly.log')).decode()
        p.save(out/'stack-evidence.json',stack_data)
        metadata_objects={}
        for target,label in zip(METADATA_OBJECTS,('metadata-projection-elf','metadata-serializer-elf')):
            run(['aarch64-linux-gnu-readelf','--wide','--sections','--symbols',objects/target],label)
            evidence=p.ordinary(out/(label+'.log')).decode()
            relative=Path(target);cmdpath=relative.with_name('.'+relative.name+'.cmd');command=p.ordinary(objects/cmdpath)
            usage_relative=stream_candidate.compiler_stack_path(command,target);usage=p.ordinary(objects/usage_relative).decode()
            proof=metadata_object_evidence(evidence,usage)
            required={'n230_project_metadata'}if target.endswith('/v230_boot_metadata.o')else{'n10_rt_validate_adt','n10_rt_serialize_boot_args','n10_rt_serialize_record'}
            require(required<=set(proof['frames']),'actual metadata compiler frame evidence required')
            metadata_objects[target]=dict(command=command.decode(),command_sha256=sha(command),stack_relative=str(usage_relative),
                stack_usage=usage,stack_sha256=sha(usage.encode()),elf_evidence_sha256=sha(evidence.encode()),**proof)
        result['metadata_projection_compile']=dict(schema='note10-v230-metadata-compile-evidence-v1',
            ABS=metadata_symbols(leaf_symbol_raw.decode()),objects=metadata_objects,runtime_callers=0,destination_writes=False,
            new_writable_section_bytes=0,synthetic_metadata_only=True,complete_ADT=False,live_owner_verified=False)
        result['cpu_observation_target']=observation_target(p.ordinary(out/'owner-symbols.log').decode(),stack.decode(),p.ordinary(out/'owner-sections.log').decode(),owner_command)
        result['cpu_node_target']=node_target(p.ordinary(out/'owner-symbols.log').decode(),stack.decode(),p.ordinary(out/'owner-sections.log').decode(),owner_command)
        result['guarded_query_target']=query_target(p.ordinary(out/'owner-symbols.log').decode(),stack.decode(),p.ordinary(out/'owner-sections.log').decode(),owner_command,leaf_symbol_raw.decode())
        result['guarded_query_graph']=collect_guarded(objects,stack_data,leaf_symbol_raw.decode(),result['guarded_query_target'],out)
        result['node_runtime_callers']=1;result['node_runtime_observed']=False;result['package_stage_supported']=False
        def save_OF_raw(bundle):
            encoded=(json.dumps(bundle,indent=2,sort_keys=True)+'\n').encode('utf-8')
            require(len(encoded)<=of_calls.BUNDLE_CAP,'bounded selected OF raw bundle required')
            p.save(out/'of-call-evidence.json',bundle)
        result['of_call_evidence']=of_calls.collect(objects,stack_data,leaf_symbol_raw.decode(),save_OF_raw,
            json.loads(p.ordinary(out/'guarded-query-evidence.json',8388608)),result['guarded_query_target'])
        result['watchdog_binding_target']=collect_binding(objects,out,result,run,leaf_symbol_raw.decode())
        result['selected_stack_bound']=stream_candidate.verify_stack_evidence(stack_data)
        result['provider_stack_headroom_runtime_observed']=False;result['physical_ready']=False
        result['Image_growth_vs225_bytes']=len(raw)-50466828;result['linked_growth_vs225_bytes']=result['linked_extent']-57114624
        result['PID1_mapped_span_growth_vs225_bytes']=result['PID1_linkage']['mapped_span_bytes']-8192
        result['linked_noninit_growth_vs225_bytes']=layout['linked_noninit_extent']-35422208
        result['linked_noninit_growth_vs229_bytes']=layout['linked_noninit_extent']-41697280
        result['standing60_growth_cap_fit']=result['linked_noninit_growth_vs225_bytes']<=6275072
        result['requires_new_native_RAM_approval']=not result['standing60_growth_cap_fit']
        result['compiled_reader_caps']=dict(source=capacity.SOURCE_CAP,kernel=capacity.KERNEL_CAP,raw=capacity.RAW_CAP);result['capacity_revision']='v267';result['measured_growth_ACK_required']=True
        result['standing62_source_run_ACK_required']=True;result['approval61_new_carrier_applicable']=False
        result['physical_scope_review_required']=True;result['device_stage_supported']=False
        result['physical_ready']=False
        linked={row[2]for line in symbols.splitlines()if len(row:=line.split())==3 and row[1]in ('T','t')}
        require({'n217_consume','n217_ingest_current','n219_ingest_current','n219_sha256_init','n219_sha256_update','n219_sha256_final'}<=linked,'all reviewed owner/hash bodies must be linked, no runtime invocation claimed')
        require(source_pins()==context['source_sha256'],'source changed during build')
        (out/'Image').write_bytes(raw);(out/'System.map').write_text(symbols)
        result.update(passed=True,PID1_sha256=sha(init),PID1_bytes=len(init),effective_config_sha256=sha(config),
                      native_make_target='Image',native_link_validation_status='linked-in-this-Image')
        persist()
    except BaseException as error:
        result.update(error_type=type(error).__name__,error=str(error)[:1024]);persist();raise
    return result

def seal(out,head):
    files=sorted(x for x in out.iterdir() if x.is_file());sizes={x.name:x.stat().st_size for x in files}
    result=json.loads((out/'result.json').read_bytes())
    require(set(sizes)<=set(SUCCESS_MEMBERS)-{'members.json'} and (result['passed']is not True or set(sizes)==set(SUCCESS_MEMBERS)-{'members.json'}),'exact producer members required')
    require(len(files)<=40 and all(not x.is_symlink() and 0<x.stat().st_size<=67108864 for x in files) and sum(sizes.values())<=134217728,'bounded producer evidence required')
    manifest=dict(schema=MANIFEST_SCHEMA,source_head=head,member_bytes=sizes,member_sha256={x.name:sha(p.ordinary(x,67108864)) for x in files},manifest_self_excluded=True)
    p.save(out/'members.json',manifest)
    with zipfile.ZipFile(out.with_suffix('.zip'),'x',compression=zipfile.ZIP_DEFLATED) as bundle:
        for path in [*files,out/'members.json']:bundle.write(path,path.name)
    subprocess.run(['node',str(ROOT/'note10/device_test/sealed_affinity_artifact.cjs'),'seal',str(out.with_suffix('.zip')),
                    str(out.with_suffix('.n10sealed')),head],check=True,timeout=120)

def main():
    cli=argparse.ArgumentParser(description=__doc__);cli.add_argument('--output',required=True,type=Path);cli.add_argument('--expected-source-head',required=True);cli.add_argument('--passed-new-test-context',required=True);args=cli.parse_args()
    pem=base64.b64decode(os.environ['N10_RECIPIENT_PUBLIC_KEY_B64'],validate=True)
    require(sha(pem)=='49e5e0607d3ed0e24e4be5dec4d44caef2cf794586f5c6e51120bf6ca8e07b1f'and b'PRIVATE KEY'not in pem,'current reviewed78 public recipient only')
    context=json.loads(base64.b64decode(args.passed_new_test_context,validate=True))
    try:run_build(args.output,context,args.expected_source_head)
    finally:
        if args.output.is_dir():seal(args.output,args.expected_source_head)

DRIVER='drivers/watchdog/s3c2410_wdt.c'
PREIMAGES={DRIVER:'cea425d01ca901671ee67b644a15a0ee19271c970972894a2be52540f7186166',
 'arch/arm64/mm/init.c':'33072b419318e81a4143ff14c190256bc56dbc68a137bcf70be9edcdcde2f081',
 'arch/arm64/mm/v226_source_stream_kernel.c':'c77fd5ecdd9d0f1728fe946b24fdffc5944319845339895654bbbac9fdb12579',
 'arch/arm64/mm/v210_native_prepare_kernel.c':'11e2b95e1689180236790305467d23ecf60ebc648ae61b72ad9dd5a410be6b39'}
def once(raw,old,new):
    require(raw.count(old)==1,'one exact269 overlay seam');return raw.replace(old,new,1)
def transform_binding(path,raw):
    require(path in PREIMAGES and sha(raw)==PREIMAGES[path],'actual post-house/capacity preimage: '+path)
    if path==DRIVER:
        raw=once(raw,b'static int s3c2410wdt_probe(struct platform_device *pdev)\n',b'#include "v269_watchdog_driver.inc"\nstatic int s3c2410wdt_probe(struct platform_device *pdev)\n')
        raw=once(raw,b'\tint ret, cluster_index;\n',b'\tint ret, cluster_index;\n\tunsigned int n269_token = 0;\n')
        raw=once(raw,b'\ts3c_wdt[cluster_index] = wdt;\n',b'\tif (cluster_index == LITTLE_CLUSTER) n269_token = n269_begin();\n\ts3c_wdt[cluster_index] = wdt;\n')
        raw=once(raw,b'\treturn 0;\n\n err_unregister:',b'\tn269_publish(n269_token, wdt);\n\treturn 0;\n\n err_unregister:')
        raw=once(raw,b'\tstruct s3c2410_wdt *wdt = platform_get_drvdata(dev);\n\n\tif (wdt->drv_data->pmu_reset_func)',b'\tstruct s3c2410_wdt *wdt = platform_get_drvdata(dev);\n\n\tif (wdt) n269_remove(wdt);\n\tif (wdt->drv_data->pmu_reset_func)')
    elif path.endswith('/init.c'):
        raw=once(raw,b'#include "v240_guarded_query.c"\n',b'#include "v240_guarded_query.c"\n#include "v269_watchdog_owner.inc"\n')
    elif path.endswith('/v226_source_stream_kernel.c'):
        raw=once(raw,b'#include "v240_guarded_query.h"\n',b'#include "v240_guarded_query.h"\n#include <linux/v269_watchdog_binding.h>\n')
        raw=once(raw,b'    error=n240_observe_current_cpu(',b'    (void)n269_snapshot((struct n269_binding *)(n226_source_pool+N269_POOL_OFFSET));\n    error=n240_observe_current_cpu(')
    else:
        raw=once(raw,b'static __always_inline void n240_emit(int);\n',b'static __always_inline void n240_emit(int);\nstatic __always_inline void n269_emit(int);\n')
        raw=once(raw,b'n240_emit(error);',b'n240_emit(error);n269_emit(error);')
    return raw
def install_binding(source,buffers):
    records={}
    for name in PREIMAGES:
        path=source/name;before=p.ordinary(path);after=transform_binding(name,before);path.write_bytes(after)
        records[name]=dict(before_sha256=sha(before),after_sha256=sha(after))
    targets={'v269_watchdog_binding.h':'include/linux/v269_watchdog_binding.h','v269_watchdog_driver.inc':'drivers/watchdog/v269_watchdog_driver.inc','v269_watchdog_owner.inc':'arch/arm64/mm/v269_watchdog_owner.inc'}
    for name,relative in targets.items():
        target=source/relative;require(not target.exists(),'fresh269 include target');target.write_bytes(buffers['note10/device_test/'+name])
    return dict(compiler_inputs=records,source_sha256={n:sha(buffers['note10/device_test/'+n])for n in targets},record_bytes=40,pool_offset=43664,new_pool_bytes=0,attempt_before_global=True,null_remove_guard=True,original_hardware_order_retained=True)

def decode_binding(texts,expected):
    require(set(expected)=={'id','boot','cycle'}and all(re.fullmatch('[0-9a-f]{32}',v)for v in expected.values()),'same actual frame identity')
    fields={'id','boot','cycle','result','schema','state','error','cluster','variant','flags','watchdog_id','probe_cached_rate_hz','reserved','post_shutdown','armed','autonomous_return','XNU'};rows=[]
    for text in texts:
        for line in text.splitlines():
            if 'N269WDT 'not in line:continue
            words=line.split('N269WDT ',1)[1].split();row={}
            for word in words:
                require(word.count('=')==1,'exact269 frame token');k,v=word.split('=');require(k not in row,'no duplicate269 field');row[k]=v
            require(set(row)==fields and all(row[k]==v for k,v in expected.items()),'current269 closed frame identity')
            values={k:int(v)for k,v in row.items()if k not in expected}
            require(values['schema']==1 and 0<=values['state']<=6 and values['flags']&~255==0 and values['reserved']==0 and all(values[k]==0 for k in ('post_shutdown','armed','autonomous_return','XNU')),'closed269 values/no authority')
            require(all(0<=values[k]<=0xffffffff for k in ('error','cluster','variant','flags','watchdog_id'))and 0<=values['probe_cached_rate_hz']<=0xffffffffffffffff,'fixed width269 values')
            require(not rows or rows[0]==values,'no conflicting269 frames');rows.append(values)
    require(rows,'actual269 frame missing');v=rows[0]
    qualified=v['result']==v['error']==0 and v['state']==2 and v['cluster']==0 and v['variant']==1 and v['flags']&63==63 and not v['flags']&64 and v['watchdog_id']!=0xffffffff and v['probe_cached_rate_hz']>0
    return dict(schema='note10-v269-watchdog-binding-observation-v1',identity=expected,values=v,qualified=qualified,probe_cached_rate_stale_possible=True,post_shutdown=False,armed=False,autonomous_return=False,XNU=False)

def collect_binding(objects,out,result,run,linked):
    def capture(argv):
        done=subprocess.run(list(map(str,argv)),stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True,timeout=60)
        require(0<len(done.stdout)<=8388608 and len(done.stderr)<=65536,'bounded269 target text');return done.stdout.decode()
    target='drivers/watchdog/s3c2410_wdt.o';obj=objects/target;command=p.ordinary(objects/'drivers/watchdog/.s3c2410_wdt.o.cmd')
    require(b'clang-14'in command and b'-DMODULE'not in command,'same builtin269 driver command')
    usage= p.ordinary(objects/stream_candidate.compiler_stack_path(command,target)).decode();frames=stream_candidate.frames(usage)
    nm=capture(['aarch64-linux-gnu-nm','--format=posix','--print-size',obj]);rows={r[0]:r for l in nm.splitlines()if len(r:=l.split())in (3,4)}
    require(all(len(rows[n])==3 and rows[n][1]=='A'and int(rows[n][2],16)==v for n,v in {'n269_size_binding':40,'n269_align_binding':8}.items()),'actual269 ABI40/8')
    required={'n269_empty','n269_begin','n269_publish','n269_remove','n269_snapshot','n269_layout_witness'}
    require(required<=set(rows)and required<=set(frames),'actual269 driver/helper frames')
    linked_rows={r[0]:r for l in linked.splitlines()if len(r:=l.split())==4}
    owner_rows={r[0]:r for l in p.ordinary(out/'owner-symbols.log').decode().splitlines()if len(r:=l.split())==4}
    require(int(owner_rows['n269_binding_storage'][3],16)==40 and int(owner_rows['n269_binding_storage'][2],16)-int(owner_rows['n226_source_pool'][2],16)==43664,'actual269 pool alias')
    disassembly={};edges={};allowed={'memcpy','memset','_raw_spin_lock','_raw_spin_trylock','_raw_spin_unlock','preempt_schedule','preempt_schedule_notrace','__stack_chk_fail','queued_spin_lock_slowpath'}
    for name in sorted(required):
        require(name in linked_rows and int(rows[name][3],16)==int(linked_rows[name][3],16)>0,'actual269 linked body')
        body=capture(['aarch64-linux-gnu-objdump','-dr','--disassemble='+name,obj]);disassembly[name]=body
        calls=set(re.findall(r'R_AARCH64_(?:CALL26|JUMP26)\s+(\S+)',body));edges[name]=sorted(calls)
        require(calls<=required|allowed and not re.search(r'\bblr\b',body),'no new269 indirect/hardware/external callback')
        require(frames[name]['kind']=='static'and 0<=frames[name]['bytes']<=8192,'actual269 static helper frame')
    owner_call=capture(['aarch64-linux-gnu-objdump','-dr','--disassemble=n226_ingest_prepared_locked',objects/'arch/arm64/mm/init.o'])
    require(len(re.findall(r'R_AARCH64_CALL26\s+n269_snapshot\b',owner_call))==1,'one actual269 current owner caller')
    writable={n:int(row[3],16)for n,row in rows.items()if n.startswith('n269_')and len(row)==4 and row[1]in('b','B','d','D')}
    require(writable.get('n269_cache')==40 and set(writable)=={'n269_cache','n269_cache_lock'},'actual269 named driver writable inventory')
    value=dict(schema='note10-v269-watchdog-binding-target-v1',source_head=result['source_head'],run_id=result['run_id'],compiled_current_callers=1,record_bytes=40,pool_offset=43664,new_pool_bytes=0,driver_object_sha256=sha(p.ordinary(obj,67108864)),driver_command_sha256=sha(command),driver_writable_bytes=writable,driver_writable_total_bytes=sum(writable.values()),frames={n:frames[n]for n in required},external_edges=edges,disassembly=disassembly,owner_call_disassembly=owner_call,driver_symbols=nm,probe_cached_rate_stale_possible=True,armed=False,autonomous_return=False,post_shutdown=False)
    p.save(out/'watchdog-evidence.json',value)
    return {k:v for k,v in value.items()if k not in ('disassembly','owner_call_disassembly','driver_symbols')}

if __name__=='__main__':main()


