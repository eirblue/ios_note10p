"""NEW v72 cases only. Scratch files, native route stubs and fake transport."""
import argparse
from contextlib import ExitStack
import hashlib
import json
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
# Pin direct first-use bytes before importing local helpers. Existing legacy
# modules may import definitions transitively; no old suite/model is invoked.
FIRST_USE_INPUTS = (
    'test_builtin_init_route.py', 'builtin_init_route.py', 'builtin_init_route.c',
    'builtin_init_route_fixture.c', 'builtin_init_profile.py', 'sha256_kat_device_profile.py',
    'auto_cycle.py', 'run_probe.py', 'stage_phase2.py', 'precheck_window_access.py',
    'collect_reservation.py', 'materialize_auto_cycle.py', 'prepare_linux_boot.py',
    'prepare_reservation_kernel.py', 'build_boot_test_packages.py', 'build_sha256_kat_recovery.py',
    'decode_reservation.py', 'decode_auto_return.py', 'decode_sha256_runtime_kat.py')
FIRST_USE_PINS = {n: hashlib.sha256((HERE/n).read_bytes()).hexdigest() for n in FIRST_USE_INPUTS}

import builtin_init_route as route
import builtin_init_profile as evidence
import sha256_kat_device_profile as profile
import auto_cycle as cycle_host
from decode_reservation import checksum

HERE = Path(__file__).resolve().parent
OUTPUT = None
SELECTED = ()
ID, CYCLE, BOOT = '1'*32, '2'*32, '3a'*16
BANNER = 'Linux version 4.14.113-v72-builtin-init fixture-only'
ANSWER = 'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad'
CASE_NAMES = (
    'test_native_default_off', 'test_native_success', 'test_native_missing', 'test_native_exec_failure',
    'test_cpio_closed_members_modes', 'test_elf_reject_interpreter', 'test_elf_reject_writable_code',
    'test_forced_input_binding', 'test_reject_missing_force', 'test_reject_changed_embedded_archive',
    'test_guard_reject_changed_source', 'test_decode_complete_startup', 'test_decode_missing_boundary',
    'test_decode_panic_banner', 'test_decode_missing_actual_PID1', 'test_decode_mixed_boot_identity',
    'test_decode_duplicate_route', 'test_snapshot_all_before_evaluation', 'test_snapshot_cat_failure_no_fallback',
    'test_decode_multiple_current_cycle_boots',
    'test_snapshot_probe_failure_no_fallback', 'test_snapshot_current_bad_file_no_fallback',
    'test_probe_native_forms_receipt', 'test_probe_LF_unchanged', 'test_probe_wrong_path_no_call', 'test_probe_malformed_not_repaired', 'test_raw_log_bytes_unchanged',
    'test_journal_preID_order_reboot_return', 'test_journal_reboot_error_no_resend',
    'test_wait_records_rejections_and_IDs', 'test_execute_false_has_no_journal',
    'test_historical_host_pins_are_distinct', 'test_new_fields_cannot_be_omitted',
    'test_current_BOOT_binding_accepts_private_pin', 'test_current_BOOT_binding_rejects_obsolete_or_wrong_pin',
    'test_new_package_scope_carries_all_pins', 'test_new_package_scope_rejects_historical_host_head',
)
CASE_IDS = tuple('BuiltinRouteTests.'+n for n in CASE_NAMES)


def fake_elf():
    data = bytearray(256)
    data[:6] = b'\x7fELF\x02\x01'
    struct.pack_into('<HHIQQQ', data, 16, 2, 183, 1, 0x400080, 64, 0)
    struct.pack_into('<HHHHHH', data, 52, 64, 56, 1, 0, 0, 0)
    struct.pack_into('<IIQQQQQQ', data, 64, 1, 5, 0, 0x400000, 0, len(data), len(data), 4096)
    data[128:139] = b'N10MININIT2\0'
    return bytes(data)


def frames():
    def line(tag, body):
        return f'N10BOOTLINK2 boot={BOOT} {tag} {body} checksum={checksum(body.encode()):08x}\n'
    arm = ''.join(line('N10RET1', f'id={ID} cycle={CYCLE} phase=0 seq={i} delay_ms=90000 status=0') for i in (0, 1))
    start = (f'N10ROUTE2 id={ID} boot={BOOT} cycle={CYCLE} route=builtin exec_attempt=1\n'
             f'N10INIT2 id={ID} boot={BOOT} cycle={CYCLE} route=builtin started=1\n')
    kat = ''.join(line('N10SHA1', f'id={ID} copy={i} phase=late-init status=0 driver_match=1 computed=1 digest={ANSWER}') for i in (0, 1))
    request = ''.join(line('N10RET1', f'id={ID} cycle={CYCLE} phase=1 seq={i} delay_ms=90000 status=0') for i in (0, 1))
    return ('[    0.000000] '+BANNER+'\n'+arm+start+kat+request).encode()


class FakeTransport:
    def __init__(self, values=None):
        self.values, self.events = values or {}, []

    def call(self, *args, **kwargs):
        self.events.append(args)
        for _, remote in evidence.LOGS:
            if args == ('shell', '-T', profile.log_probe_command(remote)):
                value = self.values.get(('probe', remote), b'N10KAT_ABSENT\n')
                break
            if args == ('exec-out', 'cat', remote):
                value = self.values.get(('cat', remote), frames())
                break
        else:
            raise AssertionError(args)
        if isinstance(value, Exception): raise value
        return value


def generated_main():
    # Pin injection exists only in this scratch fixture. Production requires
    # exact MAIN_SHA and actual kernel compilation in the following Image step.
    source = b'''#include <linux/init.h>
static void kernel_init_freeable(void)
{
\tif (!ramdisk_execute_command)
\t\tramdisk_execute_command = "/init";

\tif (sys_access((const char __user *) ramdisk_execute_command, 0) != 0) {
\t\tramdisk_execute_command = NULL;
\t\tprepare_namespace();
\t}
}
static int kernel_init(void)
{
    int ret;
    system_state = SYSTEM_RUNNING;
\tif (ramdisk_execute_command) {
\t\tret = run_init_process(ramdisk_execute_command);
        if (!ret) return 0;
    }
    ++normal_attempts;
    return 0;
}
'''
    with patch.object(route, 'MAIN_SHA', route.sha(source)):
        return route.guard_main(source)


class BuiltinRouteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = OUTPUT
        cls.root.mkdir(parents=True)
        if any('.test_native_' in n for n in SELECTED):
            folder = cls.root/'native'
            (folder/'linux').mkdir(parents=True)
            (folder/'linux/init.h').write_bytes(b'/* native fixture header only */\n')
            (folder/'guarded-main-fixture.h').write_bytes(generated_main())
            shutil.copyfile(HERE/'builtin_init_route.c', folder/'builtin_init_route.c')
            shutil.copyfile(HERE/'builtin_init_route_fixture.c', folder/'fixture.c')
            cls.native = folder/'route-fixture'
            argv = ['gcc', '-std=c99', '-Wall', '-Wextra', '-Werror', '-Wno-unused-function',
                    '-I'+str(folder), str(folder/'fixture.c'), '-o', str(cls.native)]
            result = subprocess.run(argv, capture_output=True, timeout=60)
            evidence.raw_file(folder/'compile.stdout', result.stdout)
            evidence.raw_file(folder/'compile.stderr', result.stderr)
            evidence.save(folder/'compile.json', dict(argv=argv, returncode=result.returncode))
            if result.returncode: raise RuntimeError('NEW native route fixture compilation failed')
            evidence.save(folder/'native-executable.json', dict(binary=str(cls.native), binary_sha256=profile.sha(cls.native),
                guarded_main_sha256=profile.sha(folder/'guarded-main-fixture.h'),
                source_sha256={n: profile.sha(HERE/n) for n in ('builtin_init_route.c', 'builtin_init_route_fixture.c', 'builtin_init_route.py')}))

    def folder(self):
        p = self.root/self._testMethodName
        p.mkdir()
        return p

    def native_case(self, name):
        out = self.folder()
        result = subprocess.run([str(self.native), name], capture_output=True, timeout=5)
        evidence.raw_file(out/'stdout.bin', result.stdout)
        evidence.raw_file(out/'stderr.bin', result.stderr)
        evidence.save(out/'return.json', dict(argv=[str(self.native), name], returncode=result.returncode))
        self.assertEqual(result.returncode, 0)

    def test_native_default_off(self): self.native_case('default-off')
    def test_native_success(self): self.native_case('success')
    def test_native_missing(self): self.native_case('missing')
    def test_native_exec_failure(self): self.native_case('exec-failure')

    def test_cpio_closed_members_modes(self):
        data, pos, rows = route.cpio(fake_elf()), 0, []
        while True:
            self.assertEqual(data[pos:pos+6], b'070701')
            values = [int(data[pos+6+i*8:pos+14+i*8], 16) for i in range(13)]
            name = data[pos+110:pos+109+values[11]].decode()
            pos = (pos+110+values[11]+3)//4*4
            payload = data[pos:pos+values[6]]
            pos = (pos+values[6]+3)//4*4
            rows.append((name, values[1], values[9], values[10], payload))
            if name == 'TRAILER!!!': break
        self.assertEqual([r[0] for r in rows], ['dev', 'dev/console', 'dev/kmsg', 'init', 'TRAILER!!!'])
        self.assertEqual(rows[1][1:4], (0o020600, 5, 1))
        self.assertEqual(rows[2][1:4], (0o020600, 1, 11))
        self.assertEqual(rows[3][1], 0o100755)
        self.assertEqual(rows[3][4], fake_elf())

    def test_elf_reject_interpreter(self):
        data = bytearray(fake_elf()); struct.pack_into('<I', data, 64, 3)
        with self.assertRaises(ValueError): route.elf_manifest(bytes(data))

    def test_elf_reject_writable_code(self):
        data = bytearray(fake_elf()); struct.pack_into('<I', data, 68, 7)
        with self.assertRaises(ValueError): route.elf_manifest(bytes(data))

    def binding_fixture(self):
        root = self.folder(); elf = fake_elf(); archive = route.cpio(elf)
        (root/'overlay/init').mkdir(parents=True)
        for name, data in {'minimal-init.elf': elf, 'initramfs.cpio': archive, 'overlay/init/main.c': b'guarded fixture'}.items():
            (root/name).write_bytes(data)
        evidence.save(root/'minimal-init.json', dict(elf=route.elf_manifest(elf), cpio_sha256=route.sha(archive),
            cpio_bytes=len(archive), members=['dev', 'dev/console', 'dev/kmsg', 'init', 'TRAILER!!!']))
        result = dict(builtin_init_route=True, minimal_init_elf_sha256=route.sha(elf),
            initramfs_cpio_sha256=route.sha(archive), builtin_init_manifest_sha256=profile.sha(root/'minimal-init.json'),
            guarded_init_main_sha256=profile.sha(root/'overlay/init/main.c'))
        lines = {'CONFIG_NOTE10_BUILTIN_INIT_ROUTE=y', 'CONFIG_INITRAMFS_FORCE=y',
                 'CONFIG_INITRAMFS_COMPRESSION_NONE=y', 'CONFIG_CMDLINE=""',
                 'CONFIG_INITRAMFS_SOURCE="/fixture/initramfs.cpio"'}
        return root, result, b'Image'+archive, lines

    def test_forced_input_binding(self):
        root, result, image, lines = self.binding_fixture()
        self.assertEqual(evidence.input_binding(root, result, image, lines)['minimal_init_elf_sha256'], result['minimal_init_elf_sha256'])

    def test_reject_missing_force(self):
        root, result, image, lines = self.binding_fixture(); lines.remove('CONFIG_INITRAMFS_FORCE=y')
        with self.assertRaises(ValueError): evidence.input_binding(root, result, image, lines)

    def test_reject_changed_embedded_archive(self):
        root, result, image, lines = self.binding_fixture()
        with self.assertRaises(ValueError): evidence.input_binding(root, result, image[:-1], lines)

    def test_guard_reject_changed_source(self):
        with self.assertRaises(ValueError): route.guard_main(b'changed kernel source')

    def test_decode_complete_startup(self):
        _, observed = evidence.decode(frames(), BANNER, ID, CYCLE)
        self.assertEqual(observed['boot_identity'], BOOT)
        self.assertTrue(observed['minimal_PID1_start_observed'])

    def test_decode_missing_boundary(self):
        with self.assertRaises(ValueError): evidence.decode(frames().split(b'\n', 1)[1], BANNER, ID, CYCLE)

    def test_decode_panic_banner(self):
        data = frames().replace(b'[    0.000000]', b'[   53.972693] [bootchecker] linux_banner:')
        with self.assertRaises(ValueError): evidence.decode(data, BANNER, ID, CYCLE)

    def test_decode_missing_actual_PID1(self):
        data = b'\n'.join(l for l in frames().split(b'\n') if b'N10INIT2 ' not in l)
        with self.assertRaises(ValueError): evidence.decode(data, BANNER, ID, CYCLE)

    def test_decode_mixed_boot_identity(self):
        data = frames().replace(b'N10BOOTLINK2 boot='+BOOT.encode(), b'N10BOOTLINK2 boot='+b'4'*32, 1)
        with self.assertRaises(ValueError): evidence.decode(data, BANNER, ID, CYCLE)

    def test_decode_duplicate_route(self):
        data = frames(); line = next(l for l in data.splitlines(keepends=True) if b'N10ROUTE2' in l)
        with self.assertRaises(ValueError): evidence.decode(data+line, BANNER, ID, CYCLE)

    def test_decode_multiple_current_cycle_boots(self):
        data = frames()+frames().replace(BOOT.encode(), b'4'*32)
        with self.assertRaises(ValueError): evidence.decode(data, BANNER, ID, CYCLE)

    def snapshot(self, values):
        out = self.folder(); adb = FakeTransport(values)
        result = evidence.snapshot(adb, out, dict(kernel_banner=BANNER, build_evidence_id=ID), CYCLE)
        self.assertEqual(len([e for e in adb.events if e[:2] == ('shell', '-T')]), 3)
        self.assertEqual(len(adb.events), len(set(adb.events)))
        return out, adb, result

    def test_snapshot_all_before_evaluation(self):
        out = self.folder(); adb = FakeTransport({('probe', remote): b'N10KAT_READABLE\n' for _, remote in evidence.LOGS})
        original = evidence.decode
        def checked(*args):
            self.assertEqual(len(adb.events), 6)
            return original(*args)
        with patch.object(evidence, 'decode', checked):
            result = evidence.snapshot(adb, out, dict(kernel_banner=BANNER, build_evidence_id=ID), CYCLE)
        self.assertTrue(result['diagnostic_passed'])

    def test_snapshot_cat_failure_no_fallback(self):
        _, _, result = self.snapshot({('probe', evidence.LOGS[0][1]): b'N10KAT_READABLE\n',
            ('cat', evidence.LOGS[0][1]): RuntimeError('cat failed'), ('probe', evidence.LOGS[1][1]): b'N10KAT_READABLE\n'})
        self.assertFalse(result['diagnostic_passed']); self.assertTrue(result['errors'])

    def test_snapshot_probe_failure_no_fallback(self):
        _, _, result = self.snapshot({('probe', evidence.LOGS[0][1]): RuntimeError('transport'),
            ('probe', evidence.LOGS[1][1]): b'N10KAT_READABLE\n'})
        self.assertFalse(result['diagnostic_passed']); self.assertTrue(result['errors'])

    def test_snapshot_current_bad_file_no_fallback(self):
        _, _, result = self.snapshot({('probe', evidence.LOGS[0][1]): b'N10KAT_READABLE\n',
            ('cat', evidence.LOGS[0][1]): frames().split(b'\n', 1)[1],
            ('probe', evidence.LOGS[1][1]): b'N10KAT_READABLE\n'})
        self.assertFalse(result['diagnostic_passed'])

    def test_probe_native_forms_receipt(self):
        out = self.folder()
        for index, word in enumerate((b'READABLE', b'ABSENT')):
            raw = b'N10KAT_'+word+b'\r\n'; remote = evidence.LOGS[index][1]
            adb = FakeTransport({('probe', remote): raw})
            self.assertEqual(evidence.probe(adb, remote, out, index), b'N10KAT_'+word+b'\n')
            row = json.loads((out/f'probe-{index}.json').read_text(encoding='utf8'))
            self.assertEqual((out/row['file']).read_bytes(), raw)
            self.assertEqual(row['sha256'], route.sha(raw)); self.assertEqual(row['int5'][4], 1)
            self.assertTrue(all(type(x) is int for x in row['int5']))

    def test_probe_LF_unchanged(self):
        out = self.folder(); remote = evidence.LOGS[0][1]; raw = b'N10KAT_READABLE\n'
        adb = FakeTransport({('probe', remote): raw})
        self.assertEqual(evidence.probe(adb, remote, out, 0), raw)
        self.assertFalse(json.loads((out/'probe-0.json').read_text(encoding='utf8'))['translated'])

    def test_probe_wrong_path_no_call(self):
        out = self.folder(); adb = FakeTransport()
        with self.assertRaises(ValueError): evidence.probe(adb, '/tmp/unapproved', out, 0)
        self.assertEqual(adb.events, [])

    def test_probe_malformed_not_repaired(self):
        out = self.folder(); remote = evidence.LOGS[0][1]
        adb = FakeTransport({('probe', remote): b' N10KAT_READABLE\r\n'})
        with self.assertRaises(ValueError): evidence.probe(adb, remote, out, 0)
        self.assertFalse(json.loads((out/'probe-0.json').read_text(encoding='utf8'))['translated'])

    def test_raw_log_bytes_unchanged(self):
        raw = frames()+b'raw trailing\r\n\x00'
        out, _, result = self.snapshot({('probe', evidence.LOGS[0][1]): b'N10KAT_READABLE\r\n', ('cat', evidence.LOGS[0][1]): raw})
        self.assertEqual((out/'last_kmsg.txt').read_bytes(), raw)
        self.assertEqual(result['logs_sha256']['last_kmsg.txt'], route.sha(raw))

    def journal_fixture(self, reboot_error=False):
        out = self.folder()/'journal'; plan = dict(stages=[dict(index=1, cycle=CYCLE, packages='fixture-packages',
            kernel_build='fixture-stage-variant', image_sha256='a'*64)], image_sha256='b'*64,
            backup_manifest_sha256='c'*64, backup='fixture-backup', identity=ID, return_timeout_seconds=240)
        calls = []
        class Fake:
            serial = 'FIXTURE'
            def text(self, *args): return '/sbin/twrp'
            def call(self, *args, **kwargs):
                row = json.loads((out/'journal.json').read_text(encoding='utf8'))
                calls.append(args)
                assert row['pre_reboot_boot_id'] == 'before' and row['stage_kernel_build'] == 'fixture-stage-variant'
                assert row['partition_writes_attempted'] is True
                if args[2] == 'reboot':
                    assert row['reboots_attempted'] is True
                    if reboot_error: raise RuntimeError('fake transport close')
                    return b'native reboot reply\r\n'
                return b'fake installer return'
        with ExitStack() as stack:
            for name, value in {'validate_plan': plan, 'preflight': {'twrp_version': 'fake'},
                'verify_packages': [dict(mode='diagnostic', file='fixture.zip', payload_sha256='d'*64)],
                'stage': {'ram_directory': '/tmp/fixture'}, 'verify_partitions': None, 'boot_id': 'before'}.items():
                stack.enter_context(patch.object(cycle_host, name, return_value=value))
            stack.enter_context(patch.object(profile, 'selected', return_value=True))
            stack.enter_context(patch.object(profile, 'precheck', return_value={'ready_for_manual_access_test': True}))
            stack.enter_context(patch.object(cycle_host, 'wait_recovery', side_effect=TimeoutError('fake stop')))
            with self.assertRaises(TimeoutError): cycle_host.run_plan('fixture', 'e'*64, out, execute=True, adb=Fake())
        return out, calls, json.loads((out/'journal.json').read_text(encoding='utf8'))

    def test_journal_preID_order_reboot_return(self):
        out, calls, row = self.journal_fixture()
        self.assertEqual(len(calls), 2); self.assertEqual(row['status'], 'stopped')
        self.assertEqual((out/'reboot-return.bin').read_bytes(), b'native reboot reply\r\n')
        self.assertIsNone(row['reboot_observation']['process_exit_code'])

    def test_journal_reboot_error_no_resend(self):
        _, calls, row = self.journal_fixture(True)
        self.assertEqual(len(calls), 2)
        self.assertEqual(row['reboot_observation']['error_type'], 'RuntimeError')
        self.assertFalse(row['single_cycle_verified'])

    def test_wait_records_rejections_and_IDs(self):
        time = [0.0]; rows = []
        class Fake:
            def call(self, *args, **kwargs): return b'fake'
        def sleep(n): time[0] += n
        with patch.object(cycle_host, 'preflight', side_effect=[ValueError('same-device check'), {'twrp_version': 'fake'}, {'twrp_version': 'fake'}]), patch.object(cycle_host, 'boot_id', side_effect=['before', 'after']):
            answer = cycle_host.wait_recovery(Fake(), 'before', 8, monotonic=lambda: time[0], sleep=sleep, observe=rows.append)
        self.assertEqual(answer, 'after'); self.assertEqual(rows[0]['error_type'], 'ValueError')
        self.assertFalse(rows[1]['changed']); self.assertTrue(rows[2]['changed'])

    def test_execute_false_has_no_journal(self):
        out = self.folder()/'forbidden-journal'
        with self.assertRaises(ValueError): cycle_host.run_plan('no-plan', '0'*64, out, execute=False)
        self.assertFalse(out.exists())

    def test_historical_host_pins_are_distinct(self):
        old = profile.host_binding(profile.V71_HOST_HEAD)
        current = profile.host_binding('f'*40)
        self.assertEqual(old['host_profile_source_sha256'], profile.V71_HOST_PINS)
        self.assertNotEqual(old['host_profile_source_sha256'], current['host_profile_source_sha256'])

    def test_new_fields_cannot_be_omitted(self):
        row = dict(device_profile=profile.BUILTIN_PROFILE)
        row.update({k: 'f'*64 for k in profile.FIELDS if k != 'device_profile'})
        with self.assertRaises(KeyError): profile.fields(row)

    def package_row(self):
        row = dict(device_profile=profile.BUILTIN_PROFILE, build_evidence_id=ID, kernel_banner=BANNER,
            source_head='d'*40, auto_return_diagnostic=True, auto_cycle_token=CYCLE,
            **profile.host_binding('e'*40))
        row.update({k: 'f'*64 for k in ('profile_sha256', 'accepted_result_sha256',
            'image_root_receipt_sha256', 'root_reader_result_sha256', *evidence.EXTRA_FIELDS)})
        return row

    def test_new_package_scope_carries_all_pins(self):
        row = self.package_row(); profile.package_scope(row)
        del row['guarded_init_main_sha256']
        with self.assertRaises(ValueError): profile.package_scope(row)

    def test_new_package_scope_rejects_historical_host_head(self):
        row = self.package_row(); row.update(profile.host_binding(profile.V71_HOST_HEAD))
        with self.assertRaises(ValueError): profile.package_scope(row)

    def test_current_BOOT_binding_accepts_private_pin(self):
        pair = dict(device_profile=profile.PROFILE, source_head='9bfe108e7fd7a063bacce9418be46d269cb872d9',
                    host_profile_source_head=profile.V71_HOST_HEAD)
        evidence.current_boot_binding({'current_boot_payload_sha256': 'a'*64}, pair, {'payload_sha256': 'a'*64})

    def test_current_BOOT_binding_rejects_obsolete_or_wrong_pin(self):
        pair = dict(device_profile=None, source_head='9bfe108e7fd7a063bacce9418be46d269cb872d9',
                    host_profile_source_head=profile.V71_HOST_HEAD)
        with self.assertRaises(ValueError):
            evidence.current_boot_binding({'current_boot_payload_sha256': 'a'*64}, pair, {'payload_sha256': 'a'*64})
        pair['device_profile'] = profile.PROFILE
        with self.assertRaises(ValueError):
            evidence.current_boot_binding({'current_boot_payload_sha256': 'b'*64}, pair, {'payload_sha256': 'a'*64})


class RecordedResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs); self.passed_ids, self.failed_ids, self.framework_errors = [], [], []
    def addSuccess(self, test):
        self.passed_ids.append('BuiltinRouteTests.'+test._testMethodName); super().addSuccess(test)
    def addFailure(self, test, err):
        self.failed_ids.append('BuiltinRouteTests.'+test._testMethodName); super().addFailure(test, err)
    def addError(self, test, err):
        if isinstance(test, BuiltinRouteTests): self.failed_ids.append('BuiltinRouteTests.'+test._testMethodName)
        else: self.framework_errors.append(test.id())
        super().addError(test, err)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--case', action='append', choices=CASE_IDS)
    args = parser.parse_args()
    OUTPUT = args.output.resolve(); SELECTED = tuple(args.case or CASE_IDS)
    private = (HERE.parent/'private').resolve()
    if OUTPUT == private or not OUTPUT.is_relative_to(private) or OUTPUT.exists() or len(set(SELECTED)) != len(SELECTED):
        raise ValueError('fresh private output and unique explicit NEW allowlisted case IDs required')
    suite = unittest.TestSuite(BuiltinRouteTests(name.split('.')[1]) for name in SELECTED)
    result = unittest.TextTestRunner(verbosity=2, resultclass=RecordedResult).run(suite)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    stable = FIRST_USE_PINS == {n: profile.sha(HERE/n) for n in FIRST_USE_INPUTS}
    loaded = {Path(m.__file__).name: profile.sha(m.__file__) for m in tuple(sys.modules.values())
              if getattr(m, '__file__', None) and Path(m.__file__).suffix == '.py' and
              Path(m.__file__).resolve().is_relative_to(HERE)}
    evidence.save(OUTPUT/'result.json', dict(schema=1, selected_ids=SELECTED, passed_ids=result.passed_ids,
        failed_ids=result.failed_ids, tests_run=result.testsRun, suite_success=result.wasSuccessful(),
        framework_errors=result.framework_errors,
        failures=len(result.failures), errors=len(result.errors), device_operations=[], old_suites_invoked=0,
        direct_source_sha256_before_import=FIRST_USE_PINS, direct_source_stable=stable,
        loaded_local_module_source_sha256_after_suite=loaded,
        loaded_module_hashes_are_definition_provenance_not_old_evaluation_execution=True))
    sys.exit(0 if result.wasSuccessful() and stable else 1)
