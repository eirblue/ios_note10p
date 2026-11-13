"""One new actual-C OF shim, existing byte oracle and new compile-gate group."""
import json
import os
from pathlib import Path
import subprocess
import sys
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]


def command(output,compiler):
    return [compiler,'-std=c11','-O2','-Wall','-Wextra','-Werror','-DN233_HOST_FIXTURE','-I',str(HERE),
        str(HERE/'v233_cpu_node_consistency.c'),str(HERE/'v233_cpu_node_fixture.c'),'-o',str(Path(output)/'cpu-node-fixture.exe')]


def oracle_cases(records):
    path=str(ROOT/'note10/xnu26')
    if path not in sys.path:sys.path.insert(0,path)
    import linux_cpu_adt as consumer
    import test_linux_cpu_adt as byte_oracle
    count=0
    for row in records:
        raw=byte_oracle.fdt(byte_oracle.tree([byte_oracle.cpu(row['reg'],row['cells'])],cells=row['cells']))
        fragment,metadata=consumer.translate(raw,require_full_handoff=False,include_firmware_timebase=False)
        if fragment!=byte_oracle.expected_cpu_fragment([row['reg']]):raise AssertionError('actual C affinity must match existing LE32 serializer')
        if any(metadata[k]is not False for k in ('complete_boot_tree','handoff_ready','cpu_execution_state_known','memory_ownership','xnu_executed')):
            raise AssertionError('byte agreement conveys no authority')
        count+=1
    if count!=3:raise AssertionError('three actual C success records required')
    return count,count*2


def evidence_cases():
    import v233_native_prepare as producer
    raw=b'#include "v231_cpu_observation.c"\n'
    expected='63af69692862ca2ca2d2e0e93d5cdb51a009be4af6c7e380c69eed489c74da9e'
    changed=producer.prepare_owner(raw,expected)
    if changed!=raw+b'#include "v233_cpu_node_consistency.c"\n' or b'n233_capture_cpu_node_consistency('in changed:
        raise AssertionError('include only; no runtime hook')
    try:producer.prepare_owner(raw+b'\n',expected)
    except ValueError:pass
    else:raise AssertionError('mutated owner preimage must reject')
    if producer.node_config(producer.NODE_CONFIG)!=producer.NODE_CONFIG:raise AssertionError('same observed configuration required')
    try:producer.node_config(dict(producer.NODE_CONFIG,OF_DYNAMIC='y'))
    except ValueError:pass
    else:raise AssertionError('do not change config to force static OF proof')
    tu='/ci/work/source/arch/arm64/mm/init.c'
    command=('cmd_arch/arm64/mm/init.o := clang-14 -fstack-usage -fno-strict-aliasing -o arch/arm64/mm/init.o -c '+tu+'\nsource_arch/arm64/mm/init.o := '+tu+'\n').encode()
    symbols=''.join(name+' A '+format(value,'x')+'\n'for name,value in producer.NODE_ABS.items())
    symbols+='n226_source_pool b 1000 c000\nn233_node_storage B '+format(0x1000+43576,'x')+' 20\n'
    sections='  [ 1] .text PROGBITS 0000000000020000 000040 000300 00 AX 0 0 4\n  [ 2] .bss NOBITS 0000000000001000 000340 00c000 00 WA 0 0 4096\n'
    usage=''
    for index,name in enumerate(producer.NODE_FUNCTIONS):
        address=0x20000+index*0x80;binding='GLOBAL'if index==0 else'LOCAL';kind='T'if index==0 else't'
        symbols+=name+' '+kind+' '+format(address,'x')+' 40\n'
        sections+=f'  {index+1}: {address:016x} 64 FUNC {binding} DEFAULT 1 {name}\n'
        usage+=tu+':26:'+name+'\t'+str(64 if index==0 else 0)+'\tstatic\n'
    sections+='  4: 0000000000001000 49152 OBJECT LOCAL DEFAULT 2 n226_source_pool\n'
    sections+=f'  5: {0x1000+43576:016x} 32 OBJECT GLOBAL DEFAULT 2 n233_node_storage\n'
    result=producer.node_target(symbols,usage,sections,command)
    if result['record_bytes']!=32 or result['runtime_callers']!=0 or result['whole_owner_writable_bytes_claimed']is not False:
        raise AssertionError('new alias/type proof only')
    for args in ((symbols,usage.replace(tu,'/ci/work/wrong.c'),sections,command),
                 (symbols,usage.replace('\tstatic','\tdynamic'),sections,command),
                 (symbols.replace('n233_node_storage B '+format(0x1000+43576,'x'),'n233_node_storage B '+format(0x1000+43584,'x')),usage,sections,command),
                 (symbols,usage,sections.replace('64 FUNC GLOBAL','60 FUNC GLOBAL'),command)):
        try:producer.node_target(*args)
        except ValueError:pass
        else:raise AssertionError('wrong TU/frame/alias/extent must reject')
    return 9,9


def run(output,compiler_argv):
    output=Path(output)
    if compiler_argv!=command(output,compiler_argv[0]):raise ValueError('exact new C node fixture argv required')
    env=dict(os.environ);env['PATH']=str(Path(compiler_argv[0]).parent)+os.pathsep+env.get('PATH','')
    (output/'COMPILE-STARTED.json').write_text(json.dumps(dict(argv=compiler_argv,attempt=1))+'\n',encoding='utf-8')
    with (output/'compile.log').open('xb')as log:subprocess.run(compiler_argv,stdout=log,stderr=subprocess.STDOUT,env=env,check=True,timeout=120)
    (output/'COMPILE-COMPLETED.json').write_text('{"returncode":0}\n',encoding='ascii')
    argv=[str(output/'cpu-node-fixture.exe')]
    (output/'C-FIXTURE-STARTED.json').write_text(json.dumps(dict(argv=argv,attempt=1))+'\n',encoding='utf-8')
    done=subprocess.run(argv,capture_output=True,env=env,check=False,timeout=120)
    (output/'fixture.stdout').write_bytes(done.stdout);(output/'fixture.stderr').write_bytes(done.stderr)
    (output/'C-FIXTURE-COMPLETED.json').write_text(json.dumps(dict(returncode=done.returncode))+'\n',encoding='ascii');done.check_returncode()
    actual=json.loads(done.stdout)
    if set(actual)!={'groups','variants','assertions','valid_records'}or (actual['groups'],actual['variants'],actual['assertions'])!=(1,29,142):
        raise ValueError('actual C node counts differ')
    oracle_variants,oracle_assertions=oracle_cases(actual['valid_records']);evidence_variants,evidence_assertions=evidence_cases()
    return dict(groups=1,variants=29+oracle_variants+evidence_variants,assertions=142+oracle_assertions+evidence_assertions,
        C_variants=29,C_assertions=142,oracle_variants=oracle_variants,oracle_assertions=oracle_assertions,evidence_variants=evidence_variants,evidence_assertions=evidence_assertions)
