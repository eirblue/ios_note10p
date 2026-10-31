"""Only new v58 PC-owned relocation cases and actual AArch64 closure inspection."""
import argparse
import hashlib
import json
import os
import re
import shutil
import struct
import subprocess
from pathlib import Path
from relocation_trial_instructions import classify
from test_relocation_trial_instructions import run_cases as instruction_cases

ROOT=Path(__file__).resolve().parents[2]
CORE={'runtime_relocation.c':'dc51d22fce4c8e0d566d6158f53aa3d512a65954541e4ea4201c5878cb17e448',
      'runtime_relocation.h':'2956336fbec371636acb62a4fc51aae451e74a65bdf4595b12e80c3be8ca9037'}
PAYLOAD='7a573eb6d2f5efc87bd5c85af130ea854eb4bad8370d17a4247e54f9593a836a'
MACHO='b2c80dea6762dc8a388563a099810b48a9157533c6b9c9db8889c29bdddf8d3f'
CASES=('real-overlap','injected-transient-mismatch','nonoverlap','minimum-offset',
 'adjacent-small','last-block-small','request-capacity','adt-capacity','command-capacity',
 'reserved-capacity','occupied-capacity','window-capacity','backup-capacity','result-capacity',
 'null-window','null-backup','null-result','null-request','window-pointer-overflow',
 'backup-pointer-overflow','adt-pointer-overflow','window-backup-alias','window-result-alias',
 'window-request-alias','window-adt-alias','backup-command-alias','backup-reserved-alias',
 'range-input-alias','adt-command-alias','nonsynthetic-adt','malformed-adt','zero-image',
 'unaligned-image','unaligned-base','invalid-window','entry-before-image','reserved-conflict',
 'range-count','virtual-overflow','command-too-long','invalid-command','adt-capacity-overflow',
 'window-capacity-overflow','result-capacity-overflow','reserved-capacity-overflow',
 'occupied-capacity-overflow','request-capacity-overflow','empty-adt')

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):p.write_text(json.dumps(v,indent=2)+'\n',encoding='utf-8')

def elf(path):
    raw=path.read_bytes()
    if raw[:6]!=b'\x7fELF\x02\x01' or struct.unpack_from('<HH',raw,16)!=(1,183):raise ValueError('AArch64 ET_REL required')
    at=struct.unpack_from('<Q',raw,40)[0];stride,count,names=struct.unpack_from('<HHH',raw,58)
    if stride!=64 or not 0<count<4096 or at+count*64>len(raw):raise ValueError('section table')
    sections=[struct.unpack_from('<IIQQQQIIQQ',raw,at+i*64) for i in range(count)]
    def data(s):
        if s[4]+s[5]>len(raw):raise ValueError('section bounds')
        return raw[s[4]:s[4]+s[5]]
    def string(table,offset):
        end=table.find(b'\0',offset)
        if offset>=len(table) or end<0:raise ValueError('string bounds')
        return table[offset:end].decode('ascii')
    undefined=[];symbols=[]
    for s in sections:
        if s[2]&1 and s[5]:raise ValueError('writable state section')
        if s[1]==2:
            if s[9]!=24 or s[5]%24:raise ValueError('symbol table')
            st=data(sections[s[6]])
            for off in range(0,s[5],24):
                name,info,other,index,value,size=struct.unpack_from('<IBBHQQ',data(s),off)
                name=string(st,name)
                if name:
                    symbols.append(name)
                    if index==0:undefined.append(name)
    if any('fixture' in n.lower() or 'observe' in n.lower() for n in symbols):raise ValueError('fixture symbol in production')
    return sorted(undefined)

RESUME_RECEIPT_SHA='c5dd693635dd91d0a753b0bf01a72b02d6f6e478ba87179b9db60f287beebfee'

def resume_production(previous,out,tools,common):
    """Read-only admission of the one failed local attempt, never a CI shortcut."""
    if any(os.environ.get(k) for k in ('CI','GITHUB_ACTIONS','GITHUB_RUN_ID')):raise ValueError('production resume forbidden in CI')
    base=ROOT/'note10/private/device-test/v58-xnu-relocation-trial-20261031'
    if previous.resolve()!= (base/'private-temp/trial-01').resolve():raise ValueError('only retained exact failed attempt may resume')
    receipt_path=base/'FOCUSED-OPERATOR-RECEIPT.json'
    if sha(receipt_path)!=RESUME_RECEIPT_SHA:raise ValueError('original failed receipt changed')
    receipt=json.loads(receipt_path.read_text())
    if receipt['exit_code']!=1 or receipt['suite']['native_cases_executed']!=0 or receipt['suite']['native_executable_created'] is not False:raise ValueError('resume scope differs')
    inventory=receipt['suite']['partial_output_files']
    files={item['path'].replace('\\','/'):item for item in inventory}
    actual={p.relative_to(previous).as_posix() for p in previous.rglob('*') if p.is_file()}
    if actual!=set(files):raise ValueError('retained attempt inventory differs')
    for name,item in files.items():
        p=previous/name
        if p.is_symlink() or p.stat().st_size!=item['length'] or sha(p)!=item['sha256']:raise ValueError('retained attempt bytes changed')
    for name in ('runtime_relocation.c','runtime_relocation.h','runtime_relocation_trial.c','runtime_relocation_trial.h','relocation_trial_fixture.h','relocation_trial_native.c'):
        if sha(previous/'source'/name)!=sha(out/'source'/name):raise ValueError('unchanged compiled C/h required')
    tool_proof=receipt['provenance']['toolchain']
    for key,path in tools.items():
        matches=[v for v in tool_proof.values() if Path(v['path']).resolve()==path.resolve()]
        if len(matches)!=1 or sha(path)!=matches[0]['sha256']:raise ValueError('original tool binding differs: '+key)
    commands=json.loads((previous/'commands.json').read_text())
    oldsrc=previous/'source'
    oldcommon=common[:-1]+[str(oldsrc)]
    expected=[[str(tools[k]),'--version'] for k in ('cc','objdump','linker')]
    for stem in ('runtime_relocation','runtime_relocation_trial'):
        expected.append(list(map(str,[tools['cc'],'--target=aarch64-none-elf',*oldcommon,'-c',oldsrc/(stem+'.c'),'-o',previous/(stem+'.o')])))
    expected.extend([list(map(str,[tools['linker'],'-r',previous/'runtime_relocation_trial.o',previous/'runtime_relocation.o','-o',previous/'production-closed.o'])),
      list(map(str,[tools['objdump'],'-d',previous/'production-closed.o']))])
    if [entry['command'] for entry in commands]!=expected:raise ValueError('original exact production command template differs')
    for name in ('runtime_relocation.o','runtime_relocation_trial.o','production-closed.o','production-disassembly.log','cc-version.log','objdump-version.log','linker-version.log','runtime_relocation-compile.log','runtime_relocation_trial-compile.log','link.log'):
        shutil.copyfile(previous/name,out/name)
    shutil.copyfile(previous/'commands.json',out/'reused-production-commands.json')
    proof={'reused_compilation':True,'prior_failed_receipt_sha256':RESUME_RECEIPT_SHA,'prior_output':str(previous),
      'original_source_hashes':{name:files['source/'+name]['sha256'] for name in ('runtime_relocation.c','runtime_relocation.h','runtime_relocation_trial.c','runtime_relocation_trial.h')},
      'current_python_checker_sha256':sha(Path(__file__)),'prior_python_checker_sha256':files['source/test_relocation_trial.py']['sha256'],
      'retained_inventory':inventory,'native_cases_previously_executed':0,'whole_ci_accepted':False}
    write(out/'production-reuse.json',proof)
    return proof

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--input',type=Path,required=True,help='Verified native artifact directory containing MachO')
    ap.add_argument('--payload',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--cc',default='clang-14');ap.add_argument('--objdump',default='llvm-objdump-14')
    ap.add_argument('--linker',default='ld.lld-14')
    ap.add_argument('--resume-production-proof',type=Path,help='Local exact failed trial-01 only; forbidden in CI')
    a=ap.parse_args()
    out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
    macho=a.input/'note10-experimental.macho'
    if sha(macho)!=MACHO or macho.stat().st_size!=18522008 or sha(a.payload)!=PAYLOAD or a.payload.stat().st_size!=19578880:raise ValueError('pinned real data mismatch')
    sources=[ROOT/'note10/xnu26'/n for n in (*CORE,'runtime_relocation_trial.c','runtime_relocation_trial.h')]
    sources += [ROOT/'note10/device_test'/n for n in ('relocation_trial_native.c','relocation_trial_fixture.h','test_relocation_trial.py','relocation_trial_input.py','relocation_trial_instructions.py','test_relocation_trial_instructions.py')]
    sources += [ROOT/'.github/workflows/note10-relocation-trial.yml']
    for name,digest in CORE.items():
        if sha(ROOT/'note10/xnu26'/name)!=digest:raise ValueError('immutable planner changed')
    src=out/'source';src.mkdir()
    for p in sources:shutil.copyfile(p,src/p.name)
    commands=[]
    def run(cmd,name):
        commands.append({'command':list(map(str,cmd)),'log':name})
        write(out/'commands.json',commands)
        result=subprocess.run(list(map(str,cmd)),stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        (out/name).write_bytes(result.stdout)
        if result.returncode:raise RuntimeError(f'{name}: exit {result.returncode}')
        return result.stdout.decode('utf-8',errors='strict')
    common=['-std=c11','-O2','-Wall','-Wextra','-Werror','-ffreestanding','-fno-builtin','-fno-stack-protector','-I',str(src)]
    classifier_cases=instruction_cases()
    write(out/'instruction-fixtures.json',{'fixture_only':True,'cases':classifier_cases,'whole_ci_accepted':False})
    toolchain={};tools={}
    for name,tool in (('cc',a.cc),('objdump',a.objdump),('linker',a.linker)):
        resolved=Path(shutil.which(tool) or tool).resolve(strict=True);tools[name]=resolved
        toolchain[name]={'path':str(resolved),'sha256':sha(resolved)}
    production={'reused_compilation':False,'native_cases_previously_executed':0}
    if a.resume_production_proof:
        production=resume_production(a.resume_production_proof.resolve(),out,tools,common)
    else:
        for name,tool in (('cc',a.cc),('objdump',a.objdump),('linker',a.linker)):
            run([tool,'--version'],name+'-version.log')
        for stem in ('runtime_relocation','runtime_relocation_trial'):
            run([a.cc,'--target=aarch64-none-elf',*common,'-c',src/(stem+'.c'),'-o',out/(stem+'.o')],stem+'-compile.log')
        run([a.linker,'-r',out/'runtime_relocation_trial.o',out/'runtime_relocation.o','-o',out/'production-closed.o'],'link.log')
        run([a.objdump,'-d',out/'production-closed.o'],'production-disassembly.log')
    if elf(out/'runtime_relocation_trial.o')!=['n10_rt_plan']:raise ValueError('individual trial dependency closure')
    if elf(out/'runtime_relocation.o'):raise ValueError('planner unresolved dependency')
    if elf(out/'production-closed.o'):raise ValueError('component unresolved dependency')
    classification=classify((out/'production-disassembly.log').read_text(encoding='utf-8'))
    write(out/'production-instruction-proof.json',classification)
    exe=out/('trial.exe' if __import__('os').name=='nt' else 'trial')
    run([a.cc,*common,'-include',src/'relocation_trial_fixture.h',src/'runtime_relocation_trial.c',src/'runtime_relocation.c',src/'relocation_trial_native.c','-o',exe],'native-compile.log')
    cases=[]
    for i,name in enumerate(CASES):
        text=run([exe,str(i),a.payload.resolve(),out],f'case-{i:02d}.log')
        if not re.fullmatch(rf'CASE\|{i}\|status=-?\d+\|observed=[01]\|bytes=\d+\|restored=\d+\r?\n',text):raise ValueError('strict case transcript')
        cases.append({'id':i,'name':name,'passed':True,'log_sha256':sha(out/f'case-{i:02d}.log')})
    comparisons=[]
    # Read-only independent verifier: never uses trial backup as sole oracle.
    payload=a.payload.read_bytes()
    for i in (0,1):
        before=(out/f'case{i}-before.bin').read_bytes();after=(out/f'case{i}-after.bin').read_bytes()
        transient=(out/f'case{i}-transient.bin').read_bytes();backup=(out/f'case{i}-backup.bin').read_bytes()
        if len(before)!=0x22b0000 or before[:len(payload)]!=payload or before[len(payload):]!=b'\x69'*(len(before)-len(payload)) or after!=before or transient!=payload or backup!=before:raise ValueError('independent byte oracle')
        comparisons.append({'case':i,'before_sha256':hashlib.sha256(before).hexdigest(),'after_sha256':hashlib.sha256(after).hexdigest(),
          'transient_sha256':hashlib.sha256(transient).hexdigest(),'backup_sha256':hashlib.sha256(backup).hexdigest(),
          'full_prefix_size':len(before),'transient_size':len(transient),'byte_comparison_passed':True})
    result={'schema':1,'version':'v58','passed':True,'fixture_only':True,'synthetic_adt':True,
      'hardware_verified':False,'physical_memory_or_hardware_accessed':False,'xnu_executed':False,
      'whole_ci_accepted':False,'ci_context':{k:os.environ.get(k) for k in ('GITHUB_RUN_ID','GITHUB_RUN_ATTEMPT','GITHUB_SHA','GITHUB_JOB','GITHUB_WORKFLOW_REF')},'cases':cases,'independent_comparisons':comparisons,
      'production_aarch64_executed':False,'production_closure_passed':True,'production_compile':production,'instruction_fixture_cases':classifier_cases,'instruction_classification':classification,
      'toolchain':toolchain,'source_sha256':{p.relative_to(ROOT).as_posix():sha(p) for p in sources},
      'payload_sha256':sha(a.payload),'macho_sha256':sha(macho),'kernel_offset':0x1004000,'affected_prefix':0x22b0000}
    result['files_sha256']={p.relative_to(out).as_posix():sha(p) for p in sorted(out.rglob('*')) if p.is_file()}
    write(out/'result.json',result)

if __name__=='__main__':main()
