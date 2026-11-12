"""220macro-safe attribute transform; unchanged219SHA algorithm and owner ABI."""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import uuid
import zipfile
import v219_native_source_prepare as retained
p,house,archive_helper=retained.p,retained.house,retained.archive_helper
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
WORKFLOW='.github/workflows/note10-v220-native-source-budget.yml'
JOB='v220-native-source-budget'
BUILD_SCHEMA='note10-v220-noinline-object-build-v1'
CONTEXT_SCHEMA='note10-v220-noinline-public-input-v1'
MANIFEST_SCHEMA='note10-v220-noinline-sealed-members-v1'
FIXTURE_SCHEMA='note10-v220-noinline-macro-fixture-result-v1'
PUBLIC_NEW=('v220_native_source_prepare.py','test_v220_noinline_macro.py')
SUCCESS_MEMBERS=retained.SUCCESS_MEMBERS
require,sha=retained.require,retained.sha
STOCK_USR=retained.STOCK_USR
object_profile,object_mismatches=retained.object_profile,retained.object_mismatches
target_sizes,stack_frames=retained.target_sizes,retained.stack_frames
STOCK_MACRO_URL='https://raw.githubusercontent.com/corsicanu/android_kernel_samsung_universal9820/55f042627bb7030c93550faafa117674d32b21d1/include/linux/compiler-gcc.h'
STOCK_MACRO_BYTES=12488
STOCK_MACRO_SHA256='cdd7c6ef076b771b1cf3598a8dd2de70dad38ff33bbb5f142d29d09e78c16d40'
MACRO_ARG='-Dnoinline=__attribute__((noinline))'
BEFORE=b'__attribute__((noinline))'
AFTER=b'__attribute__((__noinline__))'
ORIGINAL_SHA256='26fa58f3905a1b9c0e1b83f267fe9d3e3992a0e1f11dee42a1bc144efd4da1c6'
ORIGINAL_BYTES=11947
PATCHED_SHA256='514d15b9e045df097332b140175bb0f8c8593a5dc585ceb22ec9546c4bf2cdac'
FROZEN219_MAP_SHA256='d07bbc02a07f56ecd24f20646a149ff1463abcba0d72f02d557faacaa2384b8f'


def patch_noinline(raw):
    require(type(raw)is bytes and len(raw)==ORIGINAL_BYTES and sha(raw)==ORIGINAL_SHA256 and
            raw.count(BEFORE)==4 and AFTER not in raw,'exact closed original219SHA source required; duplicate/mutated input denied')
    changed=raw.replace(BEFORE,AFTER)
    require(changed.count(AFTER)==4 and BEFORE not in changed and sha(changed)==PATCHED_SHA256,'exact four-token patched source required')
    return changed


def stock_macro(raw):
    require(type(raw)is bytes and len(raw)==STOCK_MACRO_BYTES and sha(raw)==STOCK_MACRO_SHA256 and
            raw.splitlines()[103]==b'#define  noinline\t__attribute__((noinline))','exact pinned stock compiler macro required')
    return MACRO_ARG


def object_settings():return dict(retained.object_settings(),LOCALVERSION='"-v220-noinline-object"')
def critical_settings():return dict(p.REQUIRED_CONFIG,**object_settings())


def source_pins():
    pins=retained.source_pins()
    require(sha(json.dumps(pins,sort_keys=True,separators=(',',':')).encode())==FROZEN219_MAP_SHA256,'retained219source map changed')
    pins.update({'note10/device_test/'+name:sha(p.ordinary(HERE/name))for name in PUBLIC_NEW})
    pins[WORKFLOW]=sha(p.ordinary(ROOT/WORKFLOW));return pins


def public_context(head,passed):
    p.hexid(head,40)
    require(type(passed)is dict and set(passed)=={'schema','passed','groups','variants','assertions','result_sha256'} and
            passed['schema']==FIXTURE_SCHEMA and passed['passed']is True and passed['groups']==2 and
            passed['variants']==4 and passed['assertions']==4,'exact new2/4/4macro fixture PASS required')
    p.hexid(passed['result_sha256'])
    return dict(schema=CONTEXT_SCHEMA,source_head=head,source_sha256=source_pins(),new_fixture_PASS=passed)


def install(source,identity,buffers):
    result=retained.install(source,identity,buffers)
    macro=p.ordinary(source/'include/linux/compiler-gcc.h');stock_macro(macro)
    target=source/'arch/arm64/mm/native_source_sha256.c';original=p.ordinary(target);changed=patch_noinline(original)
    target.write_bytes(changed)
    result['noinline_macro_transform']=dict(path='arch/arm64/mm/native_source_sha256.c',before_sha256=sha(original),after_sha256=sha(changed),
        replacements=4,compiler_macro_sha256=sha(macro),SHA_algorithm_changed=False,old_repository_sources_modified=False)
    return result

def run_build(output,context,head):
    require(sys.platform=='linux' and context==public_context(head,context.get('new_fixture_PASS')),'exact public-only220context required')
    require(all(os.environ.get(k)==v for k,v in {'GITHUB_SHA':head,'GITHUB_WORKFLOW_SHA':head,'GITHUB_REPOSITORY':'eirblue/ios_note10p',
        'GITHUB_JOB':JOB,'GITHUB_RUN_ATTEMPT':'1'}.items()) and os.environ.get('GITHUB_WORKFLOW_REF','').startswith('eirblue/ios_note10p/'+WORKFLOW+'@'),'fresh source-bound dispatch required')
    out=Path(output).resolve();require(out==ROOT/'note10/private/v220-ci-source-budget','fixed CI output required')
    work=out.with_name(out.name+'-work');archive=out.with_name(out.name+'-source.tar.gz')
    require(not any(x.exists()for x in (out,work,archive)),'fresh producer paths required');out.mkdir(parents=True)
    identity=uuid.uuid4().hex
    result=dict(schema=BUILD_SCHEMA,passed=False,version='v220',producer_revision='v220',source_ingest_revision='v217',hash_revision='v219',attribute_revision='v220',accounting_revision='v219',source_head=head,source_sha256=context['source_sha256'],
        public_input=context,build_evidence_id=identity,run_id=int(os.environ['GITHUB_RUN_ID']),run_attempt=1,
        owner_TU_target_attempts=0,full_Image_build_attempts=0,target_PID1_links=0,old_tests_replayed=0,runtime_callers=0,
        native_input_reads=0,physical_runtime_verified=False,device_authorized=False,complete_numeric_peak=False,stages={})
    def persist():p.save(out/'result.json',result)
    def run(argv,label,timeout=600):
        result['stages'][label]=dict(argv=list(map(str,argv)),status='started');persist()
        with (out/(label+'.log')).open('xb')as log:done=house.run_command(argv,log,timeout)
        result['stages'][label].update(status='completed',returncode=done.returncode);persist()
        if not(out/(label+'.log')).stat().st_size:(out/(label+'.log')).write_bytes(b'completed\n')
        require(done.returncode==0,'producer stage failed: '+label)
    persist()
    try:
        for name in ('clang-14','gcc','make','aarch64-linux-gnu-gcc','aarch64-linux-gnu-nm'):require(shutil.which(name)is not None,'required tool absent: '+name)
        archive_helper.acquire(archive)
        with archive.open('rb')as stream:archive_sha=hashlib.file_digest(stream,'sha256').hexdigest()
        require(archive.stat().st_size==p.ARCHIVE_BYTES and archive_sha==p.ARCHIVE_SHA,'exact stock archive required')
        work.mkdir();source=archive_helper.extract(archive,work/'source');objects=work/'objects';objects.mkdir()
        result['empty_initramfs_stock_policy']={}
        for name,(size,digest)in STOCK_USR.items():
            raw=p.ordinary(source/name);require(len(raw)==size and sha(raw)==digest,'exact stock empty-initramfs policy required')
            result['empty_initramfs_stock_policy'][name]=dict(bytes=len(raw),sha256=sha(raw))
        buffers={name:p.ordinary(ROOT/name)for name in context['source_sha256']};result['preparation']=install(source,identity,buffers);persist()
        make=['make','-C',str(source),'O='+str(objects),'ARCH=arm64','CC=clang-14','CROSS_COMPILE=aarch64-linux-gnu-',
            'CLANG_TRIPLE=aarch64-linux-gnu-','CROSS_COMPILE_ARM32=arm-linux-gnueabi-','GCC_TOOLCHAIN_DIR=/usr/aarch64-linux-gnu/bin/',
            'HOSTCC=gcc','HOSTCFLAGS=-Wno-error=deprecated-declarations','KCFLAGS=-gdwarf-4 -fstack-usage']
        run([*make,p.DEFCONFIG],'01-defconfig')
        settings=object_settings()
        edits=[]
        for key,value in settings.items():edits.extend(['--enable'if value=='y'else'--disable',key]if value in ('y','n')else['--set-str',key,value[1:-1]]if value.startswith('"')else['--set-val',key,value])
        run([source/'scripts/config','--file',objects/'.config',*edits],'02-settings');run([*make,'olddefconfig'],'03-config')
        config=p.ordinary(objects/'.config');values=house.config_values(config)
        critical=critical_settings()
        result['effective_profile']=values;result['effective_config_sha256']=sha(config)
        result['requested_settings']=settings;result['expected_critical']=critical
        result['configuration_mismatches']=object_mismatches(values,critical)
        (out/'actual-effective.config').write_bytes(config);persist()
        result['profile_guard']=object_profile(values,critical)
        require(values.get('ARM64_4K_PAGES')=='y' and values.get('SLUB')=='y' and values.get('DEFERRED_INITCALLS')=='y','actual accounting configuration required')
        result['owner_TU_target_attempts']=1;persist();run([*make,'V=1','-j4','arch/arm64/mm/init.o'],'04-owner-object',2400)
        target=objects/'arch/arm64/mm/init.o';command=objects/'arch/arm64/mm/.init.o.cmd'
        obj=p.ordinary(target,67108864);cmd=p.ordinary(command)
        require(b'clang-14'in cmd and b'-DMODULE'not in cmd,'actual builtin owner TU command required')
        (out/'owner-init.o').write_bytes(obj);(out/'owner-init.cmd').write_bytes(cmd)
        run(['aarch64-linux-gnu-nm','--format=posix','--print-size',target],'05-symbols')
        sizes=target_sizes(p.ordinary(out/'05-symbols.log').decode());p.save(out/'target-sizes.json',dict(schema='note10-v220-target-type-sizes-v1',source_head=head,bytes=sizes,allocator_resident_sizes=False))
        stack=p.ordinary(objects/'arch/arm64/mm/init.su');frames=stack_frames(stack.decode())
        (out/'owner-init.su').write_bytes(stack)
        p.save(out/'stack-frames.json',dict(schema='note10-v220-target-stack-frames-v1',source_head=head,bytes=frames,total_kernel_stack_bound=False))
        require(source_pins()==context['source_sha256'],'source changed during producer')
        result.update(passed=True,target_sizes=sizes,stack_frames=frames,provider_heap_requests=0,global_destination_no_replay_proven=False,object_bytes=len(obj),object_sha256=sha(obj),command_sha256=sha(cmd),
            effective_config_sha256=sha(config),native_make_target='arch/arm64/mm/init.o',native_link_validation_status='target-owner-TU-compiled-only')
        persist()
    except BaseException as error:result.update(error_type=type(error).__name__,error=str(error)[:1024]);persist();raise
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
    context=json.loads(base64.b64decode(args.passed_new_test_context,validate=True));require(len(json.dumps(context))<=65536,'bounded public context required')
    try:run_build(args.output,context,args.expected_source_head)
    finally:
        if args.output.is_dir():seal(args.output,args.expected_source_head)

if __name__=='__main__':main()
