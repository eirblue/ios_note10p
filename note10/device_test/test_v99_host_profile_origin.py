"""One NEW synthetic metadata regression; no package/Image/native fixture reads."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import unittest

import sha256_kat_device_profile as profile

METHOD = 'test_exact_retained_origins_and_live_construction_boundary'


class HostProfileOriginTests(unittest.TestCase):
    def test_exact_retained_origins_and_live_construction_boundary(self):
        old = dict(device_profile=profile.DATA_PROFILE, source_head=profile.V91_IMAGE_HEAD,
                   host_profile_source_head=profile.V97_PROFILE_ORIGIN_HEAD,
                   host_profile_source_sha256=dict(profile.V97_PROFILE_ORIGIN_PINS),
                   data_host_experiment='v97-current-data-reuse-v91', data_current_binding_sha256='a'*64)
        new = dict(device_profile=profile.DATA_PROFILE, source_head=profile.V99_PROFILE_ORIGIN_HEAD,
                   host_profile_source_head=profile.V99_PROFILE_ORIGIN_HEAD,
                   host_profile_source_sha256=dict(profile.V99_PROFILE_ORIGIN_PINS),
                   data_compare_schema='n10-data-compare-v1')
        # Golden complete-map digests from the approved source/preimage closure,
        # independent of a supplied package row or a runtime current-host map.
        golden = ((old,31,'c0d944e474f7470e20d0baeb52067bd0083a7db3cd4268d1587a57f4cdbb65d8'),
                  (new,34,'d2bde6cae69971e82436dacc73ad83fc17975b4372f7744d650ddfef97d63687'))
        for binding, count, digest in golden:
            with self.subTest(origin=binding['host_profile_source_head']):
                pins = binding['host_profile_source_sha256']
                self.assertEqual(len(pins),count)
                self.assertEqual(hashlib.sha256(json.dumps(pins,sort_keys=True,separators=(',',':')).encode()).hexdigest(),digest)
                origin = profile.host_profile_origin(binding)
                self.assertEqual(set(origin),{'host_profile_source_head','host_profile_source_sha256'})
                self.assertEqual(origin['host_profile_source_sha256'],pins)
                key = next(iter(pins))
                origin['host_profile_source_sha256'][key] = '0'*64
                self.assertEqual(profile.host_profile_origin(binding)['host_profile_source_sha256'],pins)
                for mutation in ('changed_pin','missing_pin','extra_pin','wrong_source','wrong_profile','wrong_origin'):
                    bad = copy.deepcopy(binding)
                    if mutation == 'changed_pin': bad['host_profile_source_sha256'][key] = '0'*64
                    if mutation == 'missing_pin': del bad['host_profile_source_sha256'][key]
                    if mutation == 'extra_pin': bad['host_profile_source_sha256']['note10/device_test/unapproved.py'] = '1'*64
                    if mutation == 'wrong_source': bad['source_head'] = 'f'*40
                    if mutation == 'wrong_profile': bad['device_profile'] = profile.BUILTIN_PROFILE
                    if mutation == 'wrong_origin':
                        bad['host_profile_source_head'] = (profile.V99_PROFILE_ORIGIN_HEAD
                            if binding is old else profile.V97_PROFILE_ORIGIN_HEAD)
                    with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                        profile.host_profile_origin(bad)
                with self.assertRaisesRegex(ValueError,'retained host origin cannot construct current host'):
                    profile.host_binding(binding['host_profile_source_head'])
        for pins in (profile.V97_PROFILE_ORIGIN_PINS,profile.V99_PROFILE_ORIGIN_PINS):
            with self.assertRaises(TypeError):
                pins[next(iter(pins))] = '0'*64
        bad_scopes = []
        for change in ({'data_compare_schema':'n10-data-compare-v1'}, {'data_host_experiment':'other'},
                       {'data_current_binding_sha256':'not-a-hash'}):
            bad = copy.deepcopy(old); bad.update(change); bad_scopes.append(bad)
        for change in ({'data_compare_schema':None}, {'data_compare_schema':'unsupported'},
                       {'data_host_experiment':None}, {'data_current_binding_sha256':'a'*64}):
            bad = copy.deepcopy(new); bad.update(change); bad_scopes.append(bad)
        bad = copy.deepcopy(new); del bad['data_compare_schema']; bad_scopes.append(bad)
        # A new normal producer cannot borrow the old current-package origin.
        bad = copy.deepcopy(new)
        bad.update(host_profile_source_head=profile.V97_PROFILE_ORIGIN_HEAD,
                   host_profile_source_sha256=dict(profile.V97_PROFILE_ORIGIN_PINS))
        bad_scopes.append(bad)
        for index, bad in enumerate(bad_scopes):
            with self.subTest(scope=index), self.assertRaises(ValueError):
                profile.host_profile_origin(bad)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=False)
    suite = unittest.TestSuite([HostProfileOriginTests(METHOD)])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    (args.output/'result.json').write_text(json.dumps(dict(schema='v99-host-origin-new-regression-v1',
        selected=['HostProfileOriginTests.'+METHOD],run=result.testsRun,failures=len(result.failures),
        errors=len(result.errors),passed=result.wasSuccessful(),fixture_compiles=0,
        native_executions=0,package_or_Image_reads=0,old_test_methods_run=0),indent=2)+'\n')
    raise SystemExit(0 if result.wasSuccessful() else 1)
