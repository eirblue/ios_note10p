"""Only v75 synthetic property-budget changes; never import the v74 suite."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import unittest
from unittest.mock import patch

import linux_cpu_adt as bridge


def node(name, properties=(), children=()):
    return name, list(properties), list(children)


def extras(count):
    return [(f'synthetic-property-{index}', b'') for index in range(count)]


def tree(root_properties=(), cpu_properties=(), parent_properties=(),
         unrelated_properties=(), descendant_properties=()):
    cpu = node('cpu@synthetic', [('device_type', b'cpu\0'), ('reg', bytes(4)), *cpu_properties],
               [node('cache', descendant_properties)] if descendant_properties else [])
    cpus = node('cpus', [('#address-cells', struct.pack('>I', 1)),
                        ('#size-cells', bytes(4)), *parent_properties], [cpu])
    return node('', root_properties, [cpus, node('auxiliary', unrelated_properties)])


def fdt(root):
    """Independent synthetic token emitter; duplicates intentionally preserved."""
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


class PropertyBudgetTests(unittest.TestCase):
    def test_wide_root_unrelated_and_deep_nodes_accepted(self):
        raw = fdt(tree(root_properties=extras(749), unrelated_properties=extras(749),
                       descendant_properties=extras(749)))
        fragment, metadata = bridge.translate(raw)
        self.assertTrue(fragment)
        self.assertEqual(metadata['cpu_count'], 1)

    def test_late_duplicate_in_wide_unrelated_node_rejected(self):
        properties = extras(749) + [('synthetic-property-0', b'')]
        with self.assertRaisesRegex(ValueError, '^FDT duplicate property name$'):
            bridge.translate(fdt(tree(unrelated_properties=properties)))

    def test_cpu_parent_128_boundary(self):
        _, metadata = bridge.translate(fdt(tree(parent_properties=extras(126))))
        self.assertEqual(metadata['cpu_count'], 1)
        with self.assertRaisesRegex(ValueError, '^FDT CPU property count$'):
            bridge.translate(fdt(tree(parent_properties=extras(127))))

    def test_cpu_child_128_boundary(self):
        _, metadata = bridge.translate(fdt(tree(cpu_properties=extras(126))))
        self.assertEqual(metadata['cpu_count'], 1)
        with self.assertRaisesRegex(ValueError, '^FDT CPU property count$'):
            bridge.translate(fdt(tree(cpu_properties=extras(127))))

    def test_duplicate_at_cpu_cap_reports_duplicate(self):
        properties = extras(126) + [('reg', bytes(4))]
        with self.assertRaisesRegex(ValueError, '^FDT duplicate property name$'):
            bridge.translate(fdt(tree(cpu_properties=properties)))

    def test_total_budget_exact_across_nodes_accepted(self):
        # Three root + two parent + two CPU + two unrelated properties = nine.
        raw = fdt(tree(root_properties=extras(3), unrelated_properties=extras(2)))
        with patch.object(bridge, 'MAX_PROPERTY_TOKENS', 9):
            _, metadata = bridge.translate(raw)
        self.assertEqual(metadata['cpu_count'], 1)

    def test_total_budget_exceeded_across_nodes_rejected(self):
        raw = fdt(tree(root_properties=extras(3), unrelated_properties=extras(2)))
        with patch.object(bridge, 'MAX_PROPERTY_TOKENS', 8):
            with self.assertRaisesRegex(ValueError, '^FDT total property token budget$'):
                bridge.translate(raw)


CASE_IDS = (
    'test_wide_root_unrelated_and_deep_nodes_accepted',
    'test_late_duplicate_in_wide_unrelated_node_rejected',
    'test_cpu_parent_128_boundary',
    'test_cpu_child_128_boundary',
    'test_duplicate_at_cpu_cap_reports_duplicate',
    'test_total_budget_exact_across_nodes_accepted',
    'test_total_budget_exceeded_across_nodes_rejected',
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    parser.add_argument('--case', action='append', choices=CASE_IDS,
                        help='Only new or affected failed cases after a correction')
    args = parser.parse_args()
    selected = list(CASE_IDS) if args.case is None else args.case
    if len(selected) != len(set(selected)):
        parser.error('Duplicate case selection')
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=False)
    suite = unittest.TestSuite(PropertyBudgetTests(name) for name in selected)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    failed = [test._testMethodName for test, _ in result.failures]
    errors = [test._testMethodName for test, _ in result.errors]
    skipped = [test._testMethodName for test, _ in result.skipped]
    unsuccessful = set(failed + errors + skipped)
    complete = result.testsRun == len(selected)
    passed = [name for name in selected if name not in unsuccessful] if complete else []
    sources = [Path(__file__), Path(bridge.__file__)]
    receipt = dict(kind='v75-new-synthetic-fdt-property-budget-cases', selected=selected,
                   passed=passed, failed=failed, errors=errors, skipped=skipped,
                   tests_run=result.testsRun, old_suites_executed=0, device_calls=0,
                   source_sha256={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
                   success=complete and result.wasSuccessful() and not skipped)
    (output / 'result.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
    return 0 if receipt['success'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
