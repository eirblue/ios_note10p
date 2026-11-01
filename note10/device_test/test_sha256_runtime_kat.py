"""One new-only batch: canonical C control flow, strict frames, fresh overlay hooks."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import unittest

from decode_sha256_runtime_kat import decode, ANSWER, checksum
from prepare_sha256_runtime_kat import render, install

HERE = Path(__file__).resolve().parent
IDENTITY = '0123456789abcdef0123456789abcdef'
OUTPUT = None


def frame(copy, status=0, driver=1, computed=1, digest=ANSWER, identity=IDENTITY):
    body = (f'id={identity} copy={copy} phase=late-init status={status} '
            f'driver_match={driver} computed={computed} digest={digest}')
    return f'N10SHA1 {body} checksum={checksum(body.encode()):08x}\n'


class RuntimeKatTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if OUTPUT is None:
            raise RuntimeError('use the explicit --output new-batch invocation')
        cls.root = OUTPUT
        cls.root.mkdir(parents=True)
        for name in ('sha256_runtime_kat.c', 'sha256_runtime_kat_fixture.c'):
            shutil.copyfile(HERE/name, cls.root/name)
        (cls.root/'sha256_kat_host.h').write_text('/* stubs declared by fixture */\n')
        (cls.root/'note10_sha256_kat_id.h').write_bytes(render(IDENTITY)['drivers/misc/note10_sha256_kat_id.h'])
        compiler = os.environ.get('CC') or shutil.which('clang') or shutil.which('cc')
        if not compiler:
            raise RuntimeError('new canonical C batch requires a host C compiler')
        cls.binary = cls.root/('fixture.exe' if os.name == 'nt' else 'fixture')
        cls.command = [compiler, '-std=c11', '-Wall', '-Wextra', '-Werror', '-O1',
                       str(cls.root/'sha256_runtime_kat_fixture.c'), '-o', str(cls.binary)]
        (cls.root/'compile-command.json').write_text(json.dumps(cls.command, indent=2)+'\n')
        result = subprocess.run(cls.command, capture_output=True, text=True, timeout=60)
        (cls.root/'compile.stdout').write_text(result.stdout)
        (cls.root/'compile.stderr').write_text(result.stderr)
        if result.returncode:
            raise AssertionError(result.stdout+result.stderr)

    def test_v70_01_canonical_c_runtime_outcomes(self):
        # Ten independent paths, one compiler invocation, all resources asserted in C.
        statuses = [0, -2, -22, -22, -22, -12, -5, -74, 0, -22]
        for scenario, status in enumerate(statuses):
            with self.subTest(scenario=scenario):
                process = subprocess.run([str(self.binary), str(scenario)], capture_output=True, text=True, timeout=10)
                (self.root/f'c-case-{scenario:02}.stdout').write_text(process.stdout)
                (self.root/f'c-case-{scenario:02}.stderr').write_text(process.stderr)
                self.assertEqual(process.returncode, 0, process.stderr)
                result = decode(process.stdout, IDENTITY)
                self.assertEqual(result['status'], status)
                self.assertEqual(result['passed'], scenario in (0, 8))
                self.assertFalse(result['physical_safety_proven'])

    def test_v70_02_decoder_accepts_log_prefixes(self):
        result = decode('[ 1.2] '+frame(1)+'kernel: '+frame(0), IDENTITY)
        self.assertTrue(result['passed'])
        self.assertEqual(result['driver'], 'sha256-generic')

    def test_v70_03_decoder_rejects_damaged_or_merged_frames(self):
        good = frame(0)+frame(1)
        bad = [frame(0), good+frame(0), frame(0)+frame(0),
               good.replace('checksum=', 'checksum=f', 1),
               frame(0)+frame(1, identity='f'*32), good.replace('copy=0', 'copy=2', 1),
               good.replace('phase=late-init', 'phase=early-init', 1),
               good.replace('N10SHA1 ', 'N10SHA1 id=duplicate ', 1)]
        for index, text in enumerate(bad):
            with self.subTest(case=index), self.assertRaises(ValueError):
                decode(text, IDENTITY)

    def test_v70_04_decoder_rejects_checksumming_contradictions(self):
        cases = [dict(driver=0), dict(computed=0), dict(digest='0'*64),
                 dict(status=-5), dict(status=-74), dict(status=1),
                 dict(status=-4096), dict(status=-5, driver=0, computed=0, digest='f'*64),
                 dict(status=-22, computed=0, digest='0'*64)]
        for index, kwargs in enumerate(cases):
            # Last case differs between intact copies; both individually well formed.
            text = frame(0, **kwargs)+frame(1, **kwargs) if index < len(cases)-1 else frame(0, **kwargs)+frame(1, status=-12, computed=0, digest='0'*64)
            with self.subTest(case=index), self.assertRaises(ValueError):
                decode(text, IDENTITY)

    def test_v70_05_overlay_default_off_and_identity_bound(self):
        files = render(IDENTITY)
        self.assertEqual(len(files), 4)
        self.assertIn(b'default n', files['drivers/misc/note10_sha256_kat.Kconfig'])
        self.assertIn(IDENTITY.encode(), files['drivers/misc/note10_sha256_kat_id.h'])
        for identity in ('', 'g'*32, 'F'*32, '0'*31, '0'*33, None):
            with self.subTest(identity=identity), self.assertRaises(ValueError):
                render(identity)

    def test_v70_06_fresh_hooks_and_duplicate_install_rejected(self):
        root = self.root/'overlay'
        misc = root/'drivers/misc'
        misc.mkdir(parents=True)
        (misc/'Kconfig').write_text('menu "Misc"\nendmenu\n')
        (misc/'Makefile').write_text('# stock\n')
        result = install(root, IDENTITY)
        self.assertEqual(len(result), 6)
        self.assertIn('note10_sha256_kat.Makefile', (misc/'Makefile').read_text())
        self.assertIn('note10_sha256_kat.Kconfig', (misc/'Kconfig').read_text())
        before = {p.name: p.read_bytes() for p in misc.iterdir()}
        with self.assertRaises(ValueError):
            install(root, IDENTITY)
        self.assertEqual(before, {p.name: p.read_bytes() for p in misc.iterdir()})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    OUTPUT = args.output.resolve()
    private = (HERE.parents[1]/'note10/private').resolve()
    if not OUTPUT.is_relative_to(private) or OUTPUT == private or OUTPUT.exists():
        raise ValueError('fresh project-private batch output required; preserve prior evidence')
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(RuntimeKatTests))
    if OUTPUT.is_dir():
        manifest = {p.relative_to(OUTPUT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in OUTPUT.rglob('*') if p.is_file()}
        (OUTPUT/'result.json').write_text(json.dumps(dict(
            passed=result.wasSuccessful(), test_methods=result.testsRun,
            failures=len(result.failures), errors=len(result.errors),
            canonical_c_stub_only=True, kernel_or_provider_executed=False,
            files_sha256=manifest), indent=2, sort_keys=True)+'\n')
    sys.exit(0 if result.wasSuccessful() else 1)
