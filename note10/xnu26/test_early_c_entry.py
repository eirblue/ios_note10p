"""Run real XNU early C to CPU-topology boundary with synthetic clock inputs."""
import argparse
from functools import partial
import json
from pathlib import Path
from boot_adt import Node,encode
from early_c_fixture import clock_tree
from handoff_bundle import build
from post_mmu_model import continue_entry,ModelPanic
from test_linked_entry import run_case
from test_materialized_entry import run
from test_post_mmu_entry import KERNEL_SHA256
from verify_experimental_artifact import verify


def test(directory,adapter,output,profile=None):
    if verify(directory)['sha256']!=KERNEL_SHA256:raise ValueError('Reviewed native kernel required')
    continuation=partial(continue_entry,c_phase='topology-return',register_inputs={'cntkctl_el1':0},
                         expected_timebase=26000000)
    result=run(directory,adapter,output,profile,continuation=continuation,model_tree=clock_tree(cpu_id=0))
    result.update(negative_checks_completed=False,c_initialization_completed=False,
                  scope='Actual XNU early-C/state/topology parser; explicit single-CPU/clock/register fixtures; after topology parser return')
    (output/'result.json').write_text(json.dumps(result,indent=2))
    for case in result['cases']:
        observed=case['continuation']
        if observed['stop']['reason']!='after_cpu_topology_return':raise ValueError('Unexpected early-C boundary')
        if observed['final_explicit_registers']!={'cntkctl_el1':0x4f}:
            raise ValueError('Unexpected explicit timer fixture result')
    plan=json.loads((output/'case-0/handoff.json').read_text())['plan']
    missing=output/'missing-clock.adt'
    missing.write_bytes(encode(Node('device-tree',children=[Node('chosen',{'boot-args':b'debug=0x14e\0'})])))
    build(directory,adapter,missing,plan,output/'missing-clock')
    try:
        run_case(directory,0x80000000,transfer_elf=adapter,handoff_bundle=output/'missing-clock',
                 continuation=partial(continue_entry,c_phase='topology',register_inputs={'cntkctl_el1':0}))
    except ModelPanic as error:
        if 'invalid bit index' not in error.report['format']:raise
        (output/'missing-clock-panic.json').write_text(json.dumps(error.report,indent=2))
    else:raise ValueError('Missing PE clock did not enter actual panic path')
    absent_cpu=output/'missing-cpu-reg.adt';absent_cpu.write_bytes(encode(clock_tree()))
    build(directory,adapter,absent_cpu,plan,output/'missing-cpu-reg')
    try:
        run_case(directory,0x80000000,transfer_elf=adapter,handoff_bundle=output/'missing-cpu-reg',
                 continuation=partial(continue_entry,c_phase='topology-return',register_inputs={'cntkctl_el1':0}))
    except ModelPanic as error:
        if 'Missing mandatory property' not in error.report['format']:raise
        (output/'missing-cpu-panic.json').write_text(json.dumps(error.report,indent=2))
    else:raise ValueError('Missing CPU ID did not enter actual panic path')
    try:
        # Inject stale event bits at the C checkpoint to test the final state
        # verifier. The separate adapter tests refuse these bits before entry.
        run_case(directory,0x80000000,transfer_elf=adapter,handoff_bundle=output/'case-0',
                 continuation=partial(continue_entry,c_phase='topology',
                     register_inputs={'cntkctl_el1':0x80},expected_timebase=26000000))
    except ValueError as error:
        if not str(error).startswith('Unexpected event-stream index'):raise
    else:raise ValueError('Stale event index was not rejected')
    result.update(negative_checks_completed=True,
                  negative_checks=['missing-clock-actual-panic','missing-cpu-reg-actual-panic','stale-event-state-rejected'],
                  fixture_frequency_hz=26000000,mmu_enable_executed=False,
                  platform_hardware_initialized=False)
    (output/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('kernel-build','adapter','output'):parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--observed-profile',type=Path)
    args=parser.parse_args();result=test(args.kernel_build,args.adapter,args.output,args.observed_profile)
    print(json.dumps({'passed':True,'cases':len(result['cases']),
                      'instructions':[c['continuation']['instructions'] for c in result['cases']],
                      'early_c_state':result['cases'][0]['continuation']['early_c_state'],
                      'negative_checks':result['negative_checks'],'hardware_verified':False}))
