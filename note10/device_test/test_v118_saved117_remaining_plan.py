"""One new synthetic saved117 remainder/domain test; no old methods or real assets."""
import argparse
from contextlib import ExitStack, contextmanager
import hashlib
import json
import runpy
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

import type3_remaining_plan as saved
import native_scoped_output_admission as native
import type3_remaining_pack as oldpack
import sha256_kat_device_profile as profile
import type3_admission as typed
import kernel_readonly_span_candidate as ro3
import kernel_readonly_input as physical
import linux_data_carrier as data
import builtin_init_profile as builtin
from prepare_linux_boot import MKBOOTIMG_SHA256,TWRP_SHA256

METHOD='test_remaining_device_domain_labels_and_canonical_cli'
SCOPE='v118-saved117-device-domain-rev2'
RESULT_SCHEMA='v118-saved117-device-domain-rev2-test-v1'
CAPS={'local_tests':1,'local_C_compiles':0,'CI':0,'new_grouped_methods':1,'new_fixture_compiles':0,
    'new_fixture_processes':0,'old_fixture_runs':0,'old_methods':0,'native_target_builds':0,'kernel_builds':0,
    'Image_builds':0,'real_decoder':0,'MachO':0,'private_payload':0,'Linux_integration':0,'target_RAM_reservation':0,
    'device_queries':0,'BOOT_writes':0,'reboots':0,'max_requested_PC_payload_bytes':0}
CARRIED_SECTIONS=('exact_current111_binding_and_read_only_scope','closed_remaining_pins_and_prefix_refusal','unreached_tail_once_and_immutable_acceptance')
OUTPUT=None


def sha(raw):return hashlib.sha256(raw).hexdigest()
def save(path,row):Path(path).write_text(json.dumps(row,indent=2)+'\n',encoding='utf-8')
def pin(path):return dict(path=str(path),sha256=sha(Path(path).read_bytes()))


def boot(kernel,ramdisk,*,padded=False):
    page=2048;align=lambda n:(n+page-1)//page*page
    header=bytearray(page);header[:8]=b'ANDROID!'
    struct.pack_into('<10I',header,8,len(kernel),0x10008000,len(ramdisk),0x11000000,0,0,0x10000100,page,1,0)
    struct.pack_into('<IQI',header,1632,0,0,1648)
    raw=bytes(header)+kernel+bytes(align(len(kernel))-len(kernel))+ramdisk+bytes(align(len(ramdisk))-len(ramdisk))
    if padded:raw+=b'SEANDROIDENFORCE'+bytes(57671680-len(raw)-len(b'SEANDROIDENFORCE'))
    return raw


class Saved117RemainingTests(unittest.TestCase):
    completed_sections=[]
    def complete(self,name):
        type(self).completed_sections.append(name)
        save(OUTPUT/'progress.json',dict(schema=RESULT_SCHEMA,scope=SCOPE,selected=[METHOD],completed_sections=list(type(self).completed_sections),initial118_method_run=0,completed_initial_sections_replayed=0,carried_completed_sections=list(CARRIED_SECTIONS),prior_initial_method_passed=False,prior_rev1_method_passed=False,rev1_method_run=0,completed_prior_sections_replayed=0))

    def _spent_initial118_method_do_not_execute(self):
        h='a'*64;host='c'*40;cycle='d'*32;identity='e'*32
        with tempfile.TemporaryDirectory(prefix='v118-new-',dir=OUTPUT) as temporary,ExitStack() as stack:
            root=Path(temporary);spent=root/'spent';offline=spent/'offline-once';template=offline/'template'
            variant=offline/'plan/cycle-01/kernel-build';packages=offline/'plan/cycle-01/packages';current=root/'prior111';backup=root/'backup'
            for directory in (template,variant,packages,current,backup):directory.mkdir(parents=True,exist_ok=True)
            n=native.record();kernel=bytearray(64);kernel[56:60]=b'ARM\x64';struct.pack_into('<3Q',kernel,8,0x80000,4096,0);kernel=bytes(kernel)
            compact=bytes(ro3.CAPACITY);official=boot(kernel,bytes(ro3.old.OLD_BYTES));original=boot(kernel,b'synthetic ramdisk',padded=True)
            diagnostic=boot(kernel,compact,padded=True);bound_sha=sha(kernel)
            backup_manifest=dict(complete=True,partition_writes=False,bootloader='N976N-SYNTHETIC',partitions=[])
            save(backup/'backup-manifest.json',backup_manifest);backup_sha=pin(backup/'backup-manifest.json')['sha256']
            prior_pair=dict(device_profile=data.PROFILE,source_head=oldpack.NATIVE,host_profile_source_head=oldpack.HEAD,
                host_profile_source_sha256=dict(oldpack.PINS),backup_manifest_sha256=backup_sha,
                **{oldpack.FIELD:dict(packaging_host=dict(host_profile_source_head=oldpack.PACKAGING_HEAD,host_profile_source_sha256=dict(oldpack.PACKAGING_PINS)))},
                packages=[dict(mode='diagnostic',payload_sha256='1'*64,payload_size=57671680),dict(mode='rollback',payload_sha256='3'*64,payload_size=57671680)])
            save(current/'package-result.json',prior_pair);save(root/'prior-plan.json',{'synthetic':'saved111'});save(root/'prior-terminal.json',{'synthetic':'terminal111'})
            predecessor=dict(native._CURRENT111_LINEAGE,packages=str(current),package_result_sha256=pin(current/'package-result.json')['sha256'],
                boot_sha256='1'*64,backup_manifest_sha256=backup_sha,plan_path=str(root/'prior-plan.json'),plan_sha256=pin(root/'prior-plan.json')['sha256'],
                execution_receipt_path=str(root/'prior-terminal.json'),execution_receipt_sha256=pin(root/'prior-terminal.json')['sha256'])
            wrapper=dict.fromkeys(native.CI_CONTEXT_KEYS,None);wrapper.update(schema='note10-root-native116-ci-success-context-v1',native_version='v116',
                native_source_head=n['head'],accepted_result_sha256=n['result'],source_sha256=n['pins'],source_manifest_sha256=n['source_manifest_sha256'],
                producer_ci_context=n['producer_ci_context'],generic_image_sha256=n['image_sha256'],Image_bytes=n['image_bytes'],current_predecessor=predecessor)
            save(spent/'context.json',wrapper)
            tool=Path(typed.__file__).resolve().parents[2]/'research/twrp-d2x-reference/aosp-mkbootimg.py'
            old=dict(schema=typed.OFFLINE_SCHEMA,status='reviewed_ready',execution_version='v117',host_source_head=saved.HEAD,native_source_head=n['head'],
                accepted_result_sha256=n['result'],producer_root=str(spent/'producer'),ci_success_context=str(spent/'context.json'),
                ci_success_context_sha256=pin(spent/'context.json')['sha256'],compact_manifest=str(spent/'compact.json'),compact_manifest_sha256=h,
                backup=str(backup),backup_manifest_sha256=backup_sha,current_packages=str(current),current_package_result_sha256=predecessor['package_result_sha256'],
                current_boot_sha256=predecessor['boot_sha256'],reference_twrp=str(spent/'reference.img'),mkbootimg=str(tool),output=str(offline),caps=typed.OFFLINE_CAPS)
            save(spent/'old-contract.json',old);old_pin=pin(spent/'old-contract.json')
            slot=dict(schema=ro3.SCHEMA,source=ro3.MODE,capacity=ro3.CAPACITY,descriptor_bytes=80,generic=True,patched=False,
                permanent_input_bytes=ro3.CAPACITY,permanent_descriptor_bytes=80,physical_ready=False,descriptor_class=3,boot_page=2048)
            for index,key,symbol,size,preimage,offset in ((1,'slot',ro3.SLOT,ro3.CAPACITY,sha(compact),4096),(2,'descriptor',ro3.DESC,80,sha(ro3.DESCRIPTOR),4096+ro3.CAPACITY)):
                slot[key]=dict(symbol=symbol,section='.rodata.'+symbol,offset=offset,bytes=size,alignment=16,readonly_flags='A',preimage_sha256=preimage,object_section_index=index,object_symbol_offset=0)
            keys=(*profile.FIELDS,*builtin.EXTRA_FIELDS,*data.FIELDS,*data.CARRIER_FIELDS,*typed.BINDING_FIELDS,*native.SCOPED_FIELDS)
            row=dict.fromkeys(keys,h);config=b'# synthetic config\n'
            row.update(device_profile=data.PROFILE,source_head=n['head'],native_source_head=n['head'],host_profile_source_head=saved.HEAD,
                host_profile_source_sha256=dict(saved.PINS),version='v117',execution_version='v117',native_producer_version='v116',native_producer_PC_first_use=True,
                diagnostic_kind='kernel-scoped-verified-output-candidate',data_input_kind='kernel-scoped-verified-output-candidate',storage_input_kind='kernel-scoped-verified-output-candidate',
                build_evidence_id=identity,kernel_banner='Linux version 4.14.113-v116-scoped-output-candidate synthetic',accepted_result_sha256=n['result'],
                type3_native_origin=dict(source_head=n['head'],accepted_result_sha256=n['result'],source_sha256=n['pins'],native_version='v116'),**native.stage_fields(),
                kernel_readonly3_schema=ro3.SCHEMA,kernel_readonly3_slot=slot,kernel_readonly3_span_schema=ro3.old.SPAN_SCHEMA,
                kernel_readonly3_span=dict(schema=ro3.old.SPAN_SCHEMA,kernel_bytes=n['linked_bytes'],text_prefix_bytes=0,slot_contained=True,descriptor_contained=True,disjoint=True,source='linked-kernel',phase='pre_descriptor',hardware=False,ownership=False),
                kernel_readonly3_linked_bytes=n['linked_bytes'],kernel_readonly3_image_bytes=n['image_bytes'],kernel_readonly3_requires_ack=True,kernel_readonly3_marker='N10DATARO3',
                data_expectation_mode=ro3.MODE,data_expectation_slot=slot,data_carrier_stage=data.STAGE,data_relative_placement_admitted=False,raw_input_binding=False,
                data_carrier_bytes=ro3.old.OLD_BYTES,data_payload_bytes=ro3.old.PAYLOAD_BYTES,type3_external_choice='compact-v1',type3_compact_bytes=ro3.CAPACITY,
                type3_compact_sha256=sha(compact),type3_compact_manifest_sha256=h,type3_contract_path=old_pin['path'],type3_contract_sha256=old_pin['sha256'],
                type3_generic_image_sha256=n['image_sha256'],image_sha256=n['image_sha256'],image_size=n['image_bytes'],image_expectation_patched=False,
                effective_config_sha256=sha(config),auto_return_diagnostic=True)
            save(template/'device-profile.json',row)
            generic=profile.common_report(row,pin(template/'device-profile.json')['sha256']);save(template/'build-result.json',generic)
            bound=dict(generic,image_sha256=bound_sha,image_expectation_patched=True,auto_cycle_variant=True,auto_cycle_token=cycle,
                auto_cycle_template=str(template),auto_cycle_template_report_sha256=pin(template/'build-result.json')['sha256'],auto_cycle_template_image_sha256=n['image_sha256'])
            bound['type3_materialization']=typed.materialization(row,cycle,n['image_sha256'],bound_sha,pin(template/'build-result.json')['sha256'])
            save(variant/'build-result.json',bound);(variant/'handoff.config').write_bytes(config);(template/'handoff.config').write_bytes(config)
            records=[dict(mode='diagnostic',file='diagnostic.zip',sha256=h,payload_sha256=sha(diagnostic),payload_size=57671680),
                dict(mode='rollback',file='rollback.zip',sha256=h,payload_sha256=sha(original),payload_size=57671680)]
            pair=dict(profile.fields(bound),kernel_image_sha256=bound_sha,auto_return_diagnostic=True,auto_cycle_token=cycle,
                backup_manifest_sha256=backup_sha,expected_current_boot_sha256='1'*64,packages=records)
            save(packages/'package-result.json',pair)
            plan=dict(schema=1,kind='note10-bounded-auto-cycle',device_profile=data.PROFILE,execution_version='v117',executing_host_source_head=saved.HEAD,
                type3_contract_sha256=old_pin['sha256'],kernel_build=str(template),build_result_sha256=pin(template/'build-result.json')['sha256'],
                image_sha256=n['image_sha256'],identity=identity,backup=str(backup),backup_manifest_sha256=backup_sha,reference_twrp=old['reference_twrp'],mkbootimg=str(tool),
                current_packages=str(current),current_package_result_sha256=predecessor['package_result_sha256'],current_boot_payload_sha256='1'*64,
                minimum_battery=10,return_timeout_seconds=240,stages=[dict(index=1,cycle=cycle,kernel_build=str(variant),image_sha256=bound_sha,
                    build_result_sha256=pin(variant/'build-result.json')['sha256'],packages=str(packages),package_result_sha256=pin(packages/'package-result.json')['sha256'])])
            save(offline/'plan/plan.json',plan)
            failed=dict(schema='type3-offline-journal-v1',status='failed_no_restart',phase='plan_reserved',attempts=dict(templates=1,materializations=1,plans=1),
                device_operations=[],contract_sha256=old_pin['sha256'],error_type='ValueError');save(offline/'transaction.json',failed)
            (spent/'failure.txt').write_text('line 1318, in validate_plan\ncurrent_boot_binding\nValueError: reviewed exact prior profile/source/current BOOT chain required\n',encoding='utf-8')
            failure=dict(source_head=saved.HEAD,phase='offline',invocation_attempts=1,invocation_retries=0,invocation_exit_code=1,success=False,
                contract_sha256=old_pin['sha256'],stderr_path=str(spent/'failure.txt'),stderr_sha256=pin(spent/'failure.txt')['sha256']);save(spent/'receipt.json',failure)
            live=dict(host_profile_source_head=host,host_profile_source_sha256={'synthetic/live118.py':h})
            c=dict(schema=saved.SCHEMA,status='reviewed_ready',execution_version='v118',execution_host_source_head=host,execution_host_source_sha256=live['host_profile_source_sha256'],
                producing_host_source_head=saved.HEAD,original_contract=old_pin,failed_transaction=pin(offline/'transaction.json'),failure_receipt=pin(spent/'receipt.json'),
                failure_stderr=pin(spent/'failure.txt'),plan=pin(offline/'plan/plan.json'),template_profile=pin(template/'device-profile.json'),template_report=pin(template/'build-result.json'),
                variant_report=pin(variant/'build-result.json'),package_result=pin(packages/'package-result.json'),current_package_result=pin(current/'package-result.json'),
                ci_success_context=pin(spent/'context.json'),output=str(root/'remaining'),caps=saved.CAPS)
            save(root/'contract.json',c);cp=pin(root/'contract.json')
            stack.enter_context(patch.object(profile,'host_binding',return_value=live))
            actual_sha=profile.sha
            stack.enter_context(patch.object(profile,'sha',side_effect=lambda p:TWRP_SHA256 if str(p)==old['reference_twrp'] else MKBOOTIMG_SHA256 if Path(p)==tool else actual_sha(p)))
            context=saved.load(cp['path'],cp['sha256'])
            prior=prior_pair['packages'][0]
            with self.assertRaisesRegex(ValueError,'context'):builtin.current_boot_binding(plan,prior_pair,prior)
            with saved.read_scope(context,'remaining'):
                builtin.current_boot_binding(plan,prior_pair,prior)
                with self.assertRaises(ValueError):builtin.current_boot_binding(dict(plan,current_boot_payload_sha256='3'*64),prior_pair,prior)
                with self.assertRaises(ValueError):builtin.current_boot_binding(plan,dict(prior_pair,source_head='b'*40),prior)
                with self.assertRaises(ValueError):builtin.current_boot_binding(plan,prior_pair,prior_pair['packages'][1])
                with self.assertRaises(ValueError):builtin.current_boot_binding(plan,dict(prior_pair,host_profile_source_sha256={'wrong':h}),prior)
            wrong_wrapper=dict(wrapper,current_predecessor=dict(predecessor,execution_host=host))
            with saved.read_scope(dict(context,wrapper=wrong_wrapper),'remaining'):
                with self.assertRaises(ValueError):builtin.current_boot_binding(plan,prior_pair,prior)
            with saved.read_scope(context,'remaining'):
                with self.assertRaisesRegex(ValueError,'read-only'):profile.pack(backup,variant,official,tool,root/'forbidden.img',{},cycle)
            self.complete('exact_current111_binding_and_read_only_scope')
            for key in ('plan','variant_report','package_result','failed_transaction'):
                wrong=dict(c);wrong[key]=dict(c[key],sha256='f'*64);target=root/(key+'-bad.json');save(target,wrong)
                with self.assertRaises(ValueError):saved.load(target,pin(target)['sha256'])
            bad_failed=dict(failed,attempts=dict(templates=1,materializations=1,plans=2));save(spent/'bad-attempts.json',bad_failed)
            bad_count=dict(c,failed_transaction=pin(spent/'bad-attempts.json'));save(root/'bad-count.json',bad_count)
            with self.assertRaisesRegex(ValueError,'prefix/failure'):saved.load(root/'bad-count.json',pin(root/'bad-count.json')['sha256'])
            with self.assertRaises(ValueError):saved.accepted_plan(c['plan']['path'],c['plan']['sha256'])
            self.assertFalse((root/'remaining').exists());self.complete('closed_remaining_pins_and_prefix_refusal')
            import prepare_linux_boot as packing
            import build_boot_test_packages as package_writer
            parts=dict(boot=original,recovery=official,dtb=b'dtb',dtbo=b'dtbo',vbmeta=b'vbmeta')
            actual_read_bytes=Path.read_bytes
            stack.enter_context(patch.object(Path,'read_bytes',lambda path:official if str(path)==old['reference_twrp'] else actual_read_bytes(path)))
            backup_reads=stack.enter_context(patch.object(packing,'read_verified_backup',return_value=parts))
            calls=[]
            class Zip:
                def __init__(self,path):self.record=next(x for x in records if x['file']==Path(path).name);calls.append(('open',self.record['mode']))
                def __enter__(self):return self
                def __exit__(self,*args):return False
                def read(self,name):
                    calls.append((name,self.record['mode']))
                    if name=='boot.img':return diagnostic if self.record['mode']=='diagnostic' else original
                    if name=='META-INF/com/google/android/update-binary':
                        return package_writer.updater(mode=self.record['mode'],bootloader=backup_manifest['bootloader'],partitions=backup_manifest['partitions'],
                            payload_sha=self.record['payload_sha256'],current_boot_sha=pair['expected_current_boot_sha256'],auto_return=self.record['mode']=='diagnostic',device_profile=data.PROFILE)
                    raise AssertionError('unexpected member')
            stack.enter_context(patch('zipfile.ZipFile',Zip))
            acceptance=saved.prepare(cp['path'],cp['sha256'])
            self.assertEqual(backup_reads.call_count,1);self.assertEqual(sum(name=='open' for name,mode in calls),3)
            self.assertEqual(sum(name=='boot.img' for name,mode in calls),3);self.assertEqual(sum(name.startswith('META-INF') for name,mode in calls),2)
            self.assertEqual(read_json(root/'remaining/journal.json')['completed_sections'],list(saved.SECTIONS))
            with self.assertRaisesRegex(ValueError,'never restart'):saved.prepare(cp['path'],cp['sha256'])
            self.assertEqual(backup_reads.call_count,1);self.complete('unreached_tail_once_and_immutable_acceptance')
            device_output=root/'device-output';device_output.mkdir()
            device=dict(schema=saved.DEVICE_SCHEMA,status='reviewed_ready',execution_version='v118',producer_execution_version='v117',producing_host_source_head=saved.HEAD,
                execution_host_source_head=host,execution_host_source_sha256=live['host_profile_source_sha256'],plan=c['plan'],packages=str(packages),
                package_result_sha256=c['package_result']['sha256'],bound_image_sha256=bound_sha,remaining_acceptance=acceptance,output=str(device_output),
                minimum_battery=10,BOOT_write_max=1,reboot_max=1,user_availability_record_sha256='4a639d278836af88256a339d199b9fbe53ad65d354db4b8c4401796522e758e9',linked_growth_ack=native.growth_ack())
            save(root/'device.json',device);dp=pin(root/'device.json')
            execution=saved.execution_context(bound,c['plan']['sha256'],packages,'v118',host,dp['path'],dp['sha256'],device_output)
            with self.assertRaisesRegex(ValueError,'PC formats'):
                physical.require_device_scope(dict(pair,output_writer_schema='n10-host-output-writer-pc-v1'),True,execution)
            class NoTransport(Exception):pass
            seen=[]
            def stop(adb):
                seen.append('metadata-before-transport');self.assertEqual(profile.variant(variant,cycle),bound)
                with self.assertRaisesRegex(ValueError,'read-only'):profile.pack(backup,variant,official,tool,root/'forbidden.img',{},cycle)
                raise NoTransport()
            stack.enter_context(patch('stage_phase2.verify_packages',return_value=records))
            transport=stack.enter_context(patch('run_probe.preflight',side_effect=stop))
            with self.assertRaises(NoTransport):profile.precheck(packages,variant,backup,object(),{},ack_kernel_readonly_growth=True,type3_context=execution)
            with self.assertRaises(NoTransport):profile._collect_into(packages,variant,object(),device_output,ack_kernel_readonly_growth=True,type3_context=execution)
            for ctx,ack in ((None,True),(execution,False),(dict(execution,plan_sha256='f'*64),True)):
                with self.assertRaises(ValueError):profile._collect_into(packages,variant,object(),device_output,ack_kernel_readonly_growth=ack,type3_context=ctx)
            self.assertEqual(transport.call_count,2);self.assertEqual(len(seen),2);self.complete('new118_device_read_context_before_transport')
            device_context=saved._device(dp['path'],dp['sha256'],c['plan']['path'],c['plan']['sha256'],packages,'v118',host,device_output)
            with saved.read_scope(device_context,'device'):
                self.assertEqual(profile.validate_plan(c['plan']['path'],c['plan']['sha256']),plan)
            self.assertEqual(read_json(c['plan']['path']),plan);self.assertEqual(read_json(offline/'transaction.json'),failed)
            self.complete('producing117_labels_and_failed_journal_preserved')
            with patch('sys.argv',[saved.__file__,'--contract',cp['path'],'--contract-sha256',cp['sha256']]),\
                    patch.object(saved,'prepare',return_value={'synthetic':'canonical-route'}) as canonical,patch('builtins.print'):
                runpy.run_path(saved.__file__,run_name='__main__')
                canonical.assert_called_once_with(cp['path'],cp['sha256'])
            self.complete('canonical_remaining_cli_routes_one_prepare')
        save(OUTPUT/'summary.json',dict(schema=RESULT_SCHEMA,synthetic_only=True,completed_sections=list(type(self).completed_sections),
            old117_methods=0,old_validation_prefix_runs=0,actual_private_inputs=0,actual_device_operations=[],Image_reads=0,Image_builds=0,
            fixture_compiles=0,fixture_processes=0,real_decoder_calls=0,MachO_replays=0))

    @contextmanager
    def _remaining_setup(self):
        h='a'*64;host='c'*40;cycle='d'*32;identity='e'*32
        with tempfile.TemporaryDirectory(prefix='v118-new-',dir=OUTPUT) as temporary,ExitStack() as stack:
            root=Path(temporary);spent=root/'spent';offline=spent/'offline-once';template=offline/'template'
            variant=offline/'plan/cycle-01/kernel-build';packages=offline/'plan/cycle-01/packages';current=root/'prior111';backup=root/'backup'
            for directory in (template,variant,packages,current,backup):directory.mkdir(parents=True,exist_ok=True)
            n=native.record();kernel=bytearray(64);kernel[56:60]=b'ARM\x64';struct.pack_into('<3Q',kernel,8,0x80000,4096,0);kernel=bytes(kernel)
            compact=bytes(ro3.CAPACITY);official=boot(kernel,bytes(ro3.old.OLD_BYTES));original=boot(kernel,b'synthetic ramdisk',padded=True)
            diagnostic=boot(kernel,compact,padded=True);bound_sha=sha(kernel)
            synthetic_parts=dict(boot=original,recovery=official,dtb=b'dtb',dtbo=b'dtbo',vbmeta=b'vbmeta')
            partitions=[dict(partition=name,block_node='/dev/block/sda'+str(index),size=len(blob),sha256=sha(blob),
                file=name+'.img',remote_hash_before_and_after_match=True) for index,(name,blob) in enumerate(synthetic_parts.items(),1)]
            backup_manifest=dict(complete=True,partition_writes=False,bootloader='N976NSYNTHETIC',partitions=partitions)
            save(backup/'backup-manifest.json',backup_manifest);backup_sha=pin(backup/'backup-manifest.json')['sha256']
            prior_pair=dict(device_profile=data.PROFILE,source_head=oldpack.NATIVE,host_profile_source_head=oldpack.HEAD,
                host_profile_source_sha256=dict(oldpack.PINS),backup_manifest_sha256=backup_sha,
                **{oldpack.FIELD:dict(packaging_host=dict(host_profile_source_head=oldpack.PACKAGING_HEAD,host_profile_source_sha256=dict(oldpack.PACKAGING_PINS)))},
                packages=[dict(mode='diagnostic',payload_sha256='1'*64,payload_size=57671680),dict(mode='rollback',payload_sha256='3'*64,payload_size=57671680)])
            save(current/'package-result.json',prior_pair);save(root/'prior-plan.json',{'synthetic':'saved111'});save(root/'prior-terminal.json',{'synthetic':'terminal111'})
            predecessor=dict(native._CURRENT111_LINEAGE,packages=str(current),package_result_sha256=pin(current/'package-result.json')['sha256'],
                boot_sha256='1'*64,backup_manifest_sha256=backup_sha,plan_path=str(root/'prior-plan.json'),plan_sha256=pin(root/'prior-plan.json')['sha256'],
                execution_receipt_path=str(root/'prior-terminal.json'),execution_receipt_sha256=pin(root/'prior-terminal.json')['sha256'])
            wrapper=dict.fromkeys(native.CI_CONTEXT_KEYS,None);wrapper.update(schema='note10-root-native116-ci-success-context-v1',native_version='v116',
                native_source_head=n['head'],accepted_result_sha256=n['result'],source_sha256=n['pins'],source_manifest_sha256=n['source_manifest_sha256'],
                producer_ci_context=n['producer_ci_context'],generic_image_sha256=n['image_sha256'],Image_bytes=n['image_bytes'],current_predecessor=predecessor)
            save(spent/'context.json',wrapper)
            tool=Path(typed.__file__).resolve().parents[2]/'research/twrp-d2x-reference/aosp-mkbootimg.py'
            old=dict(schema=typed.OFFLINE_SCHEMA,status='reviewed_ready',execution_version='v117',host_source_head=saved.HEAD,native_source_head=n['head'],
                accepted_result_sha256=n['result'],producer_root=str(spent/'producer'),ci_success_context=str(spent/'context.json'),
                ci_success_context_sha256=pin(spent/'context.json')['sha256'],compact_manifest=str(spent/'compact.json'),compact_manifest_sha256=h,
                backup=str(backup),backup_manifest_sha256=backup_sha,current_packages=str(current),current_package_result_sha256=predecessor['package_result_sha256'],
                current_boot_sha256=predecessor['boot_sha256'],reference_twrp=str(spent/'reference.img'),mkbootimg=str(tool),output=str(offline),caps=typed.OFFLINE_CAPS)
            save(spent/'old-contract.json',old);old_pin=pin(spent/'old-contract.json')
            slot=dict(schema=ro3.SCHEMA,source=ro3.MODE,capacity=ro3.CAPACITY,descriptor_bytes=80,generic=True,patched=False,
                permanent_input_bytes=ro3.CAPACITY,permanent_descriptor_bytes=80,physical_ready=False,descriptor_class=3,boot_page=2048)
            for index,key,symbol,size,preimage,offset in ((1,'slot',ro3.SLOT,ro3.CAPACITY,sha(compact),4096),(2,'descriptor',ro3.DESC,80,sha(ro3.DESCRIPTOR),4096+ro3.CAPACITY)):
                slot[key]=dict(symbol=symbol,section='.rodata.'+symbol,offset=offset,bytes=size,alignment=16,readonly_flags='A',preimage_sha256=preimage,object_section_index=index,object_symbol_offset=0)
            keys=(*profile.FIELDS,*builtin.EXTRA_FIELDS,*data.FIELDS,*data.CARRIER_FIELDS,*typed.BINDING_FIELDS,*native.SCOPED_FIELDS)
            row=dict.fromkeys(keys,h);config=b'# synthetic config\n'
            row.update(device_profile=data.PROFILE,source_head=n['head'],native_source_head=n['head'],host_profile_source_head=saved.HEAD,
                host_profile_source_sha256=dict(saved.PINS),version='v117',execution_version='v117',native_producer_version='v116',native_producer_PC_first_use=True,
                diagnostic_kind='kernel-scoped-verified-output-candidate',data_input_kind='kernel-scoped-verified-output-candidate',storage_input_kind='kernel-scoped-verified-output-candidate',
                build_evidence_id=identity,kernel_banner='Linux version 4.14.113-v116-scoped-output-candidate synthetic',accepted_result_sha256=n['result'],
                type3_native_origin=dict(source_head=n['head'],accepted_result_sha256=n['result'],source_sha256=n['pins'],native_version='v116'),**native.stage_fields(),
                kernel_readonly3_schema=ro3.SCHEMA,kernel_readonly3_slot=slot,kernel_readonly3_span_schema=ro3.old.SPAN_SCHEMA,
                kernel_readonly3_span=dict(schema=ro3.old.SPAN_SCHEMA,kernel_bytes=n['linked_bytes'],text_prefix_bytes=0,slot_contained=True,descriptor_contained=True,disjoint=True,source='linked-kernel',phase='pre_descriptor',hardware=False,ownership=False),
                kernel_readonly3_linked_bytes=n['linked_bytes'],kernel_readonly3_image_bytes=n['image_bytes'],kernel_readonly3_requires_ack=True,kernel_readonly3_marker='N10DATARO3',
                data_expectation_mode=ro3.MODE,data_expectation_slot=slot,data_carrier_stage=data.STAGE,data_relative_placement_admitted=False,raw_input_binding=False,
                data_carrier_bytes=ro3.old.OLD_BYTES,data_payload_bytes=ro3.old.PAYLOAD_BYTES,type3_external_choice='compact-v1',type3_compact_bytes=ro3.CAPACITY,
                type3_compact_sha256=sha(compact),type3_compact_manifest_sha256=h,type3_contract_path=old_pin['path'],type3_contract_sha256=old_pin['sha256'],
                type3_generic_image_sha256=n['image_sha256'],image_sha256=n['image_sha256'],image_size=n['image_bytes'],image_expectation_patched=False,
                effective_config_sha256=sha(config),auto_return_diagnostic=True)
            save(template/'device-profile.json',row)
            generic=profile.common_report(row,pin(template/'device-profile.json')['sha256']);save(template/'build-result.json',generic)
            bound=dict(generic,image_sha256=bound_sha,image_expectation_patched=True,auto_cycle_variant=True,auto_cycle_token=cycle,
                auto_cycle_template=str(template),auto_cycle_template_report_sha256=pin(template/'build-result.json')['sha256'],auto_cycle_template_image_sha256=n['image_sha256'])
            bound['type3_materialization']=typed.materialization(row,cycle,n['image_sha256'],bound_sha,pin(template/'build-result.json')['sha256'])
            save(variant/'build-result.json',bound);(variant/'handoff.config').write_bytes(config);(template/'handoff.config').write_bytes(config)
            records=[dict(mode='diagnostic',file='diagnostic.zip',sha256=h,payload_sha256=sha(diagnostic),payload_size=57671680),
                dict(mode='rollback',file='rollback.zip',sha256=h,payload_sha256=sha(original),payload_size=57671680)]
            pair=dict(profile.fields(bound),kernel_image_sha256=bound_sha,auto_return_diagnostic=True,auto_cycle_token=cycle,
                backup_manifest_sha256=backup_sha,expected_current_boot_sha256='1'*64,packages=records)
            save(packages/'package-result.json',pair)
            plan=dict(schema=1,kind='note10-bounded-auto-cycle',device_profile=data.PROFILE,execution_version='v117',executing_host_source_head=saved.HEAD,
                type3_contract_sha256=old_pin['sha256'],kernel_build=str(template),build_result_sha256=pin(template/'build-result.json')['sha256'],
                image_sha256=n['image_sha256'],identity=identity,backup=str(backup),backup_manifest_sha256=backup_sha,reference_twrp=old['reference_twrp'],mkbootimg=str(tool),
                current_packages=str(current),current_package_result_sha256=predecessor['package_result_sha256'],current_boot_payload_sha256='1'*64,
                minimum_battery=10,return_timeout_seconds=240,stages=[dict(index=1,cycle=cycle,kernel_build=str(variant),image_sha256=bound_sha,
                    build_result_sha256=pin(variant/'build-result.json')['sha256'],packages=str(packages),package_result_sha256=pin(packages/'package-result.json')['sha256'])])
            save(offline/'plan/plan.json',plan)
            failed=dict(schema='type3-offline-journal-v1',status='failed_no_restart',phase='plan_reserved',attempts=dict(templates=1,materializations=1,plans=1),
                device_operations=[],contract_sha256=old_pin['sha256'],error_type='ValueError');save(offline/'transaction.json',failed)
            (spent/'failure.txt').write_text('line 1318, in validate_plan\ncurrent_boot_binding\nValueError: reviewed exact prior profile/source/current BOOT chain required\n',encoding='utf-8')
            failure=dict(source_head=saved.HEAD,phase='offline',invocation_attempts=1,invocation_retries=0,invocation_exit_code=1,success=False,
                contract_sha256=old_pin['sha256'],stderr_path=str(spent/'failure.txt'),stderr_sha256=pin(spent/'failure.txt')['sha256']);save(spent/'receipt.json',failure)
            live=dict(host_profile_source_head=host,host_profile_source_sha256={'synthetic/live118.py':h})
            c=dict(schema=saved.SCHEMA,status='reviewed_ready',execution_version='v118',execution_host_source_head=host,execution_host_source_sha256=live['host_profile_source_sha256'],
                producing_host_source_head=saved.HEAD,original_contract=old_pin,failed_transaction=pin(offline/'transaction.json'),failure_receipt=pin(spent/'receipt.json'),
                failure_stderr=pin(spent/'failure.txt'),plan=pin(offline/'plan/plan.json'),template_profile=pin(template/'device-profile.json'),template_report=pin(template/'build-result.json'),
                variant_report=pin(variant/'build-result.json'),package_result=pin(packages/'package-result.json'),current_package_result=pin(current/'package-result.json'),
                ci_success_context=pin(spent/'context.json'),output=str(root/'remaining'),caps=saved.CAPS)
            save(root/'contract.json',c);cp=pin(root/'contract.json')
            stack.enter_context(patch.object(profile,'host_binding',return_value=live))
            actual_sha=profile.sha
            stack.enter_context(patch.object(profile,'sha',side_effect=lambda p:TWRP_SHA256 if str(p)==old['reference_twrp'] else MKBOOTIMG_SHA256 if Path(p)==tool else actual_sha(p)))
            yield dict(root=root,stack=stack,original=original,official=official,diagnostic=diagnostic,records=records,backup_manifest=backup_manifest,old=old,tool=tool,pair=pair,config=config,cycle=cycle,c=c,cp=cp,bound=bound,packages=packages,backup=backup,variant=variant,host=host,live=live,plan=plan,offline=offline,failed=failed)

    def _spent_rev1_method_do_not_execute(self):
        # The original two completed sections are carried, never called again.
        # Resume the unfinished third section with corrected synthetic I/O.
        with self._remaining_setup() as fixture:
            root=fixture['root'];stack=fixture['stack'];original=fixture['original'];official=fixture['official']
            diagnostic=fixture['diagnostic'];records=fixture['records'];backup_manifest=fixture['backup_manifest'];old=fixture['old']
            tool=fixture['tool'];pair=fixture['pair'];config=fixture['config'];cycle=fixture['cycle']
            c=fixture['c'];cp=fixture['cp'];bound=fixture['bound'];packages=fixture['packages']
            backup=fixture['backup'];variant=fixture['variant'];host=fixture['host'];live=fixture['live']
            plan=fixture['plan'];offline=fixture['offline'];failed=fixture['failed']
            import prepare_linux_boot as packing
            import build_boot_test_packages as package_writer
            parts=dict(boot=original,recovery=official,dtb=b'dtb',dtbo=b'dtbo',vbmeta=b'vbmeta')
            actual_read_bytes=Path.read_bytes
            stack.enter_context(patch.object(Path,'read_bytes',lambda path:official if str(path)==old['reference_twrp'] else actual_read_bytes(path)))
            backup_reads=stack.enter_context(patch.object(packing,'read_verified_backup',return_value=parts))
            calls=[]
            class Zip:
                def __init__(self,path):self.record=next(x for x in records if x['file']==Path(path).name);calls.append(('open',self.record['mode']))
                def __enter__(self):return self
                def __exit__(self,*args):return False
                def read(self,name):
                    calls.append((name,self.record['mode']))
                    if name=='boot.img':return diagnostic if self.record['mode']=='diagnostic' else original
                    if name=='META-INF/com/google/android/update-binary':
                        return package_writer.updater(mode=self.record['mode'],bootloader=backup_manifest['bootloader'],partitions=backup_manifest['partitions'],
                            payload_sha=self.record['payload_sha256'],current_boot_sha=pair['expected_current_boot_sha256'],auto_return=self.record['mode']=='diagnostic',device_profile=data.PROFILE)
                    raise AssertionError('unexpected member')
            stack.enter_context(patch('zipfile.ZipFile',Zip))
            acceptance=saved.prepare(cp['path'],cp['sha256'])
            self.assertEqual(backup_reads.call_count,1);self.assertEqual(sum(name=='open' for name,mode in calls),3)
            self.assertEqual(sum(name=='boot.img' for name,mode in calls),3);self.assertEqual(sum(name.startswith('META-INF') for name,mode in calls),2)
            self.assertEqual(read_json(root/'remaining/journal.json')['completed_sections'],list(saved.SECTIONS))
            with self.assertRaisesRegex(ValueError,'never restart'):saved.prepare(cp['path'],cp['sha256'])
            self.assertEqual(backup_reads.call_count,1);self.complete('unreached_tail_once_and_immutable_acceptance')
            device_output=root/'device-output';device_output.mkdir()
            device=dict(schema=saved.DEVICE_SCHEMA,status='reviewed_ready',execution_version='v118',producer_execution_version='v117',producing_host_source_head=saved.HEAD,
                execution_host_source_head=host,execution_host_source_sha256=live['host_profile_source_sha256'],plan=c['plan'],packages=str(packages),
                package_result_sha256=c['package_result']['sha256'],bound_image_sha256=bound_sha,remaining_acceptance=acceptance,output=str(device_output),
                minimum_battery=10,BOOT_write_max=1,reboot_max=1,user_availability_record_sha256='4a639d278836af88256a339d199b9fbe53ad65d354db4b8c4401796522e758e9',linked_growth_ack=native.growth_ack())
            save(root/'device.json',device);dp=pin(root/'device.json')
            execution=saved.execution_context(bound,c['plan']['sha256'],packages,'v118',host,dp['path'],dp['sha256'],device_output)
            with self.assertRaisesRegex(ValueError,'PC formats'):
                physical.require_device_scope(dict(pair,output_writer_schema='n10-host-output-writer-pc-v1'),True,execution)
            class NoTransport(Exception):pass
            seen=[]
            def stop(adb):
                seen.append('metadata-before-transport');self.assertEqual(profile.variant(variant,cycle),bound)
                with self.assertRaisesRegex(ValueError,'read-only'):profile.pack(backup,variant,official,tool,root/'forbidden.img',{},cycle)
                raise NoTransport()
            stack.enter_context(patch('stage_phase2.verify_packages',return_value=records))
            transport=stack.enter_context(patch('run_probe.preflight',side_effect=stop))
            with self.assertRaises(NoTransport):profile.precheck(packages,variant,backup,object(),{},ack_kernel_readonly_growth=True,type3_context=execution)
            with self.assertRaises(NoTransport):profile._collect_into(packages,variant,object(),device_output,ack_kernel_readonly_growth=True,type3_context=execution)
            for ctx,ack in ((None,True),(execution,False),(dict(execution,plan_sha256='f'*64),True)):
                with self.assertRaises(ValueError):profile._collect_into(packages,variant,object(),device_output,ack_kernel_readonly_growth=ack,type3_context=ctx)
            self.assertEqual(transport.call_count,2);self.assertEqual(len(seen),2);self.complete('new118_device_read_context_before_transport')
            device_context=saved._device(dp['path'],dp['sha256'],c['plan']['path'],c['plan']['sha256'],packages,'v118',host,device_output)
            with saved.read_scope(device_context,'device'):
                self.assertEqual(profile.validate_plan(c['plan']['path'],c['plan']['sha256']),plan)
            self.assertEqual(read_json(c['plan']['path']),plan);self.assertEqual(read_json(offline/'transaction.json'),failed)
            self.complete('producing117_labels_and_failed_journal_preserved')
            with patch('sys.argv',[saved.__file__,'--contract',cp['path'],'--contract-sha256',cp['sha256']]),\
                    patch.object(saved,'prepare',return_value={'synthetic':'canonical-route'}) as canonical,patch('builtins.print'):
                runpy.run_path(saved.__file__,run_name='__main__')
                canonical.assert_called_once_with(cp['path'],cp['sha256'])
            self.complete('canonical_remaining_cli_routes_one_prepare')
        save(OUTPUT/'summary.json',dict(schema=RESULT_SCHEMA,synthetic_only=True,completed_sections=list(type(self).completed_sections),
            completed_initial_sections_replayed=0,initial118_method_run=0,carried_completed_sections=list(CARRIED_SECTIONS),prior_initial_method_passed=False,old117_methods=0,old_validation_prefix_runs=0,
            actual_private_inputs=0,actual_device_operations=[],Image_reads=0,Image_builds=0,fixture_compiles=0,fixture_processes=0,
            real_decoder_calls=0,MachO_replays=0,shared_fixture_setup_only=True))


    def test_remaining_device_domain_labels_and_canonical_cli(self):
        # Prerequisite metadata is synthetic and uses the already-tested receipt
        # format. It is not a new validation attempt or a claim of another PASS.
        with self._remaining_setup() as fixture:
            root=fixture['root'];stack=fixture['stack'];c=fixture['c'];cp=fixture['cp']
            bound=fixture['bound'];bound_sha=bound['image_sha256'];packages=fixture['packages'];pair=fixture['pair']
            backup=fixture['backup'];variant=fixture['variant'];host=fixture['host'];live=fixture['live']
            official=fixture['official'];original=fixture['original'];tool=fixture['tool'];cycle=fixture['cycle']
            records=fixture['records'];plan=fixture['plan'];offline=fixture['offline'];failed=fixture['failed']
            seed=dict(contract=c,contract_path=cp['path'],contract_sha256=cp['sha256'],host=live,bound=bound)
            seed_output=Path(c['output']);seed_output.mkdir()
            receipt_path=seed_output/'accepted-plan.json';save(receipt_path,saved._acceptance(seed));acceptance=pin(receipt_path)
            save(seed_output/'journal.json',dict(schema='type3-saved117-validation-journal-v1',status='complete',
                attempts=dict(remaining_validations=1),contract_sha256=cp['sha256'],completed_sections=list(saved.SECTIONS),
                declared_caps=saved.CAPS,device_operations=[],acceptance=acceptance,synthetic_fixture_only=True))
            prohibited_prepare=stack.enter_context(patch.object(saved,'prepare',side_effect=AssertionError('passed prepare must not execute')))
            prohibited_tail=stack.enter_context(patch.object(profile,'_validate_plan_tail',side_effect=AssertionError('passed tail must not execute')))
            parts=dict(boot=original,recovery=official,dtb=b'dtb',dtbo=b'dtbo',vbmeta=b'vbmeta')
            stack.enter_context(patch('prepare_linux_boot.read_verified_backup',return_value=parts))
            device_output=root/'device-output';device_output.mkdir()
            device=dict(schema=saved.DEVICE_SCHEMA,status='reviewed_ready',execution_version='v118',producer_execution_version='v117',producing_host_source_head=saved.HEAD,
                execution_host_source_head=host,execution_host_source_sha256=live['host_profile_source_sha256'],plan=c['plan'],packages=str(packages),
                package_result_sha256=c['package_result']['sha256'],bound_image_sha256=bound_sha,remaining_acceptance=acceptance,output=str(device_output),
                minimum_battery=10,BOOT_write_max=1,reboot_max=1,user_availability_record_sha256='4a639d278836af88256a339d199b9fbe53ad65d354db4b8c4401796522e758e9',linked_growth_ack=native.growth_ack())
            save(root/'device.json',device);dp=pin(root/'device.json')
            execution=saved.execution_context(bound,c['plan']['sha256'],packages,'v118',host,dp['path'],dp['sha256'],device_output)
            with self.assertRaisesRegex(ValueError,'PC formats'):
                physical.require_device_scope(dict(pair,output_writer_schema='n10-host-output-writer-pc-v1'),True,execution)
            class NoTransport(Exception):pass
            seen=[]
            def stop(adb):
                seen.append('metadata-before-transport');self.assertEqual(profile.variant(variant,cycle),bound)
                with self.assertRaisesRegex(ValueError,'read-only'):profile.pack(backup,variant,official,tool,root/'forbidden.img',{},cycle)
                raise NoTransport()
            stack.enter_context(patch('stage_phase2.verify_packages',return_value=records))
            transport=stack.enter_context(patch('run_probe.preflight',side_effect=stop))
            with self.assertRaises(NoTransport):profile.precheck(packages,variant,backup,object(),{},ack_kernel_readonly_growth=True,type3_context=execution)
            with self.assertRaises(NoTransport):profile._collect_into(packages,variant,object(),device_output,ack_kernel_readonly_growth=True,type3_context=execution)
            for ctx,ack in ((None,True),(execution,False),(dict(execution,plan_sha256='f'*64),True)):
                with self.assertRaises(ValueError):profile._collect_into(packages,variant,object(),device_output,ack_kernel_readonly_growth=ack,type3_context=ctx)
            self.assertEqual(transport.call_count,2);self.assertEqual(len(seen),2);self.complete('new118_device_read_context_before_transport')
            device_context=saved._device(dp['path'],dp['sha256'],c['plan']['path'],c['plan']['sha256'],packages,'v118',host,device_output)
            with saved.read_scope(device_context,'device'):
                self.assertEqual(profile.validate_plan(c['plan']['path'],c['plan']['sha256']),plan)
            self.assertEqual(read_json(c['plan']['path']),plan);self.assertEqual(read_json(offline/'transaction.json'),failed)
            self.complete('producing117_labels_and_failed_journal_preserved')
            with patch('sys.argv',[saved.__file__,'--contract',cp['path'],'--contract-sha256',cp['sha256']]),\
                    patch.object(saved,'prepare',return_value={'synthetic':'canonical-route'}) as canonical,patch('builtins.print'):
                runpy.run_path(saved.__file__,run_name='__main__')
                canonical.assert_called_once_with(cp['path'],cp['sha256'])
            prohibited_prepare.assert_not_called();prohibited_tail.assert_not_called()
            self.complete('canonical_remaining_cli_routes_one_prepare')

        save(OUTPUT/'summary.json',dict(schema=RESULT_SCHEMA,synthetic_only=True,completed_sections=list(type(self).completed_sections),
            carried_completed_sections=list(CARRIED_SECTIONS),prior_initial_method_passed=False,prior_rev1_method_passed=False,
            initial118_method_run=0,rev1_method_run=0,completed_prior_sections_replayed=0,synthetic_accepted_prerequisite=True,
            real_prepare_calls=0,real_tail_calls=0,old117_methods=0,old_validation_prefix_runs=0,actual_private_inputs=0,
            actual_device_operations=[],Image_reads=0,Image_builds=0,fixture_compiles=0,fixture_processes=0,real_decoder_calls=0,MachO_replays=0))



def read_json(path):return json.loads(Path(path).read_text(encoding='utf-8'))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--scope',required=True,choices=(SCOPE,));parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args();OUTPUT=args.output.resolve()
    if not OUTPUT.is_relative_to((Path(__file__).resolve().parents[2]/'note10/private').resolve()):raise ValueError('private synthetic output required')
    OUTPUT.mkdir(parents=True,exist_ok=False)
    result=unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite([Saved117RemainingTests(METHOD)]))
    save(OUTPUT/'result.json',dict(schema=RESULT_SCHEMA,scope=SCOPE,selected=[METHOD],run=result.testsRun,errors=len(result.errors),failures=len(result.failures),
        passed=result.wasSuccessful(),caps=CAPS,rev1_method_run=0,completed_prior_sections_replayed=0,synthetic_accepted_prerequisite=True,real_prepare_calls=0,real_tail_calls=0,prior_rev1_method_passed=False,initial118_method_run=0,completed_initial_sections_replayed=0,carried_completed_sections=list(CARRIED_SECTIONS),prior_initial_method_passed=False,shared_fixture_setup_only=True,completed_sections=list(Saved117RemainingTests.completed_sections),old_methods_run=0,old_validation_prefix_runs=0,
        fixture_compiles=0,fixture_processes=0,Image_builds=0,CI=0,actual_private_inputs=0,actual_device_operations=[],
        error_tracebacks=[dict(test=t.id(),traceback=trace) for t,trace in result.errors],failure_tracebacks=[dict(test=t.id(),traceback=trace) for t,trace in result.failures]))
    raise SystemExit(0 if result.wasSuccessful() else 1)
