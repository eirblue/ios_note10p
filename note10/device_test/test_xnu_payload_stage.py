"""PC checks for data-only XNU RAM staging records and initramfs packaging."""
import unittest
import hashlib
import json
from pathlib import Path
import tempfile
from unittest.mock import patch
from decode_reservation import checksum
from decode_xnu_stage import decode
from prepare_reservation_kernel import cpio, prepare

ID='0123456789abcdef0123456789abcdef'
SHA='a'*64


def reservation():
    records=[]
    for seq in range(2):
        body=(f'id={ID} seq={seq} base=a00000000 size=10000000 align=2000000 '
              'pages=65536 reserved=65536 invalid=0 shift=12')
        records.append('N10RAM2 '+body+f' checksum={checksum(body.encode()):08x}\n')
    return ''.join(records)


def stage(seq,*,base='a00000000',size='10000000',length='16384',digest=SHA,status='0'):
    body=(f'id={ID} seq={seq} base={base} size={size} bytes={length} '
          f'sha256={digest} status={status}')
    return 'N10XNU1 '+body+f' checksum={checksum(body.encode()):08x}\n'


def parse_newc(data):
    pos=0;files={}
    while True:
        if data[pos:pos+6]!=b'070701':raise ValueError('Bad newc magic')
        fields=[int(data[pos+6+i*8:pos+14+i*8],16) for i in range(13)]
        namesize=fields[11];filesize=fields[6];pos+=110
        name=data[pos:pos+namesize-1].decode('ascii');pos=(pos+namesize+3)&~3
        value=data[pos:pos+filesize];pos=(pos+filesize+3)&~3
        if name=='TRAILER!!!':return files
        files[name]=value


class XnuStageTests(unittest.TestCase):
    def test_stage_preparation_preserves_memblock_insertion(self,cpu_cache=False):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);source=root/'source';output=root/'output'
            output.mkdir();init_c=source/'arch/arm64/mm/init.c'
            init_c.parent.mkdir(parents=True)
            raw=b'void __init arm64_memblock_init(void)\n{\n\tmemblock_allow_resize();\n}\n'
            init_c.write_bytes(raw)
            payload=b'K'*0x4000;payload_path=root/'kernel.mem';payload_path.write_bytes(payload)
            manifest=root/'payload-manifest.json'
            digest=hashlib.sha256(payload).hexdigest()
            manifest.write_text(json.dumps(dict(schema=1,purpose='xnu-data-only-ram-stage',
                source_kind='experimental-source-built-arm64-macho',payload_file='kernel.mem',
                payload_size=len(payload),payload_sha256=digest,source_macho_sha256='b'*64,
                physical_address=None,physical_reservation_verified=False,
                deployment_ready=False,xnu_executed=False)))
            def run(command,log):
                elf=bytearray(64);elf[:6]=b'\x7fELF\x02\x01';elf[18:20]=b'\xb7\x00'
                Path(command[command.index('-o')+1]).write_bytes(elf)
            with patch('prepare_reservation_kernel.INIT_SHA',hashlib.sha256(raw).hexdigest()):
                result=prepare(source,output,run,window_access=True,
                               xnu_payload=payload_path,xnu_manifest=manifest,cpu_cache=cpu_cache)
            self.assertIn('\tnote10_reserve_xnu_window();\n\n\tmemblock_allow_resize();',init_c.read_text())
            extension=init_c.with_name('note10_xnu_reserve.c').read_text()
            self.assertIn('n10_stage_xnu_payload(reserved, count, invalid)',extension)
            self.assertTrue(result['xnu_payload_stage_diagnostic'])
            if cpu_cache:
                self.assertTrue(result['cpu_cache_roundtrip_diagnostic'])
                self.assertIn('if (note10_test_xnu_window_access(',extension)
                self.assertIn('if (n10_stage_xnu_payload(',extension)
                self.assertIn('n10_test_cpu_cache();',extension)
            self.assertEqual(parse_newc((output/'initramfs.cpio').read_bytes())['xnu/kernel.mem'],payload)

    def test_cpu_cache_preparation_preserves_prerequisites(self):
        self.test_stage_preparation_preserves_memblock_insertion(cpu_cache=True)

    def test_two_bound_readback_frames(self):
        result=decode(reservation()+stage(0)+stage(1),ID,SHA,0x4000)
        self.assertTrue(result['previous_boot_xnu_payload_stage_observed'])
        self.assertFalse(result['xnu_payload_executed'])
        self.assertFalse(result['physical_cache_mmu_handoff_verified'])

    def test_missing_corrupt_conflicting_or_failed_records_rejected(self):
        cases=(stage(0),stage(0)+stage(0),stage(0)+stage(1,digest='b'*64),
               stage(0)+stage(1,status='8'),stage(0)+stage(1,base='a20000000'),
               stage(0)+stage(1).replace('checksum=','checksum=f'))
        for records in cases:
            with self.subTest(records=records[-50:]),self.assertRaises(ValueError):
                decode(reservation()+records,ID,SHA,0x4000)

    def test_newc_contains_payload_as_data_only_file(self):
        init=bytearray(64);init[:6]=b'\x7fELF\x02\x01';init[18:20]=b'\xb7\x00'
        payload=b'K'*0x4000
        files=parse_newc(cpio(bytes(init),payload))
        self.assertEqual(files['xnu/kernel.mem'],payload)
        self.assertEqual(files['init'],bytes(init))
        self.assertNotIn('xnu/entry',files)

    def test_initramfs_without_payload_stays_minimal(self):
        init=bytearray(64);init[:6]=b'\x7fELF\x02\x01';init[18:20]=b'\xb7\x00'
        self.assertNotIn('xnu/kernel.mem',parse_newc(cpio(bytes(init))))


if __name__=='__main__':unittest.main()
