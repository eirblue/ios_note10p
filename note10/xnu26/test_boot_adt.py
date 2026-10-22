"""ADT format limits, malformed buffers and a fixed wire-format fixture."""
import struct
import unittest
from boot_adt import Node, encode, decode


def fixture():
    # Fixture bytes are format-test data, not a hardware handoff declaration.
    return Node('device-tree', {'compatible': b'samsung,exynos9825-note10\0'},
        [Node('chosen', children=[Node('note10-platform', {'version': struct.pack('<I', 1),
                                                         'test-marker': b'PC-only\0'})])])


class AdtTests(unittest.TestCase):
    def test_roundtrip_and_format_fixture(self):
        tree = fixture(); raw = encode(tree)
        self.assertEqual(decode(raw), tree)
        # One-property node: fixed header, 32-byte key, 5-byte value, 3-byte pad.
        golden = bytes.fromhex('0100000000000000') + b'name' + bytes(28) + b'\x05\0\0\0root\0\0\0\0'
        self.assertEqual(encode(Node('root')), golden)
        self.assertEqual(decode(golden), Node('root'))

    def test_every_truncation_rejected(self):
        raw = encode(fixture())
        for size in range(len(raw)):
            with self.subTest(size=size), self.assertRaises(ValueError): decode(raw[:size])

    def test_invalid_names(self):
        for name in ('', 'x' * 64, 'bad/name', 'nul\0name'):
            with self.assertRaises(ValueError): encode(Node(name))
        for key in ('', 'x' * 32, 'bad/key', 'nul\0key', 'name'):
            with self.assertRaises(ValueError): encode(Node('root', {key:b''}))

    def test_duplicate_children_and_cycles(self):
        with self.assertRaises(ValueError): encode(Node('root', children=[Node('a'), Node('a')]))
        root = Node('root'); root.children.append(root)
        with self.assertRaises(ValueError): encode(root)

    def test_bad_headers_names_padding_and_trailing_bytes(self):
        raw = encode(Node('root'))
        malformed = [raw + b'\0', struct.pack('<II', 0xffffffff, 0),
                     raw[:8] + b'x'*32 + raw[40:], raw[:40] + struct.pack('<I', 0x80000005) + raw[44:]]
        bad = bytearray(raw); bad[-1] = 1; malformed.append(bytes(bad))
        for item in malformed:
            with self.assertRaises(ValueError): decode(item)


if __name__ == '__main__': unittest.main()
