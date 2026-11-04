"""ONE new closed synthetic host117 integration method, no Image/provider/device."""
import argparse
from contextlib import ExitStack, contextmanager
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import native_scoped_output as scoped
import native_scoped_output_admission as admission
import class3_native_origin as origins
import type3_admission as typed
import type3_remaining_pack as remaining
import kernel_readonly_span_candidate as ro3
import kernel_readonly_input as physical
import readonly_stage_witness as stage
import linux_data_carrier as data
import sha256_kat_device_profile as profile
from builtin_init_profile import EXTRA_FIELDS
from decode_reservation import checksum

METHOD='test_remaining_selected_text_join_and_packer_dispatch'
SCOPE='v117-native116-scoped-output-host-admission-remaining-rev1'
RESULT_SCHEMA='v117-native116-scoped-output-host-remaining-rev1-test-v1'
CAPS={'local_tests':1,'local_C_compiles':0,'CI':0,'new_grouped_methods':1,'new_fixture_compiles':0,
    'new_fixture_processes':0,'old_fixture_runs':0,'old_methods':0,'native_target_builds':0,'kernel_builds':0,
    'Image_builds':0,'real_decoder':0,'MachO':0,'private_payload':0,'Linux_integration':0,
    'target_RAM_reservation':0,'device_queries':0,'BOOT_writes':0,'reboots':0,'max_requested_PC_payload_bytes':0}
OUTPUT=None


def sha(raw):return hashlib.sha256(raw).hexdigest()
def save(path,row):Path(path).write_text(json.dumps(row,indent=2)+'\n',encoding='utf-8')
def frame(marker,body,boot='3'*32):return f'N10BOOTLINK2 boot={boot} {marker} {body} checksum={checksum(body.encode("ascii")):08x}'


def corpus(status='ok',flags=0x3ff,reads=2,cleanup='void_returned'):
    identity='1'*32;cycle='2'*32
    core=f'id={identity} cycle={cycle} kind=result source={ro3.MODE} status={status} carrier={ro3.CAPACITY} logical={ro3.CAPACITY} carrier_rc=0 stream=18 payload={ro3.old.PAYLOAD_BYTES} consumed=18 written={ro3.old.PAYLOAD_BYTES} calls=1 digest={"a"*64} reasons=00000000 expectations=1 captures=0 retained=1 ownership=0 executed=0'
    span=f'id={identity} cycle={cycle} kind=span source=linked-kernel phase=pre_descriptor state=checked attempted=1 kernel_checked=1 kernel_bytes=59590656 extents_checked=1 slot_contained=1 descriptor_contained=1 disjoint=1 admission_called=1 reasons=00000000 ownership=0 hardware=0 executed=0'
    stages=f'id={identity} cycle={cycle} kind=stages schema={stage.WIRE_SCHEMA} bits={stage.ALL:08x} work_cleanup=void_returned output_cleanup=void_returned ownership=0 hardware=0 executed=0'
    output=f'id={identity} cycle={cycle} kind=output_scope schema={scoped.WIRE_SCHEMA} flags={flags:08x} reads={reads} allocator=vmalloc retained_after_emit=0 lease_cleanup={cleanup} ownership=0 hardware=0 executed=0'
    return '\n'.join((frame('N10DATARO3',core),frame('N10DATASPAN1',span),frame('N10DATASTAGE1',stages),frame('N10OUTPUTLEASE1',output)))


class Native116Host117Tests(unittest.TestCase):
    completed_sections=[]

    def _record_completed(self,name):
        type(self).completed_sections.append(name)
        save(OUTPUT/'progress.json',dict(schema=RESULT_SCHEMA,scope=SCOPE,selected=[METHOD],
            completed_sections=list(type(self).completed_sections),original_method_run=0,
            completed_prefix_replayed=0,shared_fixture_setup_only=True))

    def _spent_initial_method_do_not_execute(self):
        # Production has no usable placeholder origin. Only this isolated closed
        # synthetic registry is patched; no production override API exists.
        with patch.object(admission,'_NATIVE116',None):
            with self.assertRaisesRegex(ValueError,'not bound'):admission.record()
            with self.assertRaises(ValueError):physical.require_device_scope(dict(diagnostic_kind=scoped.KIND),True)
        native='b'*40;host='c'*40;token='2'*32;identity='1'*32;h='a'*64
        item=dict(head=native,result=h,pins={f'synthetic/source-{n}.py':h for n in range(70)},producer_ci_context={'synthetic_only':True},
            image_sha256=h,image_bytes=50870284,linked_bytes=59590656,source_manifest_sha256=h,
            run_id=1,attempt=1,job_id=2,artifact_id=3,workflow_id=4,state_bytes=88,outcome_bytes=128,
            test_result_sha256=h,fixture_result_sha256=h,plaintext_zip_sha256=h)
        with tempfile.TemporaryDirectory(prefix='v117-new-',dir=OUTPUT) as temporary,ExitStack() as stack:
            root=Path(temporary);packages=root/'packages';variant=root/'offline/plan/cycle-01/kernel-build';backup=root/'backup';out=root/'execution'
            for directory in (packages,variant,backup,out,root/'offline',root/'generic',root/'current'):directory.mkdir(parents=True,exist_ok=True)
            contract_path=root/'offline-contract.json';device_path=root/'device-contract.json';config=b'# synthetic config only\n'
            (variant/'handoff.config').write_bytes(config)
            baseline=dict(bootloader='SYNTHETIC',partitions=[]);save(backup/'backup-manifest.json',baseline)
            host_binding=dict(host_profile_source_head=host,host_profile_source_sha256={'synthetic/live.py':h})
            tool=Path(typed.__file__).resolve().parents[2]/'research/twrp-d2x-reference/aosp-mkbootimg.py'
            contract=dict(schema=typed.OFFLINE_SCHEMA,status='reviewed_ready',execution_version='v117',host_source_head=host,
                native_source_head=native,accepted_result_sha256=h,producer_root=str(root/'generic'),
                ci_success_context=str(root/'context.json'),ci_success_context_sha256=h,
                compact_manifest=str(root/'compact.json'),compact_manifest_sha256=h,backup=str(backup),
                backup_manifest_sha256=sha((backup/'backup-manifest.json').read_bytes()),current_packages=str(root/'current'),
                current_package_result_sha256=h,current_boot_sha256=h,reference_twrp=str(root/'reference.img'),
                mkbootimg=str(tool),output=str(root/'offline'),caps=typed.OFFLINE_CAPS)
            save(contract_path,contract);contract_sha=sha(contract_path.read_bytes())
            slot=dict(schema=ro3.SCHEMA,source=ro3.MODE,capacity=ro3.CAPACITY,descriptor_bytes=80,
                generic=True,patched=False,permanent_input_bytes=ro3.CAPACITY,permanent_descriptor_bytes=80,
                physical_ready=False,descriptor_class=3,boot_page=2048)
            for index,key,symbol,size,preimage,offset in ((1,'slot',ro3.SLOT,ro3.CAPACITY,sha(bytes(ro3.CAPACITY)),4096),
                    (2,'descriptor',ro3.DESC,80,sha(ro3.DESCRIPTOR),4096+ro3.CAPACITY)):
                slot[key]=dict(symbol=symbol,section='.rodata.'+symbol,offset=offset,bytes=size,alignment=16,
                    readonly_flags='A',preimage_sha256=preimage,object_section_index=index,object_symbol_offset=0)
            keys=(*profile.FIELDS,*EXTRA_FIELDS,*data.FIELDS,*data.CARRIER_FIELDS,*typed.BINDING_FIELDS,*admission.SCOPED_FIELDS)
            row=dict.fromkeys(keys,h)
            row.update(device_profile=data.PROFILE,diagnostic_kind=scoped.KIND,data_input_kind=scoped.KIND,storage_input_kind=scoped.KIND,
                source_head=native,native_source_head=native,native_producer_version='v116',version='v117',execution_version='v117',
                native_producer_PC_first_use=True,PC_only=False,**host_binding,**admission.stage_fields(),
                type3_native_origin=dict(source_head=native,accepted_result_sha256=h,source_sha256=item['pins'],native_version='v116'),
                kernel_readonly3_schema=ro3.SCHEMA,kernel_readonly3_slot=slot,kernel_readonly3_span_schema=ro3.old.SPAN_SCHEMA,
                kernel_readonly3_span=dict(schema=ro3.old.SPAN_SCHEMA,kernel_bytes=59590656,text_prefix_bytes=0,slot_contained=True,
                    descriptor_contained=True,disjoint=True,source='linked-kernel',phase='pre_descriptor',hardware=False,ownership=False),
                kernel_readonly3_linked_bytes=59590656,kernel_readonly3_image_bytes=50870284,kernel_readonly3_requires_ack=True,
                kernel_readonly3_marker='N10DATARO3',data_expectation_mode=ro3.MODE,data_expectation_slot=slot,
                data_carrier_stage=data.STAGE,data_relative_placement_admitted=False,raw_input_binding=False,
                type3_external_choice='compact-v1',type3_compact_bytes=ro3.CAPACITY,type3_compact_manifest_sha256=h,
                data_carrier_bytes=ro3.old.OLD_BYTES,data_payload_bytes=ro3.old.PAYLOAD_BYTES,
                type3_contract_path=str(contract_path),type3_contract_sha256=contract_sha,
                image_size=50870284,image_sha256=h,kernel_image_sha256=h,effective_config_sha256=sha(config),
                image_expectation_patched=True,auto_cycle_variant=True,auto_cycle_token=token,auto_cycle_template=str(root/'offline/template'),
                auto_return_diagnostic=True,build_evidence_id=identity,kernel_banner=origins.banner(dict(diagnostic_kind=scoped.KIND))+'synthetic',
                backup_manifest_sha256=contract['backup_manifest_sha256'])
            row['type3_materialization']=typed.materialization(row,token,h,h,h)
            save(variant/'build-result.json',row);save(packages/'package-result.json',row)
            save(root/'offline/transaction.json',dict(status='complete',phase='complete',contract_sha256=contract_sha,result={'plan_sha256':h}))
            stack.enter_context(patch.object(admission,'_NATIVE116',item))
            stack.enter_context(patch.object(profile,'host_binding',return_value=host_binding))
            actual_sha=profile.sha
            from prepare_linux_boot import MKBOOTIMG_SHA256
            # Isolate ONLY the unchanged exact canonical repository tool hash.
            # All canonical path/is_file/no-symlink checks and other hashes run.
            stack.enter_context(patch.object(profile,'sha',side_effect=lambda p:MKBOOTIMG_SHA256 if Path(p)==tool else actual_sha(p)))
            self.assertEqual(typed.load_offline(contract_path,contract_sha),contract)
            self.assertEqual(typed.candidate_scope(row,patched=True),contract)
            # Private baseline authority admits only fixed public111 lineage;
            # raw BOOT/package/terminal pins are not embedded in source.
            baseline_context=dict.fromkeys(admission.CURRENT_KEYS,h)
            baseline_context.update(admission._CURRENT111_LINEAGE,packages=str(root/'current'),
                plan_path=str(root/'saved-plan.json'),execution_receipt_path=str(root/'saved-receipt.json'))
            self.assertEqual(admission._baseline_context(baseline_context),baseline_context)
            with self.assertRaisesRegex(ValueError,'lineage'):
                admission._baseline_context(dict(baseline_context,execution_host=host))
            broken=dict(contract,mkbootimg=str(root/'arbitrary-tool.py'));save(root/'bad-contract.json',broken)
            with self.assertRaisesRegex(ValueError,'canonical repository'):typed.load_offline(root/'bad-contract.json',sha((root/'bad-contract.json').read_bytes()))
            with self.assertRaises(ValueError):typed.candidate_scope(dict(row,native_source_head='d'*40),patched=True)
            with self.assertRaisesRegex(ValueError,'PC formats'):typed.candidate_scope(dict(row,output_writer_schema='n10-host-output-writer-pc-v1'))
            device=dict(schema=admission.DEVICE_SCHEMA,status='reviewed_ready',execution_version='v117',host_source_head=host,
                host_source_sha256=host_binding['host_profile_source_sha256'],native_source_head=native,plan_sha256=h,packages=str(packages),
                package_result_sha256=sha((packages/'package-result.json').read_bytes()),bound_image_sha256=h,
                offline_contract_sha256=contract_sha,output=str(out),minimum_battery=10,BOOT_write_max=1,reboot_max=1,
                user_availability_record_sha256='4a639d278836af88256a339d199b9fbe53ad65d354db4b8c4401796522e758e9',linked_growth_ack=admission.growth_ack())
            save(device_path,device);device_sha=sha(device_path.read_bytes())
            context=typed.execution_context(row,h,packages,'v117',host,device_path,device_sha,out)
            self.assertTrue(physical.require_device_scope(row,True,context))
            self.assertIsNone(admission._DEVICE_READ.get());self.assertIsNone(remaining._ACTIVE.get())
            for ack,ctx in ((False,context),(True,None),(True,dict(context,plan_sha256='d'*64))):
                with self.assertRaises(ValueError):physical.require_device_scope(row,ack,ctx)
            observed=[]
            class ReachedReadScope(Exception):pass
            def stop_before_transport(adb):
                self.assertIsNotNone(admission._DEVICE_READ.get())
                self.assertEqual(profile.variant(variant,token),row)
                with self.assertRaisesRegex(ValueError,'outside'):remaining.require_pack(variant,root/'forbidden.img',token)
                with self.assertRaisesRegex(ValueError,'read-only'):profile.pack(backup,variant,b'',tool,root/'forbidden.img',{},token)
                observed.append('metadata_before_transport');raise ReachedReadScope()
            stack.enter_context(patch('stage_phase2.verify_packages',return_value=[]))
            stack.enter_context(patch('prepare_linux_boot.read_verified_backup',return_value=None))
            transport=stack.enter_context(patch('run_probe.preflight',side_effect=stop_before_transport))
            with self.assertRaises(ReachedReadScope):profile.precheck(packages,variant,backup,object(),{},ack_kernel_readonly_growth=True,type3_context=context)
            self.assertEqual(observed,['metadata_before_transport'])
            self.assertTrue((out/'PREINSTALL-CHECK-01.json').exists());self.assertFalse((packages/'PREINSTALL-CHECK.json').exists())
            with self.assertRaisesRegex(ValueError,'fresh host117'):profile.precheck(packages,variant,backup,object(),{},ack_kernel_readonly_growth=True,type3_context=context)
            with self.assertRaises(ReachedReadScope):profile._collect_into(packages,variant,object(),out,ack_kernel_readonly_growth=True,type3_context=context)
            self.assertEqual(transport.call_count,2)
            for ctx in (None,dict(context,contract_sha256='e'*64)):
                with self.assertRaises(ValueError):profile._collect_into(packages,variant,object(),out,ack_kernel_readonly_growth=True,type3_context=ctx)
            self.assertEqual(transport.call_count,2);self.assertIsNone(admission._DEVICE_READ.get());self.assertIsNone(remaining._ACTIVE.get())
            # New adapter parses all functional companions from one selected text.
            text=corpus();legacy=data.decode(text,identity,token,_source_class=ro3.MODE)
            stages=stage._decode_joined(text,identity,token,legacy,expected_schema=stage.SCHEMA,producer_kind=scoped.KIND)
            joined=admission.decode_joined(text,identity,token,legacy,stages)
            self.assertTrue(joined['passed']);self.assertEqual(joined['reads'],2)
            def selected_text_only(raw,banner,rid,cycle,*,digest_decoder,digest_marker,component_evidence):
                # Mock only the unchanged selected-text/PID1-return envelope;
                # all new class3 functional join/parser logic remains actual.
                self.assertEqual(digest_marker,b'N10DATARO3')
                legacy_row=digest_decoder(raw.decode('ascii'),rid)
                return raw,dict(kat=legacy_row,boot_identity=legacy_row['boot_identity'])
            with patch('builtin_init_profile.decode',side_effect=selected_text_only):
                _,accepted=ro3.decode_selected(text.encode('ascii'),row['kernel_banner'],identity,token,expected=row)
                self.assertTrue(accepted['component_evidence']['functional_acceptance'])
                with self.assertRaises(data.ComponentObservationError) as missing:
                    ro3.decode_selected(text.rsplit('\n',1)[0].encode('ascii'),row['kernel_banner'],identity,token,expected=row)
                evidence=missing.exception.component_evidence
                self.assertIn('kernel_readonly3_data',evidence);self.assertIn('readonly_stage_witness',evidence)
                self.assertEqual(evidence['native_scoped_output']['state'],'invalid_or_missing')
                self.assertFalse(evidence['functional_acceptance'])
            for bad in (text+'\n'+text.splitlines()[-1],text.rsplit('\n',1)[0],text.replace('N10OUTPUTLEASE1','N10OUTPUTLEASE2'),
                    corpus(reads=1),corpus(cleanup='not_called'),text.replace('N10BOOTLINK2 boot='+'3'*32+' N10OUTPUTLEASE1','N10BOOTLINK2 boot='+'4'*32+' N10OUTPUTLEASE1')):
                with self.assertRaises(ValueError):admission.decode_joined(bad,identity,token,legacy,stages)
            for status,flags,reads,cleanup in (('output_offer',0,0,'not_called'),('output_consumer',0x7e3,0,'void_returned')):
                failure=corpus(status,flags,reads,cleanup);raw=data.decode(failure,identity,token,_source_class=ro3.MODE)
                events=stage._decode_joined(failure,identity,token,raw,expected_schema=stage.SCHEMA,producer_kind=scoped.KIND)
                observation=admission.decode_joined(failure,identity,token,raw,events)
                self.assertFalse(observation['passed']);self.assertFalse(raw['passed']);self.assertEqual(raw['status'],status)
                with self.assertRaises(ValueError):stage._decode_joined(failure,identity,token,raw,expected_schema=stage.SCHEMA)
            # Check propagation through the production field projection and actual
            # packer dispatch entry, stopping before any Image/BOOT input read.
            projected=profile.fields(row)
            self.assertTrue(all(projected[key]==row[key] for key in admission.SCOPED_FIELDS))
            import prepare_linux_boot as packer
            class IntrinsicReadReached(Exception):pass
            def no_image(path):
                if Path(path)==variant/'Image':raise IntrinsicReadReached()
                raise AssertionError('unexpected binary input')
            with patch.object(Path,'read_bytes',no_image):
                with self.assertRaises(IntrinsicReadReached):packer.pack_verified(backup,variant,root/'reference.img',tool,root/'never.img',{},row,config,token,kat_profile=True)
            self.assertFalse((root/'never.img').exists())
        save(OUTPUT/'summary.json',dict(schema=RESULT_SCHEMA,synthetic_only=True,new_host_method=1,
            raw_Image_reads=0,fixture_compiles=0,fixture_processes=0,CI=0,actual_device_operations=[],old_methods=0,
            exact_native116_origin_bound_in_production=True,companion_required=True,PC_formats_permanently_forbidden=True,
            output_lifetime_semantics='call_boundaries_only',global_RAM_ownership=False,xnu_executed=False))


    @contextmanager
    def _remaining_setup(self):
        native='b'*40;host='c'*40;token='2'*32;identity='1'*32;h='a'*64
        item=dict(head=native,result=h,pins={f'synthetic/source-{n}.py':h for n in range(70)},producer_ci_context={'synthetic_only':True},
            image_sha256=h,image_bytes=50870284,linked_bytes=59590656,source_manifest_sha256=h,
            run_id=1,attempt=1,job_id=2,artifact_id=3,workflow_id=4,state_bytes=88,outcome_bytes=128,
            test_result_sha256=h,fixture_result_sha256=h,plaintext_zip_sha256=h)
        with tempfile.TemporaryDirectory(prefix='v117-new-',dir=OUTPUT) as temporary,ExitStack() as stack:
            root=Path(temporary);packages=root/'packages';variant=root/'offline/plan/cycle-01/kernel-build';backup=root/'backup';out=root/'execution'
            for directory in (packages,variant,backup,out,root/'offline',root/'generic',root/'current'):directory.mkdir(parents=True,exist_ok=True)
            contract_path=root/'offline-contract.json';device_path=root/'device-contract.json';config=b'# synthetic config only\n'
            (variant/'handoff.config').write_bytes(config)
            baseline=dict(bootloader='SYNTHETIC',partitions=[]);save(backup/'backup-manifest.json',baseline)
            host_binding=dict(host_profile_source_head=host,host_profile_source_sha256={'synthetic/live.py':h})
            tool=Path(typed.__file__).resolve().parents[2]/'research/twrp-d2x-reference/aosp-mkbootimg.py'
            contract=dict(schema=typed.OFFLINE_SCHEMA,status='reviewed_ready',execution_version='v117',host_source_head=host,
                native_source_head=native,accepted_result_sha256=h,producer_root=str(root/'generic'),
                ci_success_context=str(root/'context.json'),ci_success_context_sha256=h,
                compact_manifest=str(root/'compact.json'),compact_manifest_sha256=h,backup=str(backup),
                backup_manifest_sha256=sha((backup/'backup-manifest.json').read_bytes()),current_packages=str(root/'current'),
                current_package_result_sha256=h,current_boot_sha256=h,reference_twrp=str(root/'reference.img'),
                mkbootimg=str(tool),output=str(root/'offline'),caps=typed.OFFLINE_CAPS)
            save(contract_path,contract);contract_sha=sha(contract_path.read_bytes())
            slot=dict(schema=ro3.SCHEMA,source=ro3.MODE,capacity=ro3.CAPACITY,descriptor_bytes=80,
                generic=True,patched=False,permanent_input_bytes=ro3.CAPACITY,permanent_descriptor_bytes=80,
                physical_ready=False,descriptor_class=3,boot_page=2048)
            for index,key,symbol,size,preimage,offset in ((1,'slot',ro3.SLOT,ro3.CAPACITY,sha(bytes(ro3.CAPACITY)),4096),
                    (2,'descriptor',ro3.DESC,80,sha(ro3.DESCRIPTOR),4096+ro3.CAPACITY)):
                slot[key]=dict(symbol=symbol,section='.rodata.'+symbol,offset=offset,bytes=size,alignment=16,
                    readonly_flags='A',preimage_sha256=preimage,object_section_index=index,object_symbol_offset=0)
            keys=(*profile.FIELDS,*EXTRA_FIELDS,*data.FIELDS,*data.CARRIER_FIELDS,*typed.BINDING_FIELDS,*admission.SCOPED_FIELDS)
            row=dict.fromkeys(keys,h)
            row.update(device_profile=data.PROFILE,diagnostic_kind=scoped.KIND,data_input_kind=scoped.KIND,storage_input_kind=scoped.KIND,
                source_head=native,native_source_head=native,native_producer_version='v116',version='v117',execution_version='v117',
                native_producer_PC_first_use=True,PC_only=False,**host_binding,**admission.stage_fields(),
                type3_native_origin=dict(source_head=native,accepted_result_sha256=h,source_sha256=item['pins'],native_version='v116'),
                kernel_readonly3_schema=ro3.SCHEMA,kernel_readonly3_slot=slot,kernel_readonly3_span_schema=ro3.old.SPAN_SCHEMA,
                kernel_readonly3_span=dict(schema=ro3.old.SPAN_SCHEMA,kernel_bytes=59590656,text_prefix_bytes=0,slot_contained=True,
                    descriptor_contained=True,disjoint=True,source='linked-kernel',phase='pre_descriptor',hardware=False,ownership=False),
                kernel_readonly3_linked_bytes=59590656,kernel_readonly3_image_bytes=50870284,kernel_readonly3_requires_ack=True,
                kernel_readonly3_marker='N10DATARO3',data_expectation_mode=ro3.MODE,data_expectation_slot=slot,
                data_carrier_stage=data.STAGE,data_relative_placement_admitted=False,raw_input_binding=False,
                type3_external_choice='compact-v1',type3_compact_bytes=ro3.CAPACITY,type3_compact_manifest_sha256=h,
                data_carrier_bytes=ro3.old.OLD_BYTES,data_payload_bytes=ro3.old.PAYLOAD_BYTES,
                type3_contract_path=str(contract_path),type3_contract_sha256=contract_sha,
                image_size=50870284,image_sha256=h,kernel_image_sha256=h,effective_config_sha256=sha(config),
                image_expectation_patched=True,auto_cycle_variant=True,auto_cycle_token=token,auto_cycle_template=str(root/'offline/template'),
                auto_return_diagnostic=True,build_evidence_id=identity,kernel_banner=origins.banner(dict(diagnostic_kind=scoped.KIND))+'synthetic',
                backup_manifest_sha256=contract['backup_manifest_sha256'])
            row['type3_materialization']=typed.materialization(row,token,h,h,h)
            save(variant/'build-result.json',row);save(packages/'package-result.json',row)
            save(root/'offline/transaction.json',dict(status='complete',phase='complete',contract_sha256=contract_sha,result={'plan_sha256':h}))
            stack.enter_context(patch.object(admission,'_NATIVE116',item))
            stack.enter_context(patch.object(profile,'host_binding',return_value=host_binding))
            actual_sha=profile.sha
            from prepare_linux_boot import MKBOOTIMG_SHA256
            # Isolate ONLY the unchanged exact canonical repository tool hash.
            # All canonical path/is_file/no-symlink checks and other hashes run.
            stack.enter_context(patch.object(profile,'sha',side_effect=lambda p:MKBOOTIMG_SHA256 if Path(p)==tool else actual_sha(p)))
            yield dict(root=root,row=row,variant=variant,backup=backup,tool=tool,config=config,token=token,identity=identity)

    def test_remaining_selected_text_join_and_packer_dispatch(self):
        # Continuation starts at the original failing adapter call. The completed
        # prefix is carried as evidence, never invoked by this selected method.
        with self._remaining_setup() as fixture:
            root=fixture['root'];row=fixture['row'];variant=fixture['variant'];backup=fixture['backup']
            tool=fixture['tool'];config=fixture['config'];token=fixture['token'];identity=fixture['identity']
            text=corpus()
            def selected_text_only(raw,banner,rid,cycle,*,digest_decoder,digest_marker,component_evidence):
                # Mock only the unchanged selected-text/PID1-return envelope;
                # all new class3 functional join/parser logic remains actual.
                self.assertEqual(digest_marker,b'N10DATARO3')
                legacy_row=digest_decoder(raw.decode('ascii'),rid)
                return raw,dict(kat=legacy_row,boot_identity=legacy_row['boot_identity'])
            with patch('builtin_init_profile.decode',side_effect=selected_text_only):
                _,accepted=ro3.decode_selected(text.encode('ascii'),row['kernel_banner'],identity,token,expected=row)
                self.assertTrue(accepted['component_evidence']['functional_acceptance'])
                legacy=accepted['component_evidence']['kernel_readonly3_data']
                stages=accepted['component_evidence']['readonly_stage_witness']
                with self.assertRaises(data.ComponentObservationError) as missing:
                    ro3.decode_selected(text.rsplit('\n',1)[0].encode('ascii'),row['kernel_banner'],identity,token,expected=row)
                evidence=missing.exception.component_evidence
                self.assertIn('kernel_readonly3_data',evidence);self.assertIn('readonly_stage_witness',evidence)
                self.assertEqual(evidence['native_scoped_output']['state'],'invalid_or_missing')
                self.assertFalse(evidence['functional_acceptance'])
            self._record_completed('selected_text_join_and_missing_companion')
            for bad in (text+'\n'+text.splitlines()[-1],text.rsplit('\n',1)[0],text.replace('N10OUTPUTLEASE1','N10OUTPUTLEASE2'),
                    corpus(reads=1),corpus(cleanup='not_called'),text.replace('N10BOOTLINK2 boot='+'3'*32+' N10OUTPUTLEASE1','N10BOOTLINK2 boot='+'4'*32+' N10OUTPUTLEASE1')):
                with self.assertRaises(ValueError):admission.decode_joined(bad,identity,token,legacy,stages)
            self._record_completed('closed_output_companion_rejections')
            for status,flags,reads,cleanup in (('output_offer',0,0,'not_called'),('output_consumer',0x7e3,0,'void_returned')):
                failure=corpus(status,flags,reads,cleanup);raw=data.decode(failure,identity,token,_source_class=ro3.MODE)
                events=stage._decode_joined(failure,identity,token,raw,expected_schema=stage.SCHEMA,producer_kind=scoped.KIND)
                observation=admission.decode_joined(failure,identity,token,raw,events)
                self.assertFalse(observation['passed']);self.assertFalse(raw['passed']);self.assertEqual(raw['status'],status)
                with self.assertRaises(ValueError):stage._decode_joined(failure,identity,token,raw,expected_schema=stage.SCHEMA)
            self._record_completed('scoped_failure_phase_evidence')
            # Check propagation through the production field projection and actual
            # packer dispatch entry, stopping before any Image/BOOT input read.
            projected=profile.fields(row)
            self.assertTrue(all(projected[key]==row[key] for key in admission.SCOPED_FIELDS))
            self._record_completed('package_field_projection')
            import prepare_linux_boot as packer
            class IntrinsicReadReached(Exception):pass
            def no_image(path):
                if Path(path)==variant/'Image':raise IntrinsicReadReached()
                raise AssertionError('unexpected binary input')
            with patch.object(Path,'read_bytes',no_image):
                with self.assertRaises(IntrinsicReadReached):packer.pack_verified(backup,variant,root/'reference.img',tool,root/'never.img',{},row,config,token,kat_profile=True)
            self.assertFalse((root/'never.img').exists())
            self._record_completed('packer_dispatch_before_intrinsic_input')
        save(OUTPUT/'summary.json',dict(completed_sections=list(type(self).completed_sections),schema=RESULT_SCHEMA,synthetic_only=True,remaining_host_method=1,
            completed_prefix_replayed=0,original_method_run=0,shared_fixture_setup_only=True,
            raw_Image_reads=0,fixture_compiles=0,fixture_processes=0,CI=0,actual_device_operations=[],old_methods=0,
            companion_required=True,output_lifetime_semantics='call_boundaries_only',global_RAM_ownership=False,xnu_executed=False))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--scope',required=True,choices=(SCOPE,));parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();OUTPUT=args.output.resolve()
    if not OUTPUT.is_relative_to((Path(__file__).resolve().parents[2]/'note10/private').resolve()):raise ValueError('private synthetic output required')
    OUTPUT.mkdir(parents=True,exist_ok=False)
    result=unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite([Native116Host117Tests(METHOD)]))
    save(OUTPUT/'result.json',dict(schema=RESULT_SCHEMA,scope=args.scope,selected=[METHOD],run=result.testsRun,
        errors=len(result.errors),failures=len(result.failures),passed=result.wasSuccessful(),caps=CAPS,completed_sections=list(Native116Host117Tests.completed_sections),
        error_tracebacks=[dict(test=t.id(),traceback=trace) for t,trace in result.errors],
        failure_tracebacks=[dict(test=t.id(),traceback=trace) for t,trace in result.failures],fixture_compiles=0,
        fixture_processes=0,Image_builds=0,CI=0,actual_device_operations=[],old_methods_run=0,original_method_run=0,completed_prefix_replayed=0,shared_fixture_setup_only=True))
    raise SystemExit(0 if result.wasSuccessful() else 1)
