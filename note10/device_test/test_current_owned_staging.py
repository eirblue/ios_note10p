"""Only new exact-current owned-capacity native and metadata paths; no old suite/core execution."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest
from unittest import mock
import current_owned_staging as current
import linux_data_carrier as data


def store(path,value):
    raw=(json.dumps(value,indent=2)+'\n').encode();path.write_bytes(raw);return data.sha(raw)


class CurrentOwnedTests(unittest.TestCase):
    compiles=0
    executions=[]
    @classmethod
    def setUpClass(cls):
        cls.fixture=cls.output/'current-owned-fixture'
        command=['clang-14','-std=gnu11','-O2','-Wall','-Wextra','-Werror','-I',str(data.HERE),
            str(data.HERE/'current_owned_staging_fixture.c'),'-lcrypto','-o',str(cls.fixture)]
        cls.compiles+=1;result=subprocess.run(command,capture_output=True)
        (cls.output/'fixture-compile.log').write_bytes(result.stdout+result.stderr)
        (cls.output/'fixture-command.json').write_text(json.dumps(command,indent=2)+'\n')
        if result.returncode:raise RuntimeError('new current-capacity fixture compilation failed')
        cls.binary=cls.fixture.read_bytes()
        if cls.binary.count(data.SLOT_PREIMAGE)!=1:raise RuntimeError('one generic own-Image slot required')
        cls.slot=cls.binary.index(data.SLOT_PREIMAGE)
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory(prefix='v96-synthetic-',dir=data.HERE.parent/'private')
        self.addCleanup(self.temporary.cleanup);self.root=Path(self.temporary.name);self.invocations=0
    def sample(self,size):
        stream=b'\x5d'+(1<<23).to_bytes(4,'little')+size.to_bytes(8,'little')+bytes(5)
        total=128+len(stream)+16
        header=struct.pack('<8sHHI4Q32s32s16s',b'N10DATA1',1,128,0,total,128,len(stream),size,
            hashlib.sha256(stream).digest(),hashlib.sha256(bytes(size)).digest(),bytes(16))
        return header+stream+bytes(16)
    def invoke(self,size=None,mode='good'):
        size=current.BYTES if size is None else size;raw=self.sample(size)
        self.invocations+=1;prefix=self.root/str(self.invocations)
        carrier=prefix.with_suffix('.data');carrier.write_bytes(raw)
        code=bytearray(self.binary)
        code[self.slot+24:self.slot+64]=hashlib.sha256(raw).digest()+len(raw).to_bytes(8,'little')
        executable=prefix.with_suffix('.fixture');executable.write_bytes(code);executable.chmod(0o700)
        result=subprocess.run([str(executable),str(carrier),mode],capture_output=True,text=True)
        prefix.with_suffix('.stdout').write_text(result.stdout);prefix.with_suffix('.stderr').write_text(result.stderr)
        self.assertEqual(result.returncode,0,result.stderr)
        row=json.loads(result.stdout);type(self).executions.append(dict(mode=mode,payload_bytes=size,**row));return row
    def test_current_capacity_direct_output_and_old_span_refusal(self):
        row=self.invoke()
        self.assertEqual((row['status'],row['capacity'],row['written'],row['calls']),('ok',current.BYTES,current.BYTES,1))
        self.assertEqual((row['reserved'],row['early'],row['allocations'],row['frees']),(1,1,1,1))
        self.assertEqual((row['output_cleared'],row['workspace_cleared'],row['guards']),(1,1,1))
        self.assertLessEqual(row['state_bytes'],128)
        row=self.invoke(size=current.legacy.BYTES)
        self.assertEqual((row['status'],row['calls'],row['allocations'],row['guards']),('owned_output',0,0,1))
    def test_current_capacity_cleanup_and_canaries(self):
        for mode,calls,zero in (('capacity_changed',0,0),('workspace_fail',0,1),('core_fail',1,1),('payload_hash_fail',1,1)):
            row=self.invoke(mode=mode)
            self.assertNotEqual(row['status'],'ok')
            self.assertEqual((row['calls'],row['output_cleared'],row['guards'],row['early']),(calls,zero,1,1))
            self.assertEqual(row['workspace_cleared'],1)
    def producer(self):
        source='1'*40
        return dict(passed=True,Image_built=True,BOOT_built=False,version='v96',diagnostic_kind=current.KIND,
            PC_only=True,physical_ready=False,owned_capacity_bytes=current.BYTES,owned_alignment_bytes=current.ALIGN,
            owned_default_enabled=False,current_owned_default_enabled=False,owned_capacity_source='current_owned_capacity.h',
            data_expectation_mode=data.MODE,ci_context=dict(GITHUB_SHA=source,GITHUB_WORKFLOW_SHA=source,
            GITHUB_RUN_ID='101',GITHUB_RUN_ATTEMPT='1',GITHUB_JOB=current.KIND,GITHUB_REPOSITORY='eirblue/ios_note10p',
            GITHUB_WORKFLOW_REF='eirblue/ios_note10p/'+current.WORKFLOW+'@refs/heads/main'))
    def host_records(self):
        ci=dict(GITHUB_SHA='2'*40,GITHUB_WORKFLOW_REF='eirblue/ios_note10p/.github/workflows/note10-exynos-checked-ptpage-pc.yml@refs/heads/main')
        context=dict(kind='v84-current-native',producer_id='3'*64,input_binding='4'*64,
            producer=dict(candidate_kind='v94-exynos-checked-ptpage-pc',source_commit='2'*40,ci_context=ci))
        inputs=dict(actual_producer_context=context,producer_context_sha256='5'*64,
            producer_result_sha256_reused_from_accepted_receipt='6'*64)
        input_path=self.root/'inputs.json';input_sha=store(input_path,inputs)
        fit=dict(current_producer_kind='v94-exynos-checked-ptpage-pc',ci_context=ci,producer_id='3'*64,
            input_binding='4'*64,producer_context_sha256='5'*64,producer_result_sha256='6'*64,
            payload_bytes=current.BYTES,PC_only=True,physical_ready=False,carrier_admitted=False)
        fit_path=self.root/'fit.json';fit_sha=store(fit_path,fit)
        made=dict(kind='v95-fresh-current-payload-carrier-pc',accepted=True,decoder_calls=1,fits_budget=True,
            payload_manifest_sha256=fit_sha,input_binding_metadata_sha256=input_sha,payload_bytes=current.BYTES,
            PC_only=True,physical_ready=False,carrier_admitted=False)
        made_path=self.root/'made.json';made_sha=store(made_path,made)
        host=dict(schema='note10-v95-host-operator-receipt-v1',actual_transform=dict(command_invocations=1,exit_code=0,
            result_path=str(made_path),result_manifest_sha256=made_sha,fit_report_path=str(fit_path),fit_report_sha256=fit_sha,
            input_binding_path=str(input_path),input_binding_sha256=input_sha))
        host_path=self.root/'host.json';return host_path,store(host_path,host),host,inputs,input_path
    def test_closed_current_profile_defaults_and_receipt_join(self):
        result=self.producer();source='1'*40
        self.assertEqual(current.legacy.BYTES,19546112)
        self.assertFalse(current.pc_contract(result,source)['physical_ready'])
        from sha256_kat_device_profile import physical_input_scope
        with self.assertRaisesRegex(ValueError,'PC-only owned staging'):
            physical_input_scope(dict(result,PC_only=False))
        for delta in ({'owned_capacity_bytes':current.legacy.BYTES},{'current_owned_default_enabled':True},
                      {'owned_default_enabled':True},{'physical_ready':True},{'diagnostic_kind':current.legacy.KIND}):
            with self.assertRaises(ValueError):current.pc_contract(dict(result,**delta),source)
        with mock.patch.object(current.legacy,'relative',return_value=dict(checks={'intrinsic_caps':True},route_relation={})):
            yes=current.relative({},['CONFIG_NOTE10_CURRENT_OWNED_STAGING=y'],{},elf=b'',archive=b'',raw_inputs={})
            self.assertTrue(yes['relative_eligible']);self.assertFalse(yes['physical_ready'])
            no=current.relative({},[],{},elf=b'',archive=b'',raw_inputs={});self.assertFalse(no['relative_eligible'])
        result_path=self.root/'producer.json';result_sha=store(result_path,result)
        host_path,host_sha,host,inputs,input_path=self.host_records()
        joined=current.join_host_payload(result_path,result_sha,source,host_receipt=host_path,host_receipt_sha256=host_sha)
        self.assertTrue(joined['new_owned_capacity_match']);self.assertFalse(joined['legacy_owned_capacity_match'])
        self.assertFalse(joined['physical_ready']);self.assertFalse(joined['global_RAM_ownership'])
        for wrong in ('v85-current-native','v93-exynos-leaf-bootstrap-pc'):
            inputs['actual_producer_context']['producer']['candidate_kind']=wrong
            host['actual_transform']['input_binding_sha256']=store(input_path,inputs)
            made_path=Path(host['actual_transform']['result_path'])
            made=json.loads(made_path.read_text())
            made['input_binding_metadata_sha256']=host['actual_transform']['input_binding_sha256']
            host['actual_transform']['result_manifest_sha256']=store(made_path,made)
            changed=store(host_path,host)
            with self.assertRaises(ValueError):
                current.join_host_payload(result_path,result_sha,source,host_receipt=host_path,host_receipt_sha256=changed)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--case',action='append',choices=current.CASE_NAMES);a=p.parse_args()
    out=a.output.resolve();private=(data.HERE.parent/'private').resolve()
    if out==private or not out.is_relative_to(private) or out.exists():p.error('fresh private output required')
    selected=a.case if a.case is not None else json.loads(os.environ.get('N10_NEW_CASES_JSON','[]'))
    if type(selected) is not list or not selected or len(selected)!=len(set(selected)) or any(n not in current.CASE_NAMES for n in selected):
        p.error('explicit unique NEW case selection required')
    out.mkdir(parents=True);CurrentOwnedTests.output=out
    result=unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(CurrentOwnedTests(n) for n in selected))
    failed={t._testMethodName for t,_ in result.failures+result.errors if hasattr(t,'_testMethodName')}
    complete=result.testsRun==len(selected)
    report=dict(kind=current.KIND+'-new-tests',selected=selected,tests_run=result.testsRun,
        passed=[n for n in selected if n not in failed] if complete else [],failed=sorted(failed),
        fixture_compiles=CurrentOwnedTests.compiles,success=result.wasSuccessful() and complete and not result.skipped,
        executions=CurrentOwnedTests.executions,source_sha256={n:data.sha((data.HERE/n).read_bytes()) for n in
        (*current.SOURCES,'owned_contiguous_staging.c','linux_data_carrier.c','carrier_lzma.h','build_builtin_init_image.py','sha256_kat_device_profile.py')},
        ci_context={k:os.environ.get(k,'') for k in ('GITHUB_SHA','GITHUB_RUN_ID','GITHUB_RUN_ATTEMPT','GITHUB_JOB','GITHUB_WORKFLOW_REF','GITHUB_WORKFLOW_SHA','GITHUB_REPOSITORY')},
        new_production_capacity_C_executed=bool(CurrentOwnedTests.executions),portable_decoder_executed=False,
        old_tests_executed=0,actual_payload_or_carrier_inputs=0,PC_only=True,physical_ready=False,
        whole_XNU_kernel_entry_executed=False,hardware_XNU_executed=False,device_operations=[])
    (out/'result.json').write_text(json.dumps(report,indent=2)+'\n')
    return 0 if report['success'] else 1
if __name__=='__main__':raise SystemExit(main())
