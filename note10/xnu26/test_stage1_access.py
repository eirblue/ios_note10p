"""Independent descriptor fixtures for the bounded EL1 permission subset."""
import unittest
from stage1_access import check_access,translation


class Stage1Tests(unittest.TestCase):
    def setUp(self):
        self.state={'tcr_el1':0x226511a511,'sctlr_el1':0x3454593d,
                    'ttbr0_el1':0x10000,'ttbr1_el1':0x18000}
        self.memory={0x10000:0x14003,0x14008:0x4000401,
                     0x18000:0x1c003,0x1c008:0x4000401}
        self.va=0x2001234

    def read64(self,address):return self.memory.get(address,0)
    def access(self,kind='read',**kwargs):
        return translation(self.read64,self.state,self.va,False,kind,**kwargs)

    def test_exact_block_pa_and_high_canonical_alias(self):
        self.assertEqual(self.access()['physical_address'],0x4001234)
        result=translation(self.read64,self.state,0xffff800002001234,True,'fetch')
        self.assertEqual(result['physical_address'],0x4001234)

    def test_leaf_readonly_allows_reads_but_rejects_writes(self):
        self.memory[0x14008]|=1<<7
        self.access('read');self.access('fetch')
        with self.assertRaisesRegex(ValueError,'read-only'):self.access('write')

    def test_parent_readonly_is_inherited(self):
        self.memory[0x10000]|=1<<62
        self.access('read')
        with self.assertRaisesRegex(ValueError,'read-only'):self.access('write')

    def test_leaf_and_parent_pxn(self):
        for at,bit in ((0x14008,53),(0x10000,59)):
            with self.subTest(bit=bit):
                self.setUp();self.memory[at]|=1<<bit
                self.access('read');self.access('write')
                with self.assertRaisesRegex(ValueError,'execute'):self.access('fetch')

    def test_uxn_does_not_deny_el1_fetch(self):
        self.memory[0x14008]|=1<<54;self.memory[0x10000]|=1<<60
        self.access('fetch')

    def test_access_flag_and_disabled_walks(self):
        self.memory[0x14008]&=~(1<<10)
        with self.assertRaisesRegex(ValueError,'Access flag'):self.access()
        self.setUp();self.state['tcr_el1']|=1<<7
        with self.assertRaisesRegex(ValueError,'walk disabled'):self.access()

    def test_wxn_depends_on_effective_write_permission(self):
        self.state['sctlr_el1']|=1<<19
        with self.assertRaisesRegex(ValueError,'execute'):self.access('fetch')
        self.memory[0x10000]|=1<<62
        self.access('fetch')

    def test_pan_only_restricts_user_accessible_data(self):
        self.access('read',pan=True)
        self.memory[0x14008]|=1<<6
        self.access('write',pan=False)
        for kind in ('read','write'):
            with self.subTest(kind=kind),self.assertRaisesRegex(ValueError,'PAN'):self.access(kind,pan=True)

    def test_el0_writable_mapping_is_implicitly_pxn(self):
        self.memory[0x14008]|=1<<6
        with self.assertRaisesRegex(ValueError,'execute'):self.access('fetch')
        # Hierarchical RO removes EL0 write permission; the implicit XN
        # restriction no longer applies, although PAN still blocks data.
        self.memory[0x10000]|=1<<62
        self.access('fetch',pan=True)
        with self.assertRaisesRegex(ValueError,'PAN'):self.access('read',pan=True)

    def test_parent_el0_disable_changes_effective_user_permission(self):
        self.memory[0x14008]|=1<<6;self.memory[0x10000]|=1<<61
        self.access('fetch');self.access('write',pan=True)
        self.assertFalse(self.access()['el0_accessible'])

    def test_cross_page_write_checks_both_pages(self):
        self.memory[0x14008]=0x20003
        self.memory[0x20000]=0x4000403
        self.memory[0x20008]=0x4004483
        result=check_access(self.read64,self.state,0x2003ffc,8,False,'read')
        self.assertEqual(result['physical_address'],0x4003ffc);self.assertEqual(len(result['chunks']),2)
        with self.assertRaisesRegex(ValueError,'read-only'):
            check_access(self.read64,self.state,0x2003ffc,8,False,'write')

    def test_invalid_descriptors_addresses_and_unsupported_controls(self):
        for descriptor in (0,2,0x4004401,0x10000000401):
            with self.subTest(descriptor=descriptor):
                self.setUp();self.memory[0x14008]=descriptor
                with self.assertRaises(ValueError):self.access()
        for bit in (39,40,41,42,59):
            self.setUp();self.state['tcr_el1']|=1<<bit
            with self.subTest(bit=bit),self.assertRaisesRegex(ValueError,'Unsupported'):self.access()
        for bit in (25,57):
            self.setUp();self.state['sctlr_el1']|=1<<bit
            with self.subTest(sctlr_bit=bit),self.assertRaisesRegex(ValueError,'Unsupported'):self.access()
        self.setUp()
        for address,high in ((1<<47,False),(0x80000000,True),(1<<64,True)):
            with self.subTest(address=address),self.assertRaises(ValueError):
                translation(self.read64,self.state,address,high,'read')


if __name__=='__main__':unittest.main()
