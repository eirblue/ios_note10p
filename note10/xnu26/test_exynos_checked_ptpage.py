"""Only the new actual production checked-page component, under controlled native stubs."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import unittest
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
SOURCES=('exynos_checked_ptpage.c','exynos_checked_ptpage_fixture.c','test_exynos_checked_ptpage.py',
         'prepare_exynos_checked_ptpage.py','patches/0013-exynos9825-checked-dynamic-ptpage.patch')
CASE_IDS=('test_first_allocations_before_avail_end_initialization',
          'test_raw_and_dynamic_refusals_before_conversion_or_write',
          'test_capped_full_page_loop_and_final_refusal')

class CheckedPagesTests(unittest.TestCase):
    compiles=0
    executions=[]
    @classmethod
    def setUpClass(cls):
        cls.executable=cls.output/'checked-ptpage-fixture'
        compiler=subprocess.check_output(['xcrun','--find','clang'],text=True).strip()
        command=[compiler,'-std=c11','-O2','-Wall','-Wextra','-Werror','-I',str(HERE),
                 str(HERE/'exynos_checked_ptpage_fixture.c'),'-o',str(cls.executable)]
        cls.compiles+=1
        result=subprocess.run(command,capture_output=True,text=True)
        (cls.output/'compile.log').write_text(result.stdout+result.stderr)
        (cls.output/'compile-command.json').write_text(json.dumps(command,indent=2)+'\n')
        if result.returncode:raise RuntimeError('new production checked allocator fixture compilation failed')
    def run_mode(self,mode):
        result=subprocess.run([str(self.executable),mode],capture_output=True,text=True)
        (self.output/(mode+'.stdout')).write_text(result.stdout)
        (self.output/(mode+'.stderr')).write_text(result.stderr)
        self.assertEqual(result.returncode,0,result.stderr)
        record=json.loads(result.stdout)
        self.assertEqual(record['mode'],mode)
        self.assertTrue(record['success'])
        self.assertGreater(record['checks'],0)
        type(self).executions.append(record)
    def test_first_allocations_before_avail_end_initialization(self):
        self.run_mode('first')
    def test_raw_and_dynamic_refusals_before_conversion_or_write(self):
        self.run_mode('refusals')
    def test_capped_full_page_loop_and_final_refusal(self):
        self.run_mode('loop')

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--case',action='append',choices=CASE_IDS)
    a=p.parse_args();out=a.output.resolve();private=(ROOT/'note10/private').resolve()
    if out==private or not out.is_relative_to(private) or out.exists():p.error('fresh private output required')
    selected=a.case if a.case is not None else json.loads(os.environ.get('N10_CI_CASE_JSON','[]'))
    if (type(selected) is not list or not selected or len(selected)!=len(set(selected)) or
        any(n not in CASE_IDS for n in selected)):p.error('explicit closed NEW case selection required')
    out.mkdir(parents=True);CheckedPagesTests.output=out
    result=unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(CheckedPagesTests(n) for n in selected))
    failed={t._testMethodName for t,_ in result.failures+result.errors if hasattr(t,'_testMethodName')}
    complete=result.testsRun==len(selected)
    report=dict(kind='v94-new-production-checked-ptpage',selected=selected,
        passed=[n for n in selected if n not in failed] if complete else [],tests_run=result.testsRun,
        failed=sorted(failed),success=result.wasSuccessful() and complete and not result.skipped,
        fixture_compiles=CheckedPagesTests.compiles,executions=CheckedPagesTests.executions,
        source_sha256={n:hashlib.sha256((HERE/n).read_bytes()).hexdigest() for n in SOURCES},
        ci_context={k:os.environ.get(k,'') for k in ('GITHUB_SHA','GITHUB_RUN_ID','GITHUB_RUN_ATTEMPT',
          'GITHUB_JOB','GITHUB_WORKFLOW_REF','GITHUB_WORKFLOW_SHA','GITHUB_REPOSITORY')},
        new_production_C_host_executed=bool(CheckedPagesTests.executions),PC_only=True,
        physical_ready=False,whole_XNU_kernel_entry_executed=False,hardware_XNU_executed=False,
        old_tests_executed=0,device_operations=[])
    (out/'result.json').write_text(json.dumps(report,indent=2)+'\n')
    return 0 if report['success'] else 1
if __name__=='__main__':raise SystemExit(main())
