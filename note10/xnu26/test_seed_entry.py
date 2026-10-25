"""Execute actual PE seed copy/erasure with public, predictable PC inputs only."""
import argparse
from functools import partial
import json
from pathlib import Path
from boot_adt import encode
from early_c_fixture import clock_tree,single_cpu_plan
from handoff_bundle import ROOT,build
from post_mmu_model import continue_entry,ModelPanic
from seed_fixture import PC_SEED,SeedResultError
from test_linked_entry import run_case
from test_vm_entry import REGISTERS,CACHES
from test_post_mmu_entry import KERNEL_SHA256
from verify_experimental_artifact import verify


def test(directory,adapter,output):
    if not output.resolve().is_relative_to((ROOT/'note10/private').resolve()) or output.exists():
        raise ValueError('Fresh private output required')
    checked=verify(directory)
    if checked['sha256']!=KERNEL_SHA256:raise ValueError('Reviewed native kernel required')
    plan=single_cpu_plan(directory);ram=plan['ram']['start']
    output.mkdir(parents=True,exist_ok=False)
    def execute(name,seed):
        adt=output/(name+'.adt');adt.write_bytes(encode(clock_tree(cpu_id=0,dram=(ram,0x40000000),seed=seed)))
        bundle=output/name;build(directory,adapter,adt,plan,bundle)
        return run_case(directory,ram,transfer_elf=adapter,handoff_bundle=bundle,cpu_model='max',
                        continuation=partial(continue_entry,c_phase='seed-return',register_inputs=REGISTERS,
                                             expected_timebase=26000000,cache_inputs=CACHES))
    positive=execute('predictable-pc-seed',PC_SEED)['continuation']
    result={'passed':False,'instructions':positive['instructions'],'state':positive['early_c_state']['seed_consumption'],
            'hardware_verified':False,'hardware_seed_ready':False,'deployment_ready':False,'device_operations':[],
            'vm_initialization_entered':True,'vm_initialization_completed':False,'negative_checks_completed':False,
            'scope':'Actual PE seed copy and exact ADT erasure; public predictable PC fixtures, not hardware entropy'}
    (output/'result.json').write_text(json.dumps(result,indent=2))
    try:execute('missing-seed',None)
    except ModelPanic as error:
        if 'no random seed' not in error.report['format']:raise
        (output/'missing-seed-panic.json').write_text(json.dumps(error.report,indent=2))
    else:raise ValueError('Missing seed did not enter actual panic path')
    try:execute('zero-seed',bytes(256))
    except SeedResultError as error:
        if error.report['request']!=256 or error.report['returned']!=0:raise
        result['zero_seed_actual_return']=error.report
    else:raise ValueError('All-zero seed was silently accepted')
    result.update(passed=True,negative_checks_completed=True,
                  negative_checks=['missing-seed-actual-panic','all-zero-seed-actual-return-zero'],
                  zero_seed_caller_panic_executed=False)
    (output/'result.json').write_text(json.dumps(result,indent=2))
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('kernel-build','adapter','output'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();print(json.dumps(test(args.kernel_build,args.adapter,args.output)))
