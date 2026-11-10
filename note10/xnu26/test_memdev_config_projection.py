"""Three new projection cases; no native generator, compiler or old fixture."""
import hashlib
import json
import unittest

from memdev_config_projection import project_defines


class MemdevConfigProjectionTests(unittest.TestCase):
    def test_normal_defines_are_public_and_unchanged(self):
        defines = ['-DMACH', '-DCONFIG_KN_HASHSIZE=48', '-DPRIVATE', '-DVALUE=-1']
        before = defines.copy()
        public, record = project_defines(defines)
        self.assertEqual(public, before)
        self.assertEqual(defines, before)
        self.assertEqual(record, dict(schema='note10-v169-bsd-defines-projection-v1',
            full_count=4, full_sha256=hashlib.sha256(json.dumps(before, separators=(',', ':')).encode()).hexdigest(),
            public_count=4, omitted_count=0, omitted=[]))

    def test_actual_bsd_expression_is_omitted_without_argv_change(self):
        flag = '-DCONFIG_NMBCLUSTERS=((1024 * 256) / MCLBYTES)'
        defines = ['-DMACH', flag, '-DPRIVATE']
        before = defines.copy()
        public, record = project_defines(defines)
        self.assertEqual(public, ['-DMACH', '-DPRIVATE'])
        self.assertEqual(defines, before)
        self.assertEqual(record['full_count'], 3)
        self.assertEqual(record['public_count'], 2)
        self.assertEqual(record['omitted_count'], 1)
        self.assertEqual(record['omitted'], [dict(name='CONFIG_NMBCLUSTERS',
            sha256=hashlib.sha256(flag.encode()).hexdigest())])
        self.assertEqual(record['full_sha256'], hashlib.sha256(
            json.dumps(before, separators=(',', ':')).encode()).hexdigest())
        self.assertNotIn('MCLBYTES', json.dumps(record))

    def test_unsafe_values_never_enter_public_text(self):
        defines = ['-DPOSIX=/synthetic/private.h', r'-DDRIVE=C:\synthetic\private.h',
            r'-DUNC=\\synthetic\share\private.h', '-DTILDE=~/synthetic/private.h',
            "-DQUOTE='/synthetic/O'Neil/private.h'", '-I/synthetic/private']
        before = defines.copy()
        public, record = project_defines(defines)
        self.assertEqual(public, [])
        self.assertEqual(defines, before)
        self.assertEqual(record['public_count'], 0)
        self.assertEqual(record['omitted_count'], len(before))
        self.assertEqual(record['omitted'], [dict(name=name, sha256=hashlib.sha256(flag.encode()).hexdigest())
            for name, flag in zip(['POSIX', 'DRIVE', 'UNC', 'TILDE', 'QUOTE', 'unclassified'], before)])
        self.assertNotIn('synthetic', json.dumps(record))
        for invalid in (None, ['-DMACH', 1], ['x' * 4097], ['-DMACH'] * 1025):
            with self.assertRaises(ValueError):
                project_defines(invalid)


if __name__ == '__main__':
    unittest.main()
