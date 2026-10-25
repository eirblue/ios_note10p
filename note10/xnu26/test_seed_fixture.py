"""Bounds and corruption checks for the PC-only seed-consumption checkpoint."""
import struct
from types import SimpleNamespace
import unittest
from boot_adt import Node,encode
from seed_fixture import PC_SEED,property_spans,locate,inspect


class SeedTests(unittest.TestCase):
    def setUp(self):
        self.raw=encode(Node('device-tree',{'duplicate-bytes':PC_SEED},[
            Node('chosen',{'random-seed':PC_SEED,'after':b'keep\0'})]))
        self.memory=bytearray(0x10000);self.memory[0x4000:0x4000+len(self.raw)]=self.raw
        self.uc=SimpleNamespace(mem_read=lambda a,n:self.memory[a:a+n])
        self.args=bytearray(1152);struct.pack_into('<QI',self.args,96,0x4000,len(self.raw))
        self.region=locate(self.uc,self.args)
        self.destination=0x8000
        self.memory[self.destination:self.destination+256]=PC_SEED
        start=self.region['address'];self.memory[start:start+256]=bytes(256)
    def inspect(self):return inspect(self.uc,self.region,self.destination,256,256)
    def test_exact_property_not_duplicate_payload(self):
        self.assertEqual(self.inspect()['bytes_copied'],256)
        self.assertFalse(self.inspect()['hardware_seed_ready'])
        other=property_spans(self.raw)[('/device-tree','duplicate-bytes')][0]
        self.assertEqual(bytes(self.memory[0x4000+other:0x4000+other+256]),PC_SEED)
    def test_bad_copy_incomplete_wipe_or_other_mutation(self):
        for address in (self.destination,self.region['address'],0x4000+len(self.raw)-4):
            self.setUp();self.memory[address]^=1
            with self.subTest(address=address),self.assertRaises(ValueError):self.inspect()
    def test_wrong_count_or_missing_property(self):
        for region,request,returned in ((None,256,256),(self.region,256,0),(self.region,128,128)):
            with self.subTest(request=request,returned=returned),self.assertRaisesRegex(ValueError,'byte count'):
                inspect(self.uc,region,self.destination,request,returned)
    def test_truncated_or_trailing_tree(self):
        for raw in (self.raw[:-1],self.raw+b'\0'):
            with self.assertRaises(ValueError):property_spans(raw)
    def test_absent_seed_stays_absent(self):
        raw=encode(Node('device-tree',children=[Node('chosen')]))
        self.memory[0x4000:0x4000+len(raw)]=raw;struct.pack_into('<I',self.args,104,len(raw))
        self.assertIsNone(locate(self.uc,self.args))


if __name__=='__main__':unittest.main()
