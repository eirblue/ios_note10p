"""Six new PC groups for RAMDisk backing in the native boot-data band."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import struct
import sys
import unittest

from boot_adt import decode, encode_ramdisk_adt
from boot_contract import OFFSETS, Region
from handoff_bundle import ROOT, construct, load
from test_handoff_bundle import fixture


KERNEL_END = 0x87010000
BACKING = Region(0x87800000, 0x8000)
TOP = 0x8780c000


def inputs(backing=BACKING, top=TOP):
    raw, checked, adapter, adt, plan = fixture()
    adt = encode_ramdisk_adt(decode(adt), mapped_ram=Region(**plan['ram']),
                             backing=backing, physical_base=backing.start + 0x1000, size=0x3000)
    plan.update(command_line='rd=md0', reserved=[{'start': backing.start, 'size': backing.size}],
                top_of_kernel=top)
    return raw, checked, adapter, adt, plan


def save(directory, manifest, files):
    for name, data in files.items():
        (directory / name).write_bytes(data)
    (directory / 'handoff.json').write_text(json.dumps(manifest), encoding='utf-8')


def write_bundle(name, manifest, files):
    directory = OUTPUT / name
    directory.mkdir()
    save(directory, manifest, files)
    return directory


class RamdiskBootDataTests(unittest.TestCase):
    def test_1_boot_data_round_trip(self):
        data = inputs()
        before = copy.deepcopy(data)
        manifest, files = construct(*data)
        self.assertEqual(data, before)
        kernel = next(row for row in manifest['buffers'] if row['file'] == 'kernel.mem')
        self.assertEqual(kernel['physical_address'] + kernel['size'], KERNEL_END)
        self.assertEqual(set(files), {'kernel.mem', 'boot-args.mem', 'device-tree.mem', 'adapter.mem'})
        self.assertEqual(files['device-tree.mem'][:len(data[3])], data[3])
        self.assertFalse(manifest['physical_reservation_verified'])
        self.assertFalse(manifest['deployment_ready'])
        self.assertEqual(manifest['device_operations'], [])
        directory = write_bundle('boot-data', manifest, files)
        self.assertEqual(load(directory, kernel_sha256=manifest['kernel_sha256']), (manifest, files))

    def test_2_half_open_boundaries(self):
        backing = Region(KERNEL_END, 0x8000)
        manifest, files = construct(*inputs(backing, backing.end))
        self.assertEqual(struct.unpack_from('<Q', files['boot-args.mem'], OFFSETS['topOfKernelData'])[0],
                         backing.end)
        directory = write_bundle('boundaries', manifest, files)
        self.assertEqual(load(directory, kernel_sha256=manifest['kernel_sha256']), (manifest, files))

    def test_3_backing_above_or_across_top(self):
        for top in (BACKING.start, BACKING.start + 0x4000):
            with self.subTest(top=top), self.assertRaisesRegex(ValueError, 'reserved backing'):
                construct(*inputs(top=top))

    def test_4_backing_before_kernel(self):
        with self.assertRaisesRegex(ValueError, 'reserved backing'):
            construct(*inputs(Region(0x86800000, 0x8000)))

    def test_5_candidate_selection_absence_and_top_type(self):
        data = inputs()
        invalid = {'start': BACKING.start, 'size': 0x10000}
        valid = copy.deepcopy(data[-1]['reserved'][0])
        data[-1]['reserved'] = [invalid]
        with self.assertRaisesRegex(ValueError, 'reserved backing'):
            construct(*data)
        data[-1]['reserved'].append(valid)
        self.assertEqual(len(construct(*data)[1]), 4)
        absent = fixture()
        self.assertEqual(len(construct(*absent)[1]), 4)
        for top in (True, '0x8780c000'):
            changed = inputs(top=top)
            with self.subTest(top=top), self.assertRaisesRegex(ValueError, 'unsigned integer'):
                construct(*changed)

    def test_6_coherent_reload_tampering(self):
        manifest, files = construct(*inputs())
        directory = write_bundle('tampered', manifest, files)
        for change in ('lower-top', 'extend-reservation'):
            altered = copy.deepcopy(manifest)
            payloads = dict(files)
            if change == 'lower-top':
                top = BACKING.start + 0x4000
                altered['plan']['top_of_kernel'] = top
                args = bytearray(files['boot-args.mem'])
                struct.pack_into('<Q', args, OFFSETS['topOfKernelData'], top)
                payloads['boot-args.mem'] = bytes(args)
                item = next(row for row in altered['buffers'] if row['file'] == 'boot-args.mem')
                item['sha256'] = hashlib.sha256(payloads['boot-args.mem']).hexdigest()
                self.assertEqual(struct.unpack_from('<Q', payloads['boot-args.mem'],
                                                    OFFSETS['topOfKernelData'])[0],
                                 altered['plan']['top_of_kernel'])
            else:
                altered['plan']['reserved'][0]['size'] = 0x10000
                self.assertEqual(altered['buffers'], manifest['buffers'])
            save(directory, altered, payloads)
            with self.subTest(change=change), self.assertRaisesRegex(ValueError, 'reserved backing'):
                load(directory, kernel_sha256=manifest['kernel_sha256'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    OUTPUT = args.output.resolve()
    if not OUTPUT.is_relative_to((ROOT / 'note10/private').resolve()) or OUTPUT.exists():
        raise ValueError('Fresh private fixture output required')
    OUTPUT.mkdir(parents=True, exist_ok=False)
    unittest.main(argv=[sys.argv[0]])
