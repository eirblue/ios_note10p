"""Five new backend/base/protocol predicates; synthetic native input only."""
from copy import deepcopy
import struct


def native():
    names=b'\0.text\0.rela.text\0.symtab\0.strtab\0.shstrtab\0';strings=b'\0cpu_switch_to\0external_symbol\0';body=struct.pack('<III',0xd280000a|(0x1230<<5),0x8b0a0008,0xd65f03c0);symbols=bytes(24)+struct.pack('<IBBHQQ',1,0x12,0,1,0,len(body))+struct.pack('<IBBHQQ',15,0x10,0,0,0,0);chunks=[body,b'',symbols,strings,names];specs=[(1,1,6,0,0,4,0),(7,4,0,3,1,8,24),(18,2,0,4,1,8,24),(26,3,0,0,0,1,0),(34,3,0,0,0,1,0)];raw=bytearray(64);sections=[bytes(64)]
    for chunk,(name,kind,flags,link,info,align,ents)in zip(chunks,specs):
        raw.extend(bytes((-len(raw))%align));at=len(raw);raw.extend(chunk);sections.append(struct.pack('<IIQQQQIIQQ',name,kind,flags,0,at,len(chunk),link,info,align,ents))
    raw.extend(bytes((-len(raw))%8));table=len(raw);raw.extend(b''.join(sections));raw[:16]=b'\x7fELF\x02\x01\x01'+bytes(9);struct.pack_into('<HHIQQQIHHHHHH',raw,16,1,183,1,0,0,table,0,64,0,0,64,6,5);return bytes(raw)


def arguments(adapter):
    body,info=adapter.extract(native());base='/fixture/source/';entry='cmd_arch/arm64/kernel/entry.o := clang-14 -D__ASSEMBLY__ -c -o arch/arm64/kernel/.tmp_entry.o '+base+'arch/arm64/kernel/entry.S ; true\nsource_arch/arm64/kernel/entry.o := '+base+'arch/arm64/kernel/entry.S\n';offsets='cmd_arch/arm64/kernel/asm-offsets.s := clang-14 -DANDROID_VERSION=110000 -DANDROID_MAJOR_VERSION=r -S -o arch/arm64/kernel/asm-offsets.s '+base+'arch/arm64/kernel/asm-offsets.c\nsource_arch/arm64/kernel/asm-offsets.s := '+base+'arch/arm64/kernel/asm-offsets.c\n';header='#define THREAD_CPU_CONTEXT 4656 /* offsetof */\n';assembly='.ascii "->THREAD_CPU_CONTEXT #4656 offsetof(struct task_struct, thread.cpu_context)"\n'
    return [body,info,entry,offsets,header,assembly,'ENTRY(cpu_switch_to)\n mov x10, #THREAD_CPU_CONTEXT','DEFINE(THREAD_CPU_CONTEXT, offsetof(struct task_struct, thread.cpu_context));','struct cpu_context { unsigned long x19; };']


def run(adapter,codec,producer_source,public_sources):
    completed=[]
    def valid():
        p=adapter.prove(*arguments(adapter));return p['generated_context_base_immediate_binding_proven']is True and p['generated_THREAD_CPU_CONTEXT']==4656 and p['compiler_static_SU_bytes']is None and p['assembly_C_compiler_SU_claimed']is p['switch_resume_contract_proven']is False
    def reject(kind):
        args=arguments(adapter)
        if kind=='undefined':args[1]=deepcopy(args[1]);args[1]['provider'].update(type=0,section=0)
        elif kind=='offset':args[4]=args[4].replace('4656','4664');args[5]=args[5].replace('4656','4664')
        else:args[1]=deepcopy(args[1]);args[1]['relocations'].append(dict(offset=0,type=282,symbol_index=2,target=args[1]['symbols'][2],addend=0))
        try:adapter.prove(*args)
        except ValueError:return True
        return False
    def wire():
        context=dict(schema=adapter.SCHEMA+'-public-input-v1',source_head='1'*40,source_sha256=public_sources,fixture=dict(passed=True,groups=1,variants=5,assertions=5,result_sha256='2'*64));encoded=codec.encode_wire(producer_source,context);return codec.boundary_decode(producer_source,encoded)==context
    cases=(('defined_backend_generated_base_no_SU_claim',valid),('undefined_backend_rejected',lambda:reject('undefined')),('generated_base_immediate_mismatch_rejected',lambda:reject('offset')),('selected_relocation_rejected',lambda:reject('relocation')),('actual_new_CLI_base64_roundtrip',wire))
    try:
        for name,predicate in cases:
            if predicate()is not True:raise ValueError('new backend predicate failed: '+name)
            completed.append(name)
    except BaseException as error:
        error.fixture_progress=dict(groups=1,variants=5,assertions=5,completed_variants=len(completed),completed_assertions=len(completed),case_names=completed);raise
    return dict(groups=1,variants=5,assertions=5,completed_variants=5,completed_assertions=5,case_names=completed,host_processes=0,selected_body_reads=0,fresh_object_reads=0)
