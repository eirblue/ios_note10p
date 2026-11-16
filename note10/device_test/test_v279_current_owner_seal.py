"""One new seam/target-refusal conjunction; no retained fixture replay."""
from pathlib import Path
import v279_native_prepare as producer

def rejected(fn,*args):
    try:fn(*args)
    except (ValueError,KeyError):return True
    return False

def predicate():
    here=Path(__file__).resolve().parent
    raw=(here/'v226_source_stream_kernel.c').read_bytes()
    changed=producer.owner_overlay(raw)
    include=b'#include "v279_current_owner_seal.inc"\n'
    assert changed.count(producer.CALL)==1 and changed.count(include)==1
    assert changed.replace(include,b'',1).replace(producer.CALL,b'',1)==raw
    assert changed.index(b'if(n217_kernel_state.spent)return -EALREADY;')<changed.index(b'memset(n226_source_pool,0,sizeof(n226_source_pool));')<changed.index(producer.CALL)<changed.index(b' done:')
    assert producer.CALL.startswith(b'    if(!error)error=n278_seal_once(')
    assert rejected(producer.owner_overlay,raw.replace(producer.SEAM,b'absent'))
    assert rejected(producer.owner_overlay,raw.replace(producer.SEAM,producer.SEAM*2))
    assert producer.SEAL_TARGET=='arch/arm64/mm/v278_current_owner_seal.o'and producer.OWNER_TARGET=='arch/arm64/mm/init.o'
    assert producer.KBUILD==b'obj-$(CONFIG_NOTE10_V210_NATIVE_PREPARE) += v278_current_owner_seal.o\n'
    assert (producer.NAMED_CAP,producer.OUTLINED_CAP,producer.EXTENT_CAP)==(13,30,43)
    assert rejected(producer.storage,'n279_size_seal A 4b0\n','','','')
    assert rejected(producer.own_frame,'n278_seal_once',[(4096,'sub','sp, sp, #16'),(4100,'ret','')],{},0,False)
    record=dict(name='foreign_helper',address=8192,bytes=4,offset=0,kind='T',ordinal=0)
    edge=dict(mnemonic='bl',unresolved=False,target=8192,address=4096,resolved_records=[record],resolved_symbols=['foreign_helper'])
    assert rejected(producer.edge_target,edge,{})
    record=dict(record,name='n210_request_valid',offset=4)
    assert rejected(producer.edge_target,{**edge,'resolved_records':[record],'resolved_symbols':['n210_request_valid']},{})
    return dict(passed=True,groups=1,variants=1,assertions=1)
