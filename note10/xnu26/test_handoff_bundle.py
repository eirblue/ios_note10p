import copy
import hashlib
import json
from pathlib import Path
import struct
import tempfile
import unittest
from boot_adt import Node,encode
from handoff_bundle import ROOT,PAGE,construct,load,materialize_adapter,materialize_kernel


def adapter_fixture():
    raw=bytearray(512)
    ident=b'\x7fELF\x02\x01\x01'+bytes(9)
    struct.pack_into('<16sHHIQQQIHHHHHH',raw,0,ident,2,183,1,0,64,384,0,64,56,2,64,2,0)
    struct.pack_into('<II6Q',raw,64,1,5,256,0,0,4,4,4)
    struct.pack_into('<II6Q',raw,120,1,6,320,64,64,64,64,64)
    raw[256:260]=b'\xc0\x03\x5f\xd6'
    raw[320:384]=struct.pack('<8sII6Q',b'N10XFER1',1,64,0,0,0,0,0,0)
    struct.pack_into('<IIQQQQIIQQ',raw,448,0,1,0,0,256,4,0,0,4,0)
    return bytes(raw)


def fixture():
    virtual=0xfffffff000000000;base=virtual+0x7004000
    segments=[dict(virtual_address=base,virtual_size=PAGE,file_offset=0,file_size=16),
              dict(virtual_address=base+2*PAGE,virtual_size=PAGE,file_offset=16,file_size=8)]
    checked={'segments':segments,'entry_virtual_address':hex(base)}
    raw=b'A'*16+b'B'*8
    plan={'schema':1,'purpose':'synthetic-pc-model','physical_reservation_verified':False,
          'ram':{'start':0x80000000,'size':0x40000000},'virtual_base':virtual,'reserved':[],'occupied':[],
          'arguments_address':0x86004000,'device_tree_address':0x86008000,'adapter_address':0x8600c000,
          'top_of_kernel':0x87010000,'command_line':'debug=0x14e'}
    return raw,checked,adapter_fixture(),encode(Node('device-tree',children=[Node('chosen')])),plan


class BundleTests(unittest.TestCase):
    def test_actual_built_transfer_elf(self):
        path=ROOT/'note10/private/xnu-transfer/transfer.elf'
        if not path.exists():self.skipTest('Build the ARM64 transfer ELF first')
        data,entry,record=materialize_adapter(path.read_bytes())
        self.assertEqual(len(data),PAGE);self.assertEqual(entry%4,0);self.assertEqual(record%64,0)
        self.assertEqual(data[record:record+64],struct.pack('<8sII6Q',b'N10XFER1',1,64,0,0,0,0,0,0))

    def test_segments_bss_holes_and_padding(self):
        raw,checked,_,_,_=fixture();base,data=materialize_kernel(raw,checked['segments'])
        self.assertEqual(len(data),3*PAGE);self.assertEqual(data[:16],b'A'*16)
        self.assertEqual(data[16:2*PAGE],bytes(2*PAGE-16))
        self.assertEqual(data[2*PAGE:2*PAGE+8],b'B'*8);self.assertEqual(data[2*PAGE+8:],bytes(PAGE-8))

    def test_bad_segment_bounds_and_overlap(self):
        raw,checked,_,_,_=fixture()
        for field,value in (('file_size',PAGE+1),('file_offset',1000),('virtual_size',512*1024*1024)):
            segments=copy.deepcopy(checked['segments']);segments[0][field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):materialize_kernel(raw,segments)
        segments=copy.deepcopy(checked['segments']);segments[1]['virtual_address']=segments[0]['virtual_address']
        with self.assertRaises(ValueError):materialize_kernel(raw,segments)

    def test_adapter_relocation_permissions_record_and_truncation(self):
        raw=adapter_fixture();data,entry,record=materialize_adapter(raw)
        self.assertEqual((len(data),entry,record),(PAGE,0,64))
        changes=[]
        b=bytearray(raw);struct.pack_into('<I',b,452,4);changes.append(bytes(b))
        b=bytearray(raw);struct.pack_into('<I',b,68,7);changes.append(bytes(b))
        b=bytearray(raw);b[320]=0;changes.append(bytes(b))
        b=bytearray(raw);struct.pack_into('<Q',b,24,200);changes.append(bytes(b))
        b=bytearray(raw);struct.pack_into('<I',b,120,2);changes.append(bytes(b))
        b=bytearray(raw);struct.pack_into('<Q',b,24,1);changes.append(bytes(b))
        changes.extend([raw[:100],b'not an elf'])
        for b in changes:
            with self.assertRaises(ValueError):materialize_adapter(b)

    def test_materialized_arguments_and_transfer_descriptor(self):
        inputs=fixture();manifest,files=construct(*inputs);plan=inputs[-1]
        self.assertEqual(struct.unpack_from('<Q',files['boot-args.mem'],96)[0],plan['virtual_base']+0x6008000)
        self.assertEqual(struct.unpack_from('<QQ',files['adapter.mem'],64+16),(plan['arguments_address'],manifest['xnu_entry_physical']))
        self.assertEqual(files['adapter.mem'][64+32:64+64],bytes(32))
        self.assertFalse(manifest['physical_reservation_verified'])

    def test_overlap_occupancy_and_hardware_claim_refused(self):
        raw,checked,adapter,adt,plan=fixture()
        changes=[dict(adapter_address=plan['arguments_address']),dict(device_tree_address=plan['arguments_address']),
                 dict(occupied=[{'start':plan['adapter_address'],'size':PAGE}]),
                 dict(reserved=[{'start':0x87004000,'size':PAGE}]),dict(purpose='hardware'),
                 dict(physical_reservation_verified=True),dict(top_of_kernel=0x87008000),
                 dict(adapter_address=0x84000000)]
        for delta in changes:
            with self.subTest(delta=delta),self.assertRaises(ValueError):construct(raw,checked,adapter,adt,{**plan,**delta})

    def test_disk_hash_and_manifest_cross_links(self):
        inputs=fixture();manifest,files=construct(*inputs)
        parent=ROOT/'note10/private/bundle-tests';parent.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=parent) as name:
            directory=Path(name);self.assertTrue(directory.resolve().is_relative_to(parent.resolve()))
            for filename,data in files.items():(directory/filename).write_bytes(data)
            path=directory/'handoff.json';path.write_text(json.dumps(manifest),encoding='utf-8')
            self.assertEqual(load(directory,kernel_sha256=manifest['kernel_sha256'])[1],files)
            for field in ('boot_args_physical','adapter_record_physical','xnu_entry_physical'):
                changed=copy.deepcopy(manifest);changed[field]+=PAGE
                path.write_text(json.dumps(changed),encoding='utf-8')
                with self.subTest(field=field),self.assertRaises(ValueError):load(directory,kernel_sha256=manifest['kernel_sha256'])
            path.write_text(json.dumps(manifest),encoding='utf-8')
            with self.assertRaises(ValueError):load(directory,kernel_sha256='0'*64)
            changed=copy.deepcopy(manifest);changed['deployment_ready']=True
            path.write_text(json.dumps(changed),encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'cannot authorize'):load(directory,kernel_sha256=manifest['kernel_sha256'])
            path.write_text(json.dumps(manifest),encoding='utf-8')
            (directory/'adapter.mem').write_bytes(b'X'*PAGE)
            with self.assertRaisesRegex(ValueError,'hash mismatch'):load(directory,kernel_sha256=manifest['kernel_sha256'])


if __name__=='__main__':unittest.main()
