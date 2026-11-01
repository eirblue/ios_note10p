"""NEW pure-Python profile connections only; fake BOOT/ADB, no compiler/device."""
import argparse
from contextlib import ExitStack
import hashlib
import json
from pathlib import Path
import struct
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import zipfile

import sha256_kat_device_profile as profile
import materialize_auto_cycle as slot
import prepare_linux_boot as packer
import build_boot_test_packages as packages
import stage_phase2 as staging
import auto_cycle as actuator
from decode_reservation import checksum

OUTPUT = None
IDENTITY = '123456789abcdef0123456789abcdef0'
SOURCE = '1'*40
HOST_SOURCE = '2'*40
BANNER = 'Linux version 4.14.113-v71-sha256-recovery fixture-only'
ANSWER = 'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad'
CASE_IDS = (
    'KatProfileTests.test_v71p_01_truthful_template_and_only_cycle_slot_patch',
    'KatProfileTests.test_v71p_02_reject_changed_pins_source_config_and_fake_scope',
    'KatProfileTests.test_v71p_03_closed_updater_keeps_five_partition_writer',
    'KatProfileTests.test_v71p_04_pair_plan_current_boot_and_rollback_binding',
    'KatProfileTests.test_v71p_05_latest_boot_and_cycle_clip_before_decoders',
    'KatProfileTests.test_v71p_06_new_precheck_battery_nodes_and_ram_rejection',
    'KatProfileTests.test_v71p_07_common_journal_attempt_order_and_no_resend',
    'KatProfileTests.test_v71p_08_execute_false_never_constructs_adb_or_journal',
    'KatProfileTests.test_v71p_09_root_receipt_tuple_and_closed_schema_rejection',
    'KatProfileTests.test_v71p_10_closed_profile_uses_common_packer_only_after_binding',
    'KatProfileTests.test_v71p_11_resigned_writer_or_ramdisk_cannot_bypass_plan',
    'KatProfileTests.test_v71p_12_readable_cat_failure_cannot_fall_back_to_passing_log',
    'KatProfileTests.test_v71p_13_probe_transport_failure_cannot_fall_back_to_passing_log',
)


class RecordedResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.passed_ids, self.failed_ids, self.executed_ids, self.framework_errors = [], [], [], []

    @staticmethod
    def case_id(test):
        return '.'.join(test.id().split('.')[-2:])

    def startTest(self, test):
        self.executed_ids.append(self.case_id(test))
        super().startTest(test)

    def addSuccess(self, test):
        self.passed_ids.append(self.case_id(test))
        super().addSuccess(test)

    def mark_failed(self, test):
        identity = self.case_id(test)
        target = self.failed_ids if identity in CASE_IDS else self.framework_errors
        if identity not in target: target.append(identity)

    def addFailure(self, test, err):
        self.mark_failed(test)
        super().addFailure(test, err)

    def addError(self, test, err):
        self.mark_failed(test)
        super().addError(test, err)

    def addSubTest(self, test, subtest, err):
        if err is not None: self.mark_failed(test)
        super().addSubTest(test, subtest, err)


def digest(data):
    return hashlib.sha256(data).hexdigest()


RAMDISK = b'fixture-external-TWRP-ramdisk'
TOOL = b'# pure fixture; never execute\n'


def fake_kernel(label):
    header = bytearray(64)
    header[56:60] = b'ARM\x64'
    struct.pack_into('<QQ', header, 8, 0x80000, 4096)
    return bytes(header)+label


def fake_boot(kernel, ramdisk=RAMDISK):
    header = bytearray(2048)
    header[:8] = b'ANDROID!'
    struct.pack_into('<10I', header, 8, len(kernel), 0x10008000, len(ramdisk), 0x12000000, 0, 0, 0x10000100, 2048, 1, 0)
    struct.pack_into('<IQI', header, 1632, 0, 0, 1648)
    return bytes(header)+kernel+bytes((-len(kernel)) % 2048)+ramdisk+bytes((-len(ramdisk)) % 2048)+b'SEANDROIDENFORCE'


OFFICIAL = fake_boot(fake_kernel(b'fixture-TWRP-kernel'))


def raw_build(root):
    root.mkdir(parents=True)
    header = bytearray(64)
    header[56:60] = b'ARM\x64'
    struct.pack_into('<QQ', header, 8, 0x80000, 4096)
    image = bytes(header)+BANNER.encode()+b'\0'+IDENTITY.encode()+b'\0'+profile.SLOT+b'\0N10RET1 N10SHA1 N10SHACTL1'
    config = '\n'.join(('CONFIG_'+key+'=y' for key in (
        'NOTE10_SHA256_KAT_RECOVERY', 'CRYPTO', 'CRYPTO_HASH', 'CRYPTO_SHA256',
        'EXYNOS_REBOOT', 'SEC_REBOOT', 'BLK_DEV_INITRD', 'RD_LZMA', 'ARM64_4K_PAGES')))
    config += '\nCONFIG_INITRAMFS_SOURCE=""\nCONFIG_CMDLINE=""\n'
    files = {'Image': image, 'prerequisites/objects/.config': config.encode(),
             'source/note10/device_test/fixture-source.py': b'# fixture input only\n',
             'source/note10/device_test/build_sha256_kat_recovery.py':
                 (Path(__file__).parent/'build_sha256_kat_recovery.py').read_bytes()}
    for name, data in files.items():
        target = root/name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    result = dict(version='v71', passed=True, Image_built=True, BOOT_built=False,
                  cycle_slot_patched=False, kernel_or_provider_executed=False,
                  kernel_commit='55f042627bb7030c93550faafa117674d32b21d1',
                  make_target='Image', integration_object='drivers/misc/note10_sha256_kat.o',
                  ci_context={'GITHUB_SHA': SOURCE, 'GITHUB_RUN_ID': '100', 'GITHUB_RUN_ATTEMPT': '1'}, image_sha256=digest(image), image_bytes=len(image),
                  build_evidence_id=IDENTITY, files_sha256={n: digest(b) for n, b in files.items()},
                  source_sha256={name[len('source/'):]: digest(data) for name, data in files.items() if name.startswith('source/')})
    profile.save(root/'result.json', result)
    return profile.sha(root/'result.json')


def bind_template(raw, output, pin, source=SOURCE):
    result = profile.read(raw/'result.json')
    receipt = dict(schema=1, kind=profile.PROFILE+'-accepted-image', accepted=True,
                   root_reader_result_sha256='3'*64, producer_source_head=SOURCE,
                   ci_result_sha256=profile.sha(raw/'result.json'), image_sha256=result['image_sha256'],
                   image_bytes=result['image_bytes'], effective_config_sha256=profile.sha(raw/'prerequisites/objects/.config'),
                   build_evidence_id=IDENTITY, kernel_banner=BANNER, run_id=100, attempt=1,
                   workflow_id=1, job_id=2, artifact_id=3, artifact_zip_sha256='4'*64, artifact_zip_bytes=1)
    path = raw.parent/(raw.name+'-fixture-root-receipt.json')
    profile.save(path, receipt)
    return profile.prepare_template(raw, output, pin, source, root_receipt=path,
                                    root_receipt_sha256=profile.sha(path), host_source_head=HOST_SOURCE)


def backup(root):
    root.mkdir()
    original = fake_boot(fake_kernel(b'fixture-stock-kernel'))
    parts = {'boot': original+bytes(16384-len(original)), 'recovery': OFFICIAL+bytes(2048),
             'dtb': b'DTB'*100, 'dtbo': b'DTBO'*100, 'vbmeta': b'VBMETA'*100}
    rows = []
    for index, (name, data) in enumerate(parts.items(), 1):
        (root/(name+'.img')).write_bytes(data)
        rows.append(dict(partition=name, file=name+'.img', size=len(data), sha256=digest(data),
                         block_node='/dev/block/sda'+str(index), remote_hash_before_and_after_match=True))
    profile.save(root/'backup-manifest.json', dict(complete=True, partition_writes=False,
                 bootloader='N976NTEST', partitions=rows))
    return parts, rows


def fake_prototype(root, variant, token, base):
    parts = {name: (base/(name+'.img')).read_bytes() for name in ('boot', 'recovery')}
    image = (variant/'Image').read_bytes()
    raw = fake_boot(image)
    path = root/'boot.img'
    path.write_bytes(raw)
    bound = profile.variant(variant, token)
    meta = dict(prototype_created=True, kind='temporary Linux diagnostic boot; not XNU/iOS',
                size=len(raw), sha256=digest(raw), kernel_build_sha256=digest(image),
                backup_manifest_sha256=profile.sha(base/'backup-manifest.json'),
                original_boot_sha256=digest(parts['boot']), existing_recovery_partition_sha256=digest(parts['recovery']),
                auto_return_diagnostic=True, auto_cycle_token=token, **profile.fields(bound))
    profile.save(path.with_suffix('.json'), meta)
    return path


def environment(root):
    root.mkdir()
    artifact = root/'artifact'
    pin = raw_build(artifact)
    template = root/'template'
    bind_template(artifact, template, pin)
    base = root/'backup'
    parts, rows = backup(base)
    reference, tool = root/'reference.img', root/'fake-mkbootimg.py'
    reference.write_bytes(OFFICIAL)
    tool.write_bytes(TOOL)
    previous = root/'previous'
    previous.mkdir()
    slot.materialize(template, previous/'variant', 'a'*32)
    proto = fake_prototype(previous, previous/'variant', 'a'*32, base)
    packages.build(base, proto, previous/'packages')
    stage = root/'cycle-01'
    stage.mkdir()
    slot.materialize(template, stage/'kernel-build', 'b'*32)
    proto = fake_prototype(stage, stage/'kernel-build', 'b'*32, base)
    pair = packages.build(base, proto, stage/'packages', previous/'packages')
    plan = dict(schema=1, kind='note10-bounded-auto-cycle', device_profile=profile.PROFILE,
                kernel_build=str(template), backup=str(base),
                backup_manifest_sha256=profile.sha(base/'backup-manifest.json'),
                build_result_sha256=profile.sha(template/'build-result.json'),
                image_sha256=profile.sha(template/'Image'), identity=IDENTITY,
                current_packages=str(previous/'packages'),
                current_package_result_sha256=profile.sha(previous/'packages/package-result.json'),
                reference_twrp=str(reference), mkbootimg=str(tool),
                minimum_battery=10, return_timeout_seconds=240,
                stages=[dict(index=1, cycle='b'*32, kernel_build=str(stage/'kernel-build'),
                             image_sha256=profile.sha(stage/'kernel-build/Image'),
                             build_result_sha256=profile.sha(stage/'kernel-build/build-result.json'),
                             packages=str(stage/'packages'), package_result_sha256=profile.sha(stage/'packages/package-result.json'))])
    profile.save(root/'plan.json', plan)
    return SimpleNamespace(root=root, template=template, backup=base, parts=parts, rows=rows,
                           stage=stage, pair=pair, plan=plan, pin=profile.sha(root/'plan.json'))


def frames(token='b'*32, kat_before_arm=False, banner=BANNER, passed=True):
    def line(tag, body):
        return f'{tag} {body} checksum={checksum(body.encode()):08x}\n'
    kat = ''.join(line('N10SHA1', f'id={IDENTITY} copy={i} phase=late-init status={0 if passed else -5} driver_match=1 computed={1 if passed else 0} digest={ANSWER if passed else "0"*64}') for i in (0, 1))
    arm = ''.join(line('N10RET1', f'id={IDENTITY} cycle={token} phase=0 seq={i} delay_ms=90000 status=0') for i in (0, 1))
    request = ''.join(line('N10RET1', f'id={IDENTITY} cycle={token} phase=1 seq={i} delay_ms=90000 status=0') for i in (0, 1))
    return ('[    0.000000] '+banner+'\n'+(kat+arm if kat_before_arm else arm+kat)+request).encode()


class FakeAdb:
    executable = 'FAKE-ADB-NEVER-EXECUTE'
    serial = 'FIXTURE-ONLY'

    def __init__(self, env, journal=None, battery=10, fail=None):
        self.env, self.journal, self.battery, self.fail = env, journal, battery, fail
        self.events, self.boot_number = [], 1
        self.partition_hash_reads = 0
        self.probe_calls, self.cat_calls = [], []
        self.boot_hash = env.pair['expected_current_boot_sha256']
        self.log = frames(passed=fail != 'KAT-failure')

    def text(self, *args, **kwargs):
        if args == ('devices',): return 'List of devices attached\nFIXTURE-ONLY recovery\n'
        if args[:2] == ('shell', 'getprop'):
            return {'ro.product.model': 'SM-N976N', 'ro.product.device': 'd2x',
                    'ro.twrp.version': 'fixture', 'ro.bootloader': 'N976NTEST'}[args[2]]
        if args == ('shell', 'id', '-u'): return '0'
        if args == ('shell', 'uname', '-m'): return 'aarch64'
        if args == ('shell', 'cat', '/sys/class/power_supply/battery/capacity'): return str(self.battery)
        if args == ('shell', 'cat', '/proc/sys/kernel/random/boot_id'): return '00000000-0000-0000-0000-'+str(self.boot_number).zfill(12)
        if args == ('shell', 'command', '-v', 'twrp'): return '/sbin/twrp'
        if args[:3] == ('shell', 'readlink', '-f'):
            name = args[3].rsplit('/', 1)[1]
            return next(r['block_node'] for r in self.env.rows if r['partition'] == name)
        if args[:3] == ('shell', 'blockdev', '--getsize64'):
            size = next(r['size'] for r in self.env.rows if r['block_node'] == args[3])
            return str(size+1 if self.fail == 'node-size' else size)
        if args[:2] == ('shell', 'sha256sum'):
            path = args[2]
            if path.startswith('/tmp/'):
                row = next(r for r in self.env.pair['packages'] if r['file'] == path.rsplit('/', 1)[1])
                return ('0'*64 if self.fail == 'RAM-hash' else row['sha256'])+' file'
            row = next(r for r in self.env.rows if r['block_node'] == path)
            self.partition_hash_reads += 1
            return (self.boot_hash if row['partition'] == 'boot' else row['sha256'])+' file'
        raise AssertionError(args)

    def call(self, *args, **kwargs):
        for remote in ('/proc/last_kmsg', '/sys/fs/pstore/console-ramoops-0', '/sys/fs/pstore/dmesg-ramoops-0'):
            if args == ('shell', '-T', profile.log_probe_command(remote)):
                self.probe_calls.append(remote)
                if remote == '/proc/last_kmsg' and self.fail == 'probe-error-with-later-pass':
                    raise RuntimeError('fixture probe transport failure')
                readable = remote == '/proc/last_kmsg' or (
                    remote == '/sys/fs/pstore/console-ramoops-0' and self.fail in
                    ('probe-error-with-later-pass', 'cat-error-with-later-pass'))
                return b'N10KAT_READABLE\n' if readable else b'N10KAT_ABSENT\n'
        if args[:2] == ('exec-out', 'cat'):
            self.cat_calls.append(args[2])
            if args[2] == '/proc/last_kmsg' and self.fail == 'cat-error-with-later-pass':
                raise RuntimeError('fixture cat failure after readable probe')
            return self.log
        if args[:3] == ('shell', 'twrp', 'install'):
            self.events.append('install')
            record = profile.read(self.journal)
            assert record['partition_writes_attempted'] is True and record['reboots_attempted'] is False
            if self.fail == 'install': raise RuntimeError('fixture installer failure')
            self.boot_hash = next(r['payload_sha256'] for r in self.env.pair['packages'] if r['mode'] == 'diagnostic')
            return b''
        if args == ('shell', 'twrp', 'reboot'):
            self.events.append('reboot')
            assert profile.read(self.journal)['reboots_attempted'] is True
            self.boot_number += 1
            if self.fail == 'reboot-disconnect': raise RuntimeError('fixture transport closed')
            return b''
        raise AssertionError(args)


class KatProfileTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if OUTPUT is None: raise RuntimeError('explicit fresh --output required')
        cls.root = OUTPUT
        cls.root.mkdir(parents=True)

    def setUp(self):
        # Synthetic file pins only; original source bytes/constants are restored.
        self.twrp_patch = patch.object(packer, 'TWRP_SHA256', digest(OFFICIAL))
        self.tool_patch = patch.object(packer, 'MKBOOTIMG_SHA256', digest(TOOL))
        self.twrp_patch.start()
        self.tool_patch.start()
        self.addCleanup(self.tool_patch.stop)
        self.addCleanup(self.twrp_patch.stop)

    def test_v71p_01_truthful_template_and_only_cycle_slot_patch(self):
        raw = self.root/'template-case'
        pin = raw_build(raw)
        template = self.root/'bound-template'
        bind_template(raw, template, pin)
        report = profile.validate_template(template)
        self.assertFalse(any(report.get(k) for k in profile.LEGACY))
        variant = self.root/'bound-variant'
        slot.materialize(template, variant, 'c'*32)
        self.assertEqual((variant/'Image').read_bytes(), (template/'Image').read_bytes().replace(profile.SLOT, b'c'*32, 1))
        (variant/'Image').write_bytes((variant/'Image').read_bytes()+b'forged')
        with self.assertRaises(ValueError): profile.variant(variant, 'c'*32)

    def test_v71p_02_reject_changed_pins_source_config_and_fake_scope(self):
        for name in ('result-pin', 'source-head', 'source-bytes', 'config', 'Image'):
            with self.subTest(case=name):
                raw = self.root/('reject-'+name)
                pin = raw_build(raw)
                source = SOURCE
                if name == 'result-pin': pin = '0'*64
                elif name == 'source-head': source = '2'*40
                else:
                    path = raw/({'source-bytes': 'source/note10/device_test/fixture-source.py',
                                 'config': 'prerequisites/objects/.config', 'Image': 'Image'}[name])
                    path.write_bytes(path.read_bytes()+b'changed')
                output = raw.with_name(raw.name+'-output')
                with self.assertRaises(ValueError): bind_template(raw, output, pin, source)
                self.assertFalse(output.exists())
        with self.assertRaises(ValueError): profile.selected({'device_profile': 'unreviewed'})
        with self.assertRaises(ValueError): profile.no_legacy({'builtin_cpu_diagnostic': True})

    def test_v71p_03_closed_updater_keeps_five_partition_writer(self):
        _, rows = backup(self.root/'writer-backup')
        kwargs = dict(mode='diagnostic', bootloader='N976NTEST', partitions=rows,
                      payload_sha='1'*64, current_boot_sha='2'*64, auto_return=True)
        with self.assertRaises(ValueError): packages.updater(**kwargs)
        script = packages.updater(**kwargs, device_profile=profile.PROFILE).decode()
        self.assertEqual(script.count('dd if='), 1)
        self.assertIn('of="/dev/block/sda1"', script)
        for row in rows: self.assertIn('blockdev --getsize64 '+row['block_node'], script)
        self.assertNotIn('twrp reboot', script)
        with self.assertRaises(ValueError): packages.updater(**kwargs, device_profile='other')

    def test_v71p_04_pair_plan_current_boot_and_rollback_binding(self):
        env = environment(self.root/'pair-plan')
        self.assertEqual(profile.validate_plan(env.root/'plan.json', env.pin)['identity'], IDENTITY)
        records = staging.verify_packages(env.stage/'packages')
        self.assertEqual(len(records), 2)
        plan = profile.read(env.root/'plan.json')
        plan['stages'][0]['cycle'] = 'f'*32
        profile.save(env.root/'forged-plan.json', plan)
        with self.assertRaises(ValueError): profile.validate_plan(env.root/'forged-plan.json', profile.sha(env.root/'forged-plan.json'))

    def test_v71p_05_latest_boot_and_cycle_clip_before_decoders(self):
        clipped, result = profile.decode_selected(frames(), BANNER, IDENTITY, 'b'*32)
        self.assertTrue(result['kat']['passed'])
        self.assertTrue(clipped.startswith(b'N10RET1'))
        bad = [frames(kat_before_arm=True), frames(token='a'*32),
               frames()+b'[    0.000000] Linux version different\n', frames(passed=False),
               frames().replace(b'[    0.000000]', b'[    1.000000]', 1)]
        for index, raw in enumerate(bad):
            with self.subTest(case=index), self.assertRaises(ValueError):
                profile.decode_selected(raw, BANNER, IDENTITY, 'b'*32)

    def test_v71p_06_new_precheck_battery_nodes_and_ram_rejection(self):
        env = environment(self.root/'precheck')
        staged = dict(native_archive_read_verified=True,
                      packages=[r['file'] for r in env.pair['packages']], ram_directory='/tmp/note10-phase2-12345678')
        for failure in ('battery', 'node-size', 'RAM-hash'):
            adb = FakeAdb(env, battery=9 if failure == 'battery' else 10, fail=failure)
            with self.subTest(case=failure), patch.object(profile.subprocess, 'run', return_value=SimpleNamespace(returncode=0)):
                with self.assertRaises(ValueError): profile.precheck(env.stage/'packages', env.stage/'kernel-build', env.backup, adb, staged)
            self.assertEqual(adb.events, [])
            self.assertFalse(profile.read(env.stage/'packages/PREINSTALL-CHECK.json')['ready_for_manual_access_test'])

    def test_v71p_07_common_journal_attempt_order_and_no_resend(self):
        for failure in (None, 'install', 'reboot-disconnect', 'battery', 'KAT-failure'):
            with self.subTest(case=failure):
                env = environment(self.root/('actuator-'+str(failure)))
                out = env.root/'journal'
                adb = FakeAdb(env, out/'journal.json', battery=9 if failure == 'battery' else 10, fail=failure)
                staged = dict(native_archive_read_verified=True, packages=[r['file'] for r in env.pair['packages']],
                              ram_directory='/tmp/note10-phase2-12345678')
                original_collect = profile.collect
                # Only scoped test fakes; production actuator functions are never replaced.
                with ExitStack() as stack:
                    stack.enter_context(patch.object(actuator, 'stage', return_value=staged))
                    stack.enter_context(patch.object(profile.subprocess, 'run', return_value=SimpleNamespace(returncode=0)))
                    stack.enter_context(patch.object(profile, 'collect', side_effect=lambda p, k, a: original_collect(p, k, a, env.root/'captures')))
                    if failure in ('install', 'battery', 'KAT-failure'):
                        with self.assertRaises((ValueError, RuntimeError)):
                            actuator.run_plan(env.root/'plan.json', env.pin, out, execute=True, limit=1, adb=adb)
                    else:
                        actuator.run_plan(env.root/'plan.json', env.pin, out, execute=True, limit=1, adb=adb)
                record = profile.read(out/'journal.json')
                self.assertEqual(adb.events, [] if failure == 'battery' else ['install'] if failure == 'install' else ['install', 'reboot'])
                self.assertEqual(record['status'], 'stopped' if failure in ('install', 'battery', 'KAT-failure') else 'complete')
                if failure == 'KAT-failure':
                    self.assertGreaterEqual(adb.partition_hash_reads, 15)
                    self.assertFalse(record['completed'][0]['passed'])

    def test_v71p_08_execute_false_never_constructs_adb_or_journal(self):
        out = self.root/'must-not-exist'
        with self.assertRaises(ValueError): actuator.run_plan(self.root/'absent-plan', '0'*64, out, execute=False)
        self.assertFalse(out.exists())

    def test_v71p_09_root_receipt_tuple_and_closed_schema_rejection(self):
        raw = self.root/'receipt-artifact'
        pin = raw_build(raw)
        template = self.root/'receipt-template'
        bind_template(raw, template, pin)
        measured = profile.raw_binding(raw, pin, SOURCE)
        original = profile.read(template/'image-root-receipt.json')
        for key, value in (('accepted', False), ('image_sha256', '0'*64), ('run_id', 101), ('extra', True)):
            with self.subTest(key=key):
                row = dict(original)
                row[key] = value
                path = self.root/('receipt-forged-'+key+'.json')
                profile.save(path, row)
                with self.assertRaises(ValueError):
                    profile.root_receipt_binding(raw, path, profile.sha(path), measured)

    def test_v71p_10_closed_profile_uses_common_packer_only_after_binding(self):
        env = environment(self.root/'packer-dispatch')
        tool, reference = env.root/'fake-mkbootimg.py', env.root/'reference.img'
        tool.write_bytes(TOOL)
        reference.write_bytes(OFFICIAL)
        with patch.object(packer, 'MKBOOTIMG_SHA256', profile.sha(tool)), \
             patch.object(packer, 'TWRP_SHA256', profile.sha(reference)), \
             patch.object(packer, 'pack_verified', return_value={'fixture': True}) as common:
            result = packer.prepare(env.backup, env.stage/'kernel-build', reference, tool, env.root/'unused.img', 'b'*32)
            self.assertEqual(result, {'fixture': True})
            self.assertTrue(common.call_args.kwargs['kat_profile'])
            self.assertEqual(common.call_count, 1)
            with self.assertRaises(ValueError):
                packer.prepare(env.backup, env.stage/'kernel-build', reference, tool, env.root/'unwritten.img', 'a'*32)
            self.assertEqual(common.call_count, 1)
            self.assertFalse((env.root/'unwritten.img').exists())

    def test_v71p_11_resigned_writer_or_ramdisk_cannot_bypass_plan(self):
        for attack in ('writer', 'ramdisk'):
            with self.subTest(attack=attack):
                env = environment(self.root/('resigned-'+attack))
                pair = profile.read(env.stage/'packages/package-result.json')
                record = next(r for r in pair['packages'] if r['mode'] == 'diagnostic')
                target = env.stage/'packages'/record['file']
                target.with_suffix('.original.zip').write_bytes(target.read_bytes())
                with zipfile.ZipFile(target) as archive:
                    files = {name: archive.read(name) for name in archive.namelist()}
                meta = json.loads(files['manifest.json'])
                if attack == 'writer':
                    files['META-INF/com/google/android/update-binary'] += b'\necho tampered\n'
                else:
                    data = bytearray(files['boot.img'])
                    header = packer.boot_header(data)
                    data[header['ramdisk_file_offset']] ^= 1
                    files['boot.img'] = bytes(data)
                    meta['payload_sha256'] = digest(files['boot.img'])
                    files['META-INF/com/google/android/update-binary'] = packages.updater(
                        mode='diagnostic', bootloader='N976NTEST', partitions=env.rows,
                        payload_sha=meta['payload_sha256'], current_boot_sha=pair['expected_current_boot_sha256'],
                        auto_return=True, device_profile=profile.PROFILE)
                meta['updater_sha256'] = digest(files['META-INF/com/google/android/update-binary'])
                files['manifest.json'] = json.dumps(meta).encode()
                with zipfile.ZipFile(target, 'w') as archive:
                    for name, data in files.items(): archive.writestr(name, data)
                record.update(meta)
                record['sha256'] = profile.sha(target)
                profile.save(env.stage/'packages/package-result.json', pair)
                plan = profile.read(env.root/'plan.json')
                plan['stages'][0]['package_result_sha256'] = profile.sha(env.stage/'packages/package-result.json')
                profile.save(env.root/'resigned-plan.json', plan)
                with self.assertRaises(ValueError):
                    profile.validate_plan(env.root/'resigned-plan.json', profile.sha(env.root/'resigned-plan.json'))

    def test_v71p_12_readable_cat_failure_cannot_fall_back_to_passing_log(self):
        env = environment(self.root/'readable-cat-failure')
        adb = FakeAdb(env, fail='cat-error-with-later-pass')
        # The later candidate would pass; collection must never reach it after
        # the first source explicitly reported readable and then failed cat.
        self.assertTrue(profile.decode_selected(adb.log, BANNER, IDENTITY, 'b'*32)[1]['kat']['passed'])
        result = profile.collect(env.stage/'packages', env.stage/'kernel-build', adb, env.root/'captures')
        self.assertFalse(result['diagnostic_passed'])
        self.assertEqual(result['log_selections'], {})
        self.assertEqual(adb.probe_calls, ['/proc/last_kmsg'])
        self.assertEqual(adb.cat_calls, ['/proc/last_kmsg'])
        self.assertEqual(adb.events, [])

    def test_v71p_13_probe_transport_failure_cannot_fall_back_to_passing_log(self):
        env = environment(self.root/'probe-transport-failure')
        adb = FakeAdb(env, fail='probe-error-with-later-pass')
        self.assertTrue(profile.decode_selected(adb.log, BANNER, IDENTITY, 'b'*32)[1]['kat']['passed'])
        result = profile.collect(env.stage/'packages', env.stage/'kernel-build', adb, env.root/'captures')
        self.assertFalse(result['diagnostic_passed'])
        self.assertEqual(result['log_selections'], {})
        self.assertEqual(adb.probe_calls, ['/proc/last_kmsg'])
        self.assertEqual(adb.cat_calls, [])
        self.assertEqual(adb.events, [])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--case', action='append', choices=CASE_IDS,
                        help='Explicit unconsumed/newly affected method ID; default is the complete new batch')
    args = parser.parse_args()
    OUTPUT = profile.private(args.output)
    profile.require(not OUTPUT.exists(), 'fresh private host-profile test output required')
    selected = args.case or list(CASE_IDS)
    profile.require(len(selected) == len(set(selected)), 'duplicate case selection would replay a case')
    suite = unittest.TestSuite(KatProfileTests(identity.split('.', 1)[1]) for identity in selected)
    result = unittest.TextTestRunner(verbosity=2, resultclass=RecordedResult).run(suite)
    if OUTPUT.is_dir():
        files = {p.relative_to(OUTPUT).as_posix(): profile.sha(p) for p in OUTPUT.rglob('*') if p.is_file()}
        profile.save(OUTPUT/'HOST-PROFILE-TEST-RESULT.json', dict(passed=result.wasSuccessful(),
                     methods=result.testsRun, errors=len(result.errors), failures=len(result.failures),
                     selected_case_ids=selected, executed_case_ids=result.executed_ids,
                     passed_case_ids=result.passed_ids, failed_case_ids=result.failed_ids,
                     framework_errors=result.framework_errors,
                     source_sha256={'note10/device_test/'+name: profile.sha(Path(__file__).parent/name)
                                    for name in profile.HOST_SOURCES}, synthetic_inputs_only=True,
                     device_operations=[], compiler_invocations=0, old_test_runners_invoked=0, files_sha256=files))
    sys.exit(0 if result.wasSuccessful() else 1)
