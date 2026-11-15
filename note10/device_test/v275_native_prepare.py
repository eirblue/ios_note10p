"""275 supports bounded named-C frame-address formation; outlined neutrality unchanged."""
import hashlib,re
from collections import deque
from pathlib import Path
HERE=Path(__file__).resolve().parent
RETAINED_SHA='27c70fb802160e35c822098c171cf0f48068e683002bf62a63369ff5febe31de'
if hashlib.sha256((HERE/'v274_native_prepare.py').read_bytes()).hexdigest()!=RETAINED_SHA:raise ValueError('immutable274 producer')
import v274_native_prepare as retained
selected=retained.selected
p,require,sha=retained.p,retained.require,retained.sha
flow=selected.flow
ROOTS,TARGET,BOUNDARIES=retained.ROOTS,retained.TARGET,retained.BOUNDARIES
WORKFLOW='.github/workflows/note10-v275-native-prepare.yml'
JOB='v275-native-prepare'
BUILD_SCHEMA='note10-v275-holder-carrier-build-v1'
CONTEXT_SCHEMA='note10-v275-holder-carrier-public-input-v1'
MANIFEST_SCHEMA='note10-v275-holder-carrier-sealed-members-v1'
CAPTURE_SCHEMA='note10-v275-watchdog-C-frame-address-raw-v1'
TARGET_SCHEMA='note10-v275-watchdog-binding-target-v1'
SUCCESS_MEMBERS=retained.SUCCESS_MEMBERS
NEW_FILES=('v275_native_prepare.py','test_v275_watchdog_frame_address.py')
CARRIED274=dict(source_head='bd40eb0c6b363c933e8bba73756d2ff4ed527dc1',result_sha256='29f853a2f79f7f502b525602f739d7e4c243618449cc4b9da8615dccb4f56d4b',passed=True,groups=1,variants=3,assertions=3,host_compile_attempts=0,host_fixture_process_attempts=0,replayed=False)

def source_pins():
    pins=retained.source_pins();pins.pop(retained.WORKFLOW)
    pins.update({'note10/device_test/'+n:sha(p.ordinary(HERE/n))for n in NEW_FILES})
    pins[WORKFLOW]=sha(p.ordinary(selected.base.ROOT/WORKFLOW));return pins

def public_context(head,passed):
    context=retained.public_context(head,passed)
    context.update(schema=CONTEXT_SCHEMA,source_sha256=source_pins(),carried274_fixture_PASS=CARRIED274);return context

def own_frame(name,rows,external,frame,outlined):
    if outlined:
        allowed={'mov','movz','movn','movk','add','adds','sub','subs','and','ands','orr','eor','bic','bics','orn','eon','mvn','neg','negs','cmp','cmn','tst','csel','csinc','csinv','csneg','cset','csetm','lsl','lsr','asr','ror','ubfx','sbfx','bfi','bfxil','uxtb','uxth','uxtw','sxtb','sxth','sxtw','adr','adrp','ldr','ldrb','ldrh','ldrsw','ldur','ldurb','ldurh','ldursw','str','strb','strh','stur','sturb','sturh','ldp','stp','nop','ret','b','cbz','cbnz','tbz','tbnz'}
        require(frame==0 and all((op in allowed or re.fullmatch(r'b\.(eq|ne|cs|cc|hs|lo|mi|pl|vs|vc|hi|ls|ge|lt|gt|le|al|nv)',op))and(op=='ret'and args in('','x30')or not re.search(r'\b(?:sp|wsp|x29|w29|fp|x30|w30|lr)\b',args))for _,op,args in rows),'outlined supported SP/FP/LR-neutral instructions; no BL')
    states={0:(0,None)};pending=deque([0]);calls={};peak=0;closures=0;visits=0;samples=[]
    while pending:
        index=pending.popleft();visits+=1;require(visits<=len(rows)*32,'bounded watchdog own-frame convergence')
        sp,fp=states[index];address,op,args=rows[index];access=flow.memory(op,args)
        math=re.fullmatch(r'(sp|x29),\s*sp,\s*#(-?(?:0x[0-9a-f]+|\d+))',args)if op in('add','sub')else None
        address_form=re.fullmatch(r'(x(?:[0-9]|1[0-9]|2[0-8])),\s*sp,\s*#(-?(?:0x[0-9a-f]+|\d+))',args)if op=='add'else None
        if access:
            if access['pre']:sp+=access['offset'];offset=0
            else:offset=access['offset']
            origin=sp if access['base']=='sp'else fp
            require(origin is not None and sp<=origin+offset<origin+offset+access['width']<=0,'watchdog stack access within live own allocation')
            if access['load']and'x29'in access['regs']:fp=None
            sp+=access['post']
        elif math:
            value=flow.immediate(math[2])*(1 if op=='add'else-1)
            if math[1]=='sp':sp+=value
            else:fp=sp+value
        elif op=='mov'and flow.normalized(args)=='x29,sp':fp=sp
        elif address_form:
            offset=flow.immediate(address_form[2])
            require(not outlined and name in ROOTS and sp<0 and 0<=offset<-sp,'named C address must be inside current live own frame')
            samples.append(dict(address=address,register=address_form[1],SP_offset=sp,literal_offset=offset,formed_entry_SP_offset=sp+offset,live_frame_interval=[sp,0]))
        else:require(not re.search(r'\b(?:sp|wsp|x29|w29|fp)\b',args),'unsupported watchdog own SP/FP effect')
        require(-frame<=sp<=0,'watchdog allocation exceeds actual SU');peak=max(peak,-sp)
        if address in external:
            require(op in('bl','b')and(op!='b'or sp==0),'balanced SP0 external tail only');calls[address]=sp
            if op=='b':closures+=1
        if op=='ret':require(sp==0,'balanced watchdog return');closures+=1
        for nxt in flow.successors(rows,index,external):
            state=(sp,fp)
            if nxt in states:require(states[nxt]==state,'compatible watchdog own-frame merge')
            else:states[nxt]=state;pending.append(nxt)
    require(closures>0 and peak==frame,'closed watchdog own peak equals actual static SU')
    return dict(own_peak_bytes=peak,call_SP_offsets=calls,neutral_outlined=outlined,normal_ABI_call_return_assumed=not outlined,callee_peaks_included=False,SP_address_samples=samples)

_bind=retained._bind
_WATCHDOG={**retained._WATCHDOG,**{k:globals()[k]for k in('own_frame','CAPTURE_SCHEMA','TARGET_SCHEMA')}}
capture_document=_bind(retained.capture_document,_WATCHDOG,{})
scoped_closure=_bind(retained.scoped_closure,_WATCHDOG,{})
_WATCHDOG.update(capture_document=capture_document,scoped_closure=scoped_closure)
collect_binding=_bind(retained.collect_binding,_WATCHDOG,{})
_ENV={**retained._ENV,**{k:globals()[k]for k in('WORKFLOW','JOB','BUILD_SCHEMA','CONTEXT_SCHEMA','MANIFEST_SCHEMA','SUCCESS_MEMBERS','source_pins','public_context','collect_binding')}}
run_build=_bind(retained.run_build,_ENV,{'note10/private/v274-ci-native-prepare':'note10/private/v275-ci-native-prepare','v274':'v275','"-v274-watchdog-boundary-alias"':'"-v275-watchdog-C-frame-address"'})
seal=_bind(retained.seal,_ENV,{})
_ENV.update(run_build=run_build,seal=seal)
main=_bind(retained.main,_ENV,{})
classify_edge=retained.classify_edge
driver_provenance,save_capture=retained.driver_provenance,retained.save_capture
decode_binding=retained.decode_binding
if __name__=='__main__':main()
