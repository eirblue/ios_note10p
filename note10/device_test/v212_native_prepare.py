"""Freestanding prepare PID1 producer212; kernel consumer210/parser211 unchanged."""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import uuid
import zipfile
from v130_slot import newc
import v211_native_prepare as retained
p,house,archive_helper=retained.p,retained.house,retained.archive_helper
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
WORKFLOW='.github/workflows/note10-v212-native-prepare.yml'
JOB='v212-native-prepare'
BUILD_SCHEMA='note10-v212-native-prepare-build-v1'
CONTEXT_SCHEMA='note10-v212-native-prepare-public-input-v1'
MANIFEST_SCHEMA='note10-v212-native-prepare-sealed-members-v1'
FALSE_CLAIMS=retained.FALSE_CLAIMS
SLOT_BYTES=retained.SLOT_BYTES
PID1_CAP=65536
BASELINE211_IMAGE_BYTES=47005708
BASELINE211_LINKED_BYTES=55726080
BASELINE211_PID1_BYTES=721160
PUBLIC_NEW=('v212_native_prepare_pid1.c','test_v212_native_prepare_pid1.py','v212_native_prepare.py')
SUCCESS_MEMBERS=(*retained.SUCCESS_MEMBERS,'01-pid1-symbols.log')
private_member,insert,install=retained.private_member,retained.insert,retained.install
RETAINED210_CORE_PASS=retained.RETAINED210_CORE_PASS
FROZEN211_MAP_SHA256='556a2713532bfa6d7726167ea1b1970d21b084949849e57d40c2c3980bd04914'
RETAINED211_PARSER_PASS={'schema': 'note10-v211-stock-parser-fixture-result-v1', 'passed': True, 'groups': 1, 'variants': 2, 'assertions': 3, 'source_head': '3db30eb83ec3a640c6e66f09a13605ffe1e1bf9c', 'stock_sha256': '1a9af19668584dc664c28c640e02b6a03cc37a2fa5ecd1900d818bb67c775806', 'parser_source_sha256': '74b255a5ebed762e837d51e3ec2db77cc31b1904388165c49a3892e4ed77f7df', 'result_sha256': 'c73071b7e329eeb49b426605ded5c72bee4e233455a78deb599a68e506dab4f1'}


def require(ok,message):
    if not ok:raise ValueError(message)


def sha(raw):return hashlib.sha256(raw).hexdigest()


def source_pins():
    pins=retained.source_pins()
    require(sha(json.dumps(pins,sort_keys=True,separators=(',',':')).encode())==FROZEN211_MAP_SHA256,'immutable211 source map changed')
    pins.update({'note10/device_test/'+name:sha(p.ordinary(HERE/name)) for name in PUBLIC_NEW})
    pins[WORKFLOW]=sha(p.ordinary(ROOT/WORKFLOW));return pins


def inspect_pid1(raw,symbols):
    require(type(raw)is bytes and 64<=len(raw)<=PID1_CAP and raw[:7]==b'\x7fELF\x02\x01\x01' and
            struct.unpack_from('<HHI',raw,16)==(2,183,1),'bounded static ARM64 ELF required')
    entry,phoff=struct.unpack_from('<QQ',raw,24);ehsize,phsize,count=struct.unpack_from('<HHH',raw,52)
    require((ehsize,phsize)==(64,56) and 1<=count<=16 and phoff+count*phsize<=len(raw),'bounded ELF program headers')
    loads=[];entry_offsets=[];alignments=[]
    for index in range(count):
        kind,flags,offset,va,_,file_bytes,memory_bytes,alignment=struct.unpack_from('<II6Q',raw,phoff+index*phsize)
        require(kind not in (2,3),'PT_DYNAMIC/PT_INTERP forbidden')
        if kind!=1:continue
        require(flags in (4,5,6) and 0<memory_bytes and file_bytes<=memory_bytes and offset+file_bytes<=len(raw) and
                va+memory_bytes<1<<64 and alignment in (1,2,4,8,16,32,64,128,256,512,1024,2048,4096) and
                offset%alignment==va%alignment and not any(low<va+memory_bytes and va<high for low,high in loads),'bounded disjoint ELF loads')
        loads.append((va,va+memory_bytes));alignments.append(alignment)
        if flags&1 and va<=entry and entry+4<=va+file_bytes:entry_offsets.append(offset+entry-va)
    require(loads and entry%4==0 and len(entry_offsets)==1,'unique executable file-backed entry')
    mapped=((max(high for _,high in loads)+4095)//4096*4096)-(min(low for low,_ in loads)//4096*4096)
    require(0<mapped<=PID1_CAP and raw.count(b'N10MININIT2:N212PREP')==1,'bounded mapped PID1/identity required')
    rows=[line.split() for line in symbols.splitlines() if line.strip()]
    require(rows and all(len(row)>=2 and row[1] not in ('U','u','w','v') for row in rows),'runtime undefined imports forbidden')
    required=('_start','n212_start','memcpy','memset','n210_request_valid','n210_receipt_matches')
    for name in required:require(len([row for row in rows if row[0]==name and row[1] in ('T','t')])==1,'one defined production symbol required: '+name)
    start=next(row for row in rows if row[0]=='_start')
    require(len(start)>=3 and int(start[2],16)==entry,'_start symbol/entry differ')
    return dict(schema='note10-v212-freestanding-PID1-linkage-v1',passed=True,ELF_bytes=len(raw),ELF_sha256=sha(raw),entry=entry,
                entry_file_offset=entry_offsets[0],mapped_memory_bytes=sum(high-low for low,high in loads),mapped_span_bytes=mapped,
                max_load_alignment=max(alignments),load_alignment_cap=4096,undefined_symbols=[],defined_required=list(required),default_runtime_libraries=False,
                PT_INTERP=False,PT_DYNAMIC=False,PID1_revision='v212')


def generic(init):
    require(64<=len(init)<=PID1_CAP and init[:6]==b'\x7fELF\x02\x01' and init[18:20]==b'\xb7\0' and
            init.count(b'N10MININIT2:N212PREP')==1,'new compact static PID1 required')
    prefix=newc([('dev',0o040755,b'',0,0),('sys',0o040755,b'',0,0),('n10',0o040700,b'',0,0),
                 ('dev/console',0o020600,b'',5,1),('dev/kmsg',0o020600,b'',1,11),('init',0o100755,init,0,0)])
    prefix+=bytes(-len(prefix)%512)
    return prefix+bytes(SLOT_BYTES),len(prefix)


def run_build(output,context,head):
    require(sys.platform=='linux' and context==dict(schema=CONTEXT_SCHEMA,source_head=head,source_sha256=source_pins(),new_fixture_PASS=context.get('new_fixture_PASS'),retained210_core_PASS=RETAINED210_CORE_PASS,retained211_parser_PASS=RETAINED211_PARSER_PASS),
            'exact new211 context and carried unchanged210 core PASS required')
    passed=context['new_fixture_PASS']
    require(set(passed)=={'schema','passed','groups','variants','assertions','result_sha256'} and passed['schema']=='note10-v212-native-prepare-fixture-result-v1' and
            passed['passed']is True and passed['groups']==5 and passed['variants']==16 and passed['assertions']==48,'new freestanding adapter fixture PASS required')
    p.hexid(passed['result_sha256']);p.hexid(head,40)
    require(all(os.environ.get(k)==v for k,v in {'GITHUB_SHA':head,'GITHUB_WORKFLOW_SHA':head,'GITHUB_REPOSITORY':'eirblue/ios_note10p',
            'GITHUB_JOB':JOB,'GITHUB_RUN_ATTEMPT':'1'}.items()) and os.environ.get('GITHUB_WORKFLOW_REF','').startswith('eirblue/ios_note10p/'+WORKFLOW+'@'),'exact fresh CI dispatch required')
    out=Path(output).resolve();require(out==ROOT/'note10/private/v212-ci-native-prepare','fixed CI output required')
    work=out.with_name(out.name+'-work');archive=out.with_name(out.name+'-source.tar.gz')
    require(not any(x.exists() for x in (out,work,archive)),'fresh one-use producer required')
    out.mkdir(parents=True);identity=uuid.uuid4().hex
    result=dict(schema=BUILD_SCHEMA,version='v212',producer_revision='v212',consumer_revision='v210',PID1_revision='v212',passed=False,source_head=head,
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
                      CRYPTO_USER_API_HASH='y',INITRAMFS_SOURCE='"'+str(out/'initramfs.cpio')+'"',LOCALVERSION='"-v212-native-prepare"')
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
        result.update(house.check_image(raw,cpio,identity,symbols,b'N212PREP'))
        table={row[2]:int(row[0],16) for line in symbols.splitlines() if len(row:=line.split())==3 and row[2] in ('_text','_end')}
        require(set(table)=={'_text','_end'} and 0<table['_end']-table['_text']<=p.IMAGE_LIMIT,'measured linked extent cap')
        result['linked_end_minus_text']=table['_end']-table['_text']
        require(result['Image_bytes']<BASELINE211_IMAGE_BYTES and result['linked_extent']<BASELINE211_LINKED_BYTES and
                result['linked_end_minus_text']<BASELINE211_LINKED_BYTES,'actual Image and linked footprint must decrease')
        result['Image_reduction_vs211_bytes']=BASELINE211_IMAGE_BYTES-result['Image_bytes']
        result['linked_reduction_vs211_bytes']=BASELINE211_LINKED_BYTES-result['linked_extent']
        result['PID1_reduction_vs211_bytes']=BASELINE211_PID1_BYTES-len(init)
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
