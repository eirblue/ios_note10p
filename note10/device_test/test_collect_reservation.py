"""Collector contract tests with in-memory ADB responses; no device access."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import collect_reservation as collector
from decode_reservation import checksum


class FakeAdb:
    def __init__(self,log):self.log=log;self.calls=[]
    def text(self,*args):
        if args!=('shell','getprop','ro.bootloader'):raise AssertionError(args)
        return 'N976NKSU2HWH5'
    def call(self,*args,**kwargs):
        self.calls.append(args)
        if args[:3]==('shell','test','-r'):
            if args[3]!='/proc/last_kmsg':raise RuntimeError('missing fixture pstore')
            return b''
        if args==('exec-out','cat','/proc/last_kmsg'):return self.log
        raise AssertionError(args)


class CollectorTests(unittest.TestCase):
    identity='0123456789abcdef0123456789abcdef'
    def frame(self,seq):
        body=(f'id={self.identity} seq={seq} base=a00000000 size=10000000 align=2000000 '
              'pages=65536 reserved=65536 invalid=0 shift=12')
        return f'N10RAM2 {body} checksum={checksum(body.encode()):08x}\n'

    def access_frame(self,seq,**changes):
        values={'words':33554432,'written':67108864,'checked':67108864,'zeroed':33554432,
                'zero_checked':33554432,'mismatches':0,'rounds':2,'status':0}
        values.update(changes)
        body=f'id={self.identity} seq={seq} base=a00000000 size=10000000 '+' '.join(k+'='+str(v) for k,v in values.items())
        return 'N10MEM1 '+body+f' checksum={checksum(body.encode()):08x}\n'

    def xnu_frame(self,seq):
        from decode_reservation import checksum
        body=(f'id={self.identity} seq={seq} base=a00000000 size=10000000 bytes=16384 '
              f'sha256={"a"*64} status=0')
        return f'N10XNU1 {body} checksum={checksum(body.encode()):08x}\n'

    def run_fixture(self,log,*,version2=True,missing_image_id=False,access=False,xnu_stage=False):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);build=root/'build';build.mkdir();packages=root/'packages';packages.mkdir()
            image=b'Linux version 4.14.113-note10-reserve-pc (fixture)\0'
            if version2 and not missing_image_id:image+=self.identity.encode()+b'\0'
            digest=hashlib.sha256(image).hexdigest();(build/'Image').write_bytes(image)
            report={'build_passed':True,'early_xnu_reservation':True,'image_sha256':digest}
            if version2:report.update(reservation_evidence_version=2,reservation_evidence_id=self.identity)
            if access:report.update(window_access_diagnostic=True,window_access_evidence_version=1)
            if xnu_stage:report.update(xnu_payload_stage_diagnostic=True,xnu_payload_size=16384,xnu_payload_sha256='a'*64)
            (build/'build-result.json').write_text(json.dumps(report))
            (packages/'package-result.json').write_text(json.dumps({'kernel_image_sha256':digest,
                'window_access_diagnostic':access,'xnu_payload_stage_diagnostic':xnu_stage,
                'xnu_payload_size':16384 if xnu_stage else None,'xnu_payload_sha256':'a'*64 if xnu_stage else None}))
            records=[{'file':'note10-reservation-'+kind+'.zip'} for kind in ('diagnostic','rollback')]
            adb=FakeAdb(log.encode())
            with patch.object(collector,'ROOT',root),patch.object(collector,'verify_packages',return_value=records), \
                 patch.object(collector,'preflight',return_value={'twrp_version':'fixture'}) as preflight:
                if missing_image_id or (access and not version2):
                    with self.assertRaises(ValueError):collector.collect(packages,build,adb)
                    preflight.assert_not_called();return
                result=collector.collect(packages,build,adb)
            self.assertEqual(set(result['logs_sha256']),{'last_kmsg.txt'})
            self.assertFalse(result['partition_writes']);self.assertFalse(result['rebooted'])
            self.assertFalse(any(call[:2]==('exec-out','cat') and 'pstore' in call[-1] for call in adb.calls))
            return result

    def test_build_bound_frames_work_with_damaged_banner_and_missing_pstore(self):
        result=self.run_fixture('Linux versio\0 damaged\n'+self.frame(1)+self.frame(2))
        self.assertTrue(result['previous_boot_reservation_observed'])

    def test_missing_embedded_id_rejected_before_device_access(self):
        self.run_fixture(self.frame(1)+self.frame(2),missing_image_id=True)

    def test_one_frame_not_enough(self):
        self.assertFalse(self.run_fixture(self.frame(1))['previous_boot_reservation_observed'])

    def test_legacy_exact_banner_still_required(self):
        log=('Linux version 4.14.113-note10-reserve-pc (fixture)\n'
             'N10RAM1 RESERVED base=a00000000 size=10000000 align=2000000\n'
             'N10RAM1 CHECK pages=65536 reserved=65536 invalid=0 shift=12\n')
        self.assertTrue(self.run_fixture(log,version2=False)['previous_boot_reservation_observed'])
        self.assertFalse(self.run_fixture(log.replace('(fixture)','(other)'),version2=False)['previous_boot_reservation_observed'])

    def test_access_requires_its_own_complete_evidence(self):
        base=self.frame(1)+self.frame(2)
        result=self.run_fixture(base,access=True)
        self.assertTrue(result['previous_boot_reservation_observed'])
        self.assertFalse(result['previous_boot_window_access_observed'])
        self.assertFalse(result['diagnostic_passed'])
        result=self.run_fixture(base+self.access_frame(0)+self.access_frame(1),access=True)
        self.assertTrue(result['diagnostic_passed']);self.assertTrue(result['previous_boot_window_access_observed'])

    def test_access_failure_cannot_fall_back_to_reservation_pass(self):
        log=self.frame(1)+self.frame(2)+self.access_frame(0)+self.access_frame(1,mismatches=1,status=2)
        result=self.run_fixture(log,access=True)
        self.assertTrue(result['previous_boot_reservation_observed'])
        self.assertFalse(result['diagnostic_passed'])

    def test_xnu_stage_requires_matching_hash_bound_frames(self):
        base=self.frame(1)+self.frame(2)+self.access_frame(0)+self.access_frame(1)
        result=self.run_fixture(base,access=True,xnu_stage=True)
        self.assertFalse(result['diagnostic_passed'])
        result=self.run_fixture(base+self.xnu_frame(0)+self.xnu_frame(1),access=True,xnu_stage=True)
        self.assertTrue(result['diagnostic_passed'])
        self.assertTrue(result['previous_boot_xnu_payload_stage_observed'])

    def test_access_without_build_id_refused_before_device_access(self):
        self.run_fixture('',version2=False,access=True)


if __name__=='__main__':unittest.main()
