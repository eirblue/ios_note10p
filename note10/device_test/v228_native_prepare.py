"""226 PC-only candidate Image with bounded readonly source/stream workspace; no hardware admission."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import uuid
import zipfile
import v227_native_prepare as retained
import v226_source_stream as stream_candidate
import v228_source_pool_section as pool_section
state_overlay=retained.state_overlay
p,house,archive_helper=retained.p,retained.house,retained.archive_helper
footprint,tcs_guard=retained.footprint,retained.tcs_guard
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
WORKFLOW='.github/workflows/note10-v228-native-prepare.yml'
JOB='v228-native-prepare'
BUILD_SCHEMA='note10-v228-current-metadata-prepare-build-v1'
CONTEXT_SCHEMA='note10-v228-current-metadata-prepare-public-input-v1'
MANIFEST_SCHEMA='note10-v228-current-metadata-prepare-sealed-members-v1'
FIXTURE_SCHEMA='note10-v228-source-pool-section-fixture-result-v1'
PUBLIC_NEW=('v228_source_pool_section.py','test_v228_source_pool_section.py','v228_native_prepare.py')
SLOT_BYTES,PID1_CAP=4096,65536
require,sha=retained.require,retained.sha
private_member=retained.private_member
inspect_pid1,generic=stream_candidate.inspect_pid1,stream_candidate.generic
insert_private=stream_candidate.insert_private
stack_sidecar_relative=retained.stack_sidecar_relative
RETAINED211_PARSER_PASS=retained.RETAINED211_PARSER_PASS
SUCCESS_MEMBERS=retained.SUCCESS_MEMBERS
FALSE_CLAIMS=retained.FALSE_CLAIMS
owner=retained.owner
BASELINE212_IMAGE_BYTES=46284812
BASELINE212_LINKED_BYTES=55005184
BASELINE208_IMAGE_BYTES=46282764
BASELINE208_LINKED_BYTES=55001088
CARRIED221_FIXTURE_PASS={'schema': 'note10-v221-current-metadata-prepare-fixture-result-v1', 'passed': True, 'groups': 3, 'variants': 6, 'assertions': 8, 'source_head': '69f3c6dc216887be67cca74ac0a5cfaafd6e5e1b', 'result_sha256': '331ec279fe4e77f93783629980789f6dc9fdb15a423dc3dfb6a1a1400b549817'}
FROZEN227_MAP_SHA256='8f4b4c88d65ad6526fa1a1f98027bd73beb27d660e23aa1eacb80f09e55ccff8'

CARRIED222_FIXTURE_PASS={'schema': 'note10-v222-context-wire-fixture-result-v1', 'passed': True, 'groups': 1, 'variants': 3, 'assertions': 3, 'source_head': 'a7279228e86e547c786d2d997f606bf1577da579', 'result_sha256': '60080df47d8dc17510dad914aa34d102d6975905207f1fb3c61c667e3fffd352'}
CARRIED220_FIXTURE_PASS={'schema': 'note10-v220-noinline-macro-fixture-result-v1', 'passed': True, 'groups': 2, 'variants': 4, 'assertions': 4, 'source_head': '33067740ef869eaba9e6ba204a4ac3ed78f94500', 'result_sha256': '8a3531b63476b2b56cb9295d57f9480ef826620de6c27b32eaceaba7b57c0a0b'}


CARRIED223_FIXTURE_PASS={'schema': 'note10-v223-stack-sidecar-fixture-result-v1', 'passed': True, 'groups': 1, 'variants': 8, 'assertions': 8, 'source_head': '3b8eb848e2e0bf27b278374677aa89bff5109bbd', 'result_sha256': '47454ac2a2fdef65ba1656e6c153edbc5d420a5dd9f21c0116f4847104876625'}

CARRIED224_FIXTURE_PASS={'schema': 'note10-v224-metadata-interval-fixture-result-v1', 'passed': True, 'groups': 1, 'variants': 10, 'assertions': 10, 'source_head': '0c8fe959d0d1003746f41adb5c3f4766bf5784b6', 'result_sha256': '017b3f5244c2dc479c3c2ec14876172becbcdc2e07dec347af78cc9da9229c27'}

CARRIED225_FIXTURE_PASS={'schema': 'note10-v225-shared-owner-state-fixture-result-v1', 'passed': True, 'groups': 1, 'variants': 3, 'assertions': 6, 'source_head': '2530bfde8dd791abec634a15fa1db5b029c8b74d', 'result_sha256': 'd2f8fc36bf2cbafc592eabf8f3eb7b67e3f4e013dc9464a50239d617b7f6afd0'}

CARRIED227_FIXTURE_PASS={'schema': 'note10-v227-host-uintptr-inflate-fixture-result-v1', 'passed': True, 'groups': 2, 'variants': 15, 'assertions': 35, 'source_head': '93f027b4b501313b5dca10d942dd3e53b59d4dcc', 'result_sha256': '6873d6038aaf79357f03a9eee0ec3c73f1074eee394a2af7b7ce09f59beb718a'}

CARRIED226_PARTIAL_PYTHON={'schema': 'note10-v226-carried-partial-python-summary-v1', 'groups': 2, 'variants': 10, 'assertions': 20, 'source_head': 'eaeb1a7a8a5d28739777b40ef13b870f428a180b', 'result_sha256': '8f7dda8b434e6cbfbfc7c72314ffce8fcd4b787078db598b0007103ba7f0e2c5', 'basis': 'inferred-from-frozen-control-flow-and-compile-entry', 'whole_fixture_passed': False}

encode_context_wire,decode_context_wire=retained.encode_context_wire,retained.decode_context_wire


install=pool_section.install


def source_pins():
    pins=retained.source_pins()
    require(sha(json.dumps(pins,sort_keys=True,separators=(',',':')).encode())==FROZEN227_MAP_SHA256,'reviewed227source map changed')
    pins.update({'note10/device_test/'+name:sha(p.ordinary(HERE/name))for name in PUBLIC_NEW})
    pins[WORKFLOW]=sha(p.ordinary(ROOT/WORKFLOW));return pins


def public_context(head,passed):
    p.hexid(head,40)
    require(type(passed)is dict and set(passed)=={'schema','passed','groups','variants','assertions','result_sha256'} and
        passed['schema']==FIXTURE_SCHEMA and passed['passed']is True and (passed['groups'],passed['variants'],passed['assertions'])==(1,2,2),'exact new228source-section fixture PASS required')
    p.hexid(passed['result_sha256'])
    return dict(schema=CONTEXT_SCHEMA,source_head=head,source_sha256=source_pins(),new_fixture_PASS=passed,carried221_fixture_PASS=CARRIED221_FIXTURE_PASS,carried222_fixture_PASS=CARRIED222_FIXTURE_PASS,carried220_fixture_PASS=CARRIED220_FIXTURE_PASS,carried223_fixture_PASS=CARRIED223_FIXTURE_PASS,carried224_fixture_PASS=CARRIED224_FIXTURE_PASS,carried225_fixture_PASS=CARRIED225_FIXTURE_PASS,carried226_partial_python=CARRIED226_PARTIAL_PYTHON,carried227_fixture_PASS=CARRIED227_FIXTURE_PASS)

def run_build(output,context,head):
    require(sys.platform=='linux' and context==public_context(head,context.get('new_fixture_PASS')),
            'exact new228synthetic metadata context required')
    passed=context['new_fixture_PASS']
    p.hexid(passed['result_sha256']);p.hexid(head,40)
    require(all(os.environ.get(k)==v for k,v in {'GITHUB_SHA':head,'GITHUB_WORKFLOW_SHA':head,'GITHUB_REPOSITORY':'eirblue/ios_note10p',
            'GITHUB_JOB':JOB,'GITHUB_RUN_ATTEMPT':'1'}.items()) and os.environ.get('GITHUB_WORKFLOW_REF','').startswith('eirblue/ios_note10p/'+WORKFLOW+'@'),'exact fresh CI dispatch required')
    out=Path(output).resolve();require(out==ROOT/'note10/private/v228-ci-native-prepare','fixed CI output required')
    work=out.with_name(out.name+'-work');archive=out.with_name(out.name+'-source.tar.gz')
    require(not any(x.exists() for x in (out,work,archive)),'fresh one-use producer required')
    out.mkdir(parents=True);identity=uuid.uuid4().hex
    result=dict(schema=BUILD_SCHEMA,version='v228',producer_revision='v228',integration_revision='v221',wire_revision='v222',stack_path_revision='v223',metadata_interval_revision='v224',owner_state_revision='v225',source_stream_revision='v226',pool_section_revision='v228',consumer_revision='v226',PID1_revision='v226',ingest_core_revision='v217',ingest_backend_revision='v219',hash_revision='v219',attribute_revision='v220',compiled_ingestion_callers=1,native_source_allocation_bytes=6258688,native_source_allocation_observed=False,CI_native_source_input_bytes=0,hardware_authorized=False,requires_new_native_RAM_approval=True,separate_owner_target_attempts=0,passed=False,source_head=head,
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
        buffers={name:p.ordinary(ROOT/name) for name in context['source_sha256']}
        result['preparation']=install(source,identity,buffers,RETAINED211_PARSER_PASS['parser_source_sha256']);persist()
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
              'HOSTCC=gcc','HOSTCFLAGS=-Wno-error=deprecated-declarations','KCFLAGS=-gdwarf-4 -fstack-usage']
        run([*make,p.DEFCONFIG],'02-defconfig')
        baseline=house.config_values(p.ordinary(objects/'.config'))
        require(baseline.get('NOTE10_V210_NATIVE_PREPARE','n')=='n','new profile must be default off')
        settings=dict(house.SETTINGS,NOTE10_V210_NATIVE_PREPARE='y',KEXEC='n',KEXEC_FILE='n',CRYPTO_SHA256='y',
                      CRYPTO_USER_API_HASH='y',INITRAMFS_SOURCE='"'+str(out/'initramfs.cpio')+'"',LOCALVERSION='"-v228-current-metadata-prepare"',**footprint.SETTINGS)
        edits=[]
        for key,value in settings.items():edits.extend(['--enable' if value=='y' else '--disable',key] if value in ('y','n') else ['--set-str',key,value[1:-1]] if value.startswith('"') else ['--set-val',key,value])
        run([source/'scripts/config','--file',objects/'.config',*edits],'03-settings');run([*make,'olddefconfig'],'04-config')
        config=p.ordinary(objects/'.config');values=house.config_values(config)
        critical=dict(p.REQUIRED_CONFIG,**settings)
        result['effective_profile']=values;result['requested_settings']=settings;result['expected_critical']=critical
        result['configuration_mismatches']={k:dict(expected=v,actual=values.get(k,'n'))for k,v in critical.items()if values.get(k,'n')!=v}
        (out/'actual-effective.config').write_bytes(config);persist()
        for key,value in critical.items():require(values.get(key,'n')==value,'effective setting differs: '+key)
        require(not any(key.startswith('NOTE10_') and value!='n' and key not in settings for key,value in values.items()),'unselected profile forbidden')
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
        p.save(out/'target-sizes.json',dict(schema='note10-v228-target-type-sizes-v1',source_head=head,bytes=sizes,allocator_resident_sizes=False))
        p.save(out/'stack-frames.json',dict(schema='note10-v228-target-stack-frames-v1',source_head=head,bytes=frames,total_kernel_stack_bound=False))
        result['target_sizes']=sizes;result['stack_frames']=frames
        result['shared_owner_state']=state_overlay.shared_symbols(p.ordinary(out/'owner-symbols.log').decode(),sizes['state'])
        run(['aarch64-linux-gnu-readelf','--wide','--sections','--symbols',objects/'arch/arm64/mm/init.o'],'owner-sections')
        layout=stream_candidate.target_layout(p.ordinary(out/'owner-symbols.log').decode(),p.ordinary(out/'owner-sections.log').decode(),symbols,len(raw),len(cpio))
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
            run(['aarch64-linux-gnu-objdump','--disassemble='+name,objects/'vmlinux'],name+'-disassembly')
            stack_data['assembly'][name]=p.ordinary(out/(name+'-disassembly.log')).decode()
        result['selected_stack_bound']=stream_candidate.verify_stack_evidence(stack_data)
        p.save(out/'stack-evidence.json',stack_data)
        result['provider_stack_headroom_runtime_observed']=False;result['physical_ready']=False
        result['Image_growth_vs225_bytes']=len(raw)-50466828;result['linked_growth_vs225_bytes']=result['linked_extent']-57114624
        result['PID1_mapped_span_growth_vs225_bytes']=result['PID1_linkage']['mapped_span_bytes']-8192
        result['linked_noninit_growth_vs225_bytes']=layout['linked_noninit_extent']-35422208
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
    require(len(files)<=32 and all(not x.is_symlink() and 0<x.stat().st_size<=67108864 for x in files) and sum(sizes.values())<=134217728,'bounded producer evidence required')
    manifest=dict(schema=MANIFEST_SCHEMA,source_head=head,member_bytes=sizes,member_sha256={x.name:sha(p.ordinary(x,67108864)) for x in files},manifest_self_excluded=True)
    p.save(out/'members.json',manifest)
    with zipfile.ZipFile(out.with_suffix('.zip'),'x',compression=zipfile.ZIP_DEFLATED) as bundle:
        for path in [*files,out/'members.json']:bundle.write(path,path.name)
    subprocess.run(['node',str(ROOT/'note10/device_test/sealed_affinity_artifact.cjs'),'seal',str(out.with_suffix('.zip')),
                    str(out.with_suffix('.n10sealed')),head],check=True,timeout=120)

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--expected-source-head',required=True);parser.add_argument('--passed-new-test-context',required=True)
    args=parser.parse_args();house.recipient(os.environ['N10_RECIPIENT_PUBLIC_KEY_B64'])
    context=decode_context_wire(args.passed_new_test_context)
    try:run_build(args.output,context,args.expected_source_head)
    finally:
        if args.output.is_dir():seal(args.output,args.expected_source_head)

if __name__=='__main__':main()
