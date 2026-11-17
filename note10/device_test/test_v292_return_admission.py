"""Only the new actual context predicate and its exact source seam."""
import v292_native_prepare as producer

def predicate(fixture_result):
    producer.audit_api()
    source=b'#include "native_prepare_core.h"\n'+producer.OLD_FUNCTION
    changed=producer.return_overlay(source)
    producer.require(changed.count(b'#include "v292_return_admission.inc"')==1 and producer.OLD_FUNCTION not in changed,'one current return accessor replacement')
    producer.require(fixture_result==dict(passed=True,groups=1,variants=1,assertions=1,negative_cases=5),'new C return-admission conjunction only')
    return dict(passed=True,groups=1,variants=1,assertions=1)
