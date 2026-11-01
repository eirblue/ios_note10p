"""Only NEW v79 declaration paths; no CPU/placement/codec/model suites."""
import argparse
from contextlib import redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch

import linux_memory_declarations as memory


ROOT = Path(__file__).resolve().parents[2]


def node(name, properties=(), children=()):
    return name,list(properties),list(children)


def region(start=0x10000000,size=0x200000,ac=2,sc=1):
    return start.to_bytes(4*ac,'big')+size.to_bytes(4*sc,'big')


def reserved(children,ac=2,sc=1,translation=b''):
    return node('reserved-memory',[('#address-cells',struct.pack('>I',ac)),
        ('#size-cells',struct.pack('>I',sc)),('ranges',translation)],children)


def tree(ac=2,sc=1,memory_properties=None,extra=(),root_properties=None,with_cpus=True):
    props=[('#address-cells',struct.pack('>I',ac)),('#size-cells',struct.pack('>I',sc))] if root_properties is None else root_properties
    banks=[('device_type',b'memory\0'),('reg',region(ac=ac,sc=sc))] if memory_properties is None else memory_properties
    return node('',props,[*([node('cpus')] if with_cpus else []),node('memory@synthetic',banks),*extra])


def fdt(root,reserves=()):
    strings,body,offsets=bytearray(),bytearray(),{}
    def visit(entry):
        name,properties,children=entry
        body.extend(struct.pack('>I',1)+name.encode('ascii')+b'\0')
        body.extend(bytes(-len(body)&3))
        for name,value in properties:
            if name not in offsets:
                offsets[name]=len(strings);strings.extend(name.encode('ascii')+b'\0')
            body.extend(struct.pack('>III',3,len(value),offsets[name])+value)
            body.extend(bytes(-len(body)&3))
        for child in children:visit(child)
        body.extend(struct.pack('>I',2))
    visit(root);body.extend(struct.pack('>I',9))
    reserve_bytes=b''.join(struct.pack('>QQ',start,size) for start,size in reserves)+bytes(16)
    so=40+len(reserve_bytes);sto=so+len(body)
    return struct.pack('>10I',0xd00dfeed,sto+len(strings),so,sto,40,17,16,0,len(strings),len(body))+reserve_bytes+body+strings


class MemoryDeclarationTests(unittest.TestCase):
    def test_banks_usable_override_and_header_sources_remain_separate(self):
        props=[('device_type',b'memory\0'),('reg',region()+region(0x30000000,0x400000)),
               ('linux,usable-memory',region(0x10001000,0x10000))]
        manifest=memory.inventory(fdt(tree(memory_properties=props),[(0x10002000,0x1000)]))
        self.assertEqual([(r['start'],r['size']) for r in manifest['ram_declarations']],
                         [(0x10000000,0x200000),(0x30000000,0x400000)])
        self.assertEqual(manifest['linux_usable_declarations'][0]['source']['property'],'linux,usable-memory')
        self.assertEqual(manifest['header_reservations'][0]['start'],0x10002000)
        for field in ('placement_ready','memory_ownership','live_occupancy_known','handoff_ready','free_memory_computed','effective_linux_memory_map'):
            self.assertFalse(manifest[field])
        self.assertNotIn('cpus',manifest)

    def test_supported_cell_widths_and_u64_half_open_boundary(self):
        for ac,sc,start,size in ((1,2,0x1000,0x100000000),(2,2,(1<<64)-0x1000,0x1000)):
            with self.subTest(ac=ac,sc=sc):
                props=[('device_type',b'memory\0'),('reg',region(start,size,ac,sc))]
                result=memory.inventory(fdt(tree(ac,sc,props)))
                self.assertEqual((result['ram_declarations'][0]['start'],result['ram_declarations'][0]['size']),(start,size))

    def test_direct_fixed_declarations_preserve_policy_flags(self):
        fixed=node('fixed@synthetic',[('reg',region(0x10010000,0x1000)),('no-map',b''),('reusable',b'')])
        result=memory.inventory(fdt(tree(extra=[reserved([fixed])])))
        self.assertEqual(result['counts']['direct_fixed_ranges'],1)
        item=result['direct_fixed_reservations'][0]
        self.assertEqual(item['source']['node_path'],'/reserved-memory/fixed@synthetic')
        self.assertEqual(item['qualifiers']['flags']['no-map']['bytes'],0)
        self.assertFalse(item['qualifiers']['effective_admission_known'])

    def test_dynamic_wide_alignment_and_allocation_hints_stay_unresolved(self):
        alignment=(0x200000).to_bytes(8,'big')
        dynamic=node('dynamic',[('size',struct.pack('>I',0x10000)),('alignment',alignment),
                                ('alloc-ranges',region(0x10000000,0x200000))])
        result=memory.inventory(fdt(tree(extra=[reserved([dynamic])])))
        item=result['unresolved'][0]
        self.assertEqual(item['hints']['alignment'],{'bytes':8,'raw_be_hex':alignment.hex()})
        self.assertEqual(result['counts']['dynamic_nodes'],1)
        self.assertFalse(item['physical_extent_interpreted'])
        self.assertNotIn('start',item)
        self.assertEqual(result['direct_fixed_reservations'],[])

    def test_nested_and_empty_container_are_not_root_physical_ranges(self):
        nested=node('container',children=[node('child',[('reg',b'\x01\x02\x03')])])
        result=memory.inventory(fdt(tree(extra=[reserved([nested])])))
        self.assertEqual(result['counts']['container_nodes'],1)
        self.assertEqual(result['counts']['nested_nodes'],1)
        self.assertEqual(result['counts']['unresolved_records'],2)
        item=next(r for r in result['unresolved'] if 'unsupported-nested-address-space' in r['reasons'])
        self.assertEqual(item['hints']['reg']['bytes'],3)
        self.assertEqual(result['direct_fixed_reservations'],[])

    def test_conditional_no_ship_and_status_never_become_active_reservations(self):
        nodes=[node('conditional',[('reg',region()),('no-ship',b'')]),
               node('disabled',[('reg',region(0x30000000)),('status',b'disabled\0')])]
        result=memory.inventory(fdt(tree(extra=[reserved(nodes)])))
        self.assertEqual(result['counts']['conditional_nodes'],2)
        self.assertEqual(result['direct_fixed_reservations'],[])
        self.assertTrue(all(not r['physical_extent_interpreted'] for r in result['unresolved']))

    def test_explicit_root_cells_are_required(self):
        for props in ([('#size-cells',struct.pack('>I',1))],
                      [('#address-cells',b'\0\0\1'),('#size-cells',struct.pack('>I',1))],
                      [('#address-cells',struct.pack('>I',3)),('#size-cells',struct.pack('>I',1))],
                      [('#address-cells',struct.pack('>I',2)),('#size-cells',bytes(4))]):
            with self.subTest(props=props):
                with self.assertRaises(ValueError):memory.inventory(fdt(tree(root_properties=props)))

    def test_supported_ram_tuples_reject_missing_partial_zero_and_overflow(self):
        for value in (None,b'',b'\x01',region(size=0),region((1<<64)-0x1000,0x2000)):
            props=[('device_type',b'memory\0')]+([] if value is None else [('reg',value)])
            with self.subTest(value=value):
                with self.assertRaises(ValueError):memory.inventory(fdt(tree(memory_properties=props)))
        props=[('device_type',b'memory\0'),('reg',region()),('linux,usable-memory',b'\x01')]
        with self.assertRaises(ValueError):memory.inventory(fdt(tree(memory_properties=props)))

    def test_reserved_root_and_supported_fixed_tuple_contracts(self):
        fixed=node('fixed',[('reg',region())])
        invalid_roots=[reserved([fixed],ac=1),reserved([fixed],translation=b'\0'*12),
                       node('reserved-memory',[('#address-cells',struct.pack('>I',2)),('#size-cells',struct.pack('>I',1))],[fixed])]
        for parent in invalid_roots:
            with self.assertRaises(ValueError):memory.inventory(fdt(tree(extra=[parent])))
        for value in (b'',b'\x01',region(size=0)):
            with self.assertRaises(ValueError):memory.inventory(fdt(tree(extra=[reserved([node('fixed',[('reg',value)])])])))

    def test_header_reservations_require_nonzero_u64_extents(self):
        for pair in ((0x1000,0),((1<<64)-0x1000,0x2000)):
            with self.assertRaises(ValueError):memory.inventory(fdt(tree(),[pair]))

    def test_cpus_presence_restriction_and_complete_placement_rejection(self):
        with self.assertRaisesRegex(ValueError,'FDT /cpus missing'):
            memory.inventory(fdt(tree(with_cpus=False)))
        with self.assertRaisesRegex(ValueError,'Complete placement unsupported'):
            memory.inventory(b'not parsed',require_complete_placement=True)

    def test_private_build_cli_hash_semantics_and_fresh_output(self):
        with tempfile.TemporaryDirectory(prefix='v79-memory-',dir=memory.PRIVATE_ROOT) as scratch:
            base=Path(scratch);source=base/'synthetic.dtb';raw=fdt(tree());source.write_bytes(raw)
            digest=hashlib.sha256(raw).hexdigest();output=base/'result';stdout=io.StringIO()
            argv=['linux_memory_declarations.py','--input',str(source),'--input-sha256',digest,'--output',str(output)]
            with patch.object(sys,'argv',argv),redirect_stdout(stdout):memory.main()
            printed=json.loads(stdout.getvalue());saved=(output/'declarations.json').read_bytes()
            manifest=json.loads(saved)
            self.assertEqual(manifest['input_sha256'],digest)
            self.assertEqual(printed['counts']['memory_banks'],1)
            self.assertEqual(set(printed),{'policy','counts','private_output','placement_ready','memory_ownership','live_occupancy_known','handoff_ready'})
            for private_value in (str(source),digest,'memory@synthetic',str(0x10000000)):
                self.assertNotIn(private_value,stdout.getvalue())
            self.assertEqual([p.name for p in output.iterdir()],['declarations.json'])
            with self.assertRaises(ValueError):memory.build(source,digest,output)
            self.assertEqual((output/'declarations.json').read_bytes(),saved)
            failed=base/'bad-hash'
            with self.assertRaises(ValueError):memory.build(source,'0'*64,failed)
            self.assertFalse(failed.exists())
            malformed=base/'malformed.dtb'
            malformed.write_bytes(fdt(tree(memory_properties=[('device_type',b'memory\0'),('reg',region(size=0))])))
            with self.assertRaises(ValueError):memory.build(malformed,hashlib.sha256(malformed.read_bytes()).hexdigest(),base/'semantic-reject')
            self.assertFalse((base/'semantic-reject').exists())
            outside=ROOT/('v79-forbidden-'+base.name)
            with self.assertRaises(ValueError):memory.build(source,digest,outside)
            self.assertFalse(outside.exists())
            with self.assertRaises(ValueError):memory.build(ROOT/'outside-private.dtb',digest,base/'bad-input-scope')
            self.assertFalse((base/'bad-input-scope').exists())


CASE_NAMES=(
 'test_banks_usable_override_and_header_sources_remain_separate','test_supported_cell_widths_and_u64_half_open_boundary',
 'test_direct_fixed_declarations_preserve_policy_flags','test_dynamic_wide_alignment_and_allocation_hints_stay_unresolved',
 'test_nested_and_empty_container_are_not_root_physical_ranges','test_conditional_no_ship_and_status_never_become_active_reservations',
 'test_explicit_root_cells_are_required','test_supported_ram_tuples_reject_missing_partial_zero_and_overflow',
 'test_reserved_root_and_supported_fixed_tuple_contracts','test_header_reservations_require_nonzero_u64_extents',
 'test_cpus_presence_restriction_and_complete_placement_rejection','test_private_build_cli_hash_semantics_and_fresh_output',
)


class Recorded(unittest.TextTestResult):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs);self.failed_methods=set();self.framework_errors=[]
    def addFailure(self,test,error):
        self.failed_methods.add(test._testMethodName);super().addFailure(test,error)
    def addError(self,test,error):
        if isinstance(test,MemoryDeclarationTests):self.failed_methods.add(test._testMethodName)
        else:self.framework_errors.append(test.id())
        super().addError(test,error)
    def addSubTest(self,test,subtest,error):
        if error is not None:self.failed_methods.add(test._testMethodName)
        super().addSubTest(test,subtest,error)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True)
    parser.add_argument('--case',action='append',choices=CASE_NAMES)
    args=parser.parse_args();selected=list(CASE_NAMES) if args.case is None else args.case
    if len(selected)!=len(set(selected)):parser.error('duplicate new memory case selection')
    output=Path(args.output).resolve()
    if output==memory.PRIVATE_ROOT or not output.is_relative_to(memory.PRIVATE_ROOT):parser.error('private new-case output required')
    output.mkdir(parents=True,exist_ok=False)
    result=unittest.TextTestRunner(verbosity=2,resultclass=Recorded).run(unittest.TestSuite(MemoryDeclarationTests(name) for name in selected))
    passed=[name for name in selected if name not in result.failed_methods] if result.testsRun==len(selected) and not result.framework_errors else []
    sources=(Path(__file__),Path(memory.__file__),Path(memory.fdt.__file__))
    receipt=dict(kind='v79-new-memory-declaration-cases',selected=selected,passed=passed,failed=sorted(result.failed_methods),
        framework_errors=result.framework_errors,tests_run=result.testsRun,old_suites_executed=0,device_calls=0,
        source_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
        success=result.wasSuccessful() and result.testsRun==len(selected) and not result.skipped)
    (output/'result.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    return 0 if receipt['success'] else 1


if __name__=='__main__':
    raise SystemExit(main())
