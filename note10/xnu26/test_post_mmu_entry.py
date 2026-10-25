"""Execute source-linked XNU through VA return to the first arm_init call.

The MMU/cache/TLB transition is NOT executed. Physical/virtual views use
software aliases checked against actual startup tables in the PC model.
"""
import argparse
from functools import partial
import json
from pathlib import Path
from post_mmu_model import continue_entry
from test_materialized_entry import run
from test_linked_entry import run_case
from verify_experimental_artifact import verify

KERNEL_SHA256='8584aec16c94eeb16b078cb18807f5b93b923c989c19afd78a778745d851454b'


def test(directory,adapter,output,profile=None):
    if verify(directory)['sha256']!=KERNEL_SHA256:
        raise ValueError('This first-call contract requires the reviewed source-built kernel')
    result=run(directory,adapter,output,profile,continuation=continue_entry)
    for case in result['cases']:
        if case['continuation']['stop']['target_symbols']!=['_static_if_init']:
            raise ValueError('The reviewed first arm_init call boundary changed')
    result['negative_checks_completed']=False
    (output/'result.json').write_text(json.dumps(result,indent=2))
    negatives=[]
    for fault,expected in (('mapping','VA alias differs from bootstrap translation'),
                           ('argument','C entry received wrong virtual boot_args'),
                           ('af','Access flag not set'),('pxn','EL1 execute permission denied'),
                           ('readonly','EL1 write to read-only mapping'),
                           ('table-pxn','EL1 execute permission denied'),
                           ('table-readonly','EL1 write to read-only mapping'),
                           ('wxn','EL1 execute permission denied'),('epd','Translation walk disabled'),
                           ('el0-writable','EL1 execute permission denied')):
        try:
            run_case(directory,0x80000000,transfer_elf=adapter,handoff_bundle=output/'case-0',
                     continuation=partial(continue_entry,fault=fault))
        except ValueError as error:
            if not str(error).startswith(expected):raise
            negatives.append({'fault':fault,'rejected':True,'reason':expected})
        else:raise ValueError('Fault was not rejected: '+fault)
    result.update(negative_checks_completed=True,negative_checks=negatives,
                  mmu_enable_executed=False,c_initialization_completed=False,
                  scope='Actual XNU entry/arm_init prologue instructions; software VA aliases and synthetic system registers; before first C call')
    (output/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('kernel-build','adapter','output'):parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--observed-profile',type=Path)
    args=parser.parse_args();result=test(args.kernel_build,args.adapter,args.output,args.observed_profile)
    print(json.dumps({'passed':True,'cases':len(result['cases']),
                      'post_boundary_instructions':[c['continuation']['instructions'] for c in result['cases']],
                      'targets':[c['continuation']['stop']['target_symbols'] for c in result['cases']],
                      'negative_checks':len(result['negative_checks']),'hardware_verified':False,
                      'mmu_enable_executed':False}))
