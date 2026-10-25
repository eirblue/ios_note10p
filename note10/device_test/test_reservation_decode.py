import unittest
from decode_reservation import decode


LOG='''Linux version 4.14.113-note10-reserve-pc (fixture)
N10RAM1 RESERVED base=a00000000 size=10000000 align=2000000
N10RAM1 CHECK pages=65536 reserved=65536 invalid=0 shift=12
'''


class ReservationDecodeTests(unittest.TestCase):
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
