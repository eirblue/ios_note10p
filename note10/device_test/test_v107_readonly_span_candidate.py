"""Fixed NEW2 and type3 fixture1/process1; PC first use, synthetic input only."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

import kernel_readonly_input as old
import kernel_readonly_span_candidate as ro3
import linux_data_carrier as data
import sha256_kat_device_profile as profile
from decode_reservation import checksum

HERE=Path(__file__).resolve().parent
OUTPUT=None
IDENTITY,CYCLE,BOOT='1'*32,'2'*32,'3'*32
METHODS=('test_actual_type3_adapter_and_late_source','test_type3_compiler_producer_partial_observation_and_scope')
REQUIRED=(*ro3.SOURCES,'kernel_readonly_input.py','kernel_readonly_span.h','linux_data_carrier.py',
    'linux_data_carrier.c','linux_data_carrier_composition.c','build_builtin_init_image.py')


def frame(marker,body):
    return f'N10BOOTLINK2 boot={BOOT} {marker} {body} checksum={checksum(body.encode()):08x}'


def geometry():
    base=0x100000;start=4096;slot=8192;descriptor=slot+ro3.CAPACITY;init=descriptor+80+4096;end=init+4096
    raw=bytearray(end);raw[descriptor:descriptor+80]=ro3.DESCRIPTOR
    system='\n'.join(f'{base+offset:016x} {kind} {name}' for offset,kind,name in ((0,'T','_text'),(start,'T','_stext'),
        (start,'R','__start_rodata'),(slot,'r',ro3.SLOT),(descriptor,'r',ro3.DESC),(init,'T','__init_begin'),(end,'B','_end')))
    symbols=f'0000000000000000 {ro3.CAPACITY:016x} r {ro3.SLOT}\n0000000000000000 0000000000000050 r {ro3.DESC}\n'
    sections=f'[ 7] .rodata.n10_kernel_readonly3_input PROGBITS 00000000 002000 {ro3.CAPACITY:06x} 00 A 0 0 16\n[ 8] .rodata.n10_kernel_readonly3_descriptor PROGBITS 00000000 440000 000050 00 A 0 0 16\n'
    table=f'89: 0000000000000000 {ro3.CAPACITY} OBJECT LOCAL DEFAULT 7 {ro3.SLOT}\n90: 0000000000000000 80 OBJECT LOCAL DEFAULT 8 {ro3.DESC}\n'
    return bytes(raw),system,symbols,sections,table,dict(linked_kernel_bytes=end,data_state_bytes=88)


def producer(record,image_bytes,span,footprint,pins):
    return dict(version='v107',diagnostic_kind=ro3.KIND,data_input_kind=ro3.KIND,storage_input_kind=ro3.KIND,kernel_readonly3_schema=ro3.SCHEMA,
        kernel_readonly3_marker='N10DATARO3',
        kernel_readonly3_span_schema=old.SPAN_SCHEMA,kernel_readonly3_default_enabled=False,kernel_readonly3_span=span,
        kernel_readonly3_requires_ack=True,passed=True,Image_built=True,BOOT_built=False,PC_only=False,PC_first_use=True,
        physical_ready=False,deployment_ready=False,device_authorized=False,device_operations=[],data_expectation_mode=ro3.MODE,
        data_expectation_slot=record,image_expectation_patched=False,external_initrd_capture=False,input_capture_source='late-kernel-readonly-span-class3',
        permanent_input_storage_bytes=ro3.CAPACITY,permanent_descriptor_bytes=80,additional_linked_storage_bytes=ro3.CAPACITY+80,
        class2_PC_storage_absent=True,kernel_readonly3_slot=record,kernel_readonly3_linked_bytes=footprint['linked_kernel_bytes'],
        kernel_readonly3_image_bytes=image_bytes,image_bytes=image_bytes,data_footprint=footprint,source_sha256=pins,
        settings=dict(NOTE10_KERNEL_READONLY_SPAN_CANDIDATE='y',NOTE10_KERNEL_READONLY_INPUT='n',NOTE10_KERNEL_READONLY_SPAN_PC='n',
            NOTE10_READONLY_INPUT_PC='n',NOTE10_OWNED_CONTIGUOUS_STAGING='n',NOTE10_CURRENT_OWNED_STAGING='n'),
        ci_context=dict(GITHUB_SHA='7'*40,GITHUB_WORKFLOW_SHA='7'*40,GITHUB_JOB='linux-data-carrier',GITHUB_REPOSITORY='eirblue/ios_note10p',
            GITHUB_WORKFLOW_REF='eirblue/ios_note10p/'+ro3.WORKFLOW+'@refs/heads/main',GITHUB_RUN_ID='123',GITHUB_RUN_ATTEMPT='1'))


def data_body():
    row=dict(id=IDENTITY,cycle=CYCLE,kind='result',source=ro3.MODE,status='unavailable',carrier=str(ro3.CAPACITY),logical='0',carrier_rc='0',
        stream='0',payload='0',consumed='0',written='0',calls='0',digest='0'*64,reasons='00000400',expectations='0',captures='0',retained='0',ownership='0',executed='0')
    return ' '.join(f'{key}={value}' for key,value in row.items())


class ReadonlySpanCandidateTests(unittest.TestCase):
    compiles=0
    fixture_processes=0

    def test_actual_type3_adapter_and_late_source(self):
        command=['clang-14','-std=gnu11','-O2','-Wall','-Wextra','-Werror',str(HERE/'kernel_readonly_span_candidate_fixture.c'),'-o',str(OUTPUT/'readonly-span-candidate-fixture')]
        (OUTPUT/'fixture-command.json').write_text(json.dumps(command,indent=2)+'\n')
        type(self).compiles+=1;built=subprocess.run(command,capture_output=True,text=True,timeout=60)
        (OUTPUT/'fixture-compile.log').write_text(built.stdout+built.stderr);self.assertEqual(built.returncode,0,built.stderr)
        type(self).fixture_processes+=1;ran=subprocess.run([str(OUTPUT/'readonly-span-candidate-fixture')],capture_output=True,text=True,timeout=30)
        (OUTPUT/'fixture-output.json').write_text(ran.stdout);(OUTPUT/'fixture-stderr.log').write_text(ran.stderr)
        self.assertEqual(ran.returncode,0,ran.stderr);row=json.loads(ran.stdout)
        self.assertEqual(row['type_cases'],11);self.assertEqual(row['synthetic_hash_calls'],1)
        self.assertTrue(all(row[key] for key in ('actual_class3_adapter','pre_read_guard','canaries')))
        self.assertTrue(all(row[key]==0 for key in ('old_decoder_calls','allocations','input_byte_reads')))

    def test_type3_compiler_producer_partial_observation_and_scope(self):
        raw,system,symbols,sections,table,footprint=geometry()
        record=ro3.slot_metadata(raw,system,symbols,sections,table)
        span=ro3.span_metadata(system,footprint,record)
        self.assertEqual(record['descriptor_class'],3);self.assertNotEqual(ro3.DESCRIPTOR,old.DESCRIPTOR)
        self.assertEqual(record['permanent_input_bytes']+record['permanent_descriptor_bytes'],4440144)
        for old_symbol in (old.SLOT,old.DESC,'n10_readonly_input'):
            with self.assertRaises(ValueError):ro3.slot_metadata(raw,system,symbols+f'0000000000000000 0000000000000050 r {old_symbol}\n',sections,table)
        descriptor=record['descriptor']['offset'];bad=bytearray(raw);bad[descriptor:descriptor+80]=old.DESCRIPTOR
        with self.assertRaises(ValueError):ro3.slot_metadata(bytes(bad),system,symbols,sections,table)
        with self.assertRaises(ValueError):ro3.slot_metadata(raw,system,symbols,sections.replace('00 A','00 AX'),table)
        pins={'note10/device_test/'+name:'a'*64 for name in REQUIRED};row=producer(record,len(raw),span,footprint,pins)
        admitted=ro3.producer_contract(row,'7'*40,producing_sources=pins)
        self.assertEqual((admitted['candidate_kind'],admitted['storage_input_kind'],admitted['descriptor_class']),(ro3.KIND,ro3.KIND,3))
        self.assertFalse(admitted['physical_ready']);self.assertEqual(admitted['slot_count'],1)
        for key,value in (('diagnostic_kind',old.SPAN_KIND),('data_input_kind',old.KIND),('kernel_readonly3_schema',old.SCHEMA),
            ('class2_PC_storage_absent',False),('PC_first_use',False),('version','v106'),('storage_input_kind',old.KIND),('kernel_readonly3_marker','N10DATARO1')):
            bad=copy.deepcopy(row);bad[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):ro3.producer_contract(bad,'7'*40,producing_sources=pins)
        for mutate in ('class2_descriptor','span','source','config'):
            bad=copy.deepcopy(row)
            if mutate=='class2_descriptor':bad['kernel_readonly3_slot']['descriptor_class']=2
            if mutate=='span':bad['kernel_readonly3_span']['kernel_bytes']+=16
            if mutate=='source':bad['source_sha256']['note10/device_test/kernel_readonly_span_candidate.h']='b'*64
            if mutate=='config':bad['settings']['NOTE10_KERNEL_READONLY_SPAN_PC']='y'
            with self.assertRaises(ValueError):ro3.producer_contract(bad,'7'*40,producing_sources=pins)
        for head in (old.HISTORICAL_HEAD,'1fb2be6472ffd7c1c1544caf005b4db55fb07f68'):
            with self.assertRaises(ValueError):ro3.producer_contract(row,head,producing_sources=pins)
        fixture=json.loads((OUTPUT/'fixture-output.json').read_text());wire=frame('N10DATASPAN1',fixture['checked'])
        bound=int(dict(token.split('=') for token in fixture['checked'].split())['kernel_bytes'])
        # Exact current source context, synthetic compiler extents matching the fixture interval.
        context=producer(copy.deepcopy(record),bound,copy.deepcopy(span),dict(linked_kernel_bytes=bound,data_state_bytes=88),
            {'note10/device_test/'+name:data.sha((HERE/name).read_bytes()) for name in REQUIRED})
        context['kernel_readonly3_span'].update(kernel_bytes=bound,text_prefix_bytes=0)
        context['kernel_readonly3_slot']['slot']['offset']=0
        context['kernel_readonly3_slot']['descriptor']['offset']=ro3.CAPACITY+16
        banner='Linux version 4.14.113-v107-readonly-span-candidate synthetic'
        arms=[frame('N10RET1',f'id={IDENTITY} cycle={CYCLE} phase=0 seq={i} delay_ms=90000 status=0') for i in (0,1)]
        startup=[f'N10ROUTE2 id={IDENTITY} boot={BOOT} cycle={CYCLE} route=builtin exec_attempt=1',f'N10INIT2 id={IDENTITY} boot={BOOT} cycle={CYCLE} route=builtin started=1']
        requests=[frame('N10RET1',f'id={IDENTITY} cycle={CYCLE} phase=1 seq={i} delay_ms=90000 status=0') for i in (0,1)]
        for companion,has_span in (('',False),(wire.replace('disjoint=1','disjoint=0'),False),(wire,True)):
            log=('\n'.join(['[    0.000000] '+banner,*arms,*startup,frame('N10DATARO3',data_body()),companion,*requests])+'\n').encode()
            with self.assertRaises(data.ComponentObservationError) as failed:ro3.decode_selected(log,banner,IDENTITY,CYCLE,expected=context)
            evidence=failed.exception.component_evidence
            self.assertIn('kernel_readonly3_data',evidence);self.assertIn('structural_presence',evidence)
            self.assertEqual('kernel_readonly3_span' in evidence,has_span)
            self.assertFalse(evidence['functional_acceptance']);self.assertFalse(evidence['hardware_return_proven_by_frames'])
        with self.assertRaises(ValueError):data.decode(frame('N10DATARO1',data_body()),IDENTITY,CYCLE,_source_class=ro3.MODE)
        with self.assertRaises(ValueError):data.decode(frame('N10DATARO3',data_body()),IDENTITY,CYCLE,_source_class=old.MODE)
        # Generic/unpatched or forged-ready type3 requires a future intrinsic offline transaction.
        for patched in (False,True):
            forged=dict(row,PC_only=False,physical_ready=True,deployment_ready=True,device_authorized=True,image_expectation_patched=patched)
            with self.assertRaises(ValueError):old.require_device_scope(forged,True)
            with self.assertRaises(ValueError):profile.physical_input_scope(forged)
        for kind in ('readonly-input-pc',old.SPAN_KIND):
            forged=dict(row,diagnostic_kind=kind,PC_only=False,physical_ready=True,image_expectation_patched=True)
            with self.assertRaises(ValueError):old.require_device_scope(forged,True)
        from precheck_window_access import make_install_battery_policy
        self.assertEqual(make_install_battery_policy(declared_test_version='v107')['effective_minimum_percent'],10)
        with patch('precheck_window_access._approval_record',side_effect=AssertionError('must refuse before approval/device')):
            with self.assertRaises(ValueError):make_install_battery_policy(use_v105_5pct_exception=True,declared_test_version='v107',
                scope=dict(source_head=old.HISTORICAL_HEAD,data_input_kind=ro3.KIND),growth_ack=True)
            with self.assertRaises(ValueError):make_install_battery_policy(use_v105_5pct_exception=True,declared_test_version='v105',
                scope=dict(row,source_head=old.HISTORICAL_HEAD,host_profile_source_head=old.HISTORICAL_HEAD),growth_ack=True,
                approval_path=Path('/synthetic-not-opened'),approval_sha256='a'*64,execution_host_source_head='7'*40)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();OUTPUT=args.output;OUTPUT.mkdir(parents=True,exist_ok=False)
    (OUTPUT/'source-sha256.json').write_text(json.dumps({name:hashlib.sha256((HERE/name).read_bytes()).hexdigest() for name in
        (*REQUIRED,'sha256_kat_device_profile.py','builtin_init_profile.py','precheck_window_access.py')},indent=2)+'\n')
    result=unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(ReadonlySpanCandidateTests(name) for name in METHODS))
    (OUTPUT/'result.json').write_text(json.dumps(dict(schema='v107-new-type3-readonly-span-tests-v1',selected=list(METHODS),run=result.testsRun,
        failures=len(result.failures),errors=len(result.errors),passed=result.wasSuccessful(),fixture_compiles=ReadonlySpanCandidateTests.compiles,
        fixture_processes=ReadonlySpanCandidateTests.fixture_processes,old_test_methods_run=0,old_decoder_calls=0,
        actual_private_input_reads=0,device_operations=[]),indent=2)+'\n')
    raise SystemExit(0 if result.wasSuccessful() else 1)
