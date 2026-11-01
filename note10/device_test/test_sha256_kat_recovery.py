"""One NEW-only integration batch; never executes the accepted v70 test/fixture."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import unittest
from unittest.mock import patch

import prepare_sha256_kat_recovery as prepare
import build_sha256_kat_recovery as builder

HERE = Path(__file__).resolve().parent
IDENTITY = 'abcdef0123456789abcdef0123456789'
OUTPUT = None


class RecoveryIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if OUTPUT is None:
            raise RuntimeError('explicit fresh --output invocation required')
        cls.root = OUTPUT
        cls.root.mkdir(parents=True)
        for name in ('sha256_kat_recovery_fixture.c', 'sha256_kat_recovery_work.c'):
            shutil.copyfile(HERE/name, cls.root/name)
        compiler = os.environ.get('CC') or shutil.which('gcc') or shutil.which('clang')
        if not compiler:
            raise RuntimeError('new scheduling fixture requires a host C compiler')
        cls.binary = cls.root/('fixture.exe' if os.name == 'nt' else 'fixture')
        command = [compiler, '-std=c11', '-Wall', '-Wextra', '-Werror', '-O1',
                   str(cls.root/'sha256_kat_recovery_fixture.c'), '-o', str(cls.binary)]
        (cls.root/'compile-command.json').write_text(json.dumps(command, indent=2)+'\n')
        process = subprocess.run(command, capture_output=True, text=True, timeout=60)
        (cls.root/'compile.stdout').write_text(process.stdout)
        (cls.root/'compile.stderr').write_text(process.stderr)
        if process.returncode:
            raise AssertionError(process.stdout+process.stderr)

    def test_v71_01_new_worker_admission_and_queue_isolation(self):
        for scenario in range(11):
            with self.subTest(scenario=scenario):
                process = subprocess.run([str(self.binary), str(scenario)], capture_output=True, text=True, timeout=10)
                (self.root/f'connection-{scenario:02}.stdout').write_text(process.stdout)
                (self.root/f'connection-{scenario:02}.stderr').write_text(process.stderr)
                self.assertEqual(process.returncode, 0, process.stderr)

    def test_v71_02_composition_preserves_inherited_bytes(self):
        files = prepare.render(IDENTITY)
        self.assertEqual(files['drivers/misc/sha256_runtime_kat.c'], (HERE/'sha256_runtime_kat.c').read_bytes())
        self.assertEqual(files['drivers/misc/note10_auto_return.c'], (HERE/'auto_return.c').read_bytes())
        self.assertIn(b'default n', files['drivers/misc/note10_sha256_kat.Kconfig'])
        self.assertIn(IDENTITY.encode(), files['drivers/misc/note10_sha256_kat_id.h'])
        # Packaging reads only; no old KAT/recovery function or decoder execution.
        for identity in (None, '', 'F'*32, '0'*31, '0'*33, 'g'*32):
            with self.subTest(identity=identity), self.assertRaises(ValueError):
                prepare.render(identity)

    def test_v71_03_fresh_overlay_and_dirty_stock_rejection(self):
        root = self.root/'overlay'
        (root/'drivers/misc').mkdir(parents=True)
        (root/'drivers/misc/Makefile').write_text('# stock build hook\n')
        (root/'drivers/misc/Kconfig').write_text('menu "Misc"\nendmenu\n')
        stock = {}
        for index, name in enumerate(prepare.KERNEL_PINS):
            data = f'fixture-stock-{index}\n'.encode()
            target = root/name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            stock[name] = hashlib.sha256(data).hexdigest()
        with patch.dict(prepare.KERNEL_PINS, stock, clear=True):
            dirty = root/'init/main.c'
            original = dirty.read_bytes()
            dirty.write_bytes(original+b'dirty')
            with self.assertRaises(ValueError):
                prepare.install(root, IDENTITY)
            self.assertFalse((root/'drivers/misc/note10_sha256_kat.c').exists())
            dirty.write_bytes(original)
            prepared = prepare.install(root, IDENTITY)
            self.assertEqual(len(prepared), 9)
            before = {name: (root/name).read_bytes() for name in prepared}
            with self.assertRaises(ValueError):
                prepare.install(root, IDENTITY)
            self.assertEqual(before, {name: (root/name).read_bytes() for name in prepared})
        self.assertEqual((root/'drivers/misc/note10_auto_return.c').read_bytes(), (HERE/'auto_return.c').read_bytes())

    def test_v71_04_external_initrd_and_firmware_build_connection(self):
        root = self.root/'image-inputs'
        data = {'firmware/Makefile': b'prefix\n\t$(call cmd,fwbin,$(patsubst %.gen.S,%,$@))\nsuffix\n',
                'init/initramfs.c': b'prefix\n\tdo_skip_initramfs = 1;\n\treturn 1;\nsuffix\n'}
        for name, raw in data.items():
            target = root/name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
        pins = {name: hashlib.sha256(raw).hexdigest() for name, raw in data.items()}
        with patch.dict(builder.BUILD_INPUT_PINS, pins, clear=True):
            builder.prepare_image_inputs(root)
        initrd = (root/'init/initramfs.c').read_bytes()
        firmware = (root/'firmware/Makefile').read_bytes()
        self.assertNotIn(b'do_skip_initramfs = 1;', initrd)
        self.assertTrue(initrd.startswith(b'prefix\n') and initrd.endswith(b'\treturn 1;\nsuffix\n'))
        self.assertIn(b'$(srctree)/', firmware)
        self.assertTrue(firmware.startswith(b'prefix\n') and firmware.endswith(b'suffix\n'))
        self.assertEqual(builder.SETTINGS['INITRAMFS_SOURCE'], '""')
        self.assertEqual(builder.SETTINGS['INITRAMFS_FORCE'], 'n')
        self.assertEqual(builder.SETTINGS['BLK_DEV_INITRD'], 'y')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    OUTPUT = args.output.resolve()
    private = (HERE.parents[1]/'note10/private').resolve()
    if OUTPUT == private or not OUTPUT.is_relative_to(private) or OUTPUT.exists():
        raise ValueError('fresh private test output required; preserve previous evidence')
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(RecoveryIntegrationTests))
    if OUTPUT.is_dir():
        files = {p.relative_to(OUTPUT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                 for p in OUTPUT.rglob('*') if p.is_file()}
        (OUTPUT/'result.json').write_text(json.dumps(dict(
            passed=result.wasSuccessful(), methods=result.testsRun,
            included_new_worker_scenarios=11, failures=len(result.failures), errors=len(result.errors),
            v70_fixture_or_tests_executed=False, real_recovery_or_provider_executed=False,
            files_sha256=files), indent=2, sort_keys=True)+'\n')
    sys.exit(0 if result.wasSuccessful() else 1)
