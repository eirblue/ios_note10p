"""Negative and boundary tests for PC-side boot contract construction."""
import struct
import unittest
from boot_contract import Region, SIZE, encode_boot_args, validate_placement


def fixture():
    return dict(ram=Region(0x80000000, 0x40000000), reserved=[Region(0x80000000, 0x100000)],
                occupied=[Region(0x90000000, 0x1000000)],
                kernel=Region(0x87004000, 0x1000000), arguments=Region(0x86004000, 0x4000),
                device_tree=Region(0x86008000, 0x4000), top_of_kernel=0x88004000)


class ContractTests(unittest.TestCase):
    def args(self, **changes):
        args = dict(virtual_base=0xfffffff000000000, physical_base=0x80000000,
                    memory_size=0x40000000, top_of_kernel=0x88004000)
        args.update(changes)
        return encode_boot_args(**args)

    def test_complete_encoding(self):
        raw = self.args(device_tree_pointer=0xfffffff006008000, device_tree_length=0x1234,
                        command_line='debug=0x14e', video=(1, 2, 3, 4, 5, 6), machine_type=7)
        self.assertEqual(len(raw), SIZE)
        self.assertEqual(struct.unpack_from('<HH', raw), (2, 2))
        self.assertEqual(struct.unpack_from('<6Q', raw, 40), (1, 2, 3, 4, 5, 6))
        self.assertEqual(struct.unpack_from('<I', raw, 88), (7,))
        self.assertEqual(struct.unpack_from('<QI', raw, 96), (0xfffffff006008000, 0x1234))
        self.assertEqual(raw[108:120], b'debug=0x14e\0')
        self.assertEqual(raw[4:8] + raw[92:96] + raw[1132:1136], bytes(12))

    def test_command_line_byte_limit_and_nul(self):
        self.args(command_line='x' * 1023)
        for line in ('x' * 1024, '\0', '한' * 342):
            with self.subTest(line_length=len(line)), self.assertRaises(ValueError):
                self.args(command_line=line)

    def test_invalid_values(self):
        for changes in (dict(physical_base=-1), dict(memory_size=0),
                        dict(memory_size_actual=1), dict(boot_flags=1 << 64),
                        dict(machine_type=True), dict(top_of_kernel=0xc0000001),
                        dict(physical_base=0x80004000), dict(memory_size=0x40000001),
                        dict(virtual_base=0xfffffff000004000),
                        dict(virtual_base=(1 << 64) - 1),
                        dict(device_tree_pointer=0x1000), dict(device_tree_length=4),
                        dict(device_tree_pointer=(1 << 64) - 4, device_tree_length=8)):
            with self.subTest(changes=changes), self.assertRaises(ValueError): self.args(**changes)

    def test_range_overflow(self):
        for start, size in ((0, 0), (1 << 64, 1), ((1 << 64) - 1, 2), (0, -1)):
            with self.assertRaises(ValueError): Region(start, size)

    def test_valid_and_adjacent_ranges(self):
        plan = fixture()
        plan['reserved'].append(Region(plan['kernel'].end, 0x4000))
        result = validate_placement(**plan)
        self.assertTrue(result['layout_checks_passed'])
        self.assertFalse(result['deployment_ready'])

    def test_mapping_tail_and_multiblock_kernel(self):
        plan = fixture()
        # Real startup rounds the number of mapped L2 blocks down. The final
        # physical RAM page is not necessarily covered by bootstrap tables.
        plan['kernel'] = Region(0x87004000, 0x38000000)
        plan['top_of_kernel'] = plan['kernel'].end
        plan['occupied'] = []
        with self.assertRaises(ValueError): validate_placement(**plan)
        plan['kernel'] = Region(0x87004000, 0x2000000)
        plan['top_of_kernel'] = plan['kernel'].end
        self.assertTrue(validate_placement(**plan)['layout_checks_passed'])

    def test_conflicts(self):
        for field in ('reserved', 'occupied'):
            for allocation in ('kernel', 'arguments', 'device_tree'):
                plan = fixture(); plan[field].append(Region(plan[allocation].start + 1, 1))
                with self.subTest(field=field, allocation=allocation), self.assertRaises(ValueError):
                    validate_placement(**plan)

    def test_invalid_placement(self):
        for changes in (dict(arguments=Region(0x82004000, 0x4000)),
                        dict(arguments=Region(0x86004001, 0x4000)),
                        dict(arguments=Region(0x86004000, 1151)),
                        dict(device_tree=Region(0x86004000, 0x4000)),
                        dict(kernel=Region(0xbfffc000, 0x8000)),
                        dict(ram=Region(0x87004000, 0x1000000)),
                        dict(top_of_kernel=0x88000000), dict(top_of_kernel=0x88004001),
                        dict(occupied=None), dict(reserved=None)):
            plan = fixture(); plan.update(changes)
            with self.subTest(changes=changes), self.assertRaises(ValueError): validate_placement(**plan)


if __name__ == '__main__': unittest.main()
