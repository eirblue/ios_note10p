"""Five new metadata-only cases for the source-bound memdev byte extent."""
import hashlib
from pathlib import Path
import struct
import unittest

from boot_adt import Node, decode, encode, encode_ramdisk_adt
from boot_contract import Region


ROOT = Path(__file__).resolve().parents[2]
REFERENCE = 'research/ios26/xnu-reference/xnu-ac9718fb1af618d5ce8678d0dc6e8a58f252216f/'
BASE = 0x40000000


class RamdiskConsumerExtentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sources = (
            (REFERENCE + 'bsd/dev/memdev.c', 29537,
             '4d50d2fb61096aca3ab354f402069c4ffea1f82d6b6be719518954588e97747a',
             ('uint32_t        mdSize;', 'mdev[devid].mdSize = size;',
              '*size = mdev[devid].mdSize << 12;',
              'if (blkoff >= (mdev[devid].mdSize << 12))')),
            (REFERENCE + 'iokit/bsddev/IOKitBSDInit.cpp', 51805,
             '5983503bde9fa5af3d400770efa25856805ad0cbd9c91964c93785e974085f8a',
             ('getProperty("RAMDisk")',
              '(void)mdevadd(-1, ml_static_ptovirt(ramdParms[0]) >> 12, (unsigned int) (ramdParms[1] >> 12), 0);')),
            (REFERENCE + 'bsd/arm/_types.h', 4727,
             'dea174bb0a2621285e0380e1044283d04d7911c0c0c7507ae370e154b5a2d963',
             ('typedef unsigned int            __uint32_t;',)),
        )
        for relative, size, digest, anchors in sources:
            path = ROOT / relative
            if path.stat().st_size != size:
                raise AssertionError('Reference length differs: ' + relative)
            raw = path.read_bytes()
            if hashlib.sha256(raw).hexdigest() != digest:
                raise AssertionError('Reference hash differs: ' + relative)
            text = raw.decode('utf-8')
            if any(anchor not in text for anchor in anchors):
                raise AssertionError('Consumer source anchor differs: ' + relative)

    def setUp(self):
        self.tree = Node('device-tree', {'model': b'synthetic\0'}, [
            Node('chosen', {'marker': b'keep'}, [Node('memory-map', {'other': b'keep'})]),
            Node('sibling'),
        ])
        self.before = encode(self.tree)
        capacity = Region(BASE, 1 << 34)
        self.inputs = dict(mapped_ram=capacity, backing=capacity, physical_base=BASE)

    def reject(self, size):
        with self.assertRaisesRegex(ValueError, '32-bit consumer byte extent'):
            encode_ramdisk_adt(self.tree, size=size, **self.inputs)
        self.assertEqual(encode(self.tree), self.before)

    def test_largest_lossless_extent(self):
        size = 0xfffff000
        self.assertEqual(((size >> 12) << 12) & 0xffffffff, size)
        raw = encode_ramdisk_adt(self.tree, size=size, **self.inputs)
        expected = Node('device-tree', {'model': b'synthetic\0'}, [
            Node('chosen', {'marker': b'keep'}, [Node('memory-map', {
                'other': b'keep', 'RAMDisk': struct.pack('<QQ', BASE, size)})]),
            Node('sibling'),
        ])
        self.assertEqual(raw, encode(expected))
        self.assertEqual(decode(raw), expected)
        self.assertEqual(encode(self.tree), self.before)

    def test_four_gib_would_disappear(self):
        size = 0x100000000
        self.assertEqual(((size >> 12) << 12) & 0xffffffff, 0)
        self.reject(size)

    def test_four_gib_plus_page_would_shrink(self):
        size = 0x100001000
        self.assertEqual(((size >> 12) << 12) & 0xffffffff, 0x1000)
        self.reject(size)

    def test_retained_root_os_extent(self):
        self.reject(9571401728)

    def test_retained_system_os_extent(self):
        self.reject(5247074304)


if __name__ == '__main__':
    unittest.main()
