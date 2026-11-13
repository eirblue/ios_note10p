"""Fresh process.o provider provenance only; cpu_switch_to implementation remains opaque."""
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
from threading import Thread
import zipfile
import v130_archive as archive
import v251_scheduler_object as shared

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
SCHEMA='note10-v255-switch-provider'
WORKFLOW='.github/workflows/note10-v255-switch-object.yml'
PUBLIC_FILES=('note10/device_test/v255_switch_object.py','note10/device_test/test_v255_switch_object.py',WORKFLOW,'note10/device_test/v251_scheduler_effective.config','note10/device_test/v251_scheduler_object.py','note10/device_test/v130_archive.py','note10/device_test/sealed_affinity_artifact.cjs')
MEMBERS={'result.json','members.json','process.o','process.cmd','process.su','process.elf.txt','__switch_to.asm','__switch_to.bin','effective.config','tools.json','build.log','process.c','OBJECT-MAKE-STARTED.json'}
CONFIG_SHA=shared.CONFIG_SHA
SOURCE_SHA='c546e876ed45eb4b90cd0fdc51a72905ba1d7367ba022cf7c8d5542e69d21b85'
SOURCE_GUARDS={'arch/arm64/kernel/process.c':SOURCE_SHA,'arch/arm64/kernel/Makefile':'202b1a68b3a5cc5a43f5e89151c6a3cdad03809dbb30c7e03e19668f50c92fd2'}
require=shared.require
sha=shared.sha
save=shared.save
bounded=shared.bounded


def sources():return {name:sha(bounded(ROOT/name))for name in PUBLIC_FILES}


def public_context(head,fixture,result_sha256):
    require(re.fullmatch('[0-9a-f]{40}',head)and re.fullmatch('[0-9a-f]{64}',result_sha256),'source/result identifiers')
    summary={k:fixture[k]for k in ('passed','groups','variants','assertions')};summary['result_sha256']=result_sha256
    require(summary['passed']is True and (summary['groups'],summary['variants'],summary['assertions'])==(1,4,4),'new4 only')
    return dict(schema=SCHEMA+'-public-input-v1',source_head=head,source_sha256=sources(),fixture=summary)


def command_su(command):
    lines=command.splitlines();key='cmd_arch/arm64/kernel/process.o := ';require(lines and lines[0].startswith(key),'actual process command declaration');argv=shlex.split(lines[0][len(key):]);prefix='source_arch/arm64/kernel/process.o := ';source=[x[len(prefix):]for x in lines if x.startswith(prefix)]
    require(len(source)==1 and argv[-1]==source[0]and source[0].endswith('/source/arch/arm64/kernel/process.c')and argv.count('-o')==1,'actual process source/compile operands');output=Path(argv[argv.index('-o')+1])
    require(output.parent==Path('arch/arm64/kernel')and output.name in ('process.o','.tmp_process.o')and '-fstack-usage'in argv,'actual process SU operand')
    for name,value in {'ANDROID_VERSION':'110000','ANDROID_MAJOR_VERSION':'r'}.items():
        require([x for x in argv if x=='-D'+name or x.startswith('-D'+name+'=')]==['-D'+name+'='+value]and '-U'+name not in argv,'actual Android11/r compiler macros')
    return source[0],output.with_suffix('.su')


def extract(raw):
    require(raw[:6]==b'\x7fELF\x02\x01'and len(raw)>=64 and struct.unpack_from('<HH',raw,16)==(1,183),'AArch64 ELF64 relocatable object')
    offset=struct.unpack_from('<Q',raw,40)[0];ents,count,names=struct.unpack_from('<HHH',raw,58)
    require(ents==64 and 0<count<=4096 and names<count and offset+count*64<=len(raw),'bounded ELF sections')
    sections=[struct.unpack_from('<IIQQQQIIQQ',raw,offset+i*64)for i in range(count)]
    def data(index):
        require(0<=index<count,'section index');s=sections[index];require(s[1]!=8 and s[4]+s[5]<=len(raw),'section extent');return raw[s[4]:s[4]+s[5]]
    def string(table,at):
        require(0<=at<len(table)and b'\0'in table[at:],'string extent');return table[at:table.index(b'\0',at)].decode()
    tables=[i for i,s in enumerate(sections)if s[1]==2];require(len(tables)==1,'one static symbol table');table=tables[0];s=sections[table]
    require(s[9]==24 and s[5]%24==0 and s[6]<count,'symbol entries');strings=data(s[6]);symbols=[]
    for i in range(0,len(data(table)),24):
        name,info,other,index,value,size=struct.unpack_from('<IBBHQQ',data(table),i);symbols.append(dict(index=i//24,name=string(strings,name),type=info&15,binding=info>>4,visibility=other&3,section=index,value=value,bytes=size))
    matches=[s for s in symbols if s['name']=='__switch_to'];require(len(matches)==1,'unique provider symbol');provider=matches[0];section=provider['section'];start=provider['value'];size=provider['bytes']
    require(provider['type']==2 and provider['binding']==1 and provider['visibility']==0 and 0<section<count,'defined GLOBAL DEFAULT FUNC provider')
    section_name=string(data(names),sections[section][0]);flags=sections[section][2]
    require(sections[section][1]==1 and flags&6==6 and not flags&1 and not section_name.startswith('.init')and 0<size<=32768 and start%4==size%4==0 and start+size<=len(data(section)),'non-init AX/non-W complete provider extent')
    relocations=[]
    for s in sections:
        require(not(s[1]==9 and s[7]==section),'selected REL unsupported')
        if s[1]!=4 or s[7]!=section:continue
        require(s[6]==table and s[9]==24 and s[5]%24==0 and s[4]+s[5]<=len(raw),'selected RELA extent')
        for at in range(s[4],s[4]+s[5],24):
            place,info,addend=struct.unpack_from('<QQq',raw,at)
            if not start<=place<start+size:continue
            require(info>>32<len(symbols)and place%4==0,'selected relocation index/offset');relocations.append(dict(offset=place-start,type=info&0xffffffff,symbol_index=info>>32,target=dict(symbols[info>>32]),addend=addend))
    return data(section)[start:start+size],dict(provider=provider,section_name=section_name,section_flags=flags,symbols=symbols,relocations=relocations)


def verify(body,info,usage,tu,source):
    p=info['provider'];require(p['name']=='__switch_to'and p['type']==2 and p['binding']==1 and p['visibility']==0 and p['section']>0 and p['bytes']==len(body)and 0<len(body)<=32768 and len(body)%4==0,'defined complete provider')
    require(info['section_flags']&6==6 and not info['section_flags']&1 and not info['section_name'].startswith('.init'),'provider executable noninit section')
    rows=[]
    for line in usage.splitlines():
        parts=line.split('\t')
        if len(parts)==3 and parts[0].rsplit(':',1)[-1]=='__switch_to':rows.append(parts)
    require(len(rows)==1,'unique actual provider SU row');location,amount,kind=rows[0];loc=location.rsplit(':',2)
    require(len(loc)==3 and loc[0]==tu and loc[1].isdecimal()and amount.isdecimal()and kind=='static'and 0<=int(amount)<=8192,'same TU static SU')
    lines=source.splitlines();line=int(loc[1]);require(0<line<=len(lines)and re.search(r'\b__switch_to\s*\(', '\n'.join(lines[line-1:line+3])),'source definition/SU line join')
    backend_symbols=[s for s in info['symbols']if s['name']=='cpu_switch_to'];require(len(backend_symbols)==1,'unique cpu_switch_to symbol');backend=backend_symbols[0];edges=[];seen=set()
    for rel in info['relocations']:
        at=rel['offset'];require(type(at)is int and at%4==0 and 0<=at<=len(body)-4 and at not in seen,'unique selected relocation extent');seen.add(at)
        index=rel['symbol_index'];require(0<=index<len(info['symbols'])and info['symbols'][index]==rel['target']and rel['target']['index']==index,'actual relocation symbol index identity')
        if rel['type']in (282,283):
            word=struct.unpack_from('<I',body,at)[0];opcode=0x94000000 if rel['type']==283 else 0x14000000;require(word&0xfc000000==opcode,'actual branch relocation opcode');edges.append(dict(**rel,mnemonic='bl'if rel['type']==283 else 'b'))
    backend_edges=[e for e in edges if e['target']==backend and e['target']['name']=='cpu_switch_to'];require(len(backend_edges)==1 and backend_edges[0]['addend']==0,'one exact cpu_switch_to CALL26/BL or JUMP26/B')
    frontier=[];rel_by_offset={e['offset']:e for e in edges}
    for at in range(0,len(body),4):
        word=struct.unpack_from('<I',body,at)[0]
        if word&0x7c000000==0x14000000:
            imm=word&0x03ffffff;imm=imm-(1<<26)if imm&(1<<25)else imm;frontier.append(dict(offset=at,mnemonic='bl'if word&0x80000000 else 'b',encoded_section_target=p['value']+at+(imm<<2),relocation=rel_by_offset.get(at)))
        elif word&0xfffffc1f in (0xd61f0000,0xd63f0000):frontier.append(dict(offset=at,mnemonic='blr'if word&0x00200000 else 'br',opaque=True))
    limits={k:False for k in ('compiled_backend_body_captured','numeric_context_offset_measured','machine_argument_register_flow_proven','cross_object_link_resolution_proven','original_Image_body_equivalent','historical_compiler_identity_inferred','switch_resume_contract_proven','local_SP_peak_proven','whole_scheduler_or_frontdoor_stack_bound_proven','runtime_observed','physical_ready')}
    return dict(provider=p,section_name=info['section_name'],body_sha256=sha(body),fresh_provider_static_SU_bytes=int(amount),source_line=line,fresh_defined_provider_captured=True,cpu_switch_to_direct_boundary_proven=True,backend_boundary=backend_edges[0],selected_relocations=info['relocations'],transfer_frontier=frontier,**limits)


def produce(out,head,context):
    require(out==ROOT/'note10/private/v255-ci-switch-object'and not out.exists(),'fresh fixed producer output')
    require(set(context)=={'schema','source_head','source_sha256','fixture'}and context['schema']==SCHEMA+'-public-input-v1'and context['source_head']==head and re.fullmatch('[0-9a-f]{40}',head)and context['source_sha256']==sources(),'exact new public context')
    f=context['fixture'];require(set(f)=={'passed','groups','variants','assertions','result_sha256'}and f['passed']is True and (f['groups'],f['variants'],f['assertions'])==(1,4,4)and re.fullmatch('[0-9a-f]{64}',f['result_sha256']),'filtered new4 fixture')
    require(os.environ.get('PLATFORM_VERSION')=='11'and os.environ.get('ANDROID_MAJOR_VERSION')=='r','explicit Android11/r environment')
    work=out.with_name(out.name+'-work');packed=out.with_name(out.name+'-source.tar.gz');require(not work.exists()and not packed.exists(),'fresh source workspace');out.mkdir(parents=True)
    result=dict(schema=SCHEMA+'-build-v1',passed=False,source_head=head,source_sha256=sources(),public_input=context,run_id=int(os.environ['GITHUB_RUN_ID']),run_attempt=1,process_object_make_attempts=0,entry_object_make_attempts=0,full_Image_attempts=0,vmlinux_attempts=0,PID1_compile_attempts=0,old_tests_replayed=0,physical_ready=False,stages=[])
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
        require(all(sha(bounded(source/name))==digest for name,digest in SOURCE_GUARDS.items()),'pinned provider sources');(out/'process.c').write_bytes(bounded(source/'arch/arm64/kernel/process.c'))
        kconfig=source/'drivers/misc/Kconfig';original=bounded(kconfig);require(b'NOTE10_'not in original,'stock Kconfig');kconfig.write_bytes(original+shared.KCONFIG)
        config=bounded(HERE/'v251_scheduler_effective.config');require(sha(config)==CONFIG_SHA,'baseline config');(objects/'.config').write_bytes(config)
        make=['make','-C',source,'O='+str(objects),'ARCH=arm64','CC=clang-14','CROSS_COMPILE=aarch64-linux-gnu-','CLANG_TRIPLE=aarch64-linux-gnu-','CROSS_COMPILE_ARM32=arm-linux-gnueabi-','GCC_TOOLCHAIN_DIR=/usr/aarch64-linux-gnu/bin/','HOSTCC=gcc','HOSTCFLAGS=-Wno-error=deprecated-declarations','KCFLAGS=-gdwarf-4 -fstack-usage']
        run([*make,'olddefconfig'],'olddefconfig');actual=bounded(objects/'.config');(out/'effective.config').write_bytes(actual);result['observed_config_sha256']=sha(actual);require(sha(actual)==CONFIG_SHA,'effective config changed; no object fallback')
        result['process_object_make_attempts']=1;save(out/'OBJECT-MAKE-STARTED.json',dict(argv=list(map(str,[*make,'arch/arm64/kernel/process.o'])),attempt=1));run([*make,'arch/arm64/kernel/process.o'],'process-object')
        obj=bounded(objects/'arch/arm64/kernel/process.o');(out/'process.o').write_bytes(obj)
        command=bounded(objects/'arch/arm64/kernel/.process.o.cmd',2097152);(out/'process.cmd').write_bytes(command);tu,su=command_su(command.decode());usage=bounded(objects/su,2097152);(out/'process.su').write_bytes(usage)
        body,info=extract(obj);(out/'__switch_to.bin').write_bytes(body);proof=verify(body,info,usage.decode(),tu,bounded(out/'process.c').decode())
        text=run(['aarch64-linux-gnu-readelf','--wide','--sections','--symbols','--relocs',objects/'arch/arm64/kernel/process.o'],'ELF');require(text,'ELF text');(out/'process.elf.txt').write_bytes(text)
        p=info['provider'];text=run(['aarch64-linux-gnu-objdump','-d','--disassemble-zeroes','--section='+info['section_name'],'--start-address='+hex(p['value']),'--stop-address='+hex(p['value']+p['bytes']),objects/'arch/arm64/kernel/process.o'],'__switch_to',262144);require(text,'complete selected disassembly');(out/'__switch_to.asm').write_bytes(text)
        tools={name:dict(path=shutil.which(name),version=run([name,'--version'],name,65536).decode())for name in ('clang-14','aarch64-linux-gnu-as','aarch64-linux-gnu-readelf','aarch64-linux-gnu-objdump','make')};tools['packages']=run(['dpkg-query','-W','-f=${Package}=${Version}\n','clang-14','binutils-aarch64-linux-gnu','make'],'packages',65536).decode();save(out/'tools.json',tools)
        result.update(passed=True,translation_unit=tu,command_sha256=sha(command),SU_sha256=sha(usage),object_sha256=sha(obj),provider_info=info,proof=proof,config_sha256=CONFIG_SHA)
    except BaseException as error:result.update(error_type=type(error).__name__,error=str(error)[:2048]);raise
    finally:
        if 'objects'in locals():
            partial=[(objects/'arch/arm64/kernel/process.o','process.o',33554432),(objects/'arch/arm64/kernel/.process.o.cmd','process.cmd',2097152),(objects/'.config','effective.config',1048576)];cmd=objects/'arch/arm64/kernel/.process.o.cmd'
            if cmd.is_file()and 0<cmd.stat().st_size<=2097152:
                try:_,su=command_su(cmd.read_text());partial.append((objects/su,'process.su',2097152))
                except (ValueError,IndexError,UnicodeError):pass
            for path,name,cap in partial:
                if not path.is_file()or (out/name).exists():continue
                size=path.stat().st_size;result.setdefault('partial_file_metadata',{})[name]=dict(bytes=size,preserved=0<size<=cap)
                if 0<size<=cap:(out/name).write_bytes(bounded(path,cap))
        save(out/'result.json',result);files=[p for p in out.iterdir()if p.is_file()];require(all(p.name in MEMBERS and 0<p.stat().st_size<=33554432 for p in files)and sum(p.stat().st_size for p in files)<=67108864,'bounded evidence allowlist/total')
        save(out/'members.json',dict(schema=SCHEMA+'-members-v1',source_head=head,member_bytes={p.name:p.stat().st_size for p in files},member_sha256={p.name:sha(p.read_bytes())for p in files}))
        with zipfile.ZipFile(out.with_suffix('.zip'),'x',compression=zipfile.ZIP_DEFLATED)as bundle:
            for p in [*files,out/'members.json']:bundle.write(p,p.name)
        subprocess.run(['node',ROOT/'note10/device_test/sealed_affinity_artifact.cjs','seal',out.with_suffix('.zip'),out.with_suffix('.n10sealed'),head],check=True,timeout=120)


if __name__=='__main__':
    cli=argparse.ArgumentParser();cli.add_argument('--expected-source-head',required=True);cli.add_argument('--passed-new-test-context',required=True);args=cli.parse_args()
    context=json.loads(base64.b64decode(args.passed_new_test_context,validate=True));produce(ROOT/'note10/private/v255-ci-switch-object',args.expected_source_head,context)
