"""Exactly NEW2 + one actual new PC guard/consumer fixture; CI first use only."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import readonly_input_pc as pc
import sha256_kat_device_profile as profile

HERE=Path(__file__).resolve().parent
OUTPUT=None
METHODS=('test_actual_readonly_admission_and_late_consumer','test_intrinsic_slot_context_and_unconditional_physical_refusal')
REQUIRED=(*pc.SOURCES,'linux_data_carrier.c','linux_data_carrier_composition.c','build_builtin_init_image.py')


def geometry():
    start=0x100000
    slot=0x2000
    descriptor=slot+pc.CAPACITY
    init=descriptor+80+0x1000
    end=init+0x1000
    raw=bytearray(end)
    raw[descriptor:descriptor+80]=pc.DESCRIPTOR
    system='\n'.join(f'{start+offset:016x} {kind} {name}' for offset,kind,name in (
        (0,'T','_text'),(0x1000,'R','__start_rodata'),(slot,'r',pc.SLOT),
        (descriptor,'r',pc.DESC),(init,'T','__init_begin'),(end,'B','_end')))
    symbols=f'0000000000000000 {pc.CAPACITY:016x} r {pc.SLOT}\n0000000000000000 0000000000000050 r {pc.DESC}\n'
    sections=f'[ 7] .rodata.n10_readonly_input PROGBITS 00000000 002000 {pc.CAPACITY:06x} 00 A 0 0 16\n[ 8] .rodata.n10_readonly_descriptor PROGBITS 00000000 440000 000050 00 A 0 0 16\n'
    table=f'89: 0000000000000000 {pc.CAPACITY} OBJECT LOCAL DEFAULT 7 {pc.SLOT}\n90: 0000000000000000 80 OBJECT LOCAL DEFAULT 8 {pc.DESC}\n'
    return bytes(raw),system,symbols,sections,table


def producer(slot,image_bytes,pins):
    source='1'*40
    return dict(passed=True,Image_built=True,BOOT_built=False,version='v103',diagnostic_kind=pc.KIND,
        PC_only=True,physical_ready=False,deployment_ready=False,device_authorized=False,device_operations=[],
        readonly_input_schema=pc.SCHEMA,data_expectation_mode=pc.MODE,readonly_default_enabled=False,
        readonly_input_slot=slot,permanent_input_storage_bytes=pc.CAPACITY,permanent_descriptor_bytes=80,
        data_footprint=dict(data_state_bytes=88),image_bytes=image_bytes,source_sha256=pins,
        settings=dict(NOTE10_READONLY_INPUT_PC='y',NOTE10_OWNED_CONTIGUOUS_STAGING='n',NOTE10_CURRENT_OWNED_STAGING='n'),
        external_initrd_capture=False,input_capture_source='late-kernel-readonly-slot-only',
        ci_context=dict(GITHUB_SHA=source,GITHUB_WORKFLOW_SHA=source,GITHUB_JOB='linux-data-carrier',
            GITHUB_REPOSITORY='eirblue/ios_note10p',GITHUB_WORKFLOW_REF='eirblue/ios_note10p/'+pc.WORKFLOW+'@refs/heads/main',
            GITHUB_RUN_ID='123',GITHUB_RUN_ATTEMPT='1'))


class ReadonlyInputPCTests(unittest.TestCase):
    compiles=0
    fixture_processes=0

    def test_actual_readonly_admission_and_late_consumer(self):
        command=['clang-14','-std=gnu11','-O2','-Wall','-Wextra','-Werror',str(HERE/'readonly_input_pc_fixture.c'),
            '-o',str(OUTPUT/'readonly-input-fixture')]
        (OUTPUT/'fixture-command.json').write_text(json.dumps(command,indent=2)+'\n')
        type(self).compiles+=1
        built=subprocess.run(command,capture_output=True,text=True,timeout=60)
        (OUTPUT/'fixture-compile.log').write_text(built.stdout+built.stderr)
        self.assertEqual(built.returncode,0,built.stderr)
        type(self).fixture_processes+=1
        ran=subprocess.run([str(OUTPUT/'readonly-input-fixture')],capture_output=True,text=True,timeout=30)
        (OUTPUT/'fixture-output.json').write_text(ran.stdout)
        (OUTPUT/'fixture-stderr.log').write_text(ran.stderr)
        self.assertEqual(ran.returncode,0,ran.stderr)
        result=json.loads(ran.stdout)
        self.assertEqual((result['guard_cases'],result['consumer_cases'],result['old_decoder_calls']),(10,12,0))
        for field in ('actual_new_guard_and_consumer','mock_crypto_decoder','input_unchanged','allocation_canaries_and_clear'):
            self.assertIs(result[field],True)

    def test_intrinsic_slot_context_and_unconditional_physical_refusal(self):
        raw,system,symbols,sections,table=geometry()
        slot=pc.slot_metadata(raw,system,symbols,sections,table)
        self.assertEqual(slot['permanent_input_bytes'],4440064)
        self.assertTrue(pc.metadata_contract(slot,len(raw)))
        for mutate in ('writable','executable','wrong_size','alignment','linked_offset','duplicate','descriptor','nonzero_input','wrong_object_section','wrong_object_offset'):
            r,m,y,c,t=raw,system,symbols,sections,table
            if mutate=='writable': c=c.replace('00 A ','00 WA ',1)
            if mutate=='executable': c=c.replace('00 A ','00 AX ',1)
            if mutate=='wrong_size': y=y.replace(f'{pc.CAPACITY:016x}',f'{pc.CAPACITY-16:016x}',1)
            if mutate=='alignment': c=c.replace('0 0 16','0 0 8',1)
            if mutate=='linked_offset': m=m.replace(f'{0x102000:016x}',f'{0x102010:016x}',1)
            if mutate=='duplicate': m+='\n'+m.splitlines()[2]
            if mutate=='descriptor': r=raw.replace(pc.DESCRIPTOR,bytes(80),1)
            if mutate=='nonzero_input': r=raw[:0x2000]+b'1'+raw[0x2001:]
            if mutate=='wrong_object_section': t=t.replace('DEFAULT 7','DEFAULT 8',1)
            if mutate=='wrong_object_offset': t=t.replace('0000000000000000','0000000000000010',1)
            with self.subTest(mutation=mutate),self.assertRaises(ValueError): pc.slot_metadata(r,m,y,c,t)
        pins={'note10/device_test/'+name:'a'*64 for name in REQUIRED}
        result=producer(slot,len(raw),pins)
        self.assertFalse(pc.pc_contract(result,'1'*40,producing_sources=pins)['physical_ready'])
        for mutate in ('source','missing_source','ready','kind','ci','slot','source_mode','capture'):
            bad=copy.deepcopy(result)
            if mutate=='source': bad['source_sha256']['note10/device_test/readonly_input_pc.h']='b'*64
            if mutate=='missing_source': del bad['source_sha256']['note10/device_test/readonly_input_pc.h']
            if mutate=='ready': bad['physical_ready']=True
            if mutate=='kind': bad['diagnostic_kind']='linux-data-carrier'
            if mutate=='ci': bad['ci_context']['GITHUB_WORKFLOW_SHA']='2'*40
            if mutate=='slot': bad['readonly_input_slot']['slot']['readonly_flags']='WA'
            if mutate=='source_mode': bad['data_expectation_mode']='image-slot-logical-v2'
            if mutate=='capture': bad['external_initrd_capture']=True
            with self.subTest(mutation=mutate),self.assertRaises(ValueError): pc.pc_contract(bad,'1'*40,producing_sources=pins)
        for claims in (dict(PC_only=False,physical_ready=True,device_authorized=True,deployment_ready=True),
                       dict(PC_only=False,diagnostic_kind='linux-data-carrier',physical_ready=True)):
            with self.assertRaises(ValueError): profile.physical_input_scope(dict(result,**claims))
        forged=dict(diagnostic_kind=pc.KIND,PC_only=False,physical_ready=True,device_profile=profile.DATA_PROFILE)
        with self.assertRaises(ValueError): profile.physical_input_scope(forged)
        with self.assertRaises(ValueError): profile.package_scope(forged)
        with tempfile.TemporaryDirectory(dir=OUTPUT) as temp:
            source=Path(temp); (source/'arch/arm64/kernel').mkdir(parents=True)
            (source/'drivers/misc').mkdir(parents=True)
            original=b'fixture original setup; no input hook\n'
            (source/'arch/arm64/kernel/setup.c').write_bytes(original)
            config=source/'drivers/misc/note10_sha256_kat.Kconfig';config.write_bytes(b'fixture baseline\n')
            def baseline(target,identity):
                (target/'arch/arm64/kernel/setup.c').write_bytes(b'synthetic inherited hook')
                return {}
            with patch('linux_data_carrier.install',side_effect=baseline): pc.install(source,'1'*32)
            composition=(source/'drivers/misc/note10_sha256_kat.c').read_text()
            self.assertIn('#ifdef CONFIG_NOTE10_READONLY_INPUT_PC\n#define N10_DATA_READONLY_PC 1\n#else\n#define N10_DATA_COMPARE_EVIDENCE 1',composition)
            self.assertEqual((source/'arch/arm64/kernel/setup.c').read_bytes(),original)
            self.assertIn('config NOTE10_READONLY_INPUT_PC',config.read_text())
            self.assertIn('\tdefault n',config.read_text())
        retained=dict(device_profile=profile.DATA_PROFILE,source_head=profile.V102_PROFILE_ORIGIN_HEAD,
            host_profile_source_head=profile.V102_PROFILE_ORIGIN_HEAD,host_profile_source_sha256=dict(profile.V102_PROFILE_ORIGIN_PINS),
            data_compare_schema='n10-data-compare-v2',data_input_range_schema='n10-data-range-v1',
            data_early_prefix_schema='n10-data-early-prefix-v1',data_linked_kernel_bytes=4096)
        self.assertEqual(len(profile.host_profile_origin(retained)['host_profile_source_sha256']),43)
        with self.assertRaises(ValueError): profile.host_binding(profile.V102_PROFILE_ORIGIN_HEAD)
        retained['readonly_input_schema']=pc.SCHEMA
        with self.assertRaises(ValueError): profile.host_profile_origin(retained)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();OUTPUT=args.output;OUTPUT.mkdir(parents=True,exist_ok=False)
    names=(*REQUIRED,'sha256_kat_device_profile.py')
    (OUTPUT/'source-sha256.json').write_text(json.dumps({name:hashlib.sha256((HERE/name).read_bytes()).hexdigest() for name in names},indent=2)+'\n')
    result=unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(ReadonlyInputPCTests(name) for name in METHODS))
    (OUTPUT/'result.json').write_text(json.dumps(dict(schema='v103-new-readonly-input-PC-tests-v1',selected=list(METHODS),
        run=result.testsRun,failures=len(result.failures),errors=len(result.errors),passed=result.wasSuccessful(),
        fixture_compiles=ReadonlyInputPCTests.compiles,fixture_processes=ReadonlyInputPCTests.fixture_processes,
        native_real_crypto_calls=0,old_decoder_calls=0,old_test_methods_run=0,private_input_reads=0,device_operations=[]),indent=2)+'\n')
    raise SystemExit(0 if result.wasSuccessful() else 1)
