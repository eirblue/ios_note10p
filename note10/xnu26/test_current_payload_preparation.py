"""Selected new host adapter tests; synthetic inputs only, no historical readers."""
import argparse
import json
import lzma
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import prepare_current_payload as adapter

CASE_NAMES = (
    'test_current_producer_adapter_emits_real_payload_and_single_alone_stream',
    'test_foreign_context_or_changed_kernel_rejected_before_fresh_output',
    'test_measured_fit_failure_and_existing_output_preserve_inputs',
)


class CurrentPayloadPreparationTests(unittest.TestCase):
    output = None

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=self.output)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.scope = patch.object(adapter, 'PRIVATE_ROOT', self.root)
        self.scope.start()
        self.addCleanup(self.scope.stop)

    def fixture(self, name):
        directory = self.root / name
        directory.mkdir()
        raw = b'synthetic-current-load-data'
        source, upstream = 'a'*40, 'b'*40
        ci = adapter.expected_ci(source, '123', '1')
        producer = dict(source_commit=source, ci_context=ci, public_source_commit=upstream,
                        configuration='DEVELOPMENT_ARM64_EXYNOS9825', fresh_work_root='/synthetic/fresh-work')
        bindings = {'synthetic-config': 'c'*64}
        pid, binding = adapter.digest(producer), adapter.digest(bindings)
        context = dict(kind='v84-current-native', producer=producer, bindings=bindings,
                       producer_id=pid, input_binding=binding)
        result = dict(kind='v84-current-native-selected-link', phase='complete', passed=True,
            ci_context=ci, public_source_commit=upstream, producer_id=pid, input_binding=binding,
            architecture='arm64', mach_o_type='MH_EXECUTE', undefined_symbols=[], old_suites_executed=0,
            deployment_ready=False, hardware_verified=False, device_operations=[], candidate_archive_used=False,
            output_bytes=len(raw), output_sha256=adapter.sha(raw), entry_virtual_address='0x4000',
            segments=[dict(virtual_address=0x4000, virtual_size=0x4000, file_offset=0, file_size=len(raw))],
            link=dict(attempted=True, link_succeeded=True, returncode=0, candidate_archive_used=False,
                      producer_id=pid, input_binding=binding))
        (directory/'current-native.macho').write_bytes(raw)
        for filename, value in (('result.json', result), ('producer-context.json', context)):
            (directory/filename).write_text(json.dumps(value))
        return dict(producer_result=directory/'result.json',
            producer_sha256=adapter.sha((directory/'result.json').read_bytes()),
            context_sha256=adapter.sha((directory/'producer-context.json').read_bytes()),
            source_commit=source, ci_run_id='123', ci_run_attempt='1', public_source_commit=upstream,
            budget=32768, output=directory/'prepared')

    def test_current_producer_adapter_emits_real_payload_and_single_alone_stream(self):
        args = self.fixture('good')
        with patch.object(adapter, 'materialize_kernel', wraps=adapter.materialize_kernel) as core:
            report = adapter.prepare(**args)
        core.assert_called_once()
        payload = (args['output']/'kernel.mem').read_bytes()
        compressed = (args['output']/'kernel.mem.lzma').read_bytes()
        decoder = lzma.LZMADecompressor(format=lzma.FORMAT_ALONE)
        self.assertEqual(decoder.decompress(compressed, max_length=adapter.MAX_BYTES+1), payload)
        self.assertTrue(decoder.eof)
        self.assertEqual(decoder.unused_data, b'')
        self.assertEqual(report['payload_sha256'], adapter.sha(payload))
        self.assertTrue(report['fits_budget'])
        self.assertFalse(report['carrier_admitted'])
        self.assertFalse(report['deployment_ready'])
        self.assertEqual({p.name for p in args['output'].iterdir()},
                         {'kernel.mem', 'kernel.mem.lzma', 'payload-fit.json'})

    def test_foreign_context_or_changed_kernel_rejected_before_fresh_output(self):
        for variant in ('source', 'run', 'context', 'json_pin', 'kernel'):
            args = self.fixture(variant)
            if variant == 'source':
                args['source_commit'] = 'd'*40
            elif variant == 'run':
                args['ci_run_id'] = '456'
            elif variant == 'context':
                path = args['producer_result'].parent/'producer-context.json'
                context = json.loads(path.read_text())
                context['bindings']['synthetic-config'] = 'e'*64
                path.write_text(json.dumps(context))
                args['context_sha256'] = adapter.sha(path.read_bytes())
            elif variant == 'json_pin':
                args['producer_result'].write_text(args['producer_result'].read_text()+' ')
            else:
                path = args['producer_result'].parent/'current-native.macho'
                raw = path.read_bytes()
                path.write_bytes(b'X'+raw[1:])
            with self.assertRaises(ValueError, msg=variant):
                adapter.prepare(**args)
            self.assertFalse(args['output'].exists(), variant)

    def test_measured_fit_failure_and_existing_output_preserve_inputs(self):
        args = self.fixture('oversize')
        inputs = {p.name: p.read_bytes() for p in args['producer_result'].parent.iterdir() if p.is_file()}
        args['budget'] = 1
        report = adapter.prepare(**args)
        self.assertFalse(report['fits_budget'])
        self.assertLess(report['budget_delta_bytes'], 0)
        retained = {p.name: p.read_bytes() for p in args['output'].iterdir()}
        with self.assertRaises(ValueError):
            adapter.prepare(**args)
        self.assertEqual(retained, {p.name: p.read_bytes() for p in args['output'].iterdir()})
        self.assertEqual(inputs, {p.name: p.read_bytes() for p in args['producer_result'].parent.iterdir() if p.is_file()})


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--case', action='append', choices=CASE_NAMES, required=True)
    args = p.parse_args()
    if len(args.case) != len(set(args.case)):
        p.error('duplicate selected case')
    output = adapter.private(args.output)
    output.mkdir(parents=True, exist_ok=False)
    CurrentPayloadPreparationTests.output = output
    result = unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(
        CurrentPayloadPreparationTests(n) for n in args.case))
    failed = {test._testMethodName for test, _ in result.failures + result.errors}
    report = dict(kind='current-payload-preparation-new-tests', selected=args.case,
        passed=[n for n in args.case if n not in failed], failed=sorted(failed), tests_run=result.testsRun,
        success=result.wasSuccessful() and result.testsRun == len(args.case) and not result.skipped,
        synthetic=True, old_suites_executed=0, device_operations=[], xnu_executed=False)
    with (output/'result.json').open('x') as stream:
        stream.write(json.dumps(report, indent=2)+'\n')
    return 0 if report['success'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
