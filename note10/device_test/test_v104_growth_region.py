"""Fixed NEW2/fixture1 growth-region batch. Synthetic metadata only."""
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
OUTPUT=None
IDENTITY,CYCLE,BOOT='1'*32,'2'*32,'3'*32
BANNER='Linux version 4.14.113-v104-synthetic fixture-only'
METHODS=('test_actual_capture_growth_bookkeeping_guards','test_closed_growth_context_predecessor_and_partial_evidence')


def frame(marker,body,boot=BOOT):
    return f'N10BOOTLINK2 boot={boot} {marker} {body} checksum={checksum(body.encode()):08x}'


def declared():
    return dict(carrier.GROWTH_BINDING,data_compare_schema=carrier.COMPARE_SCHEMA,
        data_input_range_schema=carrier.RANGE_SCHEMA,data_early_prefix_schema=carrier.EARLY_SCHEMA,
        data_linked_kernel_bytes=0x3500000)


def data_row(captures=1):
    return dict(captures=captures,boot_identity=BOOT)


def full_log(growth):
    data=frame('N10DATA1',f'id={IDENTITY} cycle={CYCLE} kind=result source={carrier.MODE} status=carrier_mismatch '
        f'carrier=4096 logical=3000 carrier_rc=0 stream=0 payload=0 consumed=0 written=0 calls=0 digest={"0"*64} '
        'reasons=00000000 expectations=1 captures=1 retained=1 ownership=0 executed=0')
    compare=frame('N10DATACMP2',f'id={IDENTITY} cycle={CYCLE} kind=compare source={carrier.MODE} phase=carrier_integrity '
        f'state=compared logical=3000 actual={"11"*32} expected={"22"*32} equal=0 '
        'sampled=1 magic_match=0 prefix_zero=0 ownership=0 executed=0')
    relation=frame('N10DATARANGE1',f'id={IDENTITY} cycle={CYCLE} kind=range source=live-arm64 extent=native '
        'state=checked domain=physical logical=3000 input_start=0000000080800000 input_end=0000000080801000 '
        'kernel_start=0000000080000000 kernel_end=0000000083500000 logical_overlap=1 native_overlap=1 '
        'reasons=00000000 ownership=0 executed=0')
    early=frame('N10DATAEARLY1',f'id={IDENTITY} cycle={CYCLE} kind=early source=memblock-ram-map phase=post_paging '
        'state=sampled captures=1 sampled=1 magic_match=0 prefix_zero=0 reasons=00000000 ownership=0 executed=0')
    arms=[frame('N10RET1',f'id={IDENTITY} cycle={CYCLE} phase=0 seq={i} delay_ms=90000 status=0') for i in (0,1)]
    startup=[f'N10ROUTE2 id={IDENTITY} boot={BOOT} cycle={CYCLE} route=builtin exec_attempt=1',
             f'N10INIT2 id={IDENTITY} boot={BOOT} cycle={CYCLE} route=builtin started=1']
    requests=[frame('N10RET1',f'id={IDENTITY} cycle={CYCLE} phase=1 seq={i} delay_ms=90000 status=0') for i in (0,1)]
    return ('\n'.join(['[    0.000000] '+BANNER,*arms,*startup,data,compare,relation,early,*growth,*requests])+'\n').encode('ascii')


class GrowthRegionTests(unittest.TestCase):
    compiles=0
    fixture_processes=0
    fixture=None

    def test_actual_capture_growth_bookkeeping_guards(self):
        command=['clang-14','-std=gnu11','-O2','-Wall','-Wextra','-Werror',str(HERE/'linux_data_growth_fixture.c'),
            '-o',str(OUTPUT/'growth-region-fixture')]
        (OUTPUT/'fixture-command.json').write_text(json.dumps(command,indent=2)+'\n')
        type(self).compiles+=1
        built=subprocess.run(command,capture_output=True,text=True,timeout=60)
        (OUTPUT/'fixture-compile.log').write_text(built.stdout+built.stderr)
        self.assertEqual(built.returncode,0,built.stderr)
        type(self).fixture_processes+=1
        ran=subprocess.run([str(OUTPUT/'growth-region-fixture')],capture_output=True,text=True,timeout=30)
        (OUTPUT/'fixture-output.json').write_text(ran.stdout)
        (OUTPUT/'fixture-stderr.log').write_text(ran.stderr)
        self.assertEqual(ran.returncode,0,ran.stderr)
        result=json.loads(ran.stdout);type(self).fixture=result
        self.assertEqual((result['capture_cases'],result['guard_cases'],result['permanent_scalar_bytes']),(12,6,120))
        self.assertTrue(result['actual_capture_adapter']);self.assertTrue(result['bookkeeping_only'])
        self.assertEqual((result['new_extension_byte_reads'],result['new_input_byte_reads'],result['old_decoder_calls']),(0,0,0))

    def test_closed_growth_context_predecessor_and_partial_evidence(self):
        self.assertIsNotNone(type(self).fixture,'one fixture result required; no second process')
        body=type(self).fixture['wire_checked'];good=frame('N10DATAGROWTH1',body)
        text=frame('N10DATAEARLY1','synthetic-order-anchor')+'\n'+good
        parsed=carrier.decode_growth(text,IDENTITY,CYCLE,data_row(),expected=declared())
        self.assertEqual(parsed['current_linked_span'],0x3500000)
        self.assertTrue(parsed['memory']);self.assertTrue(parsed['map_start']);self.assertFalse(parsed['reserved'])
        self.assertFalse(parsed['hardware_mapping_attested']);self.assertFalse(parsed['larger_footprint_physically_admitted'])
        unavailable=frame('N10DATAGROWTH1',type(self).fixture['wire_unavailable'])
        parsed=carrier.decode_growth(frame('N10DATAEARLY1','anchor')+'\n'+unavailable,IDENTITY,CYCLE,data_row(0),expected=declared())
        self.assertIsNone(parsed['memory']);self.assertEqual(parsed['state'],'unavailable')
        for mutation in ('missing','duplicate','checksum','boot','target','budget','proposal','current','flags','query','order','unknown','overlong'):
            lines=[good];anchor=frame('N10DATAEARLY1','anchor')
            changed=body
            if mutation=='missing': lines=[]
            if mutation=='duplicate': lines=[good,good]
            if mutation=='checksum': lines=[good[:-1]+('0' if good[-1]!='0' else '1')]
            if mutation=='boot': lines=[frame('N10DATAGROWTH1',body,boot='4'*32)]
            if mutation=='target': changed=body.replace('target=59523072','target=59523071')
            if mutation=='budget': changed=body.replace('budget=59768832','budget=59768831')
            if mutation=='proposal': changed=body.replace(carrier.GROWTH_TARGET_SOURCE,'5'*40)
            if mutation=='current': changed=body.replace('current=55574528','current=55574527')
            if mutation=='flags': changed=body.replace('memory=1','memory=na')
            if mutation=='query': changed=body.replace('queries=3','queries=0')
            if mutation=='unknown': changed=body+' extra=0'
            if mutation=='overlong': changed=body+' '+('x'*416)
            if changed!=body: lines=[frame('N10DATAGROWTH1',changed)]
            selected='\n'.join([*lines,anchor] if mutation=='order' else [anchor,*lines])
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):
                carrier.decode_growth(selected,IDENTITY,CYCLE,data_row(),expected=declared())
        for changed in (dict(declared(),data_growth_budget_bytes=59768831),dict(declared(),data_linked_kernel_bytes=59523072)):
            with self.assertRaises(ValueError): carrier.growth_declaration(changed)
        with self.assertRaises(ValueError): carrier.decode_growth(text,IDENTITY,CYCLE,data_row())
        retained=dict(device_profile=profile.DATA_PROFILE,source_head=profile.V102_PROFILE_ORIGIN_HEAD,
            host_profile_source_head=profile.V102_PROFILE_ORIGIN_HEAD,host_profile_source_sha256=dict(profile.V102_PROFILE_ORIGIN_PINS),
            data_compare_schema=carrier.COMPARE_SCHEMA,data_input_range_schema=carrier.RANGE_SCHEMA,
            data_early_prefix_schema=carrier.EARLY_SCHEMA,data_linked_kernel_bytes=0x3500000)
        current=copy.deepcopy(retained)
        for key in profile.FIELDS: current.setdefault(key,'a'*64)
        for key in builtin.EXTRA_FIELDS: current[key]='b'*64
        current.update(profile_sha256='c'*64,accepted_result_sha256='d'*64,image_root_receipt_sha256='e'*64,
            root_reader_result_sha256='f'*64,build_evidence_id=IDENTITY,
            kernel_banner='Linux version 4.14.113-v91-trusted-logical synthetic',data_carrier_stage=carrier.STAGE,
            data_relative_placement_admitted=True,raw_input_binding=False,data_expectation_mode=carrier.MODE,
            data_expectation_slot={},image_expectation_patched=True,data_manifest_sha256='a'*64,
            data_carrier_sha256='b'*64,data_payload_sha256='c'*64,data_carrier_bytes=3000,data_payload_bytes=1024,
            auto_return_diagnostic=True,auto_cycle_token=CYCLE)
        profile.package_scope(current,'diagnostic')
        projected=profile.fields(dict(current,**carrier.GROWTH_BINDING))
        self.assertEqual({key:projected[key] for key in carrier.GROWTH_FIELDS},carrier.GROWTH_BINDING)
        with self.assertRaises(ValueError): profile.package_scope(dict(current,**carrier.GROWTH_BINDING),'diagnostic')
        self.assertEqual(len(profile.host_profile_origin(retained)['host_profile_source_sha256']),43)
        self.assertIsNone(carrier.expected_growth_schema(retained))
        with self.assertRaises(ValueError): carrier.decode_growth(text,IDENTITY,CYCLE,data_row(),expected=retained)
        with self.assertRaises(ValueError): carrier.expected_growth_schema(dict(retained,**carrier.GROWTH_BINDING))
        with self.assertRaises(ValueError): profile.host_binding(profile.V102_PROFILE_ORIGIN_HEAD)
        plan=dict(device_profile=profile.DATA_PROFILE,current_boot_payload_sha256='a'*64)
        diagnostic=dict(payload_sha256='a'*64)
        builtin.current_boot_binding(plan,retained,diagnostic)
        for changed in (dict(retained,source_head='e32ec501551b74b4cca5618ea25245f012656f29'),
                        dict(retained,data_early_prefix_schema='wrong'),dict(retained,**carrier.GROWTH_BINDING)):
            with self.assertRaises(ValueError): builtin.current_boot_binding(plan,changed,diagnostic)
        with self.assertRaises(ValueError): builtin.current_boot_binding(plan,retained,dict(payload_sha256='b'*64))
        with self.assertRaises(ValueError): profile.physical_input_scope(dict(diagnostic_kind='readonly-input-pc',PC_only=False,physical_ready=True))
        for evidence in ([good],[],[frame('N10DATAGROWTH1',body.replace('memory=1','memory=na'))]):
            with self.assertRaises(carrier.ComponentObservationError) as rejected:
                carrier.decode_selected(full_log(evidence),BANNER,IDENTITY,CYCLE,expected=declared())
            components=rejected.exception.component_evidence
            for key in ('data','carrier_comparison','live_input_range','early_input_prefix'): self.assertIn(key,components)
            self.assertFalse(components['functional_acceptance']);self.assertFalse(components['hardware_return_proven_by_frames'])
            if evidence==[good]: self.assertIn('growth_region',components)
            else: self.assertNotIn('growth_region',components)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();OUTPUT=args.output;OUTPUT.mkdir(parents=True,exist_ok=False)
    names=('test_v104_growth_region.py','linux_data_growth_fixture.c','linux_data_growth.h','linux_data_carrier.c',
        'linux_data_carrier.py','build_builtin_init_image.py','sha256_kat_device_profile.py','builtin_init_profile.py')
    (OUTPUT/'source-sha256.json').write_text(json.dumps({name:hashlib.sha256((HERE/name).read_bytes()).hexdigest() for name in names},indent=2)+'\n')
    result=unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(GrowthRegionTests(name) for name in METHODS))
    (OUTPUT/'result.json').write_text(json.dumps(dict(schema='v104-new-growth-region-tests-v1',selected=list(METHODS),run=result.testsRun,
        failures=len(result.failures),errors=len(result.errors),passed=result.wasSuccessful(),fixture_compiles=GrowthRegionTests.compiles,
        fixture_processes=GrowthRegionTests.fixture_processes,new_extension_byte_reads=0,new_input_byte_reads=0,
        old_decoder_calls=0,old_test_methods_run=0,device_operations=[]),indent=2)+'\n')
    raise SystemExit(0 if result.wasSuccessful() else 1)
