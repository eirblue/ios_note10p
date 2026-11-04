"""One new device-entry119 regression; metadata-only synthetic held states."""
import argparse
import ast
from contextlib import contextmanager,ExitStack
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import auto_cycle
import type3_remaining_plan as saved
import type3_admission as typed
import native_scoped_output_admission as native
import type3_remaining_pack as oldpack
import sha256_kat_device_profile as profile
import builtin_init_profile as builtin
import kernel_readonly_span_candidate as ro3
import linux_data_carrier as data

METHOD='test_device_entry_after_canonical_fixture_scope_fix'
SCOPE='v119-saved118-device-entry-fixture-rev1'
RESULT_SCHEMA='v119-saved118-device-entry-fixture-rev1-test-v1'
CAPS={'local_tests':1,'local_C_compiles':0,'CI':0,'new_grouped_methods':1,'new_fixture_compiles':0,
    'new_fixture_processes':0,'old_fixture_runs':0,'old_methods':0,'native_target_builds':0,'kernel_builds':0,
    'Image_builds':0,'real_decoder':0,'MachO':0,'private_payload':0,'Linux_integration':0,'target_RAM_reservation':0,
    'device_queries':0,'BOOT_writes':0,'reboots':0,'max_requested_PC_payload_bytes':0}
OUTPUT=None


def sha(raw):return hashlib.sha256(raw).hexdigest()
def save(path,row):Path(path).write_text(json.dumps(row,indent=2)+'\n',encoding='utf-8')
def pin(path):return dict(path=str(path),sha256=sha(Path(path).read_bytes()))


@contextmanager
def synthetic_saved118():
        h='a'*64;host='c'*40;cycle='d'*32;identity='e'*32
        with tempfile.TemporaryDirectory(prefix='v119-new-',dir=OUTPUT) as temporary,ExitStack() as stack:
            root=Path(temporary);spent=root/'spent';offline=spent/'offline-once';template=offline/'template'
            variant=offline/'plan/cycle-01/kernel-build';packages=offline/'plan/cycle-01/packages';current=root/'prior111';backup=root/'backup'
            for directory in (template,variant,packages,current,backup):directory.mkdir(parents=True,exist_ok=True)
            n=native.record();kernel=b'synthetic kernel metadata only'
            compact=bytes(ro3.CAPACITY);official=b'synthetic reference metadata';original=b'synthetic backup metadata'
            diagnostic=b'synthetic held BOOT metadata';bound_sha=sha(kernel)
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
            live=dict(host_profile_source_head=saved.VALIDATION118_HEAD,host_profile_source_sha256=dict(saved.VALIDATION118_PINS))
            c=dict(schema=saved.SCHEMA,status='reviewed_ready',execution_version='v118',execution_host_source_head=saved.VALIDATION118_HEAD,execution_host_source_sha256=live['host_profile_source_sha256'],
                producing_host_source_head=saved.HEAD,original_contract=old_pin,failed_transaction=pin(offline/'transaction.json'),failure_receipt=pin(spent/'receipt.json'),
                failure_stderr=pin(spent/'failure.txt'),plan=pin(offline/'plan/plan.json'),template_profile=pin(template/'device-profile.json'),template_report=pin(template/'build-result.json'),
                variant_report=pin(variant/'build-result.json'),package_result=pin(packages/'package-result.json'),current_package_result=pin(current/'package-result.json'),
                ci_success_context=pin(spent/'context.json'),output=str(root/'remaining'),caps=saved.CAPS)
            save(root/'contract.json',c);cp=pin(root/'contract.json')
            seed=dict(contract=c,contract_path=cp['path'],contract_sha256=cp['sha256'],host=live,bound=bound)
            # Keep every seeded path and the yield inside the live temporary
            # fixture. c stores serialized strings; filesystem operations use
            # the local Path object, never a repr/JSON-escaped representation.
            historical=root/'remaining'
            assert root.is_dir() and str(historical)==c['output']
            historical.mkdir()
            acceptance_path=historical/'accepted-plan.json';acceptance_row=saved._acceptance(seed);save(acceptance_path,acceptance_row)
            acceptance=pin(acceptance_path)
            save(historical/'journal.json',dict(schema='type3-saved117-validation-journal-v1',status='complete',attempts=dict(remaining_validations=1),
                contract_sha256=cp['sha256'],completed_sections=list(saved.SECTIONS),declared_caps=saved.CAPS,device_operations=[],acceptance=acceptance,
                synthetic_fixture_only=True))
            yield dict(root=root,plan=plan,c=c,cp=cp,bound=bound,pair=pair,packages=packages,acceptance=acceptance,acceptance_row=acceptance_row,
                validation_host=live,historical=historical,offline=offline,failed=failed)


class DeviceEntry119Tests(unittest.TestCase):
    completed_sections=[]
    def complete(self,name):
        type(self).completed_sections.append(name)
        save(OUTPUT/'progress.json',dict(schema=RESULT_SCHEMA,scope=SCOPE,selected=[METHOD],completed_sections=list(type(self).completed_sections)))

    def test_device_entry_after_canonical_fixture_scope_fix(self):
        with synthetic_saved118() as fixture,ExitStack() as stack:
            root=fixture['root'];plan=fixture['plan'];bound=fixture['bound'];packages=fixture['packages'];cp=fixture['cp']
            acceptance=fixture['acceptance'];acceptance_row=fixture['acceptance_row'];validation_host=fixture['validation_host']
            execution_head='e'*40;output=root/'new119-execution'
            # Exercise the actual common live-source guard; historical85 must
            # never pass through it as an alias for today's changed bytes.
            actual_host_binding=profile.host_binding;host_calls=[]
            def live_only(head):
                self.assertNotEqual(head,saved.VALIDATION118_HEAD)
                host_calls.append(head);return actual_host_binding(head)
            stack.enter_context(patch.object(profile,'host_binding',side_effect=live_only))
            live=profile.host_binding(execution_head)
            device=dict(schema=saved.DEVICE119_SCHEMA,status='reviewed_ready',execution_version='v119',producer_execution_version='v117',
                producing_host_source_head=saved.HEAD,validation_host_source_head=saved.VALIDATION118_HEAD,
                validation_host_source_sha256=dict(saved.VALIDATION118_PINS),execution_host_source_head=execution_head,
                execution_host_source_sha256=live['host_profile_source_sha256'],plan=fixture['c']['plan'],packages=str(packages),
                package_result_sha256=fixture['c']['package_result']['sha256'],bound_image_sha256=bound['image_sha256'],remaining_acceptance=acceptance,
                output=str(output),minimum_battery=10,BOOT_write_max=1,reboot_max=1,
                user_availability_record_sha256='4a639d278836af88256a339d199b9fbe53ad65d354db4b8c4401796522e758e9',linked_growth_ack=native.growth_ack())
            save(root/'device119.json',device);dp=pin(root/'device119.json')
            context=saved._device(dp['path'],dp['sha256'],device['plan']['path'],device['plan']['sha256'],None,'v119',execution_head,output)
            self.assertEqual(context['device_context']['packages'],str(packages))
            self.assertEqual(context['host'],validation_host);self.assertEqual(context['host']['host_profile_source_head'],saved.VALIDATION118_HEAD)
            self.assertEqual(context['device_context']['execution_host_source_head'],execution_head)
            self.assertEqual(context['device_context']['schema'],saved.CONTEXT119_SCHEMA)
            self.assertEqual(len(context['host']['host_profile_source_sha256']),85)
            self.assertNotEqual(context['host']['host_profile_source_sha256'],live['host_profile_source_sha256'])
            self.assertIsNone(saved._VALIDATION118_READ.get());self.assertFalse(output.exists())
            self.complete('actual_device_none_packages_and_separate_validation85')
            with self.assertRaisesRegex(ValueError,'contradict'):
                saved._device(dp['path'],dp['sha256'],device['plan']['path'],device['plan']['sha256'],root/'different-packages','v119',execution_head,output)
            with self.assertRaisesRegex(ValueError,'typed read authority'):saved.load(cp['path'],cp['sha256'])
            stale=dict(device,schema=saved.DEVICE_SCHEMA,execution_version='v118');save(root/'stale118.json',stale);sp=pin(root/'stale118.json')
            with self.assertRaisesRegex(ValueError,'closed119'):
                saved._device(sp['path'],sp['sha256'],device['plan']['path'],device['plan']['sha256'],None,'v118',execution_head,output)
            with self.assertRaisesRegex(ValueError,'spent118'):
                auto_cycle.run_plan(device['plan']['path'],device['plan']['sha256'],root/'stale-output',execute=True,limit=1,adb=object(),
                    ack_kernel_readonly_growth=True,declared_test_version='v118',execution_host_source_head=execution_head,
                    type3_device_contract=sp['path'],type3_device_contract_sha256=sp['sha256'])
            self.assertFalse(output.exists());self.assertFalse((root/'stale-output').exists())
            self.complete('contradictory_packages_and_stale118_refused_before_output')
            changed=dict(saved.VALIDATION118_PINS);changed[sorted(changed)[0]]='0'*64
            mutated=dict(acceptance_row,validation_host=dict(validation_host,host_profile_source_sha256=changed))
            save(root/'mutated-acceptance.json',mutated);bad_device=dict(device,remaining_acceptance=pin(root/'mutated-acceptance.json'))
            save(root/'bad-device.json',bad_device);bp=pin(root/'bad-device.json')
            with self.assertRaisesRegex(ValueError,'provenance/map'):
                saved._device(bp['path'],bp['sha256'],device['plan']['path'],device['plan']['sha256'],None,'v119',execution_head,output)
            actual_sha=profile.sha;changed_source=Path(profile.__file__).resolve()
            with patch.object(profile,'sha',side_effect=lambda path:'0'*64 if Path(path).resolve()==changed_source else actual_sha(path)):
                with self.assertRaisesRegex(ValueError,'gates differ'):
                    saved._device(dp['path'],dp['sha256'],device['plan']['path'],device['plan']['sha256'],None,'v119',execution_head,output)
            self.assertIsNone(saved._VALIDATION118_READ.get());self.assertFalse(output.exists())
            self.complete('mutated_accepted85_and_changed_live_bytes_refused')
            class BeforeTransport(Exception):pass
            transport=stack.enter_context(patch.object(auto_cycle,'preflight',side_effect=BeforeTransport()))
            prepare=stack.enter_context(patch.object(saved,'prepare',side_effect=AssertionError('spent validation must not run')))
            tail=stack.enter_context(patch.object(profile,'_validate_plan_tail',side_effect=AssertionError('old tail must not run')))
            prefix=stack.enter_context(patch.object(profile,'validate_template',side_effect=AssertionError('old prefix must not run')))
            # Actual decorated run_plan invokes _device with packages=None;
            # actual __wrapped__ body must receive its accepted119 read context.
            with self.assertRaises(BeforeTransport):
                auto_cycle.run_plan(device['plan']['path'],device['plan']['sha256'],output,execute=True,limit=1,adb=object(),
                    ack_kernel_readonly_growth=True,declared_test_version='v119',execution_host_source_head=execution_head,
                    type3_device_contract=dp['path'],type3_device_contract_sha256=dp['sha256'])
            self.assertEqual(transport.call_count,1);prepare.assert_not_called();tail.assert_not_called();prefix.assert_not_called()
            journal=json.loads((output/'journal.json').read_text(encoding='utf-8'))
            self.assertEqual(journal['type3_execution_context']['schema'],saved.CONTEXT119_SCHEMA)
            self.assertFalse(journal['partition_writes_attempted']);self.assertFalse(journal['reboots_attempted'])
            self.assertEqual(pin(device['plan']['path']),device['plan']);self.assertEqual(pin(acceptance['path']),acceptance)
            self.assertIsNone(saved._READ.get());self.assertIsNone(saved._VALIDATION118_READ.get())
            self.assertNotIn(saved.VALIDATION118_HEAD,host_calls)
            self.complete('actual_run_wrapper_reaches_pretransport_without_old_replay')
        save(OUTPUT/'summary.json',dict(schema=RESULT_SCHEMA,synthetic_only=True,completed_sections=list(type(self).completed_sections),
            actual_private_inputs=0,actual_device_operations=[],old_methods_run=0,old_validation_prefix_runs=0,real_prepare_calls=0,real_tail_calls=0,
            Image_reads=0,Image_builds=0,CI=0,fixture_compiles=0,fixture_processes=0,decoder_or_MachO_replays=0))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--scope',required=True,choices=(SCOPE,));parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args();OUTPUT=args.output.resolve()
    if not OUTPUT.is_relative_to((Path(__file__).resolve().parents[2]/'note10/private').resolve()):raise ValueError('private synthetic output required')
    OUTPUT.mkdir(parents=True,exist_ok=False)
    result=unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite([DeviceEntry119Tests(METHOD)]))
    save(OUTPUT/'result.json',dict(schema=RESULT_SCHEMA,scope=SCOPE,selected=[METHOD],run=result.testsRun,errors=len(result.errors),failures=len(result.failures),
        passed=result.wasSuccessful(),caps=CAPS,prior_method_passed=False,prior_completed_sections=[],original_method_run=0,completed_sections=list(DeviceEntry119Tests.completed_sections),actual_private_inputs=0,
        actual_device_operations=[],old_methods_run=0,old_validation_prefix_runs=0,real_prepare_calls=0,real_tail_calls=0,
        fixture_compiles=0,fixture_processes=0,Image_builds=0,CI=0,
        error_tracebacks=[dict(test=t.id(),traceback=trace) for t,trace in result.errors],failure_tracebacks=[dict(test=t.id(),traceback=trace) for t,trace in result.failures]))
    raise SystemExit(0 if result.wasSuccessful() else 1)
