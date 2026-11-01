"""NEW config-policy cases only; no worker/native/v70 suite or compiler."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import unittest
from build_sha256_kat_recovery import bootloader_cmdline_policy

OUTPUT = None


class CmdlinePolicyTests(unittest.TestCase):
    def test_v71c_01_empty_builtin_preserves_default_dt_arguments(self):
        for tail in ('', 'CONFIG_CMDLINE_FROM_BOOTLOADER=y\n',
                     '# CONFIG_CMDLINE_FORCE is not set\n# CONFIG_CMDLINE_EXTEND is not set\n'):
            with self.subTest(tail=tail):
                result = bootloader_cmdline_policy('CONFIG_CMDLINE=""\n'+tail)
                self.assertTrue(result['bootloader_arguments_preserved'])
                self.assertTrue(result['builtin_cmdline_empty'])

    def test_v71c_02_force_rejected_even_with_empty_builtin(self):
        with self.assertRaises(ValueError):
            bootloader_cmdline_policy('CONFIG_CMDLINE=""\nCONFIG_CMDLINE_FORCE=y\n')

    def test_v71c_03_nonempty_builtin_cannot_supply_root_or_boot_arguments(self):
        for value in ('root=/dev/sda1', 'rdinit=/wrong', 'console=wrong', ' '):
            with self.subTest(value=value), self.assertRaises(ValueError):
                bootloader_cmdline_policy('CONFIG_CMDLINE="'+value+'"\nCONFIG_CMDLINE_FROM_BOOTLOADER=y\n')

    def test_v71c_04_concat_duplicate_missing_or_invalid_setting_rejected(self):
        for text in ('CONFIG_CMDLINE=""\nCONFIG_CMDLINE_EXTEND=y\n',
                     'CONFIG_CMDLINE=""\nCONFIG_CMDLINE=""\n',
                     'CONFIG_CMDLINE_FORCE=n\n',
                     'CONFIG_CMDLINE=""\nCONFIG_CMDLINE_FROM_BOOTLOADER=m\n'):
            with self.subTest(text=text), self.assertRaises(ValueError):
                bootloader_cmdline_policy(text)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    OUTPUT = args.output.resolve()
    private = (Path(__file__).resolve().parents[2]/'note10/private').resolve()
    if OUTPUT == private or not OUTPUT.is_relative_to(private) or OUTPUT.exists():
        raise ValueError('fresh private config-policy test output required')
    OUTPUT.mkdir(parents=True)
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(CmdlinePolicyTests))
    sources = {name: hashlib.sha256((Path(__file__).parent/name).read_bytes()).hexdigest()
               for name in ('build_sha256_kat_recovery.py', 'test_sha256_kat_cmdline_policy.py')}
    (OUTPUT/'result.json').write_text(json.dumps(dict(passed=result.wasSuccessful(), methods=result.testsRun,
        failures=len(result.failures), errors=len(result.errors), source_sha256=sources,
        worker_or_v70_tests_executed=False, compiler_invocations=0, device_operations=[]), indent=2, sort_keys=True)+'\n')
    sys.exit(0 if result.wasSuccessful() else 1)
