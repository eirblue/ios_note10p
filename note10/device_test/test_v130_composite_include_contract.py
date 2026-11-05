"""NEW compile-only admission validator cases. Native include validation remains pending for fresh CI."""
import argparse
import base64
import json
from pathlib import Path
from v130_contract import ordinary,private,sha,read,save,hexid
from v130_build import source_pins,composite_include_context,COMPOSITE_SCOPE,COMPOSITE_FILES,RETURN_UFS_SOURCE_COMMIT


def reject(call):
    try:call()
    except ValueError:return
    raise AssertionError('compile-only admission rejection did not reject')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--scope',required=True,choices=[COMPOSITE_SCOPE]);p.add_argument('--retained-return-pass',required=True,type=Path)
    p.add_argument('--retained-pass-sha256',required=True);p.add_argument('--output',required=True,type=Path);a=p.parse_args()
    out=private(a.output);retained=ordinary(a.retained_return_pass)
    if out.exists() or sha(retained)!=hexid(a.retained_pass_sha256):p.error('fresh output and exact retained source30 PASS required')
    current=source_pins();delta={name:current[name] for name in COMPOSITE_FILES}
    candidate=dict(schema='note10-v130-public-composite-compile-continuation-v1',scope=COMPOSITE_SCOPE,source_contract_passed=True,native_compile_status='pending',
        retained_source_commit=RETURN_UFS_SOURCE_COMMIT,retained_return_order_PASS=read(retained),
        source_contract_PASS=dict(schema='note10-v130-composite-admission-contract-pass-v1',scope=COMPOSITE_SCOPE,passed=True,result_sha256='0'*64,source_sha256=delta),source_sha256=current)
    out.mkdir(parents=True);save(out/'attempt.json',dict(schema='note10-v130-composite-include-contract-attempt-v1',scope=COMPOSITE_SCOPE,source_sha256=delta))
    result=dict(schema='note10-v130-composite-include-contract-result-v1',scope=COMPOSITE_SCOPE,passed=False,source_sha256=delta,current_source_sha256=current,
        retained_source_commit=RETURN_UFS_SOURCE_COMMIT,native_compile_status='pending',compiler_invocations=0,fixture_processes=0,old_tests_replayed=0,
        raw_kernel_reads=0,adapter_reads=0,compressions=0,Image_reads=0,Image_builds=0,device_operations=[])
    try:
        composite_include_context(candidate,current)
        bad=json.loads(json.dumps(candidate));bad['native_compile_status']='compiled';reject(lambda:composite_include_context(bad,current))
        bad=json.loads(json.dumps(candidate));bad['source_contract_passed']=False;reject(lambda:composite_include_context(bad,current))
        bad=json.loads(json.dumps(candidate));bad['retained_source_commit']='0'*40;reject(lambda:composite_include_context(bad,current))
        unapproved=dict(current);unapproved['note10/device_test/v130_usb_gadget.inc']='0'*64
        bad=json.loads(json.dumps(candidate));bad['source_sha256']=unapproved;reject(lambda:composite_include_context(bad,unapproved))
        bad=json.loads(json.dumps(candidate));bad['retained_return_order_PASS']['source_sha256']['note10/device_test/v130_kernel.c']='0'*64
        reject(lambda:composite_include_context(bad,current))
        bad=json.loads(json.dumps(candidate));bad['source_contract_PASS']['source_sha256']['note10/device_test/v130_prepare.py']='0'*64
        reject(lambda:composite_include_context(bad,current))
        bad=json.loads(json.dumps(candidate));bad['passed']=True;reject(lambda:composite_include_context(bad,current))
        if current!=source_pins():raise ValueError('reviewed admission delta changed')
        result.update(passed=True,production_admission_validator_tested=True,include_runtime_fixture_added=False,prior30_retested=False,
            original_PASS_chain_rewritten=False,physical_ready=False,cases=['accept pending compile with exact retained30','reject invented native success',
            'reject failed source contract','reject wrong retained commit','reject changed no-bound-driver gate','reject rebound prior PASS','reject wrong delta map','reject generic new PASS overclaim'])
    except Exception:
        import traceback
        result['error']=traceback.format_exc()
    save(out/'result.json',result)
    if result['passed']:
        candidate['source_contract_PASS']['result_sha256']=sha(out/'result.json');composite_include_context(candidate,current)
        save(out/'public-compile-continuation.json',candidate)
        (out/'public-compile-continuation.b64').write_bytes(base64.b64encode(json.dumps(candidate,separators=(',',':')).encode())+b'\n')
    return 0 if result['passed'] else 1

if __name__=='__main__':raise SystemExit(main())
