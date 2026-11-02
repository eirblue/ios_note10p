"""One NEW synthetic predecessor-rule regression; no real BOOT/package inputs."""
import argparse
import copy
import json
from pathlib import Path
import unittest

from builtin_init_profile import current_boot_binding

METHOD = 'test_exact_v97_predecessor_and_private_boot_equality'


class CurrentBootChainTests(unittest.TestCase):
    def test_exact_v97_predecessor_and_private_boot_equality(self):
        plan = dict(device_profile='linux-data-carrier-v1', current_boot_payload_sha256='a'*64)
        diagnostic = dict(payload_sha256='a'*64)
        current = dict(device_profile='linux-data-carrier-v1',
            source_head='0696b4dbf157a2d51b68b26e4a5237a7c51daa80',
            host_profile_source_head='bdd56f101e3e9bb83ecbadad03be24473f143447',
            data_host_experiment='v97-current-data-reuse-v91', data_current_binding_sha256='b'*64)
        originals = copy.deepcopy((plan,current,diagnostic))
        self.assertIsNone(current_boot_binding(plan,current,diagnostic))
        self.assertEqual((plan,current,diagnostic),originals)
        # The previous exact v90 predecessor still needs no new v97-only fields.
        previous = dict(device_profile='linux-data-carrier-v1',
            source_head='59bfd8d9f21047c9d943cd0dd4f4eb96fb5459e9',
            host_profile_source_head='59bfd8d9f21047c9d943cd0dd4f4eb96fb5459e9')
        self.assertIsNone(current_boot_binding(plan,previous,diagnostic))
        for change in ({'source_head':'f'*40}, {'host_profile_source_head':'f'*40},
                       {'device_profile':'sha256-kat-builtin-init-v2'},
                       {'data_host_experiment':'other'}, {'data_current_binding_sha256':'bad'},
                       {'data_current_binding_sha256':None}, {'data_compare_schema':None},
                       {'data_compare_schema':'n10-data-compare-v1'}):
            bad = dict(current,**change)
            with self.subTest(change=change), self.assertRaisesRegex(ValueError,'exact prior'):
                current_boot_binding(plan,bad,diagnostic)
        for key in ('data_host_experiment','data_current_binding_sha256'):
            bad = dict(current); del bad[key]
            with self.subTest(missing=key), self.assertRaises(ValueError):
                current_boot_binding(plan,bad,diagnostic)
        for prior in (current,previous):
            with self.subTest(origin=prior['source_head']):
                with self.assertRaises(ValueError):
                    current_boot_binding(plan,prior,dict(payload_sha256='c'*64))
                with self.assertRaises(ValueError):
                    current_boot_binding(dict(plan,current_boot_payload_sha256='not-a-hash'),prior,diagnostic)
        # A newly produced comparison profile is not a retained v97 predecessor.
        new = dict(current,source_head='4f9eb149bd116db77eaf3400a25f7454577268a9',
                   host_profile_source_head='4f9eb149bd116db77eaf3400a25f7454577268a9',
                   data_compare_schema='n10-data-compare-v1')
        with self.assertRaises(ValueError):
            current_boot_binding(plan,new,diagnostic)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=False)
    suite = unittest.TestSuite([CurrentBootChainTests(METHOD)])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    (args.output/'result.json').write_text(json.dumps(dict(schema='v99-current-boot-chain-new-regression-v1',
        selected=['CurrentBootChainTests.'+METHOD],run=result.testsRun,failures=len(result.failures),
        errors=len(result.errors),passed=result.wasSuccessful(),fixture_compiles=0,
        real_BOOT_or_package_reads=0,native_executions=0,old_test_methods_run=0),indent=2)+'\n')
    raise SystemExit(0 if result.wasSuccessful() else 1)
