"""Small independent ABI fixtures for detecting corrupt early-C results."""
import struct
import unittest
from early_c_state import inspect_static_if


class EarlyStateTests(unittest.TestCase):
    def setUp(self):
        self.memory={}
        self.entries=struct.pack('<iiQiiQ',0x2000,16,0x2001,0x2000,16,0x2000)
        self.initial=struct.pack('<hBBIQQ',0,1,0,0,0,0)
        self.put(0x1000,struct.pack('<iiQiiQ',0x2000,16,0x1011,0x2000,16,0))
        self.put(0x2000,struct.pack('<hBBIQQ',1,1,1,2,0x1000,0))
        self.put(0x3000,struct.pack('<I',0x14000004))
        self.calls=[{'indirect':True,'target_address':'0x4000','target_symbols':['fixture']},
                    {'indirect':False,'target_address':'0x5000','target_symbols':['_ml_static_if_entry_patch'],
                     'x0':'0x1000','x1':'0x1'}]
        self.stores=[(0x3000,4)]
    def put(self,address,data):
        for offset,byte in enumerate(data):self.memory[address+offset]=byte
    def read(self,address,size):return bytes(self.memory[address+i] for i in range(size))
    def original(self,address,size):
        if (address,size)!=(0x2000,24):raise AssertionError('unexpected immutable read')
        return self.initial
    def inspect(self):
        return inspect_static_if(self.read,self.original,0x1000,self.entries,
                                 struct.pack('<Q',0x4000),self.calls,self.stores)
    def test_complete_real_layout_fixture(self):
        result=self.inspect()
        self.assertEqual((result['entries_checked'],result['keys_checked'],result['patches_checked']),(2,1,1))
        self.assertFalse(result['cache_coherence_verified'])
    def test_wrong_count_cycle_or_missing_member(self):
        for address,data in ((0x2004,struct.pack('<I',1)),(0x1008,struct.pack('<Q',0x1001)),
                             (0x1008,struct.pack('<Q',1)),(0x1008,struct.pack('<Q',0x1111))):
            self.setUp();self.put(address,data)
            with self.subTest(address=address,data=data),self.assertRaises(ValueError):self.inspect()
    def test_offsets_flags_and_initializer_calls(self):
        for action in ('offset','flags','initializer'):
            self.setUp()
            if action=='offset':self.put(0x1000,struct.pack('<i',0x2004))
            elif action=='flags':self.put(0x1008,struct.pack('<Q',0x1012))
            else:self.calls[0]['target_address']='0x4004'
            with self.subTest(action=action),self.assertRaises(ValueError):self.inspect()
    def test_wrong_instruction_or_unexecuted_patch(self):
        self.put(0x3000,struct.pack('<I',0xd503201f))
        with self.assertRaisesRegex(ValueError,'instruction mismatch'):self.inspect()
        self.setUp();self.stores=[]
        with self.assertRaisesRegex(ValueError,'store not executed'):self.inspect()
    def test_patch_must_agree_with_real_key_enablement(self):
        self.put(0x2000,struct.pack('<h',-1))
        with self.assertRaisesRegex(ValueError,'key state'):self.inspect()


if __name__=='__main__':unittest.main()
