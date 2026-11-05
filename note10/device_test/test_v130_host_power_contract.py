"""NEW link-pending admission validator cases. Native link validation remains pending for fresh CI."""
import argparse
import base64
import json
from pathlib import Path
from v130_contract import ordinary,private,sha,read,save,hexid
from v130_build import source_pins,host_power_context,HOST_POWER_SCOPE,HOST_POWER_FILES,GADGET_SOURCE_COMMIT


def reject(call):
    try:call()
    except ValueError:return
    raise AssertionError('link-pending admission rejection did not reject')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--scope',required=True,choices=[HOST_POWER_SCOPE]);p.add_argument('--retained-compile-pass',required=True,type=Path)
    p.add_argument('--retained-pass-sha256',required=True);p.add_argument('--output',required=True,type=Path);a=p.parse_args()
    out=private(a.output);retained=ordinary(a.retained_compile_pass)
    if out.exists() or sha(retained)!=hexid(a.retained_pass_sha256):p.error('fresh output and exact retained source32 PASS required')
    current=source_pins();delta={name:current[name] for name in HOST_POWER_FILES}
    candidate=dict(schema='note10-v130-public-host-power-continuation-v1',scope=HOST_POWER_SCOPE,source_contract_passed=True,native_link_status='pending',
        retained_source_commit=GADGET_SOURCE_COMMIT,retained_gadget_link_continuation=read(retained),
        source_contract_PASS=dict(schema='note10-v130-host-power-admission-pass-v1',scope=HOST_POWER_SCOPE,passed=True,result_sha256='0'*64,source_sha256=delta),source_sha256=current)
    out.mkdir(parents=True);save(out/'attempt.json',dict(schema='note10-v130-host-power-contract-attempt-v1',scope=HOST_POWER_SCOPE,source_sha256=delta))
    result=dict(schema='note10-v130-host-power-contract-result-v1',scope=HOST_POWER_SCOPE,passed=False,source_sha256=delta,current_source_sha256=current,
        retained_source_commit=GADGET_SOURCE_COMMIT,native_link_status='pending',compiler_invocations=0,fixture_processes=0,old_tests_replayed=0,
        raw_kernel_reads=0,adapter_reads=0,compressions=0,Image_reads=0,Image_builds=0,device_operations=[])
    try:
        host_power_context(candidate,current)
        bad=json.loads(json.dumps(candidate));bad['native_link_status']='compiled';reject(lambda:host_power_context(bad,current))
        bad=json.loads(json.dumps(candidate));bad['source_contract_passed']=False;reject(lambda:host_power_context(bad,current))
        bad=json.loads(json.dumps(candidate));bad['retained_source_commit']='0'*40;reject(lambda:host_power_context(bad,current))
        unapproved=dict(current);unapproved['note10/device_test/v130_usb_gadget.inc']='0'*64
        bad=json.loads(json.dumps(candidate));bad['source_sha256']=unapproved;reject(lambda:host_power_context(bad,unapproved))
        bad=json.loads(json.dumps(candidate));bad['retained_gadget_link_continuation']['source_sha256']['note10/device_test/v130_kernel.c']='0'*64
        reject(lambda:host_power_context(bad,current))
        bad=json.loads(json.dumps(candidate));bad['source_contract_PASS']['source_sha256']['note10/device_test/v130_prepare.py']='0'*64
        reject(lambda:host_power_context(bad,current))
        bad=json.loads(json.dumps(candidate));bad['passed']=True;reject(lambda:host_power_context(bad,current))
        if current!=source_pins():raise ValueError('reviewed admission delta changed')
        result.update(passed=True,production_admission_validator_tested=True,link_runtime_fixture_added=False,prior32_retested=False,
            original_PASS_chain_rewritten=False,physical_ready=False,cases=['accept pending compile with exact retained32','reject invented native success',
            'reject failed source contract','reject wrong retained commit','reject changed no-bound-driver gate','reject rebound prior PASS','reject wrong delta map','reject generic new PASS overclaim'])
    except Exception:
        import traceback
        result['error']=traceback.format_exc()
    save(out/'result.json',result)
    if result['passed']:
        candidate['source_contract_PASS']['result_sha256']=sha(out/'result.json');host_power_context(candidate,current)
        save(out/'public-host-power-continuation.json',candidate)
        (out/'public-host-power-continuation.b64').write_bytes(base64.b64encode(json.dumps(candidate,separators=(',',':')).encode())+b'\n')
    return 0 if result['passed'] else 1

if __name__=='__main__':raise SystemExit(main())
