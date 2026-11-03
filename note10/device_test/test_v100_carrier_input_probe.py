"""Fixed NEW2/fixture1 late-prefix batch; synthetic bytes and metadata only."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import unittest

import builtin_init_profile as builtin
import linux_data_carrier as carrier
import sha256_kat_device_profile as profile
from decode_reservation import checksum

HERE = Path(__file__).resolve().parent
IDENTITY, CYCLE, BOOT, OTHER = '1'*32, '2'*32, '3'*32, '4'*32
BANNER = 'Linux version 4.14.113-v100-prefix-synthetic fixture-only'
OUTPUT = None
METHODS = ('test_shared_late_prefix_capture_format_and_clear', 'test_closed_versions_refusal_and_exact_current_v99_chain')


def framed(marker, body, boot=BOOT):
    return f'N10BOOTLINK2 boot={boot} {marker} {body} checksum={checksum(body.encode()):08x}'


def data_line(status='carrier_mismatch',logical=4000,rc=0):
    return framed('N10DATA1',
        f'id={IDENTITY} cycle={CYCLE} kind=result source={carrier.MODE} status={status} '
        f'carrier={(logical+2047)//2048*2048} logical={logical} carrier_rc={rc} '
        f'stream=0 payload=0 consumed=0 written=0 calls=0 digest={"0"*64} '
        'reasons=00000000 expectations=1 captures=1 retained=1 ownership=0 executed=0')


def compare_line(version='2',**changes):
    row = dict(id=IDENTITY,cycle=CYCLE,kind='compare',source=carrier.MODE,phase='carrier_integrity',
               state='compared',logical='4000',actual='11'*32,expected='22'*32,equal='0')
    if version == '2': row.update(sampled='1',magic_match='1',prefix_zero='0')
    row.update(ownership='0',executed='0')
    row.update(changes)
    return framed('N10DATACMP'+version,' '.join(f'{key}={value}' for key,value in row.items()))


def retained_v1():
    return dict(device_profile=profile.DATA_PROFILE,source_head=profile.V99_PROFILE_ORIGIN_HEAD,
        host_profile_source_head=profile.V99_PROFILE_ORIGIN_HEAD,
        host_profile_source_sha256=dict(profile.V99_PROFILE_ORIGIN_PINS),data_compare_schema=carrier.COMPARE_SCHEMA_V1)


def retained_package_v1():
    # Synthetic complete package-scope metadata, using only authenticated public
    # origin pins. No retained package, BOOT, ZIP or Image is opened.
    row = retained_v1()
    for key in profile.FIELDS:
        row.setdefault(key,'a'*64)
    for key in builtin.EXTRA_FIELDS:
        row[key] = 'b'*64
    row.update(build_evidence_id=IDENTITY,kernel_banner='Linux version 4.14.113-v91-trusted-logical synthetic',
        data_carrier_stage=carrier.STAGE,data_relative_placement_admitted=True,raw_input_binding=False,
        data_expectation_mode=carrier.MODE,data_expectation_slot={},image_expectation_patched=True,
        data_manifest_sha256='c'*64,data_carrier_sha256='d'*64,data_payload_sha256='e'*64,
        data_carrier_bytes=4000,data_payload_bytes=1024,auto_return_diagnostic=True,auto_cycle_token=CYCLE)
    return row


def full_log(companion):
    arm = [framed('N10RET1',f'id={IDENTITY} cycle={CYCLE} phase=0 seq={i} delay_ms=90000 status=0') for i in (0,1)]
    startup = [f'N10ROUTE2 id={IDENTITY} boot={BOOT} cycle={CYCLE} route=builtin exec_attempt=1',
               f'N10INIT2 id={IDENTITY} boot={BOOT} cycle={CYCLE} route=builtin started=1']
    request = [framed('N10RET1',f'id={IDENTITY} cycle={CYCLE} phase=1 seq={i} delay_ms=90000 status=0') for i in (0,1)]
    return ('\n'.join(['[    0.000000] '+BANNER,*arm,*startup,data_line(),*companion,*request])+'\n').encode('ascii')


class CarrierInputProbeTests(unittest.TestCase):
    compiles = 0
    fixture_processes = 0

    @classmethod
    def setUpClass(cls):
        cls.fixture = OUTPUT/'late-input-probe-fixture'
        command = ['clang-14','-std=c11','-O2','-Wall','-Wextra','-Werror',
                   str(HERE/'linux_data_input_probe_fixture.c'),'-o',str(cls.fixture)]
        cls.compiles += 1
        (OUTPUT/'fixture-command.json').write_text(json.dumps(command,indent=2)+'\n')
        result = subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=120)
        (OUTPUT/'fixture-compile.log').write_bytes(result.stdout)
        if result.returncode: raise RuntimeError('NEW late-prefix helper fixture compilation failed')

    def test_shared_late_prefix_capture_format_and_clear(self):
        type(self).fixture_processes += 1
        run = subprocess.run([str(self.fixture)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=30)
        (OUTPUT/'fixture.stdout').write_bytes(run.stdout); (OUTPUT/'fixture.stderr').write_bytes(run.stderr)
        self.assertEqual(run.returncode,0)
        result = json.loads(run.stdout)
        self.assertEqual((result['evidence_bytes'],result['body_cap'],result['frame_capacity']),(84,415,448))
        self.assertEqual((result['sampled_scratch_clears'],result['clear_failed'],result['short_buffer_rejected']),(3,0,1))
        self.assertEqual((result['hash_calls'],result['decoder_calls']),(0,0))
        self.assertEqual([row['name'] for row in result['cases']],['magic','zero','other','unavailable','maximum'])
        for row in result['cases']:
            with self.subTest(case=row['name']):
                self.assertEqual((row['cleared'],row['scratch_cleared']),(1,1))
                self.assertLessEqual(row['length'],415)
                body = row['frame'].split('N10DATACMP2 ',1)[1].rsplit(' checksum=',1)[0]
                self.assertEqual(row['length'],len(body))
                sampled = row['name'] in ('magic','zero','other')
                logical = 4000 if sampled else 0 if row['name']=='unavailable' else 67108864
                legacy = data_line('carrier_mismatch' if sampled else 'carrier_crypto',logical,0 if sampled else -5)
                parsed = carrier.decode(legacy,IDENTITY,CYCLE)
                comparison = carrier.decode_compare(legacy+'\n'+row['frame'],IDENTITY,CYCLE,parsed,
                    expected=dict(data_compare_schema=carrier.COMPARE_SCHEMA))
                probe = comparison['input_probe']
                self.assertEqual(probe['sampled'],sampled)
                self.assertEqual(probe['bytes'],8 if sampled else 0)
                self.assertEqual(probe['phase'],'post_carrier_hash_compare')
                self.assertEqual(probe['magic_match'],row['name']=='magic' if sampled else None)
                self.assertEqual(probe['prefix_zero'],row['name']=='zero' if sampled else None)
                self.assertFalse(parsed['passed'])

    def test_closed_versions_refusal_and_exact_current_v99_chain(self):
        new = dict(data_compare_schema=carrier.COMPARE_SCHEMA)
        legacy = data_line(); parsed = carrier.decode(legacy,IDENTITY,CYCLE)
        old = retained_v1()
        current_pair = retained_package_v1()
        self.assertIsNone(profile.package_scope(current_pair))
        pair_fields = profile.fields(current_pair)
        self.assertEqual(pair_fields['data_compare_schema'],carrier.COMPARE_SCHEMA_V1)
        self.assertEqual(pair_fields['host_profile_source_sha256'],dict(profile.V99_PROFILE_ORIGIN_PINS))
        for mode in ('diagnostic','rollback'):
            record = dict(current_pair,mode=mode,test_purpose='linux-data-carrier' if mode=='diagnostic' else 'rollback',
                          auto_return_diagnostic=mode=='diagnostic',auto_cycle_token=CYCLE if mode=='diagnostic' else None)
            self.assertIsNone(profile.package_scope(record,mode))
            self.assertEqual(profile.fields(record),pair_fields)
        for schema in (carrier.COMPARE_SCHEMA,None,'unknown'):
            with self.subTest(retained_package_schema=schema), self.assertRaises(ValueError):
                profile.package_scope(dict(current_pair,data_compare_schema=schema))
        no_schema = dict(current_pair); del no_schema['data_compare_schema']
        with self.assertRaises(ValueError):
            profile.package_scope(no_schema)
        v1 = carrier.decode_compare(legacy+'\n'+compare_line('1'),IDENTITY,CYCLE,parsed,expected=old)
        self.assertEqual(v1['schema'],carrier.COMPARE_SCHEMA_V1)
        self.assertEqual(v1['input_probe'],dict(state='unsupported',sampled=False,bytes=0,magic_match=None,prefix_zero=None))
        for expected in (None,new):
            with self.subTest(v1_rejected_for=expected), self.assertRaises(ValueError):
                carrier.decode_compare(legacy+'\n'+compare_line('1'),IDENTITY,CYCLE,parsed,expected=expected)
        forged = copy.deepcopy(old)
        forged['host_profile_source_sha256'][next(iter(forged['host_profile_source_sha256']))] = '0'*64
        for bad in (forged,dict(old,host_profile_source_head='f'*40)):
            with self.assertRaises(ValueError):
                carrier.decode_compare(legacy+'\n'+compare_line('1'),IDENTITY,CYCLE,parsed,expected=bad)
        with self.assertRaises(ValueError):
            carrier.decode_compare(legacy+'\n'+compare_line(),IDENTITY,CYCLE,parsed,expected=old)
        with self.assertRaisesRegex(ValueError,'missing'):
            carrier.decode_compare(legacy,IDENTITY,CYCLE,parsed,expected=new)
        good = compare_line()
        bad_lines = {
            'duplicate':good+'\n'+good, 'checksum':good[:-1]+('0' if good[-1]!='0' else '1'),
            'id':compare_line(id=OTHER), 'cycle':compare_line(cycle=OTHER),
            'boot':good.replace(f'boot={BOOT}',f'boot={OTHER}'), 'logical':compare_line(logical='4001'),
            'unknown_key':compare_line(raw_prefix='forbidden'), 'trailing':good+' extra=1',
            'oversized':compare_line(kind='x'*416), 'sample_missing':compare_line(sampled='0'),
            'sample_range':compare_line(sampled='2'), 'both_flags':compare_line(prefix_zero='1'),
            'flag_range':compare_line(magic_match='2'), 'unevaluated_sample':compare_line(state='unavailable'),
        }
        for label,line in bad_lines.items():
            with self.subTest(case=label), self.assertRaises(ValueError):
                carrier.decode_compare(legacy+'\n'+line,IDENTITY,CYCLE,parsed,expected=new)
        for companions in ([],[compare_line('1')],[good]):
            with self.subTest(companions=len(companions)), self.assertRaises(carrier.ComponentObservationError) as rejected:
                carrier.decode_selected(full_log(companions),BANNER,IDENTITY,CYCLE,expected=new)
            components = rejected.exception.component_evidence
            self.assertFalse(components['functional_acceptance'])
            self.assertFalse(components['hardware_return_proven_by_frames'])
            self.assertFalse(components['data']['passed'])
            self.assertEqual(components['pid1_validation'],'not_checked')
            if companions == [good]:
                self.assertTrue(components['carrier_comparison']['input_probe']['magic_match'])
                self.assertEqual(components['data_phase'],'carrier_integrity')
        # Default local decoding is strict v2, including absent-companion refusal.
        with self.assertRaises(carrier.ComponentObservationError):
            carrier.decode_selected(full_log([]),BANNER,IDENTITY,CYCLE)
        plan = dict(device_profile=carrier.PROFILE,current_boot_payload_sha256='a'*64)
        diagnostic = dict(payload_sha256='a'*64)
        self.assertIsNone(builtin.current_boot_binding(plan,old,diagnostic))
        for change in ({'source_head':'f'*40},{'host_profile_source_head':'f'*40},
                       {'data_compare_schema':carrier.COMPARE_SCHEMA},{'data_compare_schema':None},
                       {'data_host_experiment':'other'},{'data_current_binding_sha256':'b'*64}):
            with self.subTest(predecessor=change), self.assertRaises(ValueError):
                builtin.current_boot_binding(plan,dict(old,**change),diagnostic)
        with self.assertRaises(ValueError):
            builtin.current_boot_binding(plan,old,dict(payload_sha256='c'*64))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args(); OUTPUT=args.output
    OUTPUT.mkdir(parents=True,exist_ok=False)
    names = ('test_v100_carrier_input_probe.py','linux_data_input_probe_fixture.c','linux_data_compare_evidence.h',
             'linux_data_carrier.c','linux_data_carrier.py','build_builtin_init_image.py',
             'sha256_kat_device_profile.py','builtin_init_profile.py')
    pins = {name:hashlib.sha256((HERE/name).read_bytes()).hexdigest() for name in names}
    (OUTPUT/'source-sha256.json').write_text(json.dumps(pins,indent=2)+'\n')
    result = unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(CarrierInputProbeTests(method) for method in METHODS))
    (OUTPUT/'result.json').write_text(json.dumps(dict(schema='v100-new-late-prefix-tests-v1',selected=list(METHODS),
        run=result.testsRun,failures=len(result.failures),errors=len(result.errors),passed=result.wasSuccessful(),
        fixture_compiles=CarrierInputProbeTests.compiles,fixture_processes=CarrierInputProbeTests.fixture_processes,
        real_input_reads=0,native_hash_executions=0,payload_decoder_executions=0,old_test_methods_run=0),indent=2)+'\n')
    raise SystemExit(0 if result.wasSuccessful() else 1)
