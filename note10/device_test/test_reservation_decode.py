import unittest
from decode_reservation import decode,decode_frames,checksum


LOG='''Linux version 4.14.113-note10-reserve-pc (fixture)
N10RAM1 RESERVED base=a00000000 size=10000000 align=2000000
N10RAM1 CHECK pages=65536 reserved=65536 invalid=0 shift=12
'''


class ReservationDecodeTests(unittest.TestCase):
    identity='0123456789abcdef0123456789abcdef'

    def frame(self,sequence,base='a00000000',reserved=65536,identity=None):
        body=(f'id={identity or self.identity} seq={sequence} base={base} size=10000000 '
              f'align=2000000 pages=65536 reserved={reserved} invalid=0 shift=12')
        return f'N10RAM2 {body} checksum={checksum(body.encode()):08x}\n'

    def test_frame_checksum_known_vectors(self):
        self.assertEqual(checksum(b''),0x811c9dc5)
        self.assertEqual(checksum(b'hello'),0x4f9f2cab)

    def test_intact_redundant_frames_with_corrupted_banner_and_copies(self):
        damaged=self.frame(0).replace('base=a00000000','base=b00000000')
        log='Linux versio\x00 4.x damaged\n'+damaged+self.frame(1)+self.frame(2)
        result=decode_frames(log,self.identity)
        self.assertEqual(result['intact_sequences'],[1,2])
        self.assertEqual(result['region']['base'],0xa00000000)
        self.assertFalse(result['corrupted_frames_repaired'])
        self.assertFalse(result['safe_to_reuse_address_after_reboot'])

    def test_wrong_build_partial_duplicate_conflicting_or_failed_frames(self):
        good=self.frame(0)+self.frame(1)
        for log,identity in ((good,'f'*32),(self.frame(0),self.identity),
                             (self.frame(0)*2,self.identity),
                             (good+self.frame(2,base='b00000000'),self.identity),
                             (good+self.frame(2,reserved=65535),self.identity),
                             (good+self.frame(32),self.identity)):
            with self.subTest(log=log[-80:]),self.assertRaises(ValueError):decode_frames(log,identity)

    def test_every_single_byte_mutation_is_detected(self):
        raw=self.frame(0)
        for offset,char in enumerate(raw.rstrip('\n')):
            damaged=raw[:offset]+chr(ord(char)^1)+raw[offset+1:]
            with self.subTest(offset=offset),self.assertRaises(ValueError):
                decode_frames(damaged+self.frame(1),self.identity)

    def test_complete_previous_boot_evidence(self):
        r=decode(LOG);self.assertTrue(r['previous_boot_reservation_observed'])
        self.assertFalse(r['valid_in_current_recovery_boot']);self.assertFalse(r['safe_to_reuse_address_after_reboot'])

    def test_partial_failed_or_merged_logs(self):
        for t in (LOG.replace('reserved=65536','reserved=65535'),LOG.replace('invalid=0','invalid=1'),
                  LOG+'N10RAM1 FAILED stage=page-state',LOG+LOG,LOG.split('N10RAM1 CHECK')[0],
                  LOG.replace('shift=12','shift=14'),LOG.replace('base=a00000000','base=a00000001'),
                  LOG.replace('size=10000000','size=8000000'),LOG.replace('reserve-pc','handoff-pc'),
                  LOG.replace('base=a00000000','base=10000000000')):
            with self.subTest(text=t[-60:]),self.assertRaises(ValueError):decode(t)


if __name__=='__main__':unittest.main()
