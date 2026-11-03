"""Fixed NEW2, new composite fixture1/process1; no real inputs or device."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

import kernel_readonly_input as kro
import linux_data_carrier as data
import sha256_kat_device_profile as profile
from decode_reservation import checksum

HERE=Path(__file__).resolve().parent
OUTPUT=None
IDENTITY,CYCLE,BOOT='1'*32,'2'*32,'3'*32
METHODS=('test_actual_composite_precondition_and_late_adapter','test_closed_span_producer_parser_partial_evidence_and_PC_refusal')
REQUIRED=(*kro.SOURCES,*kro.SPAN_SOURCES,'linux_data_carrier.c','linux_data_carrier_composition.c','build_builtin_init_image.py')


def frame(marker,body,boot=BOOT):
    return f'N10BOOTLINK2 boot={boot} {marker} {body} checksum={checksum(body.encode()):08x}'


def slot():
    def extent(symbol,section,offset,size,preimage,index):
        return dict(symbol=symbol,section=section,offset=offset,bytes=size,alignment=16,readonly_flags='A',
            preimage_sha256=preimage,object_section_index=index,object_symbol_offset=0)
    return dict(schema=kro.SCHEMA,source=kro.MODE,capacity=kro.CAPACITY,descriptor_bytes=80,
        slot=extent(kro.SLOT,'.rodata.n10_kernel_readonly_input',8192,kro.CAPACITY,data.sha(bytes(kro.CAPACITY)),7),
        descriptor=extent(kro.DESC,'.rodata.n10_kernel_readonly_descriptor',8192+kro.CAPACITY,80,data.sha(kro.DESCRIPTOR),8),
        generic=True,patched=False,permanent_input_bytes=kro.CAPACITY,permanent_descriptor_bytes=80,
        physical_ready=False,descriptor_class=2,boot_page=2048)


def producer(pins):
    record=slot()
    return dict(version='v106',diagnostic_kind=kro.SPAN_KIND,data_input_kind=kro.KIND,kernel_readonly_schema=kro.SCHEMA,
        kernel_readonly_span_schema=kro.SPAN_SCHEMA,kernel_readonly_span_default_enabled=False,
        kernel_readonly_span=dict(schema=kro.SPAN_SCHEMA,kernel_bytes=59518976,text_prefix_bytes=4096,
            slot_contained=True,descriptor_contained=True,disjoint=True,source='linked-kernel',phase='pre_descriptor',hardware=False,ownership=False),
        kernel_readonly_requires_ack=True,kernel_readonly_default_enabled=False,passed=True,Image_built=True,BOOT_built=False,
        PC_only=True,physical_ready=False,deployment_ready=False,device_authorized=False,device_operations=[],
        data_expectation_mode=kro.MODE,data_expectation_slot=record,image_expectation_patched=False,
        external_initrd_capture=False,input_capture_source='late-kernel-readonly-class2',
        permanent_input_storage_bytes=kro.CAPACITY,permanent_descriptor_bytes=80,additional_linked_storage_bytes=kro.CAPACITY+80,
        kernel_readonly_slot=record,kernel_readonly_linked_bytes=59523072,kernel_readonly_image_bytes=50804748,image_bytes=50804748,
        data_footprint=dict(linked_kernel_bytes=59523072,data_state_bytes=88),source_sha256=pins,
        settings=dict(NOTE10_KERNEL_READONLY_INPUT='y',NOTE10_KERNEL_READONLY_SPAN_PC='y',NOTE10_READONLY_INPUT_PC='n',NOTE10_OWNED_CONTIGUOUS_STAGING='n',NOTE10_CURRENT_OWNED_STAGING='n'),
        ci_context=dict(GITHUB_SHA='6'*40,GITHUB_WORKFLOW_SHA='6'*40,GITHUB_JOB='linux-data-carrier',GITHUB_REPOSITORY='eirblue/ios_note10p',
            GITHUB_WORKFLOW_REF='eirblue/ios_note10p/'+kro.WORKFLOW+'@refs/heads/main',GITHUB_RUN_ID='123',GITHUB_RUN_ATTEMPT='1'))


def data_body():
    values=dict(id=IDENTITY,cycle=CYCLE,kind='result',source=kro.MODE,status='unavailable',carrier=str(kro.CAPACITY),logical='0',
        carrier_rc='0',stream='0',payload='0',consumed='0',written='0',calls='0',digest='0'*64,reasons='00000400',
        expectations='0',captures='0',retained='0',ownership='0',executed='0')
    return ' '.join(f'{key}={value}' for key,value in values.items())


class KernelReadonlySpanTests(unittest.TestCase):
    compiles=0
    fixture_processes=0

    def test_actual_composite_precondition_and_late_adapter(self):
        command=['clang-14','-std=gnu11','-O2','-Wall','-Wextra','-Werror',str(HERE/'kernel_readonly_span_fixture.c'),'-o',str(OUTPUT/'kernel-span-fixture')]
        (OUTPUT/'fixture-command.json').write_text(json.dumps(command,indent=2)+'\n')
        type(self).compiles+=1;built=subprocess.run(command,capture_output=True,text=True,timeout=60)
        (OUTPUT/'fixture-compile.log').write_text(built.stdout+built.stderr);self.assertEqual(built.returncode,0,built.stderr)
        type(self).fixture_processes+=1;ran=subprocess.run([str(OUTPUT/'kernel-span-fixture')],capture_output=True,text=True,timeout=30)
        (OUTPUT/'fixture-output.json').write_text(ran.stdout);(OUTPUT/'fixture-stderr.log').write_text(ran.stderr)
        self.assertEqual(ran.returncode,0,ran.stderr);row=json.loads(ran.stdout)
        self.assertEqual(row['guard_cases'],15)
        self.assertTrue(all(row[key] for key in ('actual_adapter','descriptor_reads_blocked','canaries')))
        self.assertTrue(all(row[key]==0 for key in ('input_byte_reads','hashes','allocations','old_decoder_calls')))

    def test_closed_span_producer_parser_partial_evidence_and_PC_refusal(self):
        fixture=json.loads((OUTPUT/'fixture-output.json').read_text())
        bound=int(dict(token.split('=') for token in fixture['checked'].split())['kernel_bytes'])
        for state in ('checked','refused','not_reached'):
            result=kro.decode_span(frame('N10DATASPAN1',fixture[state]),IDENTITY,CYCLE,BOOT,bound)
            self.assertEqual(result['state'],state);self.assertFalse(result['hardware_mapping_attested'])
            self.assertFalse(result['global_RAM_ownership'])
        original=fixture['checked'];wire=frame('N10DATASPAN1',original)
        mutations=[original.replace('state=checked','state=unknown'),original.replace('ownership=0','ownership=1'),
            original.replace('disjoint=1','disjoint=0'),original.replace('kernel_bytes='+str(bound),'kernel_bytes=1'),
            original.replace('admission_called=1','admission_called=0'),original.replace('reasons=00000000','reasons=00000010'),
            original+' extra=0',original.replace('kernel_checked=1','kernel_checked=0'),
            original+' '*416]
        for body in mutations:
            with self.subTest(body=body),self.assertRaises(ValueError):kro.decode_span(frame('N10DATASPAN1',body),IDENTITY,CYCLE,BOOT,bound)
        for bad in ('',wire+'\n'+wire,frame('N10DATASPAN1',original,boot='4'*32),wire[:-1]+('0' if wire[-1]!='0' else '1'),wire.replace('N10DATASPAN1','N10DATASPAN2')):
            with self.assertRaises(ValueError):kro.decode_span(bad,IDENTITY,CYCLE,BOOT,bound)
        with self.assertRaises(ValueError):kro.decode_span(wire,IDENTITY,CYCLE,BOOT,bound+1)
        pins={'note10/device_test/'+name:'a'*64 for name in REQUIRED};row=producer(pins)
        self.assertTrue(kro.span_producer_contract(row,'6'*40,producing_sources=pins)['PC_only'])
        for key,value in (('PC_only',False),('diagnostic_kind',kro.KIND),('kernel_readonly_span_schema',None),('version','v105')):
            bad=copy.deepcopy(row);bad[key]=value
            with self.assertRaises(ValueError):kro.span_producer_contract(bad,'6'*40,producing_sources=pins)
        bad=copy.deepcopy(row);bad['kernel_readonly_span']['text_prefix_bytes']+=16
        with self.assertRaises(ValueError):kro.span_producer_contract(bad,'6'*40,producing_sources=pins)
        bad=copy.deepcopy(row);bad['source_sha256']['note10/device_test/kernel_readonly_span.h']='b'*64
        with self.assertRaises(ValueError):kro.span_producer_contract(bad,'6'*40,producing_sources=pins)
        with self.assertRaises(ValueError):kro.span_producer_contract(row,kro.HISTORICAL_HEAD,producing_sources=pins)
        # Changed live builder must not invalidate the exact accepted e49 source closure.
        old=copy.deepcopy(row)
        for key in ('kernel_readonly_span','kernel_readonly_span_schema','kernel_readonly_span_default_enabled'):old.pop(key)
        old.update(version='v105',diagnostic_kind=kro.KIND,PC_only=False)
        old['settings'].pop('NOTE10_KERNEL_READONLY_SPAN_PC')
        old['ci_context'].update(GITHUB_SHA=kro.HISTORICAL_HEAD,GITHUB_WORKFLOW_SHA=kro.HISTORICAL_HEAD)
        old['source_sha256']={key:value for key,value in profile.V105_CANDIDATE_ORIGIN_PINS.items() if key in
            {'note10/device_test/'+name for name in (*kro.SOURCES,'linux_data_carrier.c','linux_data_carrier_composition.c','build_builtin_init_image.py')}}
        old['source_sha256']['note10/device_test/build_builtin_init_image.py']=kro.HISTORICAL_BUILDER_SHA256
        self.assertTrue(kro.producer_contract(old,kro.HISTORICAL_HEAD,historical_origin=kro.HISTORICAL_HEAD)['candidate_only'])
        with self.assertRaises(ValueError):kro.producer_contract(old,kro.HISTORICAL_HEAD)
        # Intrinsic actual symbol metadata checks a complete _stext.._end interval.
        base=0x100000;record=slot();linked=row['data_footprint']['linked_kernel_bytes']
        symbols='\n'.join(f'{value:016x} {kind} {name}' for value,kind,name in ((base,'T','_text'),(base+4096,'T','_stext'),
            (base+linked,'B','_end'),(base+record['slot']['offset'],'r',kro.SLOT),(base+record['descriptor']['offset'],'r',kro.DESC)))
        self.assertEqual(kro.span_footprint(symbols,row['data_footprint'],record),row['kernel_readonly_span'])
        with self.assertRaises(ValueError):kro.span_footprint(symbols.replace('_stext','missing'),row['data_footprint'],record)
        # Missing/malformed NEW companion retains already parsed DATA and same-boot presence.
        banner='Linux version 4.14.113-v106-kernel-span-pc synthetic'
        arms=[frame('N10RET1',f'id={IDENTITY} cycle={CYCLE} phase=0 seq={i} delay_ms=90000 status=0') for i in (0,1)]
        startup=[f'N10ROUTE2 id={IDENTITY} boot={BOOT} cycle={CYCLE} route=builtin exec_attempt=1',f'N10INIT2 id={IDENTITY} boot={BOOT} cycle={CYCLE} route=builtin started=1']
        requests=[frame('N10RET1',f'id={IDENTITY} cycle={CYCLE} phase=1 seq={i} delay_ms=90000 status=0') for i in (0,1)]
        context=producer({'note10/device_test/'+name:data.sha((HERE/name).read_bytes()) for name in REQUIRED})
        context['kernel_readonly_span'].update(kernel_bytes=bound,text_prefix_bytes=0)
        context['data_footprint']['linked_kernel_bytes']=bound
        context.update(kernel_readonly_linked_bytes=bound,kernel_readonly_image_bytes=bound,image_bytes=bound)
        context['kernel_readonly_slot']['slot']['offset']=0
        context['kernel_readonly_slot']['descriptor']['offset']=kro.CAPACITY+16
        for companion,has_span in (('',False),(wire.replace('disjoint=1','disjoint=0'),False),(wire,True)):
            log=('\n'.join(['[    0.000000] '+banner,*arms,*startup,frame('N10DATARO1',data_body()),companion,*requests])+'\n').encode()
            with self.assertRaises(data.ComponentObservationError) as failed:kro.decode_span_selected(log,banner,IDENTITY,CYCLE,expected=context)
            evidence=failed.exception.component_evidence
            self.assertIn('kernel_readonly_data',evidence);self.assertIn('structural_presence',evidence)
            self.assertEqual('kernel_readonly_span' in evidence,has_span)
            self.assertFalse(evidence['functional_acceptance']);self.assertFalse(evidence['hardware_return_proven_by_frames'])
        # Both actual device-entry guards reject new PC domain even with forged readiness and growth ACK.
        forged=dict(row,PC_only=False,physical_ready=True,deployment_ready=True,device_authorized=True)
        with self.assertRaises(ValueError):kro.require_device_scope(forged,True)
        with self.assertRaises(ValueError):profile.physical_input_scope(forged)
        from precheck_window_access import make_install_battery_policy
        self.assertEqual(make_install_battery_policy(declared_test_version='v106')['effective_minimum_percent'],10)
        with patch('precheck_window_access._approval_record',side_effect=AssertionError('must refuse before approval/device')):
            with self.assertRaises(ValueError):make_install_battery_policy(use_v105_5pct_exception=True,declared_test_version='v106',
                scope=dict(source_head=kro.HISTORICAL_HEAD),growth_ack=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();OUTPUT=args.output;OUTPUT.mkdir(parents=True,exist_ok=False)
    (OUTPUT/'source-sha256.json').write_text(json.dumps({name:hashlib.sha256((HERE/name).read_bytes()).hexdigest() for name in
        (*REQUIRED,'linux_data_carrier.py','sha256_kat_device_profile.py','builtin_init_profile.py','precheck_window_access.py')},indent=2)+'\n')
    result=unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(KernelReadonlySpanTests(name) for name in METHODS))
    (OUTPUT/'result.json').write_text(json.dumps(dict(schema='v106-new-kernel-span-tests-v1',selected=list(METHODS),run=result.testsRun,
        failures=len(result.failures),errors=len(result.errors),passed=result.wasSuccessful(),fixture_compiles=KernelReadonlySpanTests.compiles,
        fixture_processes=KernelReadonlySpanTests.fixture_processes,old_test_methods_run=0,old_decoder_calls=0,
        actual_private_input_reads=0,device_operations=[]),indent=2)+'\n')
    raise SystemExit(0 if result.wasSuccessful() else 1)
