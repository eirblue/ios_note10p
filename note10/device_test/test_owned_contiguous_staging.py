"""Explicit NEW PC-only actual owned-output paths; no historical suite execution."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import unittest
from unittest.mock import patch
import linux_data_carrier as data
import owned_contiguous_staging as owned
from test_linux_data_carrier import LinuxDataCarrierTests, Recorded

class OwnedTests(LinuxDataCarrierTests):
    cached=None
    @classmethod
    def setUpClass(cls):
        if not cls.needs_fixture:return
        cls.fixture=cls.output/'owned-contiguous-fixture'
        command=['clang-14','-std=gnu11','-O2','-Wall','-Wextra','-Werror','-DN10_OWNED_HOST_TEST=1',
                 str(data.HERE/'linux_data_carrier_fixture.c'),'-lcrypto','-o',str(cls.fixture)]
        cls.compiles+=1
        result=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=120)
        (cls.output/'fixture-compile.log').write_bytes(result.stdout)
        (cls.output/'fixture-command.json').write_text(json.dumps(command,indent=2)+'\n')
        if result.returncode:raise RuntimeError('new owned source fixture compilation failed')
        cls.fixture_raw=cls.fixture.read_bytes()
        if cls.fixture_raw.count(data.SLOT_PREIMAGE)!=1:raise RuntimeError('one generic own-Image slot required')
        cls.fixture_slot_offset=cls.fixture_raw.index(data.SLOT_PREIMAGE)
    @staticmethod
    def sample():return bytes(owned.BYTES)
    def container(self,*args,**kwargs):
        if args or kwargs:return super().container(*args,**kwargs)
        if type(self).cached is None:type(self).cached=super().container()
        return type(self).cached
    def invoke_owned(self,raw=None,mode='good',expected=None):
        raw=self.container() if raw is None else raw
        row=self.invoke(raw,mode=mode,slot_expectation=data.sha(raw) if expected is None else expected,slot_logical=len(raw))
        path=self.root/('synthetic-carrier-%02d.stderr'%self.invocations)
        m=re.fullmatch(r'OWNED reserve=(\d+) status=(\d+) early=(\d+) direct=(\d+) cleared=(\d+) capacity=(\d+)\n',path.read_text())
        self.assertIsNotNone(m)
        row['owned']=dict(zip(('reserve','status','early','direct','cleared','capacity'),map(int,m.groups())))
        return row
    def test_reserve_failure_repeat_and_no_early_touch(self):
        for mode,status in (('reserve_fail',2),('reserve_repeat',3),('mapping_fail',2)):
            row=self.invoke_owned(mode=mode)
            self.assertEqual((row['owned']['reserve'],row['owned']['status'],row['owned']['early']),(1,status,1))
            self.assertEqual((row['status'],row['allocations'],row['calls'],row['owned']['direct']),('owned_output',0,0,0))
    def test_direct_owned_output_exact_capacity_cleanup_and_refusals(self):
        row=self.invoke_owned()
        self.assertEqual((row['status'],row['written'],row['calls']),('ok',owned.BYTES,1))
        self.assertEqual(row['digest'],data.sha(self.sample()))
        self.assertEqual((row['allocations'],row['frees'],row['cleared']),(1,1,1))
        self.assertEqual((row['owned']['early'],row['owned']['direct'],row['owned']['cleared'],row['owned']['capacity']),(1,1,1,owned.BYTES))
        for mode in ('capacity_changed','alloc1','hash3'):
            failure=self.invoke_owned(mode=mode)
            self.assertNotEqual(failure['status'],'ok')
            self.assertEqual(failure['owned']['early'],1)
            self.assertEqual(failure['owned']['cleared'],0 if mode=='capacity_changed' else 1)
        refused=self.invoke_owned(expected='a'*64)
        self.assertEqual((refused['status'],refused['allocations'],refused['calls']),('carrier_mismatch',0,0))
        small=super().container(payload=b'bounded-new-owned-capacity')
        refused=self.invoke_owned(raw=small)
        self.assertEqual((refused['status'],refused['allocations'],refused['calls']),('owned_output',0,0))
    def test_closed_pc_producer_context_default_and_relative_caps(self):
        source='a'*40
        result=dict(passed=True,Image_built=True,BOOT_built=False,version='v92',diagnostic_kind=owned.KIND,PC_only=True,physical_ready=False,
            owned_capacity_bytes=owned.BYTES,owned_alignment_bytes=owned.ALIGN,owned_default_enabled=False,
            data_expectation_mode=data.MODE,ci_context={'GITHUB_SHA':source,'GITHUB_JOB':owned.KIND,'GITHUB_RUN_ID':'1','GITHUB_RUN_ATTEMPT':'1'})
        self.assertFalse(owned.pc_contract(result,source)['physical_ready'])
        from sha256_kat_device_profile import physical_input_scope
        with self.assertRaisesRegex(ValueError,'PC-only owned staging'):
            physical_input_scope(result)
        for change in ({'physical_ready':True},{'PC_only':False},{'owned_default_enabled':True},
                       {'owned_capacity_bytes':owned.BYTES+1},{'diagnostic_kind':'linux-data-carrier'},
                       {'ci_context':dict(result['ci_context'],GITHUB_SHA='b'*40)}):
            with self.assertRaises(ValueError):owned.pc_contract(dict(result,**change),source)
        for native_check in (True,False):
            with patch.object(data,'relative_admission',return_value={'checks':{'linked_span_contained':native_check},'route_relation':{'synthetic':True}}):
                admission=owned.relative({},['CONFIG_NOTE10_OWNED_CONTIGUOUS_STAGING=y'],{'combined_state_bytes':120},elf=b'',archive=b'',raw_inputs={})
                self.assertEqual(admission['relative_eligible'],native_check)
                self.assertFalse(admission['physical_ready'])
                disabled=owned.relative({},[],{'combined_state_bytes':120},elf=b'',archive=b'',raw_inputs={})
                self.assertFalse(disabled['relative_eligible'])
                too_large=owned.relative({},['CONFIG_NOTE10_OWNED_CONTIGUOUS_STAGING=y'],{'combined_state_bytes':129},elf=b'',archive=b'',raw_inputs={})
                self.assertFalse(too_large['relative_eligible'])

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--case',action='append',choices=owned.CASE_NAMES)
    args=parser.parse_args()
    output=args.output.resolve();private=(data.HERE.parent/'private').resolve()
    if not output.is_relative_to(private) or output==private or output.exists():parser.error('fresh private output required')
    selected=args.case if args.case is not None else json.loads(os.environ.get('N10_NEW_CASES_JSON','[]'))
    if type(selected) is not list or any(n not in owned.CASE_NAMES for n in selected) or len(selected)!=len(set(selected)):parser.error('closed unique NEW case selection required')
    selected=selected or list(owned.CASE_NAMES)
    output.mkdir(parents=True);OwnedTests.output=output
    OwnedTests.needs_fixture=any(n in selected for n in owned.CASE_NAMES[:2])
    result=unittest.TextTestRunner(verbosity=2,resultclass=Recorded).run(unittest.TestSuite(OwnedTests(n) for n in selected))
    complete=result.testsRun==len(selected) and not result.framework_errors
    report=dict(kind=owned.KIND+'-new-tests',selected=selected,passed=[n for n in selected if n not in result.failed_methods] if complete else [],
        failed=sorted(result.failed_methods),framework_errors=result.framework_errors,tests_run=result.testsRun,fixture_compiles=OwnedTests.compiles,
        success=result.wasSuccessful() and complete and not result.skipped,
        source_sha256={n:data.sha((data.HERE/n).read_bytes()) for n in (*owned.SOURCES,'build_builtin_init_image.py','sha256_kat_device_profile.py')},
        ci_context={k:os.environ.get(k,'') for k in ('GITHUB_SHA','GITHUB_RUN_ID','GITHUB_RUN_ATTEMPT','GITHUB_JOB','GITHUB_WORKFLOW_REF','GITHUB_WORKFLOW_SHA')},
        PC_only=True,physical_ready=False,old_suites_executed=0,device_operations=[],xnu_executed=False)
    (output/'result.json').write_text(json.dumps(report,indent=2)+'\n')
    return 0 if report['success'] else 1

if __name__=='__main__':raise SystemExit(main())
