"""Only v76 same-FDT firmware-timebase cases; no prior suites imported."""
import argparse
from contextlib import redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch

import linux_cpu_adt as bridge

FREQUENCY = 0x12345678


def node(name, properties=(), children=()):
    return name, list(properties), list(children)


def timer(compatible=b'arm,armv8-timer\0', frequency=struct.pack('>I', FREQUENCY),
          status=None, name='timer', extra=()):
    properties = [('compatible', compatible)]
    if frequency is not None:
        properties.append(('clock-frequency', frequency))
    if status is not None:
        properties.append(('status', status))
    return node(name, [*properties, *extra])


def tree(timers=(), affinities=(7,), extra=()):
    cpus = [node(f'cpu@{value:x}', [('device_type', b'cpu\0'), ('reg', struct.pack('>I', value))])
            for value in affinities]
    return node('', children=[node('cpus', [('#address-cells', struct.pack('>I', 1)),
                                           ('#size-cells', bytes(4))], cpus), *timers, *extra])


def fdt(root):
    """Synthetic token producer; no live input or old test helpers."""
    strings, body, offsets = bytearray(), bytearray(), {}
    def visit(entry):
        name, properties, children = entry
        body.extend(struct.pack('>I', 1) + name.encode('ascii') + b'\0')
        body.extend(bytes(-len(body) & 3))
        for name, value in properties:
            if name not in offsets:
                offsets[name] = len(strings)
                strings.extend(name.encode('ascii') + b'\0')
            body.extend(struct.pack('>III', 3, len(value), offsets[name]))
            body.extend(value)
            body.extend(bytes(-len(body) & 3))
        for child in children:
            visit(child)
        body.extend(struct.pack('>I', 2))
    visit(root)
    body.extend(struct.pack('>I', 9))
    return (struct.pack('>10I', 0xd00dfeed, 56 + len(body) + len(strings),
                        56, 56 + len(body), 40, 17, 16, 0, len(strings), len(body))
            + bytes(16) + body + strings)


def expected_fragment(affinities=(7,), frequency=None):
    # Independent wire expectation for the new optional property; no decoder run.
    def adt(name, properties=(), children=()):
        properties = [('name', name.encode('ascii') + b'\0'), *properties]
        raw = struct.pack('<II', len(properties), len(children))
        for key, value in properties:
            raw += key.encode('ascii').ljust(32, b'\0') + struct.pack('<I', len(value))
            raw += value + bytes(-len(value) & 3)
        return raw + b''.join(children)
    cpus = []
    for value in sorted(affinities):
        properties = [('device_type', b'cpu\0'), ('reg', struct.pack('<I', value))]
        if frequency is not None:
            properties.append(('timebase-frequency', struct.pack('<I', frequency)))
        cpus.append(adt(f'cpu@{value:x}', properties))
    return adt('device-tree', children=[adt('cpus', children=cpus)])


class FirmwareTimebaseTests(unittest.TestCase):
    def test_v8_global_declaration_exact_le32_on_each_cpu(self):
        raw = fdt(tree([timer(compatible=b'vendor,synthetic-counter\0arm,armv8-timer\0')],
                       affinities=(0x1002, 7)))
        fragment, metadata = bridge.translate(raw, include_firmware_timebase=True)
        self.assertEqual(fragment, expected_fragment((0x1002, 7), FREQUENCY))
        self.assertEqual(metadata['policy'], bridge.TIMEBASE_POLICY)
        self.assertFalse(metadata['handoff_ready'])
        self.assertFalse(metadata['cpu_execution_state_known'])
        self.assertEqual(metadata['firmware_timebase']['frequency_hz'], FREQUENCY)
        self.assertFalse(metadata['firmware_timebase']['measured'])
        self.assertFalse(metadata['firmware_timebase']['cntfrq_observed'])
        self.assertFalse(metadata['firmware_timebase']['cross_capture_join'])

    def test_v7_exact_available_statuses(self):
        for status in (b'ok\0', b'okay\0'):
            with self.subTest(status=status):
                fragment, _ = bridge.translate(fdt(tree([timer(compatible=b'arm,armv7-timer\0', status=status)])),
                                               include_firmware_timebase=True)
                self.assertEqual(fragment, expected_fragment(frequency=FREQUENCY))

    def test_default_ignores_new_timer_fields(self):
        raw = fdt(tree([timer(compatible=b'arm,armv8-timer', frequency=bytes(4), status=b'disabled\0')]))
        fragment, metadata = bridge.translate(raw)
        self.assertEqual(fragment, expected_fragment())
        self.assertEqual(metadata['policy'], bridge.POLICY)
        self.assertNotIn('firmware_timebase', metadata)

    def test_missing_architected_timer_rejected(self):
        with self.assertRaisesRegex(ValueError, '^FDT requires one architected system timer declaration$'):
            bridge.translate(fdt(tree()), include_firmware_timebase=True)

    def test_mmio_timer_only_rejected(self):
        with self.assertRaisesRegex(ValueError, '^FDT requires one architected system timer declaration$'):
            bridge.translate(fdt(tree([timer(compatible=b'arm,armv7-timer-mem\0')])),
                             include_firmware_timebase=True)

    def test_mixed_cp15_and_mmio_compatible_rejected(self):
        with self.assertRaisesRegex(ValueError, '^FDT ambiguous architected timer kind$'):
            bridge.translate(fdt(tree([timer(compatible=b'arm,armv8-timer\0arm,armv7-timer-mem\0')])),
                             include_firmware_timebase=True)

    def test_multiple_candidates_rejected_even_if_one_disabled(self):
        timers = [timer(), timer(compatible=b'arm,armv7-timer\0', name='other-timer', status=b'disabled\0')]
        with self.assertRaisesRegex(ValueError, '^FDT requires one architected system timer declaration$'):
            bridge.translate(fdt(tree(timers)), include_firmware_timebase=True)

    def test_malformed_compatible_lists_scoped_to_timer_candidates(self):
        for compatible in (b'', b'vendor,\xff\0', b'vendor,\n\0'):
            with self.subTest(unrelated_compatible=compatible):
                extra = [node('unrelated', [('compatible', compatible)])]
                fragment, _ = bridge.translate(fdt(tree([timer()], extra=extra)), include_firmware_timebase=True)
                self.assertEqual(fragment, expected_fragment(frequency=FREQUENCY))
        for compatible in (b'arm,armv8-timer', b'arm,armv8-timer\0\0',
                           b'arm,armv8-timer\0arm,armv8-timer\0'):
            with self.subTest(candidate_compatible=compatible):
                extra = [node('candidate', [('compatible', compatible)])]
                with self.assertRaisesRegex(ValueError, '^FDT compatible string list$'):
                    bridge.translate(fdt(tree([timer()], extra=extra)), include_firmware_timebase=True)

    def test_unrelated_space_compatible_preserves_timebase(self):
        extra = [node('unrelated', [('compatible', b'vendor,synthetic block with spaces\0'),
                                    ('clock-frequency', b'not-a-timer'), ('status', b'disabled\0')])]
        fragment, _ = bridge.translate(fdt(tree([timer()], extra=extra)), include_firmware_timebase=True)
        self.assertEqual(fragment, expected_fragment(frequency=FREQUENCY))

    def test_supported_timer_membership_exact_not_prefix(self):
        for compatible in (b'arm,armv8-timer-extra\0', b'prefix-arm,armv7-timer\0'):
            with self.subTest(compatible=compatible):
                lookalike = timer(compatible=compatible, name='lookalike')
                fragment, _ = bridge.translate(fdt(tree([timer(), lookalike])), include_firmware_timebase=True)
                self.assertEqual(fragment, expected_fragment(frequency=FREQUENCY))

    def test_disabled_or_malformed_status_rejected(self):
        for status in (b'disabled\0', b'okay', b'okay\0extra\0', b'', b'unknown\0'):
            with self.subTest(status=status):
                with self.assertRaisesRegex(ValueError, '^FDT architected timer unavailable or malformed status$'):
                    bridge.translate(fdt(tree([timer(status=status)])), include_firmware_timebase=True)

    def test_missing_or_invalid_frequency_rejected(self):
        for frequency in (None, b'', bytes(4), b'\x01\x02\x03', struct.pack('>Q', FREQUENCY)):
            with self.subTest(frequency=frequency):
                with self.assertRaisesRegex(ValueError, '^FDT explicit nonzero BE32 timer clock-frequency required$'):
                    bridge.translate(fdt(tree([timer(frequency=frequency)])), include_firmware_timebase=True)

    def test_duplicate_timer_property_rejected_without_output(self):
        with tempfile.TemporaryDirectory(prefix='v76-synthetic-', dir=bridge.PRIVATE_ROOT) as scratch:
            source, output = Path(scratch) / 'synthetic.dtb', Path(scratch) / 'rejected'
            raw = fdt(tree([timer(extra=[('clock-frequency', struct.pack('>I', FREQUENCY))])]))
            source.write_bytes(raw)
            with self.assertRaisesRegex(ValueError, '^FDT duplicate property name$'):
                bridge.build(source, hashlib.sha256(raw).hexdigest(), output, include_firmware_timebase=True)
            self.assertFalse(output.exists())

    def test_cli_manifest_and_stdout_keep_declaration_private(self):
        with tempfile.TemporaryDirectory(prefix='v76-synthetic-', dir=bridge.PRIVATE_ROOT) as scratch:
            source, output = Path(scratch) / 'synthetic.dtb', Path(scratch) / 'result'
            raw = fdt(tree([timer()]))
            source.write_bytes(raw)
            stdout = io.StringIO()
            argv = ['linux_cpu_adt.py', '--input', str(source), '--input-sha256', hashlib.sha256(raw).hexdigest(),
                    '--output', str(output), '--include-firmware-timebase']
            with patch.object(sys, 'argv', argv), redirect_stdout(stdout):
                bridge.main()
            manifest = json.loads((output / 'manifest.json').read_text(encoding='utf-8'))
            self.assertEqual((output / 'cpu-description.adt').read_bytes(), expected_fragment(frequency=FREQUENCY))
            self.assertEqual(manifest['firmware_timebase']['frequency_hz'], FREQUENCY)
            self.assertFalse(manifest['firmware_timebase']['measured'])
            self.assertFalse(manifest['handoff_ready'])
            self.assertEqual(json.loads(stdout.getvalue()),
                             {'policy': bridge.TIMEBASE_POLICY, 'cpu_count': 1, 'handoff_ready': False})


CASE_IDS = (
    'test_v8_global_declaration_exact_le32_on_each_cpu',
    'test_v7_exact_available_statuses',
    'test_default_ignores_new_timer_fields',
    'test_missing_architected_timer_rejected',
    'test_mmio_timer_only_rejected',
    'test_mixed_cp15_and_mmio_compatible_rejected',
    'test_multiple_candidates_rejected_even_if_one_disabled',
    'test_malformed_compatible_lists_scoped_to_timer_candidates',
    'test_unrelated_space_compatible_preserves_timebase',
    'test_supported_timer_membership_exact_not_prefix',
    'test_disabled_or_malformed_status_rejected',
    'test_missing_or_invalid_frequency_rejected',
    'test_duplicate_timer_property_rejected_without_output',
    'test_cli_manifest_and_stdout_keep_declaration_private',
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    parser.add_argument('--case', action='append', choices=CASE_IDS, required=True,
                        help='Explicit changed/new method selection; no default full-suite run')
    args = parser.parse_args()
    selected = args.case
    if len(selected) != len(set(selected)):
        parser.error('Duplicate case selection')
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=False)
    result = unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(FirmwareTimebaseTests(name) for name in selected))
    failed = [test._testMethodName for test, _ in result.failures]
    errors = [test._testMethodName for test, _ in result.errors]
    skipped = [test._testMethodName for test, _ in result.skipped]
    complete = result.testsRun == len(selected)
    unsuccessful = set(failed + errors + skipped)
    passed = [name for name in selected if name not in unsuccessful] if complete else []
    sources = [Path(__file__), Path(bridge.__file__)]
    receipt = dict(kind='v77-selected-changed-new-timer-compatible-cases', selected=selected, passed=passed,
                   failed=failed, errors=errors, skipped=skipped, tests_run=result.testsRun,
                   old_suites_executed=0, device_calls=0,
                   source_sha256={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
                   success=complete and result.wasSuccessful() and not skipped)
    (output / 'result.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
    return 0 if receipt['success'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
