"""Only the three new current-input/direct-link cases; no legacy suites or binaries."""
import argparse
import base64
import copy
import json
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import current_native_kernel as native

CASE_NAMES = ('test_current_inventory_resolves_owner_and_generated_identity',
              'test_current_context_rejects_stale_candidate_and_partial_objects',
              'test_direct_native_link_uses_current_filelist_and_reports_failure')


def assignments(c='', cxx='', assembly=''):
    return 'CFILES=' + c + '\nCXXFILES=' + cxx + '\nSFILES=' + assembly + '\n'


def fixture(root):
    source, generated, objects = root / 'source', root / 'generated', root / 'objects'
    for p in (source, generated, objects):
        p.mkdir(parents=True)
    real = source / 'osfmk/kperf/kperfbsd.c'
    real.parent.mkdir(parents=True)
    real.write_text('int fixture_bsd_owner;\n')
    makefiles = {c: assignments() for c in native.COMPONENTS}
    makefiles['bsd'] = assignments('$(SOURCE_DIR)/osfmk/kperf/kperfbsd.c ./same.c')
    makefiles['osfmk'] = assignments('./same.c')
    generated_rows = {}
    for c in ('osfmk', 'bsd'):
        p = generated / c / 'same.c'
        p.parent.mkdir()
        p.write_text('int fixture_' + c + ';\n')
        generated_rows[(c, './same.c')] = dict(path=str(p), source_sha256=native.file_sha(p), passed=True)
    inventory = native.inventory(makefiles, source, generated_rows, generated)
    runtime = root / 'compiler-runtime.a'
    runtime.write_bytes(b'synthetic compiler runtime')
    producer = dict(source_commit='a' * 40, objects_root=str(objects),
                    toolchain=dict(compiler='synthetic-clang', sdk='synthetic-sdk',
                        runtime=dict(path=str(runtime), sha256=native.file_sha(runtime))),
                    ci_context=dict(run_id=17, attempt=1), fresh_work_root=str(root))
    bindings = dict(configuration='synthetic-current', generators='synthetic-current',
                    link_flags_sha256=native.digest(['-nostdlib', '-static']))
    deps = {}
    for i, name in enumerate(native.EXTRAS):
        p = generated / ('dependency-' + str(i) + '.c')
        p.write_text('int fixture_dependency_' + str(i) + ';\n')
        deps[name] = dict(path=str(p), source_sha256=native.file_sha(p))
    current = dict(kind='v84-current-native', producer=producer, producer_id=native.digest(producer),
                   bindings=bindings, input_binding=native.digest(bindings), inventory=inventory, dependencies=deps)
    rows = []
    for i, (name, category, sha) in enumerate(
        [(r['source'], 'native', r['source_sha256']) for r in inventory] +
        [(n, native.EXTRAS[n], d['source_sha256']) for n, d in deps.items()]):
        p = objects / (str(i) + '.o')
        p.write_bytes(b'synthetic object fixture ' + str(i).encode())
        rows.append(native.stamp(current, dict(source=name, passed=True, source_sha256=sha,
            object_path=str(p), object_sha256=native.file_sha(p)), category))
    return current, rows, makefiles, source, generated_rows, generated


class CurrentNativeKernelTests(unittest.TestCase):
    output = None

    def setUp(self):
        self.root = self.output / self._testMethodName
        self.root.mkdir()

    def test_current_inventory_resolves_owner_and_generated_identity(self):
        current, rows, makefiles, source, generated, root = fixture(self.root)
        inventory = current['inventory']
        self.assertEqual(next(r['component'] for r in inventory if r['source'] == 'osfmk/kperf/kperfbsd.c'), 'bsd')
        self.assertEqual({r['source'] for r in inventory if r['source'].startswith('@generated/')},
                         {'@generated/osfmk/same.c', '@generated/bsd/same.c'})
        token = '$(SOURCE_DIR)/osfmk/kperf/kperfbsd.c'
        for changes in (
            {'bsd': assignments(token + ' ' + token)},
            {'pexpert': assignments(token)},
            {'bsd': assignments(token + ' ./same.c', token)},
            {'san': assignments('./unresolved.c')},
            {'san': assignments('$(SOURCE_DIR)/../outside.c')},
        ):
            changed = dict(makefiles)
            changed.update(changes)
            with self.assertRaises(ValueError):
                native.inventory(changed, source, generated, root)

    def test_current_context_rejects_stale_candidate_and_partial_objects(self):
        current, rows, *_ = fixture(self.root)
        self.assertEqual(len(native.admit_objects(current, rows)), len(rows))
        mutations = [('producer_id', 'b' * 64), ('input_binding', 'c' * 64),
                     ('category', 'architecture_candidates'), ('passed', False), ('source_sha256', 'd' * 64)]
        for key, value in mutations:
            changed = copy.deepcopy(rows)
            changed[0][key] = value
            with self.assertRaises(ValueError):
                native.admit_objects(current, changed)
        for changed in (rows[:-1], rows + [rows[0]]):
            with self.assertRaises(ValueError):
                native.admit_objects(current, changed)
        for key, value in (('source_commit', 'e' * 40), ('ci_context', dict(run_id=18, attempt=1)),
                           ('ci_context', dict(run_id=17, attempt=2))):
            changed = copy.deepcopy(current)
            changed['producer'][key] = value
            changed['producer_id'] = native.digest(changed['producer'])
            with self.assertRaises(ValueError):
                native.admit_objects(changed, rows)
        wrong_root = copy.deepcopy(current)
        wrong_root['producer']['objects_root'] = str(self.root / 'other-run')
        wrong_root['producer_id'] = native.digest(wrong_root['producer'])
        for row in rows:
            row['producer_id'] = wrong_root['producer_id']
        with self.assertRaises(ValueError):
            native.admit_objects(wrong_root, rows)
        from build_current_native_kernel import prior_pass_authorization
        head = 'a' * 40
        pass_record = dict(accepted=True, current_source_commit=head, passed_source_commit='b' * 40,
            run_id=17, attempt=1, result_sha256='f' * 64, passed_case_ids=list(CASE_NAMES),
            test_sources_sha256={n: native.file_sha(Path(__file__).parent / n)
                for n in ('current_native_kernel.py', 'test_current_native_kernel.py')})
        def encoded(record):
            return base64.b64encode(json.dumps(record).encode()).decode()
        with patch.dict(os.environ, N10_BUILD_ONLY='true', N10_PASSED_BATCH_CONTEXT_B64=encoded(pass_record)):
            self.assertEqual(prior_pass_authorization({'GITHUB_SHA': head}), pass_record)
        for key, value in (('accepted', False), ('current_source_commit', 'c' * 40),
                           ('test_sources_sha256', {}), ('passed_case_ids', [])):
            changed = dict(pass_record)
            changed[key] = value
            with patch.dict(os.environ, N10_BUILD_ONLY='true', N10_PASSED_BATCH_CONTEXT_B64=encoded(changed)):
                with self.assertRaises(ValueError):
                    prior_pass_authorization({'GITHUB_SHA': head})

    def test_direct_native_link_uses_current_filelist_and_reports_failure(self):
        current, rows, *_ = fixture(self.root)
        runtime = self.root / 'compiler-runtime.a'
        aliases = self.root / 'aliases.exp'
        aliases.write_text('_fixture_alias _fixture_implementation\n')
        calls = []
        def runner(command, **kwargs):
            calls.append(command)
            filelist = Path(next(arg.split(',', 2)[2] for arg in command if arg.startswith('-Wl,-filelist,')))
            self.assertEqual(filelist.read_text().splitlines(), [r['object_path'] for r in rows])
            self.assertNotIn('force_load', ' '.join(command))
            self.assertIn(str(runtime), command)
            self.assertIn('-Wl,-alias_list,' + str(aliases), command)
            return SimpleNamespace(returncode=7, stdout='', stderr='synthetic linker failure')
        report = native.direct_link(current, rows, self.root, 'synthetic-clang', 'synthetic-sdk',
            ['-nostdlib', '-static'], aliases, dict(path=str(runtime), sha256=native.file_sha(runtime)), runner=runner)
        self.assertEqual(len(calls), 1)
        self.assertFalse(report['link_succeeded'])
        self.assertFalse(report['deployment_ready'])
        self.assertEqual(report['returncode'], 7)
        self.assertIn('synthetic linker failure', (self.root / 'kernel-link.log').read_text())
        self.assertFalse((self.root / 'current-native.macho').exists())
        with self.assertRaises(ValueError):
            native.direct_link(current, rows, self.root, 'synthetic-clang', 'synthetic-sdk', [], aliases,
                dict(path=str(runtime), sha256=native.file_sha(runtime)), runner=runner)
        self.assertEqual(len(calls), 1)


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


def main():
    from build_native_bootstrap_selection import private, write_json
    p = argparse.ArgumentParser(description=__doc__)
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
        p.error('duplicate new case selection')
    output = private(args.output)
    output.mkdir(parents=True, exist_ok=False)
    CurrentNativeKernelTests.output = output
    result = unittest.TextTestRunner(verbosity=2, resultclass=Recorded).run(
        unittest.TestSuite(CurrentNativeKernelTests(n) for n in selected))
    failed = sorted(result.failed_methods)
    receipt = dict(kind='v84-new-current-native-kernel', selected=selected,
        passed=[n for n in selected if n not in failed], failed=failed, tests_run=result.testsRun,
        success=result.wasSuccessful() and result.testsRun == len(selected) and not result.skipped,
        test_sources_sha256={n: native.file_sha(Path(__file__).parent / n)
            for n in ('current_native_kernel.py', 'test_current_native_kernel.py')},
        ci_context={k: os.environ.get(k, '') for k in ('GITHUB_SHA', 'GITHUB_RUN_ID', 'GITHUB_RUN_ATTEMPT',
            'GITHUB_JOB', 'GITHUB_WORKFLOW_REF', 'GITHUB_WORKFLOW_SHA')}, old_suites_executed=0, device_operations=[])
    write_json(output / 'result.json', receipt)
    return 0 if receipt['success'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
