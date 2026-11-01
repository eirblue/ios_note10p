"""One NEW v73 batch only. No old abc/worker/native/model cases or device."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest

import sha256_stream_state as stream
import builtin_init_profile as baseline
import sha256_kat_device_profile as profile
from decode_reservation import checksum

HERE = Path(__file__).resolve().parent
ID, CYCLE, BOOT = '1'*32, '2'*32, '3'*32
BANNER = 'Linux version 4.14.113-v73-sha256-stream fixture-only'
OUTPUT = None
SELECTED = ()
CASE_NAMES = ('test_native_new_vectors', 'test_native_export_error', 'test_native_import_error',
    'test_native_state_bound', 'test_native_digest_mismatch', 'test_decoder_checksum_rejection',
    'test_decoder_cycle_rejection', 'test_decoder_missing_copy', 'test_decoder_duplicate_case',
    'test_current_boot_and_startup_binding', 'test_current_v72_chain', 'test_legacy_v72_rule_stays_closed')
CASE_IDS = tuple('StreamTests.'+n for n in CASE_NAMES)


def synthetic():
    lines = []
    for row in stream.vectors():
        for copy in (0, 1):
            body = (f'id={ID} cycle={CYCLE} case={row["case"]} copy={copy} len={row["length"]} split={row["split"]} '
                    f'statesize=104 status=0 driver_match=1 streamed=1 exported=1 imported=1 resumed=1 '
                    f'direct={row["digest"]} restored={row["digest"]}')
            lines.append(f'N10BOOTLINK2 boot={BOOT} N10SHASTREAM1 {body} checksum={checksum(body.encode()):08x}\n')
    return ''.join(lines)


class StreamTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        OUTPUT.mkdir(parents=True)
        if any('.test_native_' in name for name in SELECTED):
            folder = OUTPUT/'native'; folder.mkdir()
            (folder/'sha256_stream_vectors.h').write_bytes(stream.vector_header())
            (folder/'note10_sha256_kat_id.h').write_text('#define N10_SHA256_KAT_ID "'+ID+'"\n', encoding='ascii')
            cls.binary = folder/'stream-fixture'
            argv = ['gcc', '-std=c99', '-Wall', '-Wextra', '-Werror', '-Wno-deprecated-declarations',
                '-I'+str(HERE), '-I'+str(folder), str(HERE/'sha256_stream_fixture.c'), '-lcrypto', '-o', str(cls.binary)]
            result = subprocess.run(argv, capture_output=True, timeout=60)
            (folder/'compile.stdout').write_bytes(result.stdout); (folder/'compile.stderr').write_bytes(result.stderr)
            profile.save(folder/'compile.json', dict(argv=argv, returncode=result.returncode))
            if result.returncode: raise RuntimeError('NEW stream native fixture compile failed')

    def native(self, scenario):
        folder = OUTPUT/self._testMethodName; folder.mkdir()
        result = subprocess.run([str(self.binary), scenario], capture_output=True, timeout=10)
        (folder/'stdout.bin').write_bytes(result.stdout); (folder/'stderr.bin').write_bytes(result.stderr)
        profile.save(folder/'return.json', dict(returncode=result.returncode, scenario=scenario))
        self.assertEqual(result.returncode, 0)
        return stream.decode(result.stdout.decode('ascii'), ID, CYCLE)

    def test_native_new_vectors(self):
        observed = self.native('success'); self.assertTrue(observed['passed'])
        for row, vector in zip(observed['cases'], stream.vectors()):
            message = bytes((37*i+11)&255 for i in range(vector['length']))
            self.assertEqual(row['direct'], hashlib.sha256(message).hexdigest())
            self.assertEqual(row['restored'], row['direct'])

    def test_native_export_error(self):
        observed = self.native('export-error'); self.assertFalse(observed['passed'])
        self.assertEqual(observed['cases'][2]['exported'], 0)

    def test_native_import_error(self):
        observed = self.native('import-error'); self.assertFalse(observed['passed'])
        self.assertEqual(observed['cases'][3]['imported'], 0)

    def test_native_state_bound(self):
        observed = self.native('state-bound'); self.assertFalse(observed['passed'])
        self.assertTrue(all(row['resumed'] == 0 for row in observed['cases']))

    def test_native_digest_mismatch(self):
        observed = self.native('digest-mismatch'); self.assertFalse(observed['passed'])
        self.assertEqual(observed['cases'][2]['status'], -74)

    def test_decoder_checksum_rejection(self):
        with self.assertRaises(ValueError): stream.decode(synthetic().replace('status=0', 'status=-5', 1), ID, CYCLE)

    def test_decoder_cycle_rejection(self):
        with self.assertRaises(ValueError): stream.decode(synthetic(), ID, '4'*32)

    def test_decoder_missing_copy(self):
        with self.assertRaises(ValueError): stream.decode(''.join(synthetic().splitlines(keepends=True)[:-1]), ID, CYCLE)

    def test_decoder_duplicate_case(self):
        lines = synthetic().splitlines(keepends=True); lines[-1] = lines[0]
        with self.assertRaises(ValueError): stream.decode(''.join(lines), ID, CYCLE)

    def test_current_boot_and_startup_binding(self):
        def ret(phase):
            out = ''
            for seq in (0, 1):
                body = f'id={ID} cycle={CYCLE} phase={phase} seq={seq} delay_ms=90000 status=0'
                out += f'N10BOOTLINK2 boot={BOOT} N10RET1 {body} checksum={checksum(body.encode()):08x}\n'
            return out
        start = f'N10ROUTE2 id={ID} boot={BOOT} cycle={CYCLE} route=builtin exec_attempt=1\nN10INIT2 id={ID} boot={BOOT} cycle={CYCLE} route=builtin started=1\n'
        data = ('[    0.000000] '+BANNER+'\n'+ret(0)+start+synthetic()+ret(1)).encode()
        _, observed = stream.decode_selected(data, BANNER, ID, CYCLE)
        self.assertTrue(observed['kat']['passed'])
        with self.assertRaises(ValueError): stream.decode_selected(data.replace(b'N10INIT2', b'MISSING2'), BANNER, ID, CYCLE)

    def test_current_v72_chain(self):
        pair = dict(device_profile=profile.BUILTIN_PROFILE, source_head=profile.V72_HOST_HEAD,
                    host_profile_source_head=profile.V72_HOST_HEAD)
        plan = dict(device_profile=stream.PROFILE, current_boot_payload_sha256='a'*64)
        baseline.current_boot_binding(plan, pair, {'payload_sha256':'a'*64})
        pair['device_profile'] = profile.PROFILE
        with self.assertRaises(ValueError): baseline.current_boot_binding(plan, pair, {'payload_sha256':'a'*64})

    def test_legacy_v72_rule_stays_closed(self):
        pair = dict(device_profile=profile.BUILTIN_PROFILE, source_head=profile.V72_HOST_HEAD,
                    host_profile_source_head=profile.V72_HOST_HEAD)
        with self.assertRaises(ValueError):
            baseline.current_boot_binding({'device_profile':profile.BUILTIN_PROFILE, 'current_boot_payload_sha256':'a'*64}, pair, {'payload_sha256':'a'*64})


class Recorded(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs); self.passed_ids, self.failed_ids, self.framework_errors = [], [], []
    def addSuccess(self, test):
        self.passed_ids.append('StreamTests.'+test._testMethodName); super().addSuccess(test)
    def addFailure(self, test, error):
        self.failed_ids.append('StreamTests.'+test._testMethodName); super().addFailure(test, error)
    def addError(self, test, error):
        target = self.failed_ids if isinstance(test, StreamTests) else self.framework_errors
        target.append('StreamTests.'+test._testMethodName if isinstance(test, StreamTests) else test.id())
        super().addError(test, error)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--case', action='append', choices=CASE_IDS)
    args = parser.parse_args(); OUTPUT = args.output.resolve(); SELECTED = tuple(args.case or CASE_IDS)
    private = (HERE.parent/'private').resolve()
    if OUTPUT == private or not OUTPUT.is_relative_to(private) or OUTPUT.exists() or len(set(SELECTED)) != len(SELECTED):
        raise ValueError('fresh private output and unique NEW case allowlist required')
    pins = {n: profile.sha(HERE/n) for n in (*stream.SOURCES, 'builtin_init_profile.py', 'sha256_kat_device_profile.py')}
    result = unittest.TextTestRunner(verbosity=2, resultclass=Recorded).run(unittest.TestSuite(StreamTests(n.split('.')[1]) for n in SELECTED))
    stable = pins == {n:profile.sha(HERE/n) for n in pins}
    OUTPUT.mkdir(parents=True, exist_ok=True)
    profile.save(OUTPUT/'result.json', dict(schema=1, selected_ids=SELECTED, passed_ids=result.passed_ids,
        failed_ids=result.failed_ids, framework_errors=result.framework_errors, tests_run=result.testsRun,
        failures=len(result.failures), errors=len(result.errors), suite_success=result.wasSuccessful(),
        source_sha256=pins, source_stable=stable, old_suites_invoked=0, device_operations=[]))
    sys.exit(0 if result.wasSuccessful() and stable else 1)
