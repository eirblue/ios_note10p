from pathlib import Path
import struct
import tempfile
import unittest
from prepare_reservation_kernel import cpio,prepare
from run_probe import ROOT


class ReservationBuildTests(unittest.TestCase):
    def test_independent_cpio_reader_and_console_device(self):
        init=bytearray(80);init[:6]=b'\x7fELF\x02\x01';init[18:20]=b'\xb7\x00'
        data=cpio(bytes(init));self.assertEqual(len(data)%512,0)
        offset=0;entries={}
        while True:
            self.assertEqual(data[offset:offset+6],b'070701')
            fields=[int(data[offset+6+i*8:offset+14+i*8],16) for i in range(13)]
            name=data[offset+110:offset+110+fields[11]-1].decode('ascii')
            begin=(offset+110+fields[11]+3)&~3
            payload=data[begin:begin+fields[6]];offset=(begin+fields[6]+3)&~3
            if name=='TRAILER!!!':break
            entries[name]=(fields,payload)
        self.assertEqual(set(entries),{'dev','dev/console','init'})
        self.assertEqual(entries['dev'][0][1],0o040755)
        self.assertEqual(entries['dev/console'][0][1],0o020600)
        self.assertEqual(entries['dev/console'][0][9:11],[5,1])
        self.assertEqual(entries['init'][0][1],0o100755);self.assertEqual(entries['init'][1],bytes(init))
        self.assertEqual(len({v[0][0] for v in entries.values()}),3)

    def test_invalid_init_is_refused(self):
        for value in (b'',b'\x7fELF\x02\x01'+bytes(58),b'x'*(1024*1024+1)):
            with self.assertRaises(ValueError):cpio(value)

    def test_changed_kernel_source_refused_before_mutation(self):
        parent=ROOT/'note10/private/reservation-tests';parent.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=parent) as name:
            root=Path(name);self.assertTrue(root.resolve().is_relative_to(parent.resolve()))
            source=root/'source';path=source/'arch/arm64/mm/init.c';path.parent.mkdir(parents=True)
            path.write_text('unexpected source',encoding='utf-8');calls=[]
            with self.assertRaisesRegex(ValueError,'Pinned arm64'):prepare(source,root,lambda *args:calls.append(args))
            self.assertEqual(path.read_text(),'unexpected source');self.assertEqual(calls,[])
            self.assertFalse(path.with_name('note10_xnu_reserve.c').exists())


if __name__=='__main__':unittest.main()
