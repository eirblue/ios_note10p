"""Focused synthetic RAMDisk declaration and boot argument integration."""
from copy import deepcopy
import struct
import unittest

from boot_adt import Node, decode, encode, encode_ramdisk_adt
from boot_contract import OFFSETS, Region


BASE = 0x12345678000
INPUTS = dict(mapped_ram=Region(BASE, 0x20000), backing=Region(BASE, 0x8000),
              physical_base=BASE + 0x1000, size=0x3000)
RAMDISK_BYTES = bytes.fromhex('00906745230100000030000000000000')


def tree_with_map():
    return Node('device-tree', {'model': b'synthetic\0'}, [
        Node('chosen', {'marker': b'keep'}, [Node('memory-map', {'other': b'keep'})]),
        Node('sibling'),
    ])


def memory_map(root):
    chosen = next(child for child in root.children if child.name == 'chosen')
    return next(child for child in chosen.children if child.name == 'memory-map')


class RamdiskAdtTests(unittest.TestCase):
    def test_existing_map_and_exact_wire_bytes(self):
        original = tree_with_map()
        before = encode(original)
        raw = encode_ramdisk_adt(original, **INPUTS)
        updated = decode(raw)
        self.assertEqual(memory_map(updated).properties, {'other': b'keep', 'RAMDisk': RAMDISK_BYTES})
        self.assertEqual(encode(updated), raw)
        self.assertEqual(encode(original), before)
        self.assertEqual(updated.properties, original.properties)
        self.assertEqual(updated.children[0].properties, original.children[0].properties)
        self.assertEqual(updated.children[1], original.children[1])

    def test_creates_memory_map_child_under_chosen(self):
        original = Node('device-tree', children=[Node('chosen', children=[Node('sibling')])])
        updated = decode(encode_ramdisk_adt(original, **INPUTS))
        self.assertEqual([child.name for child in updated.children[0].children], ['sibling', 'memory-map'])
        self.assertEqual(memory_map(updated).properties['RAMDisk'], RAMDISK_BYTES)
        self.assertEqual([child.name for child in original.children[0].children], ['sibling'])

    def test_extent_alignment_and_containment_refusals(self):
        original = tree_with_map()
        before = encode(original)
        cases = (
            {'size': 0}, {'size': 0x3001}, {'physical_base': BASE + 1},
            {'physical_base': 0, 'mapped_ram': Region(0, 0x20000), 'backing': Region(0, 0x8000)},
            {'physical_base': (1 << 64) - 0x1000},
            {'physical_base': BASE + 0x8000},
            {'mapped_ram': Region(BASE, 0x4000)},
            {'backing': Region(BASE + 0x1000, 0x8000)},
            {'backing': Region(BASE, 0x5000)},
        )
        for changes in cases:
            with self.subTest(changes=changes):
                with self.assertRaises(ValueError):
                    encode_ramdisk_adt(original, **dict(INPUTS, **changes))
                self.assertEqual(encode(original), before)

    def test_consumer_size_limit(self):
        original = tree_with_map()
        capacity = Region(BASE, 1 << 44)
        common = dict(mapped_ram=capacity, backing=capacity, physical_base=BASE)
        limit = 0xfffff000
        raw = encode_ramdisk_adt(original, size=limit, **common)
        self.assertEqual(struct.unpack('<QQ', memory_map(decode(raw)).properties['RAMDisk']), (BASE, limit))
        with self.assertRaises(ValueError):
            encode_ramdisk_adt(original, size=limit + 0x1000, **common)
        self.assertEqual(memory_map(original).properties, {'other': b'keep'})

    def test_duplicate_and_missing_path_refusals(self):
        previous = decode(encode_ramdisk_adt(tree_with_map(), **INPUTS))
        cases = (
            previous,
            Node('device-tree'),
            Node('device-tree', children=[Node('chosen'), Node('chosen')]),
            Node('device-tree', children=[Node('chosen', children=[Node('memory-map'), Node('memory-map')])]),
        )
        for original in cases:
            before = deepcopy(original)
            with self.subTest(original=original):
                with self.assertRaises(ValueError):
                    encode_ramdisk_adt(original, **INPUTS)
                self.assertEqual(original, before)

    def test_synthetic_handoff_bundle(self):
        from handoff_bundle import construct
        from test_handoff_bundle import fixture

        kernel, checked, adapter, raw, plan = fixture()
        mapped = Region(0x86000000, 0x2000000)
        backing = Region(0x87800000, 0x8000)
        disk_base, disk_size = backing.start + 0x1000, 0x3000
        adt = encode_ramdisk_adt(decode(raw), mapped_ram=mapped, backing=backing,
                                physical_base=disk_base, size=disk_size)
        plan = dict(plan, command_line='rd=md0', reserved=[dict(start=backing.start, size=backing.size)],
                    top_of_kernel=backing.end)
        manifest, files = construct(kernel, checked, adapter, adt, plan)
        args = files['boot-args.mem']
        length, = struct.unpack_from('<I', args, OFFSETS['deviceTreeLength'])
        self.assertEqual(length, len(adt))
        self.assertEqual(length, manifest['device_tree_length'])
        self.assertEqual(args[OFFSETS['CommandLine']:].split(b'\0', 1)[0], b'rd=md0')
        packed_tree = decode(files['device-tree.mem'][:length])
        self.assertEqual(struct.unpack('<QQ', memory_map(packed_tree).properties['RAMDisk']), (disk_base, disk_size))
        self.assertTrue(all(not backing.overlaps(Region(row['physical_address'], row['size']))
                            for row in manifest['buffers']))
        self.assertIs(manifest['deployment_ready'], False)
        self.assertIs(manifest['physical_reservation_verified'], False)
        self.assertEqual(manifest['device_operations'], [])


if __name__ == '__main__':
    unittest.main()
