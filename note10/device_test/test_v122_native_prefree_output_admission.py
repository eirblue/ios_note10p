"""One NEW synthetic native121/host122 admission and prefree join method."""
import argparse
from contextlib import ExitStack
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import native_prefree_output_admission as prefree
import native_prefree_output_zero as native
import native_scoped_output_admission as admission
import type3_admission as typed
import type3_remaining_pack as remaining
import class3_native_origin as origins
import kernel_readonly_span_candidate as ro3
import kernel_readonly_input as physical
import readonly_stage_witness as stage
import linux_data_carrier as data
import sha256_kat_device_profile as profile
from builtin_init_profile import EXTRA_FIELDS
from decode_reservation import checksum
METHOD='test_native121_typed_origin_prefree_join_and_packages_none_before_transport'
SCOPE='v122-native121-prefree-output-admission'
RESULT_SCHEMA='v122-native121-prefree-host-test-v1'
CAPS={'local_tests':1,'local_C_compiles':0,'CI':0,'new_grouped_methods':1,'new_fixture_compiles':0,'new_fixture_processes':0,'old_fixture_runs':0,'old_methods':0,'native_target_builds':0,'kernel_builds':0,'Image_builds':0,'real_decoder':0,'MachO':0,'private_payload':0,'Linux_integration':0,'target_RAM_reservation':0,'device_queries':0,'BOOT_writes':0,'reboots':0,'max_requested_PC_payload_bytes':4096}
OUTPUT=None

def sha(raw):return hashlib.sha256(raw).hexdigest()
def save(path,row):Path(path).write_text(json.dumps(row,indent=2)+'\n',encoding='utf-8')
def frame(marker,body,boot='3'*32):return f'N10BOOTLINK2 boot={boot} {marker} {body} checksum={checksum(body.encode("ascii")):08x}'

def corpus(payload=ro3.old.PAYLOAD_BYTES,written=None,status='ok',nonzero=0,reads=None,zero=None,free_result='void_returned',boot='3'*32):
    written=payload if written is None else written;reads=payload if reads is None else reads;zero=int(nonzero==0) if zero is None else zero
    ident='1'*32;cycle='2'*32
    bits=stage.ALL;lease=0x3ff;borrow_reads=2
    if status=='decode':
        for name in ('api_ok','length_enter','length_ok','hash_called','hash_returned','digest_enter','digest_ok'):bits &= ~(1<<stage.EVENTS.index(name))
        lease=0x3c0;borrow_reads=0
    core=f'id={ident} cycle={cycle} kind=result source={ro3.MODE} status={status} carrier={ro3.CAPACITY} logical={ro3.CAPACITY} carrier_rc=0 stream=18 payload={payload} consumed=18 written={written} calls=1 digest={"a"*64} reasons=00000000 expectations=1 captures=0 retained=1 ownership=0 executed=0'
    span=f'id={ident} cycle={cycle} kind=span source=linked-kernel phase=pre_descriptor state=checked attempted=1 kernel_checked=1 kernel_bytes=59588608 extents_checked=1 slot_contained=1 descriptor_contained=1 disjoint=1 admission_called=1 reasons=00000000 ownership=0 hardware=0 executed=0'
    stages=f'id={ident} cycle={cycle} kind=stages schema={stage.WIRE_SCHEMA} bits={bits:08x} work_cleanup=void_returned output_cleanup=void_returned ownership=0 hardware=0 executed=0'
    output=f'id={ident} cycle={cycle} kind=output_scope schema=native-output-scope-v1 flags={lease:08x} reads={borrow_reads} allocator=vmalloc retained_after_emit=0 lease_cleanup=void_returned ownership=0 hardware=0 executed=0'
    observation=f'id={ident} cycle={cycle} kind=prefree_zero schema={native.WIRE_SCHEMA} capacity={payload} reads={reads} nonzero={nonzero} scan_called=1 scan_returned=1 observed_zero={zero} free_called=1 free_returned=1 free_result={free_result} ownership=0 hardware=0 executed=0'
    return '\n'.join((frame('N10DATARO3',core),frame('N10DATASPAN1',span),frame('N10DATASTAGE1',stages),frame('N10OUTPUTLEASE1',output),frame('N10OUTPUTZERO1',observation,boot)))

class Native121Host122Tests(unittest.TestCase):
    completed_sections=[]
    def done(self,name):
        type(self).completed_sections.append(name)
        save(OUTPUT/'progress.json',dict(schema=RESULT_SCHEMA,scope=SCOPE,selected=[METHOD],completed_sections=list(type(self).completed_sections)))

    def test_native121_typed_origin_prefree_join_and_packages_none_before_transport(self):
        item=prefree.record();host='c'*40;h='a'*64;token='2'*32
        self.assertEqual(len(item['pins']),74);self.assertEqual(item['version'],'v121')
        isolated=prefree.record();pin=next(iter(isolated['pins']));original_pin=item['pins'][pin]
        isolated['pins'][pin]='0'*64;isolated['producer_ci_context']['GITHUB_SHA']='0'*40
        self.assertEqual(prefree.record()['pins'][pin],original_pin)
        self.assertEqual(prefree.record()['producer_ci_context'],item['producer_ci_context'])
        with self.assertRaises(TypeError):prefree._NATIVE121['pins'][pin]='0'*64
        compiler=dict(temporary_outcome_bytes=128)
        producer=dict(source_sha256=item['pins'],version='v121',diagnostic_kind=native.KIND,image_bytes=item['image_bytes'],image_sha256=item['image_sha256'],kernel_readonly3_linked_bytes=item['linked_bytes'],passed=True,Image_built=True,kernel_or_provider_executed=False,ci_context={'GITHUB_SHA':item['head']},PC_only=False,physical_ready=False,operation_scope_PC_only=True,admission_blocked=True,kernel_readonly3_candidate_contract=compiler,data_footprint={'data_state_bytes':88})
        with patch.object(ro3,'producer_contract',return_value=compiler):
            self.assertEqual(admission.producer(producer,item['head']),compiler)
            bad=copy.deepcopy(producer);bad['source_sha256']['synthetic/mutated.py']=h
            with self.assertRaises(ValueError):admission.producer(bad,item['head'])
        self.assertFalse(admission.provenance(item['head'])['physical_ready'])
        with self.assertRaisesRegex(ValueError,'composition'):profile.physical_input_scope(producer,readonly_origin=item['head'])
        self.done('accepted_native121_origin_and_immutable_provenance')
        with tempfile.TemporaryDirectory(prefix='v122-new-',dir=OUTPUT) as temporary,ExitStack() as stack:
            root=Path(temporary);packages=root/'packages';variant=root/'offline/plan/cycle-01/kernel-build';backup=root/'backup';out=root/'execution'
            for directory in (packages,variant,backup,out,root/'generic',root/'current'):directory.mkdir(parents=True,exist_ok=True)
            config=b'# synthetic only\n';(variant/'handoff.config').write_bytes(config)
            save(backup/'backup-manifest.json',dict(bootloader='SYNTHETIC',partitions=[]))
            live=root/'live.py';live.write_bytes(b'# synthetic live source\n');live_pin=sha(live.read_bytes())
            binding=dict(host_profile_source_head=host,host_profile_source_sha256={'synthetic/live.py':live_pin})
            def live_binding(head):
                data.require(head==host and sha(live.read_bytes())==live_pin,'closed synthetic live source changed')
                return binding
            stack.enter_context(patch.object(profile,'host_binding',side_effect=live_binding))
            tool=Path(typed.__file__).resolve().parents[2]/'research/twrp-d2x-reference/aosp-mkbootimg.py'
            actual_sha=profile.sha
            from prepare_linux_boot import MKBOOTIMG_SHA256
            stack.enter_context(patch.object(profile,'sha',side_effect=lambda p:MKBOOTIMG_SHA256 if Path(p)==tool else actual_sha(p)))
            contract_path=root/'offline-contract.json';device_path=root/'device-contract.json'
            contract=dict(schema=typed.OFFLINE_SCHEMA,status='reviewed_ready',execution_version='v122',host_source_head=host,native_source_head=item['head'],accepted_result_sha256=item['result'],producer_root=str(root/'generic'),ci_success_context=str(root/'context.json'),ci_success_context_sha256=h,compact_manifest=str(root/'compact.json'),compact_manifest_sha256=h,backup=str(backup),backup_manifest_sha256=sha((backup/'backup-manifest.json').read_bytes()),current_packages=str(root/'current'),current_package_result_sha256=h,current_boot_sha256=h,reference_twrp=str(root/'reference.img'),mkbootimg=str(tool),output=str(root/'offline'),caps=typed.OFFLINE_CAPS)
            save(contract_path,contract);contract_sha=sha(contract_path.read_bytes())
            slot=dict(schema=ro3.SCHEMA,source=ro3.MODE,capacity=ro3.CAPACITY,descriptor_bytes=80,generic=True,patched=False,permanent_input_bytes=ro3.CAPACITY,permanent_descriptor_bytes=80,physical_ready=False,descriptor_class=3,boot_page=2048)
            for index,key,symbol,size,preimage,offset in ((1,'slot',ro3.SLOT,ro3.CAPACITY,sha(bytes(ro3.CAPACITY)),4096),(2,'descriptor',ro3.DESC,80,sha(ro3.DESCRIPTOR),4096+ro3.CAPACITY)):
                slot[key]=dict(symbol=symbol,section='.rodata.'+symbol,offset=offset,bytes=size,alignment=16,readonly_flags='A',preimage_sha256=preimage,object_section_index=index,object_symbol_offset=0)
            keys=(*profile.FIELDS,*EXTRA_FIELDS,*data.FIELDS,*data.CARRIER_FIELDS,*typed.BINDING_FIELDS,*admission.SCOPED_FIELDS,*prefree.FIELDS)
            row=dict.fromkeys(keys,h)
            row.update(device_profile=data.PROFILE,diagnostic_kind=native.KIND,data_input_kind=native.KIND,storage_input_kind=native.KIND,source_head=item['head'],native_source_head=item['head'],native_producer_version='v121',version='v122',execution_version='v122',native_producer_PC_first_use=True,PC_only=False,**binding,**admission.stage_fields(item['head']),type3_native_origin=origins.origin(item['head']),kernel_readonly3_schema=ro3.SCHEMA,kernel_readonly3_slot=slot,kernel_readonly3_span_schema=ro3.old.SPAN_SCHEMA,kernel_readonly3_span=dict(schema=ro3.old.SPAN_SCHEMA,kernel_bytes=item['linked_bytes'],text_prefix_bytes=0,slot_contained=True,descriptor_contained=True,disjoint=True,source='linked-kernel',phase='pre_descriptor',hardware=False,ownership=False),kernel_readonly3_linked_bytes=item['linked_bytes'],kernel_readonly3_image_bytes=item['image_bytes'],kernel_readonly3_requires_ack=True,kernel_readonly3_marker='N10DATARO3',data_expectation_mode=ro3.MODE,data_expectation_slot=slot,data_carrier_stage=data.STAGE,data_relative_placement_admitted=False,raw_input_binding=False,type3_external_choice='compact-v1',type3_compact_bytes=ro3.CAPACITY,type3_compact_manifest_sha256=h,data_carrier_bytes=ro3.old.OLD_BYTES,data_payload_bytes=ro3.old.PAYLOAD_BYTES,type3_contract_path=str(contract_path),type3_contract_sha256=contract_sha,image_size=item['image_bytes'],image_sha256=h,kernel_image_sha256=h,effective_config_sha256=sha(config),image_expectation_patched=True,auto_cycle_variant=True,auto_cycle_token=token,auto_cycle_template=str(root/'offline/template'),auto_return_diagnostic=True,build_evidence_id='1'*32,kernel_banner=origins.banner(dict(diagnostic_kind=native.KIND))+'synthetic',backup_manifest_sha256=contract['backup_manifest_sha256'])
            row['type3_materialization']=typed.materialization(row,token,h,h,h)
            save(variant/'build-result.json',row);save(packages/'package-result.json',row)
            # Actual new typed pack transaction gate; unchanged variant bytes and
            # packer I/O are isolated here. Actual saved-metadata reader is exercised below.
            save(root/'offline/transaction.json',dict(schema='type3-offline-journal-v1',status='started',phase='plan_reserved',contract_sha256=contract_sha))
            with patch.object(profile,'variant',return_value=row),patch('prepare_linux_boot.pack_verified',return_value={'synthetic_only':True}) as packer:
                self.assertEqual(profile.pack(backup,variant,b'',tool,root/'offline/plan/cycle-01/boot.img',{},token),{'synthetic_only':True})
                self.assertEqual(packer.call_count,1)
            save(root/'offline/transaction.json',dict(status='complete',phase='complete',contract_sha256=contract_sha,result={'plan_sha256':h}))
            self.assertEqual(typed.candidate_scope(row,patched=True),contract)
            for changed in (dict(row,version='v117'),dict(row,host_profile_source_sha256={'changed':h}),dict(row,diagnostic_kind='unsupported'),dict(row,output_retirement_schema='n10-host-output-retirement-zero-pc-v1')):
                with self.assertRaises(ValueError):typed.candidate_scope(changed,patched=True)
            device=dict(schema=prefree.device_schema(item['head']),status='reviewed_ready',execution_version='v122',host_source_head=host,host_source_sha256=binding['host_profile_source_sha256'],native_source_head=item['head'],plan_sha256=h,packages=str(packages),package_result_sha256=sha((packages/'package-result.json').read_bytes()),bound_image_sha256=h,offline_contract_sha256=contract_sha,output=str(out),minimum_battery=10,BOOT_write_max=1,reboot_max=1,user_availability_record_sha256='4a639d278836af88256a339d199b9fbe53ad65d354db4b8c4401796522e758e9',linked_growth_ack=admission.growth_ack(item['head']))
            save(device_path,device);device_sha=sha(device_path.read_bytes())
            context=typed.execution_context(row,h,None,'v122',host,device_path,device_sha,out)
            self.assertEqual(context['packages'],str(packages));self.assertTrue(physical.require_device_scope(row,True,context))
            for supplied in (root/'other',):
                with self.assertRaisesRegex(ValueError,'packages contradict'):typed.execution_context(row,h,supplied,'v122',host,device_path,device_sha,out)
            with self.assertRaises(ValueError):typed.execution_context(row,h,None,'v117',host,device_path,device_sha,out)
            live.write_bytes(b'# changed\n')
            with self.assertRaisesRegex(ValueError,'live source changed'):physical.require_device_scope(row,True,context)
            live.write_bytes(b'# synthetic live source\n')
            self.done('closed_composition_live_source_and_packages_none_before_transport')
            class BeforeTransport(Exception):pass
            observed=[]
            def stop(adb):
                self.assertIsNotNone(admission._DEVICE_READ.get());self.assertEqual(profile.variant(variant,token),row)
                self.assertIsNone(remaining._ACTIVE.get())
                with self.assertRaisesRegex(ValueError,'read-only'):profile.pack(backup,variant,b'',tool,root/'forbidden.img',{},token)
                observed.append('read_scope');raise BeforeTransport()
            stack.enter_context(patch('stage_phase2.verify_packages',return_value=[]))
            stack.enter_context(patch('prepare_linux_boot.read_verified_backup',return_value=None))
            transport=stack.enter_context(patch('run_probe.preflight',side_effect=stop))
            with self.assertRaises(BeforeTransport):profile.precheck(packages,variant,backup,object(),{},ack_kernel_readonly_growth=True,type3_context=context)
            self.assertTrue((out/'PREINSTALL-CHECK-01.json').is_file());self.assertFalse((packages/'PREINSTALL-CHECK.json').exists())
            with self.assertRaises(BeforeTransport):profile._collect_into(packages,variant,object(),out,ack_kernel_readonly_growth=True,type3_context=context)
            for ack,ctx in ((False,context),(True,None),(True,dict(context,contract_sha256='e'*64))):
                with self.assertRaises(ValueError):profile._collect_into(packages,variant,object(),out,ack_kernel_readonly_growth=ack,type3_context=ctx)
            self.assertEqual(transport.call_count,2);self.assertEqual(observed,['read_scope','read_scope']);self.assertIsNone(admission._DEVICE_READ.get())
            self.done('actual_precheck_and_direct_collect_read_scope_only')
            from builtin_init_profile import current_boot_binding
            from type3_remaining_pack import HEAD,PINS,PACKAGING_HEAD,PACKAGING_PINS,FIELD
            authority=dict.fromkeys(admission.CURRENT_KEYS,h);authority.update(admission._CURRENT111_LINEAGE,packages=str(root/'current'),plan_path=str(root/'prior-plan.json'),execution_receipt_path=str(root/'prior-receipt.json'))
            prior=dict(device_profile=data.PROFILE,source_head='f20987a42249e61ef028c52099931f740d9a6cc5',host_profile_source_head=HEAD,host_profile_source_sha256=dict(PINS),backup_manifest_sha256=h,packages=[dict(mode='diagnostic',payload_sha256=h)],**{FIELD:dict(packaging_host=dict(host_profile_source_head=PACKAGING_HEAD,host_profile_source_sha256=dict(PACKAGING_PINS)))})
            plan=dict(device_profile=data.PROFILE,current_packages=authority['packages'],current_package_result_sha256=h,current_boot_payload_sha256=h)
            t=prefree._CURRENT_READ.set(authority)
            try:
                self.assertIsNone(current_boot_binding(plan,prior,prior['packages'][0]))
                with self.assertRaises(ValueError):current_boot_binding(dict(plan,current_boot_payload_sha256='b'*64),prior,prior['packages'][0])
            finally:prefree._CURRENT_READ.reset(t)
            with self.assertRaises(ValueError):current_boot_binding(plan,prior,prior['packages'][0])
            self.done('current111_predecessor_private_read_binding')
            def selected_text_only(raw,banner,identity,cycle,*,digest_decoder,digest_marker,component_evidence):
                self.assertEqual(digest_marker,b'N10DATARO3');observed=digest_decoder(raw.decode('ascii'),identity)
                return raw,dict(kat=observed,boot_identity=observed['boot_identity'])
            with patch('builtin_init_profile.decode',side_effect=selected_text_only):
                _,accepted=ro3.decode_selected(corpus().encode('ascii'),'synthetic','1'*32,token,expected=row)
                witness=accepted['component_evidence']['native_prefree_output_zero'];self.assertTrue(witness['passed']);self.assertEqual(witness['capacity'],ro3.old.PAYLOAD_BYTES)
                for text in (corpus()+"\n"+corpus().splitlines()[-1],corpus(nonzero=2,status='output_zero_observation'),corpus(reads=ro3.old.PAYLOAD_BYTES-1),corpus(free_result='not_called'),corpus(boot='4'*32)):
                    with self.assertRaises(data.ComponentObservationError):ro3.decode_selected(text.encode('ascii'),'synthetic','1'*32,token,expected=row)
                with self.assertRaises(data.ComponentObservationError) as partial:ro3.decode_selected(corpus(payload=32,written=7,status='decode').encode('ascii'),'synthetic','1'*32,token,expected=row)
                result=partial.exception.component_evidence['native_prefree_output_zero'];self.assertEqual((result['capacity'],result['reads']),(32,32));self.assertFalse(result['passed'])
            self.done('same_selected_text_prefree_counts_failures_and_partial_evidence')

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--scope',required=True,choices=(SCOPE,));parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args();OUTPUT=args.output.resolve();root=Path(__file__).resolve().parents[2]
    if not OUTPUT.is_relative_to(root/'note10/private'):raise ValueError('fresh private synthetic output required')
    OUTPUT.mkdir(parents=True,exist_ok=False)
    result=unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite([Native121Host122Tests(METHOD)]))
    save(OUTPUT/'result.json',dict(schema=RESULT_SCHEMA,scope=SCOPE,selected=[METHOD],run=result.testsRun,errors=len(result.errors),failures=len(result.failures),passed=result.wasSuccessful(),caps=CAPS,completed_sections=Native121Host122Tests.completed_sections,old_methods_run=0,fixture_compiles=0,fixture_processes=0,actual_private_inputs=0,actual_device_operations=[],CI=0,Image_builds=0,error_tracebacks=[dict(test=t.id(),traceback=v) for t,v in result.errors],failure_tracebacks=[dict(test=t.id(),traceback=v) for t,v in result.failures]))
    raise SystemExit(0 if result.wasSuccessful() else 1)
