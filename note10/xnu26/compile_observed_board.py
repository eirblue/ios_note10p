"""Compile real XNU board components with hash-bound Linux cache/page inputs.

Uses foreign VMAPPLE generated headers for dependency diagnostics only.
Does not build or deploy a full observed-hardware XNU kernel.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
from observed_profile import ROOT,load
from probe_kernel_headers import context


def compile_profile(profile_path):
    if not profile_path.resolve().is_relative_to((ROOT/'note10/private').resolve()):
        raise ValueError('Private observed profile required')
    profile=load(profile_path)
    reference,_,_,compiler,common,_=context()
    out=profile_path.parent/'compiled'
    if out.exists():raise ValueError('Refusing mixed observed compile results')
    trees={}
    for name,folder,key in (('board','xnu26-board','files'),('irq','xnu26-irq','component_sha256'),
                            ('bootstrap','xnu26-bootstrap','files')):
        folder=ROOT/'note10/private'/folder
        report=json.loads((folder/'patch-result.json').read_text())
        tree=folder/'patched-inputs'
        for path,digest in report[key].items():
            if hashlib.sha256((tree/path).read_bytes()).hexdigest()!=digest:
                raise ValueError('Changed prepared XNU source input: '+path)
        trees[name]=tree
    out.mkdir()
    prefix=['-I',str(trees['board']/'pexpert'),'-I',str(trees['board']/'osfmk'),
            '-I',str(trees['irq']/'osfmk'),'-I',str(trees['bootstrap']/'pexpert'),
            '-I',str(trees['irq']/'pexpert/arm')]
    target=json.loads((ROOT/'note10/target.json').read_text())
    meta=ROOT/target['research_directory']/'generated-headers-vmapple/RELEASE_ARM64_VMAPPLE/pexpert/RELEASE/meta_features.h'
    flags=[str(compiler),*prefix,*[f for f in common if f!='-fsyntax-only'],
           '-DARM64_BOARD_CONFIG_EXYNOS9825','-DPEXPERT_KERNEL_PRIVATE',
           '-include',str(meta),'-include',str(profile_path.parent/'observed-board.h'),
           '-O2','-mstrict-align','-mno-implicit-float','-fno-stack-protector','-Wall','-Wextra','-Werror']
    unit=out/'observed-asserts.c'
    assertions=''.join(f'_Static_assert({name} == {value}, "{name}");\n' for name,value in
                       (('MAX_CPUS',1),('ARM_PGSHIFT',14),('MMU_I_CLINE',profile['defines']['N10_ICACHE_LINE_LOG2']),
                        ('MMU_CLINE',profile['defines']['N10_DCACHE_LINE_LOG2']),
                        ('MAX_L2_CLINE',profile['defines']['N10_MAX_CACHE_LINE_LOG2'])))
    unit.write_text('#include <machine/machine_routines.h>\n#include <mach/vm_types.h>\n'+assertions,encoding='utf-8')
    sources=[unit,*[ROOT/'note10/xnu26'/n for n in ('pe_note10_bootstrap.c','pe_note10_irq.c')]]
    records=[]
    for source in sources:
        obj=out/(source.stem+'.o');command=[*flags,'-c',str(source),'-o',str(obj)]
        result=subprocess.run(command,capture_output=True,timeout=90)
        obj.with_suffix('.log').write_bytes(result.stdout+result.stderr)
        if result.returncode:raise RuntimeError('Observed board compile failed; see '+str(obj.with_suffix('.log')))
        assembly=subprocess.check_output([str(compiler.parent/'llvm-objdump.exe'),'--disassemble','--no-show-raw-insn',str(obj)]).decode()
        if source!=unit:
            instructions=re.findall(r'^\s*[0-9a-f]+:\s+([a-z].*)$',assembly,re.M)
            if not instructions or any(re.search(r'\b(?:v|q|d|s|h|b)\d+\b',i.split('<')[0]) for i in instructions):
                raise ValueError('Missing instructions or unexpected vector/FP use')
        obj.with_suffix('.asm').write_text(assembly,encoding='utf-8')
        records.append({'source':source.name,'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
                        'object_sha256':hashlib.sha256(obj.read_bytes()).hexdigest(),'command':command})
    report={'passed':True,'objects':records,'source_commit':reference['commit'],'defines':profile['defines'],
            'observed_profile_sha256':hashlib.sha256(profile_path.read_bytes()).hexdigest(),
            'register_inputs_observed_in_linux':True,'foreign_generated_config':'RELEASE_ARM64_VMAPPLE',
            'whole_kernel_build':False,'xnu_executed':False,'deployment_ready':False,'device_operations':[]}
    (out/'result.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('profile',type=Path)
    r=compile_profile(parser.parse_args().profile)
    print(json.dumps({'passed':r['passed'],'objects':len(r['objects']),'whole_kernel_build':False}))
