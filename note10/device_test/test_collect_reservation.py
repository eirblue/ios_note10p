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
    def test_dma_generation_from_actual_pm_decoder_and_saved_json(self):
        from decode_pm_timer import decode_quiescence
        from test_pm_quiesce_decode import record
        from test_dma_pm_contract import evidence,ID
        pm={'quiescence':decode_quiescence(record(0,id=ID,generation=2)+record(1,id=ID,generation=2),ID)}
        for value in (pm,json.loads(json.dumps(pm))):
            self.assertTrue(collector.decode_dma_pm_observation(evidence(),ID,value)['dma_pm_framework_observed'])
        pm['quiescence']['attempts'][1]['result']['generation']=3
        with self.assertRaises(ValueError):collector.decode_dma_pm_observation(evidence(),ID,pm)
    def test_ufs_generation_from_actual_pm_decoder_and_saved_json(self):
        from decode_pm_timer import decode_quiescence
        from test_pm_quiesce_decode import record
        from test_ufs_pm_contract import evidence,ID
        pm={'quiescence':decode_quiescence(record(0,id=ID,generation=2)+record(1,id=ID,generation=2),ID)}
        for value in (pm,json.loads(json.dumps(pm))):
            self.assertTrue(collector.decode_ufs_pm_observation(evidence(),ID,value)['ufs_pm_driver_state_observed'])
        pm['quiescence']['attempts'][1]['result']['generation']=3
        with self.assertRaises(ValueError):collector.decode_ufs_pm_observation(evidence(),ID,pm)

    def test_iommu_generation_from_actual_pm_decoder_and_saved_json(self):
        from decode_pm_timer import decode_quiescence
        from test_pm_quiesce_decode import record
        from test_iommu_pm_contract import evidence,ID
        pm={'quiescence':decode_quiescence(record(0,id=ID,generation=2)+record(1,id=ID,generation=2),ID)}
        for value in (pm,json.loads(json.dumps(pm))):
            self.assertTrue(collector.decode_iommu_pm_observation(evidence(),ID,value)['iommu_pm_driver_inventory_observed'])
        pm['quiescence']['attempts'][1]['result']['generation']=3
        with self.assertRaises(ValueError):collector.decode_iommu_pm_observation(evidence(),ID,pm)
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

    def run_fixture(self,log,*,version2=True,missing_image_id=False,access=False,xnu_stage=False,cpu_cache=False,pm_timer=False,boot_binding=False,auto_return=False):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);build=root/'build';build.mkdir();packages=root/'packages';packages.mkdir()
            image=b'Linux version 4.14.113-note10-reserve-pc (fixture)\0'
            if version2 and not missing_image_id:image+=self.identity.encode()+b'\0'
            digest=hashlib.sha256(image).hexdigest();(build/'Image').write_bytes(image)
            report={'build_passed':True,'early_xnu_reservation':True,'image_sha256':digest}
            if version2:report.update(reservation_evidence_version=2,reservation_evidence_id=self.identity)
            if access:report.update(window_access_diagnostic=True,window_access_evidence_version=1)
            if xnu_stage:report.update(xnu_payload_stage_diagnostic=True,xnu_payload_size=16384,xnu_payload_sha256='a'*64)
            if cpu_cache:report.update(cpu_cache_roundtrip_diagnostic=True,cpu_cache_evidence_version=1)
            if pm_timer:report.update(pm_timer_diagnostic=True,pm_timer_evidence_version=1)
            if boot_binding:report.update(boot_binding_evidence_version=1)
            if auto_return:report.update(auto_return_diagnostic=True,auto_return_evidence_version=1)
            (build/'build-result.json').write_text(json.dumps(report))
            (packages/'package-result.json').write_text(json.dumps({'kernel_image_sha256':digest,
                'window_access_diagnostic':access,'xnu_payload_stage_diagnostic':xnu_stage,
                'cpu_cache_roundtrip_diagnostic':cpu_cache,'pm_timer_diagnostic':pm_timer,
                'auto_return_diagnostic':auto_return,'auto_cycle_token':self.identity if auto_return else None,
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
            self.assertEqual((Path(result['directory'])/'last_kmsg.txt').read_bytes(),log.encode())
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

    def boot_header(self,banner='Linux version 4.14.113-note10-reserve-pc (fixture)'):
        return '<5>[    0.000000]  [0: swapper: 0] '+banner+'\n'

    def test_merged_boots_use_latest_complete_boundary_preserving_raw(self):
        first=self.boot_header()+self.frame(0)+self.frame(1)
        latest=self.boot_header()+self.frame(0)+self.frame(1)
        result=self.run_fixture(first+latest)
        self.assertTrue(result['diagnostic_passed'])
        selected=result['log_selections']['last_kmsg.txt']
        self.assertEqual(selected['byte_start'],len(first.encode()))
        self.assertEqual(selected['selected_sha256'],hashlib.sha256(latest.encode()).hexdigest())
        self.assertFalse(selected['older_pass_fallback'])

    def test_latest_incomplete_boot_cannot_fall_back_to_older_pass(self):
        first=self.boot_header()+self.frame(0)+self.frame(1)
        latest=self.boot_header()+self.frame(0)
        self.assertFalse(self.run_fixture(first+latest)['diagnostic_passed'])

    def test_newer_wrong_banner_refused_even_with_matching_frame_id(self):
        first=self.boot_header()+self.frame(0)+self.frame(1)
        latest=self.boot_header('Linux version 4.14.113-note10-reserve-pc (other)')+self.frame(0)+self.frame(1)
        result=self.run_fixture(first+latest)
        self.assertFalse(result['diagnostic_passed'])
        self.assertIn('banner differs',result['decode_failures']['last_kmsg.txt'])

    def test_duplicate_frames_inside_selected_boot_still_refused(self):
        latest=self.boot_header()+self.frame(0)+self.frame(1)+self.frame(0)
        self.assertFalse(self.run_fixture(latest)['diagnostic_passed'])

    def test_evidence_families_cannot_be_joined_across_boots(self):
        first=self.boot_header()+self.frame(0)+self.frame(1)+self.access_frame(0)+self.access_frame(1)
        latest=self.boot_header()+self.frame(0)+self.frame(1)+self.xnu_frame(0)+self.xnu_frame(1)
        self.assertFalse(self.run_fixture(first+latest,access=True,xnu_stage=True)['diagnostic_passed'])

    def test_cpu_cache_batch_cannot_pass_on_payload_stage_alone(self):
        from test_cpu_cache_decode import summary,snapshots
        text=self.frame(0)+self.frame(1)+self.access_frame(0)+self.access_frame(1)+self.xnu_frame(0)+self.xnu_frame(1)
        result=self.run_fixture(text,access=True,xnu_stage=True,cpu_cache=True)
        self.assertFalse(result['diagnostic_passed'])
        self.assertTrue(result['previous_boot_xnu_payload_stage_observed'])
        result=self.run_fixture(text+summary(0)+summary(1)+snapshots(),access=True,xnu_stage=True,cpu_cache=True)
        self.assertTrue(result['diagnostic_passed'])
        self.assertTrue(result['previous_boot_cpu_cache_roundtrip_observed'])

    def test_pm_scope_requires_its_own_complete_chain(self):
        from test_cpu_cache_decode import summary,snapshots
        from test_pm_timer_contract import pm,timers
        text=self.frame(0)+self.frame(1)+self.access_frame(0)+self.access_frame(1)+self.xnu_frame(0)+self.xnu_frame(1)
        text+=summary(0)+summary(1)+snapshots()
        result=self.run_fixture(text,access=True,xnu_stage=True,cpu_cache=True,pm_timer=True)
        self.assertTrue(result['previous_boot_cpu_cache_roundtrip_observed'])
        self.assertFalse(result['diagnostic_passed'])
        result=self.run_fixture(text+pm(0)+pm(1)+timers(),access=True,xnu_stage=True,cpu_cache=True,pm_timer=True)
        self.assertTrue(result['diagnostic_passed'])
        self.assertTrue(result['previous_boot_pm_timer_observed'])

    def test_damaged_start_banner_needs_exact_in_interval_panic_banner_and_id(self):
        start=self.boot_header('Linux version 4.14.113-note10-reserve+pc (fixture)')
        exact='<0>[  123.000000] I[0:swapper:0] linux_banner: Linux version 4.14.113-note10-reserve-pc (fixture)\n'
        log=start+self.frame(0)+self.frame(1)+exact
        result=self.run_fixture(log)
        self.assertTrue(result['diagnostic_passed'])
        self.assertTrue(result['log_selections']['last_kmsg.txt']['exact_panic_banner_corroboration'])
        self.assertFalse(result['log_selections']['last_kmsg.txt']['start_banner_matches_image'])
        self.assertFalse(self.run_fixture(log.replace(exact,exact.replace('(fixture)','(other)')))['diagnostic_passed'])
        self.assertFalse(self.run_fixture(start+exact)['diagnostic_passed'])

    def test_new_build_bound_banner_is_checked_by_collector(self):
        banner='Linux version 4.14.113-note10-reserve-pc (fixture)'
        frames=''
        for seq in range(2):
            body=f'id={self.identity} seq={seq} banner={banner}'
            frames+=f'N10BND1 {body} checksum={checksum(body.encode()):08x}\n'
        log=self.boot_header('Linux version damaged')+self.frame(0)+self.frame(1)+frames
        self.assertFalse(self.run_fixture(log)['diagnostic_passed'])
        result=self.run_fixture(log,boot_binding=True)
        self.assertTrue(result['diagnostic_passed'])
        self.assertTrue(result['log_selections']['last_kmsg.txt']['exact_checksummed_banner_binding'])

    def auto_arm(self,seq):
        body=f'id={self.identity} cycle={self.identity} phase=0 seq={seq} delay_ms=90000 status=0'
        return f'N10RET1 {body} checksum={checksum(body.encode()):08x}\n'

    def test_previous_cycle_diagnostics_cannot_pass_new_arm(self):
        from test_cpu_cache_decode import summary,snapshots
        from test_pm_timer_contract import pm,timers
        old=self.frame(0)+self.frame(1)+self.access_frame(0)+self.access_frame(1)+self.xnu_frame(0)+self.xnu_frame(1)+summary(0)+summary(1)+snapshots()+pm(0)+pm(1)+timers()
        result=self.run_fixture(old+self.auto_arm(0)+self.auto_arm(1),access=True,xnu_stage=True,cpu_cache=True,pm_timer=True,auto_return=True)
        self.assertFalse(result['diagnostic_passed'])
        result=self.run_fixture(self.auto_arm(0)+self.auto_arm(1)+old,access=True,xnu_stage=True,cpu_cache=True,pm_timer=True,auto_return=True)
        self.assertTrue(result['diagnostic_passed'])

    def test_old_panic_banner_cannot_corroborate_new_boot(self):
        old=self.boot_header()+self.frame(0)+self.frame(1)
        old+='<0>[  123.000000] I[0:swapper:0] linux_banner: Linux version 4.14.113-note10-reserve-pc (fixture)\n'
        latest=self.boot_header('Linux version other')+self.frame(0)+self.frame(1)
        self.assertFalse(self.run_fixture(old+latest)['diagnostic_passed'])


if __name__=='__main__':unittest.main()
