"""One NEW bounded hosted writer integration fixture; CI-only synthetic reports."""
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
METHOD='test_bounded_append_prefix_finalization_and_permanent_pc_scope'
SCOPE='v114-host-output-writer-pc'
KIND='host-output-writer-pc'
SCHEMA='n10-host-output-writer-pc-v1'
CARRIED={'note10/device_test/readonly_output_lease_pc.h': 'e9673bae4f72d1a20940e0f27e872cc8fc649eef4c197452db5cc0c8908485cf', 'note10/device_test/host_owned_output_adapter_pc.h': '060b88a1c31d2bd2e2de56058951fe281b954801b433dcdc1cd0f9e53033dbbb'}
CAPS={'local_tests': 0, 'local_C_compiles': 0, 'CI': 1, 'new_grouped_methods': 1, 'new_fixture_compiles': 1, 'new_fixture_processes': 1, 'old_fixture_runs': 0, 'old_methods': 0, 'native_target_builds': 0, 'kernel_builds': 0, 'Image_builds': 0, 'real_decoder': 0, 'MachO': 0, 'private_payload': 0, 'Linux_integration': 0, 'target_RAM_reservation': 0, 'device_queries': 0, 'BOOT_writes': 0, 'reboots': 0, 'max_requested_PC_payload_bytes': 4096}
OUTPUT=None


def save(path,row):Path(path).write_text(json.dumps(row,sort_keys=True,indent=2)+'\n',encoding='utf-8')


class HostOutputWriterPCTests(unittest.TestCase):
    compiles=0
    processes=0

    def test_bounded_append_prefix_finalization_and_permanent_pc_scope(self):
        for name,expected in CARRIED.items():self.assertEqual(hashlib.sha256((ROOT/name).read_bytes()).hexdigest(),expected)
        executable=OUTPUT/'host-output-writer-fixture'
        command=['clang-14','-std=c11','-O2','-Wall','-Wextra','-Werror','-fno-builtin-memcpy','-fno-builtin-malloc','-fno-builtin-free',
            str(HERE/'host_output_writer_pc_fixture.c'),'-o',str(executable)]
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
        self.assertEqual(report,dict(schema='n10-host-output-writer-fixture-pc-v1',passed=True,cases=5,counters_complete=True,
            allocation_attempts=7,allocations=7,frees=7,copy_calls=10,copied_bytes=4172,malloc_failure_observed=False,
            single_threaded=True,source_readability_attested=False,verification_authenticity_attested=False,
            ownership_attested=False,security_boundary=False,zeroization_proven=False,real_decoder_calls=0,hardware_operations=0))
        rows=[dict(diagnostic_kind=KIND),dict(schema=SCHEMA),dict(output_writer_schema=SCHEMA),dict(diagnostic_kind=KIND,output_writer_schema=SCHEMA)]
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
            single_threaded=True,caller_discipline_required=True,verification_still_caller_asserted=True,
            source_readability_attested=False,security_boundary=False,ownership_attested=False,target_RAM_ownership=False,
            zeroization_proven=False,malloc_failure_coverage='not_observed_not_claimed',
            permanent_kind_and_schema_refusal=True,forged_flags_refused=True,guard_cases=4,actual_device_operations=[],
            old_fixture_runs=0,old_methods_run=0,real_decoder_calls=0,Image_builds=0,kernel_compiles=0))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--scope',required=True,choices=(SCOPE,));parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();OUTPUT=args.output.resolve()
    if not OUTPUT.is_relative_to((ROOT/'note10/private').resolve()):raise ValueError('private CI synthetic output required')
    OUTPUT.mkdir(parents=True,exist_ok=False)
    names=('note10/device_test/host_output_writer_pc.h','note10/device_test/host_output_writer_pc_fixture.c',
        'note10/device_test/test_v114_host_output_writer.py','note10/device_test/kernel_readonly_input.py',
        '.github/workflows/note10-host-output-writer-pc.yml',*CARRIED)
    save(OUTPUT/'source-sha256.json',{name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in names})
    result=unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite([HostOutputWriterPCTests(METHOD)]))
    save(OUTPUT/'result.json',dict(schema='v114-host-output-writer-pc-test-v1',scope=args.scope,selected=[METHOD],run=result.testsRun,
        errors=len(result.errors),failures=len(result.failures),passed=result.wasSuccessful(),fixture_compiles=HostOutputWriterPCTests.compiles,
        fixture_processes=HostOutputWriterPCTests.processes,Image_builds=0,kernel_compiles=0,real_decoder_calls=0,MachO_replays=0,
        actual_private_inputs=0,actual_device_operations=[],old_methods_run=0,old_fixture_runs=0,diagnostic_kind=KIND,output_writer_schema=SCHEMA,
        PC_only=True,physical_ready=False,caps=CAPS,carried_dependencies=CARRIED,
        error_tracebacks=[dict(test=test.id(),traceback=trace) for test,trace in result.errors],
        failure_tracebacks=[dict(test=test.id(),traceback=trace) for test,trace in result.failures]))
    raise SystemExit(0 if result.wasSuccessful() else 1)
