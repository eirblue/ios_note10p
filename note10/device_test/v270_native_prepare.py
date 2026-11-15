"""Macro-safe270 include over the immutable269 completed-probe carrier."""
import hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parent
RETAINED_SHA='dd8075fefecc6e5c31f24966f305d7bf09031e4395cd80d95a1586a6ab2969b1'
if hashlib.sha256((HERE/'v269_native_prepare.py').read_bytes()).hexdigest()!=RETAINED_SHA:raise ValueError('immutable269 producer source')
import v269_native_prepare as retained
WORKFLOW='.github/workflows/note10-v270-native-prepare.yml'
JOB='v270-native-prepare'
BUILD_SCHEMA='note10-v270-holder-carrier-build-v1'
CONTEXT_SCHEMA='note10-v270-holder-carrier-public-input-v1'
MANIFEST_SCHEMA='note10-v270-holder-carrier-sealed-members-v1'
SUCCESS_MEMBERS=retained.SUCCESS_MEMBERS
NEW_FILES=('v270_watchdog_driver.inc','test_v270_watchdog_macro.py','v270_native_prepare.py')
CARRIED269=dict(source_head='47fef23deb02cb98627627cef54b4bd1c245a788',result_sha256='127e9285b435913a60635e4b6660bf767ce84aac4f2eeced9010b4d797e78412',passed=True,groups=1,variants=12,assertions=12,host_compile_attempts=1,host_fixture_process_attempts=1,replayed=False)
def source_pins():
    pins=retained.source_pins();pins.pop(retained.WORKFLOW)
    pins.update({'note10/device_test/'+n:retained.sha(retained.p.ordinary(HERE/n))for n in NEW_FILES})
    pins[WORKFLOW]=retained.sha(retained.p.ordinary(retained.ROOT/WORKFLOW));return pins
def public_context(head,passed):
    retained.p.hexid(head,40)
    retained.require(type(passed)is dict and set(passed)=={'passed','groups','variants','assertions','result_sha256'}and passed['passed']is True and(passed['groups'],passed['variants'],passed['assertions'])==(1,1,1),'one new macro compile PASS only')
    retained.p.hexid(passed['result_sha256'])
    return dict(schema=CONTEXT_SCHEMA,source_head=head,source_sha256=source_pins(),new_fixture_PASS=passed,carried269_fixture_PASS=CARRIED269,holder_bytes=retained.capacity.SOURCE_CAP,CI_native_source_input_bytes=0)
def transform_binding(path,raw):
    changed=retained.transform_binding(path,raw)
    if path==retained.DRIVER:
        changed=retained.once(changed,b'#include "v269_watchdog_driver.inc"\n',b'#include "v270_watchdog_driver.inc"\n')
    return changed
_bind=retained.baseline._bind
_ENV={**retained.__dict__,**{k:globals()[k]for k in ('WORKFLOW','JOB','BUILD_SCHEMA','CONTEXT_SCHEMA','MANIFEST_SCHEMA','SUCCESS_MEMBERS','source_pins','public_context','transform_binding')}}
def install_binding(source,buffers):
    records={}
    for name in retained.PREIMAGES:
        path=source/name;before=retained.p.ordinary(path);after=transform_binding(name,before);path.write_bytes(after)
        records[name]=dict(before_sha256=retained.sha(before),after_sha256=retained.sha(after))
    targets={'v269_watchdog_binding.h':'include/linux/v269_watchdog_binding.h','v270_watchdog_driver.inc':'drivers/watchdog/v270_watchdog_driver.inc','v269_watchdog_owner.inc':'arch/arm64/mm/v269_watchdog_owner.inc'}
    for name,relative in targets.items():
        target=source/relative;retained.require(not target.exists(),'fresh270 include target');target.write_bytes(buffers['note10/device_test/'+name])
    return dict(compiler_inputs=records,source_sha256={n:retained.sha(buffers['note10/device_test/'+n])for n in targets},record_bytes=40,pool_offset=43664,new_pool_bytes=0,attempt_before_global=True,null_remove_guard=True,original_hardware_order_retained=True)
_ENV['install_binding']=install_binding
run_build=_bind(retained.run_build,_ENV,{'note10/private/v269-ci-native-prepare':'note10/private/v270-ci-native-prepare','v269':'v270','"-v269-watchdog-probe-binding"':'"-v270-watchdog-noinline-macro"'})
seal=_bind(retained.seal,_ENV,{})
_ENV.update(run_build=run_build,seal=seal)
main=_bind(retained.main,_ENV,{})
# The report ABI, current caller and target evidence remain the retained269 semantics.
DRIVER=retained.DRIVER
decode_binding=retained.decode_binding
if __name__=='__main__':main()
