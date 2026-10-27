"""Offline contracts for per-cycle evidence and bounded host control."""
import hashlib
import json
import tempfile
import unittest
import urllib.request
from functools import lru_cache
from pathlib import Path
from unittest.mock import patch
import auto_cycle as host
from decode_auto_return import decode, select_cycle_log
from decode_reservation import checksum

IDENTITY = '0123456789abcdef0123456789abcdef'
TOKEN = '1234567890abcdef1234567890abcdef'


def frame(phase, seq, cycle=TOKEN, status=0):
    body = f'id={IDENTITY} cycle={cycle} phase={phase} seq={seq} delay_ms=90000 status={status}'
    return (f'N10RET1 {body} checksum={checksum(body.encode()):08x}\n').encode()


def good():
    return frame(0, 0) + frame(0, 1) + frame(1, 0) + frame(1, 1)


class EvidenceTests(unittest.TestCase):
    def test_complete_return_request(self):
        value = decode(good(), IDENTITY, TOKEN)
        self.assertTrue(value['auto_recovery_request_observed'])
        self.assertFalse(value['hardware_recovery_reentry_verified'])

    def test_old_cycle_cannot_complete_current(self):
        with self.assertRaises(ValueError):
            decode(frame(0, 0) + frame(0, 1) + frame(1, 0, cycle='f'*32) + frame(1, 1, cycle='f'*32), IDENTITY, TOKEN)

    def test_duplicate_missing_or_failed_return_refused(self):
        for data in (good()+frame(1, 0), frame(0, 0)+frame(1, 0)+frame(1, 1), good()+frame(2, 0, status=1), good()+frame(3, 0, status=1)):
            with self.assertRaises(ValueError):
                decode(data, IDENTITY, TOKEN)

    def test_cycle_scope_discards_all_earlier_diagnostics(self):
        old = b'old successful diagnostic\n'
        selected, offset = select_cycle_log(old+good(), IDENTITY, TOKEN)
        self.assertEqual(offset, len(old))
        self.assertEqual(selected, good())

    def test_corrupted_binding_not_repaired(self):
        with self.assertRaises(ValueError):
            select_cycle_log(frame(0, 0)+frame(0, 1).replace(b'checksum=', b'checksum=f'), IDENTITY, TOKEN)

    def test_return_before_arm_refused(self):
        with self.assertRaises(ValueError):
            decode(frame(1, 0)+frame(1, 1)+frame(0, 0)+frame(0, 1), IDENTITY, TOKEN)


class SlotTests(unittest.TestCase):
    def fixture(self,root,data=None):
        from materialize_auto_cycle import SLOT
        data=data if data is not None else b'prefixN10RET1'+SLOT+b'\0suffix'
        source=root/'template';source.mkdir()
        report=dict(build_passed=True,auto_return_diagnostic=True,auto_cycle_slot=SLOT.decode(),
                    image_sha256=hashlib.sha256(data).hexdigest(),image_size=len(data))
        (source/'Image').write_bytes(data)
        (source/'build-result.json').write_text(json.dumps(report))
        return source

    def test_exact_data_slot_only_and_template_unchanged(self):
        from materialize_auto_cycle import materialize,validate,SLOT
        with tempfile.TemporaryDirectory() as name:
            root=Path(name);source=self.fixture(root);original=(source/'Image').read_bytes()
            materialize(source,root/'variant',TOKEN)
            validate(root/'variant',TOKEN,source)
            self.assertEqual((source/'Image').read_bytes(),original)
            self.assertEqual((root/'variant/Image').read_bytes(),original.replace(SLOT,TOKEN.encode()))

    def test_missing_or_duplicate_slot_refused(self):
        from materialize_auto_cycle import materialize,SLOT
        for data in (b'N10RET1',b'N10RET1'+(SLOT+b'\0')*2):
            with tempfile.TemporaryDirectory() as name:
                root=Path(name);source=self.fixture(root,data)
                with self.assertRaises(ValueError):materialize(source,root/'variant',TOKEN)

    def test_bad_template_hash_refused(self):
        from materialize_auto_cycle import materialize
        with tempfile.TemporaryDirectory() as name:
            root=Path(name);source=self.fixture(root)
            (source/'Image').write_bytes(b'changed')
            with self.assertRaises(ValueError):materialize(source,root/'variant',TOKEN)

    def test_other_byte_or_metadata_mutation_refused(self):
        from materialize_auto_cycle import materialize,validate
        for metadata in (False,True):
            with tempfile.TemporaryDirectory() as name:
                root=Path(name);source=self.fixture(root);variant=root/'variant'
                materialize(source,variant,TOKEN)
                if metadata:
                    report=host.read(variant/'build-result.json');report['build_passed']=False
                    host.save(variant/'build-result.json',report)
                else:
                    data=(variant/'Image').read_bytes();(variant/'Image').write_bytes(b'X'+data[1:])
                with self.assertRaises(ValueError):validate(variant,TOKEN)


@lru_cache(maxsize=1)
def pinned_restart_sources():
    from prepare_auto_return import PINS
    result={}
    for name,digest in PINS.items():
        raw=urllib.request.urlopen('https://raw.githubusercontent.com/corsicanu/android_kernel_samsung_universal9820/55f042627bb7030c93550faafa117674d32b21d1/'+name,timeout=40).read()
        if hashlib.sha256(raw).hexdigest()!=digest:raise ValueError('Restart source pin differs')
        result[name]=raw
    return result


class SourceTests(unittest.TestCase):
    def test_pinned_route_preserves_restart_dump_and_recovery_argument(self):
        sources=pinned_restart_sources()
        self.assertIn(b'kmsg_dump(KMSG_DUMP_RESTART)',sources['kernel/reboot.c'])
        self.assertIn(b'!strncmp(cmd, "recovery", 8)',sources['drivers/samsung/sec_reboot.c'])
    def test_extension_is_opt_in_and_armed_before_reservation_gates(self):
        from prepare_auto_return import prepare
        with tempfile.TemporaryDirectory() as name:
            root=Path(name)
            for path,raw in pinned_restart_sources().items():
                p=root/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
            target=root/'arch/arm64/mm/init.c';target.parent.mkdir(parents=True)
            original=b'#include "note10_pm_timer_roundtrip.c"\n    unsigned long start, count, i, reserved = 0, invalid = 0;\n'
            changed,report=prepare(root,target,original)
            self.assertTrue(report['auto_return_diagnostic'])
            self.assertIn(b'n10_arm_auto_return()',changed)
            self.assertLess(changed.index(b'note10_auto_return.c'),changed.index(b'note10_pm_timer_roundtrip.c'))
    def test_restart_source_mutation_rejected(self):
        from prepare_auto_return import prepare
        with tempfile.TemporaryDirectory() as name:
            root=Path(name)
            for path,raw in pinned_restart_sources().items():
                p=root/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw+b'changed')
            with self.assertRaises(ValueError):prepare(root,root/'init.c',b'')


class FakeAdb:
    serial = 'fixture-device'

    def __init__(self):
        self.calls = []

    def text(self, *args):
        self.calls.append(args)
        if args == ('shell', 'command', '-v', 'twrp'):
            return '/sbin/twrp'
        raise AssertionError(args)

    def call(self, *args, **kwargs):
        self.calls.append(args)
        return b''


class HostTests(unittest.TestCase):
    def setUp(self):
        parent = host.ROOT/'note10/private/device-test'
        parent.mkdir(parents=True, exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(dir=parent)
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_no_execute_means_no_device_contact(self):
        with patch.object(host, 'Adb') as adb, self.assertRaises(ValueError):
            host.run_plan(self.root/'none', '0'*64, self.root/'out')
        adb.assert_not_called()

    def test_reviewed_plan_hash_required(self):
        path = self.root/'plan.json'
        path.write_text('{}')
        with self.assertRaises(ValueError):
            host.validate_plan(path, '0'*64)

    def test_current_v7_cannot_be_prepared_for_automatic_run(self):
        build = self.root/'build'
        build.mkdir()
        (build/'build-result.json').write_text(json.dumps(dict(build_passed=True, auto_return_diagnostic=False)))
        with patch.object(host, 'Adb') as adb, self.assertRaises(ValueError):
            host.prepare_plan(kernel_build=build, backup=self.root/'backup', twrp=self.root/'twrp', mkbootimg=self.root/'mk', current_packages=self.root/'current', output=self.root/'out')
        adb.assert_not_called()

    def fixture(self):
        packages = self.root/'packages'
        packages.mkdir()
        capture = self.root/'capture'
        capture.mkdir()
        (capture/'selected.txt').write_bytes(good())
        plan = dict(stages=[dict(index=1, cycle=TOKEN, kernel_build=str(self.root/'variant'), packages=str(packages))], kernel_build=str(self.root/'kernel'), backup=str(self.root/'backup'), core_model='core', gate_model='gate', init_model='init', identity=IDENTITY, return_timeout_seconds=240, image_sha256='a'*64, backup_manifest_sha256='b'*64)
        captured = dict(diagnostic_passed=True, directory=str(capture), log_selections={'log': dict(selected_file='selected.txt')})
        return plan, captured

    def invoke(self, *, ready_error=None, timeout=False, passed=True, missing_return=False):
        plan, captured = self.fixture()
        captured['diagnostic_passed'] = passed
        if missing_return:
            (Path(captured['directory'])/'selected.txt').write_bytes(frame(0, 0)+frame(0, 1))
        adb = FakeAdb()
        with patch.object(host, 'validate_plan', return_value=plan), patch.object(host, 'preflight', return_value={'twrp_version': 'fixture'}), patch.object(host, 'stage', return_value={'ram_directory': '/tmp/fixture'}), patch.object(host, 'check', side_effect=ready_error, return_value={'ready_for_manual_access_test': True}), patch.object(host, 'verify_packages', return_value=[dict(mode='diagnostic', file='diag.zip', payload_sha256='c'*64)]), patch.object(host, 'boot_id', return_value='before'), patch.object(host, 'verify_partitions'), patch.object(host, 'wait_recovery', side_effect=TimeoutError('timeout') if timeout else None, return_value='after'), patch.object(host, 'collect', return_value=captured):
            try:
                result = host.run_plan(self.root/'plan', 'd'*64, self.root/'out', execute=True, adb=adb)
                error = None
            except Exception as caught:
                result, error = None, caught
        return adb, result, error

    def test_single_cycle_orders_install_reboot_collect(self):
        adb, result, error = self.invoke()
        self.assertIsNone(error)
        self.assertEqual(result['status'], 'complete')
        self.assertTrue(result['single_cycle_verified'])
        self.assertEqual([c[2] for c in adb.calls if c[:2] == ('shell', 'twrp')], ['install', 'reboot'])

    def test_low_battery_stops_before_install(self):
        adb, result, error = self.invoke(ready_error=ValueError('battery'))
        self.assertIsInstance(error, ValueError)
        self.assertFalse(any(c[:2] == ('shell', 'twrp') for c in adb.calls))

    def test_timeout_never_retries_reboot_or_install(self):
        adb, result, error = self.invoke(timeout=True)
        self.assertIsInstance(error, TimeoutError)
        self.assertEqual(sum(c[:2] == ('shell', 'twrp') for c in adb.calls), 2)

    def test_failed_diagnostic_stops_repetitions(self):
        adb, result, error = self.invoke(passed=False)
        self.assertIsInstance(error, ValueError)
        self.assertEqual(host.read(self.root/'out/journal.json')['status'], 'stopped')

    def test_missing_return_does_not_issue_commission_proof(self):
        adb, result, error = self.invoke(missing_return=True)
        self.assertIsInstance(error, ValueError)
        self.assertFalse(host.read(self.root/'out/journal.json')['single_cycle_verified'])

    def test_multiple_cycles_require_prior_single_cycle_proof(self):
        plan, capture = self.fixture()
        plan['stages'] *= 2
        with patch.object(host, 'validate_plan', return_value=plan), patch.object(host, 'Adb') as adb, self.assertRaises(ValueError):
            host.run_plan(self.root/'plan', 'd'*64, self.root/'out', execute=True, limit=2)
        adb.assert_not_called()

    def test_wait_does_not_accept_old_recovery_boot(self):
        clock = [0]
        def sleep(n):
            clock[0] += n
        with patch.object(host, 'preflight'), patch.object(host, 'boot_id', side_effect=['old', 'old', 'new']):
            self.assertEqual(host.wait_recovery(FakeAdb(), 'old', 10, monotonic=lambda: clock[0], sleep=sleep), 'new')


class BatteryPolicyTests(unittest.TestCase):
    def test_user_authorized_floor_and_invalid_capacity(self):
        from precheck_window_access import require_install_battery
        for capacity in (10, 11, 30, 100):
            require_install_battery(capacity)
        for capacity in (-1, 0, 9, 101):
            with self.assertRaises(ValueError):
                require_install_battery(capacity)


if __name__ == '__main__':
    unittest.main()
