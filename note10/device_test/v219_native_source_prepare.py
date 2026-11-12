"""219direct hash/request evidence: owner TU only; no caller/Image/PID1."""
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
import v218_native_source_prepare as retained
p,house,archive_helper=retained.p,retained.house,retained.archive_helper
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
WORKFLOW='.github/workflows/note10-v219-native-source-budget.yml'
JOB='v219-native-source-budget'
BUILD_SCHEMA='note10-v219-source-budget-object-build-v1'
CONTEXT_SCHEMA='note10-v219-source-budget-public-input-v1'
MANIFEST_SCHEMA='note10-v219-source-budget-sealed-members-v1'
FIXTURE_SCHEMA='note10-v219-source-budget-fixture-result-v1'
PUBLIC_NEW=('native_source_sha256.h','native_source_sha256.c','native_source_sha256_fixture.c','v219_source_owner_kernel.c',
            'native_source_request_budget.py','test_native_source_request_budget.py','v219_native_source_prepare.py')
SUCCESS_MEMBERS=retained.SUCCESS_MEMBERS+('owner-init.su','stack-frames.json')
require,sha=retained.require,retained.sha
STOCK_USR=retained.STOCK_USR
object_profile,object_mismatches=retained.object_profile,retained.object_mismatches
NEW_SIZE_NAMES=('sha_state','kernel_context','cpio_dir')
FRAME_NAMES=('n219_sha256_transform','n219_sha256_init','n219_sha256_update','n219_sha256_final','n219_ingest_current')
FROZEN218_MAP_SHA256='d4709187511955be5ee6a2d4945ca85882b96c3085c55e361bb4f4c8731c3127'


def object_settings():return dict(retained.object_settings(),LOCALVERSION='"-v219-source-budget-object"')
def critical_settings():return dict(p.REQUIRED_CONFIG,**object_settings())

def source_pins():
    pins=retained.source_pins()
    require(sha(json.dumps(pins,sort_keys=True,separators=(',',':')).encode())==FROZEN218_MAP_SHA256,'retained218source map changed')
    pins.update({'note10/device_test/'+name:sha(p.ordinary(HERE/name))for name in PUBLIC_NEW})
    pins[WORKFLOW]=sha(p.ordinary(ROOT/WORKFLOW));return pins

def public_context(head,passed):
    p.hexid(head,40)
    require(type(passed)is dict and set(passed)=={'schema','passed','groups','variants','assertions','result_sha256'} and
            passed['schema']==FIXTURE_SCHEMA and passed['passed']is True and passed['groups']==7 and
            passed['variants']==14 and passed['assertions']==25,'exact new7/14/25PASS required')
    p.hexid(passed['result_sha256'])
    return dict(schema=CONTEXT_SCHEMA,source_head=head,source_sha256=source_pins(),new_fixture_PASS=passed)

def install(source,identity,buffers):
    result=retained.install(source,identity,buffers)
    target=source/'arch/arm64/mm/init.c';raw=p.ordinary(target)
    anchor=b'#include "v217_source_owner_kernel.c"\n#endif\n'
    require(raw.count(anchor)==1,'exact retained217 neutral callback seam required')
    added=b'#include "native_source_sha256.c"\n#include "v219_source_owner_kernel.c"\n'
    changed=raw.replace(anchor,anchor.replace(b'#endif\n',added+b'#endif\n'),1);target.write_bytes(changed)
    names=('native_source_sha256.h','native_source_sha256.c','v219_source_owner_kernel.c')
    for name in names:(target.parent/name).write_bytes(buffers['note10/device_test/'+name])
    result['fixed_source_budget_boundary']=dict(before_sha256=sha(raw),after_sha256=sha(changed),
        source_sha256={name:sha(buffers['note10/device_test/'+name])for name in names},runtime_callers=0,
        old_globals_mutated=False,global_destination_no_replay_proven=False)
    return result

def target_sizes(symbols):
    sizes=retained.target_sizes(symbols);rows=[line.split()for line in symbols.splitlines()if line.strip()]
    for name in NEW_SIZE_NAMES:
        found=[row for row in rows if row[0]=='n219_size_'+name]
        require(len(found)==1 and len(found[0])==4 and found[0][1]in ('R','r'),'actual new target sizeof required')
        sizes['n219_'+name]=int(found[0][3],16);require(0<sizes['n219_'+name]<=1048576,'new sizeof cap')
    for name in ('n219_ingest_current','n219_sha256_init','n219_sha256_update','n219_sha256_final'):
        require(len([row for row in rows if row[0]==name and row[1]in ('T','t')])==1,'new direct hash/entry body required')
    return sizes

def stack_frames(raw):
    rows={}
    for line in raw.splitlines():
        fields=line.split('\t')
        if len(fields)!=3:continue
        name=fields[0].rsplit(':',1)[-1]
        if name in FRAME_NAMES:
            require(name not in rows and fields[2]=='static' and fields[1].isdigit() and 0<=int(fields[1])<=1048576,'unique bounded static frame required')
            rows[name]=int(fields[1])
    require(set(rows)==set(FRAME_NAMES),'all new static frames required; not total kernel-stack claim')
    return rows

def run_build(output,context,head):
    require(sys.platform=='linux' and context==public_context(head,context.get('new_fixture_PASS')),'exact public-only219context required')
    require(all(os.environ.get(k)==v for k,v in {'GITHUB_SHA':head,'GITHUB_WORKFLOW_SHA':head,'GITHUB_REPOSITORY':'eirblue/ios_note10p',
        'GITHUB_JOB':JOB,'GITHUB_RUN_ATTEMPT':'1'}.items()) and os.environ.get('GITHUB_WORKFLOW_REF','').startswith('eirblue/ios_note10p/'+WORKFLOW+'@'),'fresh source-bound dispatch required')
    out=Path(output).resolve();require(out==ROOT/'note10/private/v219-ci-source-budget','fixed CI output required')
    work=out.with_name(out.name+'-work');archive=out.with_name(out.name+'-source.tar.gz')
    require(not any(x.exists()for x in (out,work,archive)),'fresh producer paths required');out.mkdir(parents=True)
    identity=uuid.uuid4().hex
    result=dict(schema=BUILD_SCHEMA,passed=False,version='v219',producer_revision='v219',source_ingest_revision='v217',hash_revision='v219',accounting_revision='v219',source_head=head,source_sha256=context['source_sha256'],
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
        sizes=target_sizes(p.ordinary(out/'05-symbols.log').decode());p.save(out/'target-sizes.json',dict(schema='note10-v219-target-type-sizes-v1',source_head=head,bytes=sizes,allocator_resident_sizes=False))
        stack=p.ordinary(objects/'arch/arm64/mm/init.su');frames=stack_frames(stack.decode())
        (out/'owner-init.su').write_bytes(stack)
        p.save(out/'stack-frames.json',dict(schema='note10-v219-target-stack-frames-v1',source_head=head,bytes=frames,total_kernel_stack_bound=False))
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
