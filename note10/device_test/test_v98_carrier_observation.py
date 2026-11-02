"""Two NEW synthetic host reporting cases; no native execution or real inputs."""
import argparse
import json
from pathlib import Path
import unittest

import builtin_init_profile as profile
import linux_data_carrier as carrier
from decode_reservation import checksum
from sha256_kat_device_profile import log_probe_command

IDENTITY, CYCLE, BOOT, OTHER = '1'*32, '2'*32, '3'*32, '4'*32
BANNER = 'Linux version 4.14.113-v98-synthetic-observation fixture-only'
OUTPUT = None


def frame(tag, body, boot=BOOT):
    return f'N10BOOTLINK2 boot={boot} {tag} {body} checksum={checksum(body.encode()):08x}\n'


def synthetic_log(variant='complete'):
    arm = ''.join(frame('N10RET1', f'id={IDENTITY} cycle={CYCLE} phase=0 seq={i} delay_ms=90000 status=0')
                  for i in (0, 1))
    startup = (f'N10ROUTE2 id={IDENTITY} boot={BOOT} cycle={CYCLE} route=builtin exec_attempt=1\n'
               f'N10INIT2 id={IDENTITY} boot={BOOT} cycle={CYCLE} route=builtin started=1\n')
    body = (f'id={IDENTITY} cycle={OTHER if variant == "wrong_data_cycle" else CYCLE} '
            'kind=result source=image-slot-logical-v2 status=carrier_mismatch '
            'carrier=4096 logical=4000 carrier_rc=0 stream=0 payload=0 consumed=0 written=0 calls=0 '
            f'digest={"0"*64} reasons=00000000 expectations=1 captures=1 retained=1 ownership=0 executed=0')
    data = frame('N10DATA1', body, OTHER if variant == 'wrong_data_boot' else BOOT)
    request = ''.join(frame('N10RET1', f'id={IDENTITY} cycle={CYCLE} phase=1 seq={i} delay_ms=90000 status=0')
                      for i in (0, 1))
    if variant == 'malformed_data':
        data = data.replace('carrier_rc=0', 'carrier_rc=1')  # checksum now differs
    if variant == 'wrong_pid1_boot':
        startup = startup.replace(f'boot={BOOT}', f'boot={OTHER}')
    if variant == 'missing_pid1':
        startup = startup.splitlines(keepends=True)[0]
    if variant == 'wrong_return_cycle':
        request = request.replace(f'cycle={CYCLE}', f'cycle={OTHER}')
    return ('[    0.000000] '+BANNER+'\n'+arm+startup+data+request).encode('ascii')


class SyntheticTransport:
    def __init__(self, raw):
        self.raw, self.calls = raw, []

    def call(self, *args, **kwargs):
        self.calls.append(args)
        for index, (_, remote) in enumerate(profile.LOGS):
            if args == ('shell', '-T', log_probe_command(remote)):
                return b'N10KAT_READABLE\n' if index == 0 else b'N10KAT_ABSENT\n'
            if index == 0 and args == ('exec-out', 'cat', remote):
                return self.raw
        raise AssertionError('unexpected synthetic transport command')


class CarrierObservationTests(unittest.TestCase):
    def capture(self, variant):
        out = OUTPUT/self._testMethodName/variant
        out.mkdir(parents=True)
        transport = SyntheticTransport(synthetic_log(variant))
        bound = dict(device_profile=carrier.PROFILE, kernel_banner=BANNER, build_evidence_id=IDENTITY)
        result = profile.snapshot(transport, out, bound, CYCLE, decode_fn=carrier.decode_selected)
        self.assertEqual(len(transport.calls), 4)  # three distinct probes, one capture
        self.assertFalse(result['diagnostic_passed'])
        self.assertEqual(result['observations'], [])
        self.assertEqual(result['log_selections'], {})
        self.assertFalse(result['hardware_return_proven_by_frames'])
        self.assertNotIn('automatic_return_evidence', result)
        saved = json.loads((out/'result.json').read_text())
        self.assertEqual(saved, result)
        components = result['rejected_component_observations'][0]['components']
        self.assertFalse(components['functional_acceptance'])
        self.assertFalse(components['hardware_return_proven_by_frames'])
        return result, components

    def test_integrity_refusal_retains_components_without_acceptance(self):
        result, components = self.capture('complete')
        self.assertIn('phase=carrier_integrity status=carrier_mismatch', result['errors'][0])
        self.assertNotIn('functional decode failed', result['errors'][0])
        self.assertEqual(components['data_phase'], 'carrier_integrity')
        self.assertEqual((components['data']['carrier_rc'], components['data']['reasons']), (0, 0))
        self.assertFalse(components['data']['passed'])
        self.assertEqual(components['data']['calls'], 0)
        self.assertEqual(components['return_validation'], 'validated_request_records')
        self.assertEqual(components['auto_return_records']['arm_frames'], 2)
        self.assertEqual(components['auto_return_records']['request_frames'], 2)
        self.assertFalse(components['auto_return_records']['hardware_recovery_reentry_verified'])
        self.assertEqual(components['pid1_validation'], 'not_checked')
        self.assertEqual(components['return_boot_association'], 'not_checked')
        self.assertEqual(components['structural_presence'], dict(validation='presence_only',
            route_same_boot_markers=1, route_other_boot_markers=0,
            pid1_same_boot_markers=1, pid1_other_boot_markers=0))

    def test_invalid_or_unassociated_components_never_gain_acceptance(self):
        for variant in ('malformed_data', 'wrong_data_cycle', 'wrong_data_boot',
                        'wrong_pid1_boot', 'missing_pid1', 'wrong_return_cycle'):
            with self.subTest(variant=variant):
                _, components = self.capture(variant)
                self.assertEqual(components['pid1_validation'], 'not_checked')
                self.assertEqual(components['return_boot_association'], 'not_checked')
                if variant in ('malformed_data', 'wrong_data_cycle', 'wrong_return_cycle'):
                    self.assertNotIn('data', components)
                    self.assertNotIn('structural_presence', components)
                else:
                    self.assertEqual(components['structural_presence']['pid1_same_boot_markers'], 0)
                    self.assertEqual(components['structural_presence']['validation'], 'presence_only')
                if variant == 'wrong_return_cycle':
                    self.assertEqual(components['return_validation'], 'not_checked')
                    self.assertNotIn('auto_return_records', components)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    OUTPUT = args.output
    OUTPUT.mkdir(parents=True, exist_ok=False)
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(CarrierObservationTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    (OUTPUT/'result.json').write_text(json.dumps(dict(schema='v98-new-host-observation-tests-v1',
        selected=2, run=result.testsRun, failures=len(result.failures), errors=len(result.errors),
        passed=result.wasSuccessful(), real_logs_read=0, native_executions=0), indent=2)+'\n')
    raise SystemExit(0 if result.wasSuccessful() else 1)
