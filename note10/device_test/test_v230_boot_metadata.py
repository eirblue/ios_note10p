"""One actual C current-layout group, with the retained Python ABI byte oracle."""
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
HERE=Path(__file__).resolve().parent
XNU=HERE.parent/'xnu26'


def command(output,compiler):
    return [compiler,'-std=c11','-O2','-Wall','-Wextra','-Werror','-I',str(HERE),'-I',str(XNU),
        *[str(HERE/name)for name in ('v230_boot_metadata.c','v230_boot_metadata_fixture.c','native_parcel_core.c')],
        str(XNU/'runtime_relocation.c'),'-o',str(Path(output)/'boot-metadata-fixture.exe')]


def evidence_cases():
    import v230_native_prepare as producer
    symbols='\n'.join(name+' A '+format(value,'x')for name,value in producer.METADATA_ABS.items())+'\n'
    symbols+='\n'.join(name+' T '+format(4096+index*4,'x')+' 4'for index,name in enumerate(
        ('n230_project_metadata','n10_rt_validate_adt','n10_rt_serialize_boot_args','n10_rt_serialize_record')))+'\n'
    if producer.metadata_symbols(symbols)!=producer.METADATA_ABS:raise AssertionError('computed ABS type values must not be parsed as R-array sizes')
    try:producer.metadata_symbols(symbols.replace('n230_size_placement A 60','n230_size_placement A 61'))
    except ValueError:pass
    else:raise AssertionError('wrong target placement size must fail closed')
    elf='  [ 1] .text PROGBITS 0000000000000000 000040 000004 00 AX 0 0 4\n  1: 0000000000000000 4 FUNC GLOBAL DEFAULT 1 n230_project_metadata\n'
    usage='v230_boot_metadata.c:1:1:n230_project_metadata\t16\tstatic\n'
    actual=producer.metadata_object_evidence(elf,usage)
    if actual['writable_section_bytes']!=0 or actual['frames']['n230_project_metadata']['bytes']!=16:raise AssertionError('same-object static frames and no writable storage required')
    try:producer.metadata_object_evidence(elf+'  [ 2] .bss NOBITS 0000000000000000 000044 000008 00 WA 0 0 8\n',usage)
    except ValueError:pass
    else:raise AssertionError('new writable data/BSS must fail closed')


def run(output,compiler_argv):
    output=Path(output)
    if compiler_argv!=command(output,compiler_argv[0]):raise ValueError('exact new C fixture argv required')
    if str(XNU)not in sys.path:sys.path.insert(0,str(XNU))
    from boot_contract import encode_boot_args
    env=dict(os.environ);env['PATH']=str(Path(compiler_argv[0]).parent)+os.pathsep+env.get('PATH','')
    (output/'COMPILE-STARTED.json').write_text(json.dumps(dict(argv=compiler_argv,attempt=1))+'\n',encoding='utf-8')
    with (output/'compile.log').open('xb')as log:
        subprocess.run(compiler_argv,stdout=log,stderr=subprocess.STDOUT,env=env,check=True,timeout=120)
    (output/'COMPILE-COMPLETED.json').write_text('{"returncode":0}\n',encoding='ascii')
    argv=[str(output/'boot-metadata-fixture.exe')]
    (output/'C-FIXTURE-STARTED.json').write_text(json.dumps(dict(argv=argv,attempt=1))+'\n',encoding='utf-8')
    done=subprocess.run(argv,capture_output=True,env=env,check=False,timeout=120)
    (output/'fixture.stdout').write_bytes(done.stdout);(output/'fixture.stderr').write_bytes(done.stderr)
    (output/'C-FIXTURE-COMPLETED.json').write_text(json.dumps(dict(returncode=done.returncode))+'\n',encoding='ascii')
    done.check_returncode();actual=json.loads(done.stdout)
    if set(actual)!={'success','groups','variants','assertions'}or (actual['groups'],actual['variants'],actual['assertions'])!=(1,15,36)or len(actual['success'])!=2:
        raise ValueError('actual C projection batch counts differ')
    for row in actual['success']:
        expected=encode_boot_args(virtual_base=row['virtual_base'],physical_base=row['physical_base'],memory_size=33554432,
            top_of_kernel=row['top'],device_tree_pointer=row['dt_virtual'],device_tree_length=56,memory_size_actual=33554432)
        if bytes.fromhex(row['args_hex'])!=expected:raise AssertionError('projection bytes differ from retained real-ABI Python oracle')
        record=struct.pack('<8sII6Q',b'N10XFER1',1,64,row['args_pa'],row['entry_pa'],0,0,0,0)
        if bytes.fromhex(row['record_hex'])!=record:raise AssertionError('current-layout transfer record bytes differ')
    evidence_cases()
    return dict(groups=1,variants=19,assertions=44,C_assertions=36,oracle_assertions=4,evidence_assertions=4)
