"""Only the three new native-selection cases; actual upstream config tool, no old suites."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import unittest

import build_native_bootstrap_selection as native
from prepare_native_bootstrap_selection import OPTION, SOURCES

CASE_NAMES = (
    'test_exynos_native_config_selects_each_bootstrap_source_once',
    'test_existing_ppl_sptm_selection_preserved_by_alternative_rules',
    'test_selected_source_build_rejects_duplicate_or_candidate_ownership',
)


def source_tokens(text):
    text = text.replace('\\\n', ' ')
    return {key: re.search('^' + key + '=(.*)$', text, re.M).group(1).split()
            for key in ('CFILES', 'SFILES')}


class NativeBootstrapSelectionTests(unittest.TestCase):
    work = None

    def context(self):
        c = native.load_context(self.work)
        return Path(c['source']), Path(c['tool'])

    def test_exynos_native_config_selects_each_bootstrap_source_once(self):
        source, tool = self.context()
        for variant in ('RELEASE', 'DEVELOPMENT', 'DEBUG'):
            with self.subTest(variant=variant):
                out = self.work / ('selection-' + variant)
                text = native.configure(source, tool, out, variant)
                self.assertEqual(native.selected_sources({'osfmk': text}), SOURCES)
                header = (out / 'config_note10_native_bootstrap.h').read_text()
                self.assertRegex(header, r'#define\s+' + OPTION + r'\s+1\b')
                tokens = source_tokens(text)
                self.assertFalse(any('/sptm/' in n for values in tokens.values() for n in values))
                self.assertNotIn('-DCONFIG_PMAP_PPL', native.definitions(text))
                self.assertNotIn('-DCONFIG_SPTM', native.definitions(text))

    def test_existing_ppl_sptm_selection_preserved_by_alternative_rules(self):
        source, tool = self.context()
        baseline = self.work / 'original-config-directory'
        baseline.mkdir()
        # Copy only the config directory inputs. The accepted source is not rewritten.
        for p in (source / 'osfmk/conf').iterdir():
            if p.is_file():
                shutil.copyfile(p, baseline / p.name)
        (baseline / 'files.arm64').write_bytes((self.work / 'baseline-files.arm64').read_bytes())
        for name, extras in (
            ('ppl', ('CONFIG_PMAP_PPL', 'NOS_ARM_ASM', 'NOS_ARM_PMAP')),
            ('sptm', ('CONFIG_SPTM', 'NOS_ARM_ASM')),
        ):
            with self.subTest(selection=name):
                old = native.configure(source, tool, self.work / (name + '-old'),
                    extras=extras, option=False, conf_directory=baseline)
                new = native.configure(source, tool, self.work / (name + '-new'),
                    extras=extras, option=False)
                self.assertEqual(source_tokens(old), source_tokens(new))
        # Both alternatives matching must still give one source definition.
        both = native.configure(source, tool, self.work / 'both-alternatives',
            extras=('CONFIG_PMAP_PPL', 'NOS_ARM_ASM', 'NOS_ARM_PMAP'))
        self.assertEqual(native.selected_sources({'osfmk': both}), SOURCES)

    def test_selected_source_build_rejects_duplicate_or_candidate_ownership(self):
        source, tool = self.context()
        text = native.configure(source, tool, self.work / 'ownership-input')
        self.assertEqual(len(native.selected_sources({'osfmk': text})), 15)
        token = '$(SOURCE_DIR)/' + SOURCES[0]
        duplicate = re.sub(r'^CFILES=', 'CFILES=' + token + ' ', text, count=1, flags=re.M)
        with self.assertRaises(ValueError):
            native.selected_sources({'osfmk': duplicate})
        with self.assertRaises(ValueError):
            native.selected_sources({'osfmk': text, 'bsd': text})
        missing = text.replace(token, '', 1)
        with self.assertRaises(ValueError):
            native.selected_sources({'osfmk': missing})
        for wrong in ({'PLATFORM_C': text}, {'osfmk': text, 'platform-asm': text}):
            with self.assertRaises(ValueError):
                native.selected_sources(wrong)


class Recorded(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.failed_methods = set()

    def addFailure(self, test, error):
        self.failed_methods.add(test._testMethodName)
        super().addFailure(test, error)

    def addError(self, test, error):
        self.failed_methods.add(test._testMethodName)
        super().addError(test, error)

    def addSubTest(self, test, subtest, error):
        if error is not None:
            self.failed_methods.add(test._testMethodName)
        super().addSubTest(test, subtest, error)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--work', required=True)
    p.add_argument('--output', required=True)
    p.add_argument('--case', action='append', choices=CASE_NAMES)
    args = p.parse_args()
    selected = args.case
    if selected is None:
        selected = json.loads(os.environ.get('N10_CI_CASE_JSON', '[]'))
        if type(selected) is not list or any(type(n) is not str or n not in CASE_NAMES for n in selected):
            p.error('closed new case ID array required')
        selected = selected or list(CASE_NAMES)
    if len(selected) != len(set(selected)):
        p.error('duplicate case selection')
    NativeBootstrapSelectionTests.work = native.private(args.work)
    context = native.load_context(NativeBootstrapSelectionTests.work)
    output = native.private(args.output)
    output.mkdir(parents=True, exist_ok=False)
    result = unittest.TextTestRunner(verbosity=2, resultclass=Recorded).run(
        unittest.TestSuite(NativeBootstrapSelectionTests(n) for n in selected))
    failed = sorted(result.failed_methods)
    success = result.wasSuccessful() and result.testsRun == len(selected) and not result.skipped
    receipt = dict(kind='v83-new-native-bootstrap-source-selection', selected=selected,
        passed=[n for n in selected if n not in failed], failed=failed,
        tests_run=result.testsRun, success=success, old_suites_executed=0,
        ci_context=context['ci_context'], public_source_commit=native.COMMIT,
        source_sha256={name: hashlib.sha256((Path(__file__).parent / name).read_bytes()).hexdigest()
            for name in ('test_native_bootstrap_selection.py', 'build_native_bootstrap_selection.py',
                         'prepare_native_bootstrap_selection.py')}, device_operations=[])
    native.write_json(output / 'result.json', receipt)
    return 0 if success else 1


if __name__ == '__main__':
    raise SystemExit(main())
