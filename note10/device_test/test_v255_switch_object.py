"""Four new synthetic provider/actual-CLI predicates; no native execution."""
from copy import deepcopy
import struct


def synthetic(defined=True):
    names=b'\0.text\0.rela.text\0.symtab\0.strtab\0.shstrtab\0';strings=b'\0__switch_to\0cpu_switch_to\0';body=struct.pack('<II',0x94000000,0xd65f03c0)
    symbols=bytes(24)+struct.pack('<IBBHQQ',1,0x12 if defined else 0x10,0,1 if defined else 0,0,8 if defined else 0)+struct.pack('<IBBHQQ',13,0x10,0,0,0,0)
    chunks=[b'',body,struct.pack('<QQq',0,(2<<32)|283,0),symbols,strings,names];raw=bytearray(64);sections=[bytes(64)]
    specs=[(1,1,6,0,0,4,0),(7,4,0,3,1,8,24),(18,2,0,4,1,8,24),(26,3,0,0,0,1,0),(34,3,0,0,0,1,0)]
    for chunk,(name,kind,flags,link,info,align,entsize)in zip(chunks[1:],specs):
        raw.extend(bytes((-len(raw))%align));at=len(raw);raw.extend(chunk);sections.append(struct.pack('<IIQQQQIIQQ',name,kind,flags,0,at,len(chunk),link,info,align,entsize))
    raw.extend(bytes((-len(raw))%8));table=len(raw);raw.extend(b''.join(sections));raw[:16]=b'\x7fELF\x02\x01\x01'+bytes(9);struct.pack_into('<HHIQQQIHHHHHH',raw,16,1,183,1,0,0,table,0,64,0,0,64,6,5)
    return bytes(raw)


def run(adapter,codec,producer_source,public_sources):
    completed=[];tu='/fixture/source/arch/arm64/kernel/process.c';source='struct task_struct *__switch_to(struct task_struct *prev, struct task_struct *next) { return cpu_switch_to(prev,next); }\n';usage=tu+':1:__switch_to\t16\tstatic\n'
    def valid():
        body,info=adapter.extract(synthetic());proof=adapter.verify(body,info,usage,tu,source)
        return proof['fresh_defined_provider_captured']is proof['cpu_switch_to_direct_boundary_proven']is True and proof['fresh_provider_static_SU_bytes']==16 and proof['cross_object_link_resolution_proven']is False
    def undefined():
        try:adapter.extract(synthetic(False))
        except ValueError:return True
        return False
    def wrong_index():
        body,info=adapter.extract(synthetic());info=deepcopy(info);info['relocations'][0]['symbol_index']=1
        try:adapter.verify(body,info,usage,tu,source)
        except ValueError:return True
        return False
    def actual_wire():
        context=dict(schema=adapter.SCHEMA+'-public-input-v1',source_head='1'*40,source_sha256=public_sources,fixture=dict(passed=True,groups=1,variants=4,assertions=4,result_sha256='2'*64));encoded=codec.encode_wire(producer_source,context)
        return codec.boundary_decode(producer_source,encoded)==context
    cases=(('defined_provider_TU_SU_backend',valid),('undefined_provider_rejected',undefined),('backend_relocation_index_mismatch_rejected',wrong_index),('actual_new_CLI_base64_roundtrip',actual_wire))
    try:
        for name,predicate in cases:
            if predicate()is not True:raise ValueError('new predicate failed: '+name)
            completed.append(name)
    except BaseException as error:
        error.fixture_progress=dict(groups=1,variants=4,assertions=4,completed_variants=len(completed),completed_assertions=len(completed),case_names=completed);raise
    return dict(groups=1,variants=4,assertions=4,completed_variants=4,completed_assertions=4,case_names=completed)
