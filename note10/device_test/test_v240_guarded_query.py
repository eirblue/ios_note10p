"""One new actual guarded C body group plus directly affected overlay/type seams."""
import json
from pathlib import Path
import subprocess
import v240_native_prepare as p

C_COUNTS=dict(variants=19,assertions=138)
E_COUNTS=dict(variants=12,assertions=12)
COUNTS=dict(groups=1,variants=31,assertions=150)


def target_data():
    functions=p.QUERY_CAPTURE;source='/ci/work/source/arch/arm64/mm/init.c'
    command=('cmd_arch/arm64/mm/init.o := clang-14 -fstack-usage -fno-strict-aliasing -o arch/arm64/mm/.tmp_init.o -c '+source+'\nsource_arch/arm64/mm/init.o := '+source+'\n').encode()
    rows=[];usage='';elf=' [ 1] .text PROGBITS 0000000000000000 000040 000800 00 AX 0 0 4\n [ 2] .bss.n226_source_pool NOBITS 0000000000000000 001000 00c000 00 WA 0 0 4096\n';linked=''
    for i,name in enumerate(functions):
        kind='T'if name in ('n240_observe_current_cpu','n240_invalidate_observations','n231_capture_cpu_observation','n226_stack_room')else't'
        rows.append(name+' '+kind+' '+format(i*8,'x')+' 8');usage+=source+':1:'+name+'\t16\tstatic\n'
        elf+=' '+str(i+1)+': '+format(i*8,'016x')+' 8 FUNC '+('GLOBAL'if kind=='T'else'LOCAL')+' DEFAULT 1 '+name+'\n'
        linked+=name+' '+kind+' '+format(0x10000+i*8,'x')+' 8\n'
    for name,value in p.QUERY_ABS.items():rows.append(name+' A '+format(value,'x'))
    pool=0x100000;slot=pool+43608
    rows+=['n226_source_pool b '+format(pool,'x')+' c000','n240_query_storage B '+format(slot,'x')+' 38']
    elf+=' 90: '+format(pool,'016x')+' 49152 OBJECT LOCAL DEFAULT 2 n226_source_pool\n 91: '+format(slot,'016x')+' 56 OBJECT GLOBAL DEFAULT 2 n240_query_storage\n'
    return '\n'.join(rows)+'\n',usage,elf,command,linked


def graph_data():
    symbols,usage,elf,command,linked=target_data();name='OUTLINED_FUNCTION_999';source='/ci/work/source/arch/arm64/mm/init.c'
    elf+=' 92: 0000000000000100 4 FUNC LOCAL DEFAULT 1 '+name+'\n';usage+=source+':1:'+name+'\t0\tstatic\n'
    linked+=name+' t 10100 4\n';target=p.query_target(symbols,usage,elf,command,linked)
    raw=dict(schema='note10-v240-guarded-query-raw-v1',linked_nm_sha256=p.sha(linked.encode()),target=target,assembly={},symbols={},tools=[])
    for i,key in enumerate((*p.QUERY_CAPTURE,'owner-outlined@0000000000010100:4')):
        local=i==len(p.QUERY_CAPTURE);symbol=name if local else key;address=0x10100 if local else 0x10000+i*8;size=4 if local else 8
        item=dict(symbol=symbol,address=address,bytes=size,aliases=[symbol]);text=format(address,'x')+' <'+symbol+'>:\n'
        text+=' '+format(address,'x')+': 94000000 bl 10100 <'+name+'>\n'if i==0 else ' '+format(address,'x')+': d65f03c0 ret\n'
        if size==8:text+=' '+format(address+4,'x')+': d65f03c0 ret\n'
        raw['symbols'][key]=item;raw['assembly'][key]=text
        raw['tools'].append(dict(key=key,argv=['aarch64-linux-gnu-objdump','-d','--disassemble-zeroes','--start-address='+hex(address),'--stop-address='+hex(address+size),'/ci/work/objects/vmlinux'],returncode=0,stdout_sha256=p.sha(text.encode()),stderr=''))
    return raw,target,linked,dict(objects={'arch/arm64/mm/init.o':dict(stack_usage=usage,elf_sections_and_symbols=elf)}),'/ci/work/objects'


def run(output,compiler_argv):
    out=Path(output);argv=p.fixture_command(out,compiler_argv[0]);p.require(argv==compiler_argv,'exact new C argv required')
    p.p.save(out/'COMPILE-STARTED.json',dict(argv=argv,attempt=1))
    with (out/'compile.log').open('xb')as log:done=subprocess.run(argv,stdout=log,stderr=subprocess.STDOUT,timeout=120,check=False)
    p.require(done.returncode==0,'new guarded C compile failed')
    p.p.save(out/'C-FIXTURE-STARTED.json',dict(argv=[str(out/'guarded-query-fixture.exe')],attempt=1))
    done=subprocess.run([str(out/'guarded-query-fixture.exe')],stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=60,check=False)
    (out/'C.stdout').write_bytes(done.stdout);(out/'C.stderr').write_bytes(done.stderr)
    p.require(done.returncode==0 and json.loads(done.stdout)==C_COUNTS,'actual new guarded C cases failed')
    old=b'#include "v231_cpu_observation.h"\nif(n217_kernel_state.spent)return -EALREADY;\nmemset(n226_source_pool,0,sizeof(n226_source_pool));\nOWNER_ADMISSION\n'
    old+=b'    error=n231_capture_cpu_observation((struct n231_cpu_observation *)(n226_source_pool+N231_POOL_OFFSET));\n    if(error)goto early;\n'
    old+=b'    /* Capture/put_cpu and possible scheduling have returned before this sample. */\nFRESH_ROOM_SAMPLE\n    error=n226_open(ctx);\n done:\n'
    old+=b'    if(error)memset(n226_source_pool+N231_POOL_OFFSET,0,sizeof(struct n231_cpu_observation));\n'
    main=b'kernel-source\n#include "v233_cpu_node_consistency.c"\n';store=b'static __always_inline void n231_emit(int);\nOUTER_STORE{n226_emit(error);n231_emit(error);}\n'
    cases=[]
    def accepted(name,call):cases.append((name,call,True))
    def rejected(name,call):cases.append((name,call,False))
    def caller():
        new=p.prepare_stream(old,p.sha(old));return new.index(b'n217_kernel_state.spent')<new.index(b'memset(n226_source_pool')<new.index(b'OWNER_ADMISSION')<new.index(b'n240_observe_current_cpu(')<new.index(b'FRESH_ROOM_SAMPLE')<new.index(b'n226_open(')and b'error=n231_capture_cpu_observation('not in new
    accepted('one guarded caller follows spent/reset/owner before source-open',caller)
    rejected('mutated stream preimage rejected',lambda:p.prepare_stream(old+b'\n',p.sha(old)))
    accepted('every late error invalidates sample node and receipt',lambda:b'if(error)n240_invalidate_observations('in p.prepare_stream(old,p.sha(old))and b'N233_POOL_OFFSET'in p.prepare_stream(old,p.sha(old)))
    accepted('new body follows unchanged providers in owner TU',lambda:p.prepare_main(main,p.sha(main)).endswith(b'#include "v233_cpu_node_consistency.c"\n#include "v240_guarded_query.c"\n'))
    rejected('mutated owner include preimage rejected',lambda:p.prepare_main(main+b'\n',p.sha(main)))
    accepted('query logger stays at existing outer store depth',lambda:b'n226_emit(error);n231_emit(error);n240_emit(error);'in p.prepare_store(store,p.sha(store)))
    data=target_data()
    accepted('actual owner ABI parser binds56 alias and static frames',lambda:p.query_target(*data)['record_bytes']==56)
    rejected('wrong alias offset rejected',lambda:p.query_target(data[0].replace('n240_query_storage B 10aa58','n240_query_storage B 10aa60'),*data[1:]))
    rejected('dynamic new query frame rejected',lambda:p.query_target(data[0],data[1].replace('\t16\tstatic','\t16\tdynamic',1),*data[2:]))
    graph=graph_data()
    accepted('fresh graph binds named and direct owner helper to same TU and root',lambda:bool(p.verify_guarded(*graph)['direct_owner_local_bodies']))
    rejected('jointly moved guarded captures reject retained same-image root',lambda:p.verify_guarded(*graph[:4],'/ci/other/objects'))
    def wrong_helper():
        raw,target,nm,stack,root=graph_data();owner=stack['objects']['arch/arm64/mm/init.o'];owner['elf_sections_and_symbols']=owner['elf_sections_and_symbols'].replace('0000000000000100 4 FUNC LOCAL','0000000000000104 4 FUNC LOCAL')
        return p.verify_guarded(raw,target,nm,stack,root)
    rejected('selected direct helper ELF address mismatch rejected',wrong_helper)
    for name,call,wanted in cases:
        try:actual=call()is not False
        except(ValueError,KeyError,TypeError):actual=False
        if actual is not wanted:raise AssertionError(name)
    p.require(len(cases)==E_COUNTS['variants'],'exact new overlay/type case count')
    return dict(COUNTS,C_variants=C_COUNTS['variants'],C_assertions=C_COUNTS['assertions'],evidence_variants=E_COUNTS['variants'],evidence_assertions=E_COUNTS['assertions'])
