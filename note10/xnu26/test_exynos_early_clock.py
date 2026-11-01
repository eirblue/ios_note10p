"""One host fixture compile; only the new Exynos early-clock C paths."""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import unittest

from prepare_exynos_early_clock import PATCH_NAME, COMPONENT_SHA256, PATCH_SHA256, embedded_component

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PRIVATE = ROOT / 'note10/private'
CASE_NAMES = ('test_owned_declaration_without_arm_io_and_consumer_boundaries',
              'test_boot_cpu_state_selection_rejects_missing_malformed_and_ambiguous',
              'test_selected_clock_width_range_and_critical_duplicates_fail_before_commit')
TEST_INPUTS = ('exynos_early_clock.c', 'exynos_early_clock_fixture.c', 'exynos_early_clock_fixture.h',
               'test_exynos_early_clock.py', 'prepare_exynos_early_clock.py', 'patches/' + PATCH_NAME)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def source_pins():
    return {name: sha(HERE / name) for name in TEST_INPUTS}


def private(path):
    path = Path(path).absolute()
    if path.resolve() != path or not path.is_relative_to(PRIVATE) or path == PRIVATE:
        raise ValueError('ordinary private output child required')
    return path


def retained_pass():
    raw = os.environ.get('N10_CLOCK_PASS_CONTEXT_B64', '')
    if len(raw) > 16384:
        raise ValueError('bounded Root clock PASS context required')
    record = json.loads(base64.b64decode(raw, validate=True))
    keys = {'accepted', 'current_source_commit', 'passed_source_commit', 'run_id', 'attempt',
            'result_sha256', 'test_sources_sha256', 'passed_case_ids'}
    head = os.environ.get('GITHUB_SHA', '')
    if (set(record) != keys or record['accepted'] is not True or
        not re.fullmatch('[0-9a-f]{40}', head) or record['current_source_commit'] != head or
        not re.fullmatch('[0-9a-f]{40}', record['passed_source_commit']) or
        any(type(record[k]) is not int or record[k] < 1 for k in ('run_id', 'attempt')) or
        not re.fullmatch('[0-9a-f]{64}', record['result_sha256']) or
        record['test_sources_sha256'] != source_pins() or record['passed_case_ids'] != list(CASE_NAMES)):
        raise ValueError('Root must bind actual retained clock PASS to unchanged inputs and this source')
    return record


class ExynosEarlyClockTests(unittest.TestCase):
    output = None
    command = None
    binding = None
    fixture_compiles = 0

    @classmethod
    def setUpClass(cls):
        component = (HERE / 'exynos_early_clock.c').read_bytes()
        patch = (HERE / 'patches' / PATCH_NAME).read_bytes()
        if (hashlib.sha256(component).hexdigest() != COMPONENT_SHA256 or
            hashlib.sha256(patch).hexdigest() != PATCH_SHA256 or embedded_component(patch) != component):
            raise ValueError('kernel materialized helper must equal the tested production C bytes')
        cls.binding = dict(component_sha256=COMPONENT_SHA256, patch_sha256=PATCH_SHA256,
                           kernel_added_file_matches_tested_component=True)
        stubs = cls.output / 'thin-dt-api'
        # The fixture supplies only interface declarations/data and DT callbacks.
        # The clock algorithm is included unchanged from the production C file.
        for name in ('pexpert/pexpert.h', 'pexpert/device_tree.h', 'kern/debug.h', 'libkern/libkern.h'):
            path = stubs / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('/* host fixture API is declared by the fixture header */\n')
        compiler = shutil.which('clang')
        if not compiler:
            raise ValueError('host Clang required for the one new C fixture')
        cls.executable = cls.output / 'exynos-clock-fixture'
        cls.command = [compiler, '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror', '-I', str(stubs),
                       str(HERE / 'exynos_early_clock_fixture.c'), '-o', str(cls.executable)]
        cls.fixture_compiles += 1
        result = subprocess.run(cls.command, capture_output=True, timeout=60)
        (cls.output / 'fixture-compile.log').write_bytes(result.stdout + result.stderr)
        if result.returncode:
            raise RuntimeError('actual new production-C fixture compilation failed')

    def invoke(self, name):
        result = subprocess.run([str(self.executable), name], capture_output=True, text=True, timeout=10)
        (self.output / (name + '.log')).write_text(result.stdout + result.stderr)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(json.loads(result.stdout), dict(passed=True, synthetic=True, hardware_operations=0))

    def test_owned_declaration_without_arm_io_and_consumer_boundaries(self):
        self.invoke('valid')

    def test_boot_cpu_state_selection_rejects_missing_malformed_and_ambiguous(self):
        self.invoke('selector')

    def test_selected_clock_width_range_and_critical_duplicates_fail_before_commit(self):
        self.invoke('properties')


class Recorded(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.failed_methods, self.framework_errors = set(), []

    def addFailure(self, test, error):
        self.failed_methods.add(test._testMethodName)
        super().addFailure(test, error)

    def addError(self, test, error):
        name = getattr(test, '_testMethodName', None)
        if name:
            self.failed_methods.add(name)
        else:
            self.framework_errors.append(test.id())
        super().addError(test, error)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', required=True)
    p.add_argument('--case', action='append', choices=CASE_NAMES)
    p.add_argument('--authorize-skip', action='store_true', help='Root-bound actual clock PASS only; no test execution')
    args = p.parse_args()
    output = private(args.output)
    output.mkdir(parents=True, exist_ok=False)
    if args.authorize_skip:
        receipt = dict(kind='v85-exynos-early-clock-retained-pass', tests_executed=0,
                       retained_pass_authorization=retained_pass(), test_sources_sha256=source_pins())
        (output / 'result.json').write_text(json.dumps(receipt, indent=2) + '\n')
        return 0
    selected = args.case
    if selected is None:
        selected = json.loads(os.environ.get('N10_CI_CASE_JSON', '[]'))
        if type(selected) is not list or any(type(n) is not str or n not in CASE_NAMES for n in selected):
            p.error('closed new clock case array required')
        selected = selected or list(CASE_NAMES)
    if len(selected) != len(set(selected)):
        p.error('duplicate new clock case selection')
    ExynosEarlyClockTests.output = output
    result = unittest.TextTestRunner(verbosity=2, resultclass=Recorded).run(
        unittest.TestSuite(ExynosEarlyClockTests(n) for n in selected))
    failed = sorted(result.failed_methods)
    complete = result.testsRun == len(selected) and not result.framework_errors
    receipt = dict(kind='v85-exynos-early-clock', selected=selected, passed=[n for n in selected if n not in failed] if complete else [],
        failed=failed, tests_run=result.testsRun, framework_errors=result.framework_errors,
        success=result.wasSuccessful() and complete and not result.skipped,
        fixture_compiles=ExynosEarlyClockTests.fixture_compiles, fixture_command=ExynosEarlyClockTests.command,
        production_component_binding=ExynosEarlyClockTests.binding, test_sources_sha256=source_pins(),
        ci_context={k: os.environ.get(k, '') for k in ('GITHUB_SHA', 'GITHUB_RUN_ID', 'GITHUB_RUN_ATTEMPT',
            'GITHUB_JOB', 'GITHUB_WORKFLOW_REF', 'GITHUB_WORKFLOW_SHA')},
        synthetic=True, owned_device_input=False, actual_boot_cpu_state=False, hardware_operations=0,
        old_suites_executed=0, xnu_executed=False)
    (output / 'result.json').write_text(json.dumps(receipt, indent=2) + '\n')
    return 0 if receipt['success'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
