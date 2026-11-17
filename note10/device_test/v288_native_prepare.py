"""287 compares the bounded restore window while retaining the complete CFG."""
from pathlib import Path
import v286_native_prepare as retained
p,require,sha,bind=retained.p,retained.require,retained.sha,retained.bind
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
WORKFLOW='.github/workflows/note10-v288-native-prepare.yml';JOB='v288-native-prepare'
BUILD_SCHEMA='note10-v288-CPU-metadata-PC-build-v1'
CONTEXT_SCHEMA='note10-v288-CPU-metadata-PC-public-input-v1'
MANIFEST_SCHEMA='note10-v288-CPU-metadata-PC-sealed-members-v1'
SUCCESS_MEMBERS=retained.SUCCESS_MEMBERS
CAPTURE_SCHEMA,TARGET_SCHEMA=retained.CAPTURE_SCHEMA,retained.TARGET_SCHEMA
decode_binding=retained.decode_binding
INIT_WORDS=retained.INIT_WORDS
OWNER_TARGET=retained.OWNER_TARGET
same_context,direct_call=retained.same_context,retained.direct_call
frame_states,successors=retained.frame_states,retained.successors
inventory_metadata,install_binding=retained.inventory_metadata,retained.install_binding
stream_candidate=retained.stream_candidate
NEW_FILES=('v288_native_prepare.py','test_v288_epilogue_window.py')
CARRIED286=dict(passed=False,source_head='b00ef8bacb6e567f1ace549210adb69c32bb020d',run_id=44010000999,
    Image_and_PID1_built=True,Image_bytes=50401292,producer_passed=False,carrier_eligible=False,
    PC_target_accepted=False,no_retry=True,old_tests_replayed=False)

def source_pins():
    value=retained.source_pins();value.pop(retained.WORKFLOW)
    value.update({'note10/device_test/'+name:sha(p.ordinary(HERE/name)) for name in NEW_FILES})
    value[WORKFLOW]=sha(p.ordinary(ROOT/WORKFLOW));return value

def public_context(head,passed):
    value=retained.public_context(head,passed)
    value.update(schema=CONTEXT_SCHEMA,source_sha256=source_pins(),carried_v286_failure=CARRIED286)
    return value

def init_restore(helper, helper_rows, callers, incoming, provenance):
    require(tuple(w for _,w,_,_ in helper_rows)==INIT_WORDS and helper['bytes']==20,'fixed init saved-slot reads and RET')
    same_context(provenance,callers,OWNER_TARGET,80)
    require(sorted(c['name'] for c in callers)==['n217_page_io','n285_readback_pages'] and len(incoming)==2 and
        sorted(n for n,_,op in incoming if op=='bl')==['n217_page_io','n285_readback_pages'],'only both selected init incoming contexts')
    prefix=(0xa9bb7bfd,0xf9000bf9,0x910003fd,0xa9025ff8,0xa90357f6,0xa9044ff4)
    for caller in callers:
        rows=caller['rows'];call=next(a for n,a,_ in incoming if n==caller['name']);at=next(i for i,row in enumerate(rows) if row[0]==call)
        require(tuple(w for _,w,_,_ in rows[:6])==prefix and tuple(w for _,w,_,_ in rows[at+1:at+3])==(0xa8c57bfd,0xd65f03c0),'actual save80 and adjacent FP/LR pop80 window')
        direct_call(rows[at],helper['address'])
        require([i for i,row in enumerate(rows) if row[2]=='ret']==[at+2] and
            all(not row[2].startswith(('st','cas','swp','ldadd','ldclr','ldeor','ldset')) for row in rows[6:]),'sole init return and no saved-slot overwrite')
        states,_=frame_states(rows,80);require(states[at]==(-80,-80),'actual live init caller80')
        for i in states:
            for target in successors(rows,i):
                require(target not in (at+1,at+2) or target==i+1,'no init restore bypass')
                require(i<6 or target>=6,'no reentry into init saves')
    return dict(own_peak_bytes=0,neutral_outlined=False,standalone_leaf=False,contextual_caller_frame=True,
        helper_SP_change=0,caller_frame_bytes=80,saved_SP_intervals=[[16,24],[32,48],[48,64],[64,80]],
        original_FP_LR_restored_by_caller=True,selected_incoming=incoming,provenance=provenance,
        normal_ABI_call_return_assumed=True,callee_peaks_included=False)

_code_bind=retained.retained._bind
context_inputs=bind(retained.context_inputs,{**retained.context_inputs.__globals__,'init_restore':init_restore})
verify_metadata=_code_bind(retained.verify_metadata,{**retained.verify_metadata.__globals__,'context_inputs':context_inputs},{'note10-v286-CPU-metadata-raw-v1': 'note10-v288-CPU-metadata-raw-v1', 'note10-v286-CPU-metadata-target-v1': 'note10-v288-CPU-metadata-target-v1'})
collect_binding=_code_bind(retained.collect_binding,{**retained.collect_binding.__globals__,'verify_metadata':verify_metadata},{'note10-v286-CPU-metadata-raw-v1': 'note10-v288-CPU-metadata-raw-v1', 'note10-v286-seal-frontier-v1': 'note10-v288-seal-frontier-v1', 'note10-v286-seal-order-PC-target-v1': 'note10-v288-seal-order-PC-target-v1'})
_ENV={**retained._ENV,**{name:globals()[name] for name in ('WORKFLOW','JOB','BUILD_SCHEMA','CONTEXT_SCHEMA',
    'MANIFEST_SCHEMA','SUCCESS_MEMBERS','source_pins','public_context','install_binding','collect_binding','stream_candidate')}}
run_build=_code_bind(retained.run_build,_ENV,{'note10/private/v286-ci-native-prepare': 'note10/private/v288-ci-native-prepare', 'v286': 'v288', '"-v286-contextual-validator"': '"-v288-epilogue-window"'})
seal=bind(retained.seal,{**retained.seal.__globals__,**_ENV,'inventory_metadata':inventory_metadata})
_ENV.update(run_build=run_build,seal=seal)
main=bind(retained.main,_ENV)

def audit_api():
    require(context_inputs.__globals__['init_restore'] is init_restore and verify_metadata.__globals__['context_inputs'] is context_inputs and
        collect_binding.__globals__['verify_metadata'] is verify_metadata,'new window predicate reached by fresh capture')
    require(run_build.__globals__['collect_binding'] is collect_binding and run_build.__globals__['install_binding'] is install_binding and
        main.__globals__['seal'] is seal and seal.__globals__['inventory_metadata'] is inventory_metadata,'fresh build/seal callbacks')

if __name__=='__main__':main()
