"""Exactly two NEW synthetic cases, one shared-helper compile/process; CI only."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import unittest

import linux_data_carrier as carrier
from decode_reservation import checksum

HERE = Path(__file__).resolve().parent
IDENTITY, CYCLE, BOOT, OTHER = '1'*32, '2'*32, '3'*32, '4'*32
BANNER = 'Linux version 4.14.113-v99-compare-synthetic fixture-only'
OUTPUT = None
METHODS = ('test_native_compare_capture_format_and_clear', 'test_closed_host_pair_and_legacy_refusal')


def framed(marker, body, boot=BOOT):
    return f'N10BOOTLINK2 boot={boot} {marker} {body} checksum={checksum(body.encode()):08x}'


def data_line(status='carrier_mismatch', logical=4000, rc=0):
    body = (f'id={IDENTITY} cycle={CYCLE} kind=result source={carrier.MODE} status={status} '
            f'carrier={(logical+2047)//2048*2048} logical={logical} carrier_rc={rc} '
            'stream=0 payload=0 consumed=0 written=0 calls=0 '
            f'digest={"0"*64} reasons=00000000 expectations=1 captures=1 retained=1 ownership=0 executed=0')
    return framed('N10DATA1', body)


def compare_line(**changes):
    row = dict(id=IDENTITY, cycle=CYCLE, kind='compare', source=carrier.MODE,
               phase='carrier_integrity', state='compared', logical='4000', actual='11'*32,
               expected='22'*32, equal='0', ownership='0', executed='0')
    row.update(changes)
    return framed('N10DATACMP1', ' '.join(f'{key}={value}' for key, value in row.items()))


def full_log(compare):
    arm = [framed('N10RET1', f'id={IDENTITY} cycle={CYCLE} phase=0 seq={i} delay_ms=90000 status=0') for i in (0,1)]
    startup = [f'N10ROUTE2 id={IDENTITY} boot={BOOT} cycle={CYCLE} route=builtin exec_attempt=1',
               f'N10INIT2 id={IDENTITY} boot={BOOT} cycle={CYCLE} route=builtin started=1']
    request = [framed('N10RET1', f'id={IDENTITY} cycle={CYCLE} phase=1 seq={i} delay_ms=90000 status=0') for i in (0,1)]
    return ('\n'.join(['[    0.000000] '+BANNER,*arm,*startup,data_line(),*compare,*request])+'\n').encode('ascii')


class CarrierCompareEvidenceTests(unittest.TestCase):
    compiles = 0
    fixture_processes = 0

    @classmethod
    def setUpClass(cls):
        cls.fixture = OUTPUT/'compare-evidence-fixture'
        command = ['clang-14','-std=c11','-O2','-Wall','-Wextra','-Werror',
                   str(HERE/'linux_data_compare_evidence_fixture.c'),'-o',str(cls.fixture)]
        cls.compiles += 1
        (OUTPUT/'fixture-command.json').write_text(json.dumps(command,indent=2)+'\n')
        result = subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=120)
        (OUTPUT/'fixture-compile.log').write_bytes(result.stdout)
        if result.returncode:
            raise RuntimeError('NEW shared comparison helper fixture compilation failed')

    def test_native_compare_capture_format_and_clear(self):
        type(self).fixture_processes += 1
        result = subprocess.run([str(self.fixture)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=30)
        (OUTPUT/'fixture.stdout').write_bytes(result.stdout)
        (OUTPUT/'fixture.stderr').write_bytes(result.stderr)
        self.assertEqual(result.returncode,0)
        output = json.loads(result.stdout)
        self.assertEqual((output['hash_calls'],output['decoder_calls']), (0,0))
        self.assertEqual(output['short_buffer_rejected'],1)
        self.assertEqual([row['name'] for row in output['cases']],['unequal','equal','unavailable','maximum'])
        for row in output['cases']:
            with self.subTest(case=row['name']):
                self.assertEqual((row['copied'],row['scratch_cleared'],row['cleared']),(1,1,1))
                self.assertLessEqual(row['length'],383)
                body = row['frame'].split('N10DATACMP1 ',1)[1].rsplit(' checksum=',1)[0]
                self.assertEqual(len(body),row['length'])
                logical = 67108864 if row['name']=='maximum' else 0 if row['name']=='unavailable' else 4000
                status = 'carrier_mismatch' if row['name']=='unequal' else 'header' if row['name']=='equal' else 'carrier_crypto'
                legacy = data_line(status,logical,rc=-5 if status=='carrier_crypto' else 0)
                parsed = carrier.decode(legacy,IDENTITY,CYCLE)
                compared = carrier.decode_compare(legacy+'\n'+row['frame'],IDENTITY,CYCLE,parsed,required=True)
                self.assertEqual(compared['comparison_observed'],row['name'] in ('unequal','equal'))
                self.assertEqual(compared['equal'],False if row['name']=='unequal' else True if row['name']=='equal' else None)
                self.assertEqual(compared['actual_sha256'],'11'*32 if row['name'] in ('unequal','equal') else '0'*64)
                self.assertEqual(compared['expected_sha256'],'22'*32 if row['name']=='unequal' else '11'*32 if row['name']=='equal' else '0'*64)

    def test_closed_host_pair_and_legacy_refusal(self):
        legacy = data_line()
        parsed = carrier.decode(legacy,IDENTITY,CYCLE)
        self.assertEqual(carrier.decode_compare(legacy,IDENTITY,CYCLE,parsed),
                         dict(schema=None,state='unsupported',comparison_observed=False))
        with self.assertRaisesRegex(ValueError,'declared DATA comparison frame missing'):
            carrier.decode_compare(legacy,IDENTITY,CYCLE,parsed,required=True)
        with self.assertRaises(carrier.ComponentObservationError) as failure:
            carrier.decode_selected(full_log([compare_line()]),BANNER,IDENTITY,CYCLE,
                                    expected=dict(data_compare_schema=carrier.COMPARE_SCHEMA))
        components = failure.exception.component_evidence
        self.assertFalse(components['functional_acceptance'])
        self.assertFalse(components['hardware_return_proven_by_frames'])
        self.assertEqual(components['pid1_validation'],'not_checked')
        self.assertFalse(components['data']['passed'])
        self.assertEqual(components['data_phase'],'carrier_integrity')
        self.assertTrue(components['carrier_comparison']['comparison_observed'])
        self.assertFalse(components['carrier_comparison']['equal'])
        with self.assertRaises(carrier.ComponentObservationError) as missing:
            carrier.decode_selected(full_log([]),BANNER,IDENTITY,CYCLE,
                                    expected=dict(data_compare_schema=carrier.COMPARE_SCHEMA))
        self.assertNotIn('carrier_comparison',missing.exception.component_evidence)
        good = compare_line()
        malformed = {
            'duplicate': good+'\n'+good,
            'checksum': good[:-1]+('0' if good[-1]!='0' else '1'),
            'id': compare_line(id=OTHER), 'cycle': compare_line(cycle=OTHER),
            'boot': good.replace(f'boot={BOOT}',f'boot={OTHER}'),
            'logical': compare_line(logical='4001'), 'noncanonical': compare_line(logical='04000'),
            'oversized': good.replace(' kind=compare',' kind='+'x'*384),
            'unknown_key': compare_line(extra='1'), 'trailing': good+' extra=1',
            'nonclaim': compare_line(executed='1'), 'state': compare_line(state='unknown'),
            'equal_inconsistent': compare_line(equal='1'),
            'phase_inconsistent': compare_line(actual='11'*32,expected='11'*32,equal='1'),
            'unavailable_inconsistent': compare_line(state='unavailable',actual='0'*64,expected='0'*64,equal='na'),
            'unavailable_nonzero': compare_line(state='unavailable',equal='na'),
        }
        for label, line in malformed.items():
            with self.subTest(case=label), self.assertRaises(ValueError):
                carrier.decode_compare(legacy+'\n'+line,IDENTITY,CYCLE,parsed,required=True)
        with self.assertRaisesRegex(ValueError,'order'):
            carrier.decode_compare(good+'\n'+legacy,IDENTITY,CYCLE,parsed,required=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    OUTPUT = args.output
    OUTPUT.mkdir(parents=True,exist_ok=False)
    inputs = ('test_v99_carrier_compare_evidence.py','linux_data_compare_evidence_fixture.c',
              'linux_data_compare_evidence.h','linux_data_carrier.c','linux_data_carrier_composition.c',
              'linux_data_carrier.py','sha256_kat_device_profile.py','builtin_init_profile.py')
    pins = {name:hashlib.sha256((HERE/name).read_bytes()).hexdigest() for name in inputs}
    (OUTPUT/'source-sha256.json').write_text(json.dumps(pins,indent=2)+'\n')
    suite = unittest.TestSuite(CarrierCompareEvidenceTests(method) for method in METHODS)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    (OUTPUT/'result.json').write_text(json.dumps(dict(schema='v99-new-compare-tests-v1',
        selected=list(METHODS),run=result.testsRun,failures=len(result.failures),errors=len(result.errors),
        passed=result.wasSuccessful(),fixture_compiles=CarrierCompareEvidenceTests.compiles,
        fixture_processes=CarrierCompareEvidenceTests.fixture_processes,
        real_input_reads=0,hash_executions=0,payload_decoder_executions=0,old_test_methods_run=0),indent=2)+'\n')
    raise SystemExit(0 if result.wasSuccessful() else 1)
