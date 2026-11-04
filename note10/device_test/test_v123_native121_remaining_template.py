"""One NEW exact native121 receipt dispatch and saved122 remaining scope method."""
import argparse
from contextlib import ExitStack
import copy
import hashlib
import json
from pathlib import Path
import runpy
import tempfile
import unittest
from unittest.mock import patch
import class3_native_origin as origins
import kernel_readonly_span_candidate as ro3
import materialize_auto_cycle as materializer
import native_prefree_output_admission as native
import native_prefree_output_zero as producer_kind
import native_scoped_output_admission as shared
import sha256_kat_device_profile as profile
import type3_admission as typed
import type3_remaining_template as tail
METHOD='test_exact_receipt_dispatch_and_saved122_remaining_materialization_scope'
SCOPE='v123-native121-root-receipt-remaining-tail'
RESULT_SCHEMA='v123-native121-remaining-template-test-v1'
CAPS={'local_tests':1,'local_C_compiles':0,'CI':0,'new_grouped_methods':1,'new_fixture_compiles':0,'new_fixture_processes':0,'old_fixture_runs':0,'old_methods':0,'native_target_builds':0,'kernel_builds':0,'Image_builds':0,'real_decoder':0,'MachO':0,'private_payload':0,'Linux_integration':0,'target_RAM_reservation':0,'device_queries':0,'BOOT_writes':0,'reboots':0,'max_requested_PC_payload_bytes':4440064}
OUTPUT=None

def sha(raw):return hashlib.sha256(raw).hexdigest()
def save(path,value):Path(path).write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
def pin(path):return dict(path=str(path),sha256=sha(path.read_bytes()))

class RemainingTemplateTests(unittest.TestCase):
    completed_sections=[]
    def done(self,name):
        type(self).completed_sections.append(name);save(OUTPUT/'progress.json',dict(schema=RESULT_SCHEMA,completed_sections=list(type(self).completed_sections)))

    def test_exact_receipt_dispatch_and_saved122_remaining_materialization_scope(self):
        with tempfile.TemporaryDirectory(prefix='v123-new-',dir=OUTPUT) as temporary,ExitStack() as stack:
            root=Path(temporary);old=root/'failed122';template=old/'template';template.mkdir(parents=True)
            host='c'*40;h='a'*64;token='2'*32;cfg=b'# synthetic config\n'
            size=ro3.CAPACITY+4096;generic=bytearray(size);desc=ro3.CAPACITY;cycle=desc+96
            generic[desc:desc+80]=ro3.DESCRIPTOR;generic[cycle:cycle+33]=materializer.SLOT+b'\0';generic[cycle+64:cycle+71]=b'N10RET1';generic=bytes(generic)
            compact=b'X'*ro3.CAPACITY
            (template/'Image').write_bytes(generic);(template/'kernel-readonly.data').write_bytes(compact)
            for name in ('handoff.config','actual-effective.config'):(template/name).write_bytes(cfg)
            save(template/'kernel-readonly-compact.json',{'synthetic_only':True})
            item=native.record();item['image_sha256']=sha(generic);item['image_bytes']=len(generic)
            slot=dict(schema=ro3.SCHEMA,source=ro3.MODE,capacity=ro3.CAPACITY,descriptor_bytes=80,generic=True,patched=False,permanent_input_bytes=ro3.CAPACITY,permanent_descriptor_bytes=80,physical_ready=False,descriptor_class=3,boot_page=2048)
            for index,key,symbol,count,offset,preimage in ((1,'slot',ro3.SLOT,ro3.CAPACITY,0,sha(bytes(ro3.CAPACITY))),(2,'descriptor',ro3.DESC,80,desc,sha(ro3.DESCRIPTOR))):
                slot[key]=dict(symbol=symbol,section='.rodata.'+symbol,offset=offset,bytes=count,alignment=16,readonly_flags='A',preimage_sha256=preimage,object_section_index=index,object_symbol_offset=0)
            settings={k:'n' for k in ('NOTE10_KERNEL_READONLY_INPUT','NOTE10_KERNEL_READONLY_SPAN_PC','NOTE10_READONLY_INPUT_PC','NOTE10_OWNED_CONTIGUOUS_STAGING','NOTE10_CURRENT_OWNED_STAGING')}
            settings.update(NOTE10_KERNEL_READONLY_SPAN_CANDIDATE='y',NOTE10_SCOPED_OUTPUT_LEASE='y',NOTE10_PREFREE_OUTPUT_ZERO='y')
            raw=dict(version='v121',diagnostic_kind=producer_kind.KIND,data_input_kind=producer_kind.KIND,storage_input_kind=producer_kind.KIND,readonly_stage_schema='n10-readonly-stage-witness-candidate-v1',readonly_stage_marker='N10DATASTAGE1',operation_scope_PC_only=True,admission_blocked=True,scoped_output_schema='n10-scoped-verified-output-native-candidate-v1',scoped_output_marker='N10OUTPUTLEASE1',scoped_output_handle_bytes=24,scoped_output_payload_bytes=ro3.old.PAYLOAD_BYTES,scoped_output_default_enabled=False,scoped_output_reads_per_success=2,scoped_output_retained_after_emit=False,scoped_output_reference_linked_bytes=59588608,scoped_output_linked_delta_bytes=0,prefree_output_default_enabled=False,prefree_output_reference_linked_bytes=59588608,prefree_output_linked_delta_bytes=0,**native.fields(),source_sha256=item['pins'],ci_context=item['producer_ci_context'],image_sha256=item['image_sha256'],image_bytes=len(generic),kernel_readonly3_slot=slot,kernel_readonly3_span=dict(schema=ro3.old.SPAN_SCHEMA,kernel_bytes=59588608,text_prefix_bytes=0,slot_contained=True,descriptor_contained=True,disjoint=True,source='linked-kernel',phase='pre_descriptor',hardware=False,ownership=False),kernel_readonly3_marker='N10DATARO3',kernel_readonly3_schema=ro3.SCHEMA,kernel_readonly3_span_schema=ro3.old.SPAN_SCHEMA,kernel_readonly3_default_enabled=False,kernel_readonly3_requires_ack=True,passed=True,Image_built=True,BOOT_built=False,PC_only=False,PC_first_use=True,physical_ready=False,deployment_ready=False,device_authorized=False,device_operations=[],data_expectation_mode=ro3.MODE,data_expectation_slot=slot,image_expectation_patched=False,external_initrd_capture=False,input_capture_source='late-kernel-readonly-span-class3',permanent_input_storage_bytes=ro3.CAPACITY,permanent_descriptor_bytes=80,additional_linked_storage_bytes=ro3.CAPACITY+80,class2_PC_storage_absent=True,kernel_readonly3_linked_bytes=59588608,kernel_readonly3_image_bytes=len(generic),data_footprint=dict(linked_kernel_bytes=59588608,data_state_bytes=88),settings=settings,kernel_or_provider_executed=False,files_sha256={'actual-effective.config':sha(cfg)},build_evidence_id='1'*32)
            raw['kernel_readonly3_candidate_contract']=ro3.producer_contract(raw,item['head'],producing_sources=item['pins'])
            save(template/'result.json',raw);item['result']=sha((template/'result.json').read_bytes())
            stack.enter_context(patch.object(native,'_NATIVE121',native._freeze(item))) # isolated closed synthetic origin, no production override API
            current=dict.fromkeys(shared.CURRENT_KEYS,h);current.update(shared._CURRENT111_LINEAGE,packages=str(root/'prior-packages'),plan_path=str(root/'prior-plan.json'),execution_receipt_path=str(root/'prior-receipt.json'))
            context=dict(schema='note10-root-native121-ci-success-context-v1',native_version='v121',native_source_head=item['head'],accepted_result_sha256=item['result'],source_sha256=item['pins'],source_manifest_sha256=item['source_manifest_sha256'],producer_ci_context=item['producer_ci_context'],generic_image_sha256=item['image_sha256'],Image_bytes=len(generic),candidate_contract=raw['kernel_readonly3_candidate_contract'],new_grouped_method=dict(source_head=item['head'],result_sha256=item['test_result_sha256'],selected=['test_actual_native_prefree_output_scan_and_cleanup'],run=1,errors=0,failures=0,fixture_compiles=1,fixture_processes=1),new_fixture=copy.deepcopy(native.FIXTURE_EVIDENCE),artifact={k:item[k] for k in ('run_id','attempt','job_id','workflow_id','artifact_id','plaintext_zip_sha256')},current_predecessor=current)
            save(template/'ci-success-context.json',context);context_sha=sha((template/'ci-success-context.json').read_bytes())
            original=dict(schema=typed.OFFLINE_SCHEMA,status='reviewed_ready',host_source_head=tail.HEAD,execution_version='v122',native_source_head=item['head'],accepted_result_sha256=item['result'],output=str(old),ci_success_context=str(template/'ci-success-context.json'),ci_success_context_sha256=context_sha,compact_manifest_sha256=sha((template/'kernel-readonly-compact.json').read_bytes()),producer_root=str(root/'generic'),compact_manifest=str(template/'kernel-readonly-compact.json'),backup=str(root/'backup'),backup_manifest_sha256=h,current_packages=current['packages'],current_package_result_sha256=h,current_boot_sha256=h,reference_twrp=str(root/'reference.img'),mkbootimg=str(Path(typed.__file__).resolve().parents[2]/'research/twrp-d2x-reference/aosp-mkbootimg.py'),caps=typed.OFFLINE_CAPS)
            save(root/'original-contract.json',original);(template/'type3-contract.json').write_bytes((root/'original-contract.json').read_bytes());original_sha=sha((root/'original-contract.json').read_bytes())
            binding=dict(device_profile=profile.DATA_PROFILE,diagnostic_kind=producer_kind.KIND,source_head=item['head'],native_source_head=item['head'],accepted_result_sha256=item['result'],host_profile_source_head=tail.HEAD,host_profile_source_sha256=dict(tail.PINS),version='v122',execution_version='v122',image_sha256=item['image_sha256'],image_size=len(generic),effective_config_sha256=sha(cfg),build_evidence_id='1'*32,kernel_banner=origins.banner({'diagnostic_kind':producer_kind.KIND})+'synthetic',type3_contract_path=str(root/'original-contract.json'),type3_contract_sha256=original_sha,type3_generic_image_sha256=item['image_sha256'],type3_compact_sha256=sha(compact),kernel_readonly3_image_bytes=len(generic),kernel_readonly3_slot=slot,data_expectation_mode=ro3.MODE,image_expectation_patched=False)
            binding.update(shared.stage_fields(item['head']))
            receipt=profile.ci_success_receipt(context,context_sha,binding,raw);save(template/'image-root-receipt.json',receipt)
            receipt_sha=sha((template/'image-root-receipt.json').read_bytes());binding.update(image_root_receipt_sha256=receipt_sha,root_reader_result_sha256=context_sha)
            save(template/'device-profile.json',binding);report=profile.common_report(binding,sha((template/'device-profile.json').read_bytes()));save(template/'build-result.json',report)
            self.assertEqual(profile.root_receipt_binding(template,template/'image-root-receipt.json',receipt_sha,binding),dict(image_root_receipt_sha256=receipt_sha,root_reader_result_sha256=context_sha))
            for change in ({'unexpected':True},{'producer_source_head':'e'*40},{'native_producer_provenance':dict(receipt['native_producer_provenance'],physical_ready=True)}):
                bad=dict(receipt,**change);save(root/'bad-receipt.json',bad)
                with self.assertRaises(ValueError):profile.root_receipt_binding(template,root/'bad-receipt.json',sha((root/'bad-receipt.json').read_bytes()),binding)
            badroot=root/'wrong-map';badroot.mkdir();(badroot/'ci-success-context.json').write_bytes((template/'ci-success-context.json').read_bytes());badraw=copy.deepcopy(raw);badraw['source_sha256']['wrong.py']=h;save(badroot/'result.json',badraw)
            with self.assertRaises(ValueError):profile.root_receipt_binding(badroot,template/'image-root-receipt.json',receipt_sha,binding)
            self.done('actual_native121_receipt_dispatch_and_closed_refusals')
            failed=dict(schema='type3-offline-journal-v1',status='failed_no_restart',phase='template_reserved',contract_sha256=original_sha,attempts=dict(templates=1,materializations=0,plans=0),IO_events=[{'operation':'attach_existing_compact_once'},{'operation':'intrinsic_compact_copy_validation'}]);save(old/'transaction.json',failed)
            failure=dict(schema='v122-offline-operator-receipt-v1',native_source_head=item['head'],transaction_path=str(old/'transaction.json'),output=str(old),success=False,source_head=tail.HEAD,invocation_attempts=1,invocation_exit_code=1,contract_sha256=original_sha,transaction_sha256=sha((old/'transaction.json').read_bytes()));save(root/'operator.json',failure)
            (root/'trace.txt').write_text('root_receipt_binding: closed accepted Image-root receipt required\n',encoding='utf-8')
            failure['stderr_sha256']=sha((root/'trace.txt').read_bytes());save(root/'operator.json',failure)
            host_binding=dict(host_profile_source_head=host,host_profile_source_sha256={'synthetic/live.py':h})
            stack.enter_context(patch.object(profile,'host_binding',side_effect=lambda head:host_binding if head==host else (_ for _ in ()).throw(ValueError('closed synthetic live source'))))
            contract=dict(schema=tail.SCHEMA,status='reviewed_ready',execution_version='v123',execution_host_source_head=host,execution_host_source_sha256=host_binding['host_profile_source_sha256'],original_contract=pin(root/'original-contract.json'),failed_transaction=pin(old/'transaction.json'),operator_failure=pin(root/'operator.json'),trace=pin(root/'trace.txt'),template_root=str(template),template_files={n:sha((template/n).read_bytes()) for n in tail.FILES},output=str(root/'new123'),caps=tail.CAPS)
            save(root/'remaining.json',contract);contract_sha=sha((root/'remaining.json').read_bytes())
            before={n:sha((template/n).read_bytes()) for n in (*tail.FILES,'Image','kernel-readonly.data')};old_journal=sha((old/'transaction.json').read_bytes())
            real_bounded=tail.data.bounded_private_read;real_read_bytes=Path.read_bytes;binary_reads=[]
            def metadata_only_read(path,*args,**kwargs):
                if Path(path).name in tail.BINARY_FILES:
                    binary_reads.append(str(path));raise AssertionError('loader must not read saved Image/DATA')
                return real_bounded(path,*args,**kwargs)
            def metadata_only_bytes(path):
                if Path(path).name in tail.BINARY_FILES:
                    binary_reads.append(str(path));raise AssertionError('metadata tail must not read saved Image/DATA')
                return real_read_bytes(path)
            with patch.object(tail.data,'bounded_private_read',side_effect=metadata_only_read),patch.object(Path,'read_bytes',metadata_only_bytes):
                ctx=tail._start(root/'remaining.json',contract_sha)
            active=tail._ACTIVE.set(ctx)
            try:
                with patch.object(tail.data,'bounded_private_read',side_effect=metadata_only_read),patch.object(Path,'read_bytes',metadata_only_bytes):
                    tail._ready(ctx);view=profile.validate_template(template)
                self.assertEqual(binary_reads,[])
                self.assertEqual(view['version'],'v123');self.assertEqual(view[tail.FIELD]['composing_host']['host_profile_source_head'],tail.HEAD)
                self.assertEqual(typed.candidate_scope(view,patched=False)['host_source_head'],host)
                self.done('remaining_metadata_tail_and_readonly122_live123_separation')
                plan_dir=ctx['output']/'plan';typed.require_plan_transaction(view,plan_dir);plan_dir.mkdir();(plan_dir/'cycle-01').mkdir();variant=plan_dir/'cycle-01/kernel-build'
                with patch.object(typed,'read_compact',return_value=(compact,{})):
                    bound=materializer.materialize(template,variant,token)
                    self.assertEqual(bound['host_profile_source_head'],host);self.assertEqual(bound['version'],'v123')
                    self.assertEqual(bound[tail.FIELD]['composing_host']['host_profile_source_sha256'],dict(tail.PINS))
                    self.assertEqual(materializer.validate(variant,token,template),bound)
                    self.assertEqual(tail.candidate(dict(bound,mode='rollback',auto_return_diagnostic=False,auto_cycle_token=None),True)['execution_version'],'v123')
                    with patch('prepare_linux_boot.pack_verified',return_value={'synthetic_only':True}) as packer:
                        self.assertEqual(profile.pack(root/'backup',variant,b'',root/'tool.py',plan_dir/'cycle-01/boot.img',{},token),{'synthetic_only':True});self.assertEqual(packer.call_count,1)
                        with self.assertRaises(ValueError):profile.pack(root/'backup',variant,b'',root/'tool.py',plan_dir/'cycle-01/boot.img',{},token)
                save(plan_dir/'plan.json',{tail.FIELD:tail.marker(ctx),'execution_version':'v123'})
                tail._finish(ctx,dict(plan=str(plan_dir/'plan.json'),plan_sha256=sha((plan_dir/'plan.json').read_bytes())))
                self.assertEqual(tail.read(ctx['output']/'transaction.json')['counts'],dict(template_tail=1,materializations=1,variant_validations=1,packs=1,plans=1))
                with self.assertRaises(ValueError):tail._start(root/'remaining.json',contract_sha)
                self.done('actual_new_materialization_validation_and_one_packer_gate')
                called=[]
                with patch.object(tail,'main',side_effect=lambda:called.append(tail._ACTIVE.get() is ctx)):
                    runpy.run_path(str(Path(tail.__file__)),run_name='__main__')
                self.assertEqual(called,[True]);self.assertEqual({n:sha((template/n).read_bytes()) for n in before},before);self.assertEqual(sha((old/'transaction.json').read_bytes()),old_journal)
            finally:tail._ACTIVE.reset(active)
            with self.assertRaises(ValueError):typed.candidate_scope(report,patched=False)
            self.assertIsNone(tail._ACTIVE.get())
            read_token=tail._READ.set(ctx)
            try:
                with self.assertRaisesRegex(ValueError,'read-only'):tail.require_pack(variant,root/'forbidden.img',token)
            finally:tail._READ.reset(read_token)
            self.done('canonical_cli_shared_context_and_saved_bytes_immutable')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--scope',required=True,choices=(SCOPE,));p.add_argument('--output',required=True,type=Path);a=p.parse_args();OUTPUT=a.output.resolve();root=Path(__file__).resolve().parents[2]
    if not OUTPUT.is_relative_to(root/'note10/private'):raise ValueError('fresh private synthetic output required')
    OUTPUT.mkdir(parents=True,exist_ok=False);result=unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite([RemainingTemplateTests(METHOD)]))
    save(OUTPUT/'result.json',dict(schema=RESULT_SCHEMA,scope=SCOPE,selected=[METHOD],run=result.testsRun,errors=len(result.errors),failures=len(result.failures),passed=result.wasSuccessful(),completed_sections=RemainingTemplateTests.completed_sections,caps=CAPS,old_methods_run=0,fixture_compiles=0,fixture_processes=0,actual_private_inputs=0,actual_device_operations=[],Image_builds=0,error_tracebacks=[dict(test=t.id(),traceback=v) for t,v in result.errors],failure_tracebacks=[dict(test=t.id(),traceback=v) for t,v in result.failures]))
    raise SystemExit(0 if result.wasSuccessful() else 1)
