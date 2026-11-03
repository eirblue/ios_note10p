"""Fixed NEW2/fixture1 early-lifetime batch; no real input or old test module."""
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

HERE=Path(__file__).resolve().parent
IDENTITY,CYCLE,BOOT,OTHER='1'*32,'2'*32,'3'*32,'4'*32
BANNER='Linux version 4.14.113-v102-early-synthetic fixture-only'
OUTPUT=None
METHODS=('test_actual_capture_ram_map_guards_and_eight_bytes','test_closed_early_schema_history_and_partial_evidence')


def frame(marker,body,boot=BOOT):
    return f'N10BOOTLINK2 boot={boot} {marker} {body} checksum={checksum(body.encode()):08x}'


def data_line(captures=1):
    return frame('N10DATA1',f'id={IDENTITY} cycle={CYCLE} kind=result source={carrier.MODE} status=carrier_mismatch '
        f'carrier=4096 logical=3000 carrier_rc=0 stream=0 payload=0 consumed=0 written=0 calls=0 digest={"0"*64} '
        f'reasons=00000000 expectations=1 captures={captures} retained=1 ownership=0 executed=0')


def compare_line():
    return frame('N10DATACMP2',f'id={IDENTITY} cycle={CYCLE} kind=compare source={carrier.MODE} '
        f'phase=carrier_integrity state=compared logical=3000 actual={"11"*32} expected={"22"*32} equal=0 '
        'sampled=1 magic_match=0 prefix_zero=1 ownership=0 executed=0')


def range_line():
    return frame('N10DATARANGE1',f'id={IDENTITY} cycle={CYCLE} kind=range source=live-arm64 extent=native '
        'state=checked domain=physical logical=3000 input_start=0000000000003000 input_end=0000000000004000 '
        'kernel_start=0000000000008000 kernel_end=0000000000009000 logical_overlap=0 native_overlap=0 '
        'reasons=00000000 ownership=0 executed=0')


def early_line(**changes):
    row=dict(id=IDENTITY,cycle=CYCLE,kind='early',source='memblock-ram-map',phase='post_paging',state='sampled',
        captures='1',sampled='1',magic_match='1',prefix_zero='0',reasons='00000000',ownership='0',executed='0')
    row.update(changes)
    return frame('N10DATAEARLY1',' '.join(f'{key}={value}' for key,value in row.items()))


def declared():
    return dict(data_compare_schema=carrier.COMPARE_SCHEMA,data_input_range_schema=carrier.RANGE_SCHEMA,
        data_linked_kernel_bytes=4096,data_early_prefix_schema=carrier.EARLY_SCHEMA)


def current_package():
    row=dict(device_profile=carrier.PROFILE,source_head=profile.V101_PROFILE_ORIGIN_HEAD,
        host_profile_source_head=profile.V101_PROFILE_ORIGIN_HEAD,
        host_profile_source_sha256=dict(profile.V101_PROFILE_ORIGIN_PINS),data_compare_schema=carrier.COMPARE_SCHEMA,
        data_input_range_schema=carrier.RANGE_SCHEMA,data_linked_kernel_bytes=4096)
    for key in profile.FIELDS: row.setdefault(key,'a'*64)
    for key in builtin.EXTRA_FIELDS: row[key]='b'*64
    row.update(build_evidence_id=IDENTITY,kernel_banner='Linux version 4.14.113-v91-trusted-logical synthetic',
        data_carrier_stage=carrier.STAGE,data_relative_placement_admitted=True,raw_input_binding=False,
        data_expectation_mode=carrier.MODE,data_expectation_slot={},image_expectation_patched=True,
        data_manifest_sha256='c'*64,data_carrier_sha256='d'*64,data_payload_sha256='e'*64,
        data_carrier_bytes=3000,data_payload_bytes=1024,auto_return_diagnostic=True,auto_cycle_token=CYCLE)
    return row


def full_log(early):
    arms=[frame('N10RET1',f'id={IDENTITY} cycle={CYCLE} phase=0 seq={i} delay_ms=90000 status=0') for i in (0,1)]
    startup=[f'N10ROUTE2 id={IDENTITY} boot={BOOT} cycle={CYCLE} route=builtin exec_attempt=1',
             f'N10INIT2 id={IDENTITY} boot={BOOT} cycle={CYCLE} route=builtin started=1']
    requests=[frame('N10RET1',f'id={IDENTITY} cycle={CYCLE} phase=1 seq={i} delay_ms=90000 status=0') for i in (0,1)]
    return ('\n'.join(['[    0.000000] '+BANNER,*arms,*startup,data_line(),compare_line(),range_line(),*early,*requests])+'\n').encode('ascii')


class InputLifetimeTests(unittest.TestCase):
    compiles=0
    fixture_processes=0

    @classmethod
    def setUpClass(cls):
        cls.fixture=OUTPUT/'early-prefix-fixture'
        command=['clang-14','-std=gnu11','-O2','-Wall','-Wextra','-Werror',
            str(HERE/'linux_data_early_prefix_fixture.c'),'-o',str(cls.fixture)]
        cls.compiles+=1
        (OUTPUT/'fixture-command.json').write_text(json.dumps(command,indent=2)+'\n')
        run=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=120)
        (OUTPUT/'fixture-compile.log').write_bytes(run.stdout)
        if run.returncode: raise RuntimeError('NEW actual early capture fixture compilation failed')

    def test_actual_capture_ram_map_guards_and_eight_bytes(self):
        type(self).fixture_processes+=1
        run=subprocess.run([str(self.fixture)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=30)
        (OUTPUT/'fixture.stdout').write_bytes(run.stdout); (OUTPUT/'fixture.stderr').write_bytes(run.stderr)
        self.assertEqual(run.returncode,0)
        output=json.loads(run.stdout)
        self.assertEqual((output['flags_bytes'],output['permanent_data_bytes'],output['body_cap'],output['frame_capacity']),(16,104,255,448))
        self.assertEqual((output['short_buffer_rejected'],output['zero_reason_unavailable_rejected']),(1,1))
        self.assertEqual((output['hash_calls'],output['decoder_calls']),(0,0))
        self.assertEqual(len(output['cases']),14)
        for row in output['cases']:
            with self.subTest(case=row['name']):
                self.assertLessEqual(row['reads'],1); self.assertEqual(row['read_bytes'],8*row['reads'])
                self.assertEqual(row['scratch_clears'],row['reads']); self.assertEqual(row['cleared'],1)
                self.assertLessEqual(row['length'],255)
                if row['ram_queries']: self.assertEqual(row['full_span_argument_ok'],1)
                if row['map_queries']: self.assertEqual(row['map_argument_ok'],1)
                if row['name'] in ('not_ram','negative_ram'):
                    self.assertEqual((row['ram_queries'],row['map_queries'],row['reads']),(1,0,0))
                if row['name']=='nomap': self.assertEqual((row['ram_queries'],row['map_queries'],row['reads']),(1,1,0))
                if row['name'] in ('nonlinear','roundtrip','overflow','globals_before','not_reached','invalid_repeat'):
                    self.assertEqual(row['reads'],0)
                if row['name']=='globals_after': self.assertEqual((row['map_queries'],row['reads']),(1,0))
                if row['name']=='repeat': self.assertEqual((row['captures'],row['reads']),(2,1))
                text=data_line(row['captures'])+'\n'+range_line()+'\n'+row['frame']
                parsed=carrier.decode(data_line(row['captures']),IDENTITY,CYCLE)
                early=carrier.decode_early(text,IDENTITY,CYCLE,parsed,expected=declared())
                sampled=row['name'] in ('magic','zero','other')
                self.assertEqual(early['sampled'],sampled)
                self.assertEqual(early['magic_match'],row['name']=='magic' if sampled else None)
                self.assertEqual(early['prefix_zero'],row['name']=='zero' if sampled else None)
                self.assertFalse(early['global_RAM_ownership']); self.assertFalse(early['hardware_mapping_attested'])
                if sampled: self.assertEqual((row['reads'],early['reasons']),(1,0))
                else: self.assertGreater(early['reasons'],0)

    def test_closed_early_schema_history_and_partial_evidence(self):
        current=current_package()
        self.assertEqual(len(current['host_profile_source_sha256']),40)
        self.assertIsNone(profile.package_scope(current)); prior_fields=profile.fields(current)
        for mode in ('diagnostic','rollback'):
            row=dict(current,mode=mode,test_purpose='linux-data-carrier' if mode=='diagnostic' else 'rollback',
                auto_return_diagnostic=mode=='diagnostic',auto_cycle_token=CYCLE if mode=='diagnostic' else None)
            self.assertIsNone(profile.package_scope(row,mode)); self.assertEqual(profile.fields(row),prior_fields)
        with self.assertRaises(ValueError): profile.host_binding(profile.V101_PROFILE_ORIGIN_HEAD)
        plan=dict(device_profile=carrier.PROFILE,current_boot_payload_sha256='a'*64)
        self.assertIsNone(builtin.current_boot_binding(plan,current,dict(payload_sha256='a'*64)))
        with self.assertRaises(ValueError): builtin.current_boot_binding(plan,current,dict(payload_sha256='f'*64))
        future=dict(current,source_head='e'*40,**profile.host_binding('e'*40),**declared())
        self.assertIsNone(profile.package_scope(future))
        self.assertEqual(profile.fields(future)['data_early_prefix_schema'],carrier.EARLY_SCHEMA)
        for value in (None,'unknown'):
            with self.assertRaises(ValueError): profile.package_scope(dict(future,data_early_prefix_schema=value))
        missing=dict(future); del missing['data_early_prefix_schema']
        with self.assertRaises(ValueError): profile.package_scope(missing)
        with self.assertRaises(ValueError): profile.package_scope(dict(current,data_early_prefix_schema=carrier.EARLY_SCHEMA))
        parsed=carrier.decode(data_line(),IDENTITY,CYCLE)
        text=data_line()+'\n'+compare_line()+'\n'+range_line()+'\n'
        self.assertEqual(carrier.decode_early(text,IDENTITY,CYCLE,parsed,expected=current),dict(schema=None,state='unsupported',sampled=False))
        good=early_line()
        invalid={'duplicate':good+'\n'+good,'checksum':good[:-1]+('0' if good[-1]!='0' else '1'),
            'id':early_line(id=OTHER),'cycle':early_line(cycle=OTHER),'boot':good.replace(f'boot={BOOT}',f'boot={OTHER}'),
            'phase':early_line(phase='pre_paging'),'source':early_line(source='unchecked'),
            'captures':early_line(captures='2'),'sampled':early_line(sampled='2'),
            'both':early_line(prefix_zero='1'),'reason':early_line(reasons='00000010'),
            'extra':early_line(raw_prefix='forbidden'),'length':early_line(kind='x'*256),'trailing':good+' extra=1',
            'zero_unavailable':early_line(state='unavailable',sampled='0',magic_match='na',prefix_zero='na',reasons='00000000')}
        for name,line in invalid.items():
            with self.subTest(case=name),self.assertRaises(ValueError):
                carrier.decode_early(text+line,IDENTITY,CYCLE,parsed,expected=declared())
        unavailable=early_line(state='unavailable',sampled='0',magic_match='na',prefix_zero='na',reasons='00000010')
        self.assertIsNone(carrier.decode_early(text+unavailable,IDENTITY,CYCLE,parsed,expected=declared())['prefix_zero'])
        with self.assertRaises(ValueError): carrier.decode_early(text+good,IDENTITY,CYCLE,parsed,expected=current)
        with self.assertRaises(ValueError): carrier.decode_early(data_line()+'\n'+good+'\n'+range_line(),IDENTITY,CYCLE,parsed,expected=declared())
        for early in ([],[invalid['checksum']],[good]):
            with self.subTest(early_count=len(early)),self.assertRaises(carrier.ComponentObservationError) as rejected:
                carrier.decode_selected(full_log(early),BANNER,IDENTITY,CYCLE,expected=declared())
            components=rejected.exception.component_evidence
            self.assertIn('data',components); self.assertIn('carrier_comparison',components); self.assertIn('live_input_range',components)
            self.assertTrue(components['carrier_comparison']['input_probe']['prefix_zero'])
            self.assertFalse(components['live_input_range']['logical_overlap'])
            self.assertFalse(components['functional_acceptance']); self.assertFalse(components['hardware_return_proven_by_frames'])
            if early==[good]: self.assertTrue(components['early_input_prefix']['magic_match'])
            else: self.assertNotIn('early_input_prefix',components)


if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args(); OUTPUT=args.output; OUTPUT.mkdir(parents=True,exist_ok=False)
    names=('test_v102_input_lifetime.py','linux_data_early_prefix_fixture.c','linux_data_early_prefix.h',
        'linux_data_carrier.c','linux_data_carrier.py','build_builtin_init_image.py','sha256_kat_device_profile.py','builtin_init_profile.py')
    (OUTPUT/'source-sha256.json').write_text(json.dumps({n:hashlib.sha256((HERE/n).read_bytes()).hexdigest() for n in names},indent=2)+'\n')
    result=unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(InputLifetimeTests(method) for method in METHODS))
    (OUTPUT/'result.json').write_text(json.dumps(dict(schema='v102-new-input-lifetime-tests-v1',selected=list(METHODS),
        run=result.testsRun,failures=len(result.failures),errors=len(result.errors),passed=result.wasSuccessful(),
        fixture_compiles=InputLifetimeTests.compiles,fixture_processes=InputLifetimeTests.fixture_processes,
        actual_kernel_or_payload_reads=0,native_hash_executions=0,old_test_methods_run=0),indent=2)+'\n')
    raise SystemExit(0 if result.wasSuccessful() else 1)
