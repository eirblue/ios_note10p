"""Fresh uninstrumented ET_EXEC compile and four production A64 model cases."""
import argparse
import importlib.metadata
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import zipfile

from relocation_trial_aarch64_model import (ROOT,CASES,COUNT_LIMIT,TIMEOUT_SECONDS,IMAGE,OFFSET,AFFECTED,
    PAYLOAD_SHA,ROW,require,sha,write,private_path,elf_image,verify_report,classify,wheel_metadata)
from test_relocation_trial_wheel_metadata import run_cases as metadata_cases

PRODUCTION={
 'note10/xnu26/runtime_relocation.c':'dc51d22fce4c8e0d566d6158f53aa3d512a65954541e4ea4201c5878cb17e448',
 'note10/xnu26/runtime_relocation.h':'2956336fbec371636acb62a4fc51aae451e74a65bdf4595b12e80c3be8ca9037',
 'note10/xnu26/runtime_relocation_trial.c':'3295a1d005c38b4ab213b69c56705a6caec453916a11d54e3287434b4a3853b9',
 'note10/xnu26/runtime_relocation_trial.h':'7b76597c2436029fdc3c259ec9d1998047d2b5e4c8ed33f9d47adf52be03eaf2'}
NEW_SOURCES=('note10/device_test/relocation_trial_aarch64_abi.c','note10/device_test/relocation_trial_aarch64_model.py',
 'note10/device_test/test_relocation_trial_aarch64.py','note10/device_test/test_relocation_trial_wheel_metadata.py','.github/workflows/note10-relocation-aarch64.yml')
SHARED=('note10/device_test/relocation_trial_input.py','note10/device_test/relocation_trial_instructions.py')
LINKER_SCRIPT='''ENTRY(n10_rt_trial)
PHDRS { code PT_LOAD FLAGS(5); ro PT_LOAD FLAGS(4); }
SECTIONS {
 . = 0x10000000;
 .text : { *(.text .text.*) } :code
 . = ALIGN(0x1000);
 .rodata : { *(.rodata .rodata.*) } :ro
 .n10_abi : { KEEP(*(.n10_abi)) } :ro
 .data : { *(.data .data.*) } :ro
 .bss : { *(.bss .bss.*) *(COMMON) } :ro
 /DISCARD/ : { *(.comment) *(.note*) *(.eh_frame*) *(.llvm_addrsig) }
}
'''

def disassembly_binding(text,image,reports):
    classification=classify(text);rows={}
    for line in text.splitlines():
        match=ROW.fullmatch(line)
        if match:rows[int(match[1],16)]={'mnemonic':match[3],'operands':match[4]}
    trial=image['symbols']['n10_rt_trial'];start=trial['value'];end=start+trial['size']
    copy=image['symbols'].get('copy')
    for report in reports:
        if report['case'] not in CASES[:2]:continue
        state=report['observer'];first=state['first_tail_write_pc'];restore=state['restore_start_pc'];read=state['first_tail_read_pc']
        restore_in_copy=bool(copy and copy['info']==2 and copy['flags']&4 and copy['size']>0 and copy['value']<=restore<copy['value']+copy['size'])
        require(start<=first<end and start<=read<end and (start<=restore<end or restore_in_copy) and
          rows[first]['mnemonic']=='strb' and rows[restore]['mnemonic']=='strb' and
          rows[read]['mnemonic'] in {'ldr','ldrb','ldur','ldurb','ldp'},'actual hook PCs bind to target backward-store/compare/restore instructions')
    return {'classification':classification,'trial_function_address':start,'trial_function_size':trial['size'],
      'observed_boundary_instructions':{report['case']:{key:{'pc':report['observer'][key],**rows[report['observer'][key]]}
        for key in ('first_tail_write_pc','first_tail_read_pc','restore_start_pc')} for report in reports if report['case'] in CASES[:2]}}

def verify_bundle(root,payload):
    """Independent artifact/data verification only; never replay the emulator."""
    result=json.loads((root/'result.json').read_text());require(result['passed'] is True and result['whole_ci_accepted'] is False,'completed PC model report')
    require(result['case_inventory']==list(CASES) and len(result['cases'])==4,'exact four target case inventory')
    image=elf_image(root/'production.elf');require(image['sha256']==result['elf_sha256'] and image['abi']==result['abi'],'independent final ELF and target ABI')
    reports=[];blobs=set()
    for name,record in zip(CASES,result['cases']):
        require(record['case']==name and record['report']=='cases/'+name+'/result.json','exact case report location')
        path=root/record['report'];require(sha(path)==record['sha256'],'case observation report hash')
        report=json.loads(path.read_text());require(report['case']==name,'case report identity')
        blobs |= verify_report(root,report,payload,image);reports.append(report)
    blob_entries=list((root/'blobs').iterdir())
    require(all(p.is_file() and not p.is_symlink() for p in blob_entries) and
      {p.relative_to(root).as_posix() for p in blob_entries}==blobs,'no missing/extra/nonregular compressed observation blobs')
    binding=disassembly_binding((root/'production-disassembly.log').read_text(),image,reports)
    require(binding==result['instruction_binding'],'independent disassembly boundary binding')
    require(result['payload_sha256']==PAYLOAD_SHA and result['payload_size']==IMAGE and result['kernel_offset']==OFFSET and result['affected_prefix']==AFFECTED,'real input and actual geometry')
    require(result['hardware_verified'] is False and result['physical_memory_or_hardware_accessed'] is False and result['xnu_executed'] is False and
      result['production_aarch64_model_executed'] is True,'PC-emulated production execution only')
    return {'case_count':4,'blob_count':len(blobs),'elf_sha256':image['sha256'],'independent_full_byte_comparisons':True,'emulator_replayed':False}

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--payload',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True);ap.add_argument('--dependency-wheels',type=Path,required=True)
    ap.add_argument('--cc',default='clang-14');ap.add_argument('--objdump',default='llvm-objdump-14');ap.add_argument('--linker',default='ld.lld-14')
    a=ap.parse_args();out=private_path(a.output);out.mkdir(parents=True,exist_ok=False)
    require(importlib.metadata.version('unicorn')=='2.1.4','exact Unicorn dependency')
    require(a.payload.stat().st_size==IMAGE and sha(a.payload)==PAYLOAD_SHA,'exact real payload')
    sources=list(PRODUCTION)+list(NEW_SOURCES)+list(SHARED)
    for name,h in PRODUCTION.items():require(sha(ROOT/name)==h,'immutable production source changed')
    source=out/'source';source.mkdir()
    for name in sources:shutil.copyfile(ROOT/name,source/Path(name).name)
    wheels=list(a.dependency_wheels.glob('*.whl'));require(len(wheels)==1 and wheels[0].name.startswith('unicorn-2.1.4-'),'exact one pinned Unicorn wheel')
    dependency=out/'dependencies';dependency.mkdir();wheel=dependency/wheels[0].name;shutil.copyfile(wheels[0],wheel)
    metadata_fixtures=metadata_cases()
    write(out/'wheel-metadata-fixtures.json',{'fixture_only':True,'cases':metadata_fixtures,'whole_ci_accepted':False})
    with zipfile.ZipFile(wheel) as z:
        metadata=[n for n in z.namelist() if n.endswith('.dist-info/METADATA')];require(len(metadata)==1,'wheel metadata')
        wheel_metadata(z.read(metadata[0]))
    commands=[]
    def run(cmd,name,timeout=120):
        entry={'command':list(map(str,cmd)),'log':name,'timeout_seconds':timeout,'completed':False};commands.append(entry);write(out/'commands.json',commands)
        began=time.monotonic()
        try:completed=subprocess.run(entry['command'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=timeout)
        except subprocess.TimeoutExpired as error:
            (out/name).write_bytes(error.stdout or b'');entry['timed_out']=True;write(out/'commands.json',commands);raise
        (out/name).write_bytes(completed.stdout);entry.update({'completed':True,'returncode':completed.returncode,'elapsed_seconds':time.monotonic()-began});write(out/'commands.json',commands)
        require(completed.returncode==0,'model command failed: '+name)
    tools={}
    for key,tool in (('cc',a.cc),('objdump',a.objdump),('linker',a.linker)):
        path=Path(shutil.which(tool) or tool).resolve(strict=True);tools[key]={'path':str(path),'sha256':sha(path)};run([tool,'--version'],key+'-version.log')
    flags=['--target=aarch64-none-elf','-std=c11','-O2','-Wall','-Wextra','-Werror','-ffreestanding','-fno-builtin','-fno-stack-protector','-I',source]
    for stem in ('runtime_relocation','runtime_relocation_trial','relocation_trial_aarch64_abi'):
        run([a.cc,*flags,'-c',source/(stem+'.c'),'-o',out/(stem+'.o')],stem+'-compile.log')
    script=out/'production.ld';script.write_text(LINKER_SCRIPT,encoding='utf-8',newline='\n')
    run([a.linker,'-static','--no-undefined','-z','max-page-size=4096','-T',script,out/'runtime_relocation_trial.o',out/'runtime_relocation.o',out/'relocation_trial_aarch64_abi.o','-o',out/'production.elf'],'link.log')
    image=elf_image(out/'production.elf')
    run([a.objdump,'-d',out/'production.elf'],'production-disassembly.log');classify((out/'production-disassembly.log').read_text())
    write(out/'abi.json',image['abi'])
    (out/'cases').mkdir();reports=[]
    for name in CASES:
        run([sys.executable,ROOT/'note10/device_test/relocation_trial_aarch64_model.py','--elf',out/'production.elf','--payload',a.payload.resolve(),
          '--case',name,'--output',out/'cases'/name,'--blobs',out/'blobs'],name+'.log',timeout=TIMEOUT_SECONDS+30)
        path=out/'cases'/name/'result.json';reports.append(json.loads(path.read_text()))
    binding=disassembly_binding((out/'production-disassembly.log').read_text(),image,reports)
    report={'schema':1,'version':'v59','passed':True,'whole_ci_accepted':False,'case_inventory':list(CASES),
      'cases':[{'case':name,'report':'cases/'+name+'/result.json','sha256':sha(out/'cases'/name/'result.json')} for name in CASES],
      'elf_sha256':image['sha256'],'abi':image['abi'],'instruction_binding':binding,'toolchain':tools,
      'source_sha256':{name:sha(ROOT/name) for name in sources},'wheel':{'file':'dependencies/'+wheel.name,'sha256':sha(wheel)},
      'metadata_fixture_cases':metadata_fixtures,
      'payload_sha256':PAYLOAD_SHA,'payload_size':IMAGE,'kernel_offset':OFFSET,'affected_prefix':AFFECTED,
      'production_aarch64_model_executed':True,'hardware_verified':False,'physical_memory_or_hardware_accessed':False,'xnu_executed':False,
      'model_memory_only':True,'synthetic_adt':True,
      'ci_context':{k:os.environ.get(k) for k in ('GITHUB_RUN_ID','GITHUB_RUN_ATTEMPT','GITHUB_SHA','GITHUB_JOB')},
      'configured_bounds':{'instruction_ceiling_per_case':COUNT_LIMIT,'emulator_timeout_seconds_per_case':TIMEOUT_SECONDS,'process_timeout_seconds_per_case':TIMEOUT_SECONDS+30,'executed_instruction_count':None},
      'limits':'PC Unicorn FP/AdvSIMD assumption only; no actual EL1 readiness, hardware ownership or XNU execution'}
    report['files_sha256']={p.relative_to(out).as_posix():sha(p) for p in out.rglob('*') if p.is_file()}
    write(out/'result.json',report);verification=verify_bundle(out,a.payload.read_bytes());write(out/'independent-byte-verification.json',verification)

if __name__=='__main__':main()
