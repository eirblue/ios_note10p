"""One new host-only packing-revision method; no real input or old methods."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import kernel_readonly_input as kro
import linux_data_carrier as carrier
import sha256_kat_device_profile as profile
from prepare_linux_boot import payload_size

OUTPUT=None
METHOD='test_compact_capacity_retained56_and_resume_without_materialize'


def synthetic_profile():
    slot_offset=4096;descriptor_offset=slot_offset+kro.CAPACITY
    def part(symbol,section,offset,size,preimage,index):
        return dict(symbol=symbol,section=section,offset=offset,bytes=size,alignment=16,readonly_flags='A',
            preimage_sha256=hashlib.sha256(preimage).hexdigest(),object_section_index=index,object_symbol_offset=0)
    slot=dict(schema=kro.SCHEMA,source=kro.MODE,capacity=kro.CAPACITY,descriptor_bytes=80,
        slot=part(kro.SLOT,'.rodata.n10_kernel_readonly_input',slot_offset,kro.CAPACITY,bytes(kro.CAPACITY),7),
        descriptor=part(kro.DESC,'.rodata.n10_kernel_readonly_descriptor',descriptor_offset,80,kro.DESCRIPTOR,8),
        generic=True,patched=False,permanent_input_bytes=kro.CAPACITY,permanent_descriptor_bytes=80,
        physical_ready=False,descriptor_class=2,boot_page=2048)
    return dict(device_profile=profile.DATA_PROFILE,source_head=kro.HISTORICAL_HEAD,host_profile_source_head=kro.HISTORICAL_HEAD,
        host_profile_source_sha256=dict(profile.V105_CANDIDATE_ORIGIN_PINS),data_input_kind=kro.KIND,kernel_readonly_schema=kro.SCHEMA,
        kernel_readonly_slot=slot,data_expectation_slot=slot,kernel_readonly_image_bytes=kro.CAPACITY+16384,
        kernel_readonly_linked_bytes=59523072,kernel_readonly_requires_ack=True,data_expectation_mode=kro.MODE,
        image_expectation_patched=False,data_carrier_stage=carrier.STAGE,data_relative_placement_admitted=False,raw_input_binding=False,
        kernel_readonly_compact_sha256='d'*64,kernel_readonly_compact_bytes=kro.CAPACITY,kernel_readonly_compact_manifest_sha256='e'*64,
        data_manifest_sha256='a'*64,data_carrier_sha256='b'*64,data_carrier_bytes=kro.OLD_BYTES,
        data_payload_sha256='c'*64,data_payload_bytes=kro.PAYLOAD_BYTES,image_sha256='f'*64,
        effective_config_sha256='a'*64,build_evidence_id='1'*32)


class PackingRevisionTests(unittest.TestCase):
    def test_compact_capacity_retained56_and_resume_without_materialize(self):
        with self.assertRaises(ValueError):payload_size(50804748,kro.OLD_BYTES,2048,57671680)
        needed=payload_size(50804748,kro.CAPACITY,2048,57671680)
        self.assertLess(needed,57671680);self.assertEqual(needed,55248896)
        generic=synthetic_profile()
        self.assertEqual(len(profile.host_profile_origin(generic)['host_profile_source_sha256']),56)
        with self.assertRaises(ValueError):profile.host_binding(kro.HISTORICAL_HEAD)
        with self.assertRaises(ValueError):profile.physical_input_scope(dict(generic,data_expectation_mode='kernel-readonly-slot-v1',PC_only=False))
        with tempfile.TemporaryDirectory(dir=OUTPUT) as temp:
            folder=Path(temp);template=folder/'template';template.mkdir()
            source=folder/'failed/cycle-01/kernel-build';source.mkdir(parents=True)
            backup=folder/'backup';backup.mkdir();current=folder/'current';current.mkdir()
            (backup/'backup-manifest.json').write_text('{}');(current/'package-result.json').write_text('{}')
            cycle='2'*32;template_sha='3'*64;source_image=hashlib.sha256(b'synthetic-patched-image').hexdigest()
            reuse=dict(template=str(template),template_profile_sha256=template_sha,source_variant=str(source),
                source_report_sha256='4'*64,source_image_sha256=source_image,cycle=cycle,
                operator_receipt=str(folder/'operator.json'),operator_receipt_sha256='5'*64)
            original=dict(generic,auto_cycle_variant=True,auto_cycle_token=cycle,auto_cycle_template=str(template),
                auto_cycle_template_report_sha256='6'*64,auto_cycle_template_image_sha256=generic['image_sha256'],
                image_sha256=source_image,image_expectation_patched=True)
            operator=dict(schema='v105-offline-preparation-operator-receipt-v1',status='stopped_on_plan_prepare_failure',source_head=kro.HISTORICAL_HEAD,
                template=dict(exit_code=0,invocation_count=1,path=str(template),build_result_sha256='6'*64),
                plan=dict(exit_code=1,invocation_count=1,exact_failure='Prototype exceeds actual boot partition',plan_json_exists=False,partial_cycle_packages_exist=False))
            self.assertEqual(kro.reuse_metadata(generic,original,operator,reuse,'6'*64),original)
            for change in (dict(original,image_expectation_patched=False),dict(original,auto_cycle_token='7'*32),dict(original,source_head='8'*40)):
                with self.assertRaises(ValueError):kro.reuse_metadata(generic,change,operator,reuse,'6'*64)
            bad=copy.deepcopy(operator);bad['plan']['plan_json_exists']=True
            with self.assertRaises(ValueError):kro.reuse_metadata(generic,original,bad,reuse,'6'*64)
            (template/'build-result.json').write_text(json.dumps(generic));(template/'device-profile.json').write_text('{}')
            (source/'build-result.json').write_text(json.dumps(original))
            for name,value in (('Image',b'synthetic-patched-image'),('handoff.config',b'synthetic config'),
                ('kernel-readonly.data',b'synthetic compact'),('kernel-readonly-compact.json',b'{}')):(source/name).write_bytes(value)
            (folder/'operator.json').write_text(json.dumps(operator))
            baseline={name:(source/name).read_bytes() for name in ('Image','build-result.json','handoff.config')}
            calls=[]
            def authenticate(record):
                calls.append('authenticate');self.assertEqual(record['source_variant'],str(source));return original
            def prepare(backup_path,target,twrp,mkbootimg,boot,token):
                calls.append('pack');report=json.loads((target/'build-result.json').read_text())
                self.assertEqual(report['kernel_readonly_external_choice'],'compact-v1');self.assertEqual(token,cycle)
                self.assertEqual((target/'Image').read_bytes(),baseline['Image']);boot.write_bytes(b'synthetic BOOT')
            def build(backup_path,boot,packages,current_path):
                calls.append('packages');packages.mkdir();(packages/'package-result.json').write_text('{}')
            def validate(path,pin):
                calls.append('intrinsic-plan');plan=json.loads(path.read_text())
                self.assertEqual(plan['stages'][0]['cycle'],cycle);self.assertEqual(plan['kernel_readonly_external_choice'],'compact-v1')
                self.assertEqual(plan['kernel_readonly_packing_host']['host_profile_source_head'],'9'*40)
                self.assertEqual(plan['current_boot_payload_sha256'],'a'*64)
            no_replay=AssertionError('duplicate derivation/template/materialize/repatch is forbidden')
            with patch.object(kro,'authenticate_reuse',side_effect=authenticate),patch('prepare_linux_boot.prepare',side_effect=prepare),                patch('build_boot_test_packages.build',side_effect=build),patch('stage_phase2.verify_packages',return_value=[dict(mode='diagnostic',payload_sha256='a'*64)]),                patch.object(profile,'validate_plan',side_effect=validate),patch('materialize_auto_cycle.materialize',side_effect=no_replay),                patch('materialize_auto_cycle.bound_image',side_effect=no_replay),patch.object(kro,'patch_image',side_effect=no_replay),                patch.object(kro,'derive',side_effect=no_replay),patch.object(profile,'prepare_template',side_effect=no_replay):
                result=kro.resume_pack(template=template,template_profile_sha256=template_sha,materialized=source,
                    materialized_report_sha256='4'*64,materialized_image_sha256=source_image,operator_receipt=folder/'operator.json',
                    operator_receipt_sha256='5'*64,backup=backup,twrp=folder/'twrp',mkbootimg=folder/'mkbootimg',
                    current_packages=current,output=folder/'revision1',host_source_head='9'*40)
            self.assertEqual(calls,['authenticate','pack','packages','intrinsic-plan'])
            self.assertEqual(result['native_source_head'],kro.HISTORICAL_HEAD)
            self.assertEqual(result['executing_host']['host_profile_source_head'],'9'*40)
            self.assertEqual(result['device_operations'],[])
            for name,value in baseline.items():self.assertEqual((source/name).read_bytes(),value)
            wrapper=json.loads((folder/'revision1/cycle-01/kernel-build/build-result.json').read_text())
            self.assertEqual(wrapper['host_profile_source_head'],kro.HISTORICAL_HEAD)
            self.assertEqual(kro.packing_scope(wrapper)['new_external_bytes'],kro.CAPACITY)
            forged=copy.deepcopy(wrapper);forged['kernel_readonly_external_choice']='legacy-full'
            with self.assertRaises(ValueError):kro.packing_scope(forged)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();OUTPUT=args.output;OUTPUT.mkdir(parents=True,exist_ok=False)
    result=unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite([PackingRevisionTests(METHOD)]))
    (OUTPUT/'result.json').write_text(json.dumps(dict(schema='v105-packing-rev1-new1',selected=[METHOD],run=result.testsRun,
        failures=len(result.failures),errors=len(result.errors),passed=result.wasSuccessful(),C_fixture_compiles=0,Image_builds=0,
        old_test_methods=0,actual_private_calls=0,device_operations=[]),indent=2)+'\n')
    raise SystemExit(0 if result.wasSuccessful() else 1)
