"""Focused NEW production continuation-validator checks; native PID1 compilation belongs to fresh CI."""
import argparse
import base64
import json
from pathlib import Path
from v130_contract import ROOT,ordinary,private,sha,read,save,hexid
from v130_build import source_pins,continuation_context,RETAINED_SOURCE_COMMIT,RETAINED_SYNTHETIC_RESULT_SHA256,DELTA_SCOPE,DELTA_FILES


def reject(call):
    try:call()
    except ValueError:return
    raise AssertionError('new continuation rejection did not reject')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--scope',choices=[DELTA_SCOPE],required=True)
    p.add_argument('--retained-public-pass',type=Path,required=True);p.add_argument('--retained-pass-sha256',required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    out=private(a.output);retained_path=ordinary(a.retained_public_pass)
    if out.exists():p.error('fresh NEW continuation-validator output required')
    if sha(retained_path)!=hexid(a.retained_pass_sha256):p.error('exact original synthetic PASS metadata required')
    old=read(retained_path);current=source_pins();delta={k:current[k] for k in DELTA_FILES}
    candidate=dict(schema='note10-v130-public-continuation-pass-v1',scope=DELTA_SCOPE,passed=True,
        retained_source_commit=RETAINED_SOURCE_COMMIT,retained_NEW_PASS=old,
        delta_NEW_PASS=dict(schema='note10-v130-event-return-delta-pass-v1',scope=DELTA_SCOPE,passed=True,result_sha256='0'*64,source_sha256=delta),
        source_sha256=current)
    out.mkdir(parents=True);save(out/'attempt.json',dict(schema='note10-v130-event-return-delta-attempt-v1',scope=DELTA_SCOPE,source_sha256=delta))
    result=dict(schema='note10-v130-event-return-delta-result-v1',scope=DELTA_SCOPE,passed=False,source_sha256=delta,
        retained_source_commit=RETAINED_SOURCE_COMMIT,retained_synthetic_result_sha256=RETAINED_SYNTHETIC_RESULT_SHA256,
        current_source_sha256=current,compiler_invocations=0,fixture_processes=0,old_tests_replayed=0,
        raw_kernel_reads=0,adapter_reads=0,compressions=0,Image_reads=0,Image_builds=0,device_operations=[])
    try:
        continuation_context(candidate,current)
        bad=json.loads(json.dumps(candidate));bad['retained_NEW_PASS']['source_sha256']['note10/device_test/v130_loader.c']=current['note10/device_test/v130_loader.c']
        reject(lambda:continuation_context(bad,current))
        bad=json.loads(json.dumps(candidate));bad['delta_NEW_PASS']['source_sha256']['note10/device_test/v130_loader.c']='0'*64
        reject(lambda:continuation_context(bad,current))
        bad=json.loads(json.dumps(candidate));bad['retained_source_commit']='0'*40
        reject(lambda:continuation_context(bad,current))
        unapproved=dict(current);unapproved['note10/device_test/v130_handoff_core.c']='0'*64
        bad=json.loads(json.dumps(candidate));bad['source_sha256']=unapproved
        reject(lambda:continuation_context(bad,unapproved))
        unexpected=dict(current,unreviewed_source='0'*64)
        bad=json.loads(json.dumps(candidate));bad['source_sha256']=unexpected
        reject(lambda:continuation_context(bad,unexpected))
        bad=json.loads(json.dumps(candidate));bad['schema']='unversioned'
        reject(lambda:continuation_context(bad,current))
        if current!=source_pins():raise ValueError('reviewed new delta changed during execution')
        result.update(passed=True,production_continuation_validator_tested=True,cases=['accepted original+allowed delta','retained-original-map rejection',
            'delta-map rejection','wrong-original-commit rejection','changed-tested-core rejection','unexpected-source rejection','wrong-schema rejection'],
            native_event_function_tested=False,native_event_validation='fresh complete GCC PID1 compile with unchanged -Werror in next CI',
            original_PASS_rewritten=False,current_source_fully_retested=False,physical_ready=False)
    except Exception:
        import traceback
        result['error']=traceback.format_exc()
    save(out/'result.json',result)
    if result['passed']:
        candidate['delta_NEW_PASS']['result_sha256']=sha(out/'result.json');continuation_context(candidate,current)
        save(out/'public-continuation-pass.json',candidate)
        (out/'public-continuation-pass.b64').write_bytes(base64.b64encode(json.dumps(candidate,separators=(',',':')).encode())+b'\n')
    return 0 if result['passed'] else 1

if __name__=='__main__':raise SystemExit(main())
