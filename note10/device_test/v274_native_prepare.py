"""274 admits only exact-extent aliases witnessed by an original opaque boundary."""
import hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parent
RETAINED_SHA='ea8767fd1d27a2cd13fbf0060379993d88f80351d618b9c6bfa4aeea08af88bf'
if hashlib.sha256((HERE/'v273_native_prepare.py').read_bytes()).hexdigest()!=RETAINED_SHA:raise ValueError('immutable273 producer')
import v273_native_prepare as retained
selected=retained.retained
p,require,sha=retained.p,retained.require,retained.sha
ROOTS,TARGET,BOUNDARIES=selected.ROOTS,selected.TARGET,selected.BOUNDARIES
WORKFLOW='.github/workflows/note10-v274-native-prepare.yml'
JOB='v274-native-prepare'
BUILD_SCHEMA='note10-v274-holder-carrier-build-v1'
CONTEXT_SCHEMA='note10-v274-holder-carrier-public-input-v1'
MANIFEST_SCHEMA='note10-v274-holder-carrier-sealed-members-v1'
CAPTURE_SCHEMA='note10-v274-watchdog-boundary-alias-raw-v1'
TARGET_SCHEMA='note10-v274-watchdog-binding-target-v1'
SUCCESS_MEMBERS=retained.SUCCESS_MEMBERS
NEW_FILES=('v274_native_prepare.py','test_v274_watchdog_boundary.py')
CARRIED273=dict(source_head='4e4c62602b955f748964783d57d08bc96358cb8b',result_sha256='638244452a254a144f43cf0c6975f54442675ee61af31edb423810052b3bc7d4',passed=True,groups=1,variants=3,assertions=3,host_compile_attempts=0,host_fixture_process_attempts=0,replayed=False)

def source_pins():
    pins=retained.source_pins();pins.pop(retained.WORKFLOW)
    pins.update({'note10/device_test/'+n:sha(p.ordinary(HERE/n))for n in NEW_FILES})
    pins[WORKFLOW]=sha(p.ordinary(selected.base.ROOT/WORKFLOW));return pins

def public_context(head,passed):
    context=retained.public_context(head,passed)
    context.update(schema=CONTEXT_SCHEMA,source_sha256=source_pins(),carried273_fixture_PASS=CARRIED273);return context

def classify_edge(edge,context,roots):
    records=edge['resolved_records'];names={r['name']for r in records};witness=names&BOUNDARIES
    if not witness:return selected.classify_edge(edge,context,roots)
    require(edge['mnemonic']in('bl','b')and not edge['unresolved'],'ordinary resolved watchdog call/tail only')
    require(1<=len(records)<=32 and edge['resolved_symbols']==sorted(names)and all(r['kind']in('T','t','W','w')and type(r['ordinal'])is int and r['ordinal']>=0 for r in records)and len({r['ordinal']for r in records})==len(records),'bounded complete boundary alias records')
    require(all(r['offset']==0 and r['address']==edge['target']for r in records),'exact boundary alias entry only')
    extents={(r['address'],r['bytes'])for r in records};require(len(extents)==1,'one exact boundary alias extent')
    start,size=next(iter(extents))
    require(type(start)is type(size)is int and 0<start<1<<64 and 0<size<1<<64 and start%4==size%4==0 and start+size<1<<64,'valid bounded AArch64 boundary alias extent')
    return dict(kind='boundary',names=sorted(witness),key=(start,size),aliases=sorted(names),alias_records=records)

_bind=retained._bind
_WATCHDOG={**selected.__dict__,**{k:globals()[k]for k in('classify_edge','CAPTURE_SCHEMA','TARGET_SCHEMA')}}
capture_document=_bind(selected.capture_document,_WATCHDOG,{})
scoped_closure=_bind(selected.scoped_closure,_WATCHDOG,{})
_WATCHDOG.update(capture_document=capture_document,scoped_closure=scoped_closure)
collect_binding=_bind(selected.collect_binding,_WATCHDOG,{})
_ENV={**retained._ENV,**{k:globals()[k]for k in('WORKFLOW','JOB','BUILD_SCHEMA','CONTEXT_SCHEMA','MANIFEST_SCHEMA','SUCCESS_MEMBERS','source_pins','public_context','collect_binding')}}
run_build=_bind(retained.run_build,_ENV,{'note10/private/v273-ci-native-prepare':'note10/private/v274-ci-native-prepare','v273':'v274','"-v273-watchdog-remaining-predicates"':'"-v274-watchdog-boundary-alias"'})
seal=_bind(retained.seal,_ENV,{})
_ENV.update(run_build=run_build,seal=seal)
main=_bind(retained.main,_ENV,{})
driver_provenance,save_capture=selected.driver_provenance,selected.save_capture
decode_binding=retained.decode_binding
if __name__=='__main__':main()
