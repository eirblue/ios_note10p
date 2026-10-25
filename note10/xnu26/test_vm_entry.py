"""Execute real CPU initialization up to arm_vm_init with explicit PC fixtures."""
import argparse
from functools import partial
import json
from pathlib import Path
from boot_adt import encode
from early_c_fixture import clock_tree
from handoff_bundle import ROOT,build
from post_mmu_model import continue_entry,ModelPanic,ModelExecutionError
from test_linked_entry import run_case
from test_post_mmu_entry import KERNEL_SHA256
from verify_experimental_artifact import verify

REGISTERS={'cntkctl_el1':0,'cntvct_el0':26000000,'mpidr_el1':0x80000000,
           'clidr_el1':0x82000023,'ctr_el0':0x84448004,
           'id_aa64dfr0_el1':0}
CACHES={0:0x700fe01a,1:0x200fe01a,2:0x707fe07a}


def test(directory,adapter,bundle,output):
    if not output.resolve().is_relative_to((ROOT/'note10/private').resolve()) or output.exists():
        raise ValueError('Fresh private output required')
    if verify(directory)['sha256']!=KERNEL_SHA256:raise ValueError('Reviewed native kernel required')
    plan=json.loads((bundle/'handoff.json').read_text())['plan']
    if plan['ram']!={'start':0x80000000,'size':0x40000000}:
        raise ValueError('This PC fixture requires declared 1GiB at 0x80000000')
    output.mkdir(parents=True,exist_ok=False)
    adt=output/'model.adt';adt.write_bytes(encode(clock_tree(cpu_id=0,dram=(0x80000000,0x40000000))))
    build(directory,adapter,adt,plan,output/'bundle')
    def execute(source,cache):
        return run_case(directory,0x80000000,transfer_elf=adapter,handoff_bundle=source,cpu_model='max',
                        continuation=partial(continue_entry,c_phase='vm',register_inputs=REGISTERS,
                                             expected_timebase=26000000,cache_inputs=cache))
    positive=execute(output/'bundle',CACHES)
    state=positive['continuation']
    if state['stop']['reason']!='before_arm_vm_init':raise ValueError('Wrong VM boundary')
    result={'passed':False,'negative_checks_completed':False,'instructions':state['instructions'],
            'state':state['early_c_state'],'synthetic_cpu_model':'max',
            'synthetic_registers':REGISTERS,'synthetic_caches':CACHES,
            'hardware_verified':False,'physical_reservation_verified':False,'deployment_ready':False,
            'device_operations':[],'vm_initialization_executed':False,
            'distinct_instruction_decodes':state['distinct_instruction_decodes'],
            'scope':'Real linked CPU/cache/startup code; explicit single-CPU/DRAM/cache/debug-disabled/frozen-counter PC fixtures'}
    (output/'result.json').write_text(json.dumps(result,indent=2))
    absent=output/'missing-dram.adt';absent.write_bytes(encode(clock_tree(cpu_id=0)))
    build(directory,adapter,absent,plan,output/'missing-dram')
    try:execute(output/'missing-dram',CACHES)
    except ModelPanic as error:
        if "Unable to find 'dram-base'" not in error.report['format']:raise
        (output/'missing-dram-panic.json').write_text(json.dumps(error.report,indent=2))
    else:raise ValueError('Missing DRAM did not enter actual panic path')
    try:execute(output/'bundle',{key:value for key,value in CACHES.items() if key!=2})
    except ModelExecutionError as error:
        if error.report['error']!='Missing explicit CCSIDR fixture for selector 2':raise
        result['missing_cache_rejection']={'error':error.report['error'],'instructions':error.report['instructions']}
    else:raise ValueError('Missing cache register fixture was silently accepted')
    result.update(passed=True,negative_checks_completed=True,
                  negative_checks=['missing-dram-actual-panic','missing-cache-selector-rejected'])
    (output/'result.json').write_text(json.dumps(result,indent=2))
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('kernel-build','adapter','handoff-bundle','output'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();result=test(args.kernel_build,args.adapter,args.handoff_bundle,args.output)
    print(json.dumps(result))
