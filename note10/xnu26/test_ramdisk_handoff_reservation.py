"""Six new PC groups for the RAMDisk declaration/reservation relationship."""
import argparse
import copy
import json
from pathlib import Path
import struct
import sys
import unittest

from boot_adt import Node, RAMDISK_MAX_BYTES, decode, encode, encode_ramdisk_adt
from boot_contract import Region
from handoff_bundle import ROOT, construct, load
from test_handoff_bundle import fixture


BACKING = {'start': 0x87800000, 'size': 0x8000}
DISK = (BACKING['start'] + 0x1000, 0x3000)


def inputs(size=DISK[1]):
    raw, checked, adapter, adt, plan = fixture()
    adt = encode_ramdisk_adt(decode(adt), mapped_ram=Region(0x86000000, 0x2000000),
                             backing=Region(**BACKING), physical_base=DISK[0], size=size)
    plan.update(command_line='rd=md0', reserved=[dict(BACKING)])
    return raw, checked, adapter, adt, plan


def raw_adt(value):
    return encode(Node('device-tree', children=[Node('chosen', children=[
        Node('memory-map', {'RAMDisk': value})])]))


def write_bundle(name, manifest, files):
    directory = OUTPUT / name
    directory.mkdir()
    for filename, data in files.items():
        (directory / filename).write_bytes(data)
    (directory / 'handoff.json').write_text(json.dumps(manifest), encoding='utf-8')
    return directory


class RamdiskReservationTests(unittest.TestCase):
    def test_1_valid_round_trip_and_absent_property(self):
        data = inputs()
        before = copy.deepcopy(data)
        manifest, files = construct(*data)
        self.assertEqual(data, before)
        self.assertEqual(RAMDISK_MAX_BYTES, 0xfffff000)
        self.assertEqual(set(files), {'kernel.mem', 'boot-args.mem', 'device-tree.mem', 'adapter.mem'})
        self.assertEqual(files['device-tree.mem'][:len(data[3])], data[3])
        self.assertFalse(manifest['physical_reservation_verified'])
        self.assertFalse(manifest['deployment_ready'])
        self.assertEqual(manifest['device_operations'], [])
        directory = write_bundle('valid', manifest, files)
        self.assertEqual(load(directory, kernel_sha256=manifest['kernel_sha256']), (manifest, files))
        # An absent property keeps the existing path independent of reservations.
        no_disk = list(data)
        no_disk[3] = encode(Node('device-tree', children=[Node('chosen')]))
        no_disk[4] = dict(data[4], reserved=[])
        self.assertEqual(len(construct(*no_disk)[1]), 4)

    def test_2_missing_reservation(self):
        data = inputs()
        data[-1]['reserved'] = []
        with self.assertRaisesRegex(ValueError, 'reserved backing'):
            construct(*data)

    def test_3_partial_or_wrong_reservation(self):
        for reservation in ({'start': BACKING['start'], 'size': 0x4000},
                            {'start': BACKING['start'] + 0x10000, 'size': 0x8000}):
            data = inputs(size=0x7000)
            data[-1]['reserved'] = [reservation]
            with self.subTest(reservation=reservation), self.assertRaisesRegex(ValueError, 'reserved backing'):
                construct(*data)

    def test_4_occupied_overlap(self):
        data = inputs()
        data[-1]['occupied'] = [{'start': DISK[0] + 0x2000, 'size': 0x1000}]
        with self.assertRaisesRegex(ValueError, 'occupied memory'):
            construct(*data)

    def test_5_raw_property_bypass(self):
        cases = [
            ('empty', b'', {}, 'exactly two'),
            ('short', bytes(15), {}, 'exactly two'),
            ('extra', bytes(17), {}, 'exactly two'),
            ('zero-base', struct.pack('<QQ', 0, 0x1000), {}, 'consumer byte extent'),
            ('zero-size', struct.pack('<QQ', DISK[0], 0), {}, 'Empty or overflowing'),
            ('unaligned-base', struct.pack('<QQ', DISK[0] + 1, 0x1000), {}, 'consumer byte extent'),
            ('unaligned-size', struct.pack('<QQ', DISK[0], 0x1001), {}, 'consumer byte extent'),
            ('wrapping', struct.pack('<QQ', 0xfffffffffffff000, 0x2000), {}, 'Empty or overflowing'),
            ('outside-ram', struct.pack('<QQ', 0xc0000000, 0x1000), {}, 'modeled RAM'),
            ('unaligned-backing-start', struct.pack('<QQ', *DISK),
             {'reserved': [{'start': DISK[0], 'size': 0x4000}]}, 'reserved backing'),
            ('unaligned-backing-size', struct.pack('<QQ', *DISK),
             {'reserved': [{'start': BACKING['start'], 'size': 0x7000}]}, 'reserved backing'),
            ('backing-straddles-ram', struct.pack('<QQ', *DISK),
             {'ram': {'start': 0x80000000, 'size': 0x7804000},
              'top_of_kernel': 0x87010000}, 'reserved backing'),
            ('four-gib', struct.pack('<QQ', DISK[0], 0x100000000),
             {'ram': {'start': 0x80000000, 'size': 0x200000000},
              'reserved': [{'start': BACKING['start'], 'size': 0x100004000}]}, 'consumer byte extent'),
        ]
        for name, value, delta, error in cases:
            data = list(inputs())
            data[3] = raw_adt(value)
            data[-1].update(delta)
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, error):
                construct(*data)

    def test_6_reload_plan_tampering(self):
        manifest, files = construct(*inputs())
        original = copy.deepcopy(manifest)
        directory = write_bundle('tampered-plan', manifest, files)
        for delta, error in (({'reserved': []}, 'reserved backing'),
                             ({'occupied': [{'start': DISK[0], 'size': 0x1000}]}, 'occupied memory')):
            changed = copy.deepcopy(original)
            changed['plan'].update(delta)
            self.assertEqual(changed['buffers'], original['buffers'])
            (directory / 'handoff.json').write_text(json.dumps(changed), encoding='utf-8')
            with self.subTest(delta=delta), self.assertRaisesRegex(ValueError, error):
                load(directory, kernel_sha256=original['kernel_sha256'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    OUTPUT = args.output.resolve()
    if not OUTPUT.is_relative_to((ROOT / 'note10/private').resolve()) or OUTPUT.exists():
        raise ValueError('Fresh private fixture output required')
    OUTPUT.mkdir(parents=True, exist_ok=False)
    unittest.main(argv=[sys.argv[0]])
