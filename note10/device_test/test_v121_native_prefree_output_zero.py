"""One NEW actual native prefree full-capacity observation fixture; no real decoder/device."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

import native_prefree_output_zero as scoped
import kernel_readonly_input as physical
import sha256_kat_device_profile as profile
import stage_phase2

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
METHOD='test_actual_native_prefree_output_scan_and_cleanup'
SCOPE='v121-native-prefree-output-zero-candidate-pc-first'
CAPS={'local_tests': 0, 'local_C_compiles': 0, 'CI': 1, 'new_grouped_methods': 1, 'new_fixture_compiles': 1, 'new_fixture_processes': 1, 'old_fixture_runs': 0, 'old_methods': 0, 'native_target_builds': 1, 'kernel_builds': 1, 'Image_builds': 1, 'real_decoder': 0, 'MachO': 0, 'private_payload': 0, 'Linux_integration': 1, 'target_RAM_reservation': 0, 'device_queries': 0, 'BOOT_writes': 0, 'reboots': 0, 'max_requested_PC_payload_bytes': 4096}
OUTPUT=None
INPUTS=('note10/device_test/native_prefree_output_zero.py','note10/device_test/native_prefree_output_zero.h',
    'note10/device_test/native_prefree_output_zero_fixture.c','note10/device_test/test_v121_native_prefree_output_zero.py',
    'note10/device_test/linux_data_carrier.c','note10/device_test/build_builtin_init_image.py',
    'note10/device_test/build_kernel_readonly_span_candidate.py','note10/device_test/kernel_readonly_span_candidate.py',
    'note10/device_test/kernel_readonly_input.py','note10/device_test/sha256_kat_device_profile.py',
    '.github/workflows/note10-linux-data-carrier.yml','note10/device_test/carrier_lzma.h',
    'note10/device_test/kernel_readonly_span_candidate.h','note10/device_test/kernel_readonly_span.h','note10/device_test/readonly_stage_witness.h','note10/device_test/native_scoped_output.py','note10/device_test/native_scoped_output.h')


def save(path,row):Path(path).write_text(json.dumps(row,sort_keys=True,indent=2)+'\n',encoding='utf-8')


class NativePrefreeOutputTests(unittest.TestCase):
    compiles=0
    processes=0

    def test_actual_native_prefree_output_scan_and_cleanup(self):
        executable=OUTPUT/'native-prefree-output-zero-fixture'
        command=['clang-14','-std=gnu11','-O2','-Wall','-Wextra','-Werror',str(HERE/'native_prefree_output_zero_fixture.c'),'-o',str(executable)]
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
        self.assertEqual(json.loads(ran.stdout),dict(schema='n10-native-prefree-output-zero-fixture-v1',cases=5,
            allocation_attempts=10,allocation_successes=9,free_calls=9,scan_reads=128,independent_free_boundary_reads=128,
            nonzero_bytes_negative_case=2,emit_frames=20,partial_decode_written=7,partial_allocated_capacity=32,
            handle_bytes=24,outcome_bytes=128,state_bytes=88,scratch_bytes=448,actual_n10_data_run_and_emit=True,
            synthetic_only=True,exact_cleanup=True,after_free_reads=0,secure_erasure_attested=False,
            real_decoder_calls=0,native_allocator_executed=False,hardware_operations=0))
        rows=[dict(diagnostic_kind=scoped.KIND),dict(data_input_kind=scoped.KIND),dict(prefree_output_schema=scoped.SCHEMA),
            dict(diagnostic_kind=scoped.KIND,prefree_output_schema=scoped.SCHEMA)]
        for row in rows:
            row.update(PC_only=False,physical_ready=True,admission_blocked=False)
            with self.subTest(current_admission=sorted(row)):
                with self.assertRaisesRegex(ValueError,'no current offline/device admission'):physical.require_device_scope(row,True)
                with self.assertRaisesRegex(ValueError,'no current offline/device admission'):profile.physical_input_scope(row)
        packages=OUTPUT/'synthetic-guard';packages.mkdir();save(packages/'package-result.json',rows[-1])
        with patch('stage_phase2.verify_packages',return_value=[]),patch('stage_phase2.preflight',side_effect=AssertionError('no transport')) as transport:
            with self.assertRaisesRegex(ValueError,'no current offline/device admission'):stage_phase2.stage(packages,object(),ack_kernel_readonly_growth=True)
            self.assertEqual(transport.call_count,0)
        save(OUTPUT/'guard-summary.json',dict(schema=scoped.SCHEMA,diagnostic_kind=scoped.KIND,producer_PC_only=False,
            operation_scope_PC_only=True,physical_ready=False,current_admission_blocked=True,guard_cases=4,
            no_PC_format_promotion=True,no_persistent_output=True,hardware_ownership_attested=False,after_free_observation=False,secure_erasure_attested=False,
            native_runtime_executed=False,actual_device_operations=[],old_methods_run=0,old_fixture_runs=0,real_decoder_calls=0))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--scope',required=True,choices=(SCOPE,));parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();OUTPUT=args.output.resolve()
    if not OUTPUT.is_relative_to((ROOT/'note10/private').resolve()):raise ValueError('private CI synthetic output required')
    OUTPUT.mkdir(parents=True,exist_ok=False)
    save(OUTPUT/'source-sha256.json',{name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in INPUTS})
    result=unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite([NativePrefreeOutputTests(METHOD)]))
    save(OUTPUT/'result.json',dict(schema='v121-native-prefree-output-zero-candidate-test-v1',scope=args.scope,selected=[METHOD],run=result.testsRun,
        errors=len(result.errors),failures=len(result.failures),passed=result.wasSuccessful(),fixture_compiles=NativePrefreeOutputTests.compiles,
        fixture_processes=NativePrefreeOutputTests.processes,Image_builds=0,kernel_compiles=0,real_decoder_calls=0,MachO_replays=0,
        actual_private_inputs=0,actual_device_operations=[],old_methods_run=0,old_fixture_runs=0,caps=CAPS,
        error_tracebacks=[dict(test=test.id(),traceback=trace) for test,trace in result.errors],
        failure_tracebacks=[dict(test=test.id(),traceback=trace) for test,trace in result.failures]))
    raise SystemExit(0 if result.wasSuccessful() else 1)
