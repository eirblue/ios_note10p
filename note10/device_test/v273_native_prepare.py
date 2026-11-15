"""273 completes only unfinished synthetic predicates; scoped272 collector unchanged."""
import hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parent
RETAINED_SHA='d9f655d26adfa01e6ba324d3d23bb41a8e2c3990a6e012ab2c94b35adf96ee69'
if hashlib.sha256((HERE/'v272_native_prepare.py').read_bytes()).hexdigest()!=RETAINED_SHA:raise ValueError('immutable272 scoped producer')
import v272_native_prepare as retained
p,require,sha=retained.p,retained.require,retained.sha
WORKFLOW='.github/workflows/note10-v273-native-prepare.yml'
JOB='v273-native-prepare'
BUILD_SCHEMA='note10-v273-holder-carrier-build-v1'
CONTEXT_SCHEMA='note10-v273-holder-carrier-public-input-v1'
MANIFEST_SCHEMA='note10-v273-holder-carrier-sealed-members-v1'
SUCCESS_MEMBERS=retained.SUCCESS_MEMBERS
CAPTURE_SCHEMA=retained.CAPTURE_SCHEMA
TARGET_SCHEMA=retained.TARGET_SCHEMA
PUBLIC_DELTA=('note10/device_test/v272_native_prepare.py','note10/device_test/test_v272_watchdog_closure.py','note10/device_test/v273_native_prepare.py','note10/device_test/test_v273_watchdog_remaining.py',WORKFLOW)
CARRIED272_PARTIAL=dict(result_sha256='b56abee80fdbbf8013139c2bf9db7de8d01512dd71a8a674ae65d017392ce4b4',passed=False,groups=1,variants=6,assertions=3,completed_variants=3,case_names=['scoped-intra-body-control-flow','duplicate-name-driver-local-closure','scope-and-provenance-rejection'],host_compile_attempts=0,host_fixture_process_attempts=0,replayed=False)

def source_pins():
    # Skip272.source_pins: its unpublished workflow is not a273 dependency.
    pins=retained.retained.source_pins();pins.pop(retained.retained.WORKFLOW)
    pins.update({n:sha(p.ordinary(retained.base.ROOT/n))for n in PUBLIC_DELTA});return pins

def public_context(head,passed):
    p.hexid(head,40)
    require(type(passed)is dict and set(passed)=={'passed','groups','variants','assertions','result_sha256'}and passed['passed']is True and(passed['groups'],passed['variants'],passed['assertions'])==(1,3,3),'only three new remaining predicates')
    p.hexid(passed['result_sha256'])
    return dict(schema=CONTEXT_SCHEMA,source_head=head,source_sha256=source_pins(),new_fixture_PASS=passed,carried269_fixture_PASS=retained.retained.retained.CARRIED269,carried270_fixture_PASS=retained.retained.CARRIED270,carried271_fixture_PASS=retained.CARRIED271,carried272_partial=CARRIED272_PARTIAL,holder_bytes=retained.base.capacity.SOURCE_CAP,CI_native_source_input_bytes=0)

_bind=retained._bind
_ENV={**retained._ENV,**{k:globals()[k]for k in('WORKFLOW','JOB','BUILD_SCHEMA','CONTEXT_SCHEMA','MANIFEST_SCHEMA','SUCCESS_MEMBERS','source_pins','public_context')}}
run_build=_bind(retained.run_build,_ENV,{'note10/private/v272-ci-native-prepare':'note10/private/v273-ci-native-prepare','v272':'v273','"-v272-watchdog-scoped-closure"':'"-v273-watchdog-remaining-predicates"'})
seal=_bind(retained.seal,_ENV,{})
_ENV.update(run_build=run_build,seal=seal)
main=_bind(retained.main,_ENV,{})
ROOTS,TARGET,driver_provenance,capture_document,save_capture,scoped_closure=(getattr(retained,n)for n in ('ROOTS','TARGET','driver_provenance','capture_document','save_capture','scoped_closure'))
collect_binding=retained.collect_binding
decode_binding=retained.decode_binding
if __name__=='__main__':main()
