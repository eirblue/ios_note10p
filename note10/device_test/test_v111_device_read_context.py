"""One NEW synthetic v111 device-read-context method; no actual input or transport."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import builtin_init_profile as builtin
import class3_native_origin as origins
import kernel_readonly_input as old
import kernel_readonly_span_candidate as ro3
import linux_data_carrier as data
import readonly_stage_witness as stages
import sha256_kat_device_profile as profile
import type3_admission as typed
import type3_remaining_pack as remaining

METHOD='test_valid_device_context_reaches_precheck_saved_metadata_before_transport'
SCOPE='v111-remaining-device-read-context'
OUTPUT=None


def digest(raw):return hashlib.sha256(raw).hexdigest()
def save(path,row):Path(path).write_text(json.dumps(row,sort_keys=True,indent=2)+'\n')


class DeviceReadContextTests(unittest.TestCase):
    def test_valid_device_context_reaches_precheck_saved_metadata_before_transport(self):
        work=OUTPUT/'synthetic';work.mkdir();template=work/'template';variant=work/'variant';backup=work/'backup'
        packed=work/'completed-pack';packages=packed/'cycle-01/packages';execution_output=work/'new-v111-execution'
        for folder in (template,variant,backup,packages,execution_output):folder.mkdir(parents=True)
        native=origins.record(remaining.NATIVE);live_head='8'*40;token='6'*32
        live=dict(host_profile_source_head=live_head,host_profile_source_sha256={'synthetic/execution.py':'8'*64})
        packing=remaining.packing_origin(remaining.PACKAGING_HEAD)
        self.assertEqual(len(packing['host_profile_source_sha256']),78)
        with self.assertRaises(ValueError):origins.live_host(remaining.PACKAGING_HEAD)
        config=b'CONFIG_SYNTHETIC_METADATA_ONLY=y\n';(variant/'handoff.config').write_bytes(config)
        slot=dict(schema=ro3.SCHEMA,source=ro3.MODE,capacity=ro3.CAPACITY,descriptor_bytes=80,generic=True,patched=False,
            permanent_input_bytes=ro3.CAPACITY,permanent_descriptor_bytes=80,physical_ready=False,descriptor_class=3,boot_page=2048)
        for index,key,symbol,section,size,preimage,offset in (
            (1,'slot',ro3.SLOT,'.rodata.n10_kernel_readonly3_input',ro3.CAPACITY,digest(bytes(ro3.CAPACITY)),4096),
            (2,'descriptor',ro3.DESC,'.rodata.n10_kernel_readonly3_descriptor',80,digest(ro3.DESCRIPTOR),4096+ro3.CAPACITY)):
            slot[key]=dict(symbol=symbol,section=section,offset=offset,bytes=size,alignment=16,readonly_flags='A',
                preimage_sha256=preimage,object_section_index=index,object_symbol_offset=0)
        span=dict(schema=old.SPAN_SCHEMA,kernel_bytes=native['linked_bytes']-2048,text_prefix_bytes=2048,slot_contained=True,
            descriptor_contained=True,disjoint=True,source='linked-kernel',phase='pre_descriptor',hardware=False,ownership=False)
        old_contract_path=work/'original-contract.json';old_contract_sha='e'*64
        old_contract=dict(execution_version='v110',host_source_head=remaining.HEAD,compact_manifest_sha256='b'*64)
        binding=dict(device_profile=data.PROFILE,diagnostic_kind=stages.KIND,data_input_kind=stages.KIND,storage_input_kind=stages.KIND,
            **origins.stage_fields(),kernel_readonly3_schema=ro3.SCHEMA,kernel_readonly3_slot=slot,kernel_readonly3_span_schema=old.SPAN_SCHEMA,
            kernel_readonly3_span=span,kernel_readonly3_linked_bytes=native['linked_bytes'],kernel_readonly3_image_bytes=native['image_bytes'],
            kernel_readonly3_requires_ack=True,kernel_readonly3_marker='N10DATARO3',data_carrier_stage=data.STAGE,
            data_relative_placement_admitted=False,raw_input_binding=False,data_expectation_mode=ro3.MODE,data_expectation_slot=slot,
            image_expectation_patched=True,accepted_result_sha256=native['result'],source_head=native['head'],native_source_head=native['head'],
            version='v110',execution_version='v110',native_producer_version='v109',native_producer_PC_first_use=True,
            type3_native_origin=origins.origin(native['head']),host_profile_source_head=remaining.HEAD,host_profile_source_sha256=dict(remaining.PINS),
            image_sha256='f'*64,image_size=native['image_bytes'],type3_generic_image_sha256='a'*64,
            type3_contract_path=str(old_contract_path),type3_contract_sha256=old_contract_sha,type3_external_choice='compact-v1',
            type3_compact_sha256='c'*64,type3_compact_bytes=ro3.CAPACITY,type3_compact_manifest_sha256='b'*64,
            data_carrier_bytes=old.OLD_BYTES,data_payload_bytes=old.PAYLOAD_BYTES,data_manifest_sha256='b'*64,data_carrier_sha256='c'*64,
            data_payload_sha256='d'*64,effective_config_sha256=digest(config),build_evidence_id='1'*32,kernel_banner=origins.banner(dict(data_input_kind=stages.KIND))+'synthetic',
            image_root_receipt_sha256='a'*64,root_reader_result_sha256='b'*64,**{key:'a'*64 for key in builtin.EXTRA_FIELDS})
        bound=profile.common_report(binding,'a'*64)
        bound.update(auto_cycle_variant=True,auto_cycle_token=token,auto_cycle_template=str(template),
            auto_cycle_template_report_sha256='a'*64,auto_cycle_template_image_sha256='a'*64)
        bound['type3_materialization']=typed.materialization(bound,token,'a'*64,'f'*64,'a'*64)
        save(variant/'build-result.json',bound)
        remaining_path=work/'remaining-contract.json';remaining_sha='9'*64
        lineage=dict(schema=remaining.SCHEMA,contract_path=str(remaining_path),contract_sha256=remaining_sha,packaging_host=packing)
        contract=dict(output=str(packed),packaging_host_source_head=remaining.PACKAGING_HEAD,native_source_head=native['head'],
            variant_report_sha256=profile.sha(variant/'build-result.json'),variant_config_sha256=digest(config),bound_image_sha256='f'*64,
            original_contract_sha256=old_contract_sha,cycle=token)
        retained_context=dict(contract=contract,old=old_contract,template=template,variant=variant,generic={},report=bound,host=packing,binding=lineage)
        pair=dict(bound,**{remaining.FIELD:lineage},kernel_image_sha256=bound['image_sha256'],backup_manifest_sha256='0'*64)
        save(backup/'backup-manifest.json',dict(synthetic=True));pair['backup_manifest_sha256']=profile.sha(backup/'backup-manifest.json')
        save(packages/'package-result.json',pair);package_sha=profile.sha(packages/'package-result.json')
        stage=dict(kernel_build=str(variant),build_result_sha256=contract['variant_report_sha256'],image_sha256=bound['image_sha256'],
            cycle=token,packages=str(packages),package_result_sha256=package_sha)
        plan=dict(execution_version='v110',stages=[stage],**{remaining.FIELD:lineage});save(packed/'plan.json',plan);plan_sha=profile.sha(packed/'plan.json')
        save(packed/'transaction.json',dict(schema='type3-remaining-pack-journal-v1',status='complete',phase='complete',contract_sha256=remaining_sha,
            attempts=dict(BOOT_packings=1,package_pair_builds=1,plans=1,intrinsic_variant_data_consumptions=1,intrinsic_packer_compact_validations=1),
            device_operations=[],result=dict(plan_sha256=plan_sha)))
        device=dict(schema=remaining.DEVICE2_SCHEMA,status='reviewed_ready',execution_version='v111',producer_host_source_head=remaining.HEAD,
            packaging_host_source_head=remaining.PACKAGING_HEAD,execution_host_source_head=live_head,execution_host_source_sha256=live['host_profile_source_sha256'],
            native_source_head=native['head'],plan_sha256=plan_sha,packages=str(packages),package_result_sha256=package_sha,
            bound_image_sha256=bound['image_sha256'],offline_contract_sha256=old_contract_sha,remaining_contract_sha256=remaining_sha,
            output=str(execution_output),minimum_battery=10,BOOT_write_max=1,reboot_max=1,
            user_availability_record_sha256='4a639d278836af88256a339d199b9fbe53ad65d354db4b8c4401796522e758e9')
        device_path=work/'device-v2.json';save(device_path,device)
        old_receipt=packages/'PREINSTALL-CHECK.json';old_receipt.write_bytes(b'preserved spent v110 evidence\n');old_raw=old_receipt.read_bytes()
        def load_retained(path,pin):
            self.assertEqual((Path(path),pin),(remaining_path,remaining_sha));return retained_context
        def load_original(path,pin):
            self.assertEqual((Path(path),pin),(old_contract_path,old_contract_sha));return old_contract
        def live_origin(head):
            self.assertEqual(head,live_head);return copy.deepcopy(live)
        class TransportBoundary(Exception):pass
        actual_saved_metadata=remaining.saved_metadata;seen=[]
        def saved_metadata(*args,**kwargs):
            result=actual_saved_metadata(*args,**kwargs);seen.append(Path(args[0]));return result
        def transport(adb):
            self.assertIsNone(remaining._ACTIVE.get());self.assertIs(remaining._DEVICE_READ.get(),retained_context)
            self.assertIn(variant,seen)
            with self.assertRaises(ValueError):remaining.require_pack(variant,work/'forbidden-boot.img',token)
            raise TransportBoundary('mocked before any transport')
        # The two prior metadata loaders are isolated I/O fixtures; new execution/read/precheck guards run unchanged.
        with patch('type3_remaining_pack.load',side_effect=load_retained),patch('type3_admission.load_offline',side_effect=load_original),\
             patch('sha256_kat_device_profile.host_binding',side_effect=live_origin),\
             patch('stage_phase2.verify_packages',return_value=[dict(mode='diagnostic',file='synthetic.zip')]),\
             patch('prepare_linux_boot.read_verified_backup',return_value={}),\
             patch('run_probe.preflight',side_effect=transport) as transport_io,\
             patch('type3_remaining_pack.saved_metadata',side_effect=saved_metadata):
            def execution():return typed.execution_context(pair,plan_sha,packages,'v111',live_head,device_path,profile.sha(device_path),execution_output)
            context=execution();self.assertEqual(context['schema'],remaining.CONTEXT2_SCHEMA)
            self.assertEqual(context['host_source_sha256'],live['host_profile_source_sha256'])
            for ctx,ack,kernel,receipt in ((None,True,variant,None),(context,False,variant,None),
                (dict(context,host_source_sha256={'wrong.py':'0'*64}),True,variant,None),
                (context,True,work/'wrong-variant',None),(context,True,variant,old_receipt)):
                with self.subTest(denial=(ctx is None,ack,str(kernel),str(receipt))),self.assertRaises(ValueError):
                    profile.precheck(packages,kernel,backup,object(),{},ack_kernel_readonly_growth=ack,type3_context=ctx,receipt_path=receipt)
            self.assertEqual(transport_io.call_count,0)
            with self.assertRaises(ValueError):profile._collect_into(packages,variant,object(),work/'unused-capture',ack_kernel_readonly_growth=True)
            self.assertEqual(transport_io.call_count,0)
            # Exercise the direct collector's actual decorator, with its unchanged first I/O isolated.
            class CollectionBoundary(Exception):pass
            def collection_io(actual_packages):
                self.assertEqual(Path(actual_packages),packages)
                self.assertIsNone(remaining._ACTIVE.get());self.assertIs(remaining._DEVICE_READ.get(),retained_context)
                self.assertEqual(remaining.saved_metadata(variant,token,template),bound)
                with self.assertRaises(ValueError):remaining.require_pack(variant,work/'forbidden-collect-pack.img',token)
                raise CollectionBoundary('mocked collector I/O before logs or transport')
            with patch('stage_phase2.verify_packages',side_effect=collection_io) as collection_boundary:
                with self.assertRaises(CollectionBoundary):
                    profile._collect_into(packages,variant,object(),work/'unused-capture',ack_kernel_readonly_growth=True,type3_context=context)
                self.assertEqual(collection_boundary.call_count,1)
                wrong_collection=dict(context,host_source_sha256={'wrong.py':'0'*64})
                with self.assertRaises(ValueError):
                    profile._collect_into(packages,variant,object(),work/'unused-capture',ack_kernel_readonly_growth=True,type3_context=wrong_collection)
                self.assertEqual(collection_boundary.call_count,1)
            self.assertIsNone(remaining._DEVICE_READ.get());self.assertIsNone(remaining._ACTIVE.get())
            self.assertFalse((work/'unused-capture').exists());self.assertEqual(transport_io.call_count,0)
            with self.assertRaises(TransportBoundary):profile.precheck(packages,variant,backup,object(),{},ack_kernel_readonly_growth=True,type3_context=context)
            self.assertEqual(transport_io.call_count,1);self.assertIn(variant,seen)
            self.assertTrue((execution_output/'PREINSTALL-CHECK-01.json').is_file())
            with self.assertRaises(ValueError):profile.precheck(packages,variant,backup,object(),{},ack_kernel_readonly_growth=True,type3_context=context)
            self.assertEqual(transport_io.call_count,1);self.assertEqual(old_receipt.read_bytes(),old_raw)
            for key,value in (('schema',remaining.DEVICE_SCHEMA),('execution_host_source_head',remaining.PACKAGING_HEAD),
                ('packaging_host_source_head',live_head),('execution_host_source_sha256',{'wrong.py':'0'*64}),('execution_version','v110')):
                wrong=copy.deepcopy(device);wrong[key]=value;save(device_path,wrong)
                with self.subTest(contract=key),self.assertRaises(ValueError):execution()
            self.assertEqual(transport_io.call_count,1)
        self.assertIsNone(remaining._ACTIVE.get());self.assertIsNone(remaining._DEVICE_READ.get())
        self.assertFalse((variant/'Image').exists());self.assertFalse((variant/'kernel-readonly.data').exists())
        save(OUTPUT/'summary.json',dict(actual_execution_context_precheck_variant_route=True,saved_metadata_reached=True,
            actual_direct_collector_decorator_route=True,collector_saved_metadata_read=True,wrong_explicit_collector_context_refused=True,
            mocked_collector_IO_boundary_calls=1,actual_logs_or_decoder_calls=0,
            separate_read_scope_cannot_pack=True,wrong_scope_and_ACK_refused_before_transport=True,fresh_execution_receipt=True,
            spent_v110_package_receipt_preserved=True,actual_inputs=0,actual_transport_calls=0,mocked_transport_boundary_calls=1,
            fixture_compiles=0,fixture_processes=0,Image_builds=0,CI=0,old_methods_run=0))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--scope',required=True,choices=(SCOPE,));parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();OUTPUT=profile.private(args.output);OUTPUT.mkdir(parents=True,exist_ok=False)
    names=('type3_remaining_pack.py','type3_admission.py','class3_native_origin.py','sha256_kat_device_profile.py','auto_cycle.py','test_v111_device_read_context.py')
    save(OUTPUT/'source-sha256.json',{name:profile.sha(Path(__file__).resolve().parent/name) for name in names})
    result=unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite([DeviceReadContextTests(METHOD)]))
    save(OUTPUT/'result.json',dict(schema='v111-device-read-context-regression-v1',scope=args.scope,selected=[METHOD],run=result.testsRun,
        errors=len(result.errors),failures=len(result.failures),passed=result.wasSuccessful(),fixture_compiles=0,fixture_processes=0,Image_builds=0,CI=0,
        actual_private_inputs=0,actual_device_operations=[],old_methods_run=0,error_tracebacks=[dict(test=test.id(),traceback=trace) for test,trace in result.errors],
        failure_tracebacks=[dict(test=test.id(),traceback=trace) for test,trace in result.failures]))
    raise SystemExit(0 if result.wasSuccessful() else 1)
