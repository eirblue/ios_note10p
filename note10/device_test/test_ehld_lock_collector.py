"""Exercise the collector with real prior/EHLD wire decoders and fake ADB.

Older audit bindings/decoders are isolated here; their own models validate them.
No device calls or writes occur in these fixtures.
"""
import argparse
from contextlib import ExitStack
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import test_collect_reservation as fixtures
from decode_reservation import checksum
from test_cpu_cache_decode import summary, snapshots
from test_pm_timer_contract import pm, timers

CASES = ['valid-39-preserves-prior-38', 'missing-malformed-mutation-fail',
         'unrequested-fail', 'package-scope-version-fail']

DEPENDENCIES = (
    'test_collect_reservation.py', 'test_cpu_cache_decode.py',
    'test_cpu_cache_native.py', 'test_pm_timer_contract.py',
    'prepare_pm_diagnostic.py',
)


def frame(tag, fields):
    body = ' '.join(f'{key}={value}' for key, value in fields.items())
    return f'{tag} {body} checksum={checksum(body.encode("ascii")):08x}\n'


def prior_frames(identity, running):
    text = ''
    for copy in (0, 1):
        row = dict(id=identity, copy=copy, generation=1, index=0, count=1,
                   kind=6, priority=0, valid=3, a=running, b=1,
                   c=0, d=0, e=0, f=0, g=0, h=0)
        text += frame('N10PRR1', row)
        for phase in range(3):
            gic = dict(id=identity, copy=copy, generation=1, phase=phase,
                       enable=0, active=0, config0=0, config1=0)
            gic.update({f'p{i}': 0 for i in range(8)})
            gic['matches'] = 1
            text += frame('N10PRG1', gic)
        text += frame('N10PRQ1', dict(id=identity, copy=copy, generation=1,
                      status=0, count=1, complete=1, gic_complete=1))
    return text


class EHLDCollectorTests(unittest.TestCase):
    def run_case(self, *, active=True, include=True, busy=False, old=-1,
                 malformed=False, changes=None, missing_copy=False,
                 bad_checksum=False, duplicate=False, paired_changes=None):
        fixture = fixtures.CollectorTests()
        identity = fixture.identity
        log = (fixture.frame(0) + fixture.frame(1) + fixture.access_frame(0) +
               fixture.access_frame(1) + fixture.xnu_frame(0) + fixture.xnu_frame(1) +
               summary(0) + summary(1) + snapshots() + pm(0) + pm(1) + timers())
        log += prior_frames(identity, old)
        if include:
            for copy in (0, 1):
                if missing_copy and copy == 1:
                    continue
                row = dict(id=identity, copy=copy, generation=1, index=0,
                           chain_count=1, lock_available=int(not busy),
                           running_valid=int(not busy), running=0 if busy else int(bool(old)))
                row.update(changes or {})
                encoded = frame('N10ELM1', row)
                if bad_checksum:
                    encoded = encoded.replace('checksum=', 'checksum=0', 1)
                log += encoded
                if duplicate and copy == 0:
                    log += encoded
                log += frame('N10ELQ1', dict(id=identity, copy=copy,
                             generation=1, status=0, row_count=1, complete=1))
        if malformed:
            log += 'N10ELX1 malformed\n'
        original = Path.read_text

        def read(path, *args, **kwargs):
            raw = original(path, *args, **kwargs)
            if path.name not in ('build-result.json', 'package-result.json'):
                return raw
            data = json.loads(raw)
            data.update(pm_preconditions_diagnostic=True, pm_preconditions_version=1,
                        pm_branch_diagnostic=True, pm_branch_version=1,
                        pmu_state_audit=True, pmu_state_audit_version=1,
                        pmu_control_audit=True, pmu_control_audit_version=1,
                        fpsimd_reference_audit=True, fpsimd_reference_audit_version=1,
                        rcu_context_audit=True, rcu_context_audit_version=1,
                        ehld_lock_audit=active, ehld_lock_audit_version=1 if active else None)
            if path.name == 'package-result.json':
                data.update(paired_changes or {})
            return json.dumps(data)

        with ExitStack() as stack:
            stack.enter_context(patch.object(Path, 'read_text', read))
            for module in ('pm_preconditions_binding', 'pm_branch_binding'):
                stack.enter_context(patch(module + '.assert_scope', return_value=True))
                stack.enter_context(patch(module + '.validate_model', return_value=True))
            for module in ('pmu_state_binding', 'pmu_control_binding',
                           'fpsimd_reference_binding', 'rcu_context_binding'):
                stack.enter_context(patch(module + '.validate', return_value=True))
            stack.enter_context(patch('ehld_lock_binding.validate', return_value=active))
            for module in ('decode_pmu_state', 'decode_pmu_control',
                           'decode_fpsimd_reference', 'decode_rcu_context'):
                stack.enter_context(patch(module + '.decode', return_value={}))
            stack.enter_context(patch('decode_pm_branch.decode', return_value={
                'cpu0_pmu_branch_audit': True, 'cpu0_gic_priority_footprint': True}))
            stack.enter_context(patch('collect_reservation.pm_completed_generation', return_value=2))
            return fixture.run_fixture(log, access=True, xnu_stage=True,
                                       cpu_cache=True, pm_timer=True)

    def test_valid_busy_and_signed_running_add_only_one_required_item(self):
        baseline = self.run_case(active=False, include=False)['evaluation_items']
        self.assertEqual(len(baseline), 38)
        for kwargs in ({'busy': True}, {'old': 0}, {'old': -1},
                       {'old': -(1 << 31)}, {'old': (1 << 31) - 1}):
            with self.subTest(**kwargs):
                result = self.run_case(**kwargs)
                self.assertTrue(result['diagnostic_passed'])
                items = dict(result['evaluation_items'])
                self.assertEqual(len(items), 39)
                self.assertEqual(items.pop('cpu0_ehld_lock_audit'),
                                 {'required': True, 'status': 'passed'})
                self.assertEqual(items, baseline)

    def test_missing_malformed_or_inconsistent_evidence_fails_required_item(self):
        cases = ({'include': False}, {'malformed': True}, {'missing_copy': True},
                 {'bad_checksum': True}, {'duplicate': True},
                 {'changes': {'generation': 2}}, {'changes': {'index': 1}},
                 {'changes': {'chain_count': 2}},
                 {'busy': True, 'changes': {'running': 1}},
                 {'busy': True, 'changes': {'running_valid': 1}},
                 {'old': -1, 'changes': {'running': 0}})
        for kwargs in cases:
            with self.subTest(**kwargs):
                result = self.run_case(**kwargs)
                self.assertFalse(result['diagnostic_passed'])
                self.assertEqual(result['evaluation_items']['cpu0_ehld_lock_audit'],
                                 {'required': True, 'status': 'failed'})
                self.assertTrue(result['decode_failures'])

    def test_disabled_rejects_unrequested_frames(self):
        result = self.run_case(active=False)
        self.assertFalse(result['diagnostic_passed'])
        self.assertNotIn('cpu0_ehld_lock_audit', result['evaluation_items'])

    def test_package_scope_or_version_mismatch_is_rejected(self):
        for changes in ({'ehld_lock_audit': False}, {'ehld_lock_audit_version': 2}):
            with self.subTest(**changes), self.assertRaisesRegex(ValueError, 'EHLD lock package'):
                self.run_case(paired_changes=changes)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--report', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    base = Path(__file__).resolve().parent
    measured = {name: hashlib.sha256((base / name).read_bytes()).hexdigest()
                for name in DEPENDENCIES}
    if bool(args.report) != bool(args.output):
        raise ValueError('report and output must be paired')
    if args.report and json.loads(args.report.read_text(encoding='utf-8')).get(
            'ehld_lock_collector_dependencies_sha256') != measured:
        raise ValueError('collector fixture dependencies differ from build report')
    result = unittest.main(argv=[__file__], exit=False)
    if not result.result.wasSuccessful():
        raise SystemExit(1)
    if args.output:
        args.output.mkdir(parents=True, exist_ok=False)
        proof = dict(passed=True, hardware_verified=False,
                     cases=CASES,
                     dependencies_sha256=measured,
                     harness_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
        (args.output / 'result.json').write_text(json.dumps(proof, indent=2) + '\n',
                                                encoding='utf-8', newline='\n')
