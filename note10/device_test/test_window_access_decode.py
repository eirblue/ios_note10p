import unittest
from decode_reservation import checksum
from decode_window_access import decode,COUNTS

ID='0123456789abcdef0123456789abcdef'


def frame(sequence,**updates):
    fields={'id':ID,'seq':str(sequence),'base':'a00000000','size':'10000000',**{k:str(v) for k,v in COUNTS.items()}}
    fields.update(updates)
    body=' '.join(k+'='+v for k,v in fields.items())
    return 'N10MEM1 '+body+f' checksum={checksum(body.encode()):08x}\n'


def reservation():
    lines=[]
    for seq in range(2):
        body=f'id={ID} seq={seq} base=a00000000 size=10000000 align=2000000 pages=65536 reserved=65536 invalid=0 shift=12'
        lines.append('N10RAM2 '+body+f' checksum={checksum(body.encode()):08x}\n')
    return ''.join(lines)


class AccessDecodeTests(unittest.TestCase):
    def test_complete_agreeing_records(self):
        r=decode(reservation()+frame(0)+frame(1),ID)
        self.assertEqual(r['access_intact_frame_count'],2)
        self.assertFalse(r['valid_in_current_recovery_boot'])
        self.assertFalse(r['kernel_to_xnu_transfer_verified'])
    def test_missing_corrupt_and_duplicate_records(self):
        for frames in (frame(0),frame(0)+frame(0),frame(0)+frame(1).replace('size=10000000','size=10000001')):
            with self.subTest(frames=frames),self.assertRaises(ValueError):decode(reservation()+frames,ID)
    def test_bad_geometry_or_incomplete_counts(self):
        for changes in ({'base':'a20000000'},{'size':'8000000'},{'status':'2'},{'mismatches':'1'},
                        {'rounds':'1'},{'checked':'0'},{'zero_checked':'33554431'},{'seq':'32'},
                        {'words':str(1<<64)}):
            with self.subTest(changes=changes),self.assertRaises(ValueError):
                decode(reservation()+frame(0)+frame(1,**changes),ID)
    def test_build_id_and_reservation_required(self):
        for text,identity in ((frame(0)+frame(1),ID),(reservation()+frame(0)+frame(1),'f'*32)):
            with self.assertRaises(ValueError):decode(text,identity)
    def test_corrupt_copy_not_repaired(self):
        r=decode(reservation()+frame(0)+frame(1)+'N10MEM1 damaged\n',ID)
        self.assertEqual(r['access_intact_sequences'],[0,1])
        self.assertFalse(r['corrupted_frames_repaired'])


if __name__=='__main__':unittest.main()
