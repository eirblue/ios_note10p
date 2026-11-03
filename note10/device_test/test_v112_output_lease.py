"""One NEW PC-only output-lifetime fixture; CI only, synthetic public reports."""
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
METHOD='test_new_output_offer_borrow_retire_protocol_and_nonphysical_scope'
SCOPE='v112-output-lifetime-lease-pc'
KIND='output-lifetime-lease-pc'
SCHEMA='n10-output-lifetime-lease-pc-v1'
OUTPUT=None


def save(path,row):Path(path).write_text(json.dumps(row,sort_keys=True,indent=2)+'\n',encoding='utf-8')


class OutputLeasePCTests(unittest.TestCase):
    compiles=0
    processes=0

    def test_new_output_offer_borrow_retire_protocol_and_nonphysical_scope(self):
        executable=OUTPUT/'readonly-output-lease-fixture'
        command=['clang-14','-std=c11','-O2','-Wall','-Wextra','-Werror',str(HERE/'readonly_output_lease_pc_fixture.c'),'-o',str(executable)]
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
        self.assertEqual(report,dict(schema='n10-output-lease-fixture-pc-v1',cases=5,single_threaded=True,
            one_total_borrow_per_generation=True,canaries_unchanged=True,caller_assertions_forgeable=True,copied_token_forgeable=True,
            raw_pointer_not_revoked=True,ownership_attested=False,memory_liveness_attested=False,
            real_decoder_calls=0,allocator_calls=0,cleanup_calls=0,hardware_operations=0))
        # This exact production entry guard previously had no permanent rule for this new kind.
        rows=[dict(diagnostic_kind=KIND),dict(schema=SCHEMA),dict(output_lease_schema=SCHEMA),dict(diagnostic_kind=KIND,output_lease_schema=SCHEMA)]
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
            single_threaded_logical_contract=True,owner_generation_liveness_are_caller_assertions=True,security_boundary=False,
            ownership_attested=False,memory_keepalive=False,raw_pointer_revocation=False,free_or_zeroization_semantics_proven=False,
            permanent_kind_and_schema_refusal=True,forged_flags_refused=True,guard_cases=4,actual_device_operations=[],
            old_methods_run=0,real_decoder_calls=0,Image_builds=0,kernel_compiles=0))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--scope',required=True,choices=(SCOPE,));parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();OUTPUT=args.output.resolve()
    if not OUTPUT.is_relative_to((ROOT/'note10/private').resolve()):raise ValueError('private CI synthetic output required')
    OUTPUT.mkdir(parents=True,exist_ok=False)
    names=('note10/device_test/readonly_output_lease_pc.h','note10/device_test/readonly_output_lease_pc_fixture.c',
        'note10/device_test/test_v112_output_lease.py','note10/device_test/kernel_readonly_input.py','.github/workflows/note10-output-lease-pc.yml')
    save(OUTPUT/'source-sha256.json',{name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in names})
    result=unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite([OutputLeasePCTests(METHOD)]))
    save(OUTPUT/'result.json',dict(schema='v112-output-lifetime-lease-pc-test-v1',scope=args.scope,selected=[METHOD],run=result.testsRun,
        errors=len(result.errors),failures=len(result.failures),passed=result.wasSuccessful(),fixture_compiles=OutputLeasePCTests.compiles,
        fixture_processes=OutputLeasePCTests.processes,Image_builds=0,kernel_compiles=0,real_decoder_calls=0,MachO_replays=0,
        actual_private_inputs=0,actual_device_operations=[],old_methods_run=0,diagnostic_kind=KIND,output_lease_schema=SCHEMA,PC_only=True,physical_ready=False,
        error_tracebacks=[dict(test=test.id(),traceback=trace) for test,trace in result.errors],
        failure_tracebacks=[dict(test=test.id(),traceback=trace) for test,trace in result.failures]))
    raise SystemExit(0 if result.wasSuccessful() else 1)
