"""Fresh entry.o capture and ROOT-only generated context-base binding."""
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
SCHEMA='note10-v257-switch-backend'
WORKFLOW='.github/workflows/note10-v257-switch-backend.yml'
PUBLIC_FILES=('note10/device_test/v257_switch_backend.py','note10/device_test/test_v257_switch_backend.py',WORKFLOW,'note10/device_test/v251_scheduler_effective.config','note10/device_test/v251_scheduler_object.py','note10/device_test/v130_archive.py','note10/device_test/sealed_affinity_artifact.cjs')
MEMBERS={'result.json','members.json','entry.o','entry.cmd','entry.elf.txt','cpu_switch_to.asm','cpu_switch_to.bin','intrinsic.json','effective.config','tools.json','build.log','OBJECT-MAKE-STARTED.json','asm-offsets.h','asm-offsets.s','asm-offsets.cmd','entry.S','asm-offsets.c','processor.h','Kbuild','Makefile.build','arm64-Makefile'}
CONFIG_SHA=shared.CONFIG_SHA
SOURCE_GUARDS={'arch/arm64/kernel/entry.S': '0a480946e1cdfbfd2739920580fb548eee6395881580197d33ae0dd4f5f631ef', 'arch/arm64/kernel/asm-offsets.c': 'a6d0c9d352bb4f68c1f7849a4218eb299a55f3740135e99f850eb4b6a5301fbc', 'arch/arm64/include/asm/processor.h': 'f7479391e0de21c0e9afb69db7f17f1cfa739f9cbcdc2159fd8d464783bcbfb9', 'scripts/Makefile.build': 'b8eb9a53659f378ef1973889ae7e7a76aa3b043e83a7cce02e6a7588364f785c', 'Kbuild': '4b39c9171ecb5003a806ebf58907fa6f32d7b15377f1da1ff0177581ca94f495', 'arch/arm64/kernel/Makefile': '202b1a68b3a5cc5a43f5e89151c6a3cdad03809dbb30c7e03e19668f50c92fd2'}
SOURCE_MEMBERS={'arch/arm64/kernel/entry.S': 'entry.S', 'arch/arm64/kernel/asm-offsets.c': 'asm-offsets.c', 'arch/arm64/include/asm/processor.h': 'processor.h', 'scripts/Makefile.build': 'Makefile.build', 'Kbuild': 'Kbuild', 'arch/arm64/kernel/Makefile': 'arm64-Makefile'}
require=shared.require
sha=shared.sha
save=shared.save
bounded=shared.bounded


def sources():return {name:sha(bounded(ROOT/name))for name in PUBLIC_FILES}


def public_context(head,fixture,result_sha256):
    require(re.fullmatch('[0-9a-f]{40}',head)and re.fullmatch('[0-9a-f]{64}',result_sha256),'source/result identifiers')
    summary={k:fixture[k]for k in ('passed','groups','variants','assertions')};summary['result_sha256']=result_sha256
    require(summary['passed']is True and (summary['groups'],summary['variants'],summary['assertions'])==(1,5,5),'new5 only')
    return dict(schema=SCHEMA+'-public-input-v1',source_head=head,source_sha256=sources(),fixture=summary)


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
    matches=[s for s in symbols if s['name']=='cpu_switch_to'];require(len(matches)==1,'unique provider symbol');provider=matches[0];section=provider['section'];start=provider['value'];size=provider['bytes']
    require(provider['type']==2 and provider['binding']==1 and provider['visibility']==0 and 0<section<count,'defined GLOBAL DEFAULT FUNC provider')
    section_name=string(data(names),sections[section][0]);flags=sections[section][2]
    require(sections[section][1]==1 and flags&6==6 and not flags&1 and not section_name.startswith('.init')and 0<size<=32768 and start%4==size%4==0 and start+size<=len(data(section)),'non-init AX/non-W complete provider extent')
    mappings=[s for s in symbols if s['section']==section and re.fullmatch(r'\$[xd](?:\..*)?',s['name'])];before=[s for s in mappings if s['value']<=start]
    require(not any(s['name'].startswith('$d')and start<=s['value']<start+size for s in mappings)and (not before or max(before,key=lambda s:s['value'])['name'].startswith('$x')),'selected code mapping, no embedded data')
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


def command_operands(text,target,source_suffix,mode,outputs):
    lines=text.splitlines();key='cmd_'+target+' := ';require(lines and lines[0].startswith(key),'actual Kbuild command declaration');lexer=shlex.shlex(lines[0][len(key):],posix=True,punctuation_chars=';&|');lexer.whitespace_split=True;tokens=list(lexer);argv=[]
    for token in tokens:
        if token and all(c in ';&|'for c in token):break
        argv.append(token)
    prefix='source_'+target+' := ';sources=[line[len(prefix):]for line in lines if line.startswith(prefix)]
    require(len(sources)==1 and sources[0].endswith('/source/'+source_suffix)and argv.count(sources[0])==1 and argv.count('-o')==1 and mode in argv and Path(argv[0]).name=='clang-14','unique actual compiler/source/mode operands');output=argv[argv.index('-o')+1];require(output in outputs,'actual Kbuild compiler output');return dict(source=sources[0],output=output,argv=argv)


def generated_base(header,assembly):
    h=re.findall(r'^#define[ \t]+THREAD_CPU_CONTEXT[ \t]+(0[xX][0-9a-fA-F]+|[0-9]+)(?=[ \t]|$)',header,re.M)
    a=re.findall(r'^[ \t]*\.ascii[ \t]+"->THREAD_CPU_CONTEXT[ \t]+[$#]*(0[xX][0-9a-fA-F]+|[0-9]+)[ \t]+([^"\n]+)"',assembly,re.M)
    require(len(h)==len(a)==1 and 'offsetof'in a[0][1]and 'thread.cpu_context'in a[0][1],'unique stock generated offset records')
    parse=lambda value:int(value,16)if value.lower().startswith('0x')else int(value,10);value=parse(h[0]);require(0<value<1<<64 and value==parse(a[0][0]),'same generated THREAD_CPU_CONTEXT value');return value


def materialized_base(body):
    value=None;rows=[]
    for at in range(0,min(len(body),20),4):
        word=struct.unpack_from('<I',body,at)[0]
        if word==0x8b0a0008:
            require(value is not None,'known x10 before ADD x8,x0,x10');return value,rows,at
        require(word&31==10 and word&0x80000000,'initial64-bit x10 constant only')
        if word&0x1f800000==0x12800000:
            opcode=(word>>29)&3;shift=((word>>21)&3)*16;imm=(word>>5)&0xffff;require(opcode in (0,2,3),'valid wide immediate')
            if opcode==2:value=imm<<shift
            elif opcode==0:value=(~(imm<<shift))&((1<<64)-1)
            else:require(value is not None,'MOVK needs known x10');value=(value&~(0xffff<<shift))|(imm<<shift)
        elif word&0x7f8003e0==0x320003e0:
            n=(word>>22)&1;imms=(word>>10)&63;immr=(word>>16)&63;length=((n<<6)|((~imms)&63)).bit_length()-1;require(length>=1,'logical immediate element width');levels=(1<<length)-1;s=imms&levels;rotate=immr&levels;require(s!=levels,'valid logical immediate');width=1<<length;mask=(1<<width)-1;ones=(1<<(s+1))-1;part=((ones>>rotate)|(ones<<(width-rotate)))&mask;value=sum(part<<bit for bit in range(0,64,width))
        else:raise ValueError('unsupported initial x10 materialization')
        rows.append(dict(offset=at,word=f'{word:08x}',x10=value))
    raise ValueError('missing exact ADD x8,x0,x10 after materialization')


def prove(body,info,entry_command,offset_command,header,offset_assembly,entry_source,offset_source,processor_source):
    p=info['provider'];require(p['name']=='cpu_switch_to'and p['type']==2 and p['binding']==1 and p['visibility']==0 and p['section']>0 and p['bytes']==len(body)and 0<len(body)<=32768 and len(body)%4==0,'intrinsic defined complete backend');require(info['section_flags']&6==6 and not info['section_flags']&1 and not info['section_name'].startswith('.init')and not info['relocations'],'relocation-free selected code, never interpret placeholders')
    require(sum(s['name']=='cpu_switch_to'for s in info['symbols'])==1 and info['symbols'][p['index']]==p,'intrinsic unique symbol identity')
    entry=command_operands(entry_command,'arch/arm64/kernel/entry.o','arch/arm64/kernel/entry.S','-c',('arch/arm64/kernel/entry.o','arch/arm64/kernel/.tmp_entry.o'));require('-D__ASSEMBLY__'in entry['argv'],'assembler preprocessing provenance')
    offsets=command_operands(offset_command,'arch/arm64/kernel/asm-offsets.s','arch/arm64/kernel/asm-offsets.c','-S',('arch/arm64/kernel/asm-offsets.s',))
    for name,value in {'ANDROID_VERSION':'110000','ANDROID_MAJOR_VERSION':'r'}.items():require([x for x in offsets['argv']if x=='-D'+name or x.startswith('-D'+name+'=')]==['-D'+name+'='+value]and '-U'+name not in offsets['argv'],'actual offset-generation Android11/r macros')
    require(re.search(r'DEFINE\s*\(\s*THREAD_CPU_CONTEXT\s*,\s*offsetof\s*\(\s*struct task_struct\s*,\s*thread\.cpu_context\s*\)\s*\)',offset_source)is not None and 'ENTRY(cpu_switch_to)'in entry_source and 'THREAD_CPU_CONTEXT'in entry_source and 'struct cpu_context'in processor_source,'pinned source meanings for generated base')
    value=generated_base(header,offset_assembly);observed,materialization,add_at=materialized_base(body);require(value==observed,'generated context base differs from compiled x10 immediate')
    return dict(compiled_backend_body_captured=True,generated_THREAD_CPU_CONTEXT=value,generated_context_base_immediate_binding_proven=True,materialization=materialization,ADD_x8_x0_x10_offset=add_at,entry_compile_source=entry['source'],entry_compile_output=entry['output'],offset_generation_source=offsets['source'],offset_generation_output=offsets['output'],compiler_static_SU_bytes=None,assembly_C_compiler_SU_claimed=False,backend_save_load_semantics_proven=False,numeric_internal_context_layout_proven=False,task_stack_validity_proven=False,liveness_proven=False,switch_resume_contract_proven=False,cross_object_link_resolution_proven=False,original_Image_body_equivalent=False,historical_compiler_identity_inferred=False,local_SP_peak_proven=False,whole_scheduler_or_frontdoor_stack_bound_proven=False,runtime_observed=False,physical_ready=False)


def produce(out,head,context):
    require(out==ROOT/'note10/private/v257-ci-switch-backend'and not out.exists(),'fresh fixed producer output');require(set(context)=={'schema','source_head','source_sha256','fixture'}and context['schema']==SCHEMA+'-public-input-v1'and context['source_head']==head and re.fullmatch('[0-9a-f]{40}',head)and context['source_sha256']==sources(),'exact new public context')
    f=context['fixture'];require(set(f)=={'passed','groups','variants','assertions','result_sha256'}and f['passed']is True and (f['groups'],f['variants'],f['assertions'])==(1,5,5)and re.fullmatch('[0-9a-f]{64}',f['result_sha256']),'filtered new5 fixture');require(os.environ.get('PLATFORM_VERSION')=='11'and os.environ.get('ANDROID_MAJOR_VERSION')=='r','explicit Android11/r environment')
    work=out.with_name(out.name+'-work');packed=out.with_name(out.name+'-source.tar.gz');require(not work.exists()and not packed.exists(),'fresh source workspace');out.mkdir(parents=True)
    result=dict(schema=SCHEMA+'-build-v1',passed=False,source_head=head,source_sha256=sources(),public_input=context,run_id=int(os.environ['GITHUB_RUN_ID']),run_attempt=1,entry_object_make_attempts=0,other_explicit_object_targets=0,full_Image_attempts=0,vmlinux_attempts=0,PID1_compile_attempts=0,old_tests_replayed=0,semantic_base_proof_executed=False,physical_ready=False,stages=[])
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
        for name,digest in SOURCE_GUARDS.items():
            raw=bounded(source/name);require(sha(raw)==digest,'pinned backend/generator source');(out/SOURCE_MEMBERS[name]).write_bytes(raw)
        kconfig=source/'drivers/misc/Kconfig';original=bounded(kconfig);require(b'NOTE10_'not in original,'stock Kconfig');kconfig.write_bytes(original+shared.KCONFIG)
        config=bounded(HERE/'v251_scheduler_effective.config');require(sha(config)==CONFIG_SHA,'baseline config');(objects/'.config').write_bytes(config)
        make=['make','-C',source,'O='+str(objects),'ARCH=arm64','CC=clang-14','CROSS_COMPILE=aarch64-linux-gnu-','CLANG_TRIPLE=aarch64-linux-gnu-','CROSS_COMPILE_ARM32=arm-linux-gnueabi-','GCC_TOOLCHAIN_DIR=/usr/aarch64-linux-gnu/bin/','HOSTCC=gcc','HOSTCFLAGS=-Wno-error=deprecated-declarations','KCFLAGS=-gdwarf-4 -fstack-usage']
        run([*make,'olddefconfig'],'olddefconfig');actual=bounded(objects/'.config');(out/'effective.config').write_bytes(actual);result['observed_config_sha256']=sha(actual);require(sha(actual)==CONFIG_SHA,'effective config changed; no object fallback')
        result['entry_object_make_attempts']=1;save(out/'OBJECT-MAKE-STARTED.json',dict(argv=list(map(str,[*make,'arch/arm64/kernel/entry.o'])),attempt=1));run([*make,'arch/arm64/kernel/entry.o'],'entry-object')
        capture_paths={'entry.o':'arch/arm64/kernel/entry.o','entry.cmd':'arch/arm64/kernel/.entry.o.cmd','asm-offsets.h':'include/generated/asm-offsets.h','asm-offsets.s':'arch/arm64/kernel/asm-offsets.s','asm-offsets.cmd':'arch/arm64/kernel/.asm-offsets.s.cmd'}
        for name,path in capture_paths.items():(out/name).write_bytes(bounded(objects/path,33554432 if name=='entry.o'else 2097152))
        obj=bounded(out/'entry.o');body,info=extract(obj);(out/'cpu_switch_to.bin').write_bytes(body);save(out/'intrinsic.json',dict(object_sha256=sha(obj),selected_body_sha256=sha(body),selected_body_bytes=len(body),info=info));result.update(object_sha256=sha(obj),selected_body_sha256=sha(body),selected_body_bytes=len(body))
        text=run(['aarch64-linux-gnu-readelf','--wide','--sections','--symbols','--relocs',objects/'arch/arm64/kernel/entry.o'],'ELF');require(text,'ELF text');(out/'entry.elf.txt').write_bytes(text)
        p=info['provider'];text=run(['aarch64-linux-gnu-objdump','-d','--disassemble-zeroes','--section='+info['section_name'],'--start-address='+hex(p['value']),'--stop-address='+hex(p['value']+p['bytes']),objects/'arch/arm64/kernel/entry.o'],'cpu_switch_to',262144);require(text,'complete selected disassembly');(out/'cpu_switch_to.asm').write_bytes(text)
        tools={name:dict(path=shutil.which(name),version=run([name,'--version'],name,65536).decode())for name in ('clang-14','aarch64-linux-gnu-as','aarch64-linux-gnu-readelf','aarch64-linux-gnu-objdump','make')};tools['packages']=run(['dpkg-query','-W','-f=${Package}=${Version}\n','clang-14','binutils-aarch64-linux-gnu','make'],'packages',65536).decode();save(out/'tools.json',tools);result.update(passed=True,config_sha256=CONFIG_SHA,intrinsic_capture_only=True)
    except BaseException as error:result.update(error_type=type(error).__name__,error=str(error)[:2048]);raise
    finally:
        if 'objects'in locals():
            partial={'entry.o':'arch/arm64/kernel/entry.o','entry.cmd':'arch/arm64/kernel/.entry.o.cmd','asm-offsets.h':'include/generated/asm-offsets.h','asm-offsets.s':'arch/arm64/kernel/asm-offsets.s','asm-offsets.cmd':'arch/arm64/kernel/.asm-offsets.s.cmd','effective.config':'.config'}
            for name,path in partial.items():
                path=objects/path
                if not path.is_file()or (out/name).exists():continue
                size=path.stat().st_size;cap=33554432 if name=='entry.o'else 2097152;result.setdefault('partial_file_metadata',{})[name]=dict(bytes=size,preserved=0<size<=cap)
                if 0<size<=cap:(out/name).write_bytes(bounded(path,cap))
        save(out/'result.json',result);files=[p for p in out.iterdir()if p.is_file()];require(all(p.name in MEMBERS and 0<p.stat().st_size<=33554432 for p in files)and sum(p.stat().st_size for p in files)<=67108864,'bounded evidence allowlist/total');save(out/'members.json',dict(schema=SCHEMA+'-members-v1',source_head=head,member_bytes={p.name:p.stat().st_size for p in files},member_sha256={p.name:sha(p.read_bytes())for p in files}))
        with zipfile.ZipFile(out.with_suffix('.zip'),'x',compression=zipfile.ZIP_DEFLATED)as bundle:
            for p in [*files,out/'members.json']:bundle.write(p,p.name)
        subprocess.run(['node',ROOT/'note10/device_test/sealed_affinity_artifact.cjs','seal',out.with_suffix('.zip'),out.with_suffix('.n10sealed'),head],check=True,timeout=120)


if __name__=='__main__':
    cli=argparse.ArgumentParser();cli.add_argument('--expected-source-head',required=True);cli.add_argument('--passed-new-test-context',required=True);args=cli.parse_args()
    context=json.loads(base64.b64decode(args.passed_new_test_context,validate=True));produce(ROOT/'note10/private/v257-ci-switch-backend',args.expected_source_head,context)
