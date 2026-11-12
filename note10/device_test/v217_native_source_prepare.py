"""New217source-owner TU only; no fullImage, PID1 link or runtime caller."""
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
import v216_native_prepare as retained
import v215_native_prepare as prepared
from native_source_accounting import SIZE_NAMES
p,house,archive_helper=retained.p,retained.house,retained.archive_helper
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
WORKFLOW='.github/workflows/note10-v217-native-source-owner.yml'
JOB='v217-native-source-owner'
BUILD_SCHEMA='note10-v217-source-owner-object-build-v1'
CONTEXT_SCHEMA='note10-v217-source-owner-public-input-v1'
MANIFEST_SCHEMA='note10-v217-source-owner-sealed-members-v1'
PUBLIC_NEW=('native_source_ingest.h','native_source_ingest.c','v217_source_owner_kernel.c','native_source_ingest_fixture.c',
            'native_source_accounting.py','test_v217_native_source_accounting.py','v217_native_source_prepare.py')
SUCCESS_MEMBERS=('result.json','01-defconfig.log','02-settings.log','03-config.log','actual-effective.config',
                 '04-owner-object.log','owner-init.o','owner-init.cmd','05-symbols.log','target-sizes.json','members.json')
require,sha=retained.require,retained.sha
FROZEN216_MAP_SHA256='5378e4b5ae83e82ae675bdbf149251f1a41e62213c9fd6ee404c69382036dbe4'


def source_pins():
    pins=retained.source_pins()
    require(sha(json.dumps(pins,sort_keys=True,separators=(',',':')).encode())==FROZEN216_MAP_SHA256,'retained216source map changed')
    pins.update({'note10/device_test/'+name:sha(p.ordinary(HERE/name))for name in PUBLIC_NEW})
    pins[WORKFLOW]=sha(p.ordinary(ROOT/WORKFLOW));return pins


def public_context(head,passed):
    p.hexid(head,40)
    require(type(passed)is dict and set(passed)=={'schema','passed','groups','variants','assertions','result_sha256'} and
            passed['schema']=='note10-v217-source-owner-fixture-result-v1' and passed['passed']is True and
            passed['groups']==10 and passed['variants']==18 and passed['assertions']==37,'new sourceowner/accounting fixture PASS required')
    p.hexid(passed['result_sha256'])
    return dict(schema=CONTEXT_SCHEMA,source_head=head,source_sha256=source_pins(),new_fixture_PASS=passed)


def install(source,identity,buffers):
    result=prepared.install(source,identity,buffers,prepared.RETAINED211_PARSER_PASS['parser_source_sha256'])
    target=source/'arch/arm64/mm/init.c';raw=p.ordinary(target)
    anchor=b'#include "v210_native_prepare_kernel.c"\n#endif\n'
    require(raw.count(anchor)==1,'exact existing210owner TU seam required')
    added=b'#include "native_source_ingest.c"\n#include "v217_source_owner_kernel.c"\n'
    changed=raw.replace(anchor,anchor.replace(b'#endif\n',added+b'#endif\n'),1);target.write_bytes(changed)
    names=('native_source_ingest.h','native_source_ingest.c','v217_source_owner_kernel.c')
    for name in names:(target.parent/name).write_bytes(buffers['note10/device_test/'+name])
    result['source_owner_boundary']=dict(path='arch/arm64/mm/init.c',before_sha256=sha(raw),after_sha256=sha(changed),
        new_sources={name:sha(buffers['note10/device_test/'+name])for name in names},owner_fields_mutated=False,runtime_callers=0)
    return result


def target_sizes(symbols):
    rows=[line.split()for line in symbols.splitlines()if line.strip()]
    result={}
    for name in SIZE_NAMES:
        found=[row for row in rows if row[0]=='n217_size_'+name]
        require(len(found)==1 and len(found[0])==4 and found[0][1]in ('R','r'),'one retained target size symbol required: '+name)
        result[name]=int(found[0][3],16);require(0<result[name]<=1048576,'bounded target sizeof required')
    for name in ('n217_consume','n217_ingest_current'):
        require(len([row for row in rows if row[0]==name and row[1]in ('T','t')])==1,'actual sourceowner body must be compiled: '+name)
    require(result['request']==496 and result['result']==352,'fixed217wire ABI differs')
    return result


def run_build(output,context,head):
    require(sys.platform=='linux' and context==public_context(head,context.get('new_fixture_PASS')),'exact public-only217context required')
    require(all(os.environ.get(k)==v for k,v in {'GITHUB_SHA':head,'GITHUB_WORKFLOW_SHA':head,'GITHUB_REPOSITORY':'eirblue/ios_note10p',
        'GITHUB_JOB':JOB,'GITHUB_RUN_ATTEMPT':'1'}.items()) and os.environ.get('GITHUB_WORKFLOW_REF','').startswith('eirblue/ios_note10p/'+WORKFLOW+'@'),'fresh source-bound dispatch required')
    out=Path(output).resolve();require(out==ROOT/'note10/private/v217-ci-source-owner','fixed CI output required')
    work=out.with_name(out.name+'-work');archive=out.with_name(out.name+'-source.tar.gz')
    require(not any(x.exists()for x in (out,work,archive)),'fresh producer paths required');out.mkdir(parents=True)
    identity=uuid.uuid4().hex
    result=dict(schema=BUILD_SCHEMA,passed=False,version='v217',producer_revision='v217',source_head=head,source_sha256=context['source_sha256'],
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
        buffers={name:p.ordinary(ROOT/name)for name in context['source_sha256']};result['preparation']=install(source,identity,buffers);persist()
        make=['make','-C',str(source),'O='+str(objects),'ARCH=arm64','CC=clang-14','CROSS_COMPILE=aarch64-linux-gnu-',
            'CLANG_TRIPLE=aarch64-linux-gnu-','CROSS_COMPILE_ARM32=arm-linux-gnueabi-','GCC_TOOLCHAIN_DIR=/usr/aarch64-linux-gnu/bin/',
            'HOSTCC=gcc','HOSTCFLAGS=-Wno-error=deprecated-declarations','KCFLAGS=-gdwarf-4']
        run([*make,p.DEFCONFIG],'01-defconfig')
        settings=dict(house.SETTINGS,NOTE10_V210_NATIVE_PREPARE='y',KEXEC='n',KEXEC_FILE='n',CRYPTO_SHA256='y',CRYPTO_USER_API_HASH='y',
            INITRAMFS_SOURCE='""',LOCALVERSION='"-v217-source-owner-object"',**prepared.footprint.SETTINGS)
        edits=[]
        for key,value in settings.items():edits.extend(['--enable'if value=='y'else'--disable',key]if value in ('y','n')else['--set-str',key,value[1:-1]]if value.startswith('"')else['--set-val',key,value])
        run([source/'scripts/config','--file',objects/'.config',*edits],'02-settings');run([*make,'olddefconfig'],'03-config')
        config=p.ordinary(objects/'.config');values=house.config_values(config)
        result['profile_guard']=prepared.footprint.effective(values,dict(p.REQUIRED_CONFIG,**settings));result['effective_profile']=values
        require(values.get('ARM64_4K_PAGES')=='y' and values.get('SLUB')=='y' and values.get('DEFERRED_INITCALLS')=='y','actual accounting configuration required')
        (out/'actual-effective.config').write_bytes(config)
        result['owner_TU_target_attempts']=1;persist();run([*make,'V=1','-j4','arch/arm64/mm/init.o'],'04-owner-object',2400)
        target=objects/'arch/arm64/mm/init.o';command=objects/'arch/arm64/mm/.init.o.cmd'
        obj=p.ordinary(target,67108864);cmd=p.ordinary(command)
        require(b'clang-14'in cmd and b'-DMODULE'not in cmd,'actual builtin owner TU command required')
        (out/'owner-init.o').write_bytes(obj);(out/'owner-init.cmd').write_bytes(cmd)
        run(['aarch64-linux-gnu-nm','--format=posix','--print-size',target],'05-symbols')
        sizes=target_sizes(p.ordinary(out/'05-symbols.log').decode());p.save(out/'target-sizes.json',dict(schema='note10-v217-target-type-sizes-v1',source_head=head,bytes=sizes,allocator_resident_sizes=False))
        require(source_pins()==context['source_sha256'],'source changed during producer')
        result.update(passed=True,target_sizes=sizes,object_bytes=len(obj),object_sha256=sha(obj),command_sha256=sha(cmd),
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
