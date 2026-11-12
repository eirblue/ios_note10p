"""New211 producer: exact stock parser repair; unchanged prepare-only consumer210."""
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
import v210_native_prepare as retained
p,house,archive_helper=retained.p,retained.house,retained.archive_helper
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
WORKFLOW='.github/workflows/note10-v211-native-prepare.yml'
JOB='v211-native-prepare'
BUILD_SCHEMA='note10-v211-native-prepare-build-v1'
CONTEXT_SCHEMA='note10-v211-native-prepare-public-input-v1'
MANIFEST_SCHEMA='note10-v211-native-prepare-sealed-members-v1'
STOCK_SHA='1a9af19668584dc664c28c640e02b6a03cc37a2fa5ecd1900d818bb67c775806'
FALSE_CLAIMS=retained.FALSE_CLAIMS
SLOT_BYTES=retained.SLOT_BYTES
SUCCESS_MEMBERS=retained.SUCCESS_MEMBERS
generic,private_member,insert=retained.generic,retained.private_member,retained.insert
FROZEN210_MAP_SHA256='a0f1ff71c2367c2ba3a43704dde3c72c67bdfb49a9328f2435509ee8a1d317cb'
RETAINED210_CORE_PASS={'schema': 'note10-v210-native-prepare-fixture-result-v1', 'passed': True, 'groups': 6, 'variants': 16, 'assertions': 33, 'source_head': '5efa4cee84873e69cde58a0452d8b0719c7da7c1', 'result_sha256': '6f315fecaf8ff3a857bedfd064ba853528e242dd0ee312cd31e1ba56703296e7'}


def require(ok,message):
    if not ok:raise ValueError(message)


def sha(raw):return hashlib.sha256(raw).hexdigest()


def source_pins():
    pins=retained.source_pins()
    require(sha(json.dumps(pins,sort_keys=True,separators=(',',':')).encode())==FROZEN210_MAP_SHA256,'immutable210 source map changed')
    pins['note10/device_test/v211_native_prepare.py']=sha(p.ordinary(HERE/'v211_native_prepare.py'))
    pins[WORKFLOW]=sha(p.ordinary(ROOT/WORKFLOW))
    return pins


def prepare_rootfs(stock):
    parser=retained.parser_helper.PARSER
    require(type(stock)is bytes and len(stock)==14716 and sha(stock)==STOCK_SHA and stock.count(parser)==1,
            'exact stock rootfs/parser source required')
    assignment=retained.parser_helper.ASSIGNMENT.replace(b'\n',b' && defined(CONFIG_NOTE10_V210_NATIVE_PREPARE)\n',1)
    # Only the selected parser assignment changes; no observer prerequisite.
    replacement=parser.replace(b'\tdo_skip_initramfs = 1;',assignment,1)
    return stock.replace(parser,replacement,1)


def install(source,identity,buffers,rootfs_sha):
    # Install the unchanged stock-Linux driver/return base into a fresh tree only.
    result=p.install(source,identity,buffers)
    target=source/'init/initramfs.c';raw_rootfs=prepare_rootfs(p.ordinary(target))
    require(sha(raw_rootfs)==rootfs_sha,'reviewed new parser postimage differs')
    target.write_bytes(raw_rootfs)
    main=source/'arch/arm64/mm/init.c';raw=p.ordinary(main)
    anchor=b'void __init arm64_memblock_init(void)'
    require(raw.count(anchor)==raw.count(b'\tmemblock_allow_resize();')==1,'exact early memblock anchors required')
    includes=b'\n#ifdef CONFIG_NOTE10_V210_NATIVE_PREPARE\n#include "native_parcel_core.c"\n#include "native_prepare_core.c"\n#include "v210_native_prepare_kernel.c"\n#endif\n'
    raw=raw.replace(anchor,includes+anchor,1).replace(b'\tmemblock_allow_resize();',
        b'#ifdef CONFIG_NOTE10_V210_NATIVE_PREPARE\n    n210_early_reserve();\n#endif\n\tmemblock_allow_resize();',1);main.write_bytes(raw)
    for name in ('native_parcel_core.h','native_parcel_core.c','native_prepare_core.h','native_prepare_core.c','v210_native_prepare_kernel.c'):
        (main.parent/name).write_bytes(buffers['note10/device_test/'+name])
    # Return TU owns these real static identity/arm fields. Read-only accessor.
    target=source/'drivers/misc/v154_linux_return.c'
    target.write_bytes(p.ordinary(target)+b'\n#include "native_prepare_core.h"\nint n210_linux_context(struct n210_context *out)\n{\n    memset(out,0,sizeof(*out));\n    memcpy(out->build,N154_BUILD_ID,32);\n    memcpy(out->boot,n10_boot_id,32);\n    memcpy(out->cycle,(const void *)n10_cycle,32);\n    out->return_armed=READ_ONCE(n154_arm_result)==0;\n    return out->return_armed?0:-EAGAIN;\n}\n')
    for name in ('native_prepare_core.h','native_parcel_core.h'):(target.parent/name).write_bytes(buffers['note10/device_test/'+name])
    kconfig=source/'drivers/misc/Kconfig'
    kconfig.write_bytes(p.ordinary(kconfig)+b'\nconfig NOTE10_V210_NATIVE_PREPARE\n\tbool "Native descriptor preparation only"\n\tdepends on NOTE10_V154_LINUX_DIAGNOSTIC\n\tdefault n\n')
    result['new_overlay_paths']=['arch/arm64/mm/'+n for n in ('init.c','native_parcel_core.h','native_parcel_core.c','native_prepare_core.h','native_prepare_core.c','v210_native_prepare_kernel.c')]+['init/initramfs.c','drivers/misc/v154_linux_return.c','drivers/misc/native_prepare_core.h','drivers/misc/native_parcel_core.h','drivers/misc/Kconfig']
    result['new_overlay_sha256']={name:sha(p.ordinary(source/name)) for name in result['new_overlay_paths']}
    return result

def run_build(output,context,head):
    require(sys.platform=='linux' and context==dict(schema=CONTEXT_SCHEMA,source_head=head,source_sha256=source_pins(),new_fixture_PASS=context.get('new_fixture_PASS'),retained210_core_PASS=RETAINED210_CORE_PASS),
            'exact new211 context and carried unchanged210 core PASS required')
    passed=context['new_fixture_PASS']
    require(set(passed)=={'schema','passed','groups','variants','assertions','result_sha256','stock_sha256','parser_source_sha256'} and passed['schema']=='note10-v211-stock-parser-fixture-result-v1' and
            passed['passed']is True and passed['groups']==1 and passed['variants']==2 and passed['assertions']==3 and passed['stock_sha256']==STOCK_SHA,'new stock parser fixture PASS required')
    p.hexid(passed['parser_source_sha256'])
    p.hexid(passed['result_sha256']);p.hexid(head,40)
    require(all(os.environ.get(k)==v for k,v in {'GITHUB_SHA':head,'GITHUB_WORKFLOW_SHA':head,'GITHUB_REPOSITORY':'eirblue/ios_note10p',
            'GITHUB_JOB':JOB,'GITHUB_RUN_ATTEMPT':'1'}.items()) and os.environ.get('GITHUB_WORKFLOW_REF','').startswith('eirblue/ios_note10p/'+WORKFLOW+'@'),'exact fresh CI dispatch required')
    out=Path(output).resolve();require(out==ROOT/'note10/private/v211-ci-native-prepare','fixed CI output required')
    work=out.with_name(out.name+'-work');archive=out.with_name(out.name+'-source.tar.gz')
    require(not any(x.exists() for x in (out,work,archive)),'fresh one-use producer required')
    out.mkdir(parents=True);identity=uuid.uuid4().hex
    result=dict(schema=BUILD_SCHEMA,version='v211',producer_revision='v211',consumer_revision='v210',passed=False,source_head=head,
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
        for name in ('clang-14','gcc','make','aarch64-linux-gnu-gcc','arm-linux-gnueabi-gcc'):require(shutil.which(name)is not None,'required tool absent: '+name)
        archive_helper.acquire(archive)
        with archive.open('rb') as stream:archive_sha=hashlib.file_digest(stream,'sha256').hexdigest()
        require(archive.stat().st_size==p.ARCHIVE_BYTES and archive_sha==p.ARCHIVE_SHA,'exact stock source archive required')
        work.mkdir();source=archive_helper.extract(archive,work/'source');objects=work/'objects';objects.mkdir()
        buffers={name:p.ordinary(ROOT/name) for name in context['source_sha256']}
        result['preparation']=install(source,identity,buffers,passed['parser_source_sha256']);persist()
        compile_sources=[HERE/n for n in ('v210_native_prepare_pid1.c','native_prepare_core.c','native_parcel_core.c')]
        result['target_PID1_compile_links']=1;persist()
        run(['aarch64-linux-gnu-gcc','-std=c11','-Os','-static','-fno-stack-protector','-Wall','-Wextra','-Werror',
             '-I',HERE,'-DN154_BUILD_ID="'+identity+'"',*compile_sources,'-o',out/'minimal-init.elf'],'01-pid1')
        init=p.ordinary(out/'minimal-init.elf',2097152);cpio,prefix=generic(init);(out/'initramfs.cpio').write_bytes(cpio)
        make=['make','-C',str(source),'O='+str(objects),'ARCH=arm64','CC=clang-14','CROSS_COMPILE=aarch64-linux-gnu-',
              'CLANG_TRIPLE=aarch64-linux-gnu-','CROSS_COMPILE_ARM32=arm-linux-gnueabi-','GCC_TOOLCHAIN_DIR=/usr/aarch64-linux-gnu/bin/',
              'HOSTCC=gcc','HOSTCFLAGS=-Wno-error=deprecated-declarations','KCFLAGS=-gdwarf-4']
        run([*make,p.DEFCONFIG],'02-defconfig')
        baseline=house.config_values(p.ordinary(objects/'.config'))
        require(baseline.get('NOTE10_V210_NATIVE_PREPARE','n')=='n','new profile must be default off')
        settings=dict(house.SETTINGS,NOTE10_V210_NATIVE_PREPARE='y',KEXEC='n',KEXEC_FILE='n',CRYPTO_SHA256='y',
                      CRYPTO_USER_API_HASH='y',INITRAMFS_SOURCE='"'+str(out/'initramfs.cpio')+'"',LOCALVERSION='"-v211-native-prepare"')
        edits=[]
        for key,value in settings.items():edits.extend(['--enable' if value=='y' else '--disable',key] if value in ('y','n') else ['--set-str',key,value[1:-1]] if value.startswith('"') else ['--set-val',key,value])
        run([source/'scripts/config','--file',objects/'.config',*edits],'03-settings');run([*make,'olddefconfig'],'04-config')
        config=p.ordinary(objects/'.config');values=house.config_values(config)
        for key,value in dict(p.REQUIRED_CONFIG,**settings).items():require(values.get(key,'n')==value,'effective setting differs: '+key)
        require(not any(key.startswith('NOTE10_') and value!='n' and key not in settings for key,value in values.items()),'unselected profile forbidden')
        (out/'actual-effective.config').write_bytes(config);result['effective_profile']=values
        result['cmdline_policy']=sys.modules['builtin_init_route'].builtin_cmdline_policy(config.decode())
        result['full_Image_build_attempts']=1;persist();run([*make,'V=1','-j4','Image'],'05-Image',5400)
        raw=p.ordinary(objects/'arch/arm64/boot/Image',p.IMAGE_LIMIT);symbols=p.ordinary(objects/'System.map',16777216).decode()
        result.update(house.check_image(raw,cpio,identity,symbols,b'N210PREP'))
        table={row[2]:int(row[0],16) for line in symbols.splitlines() if len(row:=line.split())==3 and row[2] in ('_text','_end')}
        require(set(table)=={'_text','_end'} and 0<table['_end']-table['_text']<=p.IMAGE_LIMIT,'measured linked extent cap')
        result['linked_end_minus_text']=table['_end']-table['_text']
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
