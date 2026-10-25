"""Small independent ABI fixtures for detecting corrupt early-C results."""
import struct
import unittest
from early_c_state import inspect_static_if
from early_c_state import inspect_startup,inspect_startup_entries,inspect_vm_boundary
from types import SimpleNamespace
from unittest.mock import patch


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
    def test_later_indirect_callbacks_are_not_static_initializers(self):
        self.calls.extend([{'target_symbols':['_PE_init_platform']},
                           {'indirect':True,'target_symbols':['_timebase_callback'],'target_address':'0x6000'}])
        self.assertEqual(self.inspect()['initializers_executed'],1)


class StartupStateTests(unittest.TestCase):
    def setUp(self):
        import json
        from pathlib import Path
        self.layout=json.loads(Path(__file__).with_name('early_c_abi.json').read_text())['layout']
        self.memory=bytearray(0x5000)
        self.uc=SimpleNamespace(mem_read=lambda address,size:self.memory[address:address+size])
        self.symbols={'_init_thread':0x100,'_percpu_slot_cpu_data':0x1000,'_RTClockData':0x3000}
        self.state={'tpidr_el1':0x100,'cntvct_el0':26000000}
        self.put(0x100+self.layout['thread_cpu_data_offset'],0x1000,8)
        self.put(0x1000+self.layout['cpu_active_thread_offset'],0x100,8)
        self.memory[0x3000:0x3010]=struct.pack('<4I',26000000,26,500,13)
    def put(self,address,value,size):self.memory[address:address+size]=value.to_bytes(size,'little')
    def inspect(self):return inspect_startup(self.uc,self.symbols,self.state,26000000)
    def test_actual_layout_fixture(self):
        self.assertEqual(self.inspect()['nanoseconds_denom'],13)
        self.assertFalse(self.inspect()['running_clock_verified'])
    def test_corrupt_backpointers_preemption_and_timebase(self):
        for address in (0x100+self.layout['thread_cpu_data_offset'],
                        0x1000+self.layout['cpu_active_thread_offset'],
                        0x100+self.layout['thread_preemption_offset'],0x3000,0x3008,0x300c):
            self.setUp();self.memory[address]^=1
            with self.subTest(address=address),self.assertRaises(ValueError):self.inspect()
    def test_wrong_current_thread(self):
        self.state['tpidr_el1']=0
        with self.assertRaisesRegex(ValueError,'pointers'):self.inspect()


class StartupEntriesTests(unittest.TestCase):
    def setUp(self):
        self.memory=bytearray(0x1000)
        self.uc=SimpleNamespace(mem_read=lambda address,size:self.memory[address:address+size])
        self.symbols={'_startup_phase':0x100,'_startup_entry_cur':0x108}
        self.entries=[(4,0,0x8000,0),(1,10,0x8100,0x9000),(3,0,0x8200,0x9100)]
        self.initial=b''.join(struct.pack('<IIQQ',*r) for r in self.entries)
        self.memory[0x200:0x248]=b''.join(struct.pack('<IIQQ',*r) for r in sorted(self.entries))
        self.memory[0x100:0x104]=struct.pack('<I',3)
        self.memory[0x108:0x110]=struct.pack('<Q',0x230)
        self.calls=[{'indirect':True,'address':'0x7000','target_address':hex(r[2]),'x0':hex(r[3])}
                    for r in sorted(self.entries)[:2]]
    def inspect(self):
        with patch('early_c_state.sections',return_value={'__init_entry_set':(0x200,self.initial)}):
            return inspect_startup_entries(self.uc,b'',self.symbols,self.calls)
    def test_sorted_multiset_and_callbacks(self):
        self.assertEqual(self.inspect()['callbacks_executed'],2)
    def test_corruption_sort_and_cursor(self):
        for address in (0x200,0x208,0x100,0x108):
            self.setUp();self.memory[address]^=1
            with self.subTest(address=address),self.assertRaises(ValueError):self.inspect()
        self.setUp();self.memory[0x200:0x248]=self.initial
        with self.assertRaisesRegex(ValueError,'ordered'):self.inspect()
    def test_wrong_callback_order_or_arguments(self):
        self.calls.reverse()
        with self.assertRaisesRegex(ValueError,'sequence'):self.inspect()
        self.setUp();self.calls[0]['x0']='0x0'
        with self.assertRaisesRegex(ValueError,'sequence'):self.inspect()


class VmBoundaryTests(unittest.TestCase):
    def setUp(self):
        import json
        from pathlib import Path
        self.layout=json.loads(Path(__file__).with_name('early_c_abi.json').read_text())['layout']
        self.memory=bytearray(0x6000)
        self.uc=SimpleNamespace(mem_read=lambda address,size:self.memory[address:address+size])
        self.symbols={'_percpu_slot_cpu_data':0x1000,'_gDramBase':0x5000,'_gDramSize':0x5008,
                      '_pmap_first_pnum':0x5010,'_cpuid_cache_info_boot_cpu':0x5020}
        self.boot_args=bytearray(1152);struct.pack_into('<QQ',self.boot_args,16,0x80000000,0x40000000)
        self.memory[0x5000:0x5010]=struct.pack('<QQ',0x80000000,0x40000000)
        self.memory[0x5010:0x5014]=struct.pack('<I',0x20000)
        self.memory[0x5020:0x5028]=struct.pack('<Q',0x5100)
        for name,value,size in (('cpu_type_offset',0x100000c,4),('cpu_subtype_offset',1,4),
                                ('cpu_running_offset',1,1),('cpu_rtclock_deadline_offset',(1<<64)-1,8)):
            at=0x1000+self.layout[name];self.memory[at:at+size]=value.to_bytes(size,'little')
        for name,value in (('cache_valid_offset',1),('cache_line_offset',64),('cache_isize_offset',32768),
                            ('cache_dsize_offset',32768),('cache_l2size_offset',1048576)):
            at=0x5100+self.layout[name];self.memory[at:at+4]=struct.pack('<I',value)
        self.caches={0:0x700fe01a,1:0x200fe01a,2:0x707fe07a}
        self.state={'daif':0x3c0,'clidr_el1':0x82000023}
    def inspect(self):return inspect_vm_boundary(self.uc,self.symbols,self.boot_args,self.caches,self.state)
    def test_compiled_layout_fixture(self):
        self.assertEqual(self.inspect()['l2_bytes'],1048576)
        self.assertFalse(self.inspect()['vm_initialization_executed'])
    def test_corrupt_cpu_dram_page_or_cache_state(self):
        for address in (0x1000+self.layout['cpu_type_offset'],0x1000+self.layout['cpu_running_offset'],
                        0x1000+self.layout['cpu_rtclock_deadline_offset'],0x5000,0x5008,0x5010,
                        0x5100+self.layout['cache_line_offset'],0x5100+self.layout['cache_l2size_offset']):
            self.setUp();self.memory[address]^=1
            with self.subTest(address=address),self.assertRaises(ValueError):self.inspect()
    def test_unmasked_interrupts_or_unreviewed_geometry(self):
        self.state['daif']=0
        with self.assertRaisesRegex(ValueError,'masked'):self.inspect()
        self.setUp();self.state['clidr_el1']=0
        with self.assertRaisesRegex(ValueError,'Unsupported'):self.inspect()


if __name__=='__main__':unittest.main()
