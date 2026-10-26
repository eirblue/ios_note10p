import argparse
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import unittest
import urllib.request
from decode_pm_timer import decode
from prepare_pm_diagnostic import patch_suspend,SUSPEND_SHA
from test_cpu_cache_decode import summary,snapshots,SHA,SIZE,frame
from test_cpu_cache_native import prefix,IDENTITY


@lru_cache(maxsize=1)
def pinned_source():
    url=('https://raw.githubusercontent.com/corsicanu/android_kernel_samsung_universal9820/'
         '55f042627bb7030c93550faafa117674d32b21d1/kernel/power/suspend.c')
    raw=urllib.request.urlopen(url,timeout=45).read(1024*1024)
    if hashlib.sha256(raw).hexdigest()!=SUSPEND_SHA:raise ValueError('Pinned PM source hash differs')
    return raw


def pm(seq,**changes):
    values=dict(id=IDENTITY,seq=seq,before='ff',after='ff',devices=1,resume=1,blocked=0,
        oldlevel=0,newlevel=0,resume_errors=0,timers=8,error=0,sha256=SHA,status=0)
    values.update(changes);return frame('N10PMT1',values)


def timer(seq,cpu,**changes):
    values=dict(id=IDENTITY,seq=seq,cpu=cpu,before='f5',cleared='5',restored='f5',freq='18cba80',status=0)
    values.update(changes);return frame('N10TMR1',values)


def timers():return ''.join(timer(seq,cpu) for cpu in range(8) for seq in range(2))


class PmTimerTests(unittest.TestCase):
    def parse(self,text):
        chain=prefix(SHA,SIZE)+summary(0)+summary(1)+snapshots()
        return decode(chain+text,IDENTITY,SHA,SIZE)

    def binding(self,seq,banner='Linux version fixture',identity=IDENTITY):
        from decode_reservation import checksum
        body=f'id={identity} seq={seq} banner={banner}'
        return f'N10BND1 {body} checksum={checksum(body.encode()):08x}\n'

    def test_exact_bound_banner_corroborates_only_latest_interval(self):
        from collect_reservation import select_latest_boot
        start='<5>[    0.000000] Linux version damaged\n'
        log=start+self.binding(0)+self.binding(1)
        selected,report=select_latest_boot(log.encode(),'Linux version fixture',boot_binding_id=IDENTITY)
        self.assertEqual(selected,log.encode())
        self.assertTrue(report['exact_checksummed_banner_binding'])
        self.assertFalse(report['corrupted_bytes_repaired'])
        with self.assertRaises(ValueError):
            select_latest_boot(log.encode(),'Linux version fixture')
        with self.assertRaises(ValueError):
            select_latest_boot((log+start).encode(),'Linux version fixture',boot_binding_id=IDENTITY)

    def test_boot_binding_missing_wrong_duplicate_or_conflicting_refused(self):
        from collect_reservation import select_latest_boot
        start='<5>[    0.000000] Linux version damaged\n'
        for frames in (self.binding(0),self.binding(0)+self.binding(0),
                self.binding(0)+self.binding(1,banner='Linux version other'),
                self.binding(0)+self.binding(1,identity='f'*32),
                self.binding(0)+self.binding(1).replace('checksum=','checksum=f')):
            with self.subTest(frames=frames),self.assertRaises(ValueError):
                select_latest_boot((start+frames).encode(),'Linux version fixture',boot_binding_id=IDENTITY)

    def test_cpu_copies_are_interleaved_and_pm_delayed_without_wakeup_bypass(self):
        here=Path(__file__).resolve().parent
        cpu=(here/'cpu_cache_roundtrip.c').read_text()
        self.assertIn('for (sequence = 0; sequence < 32; ++sequence) {\n        for (cpu = 0; cpu < 8; ++cpu)',cpu)
        worker=(here/'pm_timer_roundtrip.c').read_text()
        self.assertLess(worker.index('on_each_cpu(n10_timer_cpu'),worker.index('error = n10_pm_devices_test'))
        self.assertIn('msecs_to_jiffies(30000)',worker)
        self.assertIn('msecs_to_jiffies(10000)',worker)
        self.assertIn('n10_pm_attempts < 3',worker)
        self.assertNotIn('pm_wakeup_clear',worker)

    def test_all_phases_and_eight_restored_timers(self):
        result=self.parse(pm(0)+pm(1)+timers())
        self.assertTrue(result['previous_boot_pm_timer_observed'])
        self.assertFalse(result['lowlevel_suspend_entered'])
        self.assertFalse(result['dma_quiescence_verified'])

    def test_failed_pm_phase_or_error_never_passes(self):
        for changes in (dict(devices=0),dict(resume=0),dict(blocked=1),dict(newlevel=4),
                        dict(resume_errors=1),dict(timers=7),dict(error=16),dict(status=4)):
            with self.subTest(changes=changes),self.assertRaises(ValueError):
                self.parse(pm(0)+pm(1,**changes)+timers())

    def test_timer_wrong_clear_restore_missing_duplicate_rejected(self):
        for text in (timers().replace(timer(1,7),''),timers()+timer(0,3),
                     timers().replace(timer(1,2),timer(1,2,cleared='15')),
                     timers().replace(timer(1,1),timer(1,1,restored='f4'))):
            with self.assertRaises(ValueError):self.parse(pm(0)+pm(1)+text)

    def test_missing_cpu_prerequisite_cannot_pass(self):
        with self.assertRaises(ValueError):decode(prefix(SHA,SIZE)+pm(0)+pm(1)+timers(),IDENTITY,SHA,SIZE)

    def test_actual_pinned_suspend_patch_has_device_exit_and_lowlevel_guard(self):
        raw=pinned_source();patched=patch_suspend(raw).decode()
        guard=patched.index('++n10_pm_active->blocked;')
        low=patched.index('error = suspend_enter(state, &wakeup);')
        self.assertLess(guard,low)
        self.assertIn('goto Resume_devices;',patched[guard:low])
        self.assertIn('if (suspend_test(TEST_DEVICES)) {\n\t\tif (n10_pm_active) ++n10_pm_active->devices;',patched)
        self.assertIn('if (n10_test)\n\t\tpm_test_level = n10_old_level;',patched)
        self.assertIn('n10_pm_owner != current',patched)
        self.assertIn('n10_pm_active->stage = 11;',patched)
        self.assertIn('n10_pm_active->stage = 21;',patched)
        self.assertEqual(patched.count('#include "note10_pm_devices_backend.c"'),1)
        with self.assertRaises(ValueError):patch_suspend(raw+b'changed')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--report',type=Path)
    args,remaining=parser.parse_known_args()
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(PmTimerTests)
    result=unittest.TextTestRunner().run(suite)
    if not result.wasSuccessful():raise SystemExit(1)
    if args.report:
        args.report.parent.mkdir(parents=True,exist_ok=True)
        args.report.write_text(json.dumps(dict(passed=True,cases=result.testsRun,source_sha256=SUSPEND_SHA,
            patched_sha256=hashlib.sha256(patch_suspend(pinned_source())).hexdigest()),indent=2))
