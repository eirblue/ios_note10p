"""Producer214: MEDIA_SUPPORT=n and a fixed six MiB neutral source slot."""
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
from v130_slot import newc
import v213_native_prepare as retained
import native_footprint_profile as footprint
p,house,archive_helper=retained.p,retained.house,retained.archive_helper
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
WORKFLOW='.github/workflows/note10-v214-native-prepare.yml'
JOB='v214-native-prepare'
BUILD_SCHEMA='note10-v214-media-footprint-build-v1'
CONTEXT_SCHEMA='note10-v214-media-footprint-public-input-v1'
MANIFEST_SCHEMA='note10-v214-media-footprint-sealed-members-v1'
FIXTURE_SCHEMA='note10-v214-media-footprint-fixture-result-v1'
FALSE_CLAIMS=retained.FALSE_CLAIMS
PID1_CAP=retained.PID1_CAP
SLOT_BYTES=footprint.SLOT_BYTES
METADATA_BYTES=footprint.METADATA_BYTES
fit=footprint.fit
BASELINE212_IMAGE_BYTES=46284812
BASELINE212_LINKED_BYTES=55005184
BASELINE208_IMAGE_BYTES=46282764
BASELINE208_LINKED_BYTES=55001088
PUBLIC_NEW=('native_footprint_profile.py','test_native_footprint_profile.py','v214_native_prepare.py')
SUCCESS_MEMBERS=retained.SUCCESS_MEMBERS
private_member,install=retained.private_member,retained.install
RETAINED211_PARSER_PASS=retained.RETAINED211_PARSER_PASS
inspect_pid1=retained.inspect_pid1
require,sha=retained.require,retained.sha
RETAINED212_PASS={'schema': 'note10-v212-native-prepare-fixture-result-v1', 'passed': True, 'groups': 5, 'variants': 16, 'assertions': 48, 'source_head': '3f67fdf066401a3e22780e7ea25971485afe7a61', 'result_sha256': '80735f2b81f05d7d1daff0a3cd2c9eaae874bf4c45c42e2a8961ac71a625079e'}
FROZEN213_MAP_SHA256='f4551cf3988ded335c0f02eb4a4647845d39b49aca42370d39fa6e34db527367'


def source_pins():
    pins=retained.source_pins()
    require(sha(json.dumps(pins,sort_keys=True,separators=(',',':')).encode())==FROZEN213_MAP_SHA256,'immutable213 source map changed')
    pins.update({'note10/device_test/'+name:sha(p.ordinary(HERE/name)) for name in PUBLIC_NEW})
    pins[WORKFLOW]=sha(p.ordinary(ROOT/WORKFLOW));return pins

def validate_fixture(passed):
    require(type(passed)is dict and set(passed)=={'schema','passed','groups','variants','assertions','result_sha256'} and
            passed['schema']==FIXTURE_SCHEMA and passed['passed']is True and passed['groups']==2 and
            passed['variants']==4 and passed['assertions']==5,'exact synthetic-only source-member PASS required')
    p.hexid(passed['result_sha256'])

def public_context(head,passed):
    validate_fixture(passed);p.hexid(head,40)
    return dict(schema=CONTEXT_SCHEMA,source_head=head,source_sha256=source_pins(),new_fixture_PASS=passed,
                retained213_serializer_PASS={'schema': 'note10-v213-source-member-fixture-result-v1', 'passed': True, 'groups': 4, 'variants': 8, 'assertions': 22, 'source_head': 'c06b9e8e28f8953be7bfec42153596753db3694e', 'result_sha256': '273d006f8dbb14ab62e0a7eb1185fe37aa4c8a554009d878a5d5da5e5c054cdb'},
                retained212_PID1_PASS=RETAINED212_PASS)

def generic(init):
    retained.require(64<=len(init)<=PID1_CAP and init[:6]==b'\x7fELF\x02\x01' and init[18:20]==b'\xb7\0' and
                     init.count(b'N10MININIT2:N212PREP')==1,'unchanged compact static PID1 required')
    prefix=newc([('dev',0o040755,b'',0,0),('sys',0o040755,b'',0,0),('n10',0o040700,b'',0,0),
                 ('dev/console',0o020600,b'',5,1),('dev/kmsg',0o020600,b'',1,11),('init',0o100755,init,0,0)])
    prefix+=bytes(-len(prefix)%512)
    return prefix+bytes(SLOT_BYTES),len(prefix)

def insert(image,build,member,metadata,cycle):
    p.hexid(cycle,32)
    start,size,marker=(build[k] for k in ('slot_offset','slot_bytes','cycle_offset'))
    require(type(start)is type(size)is type(marker)is int and size==SLOT_BYTES and 64<=start<=len(image)-size and
            64<=marker and marker+33<=len(image) and not(start<=marker<start+size) and
            image[marker:marker+33]==p.CYCLE_MARKER+b'\0' and image.count(p.CYCLE_MARKER+b'\0')==1 and
            not any(image[start:start+size]) and type(member)is bytes and member.startswith(b'\x1f\x8b\x08\x00') and
            fit(len(member))['fit']is True and type(metadata)is bytes and 0<len(metadata)<=METADATA_BYTES and metadata.startswith(b'070701'),
            'exact disabled6MiB source-built slot/member/metadata required')
    combined=member+bytes(-len(member)%4)+metadata
    require(len(combined)<=size,'completed member and metadata exceed fixed slot')
    changed=bytearray(image);changed[start:start+size]=combined+bytes(size-len(combined));changed[marker:marker+32]=cycle.encode()
    return bytes(changed),dict(member_bytes=len(member),metadata_bytes=len(metadata),used_slot_bytes=len(combined),zero_tail_bytes=size-len(combined))

def run_build(output,context,head):
    require(sys.platform=='linux' and context==public_context(head,context.get('new_fixture_PASS')),
            'exact213 synthetic context and carried unchanged component PASS required')
    passed=context['new_fixture_PASS']
    validate_fixture(passed)
    p.hexid(passed['result_sha256']);p.hexid(head,40)
    require(all(os.environ.get(k)==v for k,v in {'GITHUB_SHA':head,'GITHUB_WORKFLOW_SHA':head,'GITHUB_REPOSITORY':'eirblue/ios_note10p',
            'GITHUB_JOB':JOB,'GITHUB_RUN_ATTEMPT':'1'}.items()) and os.environ.get('GITHUB_WORKFLOW_REF','').startswith('eirblue/ios_note10p/'+WORKFLOW+'@'),'exact fresh CI dispatch required')
    out=Path(output).resolve();require(out==ROOT/'note10/private/v214-ci-native-prepare','fixed CI output required')
    work=out.with_name(out.name+'-work');archive=out.with_name(out.name+'-source.tar.gz')
    require(not any(x.exists() for x in (out,work,archive)),'fresh one-use producer required')
    out.mkdir(parents=True);identity=uuid.uuid4().hex
    result=dict(schema=BUILD_SCHEMA,version='v214',producer_revision='v214',consumer_revision='v210',PID1_revision='v212',passed=False,source_head=head,
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
        for name in ('clang-14','gcc','make','aarch64-linux-gnu-gcc','arm-linux-gnueabi-gcc','aarch64-linux-gnu-nm'):require(shutil.which(name)is not None,'required tool absent: '+name)
        archive_helper.acquire(archive)
        with archive.open('rb') as stream:archive_sha=hashlib.file_digest(stream,'sha256').hexdigest()
        require(archive.stat().st_size==p.ARCHIVE_BYTES and archive_sha==p.ARCHIVE_SHA,'exact stock source archive required')
        work.mkdir();source=archive_helper.extract(archive,work/'source');objects=work/'objects';objects.mkdir()
        result['stock_config_boundary_sha256']={}
        for name,expected in footprint.STOCK_GUARDS.items():
            original=p.ordinary(source/name);footprint.guard_source(original,expected);result['stock_config_boundary_sha256'][name]=sha(original)
        buffers={name:p.ordinary(ROOT/name) for name in context['source_sha256']}
        result['preparation']=install(source,identity,buffers,RETAINED211_PARSER_PASS['parser_source_sha256']);persist()
        compile_sources=[HERE/n for n in ('v212_native_prepare_pid1.c','native_prepare_core.c','native_parcel_core.c')]
        result['target_PID1_compile_links']=1;persist()
        run(['aarch64-linux-gnu-gcc','-std=c11','-Os','-ffreestanding','-fno-builtin','-fno-tree-loop-distribute-patterns','-fno-stack-protector',
             '-fno-pie','-no-pie','-nostdlib','-nodefaultlibs','-static','-Wl,-e,_start','-Wl,--build-id=none','-Wl,-z,max-page-size=4096',
             '-Wall','-Wextra','-Werror','-I',HERE,'-DN212_BUILD_ID="'+identity+'"',*compile_sources,'-o',out/'minimal-init.elf'],'01-pid1')
        run(['aarch64-linux-gnu-nm','--format=posix',out/'minimal-init.elf'],'01-pid1-symbols')
        init=p.ordinary(out/'minimal-init.elf',PID1_CAP);result['PID1_linkage']=inspect_pid1(init,p.ordinary(out/'01-pid1-symbols.log').decode())
        cpio,prefix=generic(init);(out/'initramfs.cpio').write_bytes(cpio)
        make=['make','-C',str(source),'O='+str(objects),'ARCH=arm64','CC=clang-14','CROSS_COMPILE=aarch64-linux-gnu-',
              'CLANG_TRIPLE=aarch64-linux-gnu-','CROSS_COMPILE_ARM32=arm-linux-gnueabi-','GCC_TOOLCHAIN_DIR=/usr/aarch64-linux-gnu/bin/',
              'HOSTCC=gcc','HOSTCFLAGS=-Wno-error=deprecated-declarations','KCFLAGS=-gdwarf-4']
        run([*make,p.DEFCONFIG],'02-defconfig')
        baseline=house.config_values(p.ordinary(objects/'.config'))
        require(baseline.get('NOTE10_V210_NATIVE_PREPARE','n')=='n','new profile must be default off')
        settings=dict(house.SETTINGS,NOTE10_V210_NATIVE_PREPARE='y',KEXEC='n',KEXEC_FILE='n',CRYPTO_SHA256='y',
                      CRYPTO_USER_API_HASH='y',INITRAMFS_SOURCE='"'+str(out/'initramfs.cpio')+'"',LOCALVERSION='"-v214-media-free-source-slot"',**footprint.SETTINGS)
        edits=[]
        for key,value in settings.items():edits.extend(['--enable' if value=='y' else '--disable',key] if value in ('y','n') else ['--set-str',key,value[1:-1]] if value.startswith('"') else ['--set-val',key,value])
        run([source/'scripts/config','--file',objects/'.config',*edits],'03-settings');run([*make,'olddefconfig'],'04-config')
        config=p.ordinary(objects/'.config');values=house.config_values(config)
        for key,value in dict(p.REQUIRED_CONFIG,**settings).items():require(values.get(key,'n')==value,'effective setting differs: '+key)
        require(not any(key.startswith('NOTE10_') and value!='n' and key not in settings for key,value in values.items()),'unselected profile forbidden')
        result['profile_guard']=footprint.effective(values,dict(p.REQUIRED_CONFIG,**settings))
        result['stock_effective_config_sha256']=sha(json.dumps(baseline,sort_keys=True,separators=(',',':')).encode())
        result['effective_delta_from_stock']={k:dict(before=baseline.get(k,'n'),after=values.get(k,'n')) for k in sorted(set(baseline)|set(values)) if baseline.get(k,'n')!=values.get(k,'n')}
        (out/'actual-effective.config').write_bytes(config);result['effective_profile']=values
        result['cmdline_policy']=sys.modules['builtin_init_route'].builtin_cmdline_policy(config.decode())
        result['full_Image_build_attempts']=1;persist();run([*make,'V=1','-j4','Image'],'05-Image',5400)
        raw=p.ordinary(objects/'arch/arm64/boot/Image',p.IMAGE_LIMIT);symbols=p.ordinary(objects/'System.map',16777216).decode()
        result.update(house.check_image(raw,cpio,identity,symbols,b'N212PREP'))
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
        require(min(result['kernel_linked_reduction_vs212_bytes'],result['kernel_end_reduction_vs212_bytes'])>=1523712,'actual sufficient kernel reduction required')
        result['slot_offset']=result['initramfs_offset']+prefix;result['slot_bytes']=SLOT_BYTES
        require(not any(raw[result['slot_offset']:result['slot_offset']+SLOT_BYTES]),'generic private slot must stay zero')
        result['object_evidence']={}
        for name in ('arch/arm64/mm/init.o','drivers/misc/v154_linux_return.o','init/initramfs.o'):
            obj=p.ordinary(objects/name,67108864);cmdpath=Path(name).with_name('.'+Path(name).name+'.cmd');cmd=p.ordinary(objects/cmdpath)
            require(b'clang-14' in cmd and b'-DMODULE' not in cmd,'same Image builtin command required')
            result['object_evidence'][name]=dict(object_sha256=sha(obj),object_bytes=len(obj),command_sha256=sha(cmd))
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
    context=json.loads(base64.b64decode(args.passed_new_test_context,validate=True));require(len(json.dumps(context))<=65536,'bounded public context required')
    try:run_build(args.output,context,args.expected_source_head)
    finally:
        if args.output.is_dir():seal(args.output,args.expected_source_head)

if __name__=='__main__':main()
