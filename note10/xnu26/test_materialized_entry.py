"""Run actual XNU/adapter instructions from materialized PC bundle buffers."""
import argparse
import hashlib
import json
from pathlib import Path
from boot_adt import Node,encode
from handoff_bundle import ROOT,PAGE,BLOCK,build,materialize_kernel
from observed_profile import load as load_observations,check_tcr
from test_linked_entry import run_case
from verify_experimental_artifact import verify


def run(directory,adapter,output,profile=None):
    if not output.resolve().is_relative_to((ROOT/'note10/private').resolve()):raise ValueError('Private model output required')
    if output.exists():raise ValueError('Refusing existing materialization model output')
    checked=verify(directory)
    raw=(directory/'note10-experimental.macho').read_bytes()
    base,kernel=materialize_kernel(raw,checked['segments'])
    output.mkdir(parents=True,exist_ok=False)
    # Explicit parser fixture only: no fabricated GIC handoff/ownership.
    adt=output/'model.adt';adt.write_bytes(encode(Node('device-tree',children=[Node('chosen',{'boot-args':b'debug=0x14e\0'})])))
    observations=load_observations(profile) if profile else None
    cases=[]
    for index,ram in enumerate((0x80000000,0x100000000)):
        virtual=0xfffffff000000000;image=ram+base-virtual
        args=(image&~(BLOCK-1))+PAGE
        plan={'schema':1,'purpose':'synthetic-pc-model','physical_reservation_verified':False,
              'ram':{'start':ram,'size':0x40000000},'virtual_base':virtual,'reserved':[],'occupied':[],
              'arguments_address':args,'device_tree_address':args+PAGE,'adapter_address':args+2*PAGE,
              'top_of_kernel':image+len(kernel),'command_line':'debug=0x14e'}
        bundle=output/('case-'+str(index))
        manifest=build(directory,adapter,adt,plan,bundle)
        case=run_case(directory,ram,transfer_elf=adapter,handoff_bundle=bundle)
        if observations:case['observed_capacity_check']=check_tcr(observations,int(case['tcr_el1'],16))
        case['buffer_count']=len(manifest['buffers'])
        case['bundle_manifest_sha256']=hashlib.sha256((bundle/'handoff.json').read_bytes()).hexdigest()
        cases.append(case)
    result={'passed':True,'cases':cases,'kernel_sha256':checked['sha256'],
            'materialized_buffers_executed_in_pc_model':True,'physical_reservation_verified':False,
            'hardware_verified':False,'deployment_ready':False,'device_operations':[],
            'scope':'Real XNU instructions and generated buffers; synthetic RAM/register/cache/TLB; stops before MMU enable'}
    (output/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('kernel-build','adapter','output'):parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--observed-profile',type=Path)
    a=parser.parse_args();r=run(a.kernel_build,a.adapter,a.output,a.observed_profile)
    print(json.dumps({'passed':r['passed'],'cases':len(r['cases']),
                      'instructions':[c['instructions'] for c in r['cases']],
                      'physical_reservation_verified':False,'stop':'before_mmu_enable'}))
