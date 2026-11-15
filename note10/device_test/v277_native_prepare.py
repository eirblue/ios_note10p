"""277 fixes only the remaining fixture locator; production276 is immutable."""
import hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parent
RETAINED_SHA='7965d16bbeb9937536a654b5931ee4bf5a13953f4e6018e283900d107005aa9f'
if hashlib.sha256((HERE/'v276_native_prepare.py').read_bytes()).hexdigest()!=RETAINED_SHA:raise ValueError('immutable276 producer')
import v276_native_prepare as retained
p,require,sha=retained.p,retained.require,retained.sha
WORKFLOW='.github/workflows/note10-v277-native-prepare.yml'
JOB='v277-native-prepare'
BUILD_SCHEMA='note10-v277-holder-carrier-build-v1'
CONTEXT_SCHEMA='note10-v277-holder-carrier-public-input-v1'
MANIFEST_SCHEMA='note10-v277-holder-carrier-sealed-members-v1'
SUCCESS_MEMBERS=retained.SUCCESS_MEMBERS
CAPTURE_SCHEMA=retained.CAPTURE_SCHEMA
TARGET_SCHEMA=retained.TARGET_SCHEMA
RETAINED276_SOURCES={'note10/device_test/test_v276_watchdog_core_completion.py': '48b0617a19195549d5e7ee961511c39a24afbc0d95fd5f9bc647ac9bf5296177', 'note10/device_test/v276_native_prepare.py': '7965d16bbeb9937536a654b5931ee4bf5a13953f4e6018e283900d107005aa9f', 'note10/device_test/v276_watchdog_binding.h': '58bfeae994f7bec753ec683d6a02a8f129f88ab2a87a22d12ac3b5b5a1a1cb8c', 'note10/device_test/v276_watchdog_binding_fixture.c': '4ce3fadcd16b525ea0773766395c537599efccf43dbcd186041780638361d015', 'note10/device_test/v276_watchdog_driver.inc': '4614a6fef8abc3d9c430e364c74481e124fbb8e0e665f76ef767efadecf9219e', 'note10/device_test/v276_watchdog_owner.inc': 'f5b9835f230f46b73a9d340acc64f8db643323ba1fe12d28bb74a4a80127b75f'}
NEW_FILES=('test_v277_watchdog_completion_remaining.py','v277_native_prepare.py')
CARRIED276_C_PASS=dict(passed=True,groups=1,variants=6,assertions=6,case_names=['deferred','immediate','sample-commit','failure-remove','duplicate','identity'],host_compile_attempts=1,host_fixture_process_attempts=1,stdout_sha256='28e8fbf5ea8a1baa29d5f0ed5f6a0bc7c07ae230121c8fa0d55e5d33814a214e',source_sha256=RETAINED276_SOURCES,replayed=False)

def source_pins():
    # Do not call276.source_pins: unpublished workflow276 is obsolete.
    pins=retained.retained.source_pins();pins.pop(retained.retained.WORKFLOW)
    pins.update({n:sha(p.ordinary(retained.selected.base.ROOT/n))for n in RETAINED276_SOURCES})
    require({n:pins[n]for n in RETAINED276_SOURCES}==RETAINED276_SOURCES,'six exact carried276 source inputs')
    pins.update({'note10/device_test/'+n:sha(p.ordinary(HERE/n))for n in NEW_FILES})
    pins[WORKFLOW]=sha(p.ordinary(retained.selected.base.ROOT/WORKFLOW));return pins

def public_context(head,passed):
    context=retained.retained.public_context(head,passed)
    context.update(schema=CONTEXT_SCHEMA,source_sha256=source_pins(),carried275_fixture_PASS=retained.CARRIED275,carried276_C_PASS=CARRIED276_C_PASS);return context

_bind=retained._bind
_ENV={**retained._ENV,**{k:globals()[k]for k in('WORKFLOW','JOB','BUILD_SCHEMA','CONTEXT_SCHEMA','MANIFEST_SCHEMA','SUCCESS_MEMBERS','source_pins','public_context')}}
run_build=_bind(retained.run_build,_ENV,{'note10/private/v276-ci-native-prepare':'note10/private/v277-ci-native-prepare','v276':'v277','"-v276-watchdog-core-completion"':'"-v277-watchdog-completion-remaining"'})
seal=_bind(retained.seal,_ENV,{})
_ENV.update(run_build=run_build,seal=seal)
main=_bind(retained.main,_ENV,{})
ROOTS,FRAME_C_NAMES,CORE_CALLER,CORE_TARGET,TARGET,BOUNDARIES=(getattr(retained,n)for n in('ROOTS','FRAME_C_NAMES','CORE_CALLER','CORE_TARGET','TARGET','BOUNDARIES'))
driver_provenance,classify_edge,own_frame,scoped_closure,core_provenance,core_certificate,aggregate_extents,collect_binding,decode_binding=(getattr(retained,n)for n in('driver_provenance','classify_edge','own_frame','scoped_closure','core_provenance','core_certificate','aggregate_extents','collect_binding','decode_binding'))
_driver_collect=retained._driver_collect
transform_binding=retained.transform_binding
prior_transform_binding=retained.retained._ENV['transform_binding']
if __name__=='__main__':main()
