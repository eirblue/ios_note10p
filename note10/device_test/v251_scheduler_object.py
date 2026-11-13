"""Scheduler object-only provenance; never builds an Image or a PID1."""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import shlex
import signal
import struct
import subprocess
import sys
from threading import Thread
import zipfile
import v130_archive as archive

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
NAMES=('preempt_schedule','preempt_schedule_common')
SCHEMA='note10-v251-scheduler-object'
WORKFLOW='.github/workflows/note10-v251-scheduler-object.yml'
PUBLIC_FILES=('note10/device_test/v251_scheduler_object.py','note10/device_test/test_v251_scheduler_object.py','note10/device_test/v251_scheduler_effective.config',WORKFLOW,'note10/device_test/v130_archive.py','note10/device_test/sealed_affinity_artifact.cjs')
MEMBERS={'result.json','members.json','core.o','core.cmd','core.su','core.elf.txt','preempt_schedule.asm','preempt_schedule_common.asm','effective.config','tools.json','build.log','core.c','OBJECT-MAKE-STARTED.json'}
CONFIG_SHA='92d9af76be2360423bfc60e729bae00d31f086d7ceae2904d7a85ad302180a2c'
CORE_SHA='45825d25fc67dbacbcacba84d3e5ca86c486da7a88143624edb57746d79cffdd'
SOURCE_GUARDS={'kernel/sched/core.c': '45825d25fc67dbacbcacba84d3e5ca86c486da7a88143624edb57746d79cffdd', 'kernel/sched/Makefile': '782cc7e23a2d9ab260e476d4db64a91be0486a31985c0ef1c6bc566b4024dfe1', 'arch/arm64/kernel/vmlinux.lds.S': '7d1e35dbdd36858f29794c16efcc197ba7950e8cf265277288c66d155062baec', 'arch/arm64/boot/Makefile': '5393fe51861fb4cb12e56049cec668246218e5351c4af205a16bdaccf8f8e9a5'}
KCONFIG=b'''\nconfig NOTE10_V154_LINUX_DIAGNOSTIC
\tbool "Bounded Linux IVA mmap denial diagnostic"
\tdepends on ARM64 && EXYNOS_IVA && INITRAMFS_FORCE
\tdefault n

config NOTE10_BUILTIN_INIT_ROUTE
\tbool
\tdefault y if NOTE10_V154_LINUX_DIAGNOSTIC

config NOTE10_V210_NATIVE_PREPARE
\tbool "Native descriptor preparation only"
\tdepends on NOTE10_V154_LINUX_DIAGNOSTIC
\tdefault n
'''


def require(ok,message):
    if not ok:raise ValueError(message)


def sha(raw):return hashlib.sha256(raw).hexdigest()


def save(path,row):
    with Path(path).open('xb')as stream:stream.write((json.dumps(row,indent=2,sort_keys=True)+'\n').encode())


def bounded(path,cap=33554432):
    p=Path(path);require(p.is_file()and not p.is_symlink()and 0<p.stat().st_size<=cap,'bounded ordinary file required');return p.read_bytes()


def sources():return {name:sha(bounded(ROOT/name))for name in PUBLIC_FILES}


def public_context(head,fixture,result_sha256):
    require(re.fullmatch('[0-9a-f]{40}',head)and re.fullmatch('[0-9a-f]{64}',result_sha256),'new source/result identifiers')
    summary={k:fixture[k]for k in ('passed','groups','variants','assertions')};summary['result_sha256']=result_sha256
    require(summary['passed']is True and (summary['groups'],summary['variants'],summary['assertions'])==(1,6,6),'new6 only')
    return dict(schema=SCHEMA+'-public-input-v1',source_head=head,source_sha256=sources(),fixture=summary)


def object_functions(raw):
    require(raw[:6]==b'\x7fELF\x02\x01'and struct.unpack_from('<HH',raw,16)==(1,183),'AArch64 ELF64 little-endian object required')
    offset=struct.unpack_from('<Q',raw,40)[0];ents,count,names=struct.unpack_from('<HHH',raw,58)
    require(ents==64 and 0<count<=4096 and names<count and offset+count*64<=len(raw),'bounded ELF section table')
    sections=[struct.unpack_from('<IIQQQQIIQQ',raw,offset+i*64)for i in range(count)]
    def data(index):
        row=sections[index];require(row[1]!=8 and row[4]+row[5]<=len(raw),'ELF section extent');return raw[row[4]:row[4]+row[5]]
    def string(raw,offset):
        require(0<=offset<len(raw)and b'\0'in raw[offset:],'ELF string bound');return raw[offset:raw.index(b'\0',offset)].decode()
    tables=[i for i,s in enumerate(sections)if s[1]==2];require(len(tables)==1,'one static symbol table');table=tables[0];symsec=sections[table]
    require(symsec[9]==24 and symsec[5]%24==0 and symsec[6]<count,'ELF symbol entries');strings=data(symsec[6]);symbols=[]
    symbol_data=data(table)
    for position in range(0,len(symbol_data),24):
        name,info,other,index,value,size=struct.unpack_from('<IBBHQQ',symbol_data,position);symbols.append(dict(name=string(strings,name),type=info&15,binding=info>>4,section=index,value=value,bytes=size))
    result={}
    for name in NAMES:
        matches=[(i,s)for i,s in enumerate(symbols)if s['name']==name and s['type']==2];require(len(matches)==1,'one actual scheduler FUNC')
        _,symbol=matches[0];section=symbol['section'];start,size=symbol['value'],symbol['bytes'];require(0<section<count and sections[section][1]==1 and 0<size<=8192 and start%4==size%4==0 and start+size<=len(data(section)),'selected actual function extent')
        relocs=[]
        for index,s in enumerate(sections):
            require(not(s[1]==9 and s[7]==section),'REL without explicit addend unsupported')
            if s[1]!=4 or s[7]!=section:continue
            require(s[6]==table and s[9]==24 and s[5]%24==0,'selected RELA table')
            relocation_data=data(index)
            for position in range(0,len(relocation_data),24):
                place,info,addend=struct.unpack_from('<QQq',relocation_data,position)
                if not start<=place<start+size:continue
                require(info>>32<len(symbols)and place%4==0,'bounded relocation');target=dict(symbols[info>>32])
                if target['type']==3:
                    candidates=[x for x in symbols if x['type']==2 and x['section']==target['section']and x['value']==target['value']+addend]
                    require(len(candidates)==1,'one section-relative target FUNC');target=dict(candidates[0]);addend=0
                relocs.append(dict(offset=place-start,type=info&0xffffffff,target=target,addend=addend))
        section_name=string(data(names),sections[section][0]);require(section_name=='.sched.text','actual scheduler input section required')
        result[name]=dict(**symbol,section_name=section_name,data=data(section)[start:start+size].hex(),relocations=relocs)
    require(result[NAMES[0]]['section']==result[NAMES[1]]['section'],'same actual scheduler input section required');return result


def nm_records(text):
    result=[]
    for ordinal,line in enumerate(text.splitlines()):
        row=line.split()
        if len(row)==4 and row[1]in ('T','t','W','w'):result.append(dict(name=row[0],kind=row[1],address=int(row[2],16),bytes=int(row[3],16),ordinal=ordinal))
    return result


def join_function(function,original,record,all_records,delta,frame):
    require(frame['kind']=='static'and type(frame['bytes'])is int and 0<=frame['bytes']<=8192,'static actual SU required')
    require(record in all_records and sum(r['name']==record['name']for r in all_records)==1 and function['name']==record['name']and function['bytes']==record['bytes']==len(original)and function['value']+delta==record['address'],'exact original nm extent/ordinal and object join')
    raw=bytearray.fromhex(function['data']);require(len(raw)==len(original),'whole function bytes required');seen=set();edges=[]
    for relocation in function['relocations']:
        position=relocation['offset'];target=relocation['target'];kind=relocation['type']
        require(kind in (282,283)and position not in seen and position%4==0 and 0<=position<=len(raw)-4,'only unique CALL26/JUMP26 supported');seen.add(position)
        require(target['type']==2 and target['section']==function['section']and relocation['addend']==0,'same-input-section exact function entry required')
        address=target['value']+delta;matches=[r for r in all_records if r['address']==address and r['bytes']==target['bytes']and r['name']==target['name']]
        require(len(matches)==1,'source-bound relocation target original nm join')
        word=struct.unpack_from('<I',raw,position)[0];opcode=0x94000000 if kind==283 else 0x14000000
        require(word&0xfc000000==opcode,'relocation branch opcode');distance=address-(record['address']+position);require(distance%4==0 and -(1<<27)<=distance<(1<<27),'branch displacement extent')
        struct.pack_into('<I',raw,position,opcode|((distance>>2)&0x03ffffff));edges.append(dict(offset=position,type=kind,target=matches[0]))
    require(bytes(raw)==original,'machine body/nonrelocation byte or relocated branch target differs')
    outgoing=[]
    for offset in range(0,len(original),4):
        word=struct.unpack_from('<I',original,offset)[0]
        if word&0x7c000000!=0x14000000:continue
        immediate=word&0x03ffffff;immediate=immediate-(1<<26)if immediate&(1<<25)else immediate;target=record['address']+offset+(immediate<<2)
        if not record['address']<=target<record['address']+len(original):outgoing.append(dict(address=record['address']+offset,mnemonic='bl'if word&0x80000000 else 'b',target=target,resolved_records=[r for r in all_records if r['address']==target]))
    return dict(name=record['name'],original_nm_record=record,original_body_sha256=sha(original),fresh_object_body_sha256=sha(bytes.fromhex(function['data'])),machine_body_equivalent=True,fresh_object_SU=frame,relocations=edges,outgoing_direct_transfers=outgoing,source_section=function['section'],section_delta=delta,historical_compiler_identity_inferred=False)


def command_su(command):
    lines=command.splitlines();key='cmd_kernel/sched/core.o := ';require(lines[0].startswith(key),'actual scheduler command declaration');argv=shlex.split(lines[0][len(key):]);source=[x[len('source_kernel/sched/core.o := '):]for x in lines if x.startswith('source_kernel/sched/core.o := ')]
    require(len(source)==1 and argv[-1]==source[0]and source[0].endswith('/source/kernel/sched/core.c')and argv.count('-o')==1,'actual source/compile operand join');output=argv[argv.index('-o')+1]
    output=Path(output);require(output.parent==Path('kernel/sched')and output.name in ('core.o','.tmp_core.o')and '-fstack-usage'in argv,'actual compiler SU sidecar required');return source[0],output.with_suffix('.su')


def su_frames(raw,source):
    frames={}
    for line in raw.splitlines():
        row=line.split('\t')
        if len(row)!=3:continue
        location,amount,kind=row;name=location.rsplit(':',1)[-1]
        if name in NAMES:
            require(name not in frames and location.rsplit(':',3)[0]==source and amount.isdecimal(),'same actual TU SU row');frames[name]=dict(bytes=int(amount),kind=kind)
    require(set(frames)==set(NAMES),'both actual scheduler SU rows');return frames


def produce(out,head,context):
    require(out==ROOT/'note10/private/v251-ci-scheduler-object'and not out.exists(),'fresh fixed producer path')
    require(context['schema']==SCHEMA+'-public-input-v1'and context['source_head']==head and context['source_sha256']==sources()and context['fixture']['passed']is True and context['fixture']['variants']==context['fixture']['assertions']==6,'actual reviewed source/new6 context')
    require(set(context)=={'schema','source_head','source_sha256','fixture'}and set(context['fixture'])=={'passed','groups','variants','assertions','result_sha256'}and context['fixture']['groups']==1,'filtered public context only')
    work=out.with_name(out.name+'-work');packed=out.with_name(out.name+'-source.tar.gz');require(not work.exists()and not packed.exists(),'fresh source workspace');out.mkdir(parents=True)
    result=dict(schema=SCHEMA+'-build-v1',passed=False,source_head=head,source_sha256=sources(),public_input=context,run_id=int(os.environ['GITHUB_RUN_ID']),run_attempt=1,scheduler_object_make_attempts=0,full_Image_attempts=0,PID1_compile_attempts=0,old_tests_replayed=0,physical_ready=False,stages=[])
    def run(argv,label,cap=8388608):
        result['stages'].append(dict(label=label,argv=list(map(str,argv)),started=True));raw=bytearray();errors=[]
        with (out/'build.log').open('ab')as log:log.write(('\n['+label+' START]\n').encode())
        child=subprocess.Popen(list(map(str,argv)),stdout=subprocess.PIPE,stderr=subprocess.STDOUT,start_new_session=True)
        def stop():
            try:os.killpg(child.pid,signal.SIGKILL)
            except ProcessLookupError:pass
        def drain():
            try:
                with (out/'build.log').open('ab')as log:
                    while block:=child.stdout.read(65536):
                        room=min(cap-len(raw),16777216-log.tell());raw.extend(block[:max(0,room)]);log.write(block[:max(0,room)]);log.flush()
                        if len(block)>room:errors.append('process output cap');stop();break
            except BaseException as error:errors.append(str(error));stop()
        thread=Thread(target=drain);thread.start()
        try:code=child.wait(timeout=600)
        except BaseException:stop();child.wait();thread.join();raise
        thread.join();result['stages'][-1].update(returncode=code,stdout_bytes=len(raw),stdout_sha256=sha(raw));require(not errors and code==0,'producer command failed: '+label+' '+str(errors));return bytes(raw)
    try:
        archive.acquire(packed)
        with packed.open('rb')as stream:require(packed.stat().st_size==212648376 and hashlib.file_digest(stream,'sha256').hexdigest()==archive.ARCHIVE_SHA,'pinned source archive')
        work.mkdir();source=archive.extract(packed,work/'source');objects=work/'objects';objects.mkdir()
        require(all(sha(bounded(source/name))==digest for name,digest in SOURCE_GUARDS.items()),'pinned scheduler/linker/build sources')
        core=bounded(source/'kernel/sched/core.c');(out/'core.c').write_bytes(core)
        kconfig=source/'drivers/misc/Kconfig';original=bounded(kconfig);require(b'NOTE10_'not in original,'stock Kconfig');kconfig.write_bytes(original+KCONFIG)
        config=bounded(HERE/'v251_scheduler_effective.config');require(sha(config)==CONFIG_SHA,'baseline config');(objects/'.config').write_bytes(config)
        make=['make','-C',source,'O='+str(objects),'ARCH=arm64','CC=clang-14','CROSS_COMPILE=aarch64-linux-gnu-','CLANG_TRIPLE=aarch64-linux-gnu-','CROSS_COMPILE_ARM32=arm-linux-gnueabi-','GCC_TOOLCHAIN_DIR=/usr/aarch64-linux-gnu/bin/','HOSTCC=gcc','HOSTCFLAGS=-Wno-error=deprecated-declarations','KCFLAGS=-gdwarf-4 -fstack-usage']
        run([*make,'olddefconfig'],'olddefconfig');actual_config=bounded(objects/'.config');(out/'effective.config').write_bytes(actual_config);result['observed_config_sha256']=sha(actual_config);require(sha(actual_config)==CONFIG_SHA,'effective config changed; stop before object make')
        result['scheduler_object_make_attempts']=1;save(out/'OBJECT-MAKE-STARTED.json',dict(argv=list(map(str,[*make,'kernel/sched/core.o'])),attempt=1))
        run([*make,'kernel/sched/core.o'],'scheduler-object')
        obj=bounded(objects/'kernel/sched/core.o');command=bounded(objects/'kernel/sched/.core.o.cmd',2097152);tu,su=command_su(command.decode());usage=bounded(objects/su,2097152)
        (out/'core.o').write_bytes(obj);(out/'core.cmd').write_bytes(command);(out/'core.su').write_bytes(usage)
        functions=object_functions(obj);frames=su_frames(usage.decode(),tu)
        elf_text=run(['aarch64-linux-gnu-readelf','--wide','--sections','--symbols','--relocs',objects/'kernel/sched/core.o'],'ELF',8388608);require(elf_text,'ELF text required');(out/'core.elf.txt').write_bytes(elf_text)
        for name,function in functions.items():
            text=run(['aarch64-linux-gnu-objdump','-d','--disassemble-zeroes','--section='+function['section_name'],'--start-address='+hex(function['value']),'--stop-address='+hex(function['value']+function['bytes']),objects/'kernel/sched/core.o'],name,131072);require(text,'function disassembly required');(out/(name+'.asm')).write_bytes(text)
        tools={name:dict(path=shutil.which(name),version=run([name,'--version'],name,65536).decode())for name in ('clang-14','aarch64-linux-gnu-as','aarch64-linux-gnu-readelf','aarch64-linux-gnu-objdump','make')}
        tools['packages']=run(['dpkg-query','-W','-f=${Package}=${Version}\n','clang-14','binutils-aarch64-linux-gnu','make'],'packages',65536).decode();save(out/'tools.json',tools)
        result.update(passed=True,translation_unit=tu,command_sha256=sha(command),SU_sha256=sha(usage),object_sha256=sha(obj),functions=functions,frames=frames,config_sha256=CONFIG_SHA)
    except BaseException as error:result.update(error_type=type(error).__name__,error=str(error)[:2048]);raise
    finally:
        if 'objects'in locals():
            partial=[(objects/'kernel/sched/core.o','core.o',33554432),(objects/'kernel/sched/.core.o.cmd','core.cmd',2097152),(objects/'.config','effective.config',1048576)]
            command_path=objects/'kernel/sched/.core.o.cmd'
            if command_path.is_file()and 0<command_path.stat().st_size<=2097152:
                try:_,sidecar=command_su(command_path.read_text());partial.append((objects/sidecar,'core.su',2097152))
                except (ValueError,IndexError,UnicodeError):pass
            for path,name,cap in partial:
                if not path.is_file()or (out/name).exists():continue
                size=path.stat().st_size;result.setdefault('partial_file_metadata',{})[name]=dict(bytes=size,preserved=0<size<=cap)
                if 0<size<=cap:(out/name).write_bytes(bounded(path,cap))
        save(out/'result.json',result);files=[p for p in out.iterdir()if p.is_file()];require(all(p.name in MEMBERS and p.stat().st_size<=33554432 for p in files)and sum(p.stat().st_size for p in files)<=67108864,'bounded manifest allowlist/total')
        save(out/'members.json',dict(schema=SCHEMA+'-members-v1',source_head=head,member_bytes={p.name:p.stat().st_size for p in files},member_sha256={p.name:sha(p.read_bytes())for p in files}))
        with zipfile.ZipFile(out.with_suffix('.zip'),'x',compression=zipfile.ZIP_DEFLATED)as bundle:
            for p in [*files,out/'members.json']:bundle.write(p,p.name)
        subprocess.run(['node',ROOT/'note10/device_test/sealed_affinity_artifact.cjs','seal',out.with_suffix('.zip'),out.with_suffix('.n10sealed'),head],check=True,timeout=120)


if __name__=='__main__':
    cli=argparse.ArgumentParser();cli.add_argument('--expected-source-head',required=True);cli.add_argument('--passed-new-test-context',required=True);args=cli.parse_args()
    context=json.loads(base64.b64decode(args.passed_new_test_context,validate=True));produce(ROOT/'note10/private/v251-ci-scheduler-object',args.expected_source_head,context)
