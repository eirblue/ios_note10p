"""Fixed NEW2 + class2 fixture1. No real input, old decoder or device execution."""
import argparse
import ast
import copy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import struct
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import builtin_init_profile as builtin
import kernel_readonly_input as kro
import linux_data_carrier as carrier
import sha256_kat_device_profile as profile
from decode_reservation import checksum

HERE=Path(__file__).resolve().parent
OUTPUT=None
IDENTITY,CYCLE,BOOT='1'*32,'2'*32,'3'*32
CYCLE_SLOT=b'N10_CYCLE_SLOT_UNSET_0123456789A'
METHODS=('test_actual_class2_source_and_late_consumer','test_compact_patch_source_history_runtime_and_ack_before_device')
REQUIRED=(*kro.SOURCES,'linux_data_carrier.c','linux_data_carrier_composition.c','build_builtin_init_image.py')


def geometry():
    base=0x100000;slot=0x2000;descriptor=slot+kro.CAPACITY;init=descriptor+80+0x1000;end=init+0x1000
    raw=bytearray(end);raw[0x1000:0x1021]=CYCLE_SLOT+b'\0';raw[descriptor:descriptor+80]=kro.DESCRIPTOR
    system='\n'.join(f'{base+offset:016x} {kind} {name}' for offset,kind,name in (
        (0,'T','_text'),(0x1000,'R','__start_rodata'),(slot,'r',kro.SLOT),
        (descriptor,'r',kro.DESC),(init,'T','__init_begin'),(end,'B','_end')))
    symbols=f'0000000000000000 {kro.CAPACITY:016x} r {kro.SLOT}\n0000000000000000 0000000000000050 r {kro.DESC}\n'
    sections=f'[ 7] .rodata.n10_kernel_readonly_input PROGBITS 00000000 002000 {kro.CAPACITY:06x} 00 A 0 0 16\n[ 8] .rodata.n10_kernel_readonly_descriptor PROGBITS 00000000 440000 000050 00 A 0 0 16\n'
    table=f'89: 0000000000000000 {kro.CAPACITY} OBJECT LOCAL DEFAULT 7 {kro.SLOT}\n90: 0000000000000000 80 OBJECT LOCAL DEFAULT 8 {kro.DESC}\n'
    return bytes(raw),system,symbols,sections,table


def synthetic_full():
    raw=bytearray(kro.OLD_BYTES);raw[:8]=b'N10DATA1';struct.pack_into('<HHIQQQQ',raw,8,1,128,0,kro.OLD_BYTES,128,kro.STREAM_BYTES,kro.PAYLOAD_BYTES)
    raw[128]=0x5d;struct.pack_into('<IQ',raw,129,1<<23,kro.PAYLOAD_BYTES)
    raw[48:80]=hashlib.sha256(raw[128:128+kro.STREAM_BYTES]).digest();raw[80:112]=bytes.fromhex('99'*32)
    return bytes(raw)


def candidate(slot,image_bytes):
    return dict(device_profile=profile.DATA_PROFILE,data_input_kind=kro.KIND,kernel_readonly_schema=kro.SCHEMA,
        kernel_readonly_slot=slot,kernel_readonly_linked_bytes=59523072,kernel_readonly_image_bytes=image_bytes,
        kernel_readonly_requires_ack=True,data_expectation_mode=kro.MODE,data_expectation_slot=slot,image_expectation_patched=False,
        data_carrier_stage=carrier.STAGE,data_relative_placement_admitted=False,raw_input_binding=False,
        source_head='6'*40,host_profile_source_head='6'*40,data_payload_bytes=kro.PAYLOAD_BYTES,data_payload_sha256='99'*32)


def producer(slot,image_bytes,pins):
    return dict(version='v105',diagnostic_kind=kro.KIND,data_input_kind=kro.KIND,kernel_readonly_schema=kro.SCHEMA,
        kernel_readonly_requires_ack=True,kernel_readonly_default_enabled=False,passed=True,Image_built=True,BOOT_built=False,
        PC_only=False,physical_ready=False,deployment_ready=False,device_authorized=False,device_operations=[],
        data_expectation_mode=kro.MODE,data_expectation_slot=slot,image_expectation_patched=False,external_initrd_capture=False,input_capture_source='late-kernel-readonly-class2',
        permanent_input_storage_bytes=kro.CAPACITY,permanent_descriptor_bytes=80,kernel_readonly_slot=slot,
        kernel_readonly_linked_bytes=59523072,kernel_readonly_image_bytes=image_bytes,image_bytes=image_bytes,
        data_footprint=dict(linked_kernel_bytes=59523072,data_state_bytes=88),source_sha256=pins,
        settings=dict(NOTE10_KERNEL_READONLY_INPUT='y',NOTE10_READONLY_INPUT_PC='n',NOTE10_OWNED_CONTIGUOUS_STAGING='n',NOTE10_CURRENT_OWNED_STAGING='n'),
        ci_context=dict(GITHUB_SHA='6'*40,GITHUB_WORKFLOW_SHA='6'*40,GITHUB_JOB='linux-data-carrier',GITHUB_REPOSITORY='eirblue/ios_note10p',
            GITHUB_WORKFLOW_REF='eirblue/ios_note10p/'+kro.WORKFLOW+'@refs/heads/main',GITHUB_RUN_ID='123',GITHUB_RUN_ATTEMPT='1'))


def frame(marker,body):
    return f'N10BOOTLINK2 boot={BOOT} {marker} {body} checksum={checksum(body.encode()):08x}'


def data_body(**changes):
    row=dict(id=IDENTITY,cycle=CYCLE,kind='result',source=kro.MODE,status='carrier_mismatch',carrier=str(kro.CAPACITY),logical=str(kro.CAPACITY),
        carrier_rc='0',stream='0',payload='0',consumed='0',written='0',calls='0',digest='0'*64,reasons='00000000',expectations='1',captures='0',retained='1',ownership='0',executed='0')
    row.update(changes);return ' '.join(f'{key}={value}' for key,value in row.items())


def actual_function(filename,name,namespace):
    # Execute only this exact production entry body; import no historical actuator/model modules.
    parsed=ast.parse((HERE/filename).read_text())
    target=next(node for node in parsed.body if isinstance(node,ast.FunctionDef) and node.name==name)
    exec(compile(ast.Module(body=[target],type_ignores=[]),str(HERE/filename),'exec'),namespace)
    return namespace[name]


class KernelReadonlyTests(unittest.TestCase):
    compiles=0
    fixture_processes=0

    def test_actual_class2_source_and_late_consumer(self):
        command=['clang-14','-std=gnu11','-O2','-Wall','-Wextra','-Werror',str(HERE/'kernel_readonly_input_fixture.c'),'-o',str(OUTPUT/'kernel-readonly-fixture')]
        (OUTPUT/'fixture-command.json').write_text(json.dumps(command,indent=2)+'\n')
        type(self).compiles+=1;built=subprocess.run(command,capture_output=True,text=True,timeout=60)
        (OUTPUT/'fixture-compile.log').write_text(built.stdout+built.stderr);self.assertEqual(built.returncode,0,built.stderr)
        type(self).fixture_processes+=1;ran=subprocess.run([str(OUTPUT/'kernel-readonly-fixture')],capture_output=True,text=True,timeout=30)
        (OUTPUT/'fixture-output.json').write_text(ran.stdout);(OUTPUT/'fixture-stderr.log').write_text(ran.stderr)
        self.assertEqual(ran.returncode,0,ran.stderr);result=json.loads(ran.stdout)
        self.assertEqual((result['guard_cases'],result['consumer_cases'],result['old_decoder_calls']),(11,12,0))
        for key in ('actual_new_guard_and_consumer','mock_crypto_decoder','input_unchanged','allocation_canaries_and_clear'):self.assertTrue(result[key])

    def test_compact_patch_source_history_runtime_and_ack_before_device(self):
        raw,system,symbols,sections,table=geometry();slot=kro.slot_metadata(raw,system,symbols,sections,table)
        self.assertEqual(slot['descriptor_class'],2)
        old=synthetic_full();compact=kro.compact_bytes(old)
        self.assertEqual(len(compact),kro.CAPACITY);self.assertEqual(compact[:16],old[:16]);self.assertEqual(compact[24:128],old[24:128])
        self.assertEqual(compact[128:128+kro.STREAM_BYTES],old[128:128+kro.STREAM_BYTES]);self.assertEqual(compact[-2733:],bytes(2733))
        source=dict(data_manifest_sha256='a'*64,data_carrier_sha256=carrier.sha(old),data_carrier_bytes=kro.OLD_BYTES,
            data_payload_bytes=kro.PAYLOAD_BYTES,data_payload_sha256='99'*32)
        meta=kro.compact_metadata(compact,source);manifest=json.dumps(meta,sort_keys=True).encode()
        bound=kro.validate_compact(compact,manifest,source)
        row=candidate(slot,len(raw));row.update(bound,image_sha256=carrier.sha(raw))
        patched=kro.patch_image(raw,row,CYCLE,CYCLE_SLOT,compact)
        a=slot['slot']['offset'];b=slot['descriptor']['offset']
        self.assertEqual(len(patched),len(raw));self.assertEqual(patched[a:a+kro.CAPACITY],compact)
        self.assertEqual(patched[b:b+32],raw[b:b+32]);self.assertEqual(patched[b+72:b+80],raw[b+72:b+80])
        self.assertEqual(patched[b+32:b+72],kro.CAPACITY.to_bytes(8,'little')+bytes.fromhex(bound['kernel_readonly_compact_sha256']))
        allowed=((a,a+kro.CAPACITY),(b+32,b+72),(0x1000,0x1020))
        self.assertTrue(all(before==after or any(start<=i<end for start,end in allowed) for i,(before,after) in enumerate(zip(raw,patched))))
        for mutation in ('source_header','compact_padding','payload_field','generic_descriptor','overlap','old_class'):
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):
                if mutation=='source_header':kro.compact_bytes(old[:16]+(kro.OLD_BYTES-1).to_bytes(8,'little')+old[24:])
                elif mutation=='compact_padding':kro.validate_compact(compact[:-1]+b'1',manifest,source)
                elif mutation=='payload_field':kro.validate_compact(compact,json.dumps(dict(meta,payload_sha256='88'*32)).encode(),source)
                elif mutation=='generic_descriptor':
                    bad=bytearray(raw);bad[b]^=1;kro.patch_image(bytes(bad),dict(row,image_sha256=carrier.sha(bytes(bad))),CYCLE,CYCLE_SLOT,compact)
                elif mutation=='overlap':
                    bad=copy.deepcopy(row);bad['kernel_readonly_slot']['slot']['offset']=0x1000;bad['data_expectation_slot']=bad['kernel_readonly_slot']
                    kro.patch_image(raw,bad,CYCLE,CYCLE_SLOT,compact)
                else:kro.slot_metadata(raw.replace(kro.DESCRIPTOR,b'N10ROINPUTPCV1!!'+struct.pack('<IIQQ',1,80,kro.CAPACITY,0)+bytes(40)),system,symbols,sections,table)
        pins={'note10/device_test/'+name:'a'*64 for name in REQUIRED};made=producer(slot,len(raw),pins)
        self.assertFalse(kro.producer_contract(made,'6'*40,producing_sources=pins)['physical_ready'])
        for changes in (dict(version='v103',diagnostic_kind='readonly-input-pc',PC_only=False),dict(kernel_readonly_linked_bytes=kro.BUDGET+1),
                        dict(kernel_readonly_schema='old'),dict(physical_ready=True),dict(data_input_kind='linux-data-carrier')):
            with self.assertRaises(ValueError):kro.producer_contract(dict(made,**changes),'6'*40,producing_sources=pins)
        changed=copy.deepcopy(made);changed['source_sha256']['note10/device_test/kernel_readonly_input.h']='b'*64
        with self.assertRaises(ValueError):kro.producer_contract(changed,'6'*40,producing_sources=pins)
        with self.assertRaisesRegex(ValueError,'ack-kernel-readonly-growth'):kro.require_device_scope(dict(row,physical_ready=True,deployment_ready=True))
        self.assertTrue(kro.require_device_scope(row,True)) # Pure scope check only; no device/plan execution.
        for old_pc in (dict(diagnostic_kind='readonly-input-pc',PC_only=False,physical_ready=True),
                       dict(row,readonly_input_schema='n10-kernel-readonly-input-pc-v1'),dict(data_expectation_mode='kernel-readonly-slot-v1',PC_only=False)):
            with self.assertRaises(ValueError):kro.require_device_scope(old_pc,True)
            with self.assertRaises(ValueError):profile.physical_input_scope(old_pc)
        with tempfile.TemporaryDirectory(dir=OUTPUT) as temp:
            folder=Path(temp);(folder/'build-result.json').write_text(json.dumps(row));(folder/'package-result.json').write_text(json.dumps(row))
            calls=[]
            def no_device(*args,**kwargs):calls.append(True);raise AssertionError('device gate was reached')
            plan=dict(kernel_build=str(folder),stages=[{}])
            run=actual_function('auto_cycle.py','run_plan',dict(Path=Path,validate_plan=lambda *args:plan,
                read=lambda path:json.loads(Path(path).read_text()),preflight=no_device,Adb=no_device))
            with self.assertRaisesRegex(ValueError,'ack-kernel-readonly-growth'):run(folder/'not-read.json','a'*64,folder/'journal',execute=True,adb=object())
            stage=actual_function('stage_phase2.py','stage',dict(Path=Path,json=json,verify_packages=lambda path:[],preflight=no_device))
            with self.assertRaisesRegex(ValueError,'ack-kernel-readonly-growth'):stage(folder,object())
            self.assertEqual(calls,[]);self.assertFalse((folder/'journal').exists())

            # Run the actual entry through the mocked new candidate call chain.
            # Collection performs its real ACK predicate before returning rejected
            # synthetic evidence, so an omitted ACK cannot be hidden by a stub.
            propagated=[];transport_calls=[];partition_phases=[]
            package_row=dict(row,image_expectation_patched=True)
            def stage_mock(packages,adb,*,ack_kernel_readonly_growth=False):
                propagated.append(('stage',ack_kernel_readonly_growth))
                kro.require_device_scope(package_row,ack_kernel_readonly_growth)
                return dict(ram_directory='/tmp/synthetic')
            def precheck_mock(packages,build,backup,adb,staged,*,ack_kernel_readonly_growth=False):
                propagated.append(('precheck',ack_kernel_readonly_growth))
                kro.require_device_scope(package_row,ack_kernel_readonly_growth)
                return dict(ready_for_manual_access_test=True,partition_evidence=dict(status='synthetic'))
            def collector_mock(packages,build,adb,*,ack_kernel_readonly_growth=False):
                propagated.append(('collector',ack_kernel_readonly_growth))
                kro.require_device_scope(package_row,ack_kernel_readonly_growth)
                return dict(directory=str(folder),diagnostic_passed=False,log_selections={})
            class MockTransport:
                serial='synthetic-transport'
                def text(self,*args,**kwargs):
                    transport_calls.append(args)
                    if args==('shell','command','-v','twrp'):return '/sbin/twrp'
                    raise AssertionError('unexpected synthetic transport text')
                def call(self,*args,**kwargs):
                    transport_calls.append(args)
                    if args[:3] in (('shell','twrp','install'),('shell','twrp','reboot')):return b''
                    raise AssertionError('unexpected synthetic transport call')
            def partition_mock(adb,backup,expected,evidence=None):
                partition_phases.append(evidence['phase']);evidence['status']='synthetic'
            item=dict(index=1,cycle=CYCLE,packages=str(folder),kernel_build=str(folder),image_sha256='c'*64)
            complete_plan=dict(kernel_build=str(folder),device_profile=profile.DATA_PROFILE,stages=[item],backup=str(folder),
                image_sha256='c'*64,backup_manifest_sha256='d'*64,identity=IDENTITY,return_timeout_seconds=240)
            namespace=dict(Path=Path,hashlib=hashlib,time=SimpleNamespace(monotonic=lambda:0.0),
                validate_plan=lambda *args:complete_plan,read=lambda path:json.loads(Path(path).read_text()),
                private=lambda path:Path(path),save=lambda path,value:Path(path).write_text(json.dumps(value)),
                preflight=lambda adb:dict(twrp_version='synthetic'),stage=stage_mock,
                verify_packages=lambda path:[dict(mode='diagnostic',payload_sha256='b'*64,file='synthetic.zip')],
                boot_id=lambda adb:'synthetic-before',wait_recovery=lambda *args,**kwargs:'synthetic-after',
                verify_partitions=partition_mock)
            run=actual_function('auto_cycle.py','run_plan',namespace)
            with patch.object(profile,'precheck',side_effect=precheck_mock),patch.object(profile,'collect',side_effect=collector_mock):
                with self.assertRaisesRegex(ValueError,'Diagnostic or automatic-return evidence failed'):
                    run(folder/'not-read.json','a'*64,folder/'ack-journal',execute=True,adb=MockTransport(),ack_kernel_readonly_growth=True)
            self.assertEqual(propagated,[('stage',True),('precheck',True),('collector',True)])
            self.assertEqual(partition_phases,['postinstall-before-reboot','postreturn'])
            self.assertEqual([args[2] for args in transport_calls],['-v','install','reboot'])
            journal=json.loads((folder/'ack-journal/journal.json').read_text())
            self.assertTrue(journal['kernel_readonly_growth_ack']);self.assertEqual(journal['status'],'stopped')
            self.assertFalse(journal['completed'][0]['passed'])

        current=dict(device_profile=profile.DATA_PROFILE,source_head=profile.V104_PROFILE_ORIGIN_HEAD,host_profile_source_head=profile.V104_PROFILE_ORIGIN_HEAD,
            host_profile_source_sha256=dict(profile.V104_PROFILE_ORIGIN_PINS),data_compare_schema=carrier.COMPARE_SCHEMA,
            data_input_range_schema=carrier.RANGE_SCHEMA,data_early_prefix_schema=carrier.EARLY_SCHEMA,data_linked_kernel_bytes=55132160,**carrier.GROWTH_BINDING)
        self.assertEqual(len(profile.host_profile_origin(current)['host_profile_source_sha256']),51)
        with self.assertRaises(ValueError):profile.host_binding(profile.V104_PROFILE_ORIGIN_HEAD)
        plan=dict(device_profile=profile.DATA_PROFILE,current_boot_payload_sha256='a'*64);diag=dict(payload_sha256='a'*64)
        builtin.current_boot_binding(plan,current,diag)
        with self.assertRaises(ValueError):builtin.current_boot_binding(plan,dict(current,source_head='e32ec501551b74b4cca5618ea25245f012656f29'),diag)
        with self.assertRaises(ValueError):builtin.current_boot_binding(plan,current,dict(payload_sha256='b'*64))
        parsed=carrier.decode(frame('N10DATARO1',data_body()),IDENTITY,CYCLE,_source_class=kro.MODE)
        self.assertEqual(parsed['captures'],0);self.assertFalse(parsed['passed'])
        for changes in (dict(source=carrier.MODE),dict(captures='1'),dict(source='kernel-readonly-slot-v1')):
            with self.assertRaises(ValueError):carrier.decode(frame('N10DATARO1',data_body(**changes)),IDENTITY,CYCLE,_source_class=kro.MODE)
        banner='Linux version 4.14.113-v105-kernel-readonly synthetic'
        arms=[frame('N10RET1',f'id={IDENTITY} cycle={CYCLE} phase=0 seq={i} delay_ms=90000 status=0') for i in (0,1)]
        startup=[f'N10ROUTE2 id={IDENTITY} boot={BOOT} cycle={CYCLE} route=builtin exec_attempt=1',f'N10INIT2 id={IDENTITY} boot={BOOT} cycle={CYCLE} route=builtin started=1']
        requests=[frame('N10RET1',f'id={IDENTITY} cycle={CYCLE} phase=1 seq={i} delay_ms=90000 status=0') for i in (0,1)]
        log=('\n'.join(['[    0.000000] '+banner,*arms,*startup,frame('N10DATARO1',data_body()),*requests])+'\n').encode()
        with self.assertRaises(carrier.ComponentObservationError) as failed:kro.decode_selected(log,banner,IDENTITY,CYCLE,expected=dict(row,image_expectation_patched=True))
        evidence=failed.exception.component_evidence;self.assertIn('kernel_readonly_data',evidence)
        self.assertFalse(evidence['functional_acceptance']);self.assertFalse(evidence['hardware_return_proven_by_frames'])


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();OUTPUT=args.output;OUTPUT.mkdir(parents=True,exist_ok=False)
    names=(*REQUIRED,'linux_data_carrier.py','sha256_kat_device_profile.py','builtin_init_profile.py','auto_cycle.py','stage_phase2.py','materialize_auto_cycle.py','prepare_linux_boot.py')
    (OUTPUT/'source-sha256.json').write_text(json.dumps({name:hashlib.sha256((HERE/name).read_bytes()).hexdigest() for name in names},indent=2)+'\n')
    result=unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(KernelReadonlyTests(name) for name in METHODS))
    (OUTPUT/'result.json').write_text(json.dumps(dict(schema='v105-new-kernel-readonly-tests-v1',selected=list(METHODS),run=result.testsRun,
        failures=len(result.failures),errors=len(result.errors),passed=result.wasSuccessful(),fixture_compiles=KernelReadonlyTests.compiles,
        fixture_processes=KernelReadonlyTests.fixture_processes,old_PC_positive_tests=0,old_decoder_calls=0,
        old_test_methods_run=0,real_private_input_reads=0,device_operations=[]),indent=2)+'\n')
    raise SystemExit(0 if result.wasSuccessful() else 1)
