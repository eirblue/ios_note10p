"""Compile one portable decoder DLL and run only explicitly selected new cases."""
import argparse
import ctypes
import json
import lzma
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import current_data_carrier as carrier


class CurrentDataCarrierTests(unittest.TestCase):
    output = None
    decoder = None

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=self.output)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        scoped = patch.object(carrier, 'PRIVATE_ROOT', self.root)
        scoped.start()
        self.addCleanup(scoped.stop)

    @staticmethod
    def sample():
        return bytes(range(256))*13 + b'repeated-new-carrier-fixture'*80

    @staticmethod
    def stream(data):
        original = lzma.compress(data, format=lzma.FORMAT_ALONE, preset=6)
        return carrier.finite_stream(original, len(data))

    def fixture(self, name='input'):
        directory = self.root/name
        directory.mkdir()
        data = self.sample()
        original = lzma.compress(data, format=lzma.FORMAT_ALONE, preset=6)
        manifest = dict(schema=1, purpose='current-source-payload-preparation', fits_budget=True,
            carrier_admitted=False, deployment_ready=False, device_operations=[], xnu_executed=False,
            compressed_file='kernel.mem.lzma', payload_file='kernel.mem',
            compression=dict(format='LZMA_ALONE', preset=6, streams=1, padding_bytes=0),
            carrier_budget_bytes=8192, compressed_bytes=len(original), compressed_sha256=carrier.sha(original),
            payload_bytes=len(data), payload_sha256=carrier.sha(data), ci_context={'synthetic': 'only'},
            producer_result_sha256='a'*64, producer_context_sha256='b'*64,
            producer_id='c'*64, input_binding='d'*64)
        (directory/'kernel.mem.lzma').write_bytes(original)
        path = directory/'payload-fit.json'
        path.write_text(json.dumps(manifest))
        return dict(payload_manifest=path, payload_manifest_sha256=carrier.sha(path.read_bytes()),
                    budget=8192, output=directory/'prepared', decoder=self.decoder), data, original

    def test_finite_header_eos_and_container_data_identity(self):
        args, data, original = self.fixture()
        before = self.decoder.calls
        report = carrier.produce(**args)
        self.assertEqual(self.decoder.calls-before, 1)
        self.assertEqual(report['decoded_sha256'], carrier.sha(data))
        self.assertEqual(report['decoded_bytes'], len(data))
        self.assertEqual(report['decoder_calls'], 1)
        raw = (args['output']/'carrier.data').read_bytes()
        stream, size, expected = carrier.carrier_slice(raw, args['budget'])
        self.assertEqual(size, len(data))
        self.assertEqual(expected, carrier.sha(data))
        self.assertEqual(stream[:5], original[:5])
        self.assertEqual(stream[13:], original[13:])
        self.assertEqual(len(raw), args['budget'])
        self.assertFalse(report['carrier_admitted'])
        self.assertFalse(report['deployment_ready'])
        self.assertEqual({p.name for p in args['output'].iterdir()}, {'carrier.data', 'carrier-manifest.json'})

    def test_truncation_and_early_eos_fail_with_bounded_counts(self):
        data = self.sample()
        stream = self.stream(data)
        for length in (0, 1, 12, 13, 17, 18, len(stream)//2):
            facts, decoded = self.decoder.invoke(stream[:length], len(data))
            self.assertNotEqual(facts['status'], 0, length)
            self.assertLessEqual(facts['consumed'], length)
            self.assertLessEqual(facts['written'], len(data))
            self.assertEqual(decoded, b'')
        longer = stream[:5] + (len(data)+1).to_bytes(8, 'little') + stream[13:]
        facts, _ = self.decoder.invoke(longer, len(data)+1)
        self.assertEqual(facts['status'], -7)
        self.assertEqual(facts['written'], len(data))

    def test_properties_dictionary_header_and_output_caps(self):
        data = self.sample()
        stream = self.stream(data)
        variants = [bytes([0])+stream[1:], stream[:1]+(1).to_bytes(4, 'little')+stream[5:],
                    stream[:5]+b'\xff'*8+stream[13:], stream[:5]+bytes(8)+stream[13:],
                    stream[:5]+(carrier.MAX_BYTES+1).to_bytes(8, 'little')+stream[13:]]
        for value in variants:
            facts, _ = self.decoder.invoke(value, len(data))
            self.assertEqual(facts['status'], -2)
            self.assertEqual(facts['written'], 0)
        facts, _ = self.decoder.invoke(stream, len(data)-1)
        self.assertEqual(facts['status'], -4)
        repetition = self.stream(b'A'*4096)
        overrun = False
        for capacity in range(2, 9):
            short = repetition[:5]+capacity.to_bytes(8, 'little')+repetition[13:]
            facts, _ = self.decoder.invoke(short, capacity)
            self.assertIn(facts['status'], (0, -4))
            self.assertLessEqual(facts['written'], capacity)
            overrun |= facts['status'] == -4
        self.assertTrue(overrun)  # A cut inside a match must fail, never truncate into success.

    def test_workspace_and_host_allocation_failures(self):
        data = self.sample()
        stream = self.stream(data)
        for options in (dict(workspace_bytes=carrier.WORKSPACE-1), dict(workspace_offset=1)):
            facts, _ = self.decoder.invoke(stream, len(data), **options)
            self.assertEqual(facts['status'], -5)
            self.assertEqual(facts['written'], 0)
        facts, _ = self.decoder.invoke(stream, len(data), null_workspace=True)
        self.assertEqual(facts['status'], -1)
        args, _, _ = self.fixture('allocation')
        before = self.decoder.calls
        with patch.object(carrier, 'allocate_buffer', side_effect=MemoryError('synthetic allocation refusal')):
            with self.assertRaises(ValueError):
                carrier.produce(**args)
        self.assertEqual(self.decoder.calls, before)
        self.assertEqual({p.name for p in args['output'].iterdir()}, {'failure.json'})

    def test_fixed_carrier_length_padding_and_slice_bounds(self):
        data = self.sample()
        stream = self.stream(data)
        raw = carrier.container(stream, len(data), carrier.sha(data), 8192)
        variants = [raw[:-1], raw+b'\0', raw[:-1]+b'X']
        for field, replacement in ((2, 127), (3, 1), (5, 129), (6, (1 << 64)-1), (7, 0)):
            values = list(carrier.HEADER.unpack_from(raw))
            values[field] = replacement
            variants.append(carrier.HEADER.pack(*values)+raw[128:])
        values = list(carrier.HEADER.unpack_from(raw))
        values[-1] = b'X'+bytes(15)
        variants.append(carrier.HEADER.pack(*values)+raw[128:])
        before = self.decoder.calls
        for value in variants:
            with self.assertRaises(ValueError):
                carrier.carrier_slice(value, 8192)
        with self.assertRaises(ValueError):
            carrier.container(stream, len(data), carrier.sha(data), len(stream)+127)
        self.assertEqual(self.decoder.calls, before)

    def test_provenance_pins_and_fresh_output_preserve_inputs(self):
        for variant in ('manifest_pin', 'stream_pin', 'scope', 'existing'):
            args, _, _ = self.fixture(variant)
            path = args['payload_manifest']
            if variant == 'manifest_pin':
                args['payload_manifest_sha256'] = 'e'*64
            elif variant == 'stream_pin':
                stream = path.parent/'kernel.mem.lzma'
                original = stream.read_bytes()
                stream.write_bytes(original[:-1]+bytes([original[-1] ^ 1]))
            elif variant == 'scope':
                manifest = json.loads(path.read_text())
                manifest['carrier_admitted'] = True
                path.write_text(json.dumps(manifest))
                args['payload_manifest_sha256'] = carrier.sha(path.read_bytes())
            else:
                args['output'].mkdir()
                (args['output']/'keep').write_bytes(b'existing-evidence')
            inputs = {p.name: p.read_bytes() for p in path.parent.iterdir() if p.is_file()}
            before = self.decoder.calls
            with self.assertRaises(ValueError, msg=variant):
                carrier.produce(**args)
            self.assertEqual(self.decoder.calls, before)
            self.assertEqual(inputs, {p.name: p.read_bytes() for p in path.parent.iterdir() if p.is_file()})
            if variant == 'existing':
                self.assertEqual((args['output']/'keep').read_bytes(), b'existing-evidence')
            else:
                self.assertFalse(args['output'].exists())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--compiler', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--case', action='append', choices=carrier.CASE_NAMES, required=True)
    args = parser.parse_args()
    if len(args.case) != len(set(args.case)):
        parser.error('duplicate selected case')
    output = carrier.private(args.output)
    output.mkdir(parents=True, exist_ok=False)
    compiler = args.compiler.absolute()
    carrier.require(compiler.is_file() and compiler.name in ('x86_64-w64-mingw32-clang.exe', 'clang.exe'),
                    'explicit retained host compiler required')
    dll = output/'carrier_lzma.dll'
    command = [str(compiler), '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror', '-shared',
               str(carrier.ROOT/'note10/device_test/carrier_lzma.c'), '-Wl,--no-insert-timestamp', '-o', str(dll)]
    compiled = dict(command=command, compiler_path=str(compiler), compiler_stat_bytes=compiler.stat().st_size,
                    dll_file=dll.name)
    completed = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               timeout=120, check=False)
    (output/'compile.log').write_bytes(completed.stdout)
    compiled['returncode'] = completed.returncode
    if completed.returncode:
        (output/'result.json').write_text(json.dumps(dict(kind='current-data-carrier-new-tests', success=False,
            fixture_compiles=1, compiled=compiled, tests_run=0, selected=args.case, passed=[],
            failed=[], source_sha256=carrier.source_pins()), indent=2)+'\n')
        return 1
    compiled['dll_sha256'] = carrier.sha(dll.read_bytes())
    CurrentDataCarrierTests.decoder = carrier.Decoder(dll, compiled['dll_sha256'])
    CurrentDataCarrierTests.output = output
    result = unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(
        CurrentDataCarrierTests(name) for name in args.case))
    failed = {test._testMethodName for test, _ in result.failures+result.errors}
    report = dict(kind='current-data-carrier-new-tests', selected=args.case,
        passed=[n for n in args.case if n not in failed], failed=sorted(failed), tests_run=result.testsRun,
        success=result.wasSuccessful() and result.testsRun == len(args.case) and not result.skipped,
        fixture_compiles=1, compiled=compiled, source_sha256=carrier.source_pins(), synthetic=True,
        old_suites_executed=0, device_operations=[], xnu_executed=False)
    (output/'result.json').write_text(json.dumps(report, indent=2)+'\n')
    return 0 if report['success'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
