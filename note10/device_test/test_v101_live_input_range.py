"""Fixed NEW2/fixture1 live-range tests; invented scalar coordinates only."""
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
BANNER='Linux version 4.14.113-v101-range-synthetic fixture-only'
OUTPUT=None
METHODS=('test_shared_scalar_range_and_private_formatter','test_closed_range_current_origin_and_rejected_components')


def frame(marker,body,boot=BOOT):
    return f'N10BOOTLINK2 boot={boot} {marker} {body} checksum={checksum(body.encode()):08x}'


def data_line(native=4096,logical=3000):
    return frame('N10DATA1',f'id={IDENTITY} cycle={CYCLE} kind=result source={carrier.MODE} status=carrier_mismatch '
        f'carrier={native} logical={logical} carrier_rc=0 stream=0 payload=0 consumed=0 written=0 calls=0 '
        f'digest={"0"*64} reasons=00000000 expectations=1 captures=1 retained=1 ownership=0 executed=0')


def compare_line(logical=3000):
    return frame('N10DATACMP2',f'id={IDENTITY} cycle={CYCLE} kind=compare source={carrier.MODE} '
        f'phase=carrier_integrity state=compared logical={logical} actual={"11"*32} expected={"22"*32} equal=0 '
        'sampled=1 magic_match=0 prefix_zero=1 ownership=0 executed=0')


def range_line(**changes):
    # These deliberately invented physical intervals overlap only the unused tail.
    row=dict(id=IDENTITY,cycle=CYCLE,kind='range',source='live-arm64',extent='native',state='checked',
        domain='physical',logical='3000',input_start='0000000000003000',input_end='0000000000004000',
        kernel_start='0000000000003c00',kernel_end='0000000000004c00',logical_overlap='0',native_overlap='1',
        reasons='00000000',ownership='0',executed='0')
    row.update(changes)
    return frame('N10DATARANGE1',' '.join(f'{key}={value}' for key,value in row.items()))


def declared(span=4096):
    return dict(data_compare_schema=carrier.COMPARE_SCHEMA,data_input_range_schema=carrier.RANGE_SCHEMA,
                data_linked_kernel_bytes=span)


def current_package():
    row=dict(device_profile=carrier.PROFILE,source_head=profile.V100_PROFILE_ORIGIN_HEAD,
        host_profile_source_head=profile.V100_PROFILE_ORIGIN_HEAD,
        host_profile_source_sha256=dict(profile.V100_PROFILE_ORIGIN_PINS),data_compare_schema=carrier.COMPARE_SCHEMA)
    for key in profile.FIELDS: row.setdefault(key,'a'*64)
    for key in builtin.EXTRA_FIELDS: row[key]='b'*64
    row.update(build_evidence_id=IDENTITY,kernel_banner='Linux version 4.14.113-v91-trusted-logical synthetic',
        data_carrier_stage=carrier.STAGE,data_relative_placement_admitted=True,raw_input_binding=False,
        data_expectation_mode=carrier.MODE,data_expectation_slot={},image_expectation_patched=True,
        data_manifest_sha256='c'*64,data_carrier_sha256='d'*64,data_payload_sha256='e'*64,
        data_carrier_bytes=3000,data_payload_bytes=1024,auto_return_diagnostic=True,auto_cycle_token=CYCLE)
    return row


def full_log(ranges):
    arm=[frame('N10RET1',f'id={IDENTITY} cycle={CYCLE} phase=0 seq={i} delay_ms=90000 status=0') for i in (0,1)]
    startup=[f'N10ROUTE2 id={IDENTITY} boot={BOOT} cycle={CYCLE} route=builtin exec_attempt=1',
             f'N10INIT2 id={IDENTITY} boot={BOOT} cycle={CYCLE} route=builtin started=1']
    request=[frame('N10RET1',f'id={IDENTITY} cycle={CYCLE} phase=1 seq={i} delay_ms=90000 status=0') for i in (0,1)]
    return ('\n'.join(['[    0.000000] '+BANNER,*arm,*startup,data_line(),compare_line(),*ranges,*request])+'\n').encode('ascii')


class LiveInputRangeTests(unittest.TestCase):
    compiles=0
    fixture_processes=0

    @classmethod
    def setUpClass(cls):
        cls.fixture=OUTPUT/'live-input-range-fixture'
        command=['clang-14','-std=c11','-O2','-Wall','-Wextra','-Werror',
                 str(HERE/'linux_data_input_range_fixture.c'),'-o',str(cls.fixture)]
        cls.compiles+=1
        (OUTPUT/'fixture-command.json').write_text(json.dumps(command,indent=2)+'\n')
        run=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=120)
        (OUTPUT/'fixture-compile.log').write_bytes(run.stdout)
        if run.returncode: raise RuntimeError('NEW scalar live-range fixture compilation failed')

    def test_shared_scalar_range_and_private_formatter(self):
        type(self).fixture_processes+=1
        run=subprocess.run([str(self.fixture)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=30)
        (OUTPUT/'fixture.stdout').write_bytes(run.stdout); (OUTPUT/'fixture.stderr').write_bytes(run.stderr)
        self.assertEqual(run.returncode,0)
        output=json.loads(run.stdout)
        self.assertEqual((output['range_bytes'],output['snapshot_bytes'],output['body_cap'],output['frame_capacity']),(48,104,383,448))
        self.assertEqual((output['short_buffer_rejected'],output['zero_reason_unavailable_rejected']),(1,1))
        self.assertEqual((output['input_byte_reads'],output['hash_calls'],output['decoder_calls']),(0,0,0))
        checked={'logical_overlap','disjoint','touching','tail_only','contained','maximum_count'}
        self.assertEqual(len(output['cases']),14)
        for row in output['cases']:
            with self.subTest(case=row['name']):
                self.assertEqual(row['cleared'],1); self.assertLessEqual(row['length'],383)
                body=row['frame'].split('N10DATARANGE1 ',1)[1].rsplit(' checksum=',1)[0]
                self.assertEqual(len(body),row['length'])
                data=data_line(row['native'],row['logical'])
                parsed=carrier.decode(data,IDENTITY,CYCLE)
                relation=carrier.decode_range(data+'\n'+compare_line(row['logical'])+'\n'+row['frame'],IDENTITY,CYCLE,parsed,
                                              expected=declared(row['kernel_span']))
                self.assertEqual(relation['checked'],row['name'] in checked)
                self.assertFalse(relation['global_RAM_ownership'])
                if row['name'] in checked:
                    self.assertEqual(relation['logical_overlap'],row['name'] in ('logical_overlap','contained','maximum_count'))
                    self.assertEqual(relation['native_overlap'],row['name'] not in ('disjoint','touching'))
                    self.assertEqual(relation['tail_only'],row['name']=='tail_only')
                    self.assertEqual(len(relation['private_physical_bounds']),4)
                else:
                    self.assertGreater(relation['reasons'],0)
                    self.assertIsNone(relation['logical_overlap']); self.assertIsNone(relation['native_overlap'])
                    self.assertIsNone(relation['tail_only']); self.assertIsNone(relation['private_physical_bounds'])

    def test_closed_range_current_origin_and_rejected_components(self):
        current=current_package()
        self.assertEqual(len(current['host_profile_source_sha256']),37)
        self.assertIsNone(profile.package_scope(current))
        fields=profile.fields(current)
        for mode in ('diagnostic','rollback'):
            record=dict(current,mode=mode,test_purpose='linux-data-carrier' if mode=='diagnostic' else 'rollback',
                auto_return_diagnostic=mode=='diagnostic',auto_cycle_token=CYCLE if mode=='diagnostic' else None)
            self.assertIsNone(profile.package_scope(record,mode)); self.assertEqual(profile.fields(record),fields)
        with self.assertRaises(ValueError): profile.host_binding(profile.V100_PROFILE_ORIGIN_HEAD)
        plan=dict(device_profile=carrier.PROFILE,current_boot_payload_sha256='a'*64)
        self.assertIsNone(builtin.current_boot_binding(plan,current,dict(payload_sha256='a'*64)))
        for change in ({'data_compare_schema':carrier.COMPARE_SCHEMA_V1},{'data_input_range_schema':carrier.RANGE_SCHEMA},
                       {'host_profile_source_head':profile.V99_PROFILE_ORIGIN_HEAD},{'source_head':'f'*40}):
            with self.subTest(retained=change), self.assertRaises(ValueError): profile.package_scope(dict(current,**change))
        future=dict(current,source_head='e'*40,**profile.host_binding('e'*40),**declared())
        self.assertIsNone(profile.package_scope(future))
        self.assertEqual(profile.fields(future)['data_linked_kernel_bytes'],4096)
        for key in ('data_input_range_schema','data_linked_kernel_bytes','data_compare_schema'):
            bad=dict(future); del bad[key]
            with self.subTest(missing=key), self.assertRaises(ValueError): profile.package_scope(bad)
        legacy_data=data_line(); parsed=carrier.decode(legacy_data,IDENTITY,CYCLE)
        self.assertEqual(carrier.decode_range(legacy_data+'\n'+compare_line(),IDENTITY,CYCLE,parsed,expected=current),
                         dict(schema=None,state='unsupported',checked=False))
        good=range_line(); text=legacy_data+'\n'+compare_line()+'\n'
        tail=carrier.decode_range(text+good,IDENTITY,CYCLE,parsed,expected=declared())
        self.assertTrue(tail['tail_only']); self.assertFalse(tail['logical_overlap'])
        unavailable=range_line(state='unavailable',domain='none',input_start='na',input_end='na',kernel_start='na',kernel_end='na',
                               logical_overlap='na',native_overlap='na',reasons='00000002')
        self.assertIsNone(carrier.decode_range(text+unavailable,IDENTITY,CYCLE,parsed,expected=declared())['native_overlap'])
        invalid={
            'duplicate':good+'\n'+good,'checksum':good[:-1]+('0' if good[-1]!='0' else '1'),
            'identity':range_line(id=OTHER),'cycle':range_line(cycle=OTHER),
            'boot':good.replace(f'boot={BOOT}',f'boot={OTHER}'),'virtual_domain':range_line(domain='virtual'),
            'span':range_line(kernel_end='0000000000004c01'),'native_count':range_line(input_end='0000000000004001'),
            'logical_count':range_line(logical='2049'),'flags':range_line(logical_overlap='1'),
            'wrap':range_line(input_start='fffffffffffff800',input_end='0000000000000800'),
            'raw_virtual_key':range_line(virtual_pointer='forbidden'),'trailing':good+' extra=1',
            'length':range_line(kind='x'*384),
            'zero_reason_unavailable':range_line(state='unavailable',domain='none',input_start='na',input_end='na',
                kernel_start='na',kernel_end='na',logical_overlap='na',native_overlap='na',reasons='00000000'),
        }
        for label,line in invalid.items():
            with self.subTest(case=label), self.assertRaises(ValueError) as error:
                carrier.decode_range(text+line,IDENTITY,CYCLE,parsed,expected=declared())
            self.assertNotIn('0000000000003000',str(error.exception))
        for ranges in ([],[invalid['checksum']],[good]):
            with self.subTest(range_count=len(ranges)), self.assertRaises(carrier.ComponentObservationError) as rejected:
                carrier.decode_selected(full_log(ranges),BANNER,IDENTITY,CYCLE,expected=declared())
            components=rejected.exception.component_evidence
            self.assertIn('data',components); self.assertIn('carrier_comparison',components)
            self.assertTrue(components['carrier_comparison']['input_probe']['prefix_zero'])
            self.assertFalse(components['functional_acceptance']); self.assertFalse(components['hardware_return_proven_by_frames'])
            if ranges==[good]: self.assertTrue(components['live_input_range']['tail_only'])
            else: self.assertNotIn('live_input_range',components)
        with self.assertRaises(ValueError): carrier.decode_range(text+good,IDENTITY,CYCLE,parsed,expected=current)
        with self.assertRaises(ValueError): carrier.decode_range(text+good,IDENTITY,CYCLE,parsed,expected=declared(8192))
        with self.assertRaises(ValueError):
            carrier.decode_range(legacy_data+'\n'+good+'\n'+compare_line(),IDENTITY,CYCLE,parsed,expected=declared())


if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args(); OUTPUT=args.output; OUTPUT.mkdir(parents=True,exist_ok=False)
    names=('test_v101_live_input_range.py','linux_data_input_range_fixture.c','linux_data_input_range.h',
           'linux_data_carrier.c','linux_data_carrier.py','build_builtin_init_image.py',
           'sha256_kat_device_profile.py','builtin_init_profile.py')
    pins={name:hashlib.sha256((HERE/name).read_bytes()).hexdigest() for name in names}
    (OUTPUT/'source-sha256.json').write_text(json.dumps(pins,indent=2)+'\n')
    result=unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(LiveInputRangeTests(method) for method in METHODS))
    (OUTPUT/'result.json').write_text(json.dumps(dict(schema='v101-new-live-range-tests-v1',selected=list(METHODS),
        run=result.testsRun,failures=len(result.failures),errors=len(result.errors),passed=result.wasSuccessful(),
        fixture_compiles=LiveInputRangeTests.compiles,fixture_processes=LiveInputRangeTests.fixture_processes,
        actual_memory_or_payload_reads=0,native_hash_executions=0,old_test_methods_run=0),indent=2)+'\n')
    raise SystemExit(0 if result.wasSuccessful() else 1)
