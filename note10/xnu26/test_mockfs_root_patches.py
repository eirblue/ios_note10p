"""Only the new MOCKFS memory-root overlay: 0016..0020 on a fresh pinned series13 checkout; no compile."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import unittest

import prepare_mockfs_root as mockfs_scope
from build_native_bootstrap_selection import run
from prepare_native_bootstrap_selection import COMMIT

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SOURCES = ('test_mockfs_root_patches.py', 'prepare_mockfs_root.py', 'patches/series',
           *('patches/' + row[0] for row in mockfs_scope.OVERLAY))
CASE_IDS = ('test_overlay_applies_on_pinned_series13_with_exact_pre_and_post_images',)


class MockfsRootPatchTests(unittest.TestCase):
    observations = []

    def test_overlay_applies_on_pinned_series13_with_exact_pre_and_post_images(self):
        source = self.work / 'source'
        source.mkdir()
        run(['git', 'init', '-q'], source, self.output / 'source-init.log')
        run(['git', 'fetch', '--depth=1', 'https://github.com/apple-oss-distributions/xnu.git', COMMIT],
            source, self.output / 'source-fetch.log')
        run(['git', 'checkout', '-q', '--detach', 'FETCH_HEAD'], source, self.output / 'source-checkout.log')
        self.assertEqual(subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=source).decode().strip(), COMMIT)
        patches = ROOT / 'note10/xnu26/patches'
        names = [s.strip() for s in (patches / 'series').read_text().splitlines() if s.strip()]
        self.assertEqual(len(names), 13)
        for n, name in enumerate(names):
            run(['git', '-c', 'core.autocrlf=false', 'apply', patches / name], source,
                self.output / ('series-' + str(n + 1) + '.log'))
        observation = mockfs_scope.apply(source, self.output)
        self.assertEqual(observation, mockfs_scope.proof())
        type(self).observations.append(observation)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--work', type=Path, required=True)
    p.add_argument('--case', action='append', choices=CASE_IDS)
    a = p.parse_args()
    out, work, private = a.output.resolve(), a.work.resolve(), (ROOT / 'note10/private').resolve()
    for path in (out, work):
        if path == private or not path.is_relative_to(private) or path.exists():
            p.error('fresh private output and work roots required')
    if out.is_relative_to(work) or work.is_relative_to(out):
        p.error('disjoint output and work roots required')
    selected = a.case if a.case is not None else json.loads(os.environ.get('N10_CI_CASE_JSON', '[]'))
    if (type(selected) is not list or not selected or len(selected) != len(set(selected)) or
            any(n not in CASE_IDS for n in selected)):
        p.error('explicit closed NEW case selection required')
    out.mkdir(parents=True)
    work.mkdir(parents=True)
    MockfsRootPatchTests.output, MockfsRootPatchTests.work = out, work
    result = unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(MockfsRootPatchTests(n) for n in selected))
    failed = {t._testMethodName for t, _ in result.failures + result.errors if hasattr(t, '_testMethodName')}
    complete = result.testsRun == len(selected)
    report = dict(kind='v340-new-mockfs-root-overlay', selected=selected,
        passed=[n for n in selected if n not in failed] if complete else [], tests_run=result.testsRun,
        failed=sorted(failed), success=result.wasSuccessful() and complete and not result.skipped,
        observations=MockfsRootPatchTests.observations, public_source_commit=COMMIT,
        source_sha256={n: hashlib.sha256((HERE / n).read_bytes()).hexdigest() for n in SOURCES},
        ci_context={k: os.environ.get(k, '') for k in ('GITHUB_SHA', 'GITHUB_RUN_ID', 'GITHUB_RUN_ATTEMPT',
            'GITHUB_JOB', 'GITHUB_WORKFLOW_REF', 'GITHUB_WORKFLOW_SHA', 'GITHUB_REPOSITORY')},
        compiled=False, PC_only=True, physical_ready=False, whole_XNU_kernel_entry_executed=False,
        hardware_XNU_executed=False, old_tests_executed=0, device_operations=[])
    (out / 'result.json').write_text(json.dumps(report, indent=2) + '\n')
    return 0 if report['success'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
