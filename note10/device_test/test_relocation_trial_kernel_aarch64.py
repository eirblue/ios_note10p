"""New kernel-option subset compile driver; reuse the sole A64 model executor."""
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
from relocation_trial_aarch64_model import (ROOT,CASES,IMAGE,OFFSET,AFFECTED,PAYLOAD_SHA,TIMEOUT_SECONDS,COUNT_LIMIT,
    require,sha,write,private_path,elf_image,verify_report,wheel_metadata)
from test_relocation_trial_aarch64 import PRODUCTION,LINKER_SCRIPT,disassembly_binding
from relocation_trial_kernel_profile import PROFILE_ID,kernel_profile,gpr_only
from test_relocation_trial_kernel_profile import run_cases,CASE_INVENTORY

PUBLIC_SOURCES=('note10/device_test/relocation_trial_aarch64_model.py','note10/device_test/relocation_trial_kernel_profile.py',
 'note10/device_test/relocation_trial_kernel_profile.json','note10/device_test/test_relocation_trial_kernel_profile.py',
 'note10/device_test/test_relocation_trial_kernel_aarch64.py','.github/workflows/note10-relocation-kernel-profile.yml')
ABI_ORACLE='note10/device_test/relocation_trial_aarch64_abi.c'
SHARED=('note10/device_test/test_relocation_trial_aarch64.py','note10/device_test/test_relocation_trial_wheel_metadata.py',
 'note10/device_test/test_relocation_trial_aarch64_binding.py','note10/device_test/relocation_trial_instructions.py','note10/device_test/relocation_trial_input.py')
BASE_FLAGS=('--target=aarch64-none-elf','-std=c11','-Wall','-Wextra','-Werror','-ffreestanding','-fno-builtin')

def verify_kernel_bundle(root,payload,expected_profile):
    settings=kernel_profile(expected_profile);result=json.loads((root/'result.json').read_text())
    require(result['passed'] is True and result['whole_ci_accepted'] is False and result['codegen_profile']==settings,'explicit source/caller kernel profile bundle')
    flags=result['compile_flags']
    require(flags[:-2]==list(BASE_FLAGS)+settings['selected_flags'] and flags[-2]=='-I','exact selected profile and base compiler options; no O2/implicit fixture flags')
    commands=json.loads((root/'commands.json').read_text());source_prefix=flags[-1].replace('\\','/').rstrip('/')
    require(source_prefix.endswith('/source'),'recorded caller-owned source snapshot')
    for stem in ('runtime_relocation','runtime_relocation_trial','relocation_trial_aarch64_abi'):
        records=[c for c in commands if c['log']==stem+'-compile.log'];require(len(records)==1,'unique actual production compile command')
        record=records[0];command=record['command']
        require(record['completed'] is True and record['returncode']==0 and command[1:1+len(flags)]==flags and
          command[1+len(flags):2+len(flags)]==['-c'] and command[-2]=='-o' and len(command)==len(flags)+5 and
          command[-3].replace('\\','/')==source_prefix+'/'+stem+'.c' and
          command[-1].replace('\\','/')==source_prefix.rsplit('/',1)[0]+'/'+stem+'.o','actual compiled objects bound to exact profile/source command')
    require(result['case_inventory']==list(CASES) and len(result['cases'])==4 and
      [c['name'] for c in result['profile_fixture_cases']]==list(CASE_INVENTORY) and all(c['passed'] is True for c in result['profile_fixture_cases']),'exact new profile fixtures/four cases')
    image=elf_image(root/'production.elf');require(image['sha256']==result['elf_sha256'] and image['abi']==result['abi'],'actual final closed ELF and ABI')
    reports=[];blobs=set()
    for name,record in zip(CASES,result['cases']):
        require(record['case']==name and record['report']=='cases/'+name+'/result.json','canonical target case path')
        path=root/record['report'];require(sha(path)==record['sha256'],'case report hash')
        report=json.loads(path.read_text());require(report['case']==name,'case identity')
        blobs |= verify_report(root,report,payload,image,expected_profile=expected_profile);reports.append(report)
    actual=list((root/'blobs').iterdir());require(all(p.is_file() and not p.is_symlink() for p in actual) and
      {p.relative_to(root).as_posix() for p in actual}==blobs,'exact bounded compressed observation inventory')
    text=(root/'production-disassembly.log').read_text()
    require(gpr_only(text)==result['gpr_analysis'] and disassembly_binding(text,image,reports)==result['instruction_binding'],'independent GPR-only and actual boundary-PC bindings')
    require(result['payload_sha256']==PAYLOAD_SHA and result['payload_size']==IMAGE and result['kernel_offset']==OFFSET and result['affected_prefix']==AFFECTED,'real geometry/input')
    require(result['hardware_verified'] is False and result['actual_kernel_integration'] is False and result['physical_memory_or_hardware_accessed'] is False and
      result['xnu_executed'] is False and result['production_aarch64_model_executed'] is True,'PC subset-profile scope')
    return {'case_count':4,'profile_fixture_count':len(CASE_INVENTORY),'blob_count':len(blobs),'full_byte_comparisons':True,'emulator_replayed':False,'codegen_profile_id':expected_profile}

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--payload',type=Path,required=True);ap.add_argument('--dependency-wheels',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True);ap.add_argument('--profile',choices=[PROFILE_ID],required=True)
    ap.add_argument('--cc',default='clang-14');ap.add_argument('--objdump',default='llvm-objdump-14');ap.add_argument('--linker',default='ld.lld-14');a=ap.parse_args()
    settings=kernel_profile(a.profile);out=private_path(a.output);out.mkdir(parents=True,exist_ok=False)
    require(importlib.metadata.version('unicorn')=='2.1.4' and a.payload.stat().st_size==IMAGE and sha(a.payload)==PAYLOAD_SHA,'pinned runtime and real payload')
    for name,h in PRODUCTION.items():require(sha(ROOT/name)==h,'immutable production source')
    sources=list(PUBLIC_SOURCES)+list(PRODUCTION)+[ABI_ORACLE]+list(SHARED);source=out/'source';source.mkdir()
    for name in sources:shutil.copyfile(ROOT/name,source/Path(name).name)
    fixtures=run_cases();write(out/'profile-fixtures.json',{'fixture_only':True,'synthetic_only':True,'cases':fixtures,'whole_ci_accepted':False})
    wheels=list(a.dependency_wheels.glob('*.whl'));require(len(wheels)==1 and wheels[0].name.startswith('unicorn-2.1.4-'),'one exact pinned Unicorn wheel')
    (out/'dependencies').mkdir();wheel=out/'dependencies'/wheels[0].name;shutil.copyfile(wheels[0],wheel)
    with zipfile.ZipFile(wheel) as z:
        metadata=[n for n in z.namelist() if n.endswith('.dist-info/METADATA')];require(len(metadata)==1,'unique wheel metadata');wheel_metadata(z.read(metadata[0]))
    commands=[]
    def run(cmd,name,timeout=120):
        record={'command':list(map(str,cmd)),'log':name,'timeout_seconds':timeout,'completed':False};commands.append(record);write(out/'commands.json',commands);began=time.monotonic()
        try:done=subprocess.run(record['command'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=timeout)
        except subprocess.TimeoutExpired as error:(out/name).write_bytes(error.stdout or b'');record['timed_out']=True;write(out/'commands.json',commands);raise
        (out/name).write_bytes(done.stdout);record.update({'completed':True,'returncode':done.returncode,'elapsed_seconds':time.monotonic()-began});write(out/'commands.json',commands);require(done.returncode==0,'profile command failed: '+name)
    tools={}
    for key,tool in (('cc',a.cc),('objdump',a.objdump),('linker',a.linker)):
        path=Path(shutil.which(tool) or tool).resolve(strict=True);tools[key]={'path':str(path),'sha256':sha(path)};run([tool,'--version'],key+'-version.log')
    flags=[*BASE_FLAGS,*settings['selected_flags'],'-I',source]
    for stem in ('runtime_relocation','runtime_relocation_trial','relocation_trial_aarch64_abi'):
        run([a.cc,*flags,'-c',source/(stem+'.c'),'-o',out/(stem+'.o')],stem+'-compile.log')
    script=out/'production.ld';script.write_text(LINKER_SCRIPT,encoding='utf-8',newline='\n')
    run([a.linker,'-static','--no-undefined','-z','max-page-size=4096','-T',script,out/'runtime_relocation_trial.o',out/'runtime_relocation.o',out/'relocation_trial_aarch64_abi.o','-o',out/'production.elf'],'link.log')
    image=elf_image(out/'production.elf');write(out/'abi.json',image['abi'])
    run([a.objdump,'-d',out/'production.elf'],'production-disassembly.log');analysis=gpr_only((out/'production-disassembly.log').read_text())
    (out/'cases').mkdir();reports=[]
    for name in CASES:
        run([sys.executable,ROOT/'note10/device_test/relocation_trial_aarch64_model.py','--profile',a.profile,'--elf',out/'production.elf','--payload',a.payload.resolve(),
          '--case',name,'--output',out/'cases'/name,'--blobs',out/'blobs'],name+'.log',timeout=TIMEOUT_SECONDS+30)
        reports.append(json.loads((out/'cases'/name/'result.json').read_text()))
    result={'schema':1,'version':'v60','passed':True,'whole_ci_accepted':False,'codegen_profile':settings,'gpr_analysis':analysis,'profile_fixture_cases':fixtures,
      'case_inventory':list(CASES),'cases':[{'case':name,'report':'cases/'+name+'/result.json','sha256':sha(out/'cases'/name/'result.json')} for name in CASES],
      'elf_sha256':image['sha256'],'abi':image['abi'],'instruction_binding':disassembly_binding((out/'production-disassembly.log').read_text(),image,reports),
      'source_sha256':{name:sha(ROOT/name) for name in sources},'toolchain':tools,'compile_flags':[str(x) for x in flags],
      'wheel':{'file':'dependencies/'+wheel.name,'sha256':sha(wheel)},'payload_sha256':PAYLOAD_SHA,'payload_size':IMAGE,'kernel_offset':OFFSET,'affected_prefix':AFFECTED,
      'hardware_verified':False,'actual_kernel_integration':False,'physical_memory_or_hardware_accessed':False,'xnu_executed':False,'production_aarch64_model_executed':True,
      'ci_context':{k:os.environ.get(k) for k in ('GITHUB_RUN_ID','GITHUB_RUN_ATTEMPT','GITHUB_SHA','GITHUB_JOB')},
      'configured_bounds':{'instruction_ceiling_per_case':COUNT_LIMIT,'timeout_seconds_per_case':TIMEOUT_SECONDS,'process_timeout_seconds_per_case':TIMEOUT_SECONDS+30,'executed_instruction_count':None},
      'limits':'Observed kernel-option subset only. PC emulation, no actual Linux TU/kernel build, EL1/FPU hardware readiness, fixed-x18, physical writer or XNU execution.'}
    result['files_sha256']={p.relative_to(out).as_posix():sha(p) for p in out.rglob('*') if p.is_file()};write(out/'result.json',result)
    write(out/'independent-byte-verification.json',verify_kernel_bundle(out,a.payload.read_bytes(),expected_profile=PROFILE_ID))

if __name__=='__main__':main()
