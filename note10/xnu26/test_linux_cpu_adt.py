"""Only NEW synthetic FDT-to-CPU-fragment cases; no historical suites."""
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


def private_scratch():
    bridge.PRIVATE_ROOT.mkdir(parents=True, exist_ok=True)
    return tempfile.TemporaryDirectory(prefix='v74-synthetic-', dir=bridge.PRIVATE_ROOT)


def node(name, properties=(), children=()):
    return name, list(properties), list(children)


def cpu(value=0x123, cells=1, extra=()):
    return node('cpu@synthetic', [('device_type', b'cpu\0'),
                ('reg', value.to_bytes(cells * 4, 'big')), *extra])


def tree(cpus=None, cells=1, props=None, extra=()):
    if cpus is None:
        cpus = [cpu(cells=cells)]
    if props is None:
        props = [('#address-cells', struct.pack('>I', cells)), ('#size-cells', bytes(4))]
    return node('', children=[node('cpus', props, cpus), *extra])


def fdt(root=None):
    """Independent synthetic FDT v17 producer, including malformed duplicates."""
    strings = bytearray()
    offsets = {}
    body = bytearray()
    def word(value):
        body.extend(struct.pack('>I', value))
    def visit(entry):
        name, properties, children = entry
        word(1)
        body.extend(name.encode('ascii') + b'\0')
        body.extend(bytes(-len(body) & 3))
        for key, value in properties:
            if key not in offsets:
                offsets[key] = len(strings)
                strings.extend(key.encode('ascii') + b'\0')
            word(3)
            body.extend(struct.pack('>II', len(value), offsets[key]))
            body.extend(value)
            body.extend(bytes(-len(body) & 3))
        for child in children:
            visit(child)
        word(2)
    visit(tree() if root is None else root)
    word(9)
    header = struct.pack('>10I', 0xd00dfeed, 56 + len(body) + len(strings),
                         56, 56 + len(body), 40, 17, 16, 0, len(strings), len(body))
    return header + bytes(16) + body + strings


def change_word(raw, offset, value):
    changed = bytearray(raw)
    struct.pack_into('>I', changed, offset, value)
    return bytes(changed)


def expected_cpu_fragment(values):
    # Exact new bridge wire expectation, not a codec regression suite.
    def adt(name, properties=(), children=()):
        props = [('name', name.encode('ascii') + b'\0'), *properties]
        raw = struct.pack('<II', len(props), len(children))
        for key, value in props:
            raw += key.encode('ascii').ljust(32, b'\0') + struct.pack('<I', len(value))
            raw += value + bytes(-len(value) & 3)
        return raw + b''.join(children)
    cpus = [adt(f'cpu@{value:x}', [('device_type', b'cpu\0'), ('reg', struct.pack('<I', value))])
            for value in values]
    return adt('device-tree', children=[adt('cpus', children=cpus)])


class CpuFragmentTests(unittest.TestCase):
    def reject(self, raw):
        with self.assertRaises(ValueError):
            bridge.translate(raw)

    def test_one_cell_exact_little_endian_fragment(self):
        raw, meta = bridge.translate(fdt())
        self.assertEqual(raw, expected_cpu_fragment([0x123]))
        self.assertEqual(meta['cpu_count'], 1)

    def test_two_cell_affinity_exact_little_endian(self):
        raw, _ = bridge.translate(fdt(tree([cpu(0xfedcba98, 2)], cells=2)))
        self.assertEqual(raw, expected_cpu_fragment([0xfedcba98]))

    def test_sparse_affinities_sorted_without_renumbering(self):
        raw, _ = bridge.translate(fdt(tree([node('b', [('device_type', b'cpu\0'), ('reg', b'\0\0\x10\x02')]),
                                                   node('a', [('device_type', b'cpu\0'), ('reg', b'\0\0\0\x07')])])))
        self.assertEqual(raw, expected_cpu_fragment([7, 0x1002]))

    def test_affinity_above_u32_rejected(self):
        self.reject(fdt(tree([cpu(1 << 32, 2)], cells=2)))

    def test_duplicate_affinity_rejected(self):
        self.reject(fdt(tree([cpu(), node('different', [('device_type', b'cpu\0'), ('reg', b'\0\0\x01\x23')])])))

    def test_duplicate_node_rejected(self):
        self.reject(fdt(tree([cpu(), cpu(5)])))

    def test_duplicate_property_rejected(self):
        self.reject(fdt(tree([cpu(extra=[('reg', bytes(4))])])) )

    def test_missing_address_cells_rejected(self):
        self.reject(fdt(tree(props=[('#size-cells', bytes(4))])))

    def test_invalid_address_cells_rejected(self):
        self.reject(fdt(tree(cells=3)))

    def test_nonzero_size_cells_rejected(self):
        self.reject(fdt(tree(props=[('#address-cells', b'\0\0\0\1'), ('#size-cells', b'\0\0\0\1')])))

    def test_reg_width_mismatch_rejected(self):
        self.reject(fdt(tree([cpu(cells=2)], cells=1)))

    def test_cpu_count_32_accepted(self):
        children = [node(f'n{i}', [('device_type', b'cpu\0'), ('reg', struct.pack('>I', i))]) for i in range(32)]
        _, meta = bridge.translate(fdt(tree(children)))
        self.assertEqual(meta['cpu_count'], 32)

    def test_cpu_count_33_rejected(self):
        children = [node(f'n{i}', [('device_type', b'cpu\0'), ('reg', struct.pack('>I', i))]) for i in range(33)]
        self.reject(fdt(tree(children)))

    def test_missing_explicit_cpu_rejected(self):
        self.reject(fdt(tree([node('not-cpu', [('device_type', b'cpu\0suffix'), ('reg', bytes(4))])])))

    def test_unaligned_total_and_string_length_accepted(self):
        raw = fdt()
        # Preserve exact valid blocks; FDT strings may contain unused strings.
        padding = b'zz\0'
        raw += padding
        raw = change_word(raw, 4, len(raw))
        raw = change_word(raw, 32, struct.unpack_from('>I', raw, 32)[0] + len(padding))
        self.assertNotEqual(len(raw) % 4, 0)
        self.assertEqual(bridge.translate(raw)[1]['cpu_count'], 1)

    def test_oversize_input_rejected(self):
        self.reject(bytes(bridge.MAX_FDT + 1))

    def test_truncated_header_or_extent_rejected(self):
        self.reject(fdt()[:-1])

    def test_overlapping_blocks_rejected(self):
        self.reject(change_word(fdt(), 12, 56))

    def test_unterminated_reserve_map_rejected(self):
        raw = bytearray(fdt())
        raw[40:56] = bytes([1]) * 16
        self.reject(bytes(raw))

    def test_unknown_token_rejected(self):
        self.reject(change_word(fdt(), 56, 99))

    def test_missing_end_token_rejected(self):
        raw = fdt()
        end = 56 + struct.unpack_from('>I', raw, 36)[0] - 4
        self.reject(change_word(raw, end, 4))

    def test_bad_property_name_offset_rejected(self):
        raw = fdt()
        prop = raw.index(struct.pack('>I', 3), 56)
        self.reject(change_word(raw, prop + 8, struct.unpack_from('>I', raw, 32)[0]))

    def test_depth_limit_rejected(self):
        nested = node('leaf')
        for _ in range(32):
            nested = node('nested', children=[nested])
        self.reject(fdt(tree(extra=[nested])))

    def test_node_limit_rejected(self):
        self.reject(fdt(tree(extra=[node(f'n{i}') for i in range(4094)])))

    def test_property_limit_rejected(self):
        props = [('#address-cells', b'\0\0\0\1'), ('#size-cells', bytes(4))]
        props += [(f'p{i}', b'') for i in range(127)]
        self.reject(fdt(tree(props=props)))

    def test_execution_state_not_inferred(self):
        raw = fdt(tree([cpu(extra=[('status', b'okay\0'), ('state', b'running\0')])]))
        raw = change_word(raw, 28, 0x123)  # boot_cpuid_phys is not operational provenance.
        fragment, meta = bridge.translate(raw)
        self.assertNotIn(b'running', fragment)
        self.assertNotIn(b'state\0', fragment)
        self.assertFalse(meta['cpu_execution_state_known'])

    def test_reference_mismatch_and_full_handoff_rejected(self):
        _, meta = bridge.translate(fdt())
        self.assertEqual(meta['reference'], bridge.REFERENCE)
        self.assertFalse(meta['reference']['exact_match'])
        self.assertFalse(meta['handoff_ready'])
        self.assertFalse(meta['complete_boot_tree'])
        with self.assertRaisesRegex(ValueError, 'Full handoff unsupported'):
            bridge.translate(fdt(), require_full_handoff=True)

    def test_privacy_allowlist_excludes_identity_bootargs_mmio(self):
        sentinel = b'PRIVATE-SYNTHETIC-MARKER\0'
        raw = fdt(tree([cpu(extra=[('serial-number', sentinel), ('reg-private', sentinel)])],
                       extra=[node('chosen', [('bootargs', sentinel)]),
                              node('ethernet', [('mac-address', sentinel)]),
                              node('arm-io', [('ranges', sentinel)])]))
        fragment, meta = bridge.translate(raw)
        self.assertNotIn(sentinel, fragment)
        self.assertNotIn('PRIVATE-SYNTHETIC', json.dumps(meta))
        self.assertEqual(fragment, expected_cpu_fragment([0x123]))

    def test_build_fresh_files_and_manifest_binding(self):
        with private_scratch() as scratch:
            base = Path(scratch)
            source = base / 'synthetic.dtb'
            raw = fdt()
            source.write_bytes(raw)
            digest = hashlib.sha256(raw).hexdigest()
            meta = bridge.build(source, digest, base / 'output')
            fragment = (base / 'output/cpu-description.adt').read_bytes()
            self.assertEqual(meta['input_sha256'], digest)
            self.assertEqual(meta['fragment_sha256'], hashlib.sha256(fragment).hexdigest())
            self.assertEqual(json.loads((base / 'output/manifest.json').read_text()), meta)
            self.assertEqual(set(p.name for p in (base / 'output').iterdir()), {'cpu-description.adt', 'manifest.json'})

    def test_hash_rejection_leaves_no_output(self):
        with private_scratch() as scratch:
            base = Path(scratch)
            source = base / 'synthetic.dtb'
            source.write_bytes(fdt())
            with self.assertRaises(ValueError):
                bridge.build(source, '0' * 64, base / 'output')
            self.assertFalse((base / 'output').exists())

    def test_semantic_rejection_leaves_no_output(self):
        with private_scratch() as scratch:
            base = Path(scratch)
            source = base / 'synthetic.dtb'
            raw = fdt(tree(cpus=[]))
            source.write_bytes(raw)
            with self.assertRaises(ValueError):
                bridge.build(source, hashlib.sha256(raw).hexdigest(), base / 'output')
            self.assertFalse((base / 'output').exists())

    def test_existing_output_never_overwritten(self):
        with private_scratch() as scratch:
            base = Path(scratch)
            source = base / 'synthetic.dtb'
            raw = fdt()
            source.write_bytes(raw)
            output = base / 'output'
            output.mkdir()
            (output / 'keep').write_bytes(b'original')
            with self.assertRaises(FileExistsError):
                bridge.build(source, hashlib.sha256(raw).hexdigest(), output)
            self.assertEqual((output / 'keep').read_bytes(), b'original')
            self.assertEqual(len(list(output.iterdir())), 1)

    def test_cli_stdout_does_not_disclose_input_digest_path(self):
        with private_scratch() as scratch:
            base = Path(scratch)
            source = base / 'private-synthetic.dtb'
            raw = fdt()
            source.write_bytes(raw)
            digest = hashlib.sha256(raw).hexdigest()
            capture = io.StringIO()
            with patch.object(sys, 'argv', ['linux_cpu_adt.py', '--input', str(source),
                              '--input-sha256', digest, '--output', str(base / 'output')]), redirect_stdout(capture):
                bridge.main()
            self.assertNotIn(digest, capture.getvalue())
            self.assertNotIn(str(source), capture.getvalue())
            self.assertEqual(json.loads(capture.getvalue())['handoff_ready'], False)

    def test_output_outside_private_rejected_without_write(self):
        with tempfile.TemporaryDirectory(prefix='v74-outside-', dir=bridge.PRIVATE_ROOT.parents[1]) as scratch:
            base = Path(scratch)
            source = base / 'synthetic.dtb'
            raw = fdt()
            source.write_bytes(raw)
            with self.assertRaisesRegex(ValueError, 'Output must resolve below'):
                bridge.build(source, hashlib.sha256(raw).hexdigest(), base / 'output')
            self.assertFalse((base / 'output').exists())
            self.assertEqual(set(p.name for p in base.iterdir()), {'synthetic.dtb'})


CASE_IDS = (
    'test_one_cell_exact_little_endian_fragment',
    'test_two_cell_affinity_exact_little_endian',
    'test_sparse_affinities_sorted_without_renumbering',
    'test_affinity_above_u32_rejected',
    'test_duplicate_affinity_rejected',
    'test_duplicate_node_rejected',
    'test_duplicate_property_rejected',
    'test_missing_address_cells_rejected',
    'test_invalid_address_cells_rejected',
    'test_nonzero_size_cells_rejected',
    'test_reg_width_mismatch_rejected',
    'test_cpu_count_32_accepted',
    'test_cpu_count_33_rejected',
    'test_missing_explicit_cpu_rejected',
    'test_unaligned_total_and_string_length_accepted',
    'test_oversize_input_rejected',
    'test_truncated_header_or_extent_rejected',
    'test_overlapping_blocks_rejected',
    'test_unterminated_reserve_map_rejected',
    'test_unknown_token_rejected',
    'test_missing_end_token_rejected',
    'test_bad_property_name_offset_rejected',
    'test_depth_limit_rejected',
    'test_node_limit_rejected',
    'test_property_limit_rejected',
    'test_execution_state_not_inferred',
    'test_reference_mismatch_and_full_handoff_rejected',
    'test_privacy_allowlist_excludes_identity_bootargs_mmio',
    'test_build_fresh_files_and_manifest_binding',
    'test_hash_rejection_leaves_no_output',
    'test_semantic_rejection_leaves_no_output',
    'test_existing_output_never_overwritten',
    'test_cli_stdout_does_not_disclose_input_digest_path',
    'test_output_outside_private_rejected_without_write',
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    parser.add_argument('--case', action='append', choices=CASE_IDS,
                        help='Only unexecuted or affected failed cases on a later correction; default all NEW cases')
    args = parser.parse_args()
    selected = list(CASE_IDS) if args.case is None else args.case
    if len(selected) != len(set(selected)):
        parser.error('Duplicate case selection')
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=False)
    suite = unittest.TestSuite(CpuFragmentTests(name) for name in selected)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    failed = [test._testMethodName for test, _ in result.failures]
    errors = [test._testMethodName for test, _ in result.errors]
    skipped = [test._testMethodName for test, _ in result.skipped]
    unsuccessful = set(failed + errors + skipped)
    complete = result.testsRun == len(selected)
    passed = [name for name in selected if name not in unsuccessful] if complete else []
    sources = [Path(__file__), Path(bridge.__file__), Path(__file__).with_name('boot_adt.py')]
    receipt = dict(kind='v74-new-synthetic-cpu-fragment-cases', selected=selected,
                   passed=passed, failed=failed, errors=errors, skipped=skipped,
                   tests_run=result.testsRun, old_suites_executed=0, device_calls=0,
                   source_sha256={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
                   success=complete and result.wasSuccessful() and not skipped)
    (output / 'result.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
    return 0 if receipt['success'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
