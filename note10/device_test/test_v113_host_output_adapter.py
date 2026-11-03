"""One NEW hosted-allocation adapter fixture; CI-only synthetic reports."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

import kernel_readonly_input as physical
import stage_phase2

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
METHOD='test_actual_host_allocation_lease_retirement_and_permanent_pc_scope'
SCOPE='v113-host-owned-output-adapter-pc'
KIND='host-owned-output-adapter-pc'
SCHEMA='n10-host-owned-output-adapter-pc-v1'
CARRIED='note10/device_test/readonly_output_lease_pc.h'
CARRIED_SHA='e9673bae4f72d1a20940e0f27e872cc8fc649eef4c197452db5cc0c8908485cf'
OUTPUT=None


def save(path,row):Path(path).write_text(json.dumps(row,sort_keys=True,indent=2)+'\n',encoding='utf-8')


class HostOutputAdapterPCTests(unittest.TestCase):
    compiles=0
    processes=0

    def test_actual_host_allocation_lease_retirement_and_permanent_pc_scope(self):
        self.assertEqual(hashlib.sha256((ROOT/CARRIED).read_bytes()).hexdigest(),CARRIED_SHA)
        executable=OUTPUT/'host-owned-output-adapter-fixture'
        command=['clang-14','-std=c11','-O2','-Wall','-Wextra','-Werror','-fno-builtin-malloc','-fno-builtin-free',
            str(HERE/'host_owned_output_adapter_pc_fixture.c'),'-o',str(executable)]
        save(OUTPUT/'fixture-command.json',command)
        type(self).compiles+=1
        built=subprocess.run(command,capture_output=True,text=True,timeout=60)
        (OUTPUT/'fixture-compile.txt').write_text(built.stdout+built.stderr,encoding='utf-8')
        self.assertEqual(built.returncode,0,built.stderr)
        type(self).processes+=1
        ran=subprocess.run([str(executable)],capture_output=True,text=True,timeout=30)
        (OUTPUT/'fixture-output.json').write_text(ran.stdout,encoding='utf-8')
        (OUTPUT/'fixture-stderr.txt').write_text(ran.stderr,encoding='utf-8')
        self.assertEqual(ran.returncode,0,ran.stderr)
        report=json.loads(ran.stdout)
        self.assertEqual(report,dict(schema='n10-host-owned-output-adapter-fixture-pc-v1',passed=True,cases=5,counters_complete=True,
            allocation_attempts=9,allocations=9,frees=9,malloc_failure_observed=False,single_threaded=True,
            caller_discipline_required=True,ownership_attested=False,security_boundary=False,payload_zeroization_proven=False,
            real_decoder_calls=0,hardware_operations=0))
        rows=[dict(diagnostic_kind=KIND),dict(schema=SCHEMA),dict(output_adapter_schema=SCHEMA),dict(diagnostic_kind=KIND,output_adapter_schema=SCHEMA)]
        for row in rows:
            row.update(PC_only=False,physical_ready=True,deployment_ready=True)
            with self.subTest(permanent_refusal=sorted(row)),self.assertRaisesRegex(ValueError,'permanently forbidden'):
                physical.require_device_scope(row,True)
        packages=OUTPUT/'synthetic-guard';packages.mkdir()
        save(packages/'package-result.json',rows[-1])
        with patch('stage_phase2.verify_packages',return_value=[]),patch('stage_phase2.preflight',side_effect=AssertionError('no transport')) as transport:
            with self.assertRaisesRegex(ValueError,'permanently forbidden'):stage_phase2.stage(packages,object(),ack_kernel_readonly_growth=True)
            self.assertEqual(transport.call_count,0)
        save(OUTPUT/'guard-summary.json',dict(schema=SCHEMA,diagnostic_kind=KIND,PC_only=True,physical_ready=False,
            single_threaded=True,caller_discipline_required=True,written_and_verified_are_caller_assertions=True,
            security_boundary=False,ownership_attested=False,target_RAM_ownership=False,physical_contiguity_proven=False,
            zeroization_proven=False,malloc_failure_coverage='not_observed_not_claimed',
            permanent_kind_and_schema_refusal=True,forged_flags_refused=True,guard_cases=4,actual_device_operations=[],
            old_fixture_runs=0,old_methods_run=0,real_decoder_calls=0,Image_builds=0,kernel_compiles=0))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--scope',required=True,choices=(SCOPE,));parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();OUTPUT=args.output.resolve()
    if not OUTPUT.is_relative_to((ROOT/'note10/private').resolve()):raise ValueError('private CI synthetic output required')
    OUTPUT.mkdir(parents=True,exist_ok=False)
    names=('note10/device_test/host_owned_output_adapter_pc.h','note10/device_test/host_owned_output_adapter_pc_fixture.c',
        'note10/device_test/test_v113_host_output_adapter.py','note10/device_test/kernel_readonly_input.py',
        '.github/workflows/note10-host-output-adapter-pc.yml',CARRIED)
    save(OUTPUT/'source-sha256.json',{name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in names})
    result=unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite([HostOutputAdapterPCTests(METHOD)]))
    save(OUTPUT/'result.json',dict(schema='v113-host-owned-output-adapter-pc-test-v1',scope=args.scope,selected=[METHOD],run=result.testsRun,
        errors=len(result.errors),failures=len(result.failures),passed=result.wasSuccessful(),fixture_compiles=HostOutputAdapterPCTests.compiles,
        fixture_processes=HostOutputAdapterPCTests.processes,Image_builds=0,kernel_compiles=0,real_decoder_calls=0,MachO_replays=0,
        actual_private_inputs=0,actual_device_operations=[],old_methods_run=0,old_fixture_runs=0,diagnostic_kind=KIND,output_adapter_schema=SCHEMA,
        PC_only=True,physical_ready=False,carried_dependency=dict(path=CARRIED,sha256=CARRIED_SHA,old_fixture_replayed=False),
        error_tracebacks=[dict(test=test.id(),traceback=trace) for test,trace in result.errors],
        failure_tracebacks=[dict(test=test.id(),traceback=trace) for test,trace in result.failures]))
    raise SystemExit(0 if result.wasSuccessful() else 1)
