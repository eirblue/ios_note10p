"""One grouped NEW host108 synthetic transaction/call-chain regression; no hardware."""
import argparse
from contextlib import ExitStack
import copy
import hashlib
import json
from pathlib import Path
import struct
import unittest
from unittest.mock import patch

import auto_cycle
import kernel_readonly_input as old
import kernel_readonly_span_candidate as ro3
import materialize_auto_cycle as materializer
import prepare_linux_boot as packer
import sha256_kat_device_profile as profile
import stage_phase2
import type3_admission as typed

OUTPUT=None
METHOD='test_typed_native107_host108_transaction_patch_plan_and_pretransport_scope'


def digest(raw):return hashlib.sha256(raw).hexdigest()
def save(path,row):Path(path).write_text(json.dumps(row,sort_keys=True,indent=2)+'\n')


class Type3AdmissionTests(unittest.TestCase):
    def test_typed_native107_host108_transaction_patch_plan_and_pretransport_scope(self):
        work=OUTPUT/'synthetic';work.mkdir();source=work/'producer';source.mkdir();backup=work/'backup';backup.mkdir()
        prior=work/'current';prior.mkdir();derived=work/'retained-compact';derived.mkdir()
        config=b'CONFIG_SYNTHETIC_ONLY=y\n';(source/'prerequisites/objects').mkdir(parents=True)
        (source/'prerequisites/objects/.config').write_bytes(config)
        identity='1'*32;token_slot=materializer.SLOT
        slot_offset=8192;descriptor=slot_offset+ro3.CAPACITY;image_size=descriptor+80+4096
        generic=bytearray(image_size);generic[56:60]=b'ARM\x64';generic[1024:1057]=token_slot+b'\0'
        generic[512:519]=b'N10RET1';generic[descriptor:descriptor+80]=ro3.DESCRIPTOR
        (source/'Image').write_bytes(generic)
        def extent(symbol,section,offset,size,preimage,index):
            return dict(symbol=symbol,section=section,offset=offset,bytes=size,alignment=16,readonly_flags='A',
                preimage_sha256=preimage,object_section_index=index,object_symbol_offset=0)
        record=dict(schema=ro3.SCHEMA,source=ro3.MODE,capacity=ro3.CAPACITY,descriptor_bytes=80,
            slot=extent(ro3.SLOT,'.rodata.n10_kernel_readonly3_input',slot_offset,ro3.CAPACITY,digest(bytes(ro3.CAPACITY)),7),
            descriptor=extent(ro3.DESC,'.rodata.n10_kernel_readonly3_descriptor',descriptor,80,digest(ro3.DESCRIPTOR),8),
            generic=True,patched=False,permanent_input_bytes=ro3.CAPACITY,permanent_descriptor_bytes=80,physical_ready=False,descriptor_class=3,boot_page=2048)
        linked=image_size+4096
        span=dict(schema=old.SPAN_SCHEMA,kernel_bytes=linked-4096,text_prefix_bytes=4096,slot_contained=True,
            descriptor_contained=True,disjoint=True,source='linked-kernel',phase='pre_descriptor',hardware=False,ownership=False)
        base=dict(device_profile=profile.DATA_PROFILE,data_carrier_stage=__import__('linux_data_carrier').STAGE,
            data_relative_placement_admitted=False,raw_input_binding=False,diagnostic_kind=ro3.KIND,data_input_kind=ro3.KIND,storage_input_kind=ro3.KIND,
            data_expectation_mode=ro3.MODE,data_expectation_slot=record,image_expectation_patched=False,
            kernel_readonly3_schema=ro3.SCHEMA,kernel_readonly3_slot=record,kernel_readonly3_span_schema=old.SPAN_SCHEMA,kernel_readonly3_span=span,
            kernel_readonly3_linked_bytes=linked,kernel_readonly3_image_bytes=image_size,kernel_readonly3_requires_ack=True,kernel_readonly3_marker='N10DATARO3',
            accepted_result_sha256=ro3.NATIVE_RESULT_SHA256,source_head=ro3.NATIVE_HEAD,image_sha256=digest(generic),image_size=image_size,
            effective_config_sha256=digest(config),build_evidence_id=identity,kernel_banner='Linux version 4.14.113-v107-readonly-span-candidate synthetic')
        for name in __import__('builtin_init_profile').EXTRA_FIELDS:base[name]='9'*64
        native=dict(version='v107',diagnostic_kind=ro3.KIND,passed=True,Image_built=True,image_sha256=digest(generic),image_bytes=image_size,
            build_evidence_id=identity,files_sha256={'actual-effective.config':digest(config)},source_sha256=dict(ro3.NATIVE_SOURCE59),
            ci_context=dict(GITHUB_SHA=ro3.NATIVE_HEAD,GITHUB_RUN_ID='123',GITHUB_RUN_ATTEMPT='1',GITHUB_JOB='linux-data-carrier'))
        save(source/'result.json',native)
        compact=bytearray(ro3.CAPACITY);compact[:8]=b'N10DATA1'
        struct.pack_into('<HHIQQQQ',compact,8,1,128,0,ro3.CAPACITY,128,old.STREAM_BYTES,old.PAYLOAD_BYTES)
        compact[128]=0x5d;struct.pack_into('<IQ',compact,129,1<<23,old.PAYLOAD_BYTES)
        compact[48:80]=hashlib.sha256(compact[128:128+old.STREAM_BYTES]).digest();compact[80:112]=bytes.fromhex('99'*32)
        manifest=dict(schema=old.COMPACT_SCHEMA,source_manifest_sha256='b'*64,source_carrier_sha256='a'*64,source_carrier_bytes=old.OLD_BYTES,
            compact_sha256=digest(compact),compact_bytes=ro3.CAPACITY,stream_bytes=old.STREAM_BYTES,stream_sha256=compact[48:80].hex(),
            payload_bytes=old.PAYLOAD_BYTES,payload_sha256='99'*32,header_bytes=128,zero_padding_bytes=2733,decoder_calls=0,recompressions=0,device_operations=[],physical_ready=False)
        (derived/'kernel-readonly.data').write_bytes(compact);save(derived/'compact-manifest.json',manifest)
        context=dict(schema=1,kind=profile.DATA_PROFILE+'-ci-success-context',accepted=True,producer_source_head=ro3.NATIVE_HEAD,
            ci_result_sha256=ro3.NATIVE_RESULT_SHA256,image_sha256=digest(generic),image_bytes=image_size,effective_config_sha256=digest(config),
            build_evidence_id=identity,run_id=123,attempt=1,workflow_id=2,job_id=3,artifact_id=4,artifact_zip_sha256='c'*64,artifact_zip_bytes=100)
        save(work/'ci-context.json',context)
        full_size=5*1024*1024;oldboot=b'BASE'+bytes(full_size-4);official=b'OFFI'+bytes(252+old.OLD_BYTES)
        twrp=work/'reference';twrp.write_bytes(official);mkboot=work/'mkbootimg';mkboot.write_bytes(b'synthetic')
        save(backup/'backup-manifest.json',dict(bootloader='synthetic',partitions={}))
        prior_pair=dict(source_head=profile.V104_PROFILE_ORIGIN_HEAD,host_profile_source_head=profile.V104_PROFILE_ORIGIN_HEAD,
            device_profile=profile.DATA_PROFILE,data_compare_schema='n10-data-compare-v2',data_input_range_schema='n10-data-range-v1',
            data_early_prefix_schema='n10-data-early-prefix-v1',data_growth_schema='n10-data-growth-v1',
            data_growth_target_source='e32ec501551b74b4cca5618ea25245f012656f29',data_growth_target_bytes=59523072,
            data_growth_budget_bytes=59768832,data_linked_kernel_bytes=55132160,backup_manifest_sha256=digest((backup/'backup-manifest.json').read_bytes()),
            packages=[dict(mode='diagnostic',payload_sha256=digest(oldboot),payload_size=full_size)])
        save(prior/'package-result.json',prior_pair)
        contract=dict(schema=typed.OFFLINE_SCHEMA,status='reviewed_ready',execution_version='v108',host_source_head='8'*40,
            native_source_head=ro3.NATIVE_HEAD,accepted_result_sha256=ro3.NATIVE_RESULT_SHA256,producer_root=str(source.resolve()),
            ci_success_context=str((work/'ci-context.json').resolve()),ci_success_context_sha256=digest((work/'ci-context.json').read_bytes()),
            compact_manifest=str((derived/'compact-manifest.json').resolve()),compact_manifest_sha256=digest((derived/'compact-manifest.json').read_bytes()),
            backup=str(backup.resolve()),backup_manifest_sha256=digest((backup/'backup-manifest.json').read_bytes()),current_packages=str(prior.resolve()),
            current_package_result_sha256=digest((prior/'package-result.json').read_bytes()),current_boot_sha256=digest(oldboot),
            reference_twrp=str(twrp.resolve()),mkbootimg=str(mkboot.resolve()),output=str((work/'transaction').resolve()),caps=dict(typed.OFFLINE_CAPS))
        contract_path=work/'offline.json';save(contract_path,contract);contract_sha=digest(contract_path.read_bytes())
        counts=dict(materializations=0,BOOTs=0,packages=0,intrinsic_plans=0,patches=0,patch_attempts=0)
        boot_payloads={};actual_patch=typed.patch_image;actual_materialize=materializer.materialize;actual_validate_plan=profile.validate_plan
        def raw_binding(root,expected,head,**kwargs):
            self.assertEqual((expected,head,kwargs.get('readonly_origin')),(ro3.NATIVE_RESULT_SHA256,ro3.NATIVE_HEAD,ro3.NATIVE_HEAD))
            return copy.deepcopy(base)
        def patched(*args,**kwargs):
            counts['patch_attempts']+=1;result=actual_patch(*args,**kwargs);counts['patches']+=1;return result
        def materialized(*args,**kwargs):counts['materializations']+=1;return actual_materialize(*args,**kwargs)
        header=dict(kernel_addr=0x1000,tags_addr=0x2000,page_size=2048,name='synthetic',os_version=0,security_patch_month=0,header_version=1,
            recovery_dtbo_size=0,second_size=0,cmdline='synthetic',ramdisk_addr=0x3000,arm64_text_offset=0,ramdisk_file_offset=256,ramdisk_size=old.OLD_BYTES,
            second_file_offset=256+ro3.CAPACITY)
        def boot_header(payload):
            row=dict(header)
            if payload[:4]==b'DIAG':row.update(ramdisk_size=ro3.CAPACITY,kernel_sha256=boot_payloads['kernel_sha'])
            return row
        def prepare(backup_arg,variant,twrp_arg,mkboot_arg,path,cycle):
            counts['BOOTs']+=1;bound=json.loads((variant/'build-result.json').read_text())
            packer.payload_size(50870284,ro3.CAPACITY,2048,57671680)
            raw=bytearray(full_size);raw[:4]=b'DIAG';raw[256:256+ro3.CAPACITY]=compact
            raw[header['second_file_offset']:header['second_file_offset']+16]=b'SEANDROIDENFORCE'
            path.write_bytes(raw);boot_payloads.update(diagnostic=bytes(raw),kernel_sha=bound['image_sha256'],bound=bound)
        def build(backup_arg,boot,packages,current):
            counts['packages']+=1;packages.mkdir();bound=boot_payloads['bound'];fields=profile.fields(bound)
            records=[]
            for mode,payload in (('diagnostic',boot_payloads['diagnostic']),('rollback',oldboot)):
                item=dict(fields,mode=mode,file=mode+'.zip',payload_sha256=digest(payload),payload_size=len(payload),
                    kernel_image_sha256=bound['image_sha256'],auto_return_diagnostic=mode=='diagnostic',
                    auto_cycle_token=bound['auto_cycle_token'] if mode=='diagnostic' else None,test_purpose='linux-data-carrier' if mode=='diagnostic' else 'rollback')
                profile.package_scope(item,mode);records.append(item)
            pair=dict(fields,auto_return_diagnostic=True,auto_cycle_token=bound['auto_cycle_token'],kernel_image_sha256=bound['image_sha256'],
                backup_manifest_sha256=contract['backup_manifest_sha256'],expected_current_boot_sha256=digest(oldboot),packages=records)
            save(packages/'package-result.json',pair);profile.package_scope(pair)
        def verify(packages):
            pair=json.loads((Path(packages)/'package-result.json').read_text())
            if Path(packages).resolve()!=prior.resolve():
                profile.package_scope(pair)
                for row in pair['packages']:profile.package_scope(row,row['mode'])
            return pair['packages']
        def validate_plan(*args):counts['intrinsic_plans']+=1;return actual_validate_plan(*args)
        class Archive:
            def __init__(self,path):self.path=Path(path)
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def read(self,name):
                if name=='META-INF/com/google/android/update-binary':return b'WRITER'
                if name=='boot.img':return oldboot if self.path.name=='rollback.zip' else boot_payloads['diagnostic']
                raise AssertionError(name)
        with ExitStack() as stack:
            for target,value in (('sha256_kat_device_profile.raw_binding',raw_binding),('materialize_auto_cycle.materialize',materialized),
                ('type3_admission.patch_image',patched),('prepare_linux_boot.prepare',prepare),('build_boot_test_packages.build',build),
                ('stage_phase2.verify_packages',verify),('auto_cycle.verify_packages',verify),('prepare_linux_boot.read_verified_backup',lambda _:dict(boot=oldboot,recovery=official)),
                ('prepare_linux_boot.boot_header',boot_header),('build_boot_test_packages.updater',lambda **_:b'WRITER'),
                ('zipfile.ZipFile',Archive),('sha256_kat_device_profile.validate_plan',validate_plan)):
                stack.enter_context(patch(target,value))
            stack.enter_context(patch('prepare_linux_boot.TWRP_SHA256',digest(official)))
            stack.enter_context(patch('prepare_linux_boot.MKBOOTIMG_SHA256',digest(mkboot.read_bytes())))
            result=typed.prepare_offline(contract_path,contract_sha)
            plan=json.loads(Path(result['plan']).read_text());bound=boot_payloads['bound'];packages=Path(plan['stages'][0]['packages'])
            self.assertEqual((counts['materializations'],counts['BOOTs'],counts['packages'],counts['patches']),(1,1,1,1))
            self.assertEqual((bound['native_source_head'],bound['source_head'],bound['native_producer_version']),(ro3.NATIVE_HEAD,ro3.NATIVE_HEAD,'v107'))
            self.assertEqual((bound['host_profile_source_head'],bound['execution_version'],plan['minimum_battery']),('8'*40,'v108',10))
            self.assertEqual((source/'Image').read_bytes(),bytes(generic));self.assertEqual((derived/'kernel-readonly.data').read_bytes(),bytes(compact))
            with patch('type3_admission.prepare_template',side_effect=AssertionError('no transaction restart')):
                with self.assertRaises(ValueError):typed.prepare_offline(contract_path,contract_sha)
            for key,value in (('native_source_head','6'*40),('host_profile_source_head',ro3.NATIVE_HEAD),('execution_version','v107'),
                ('data_input_kind',old.KIND),('kernel_readonly3_image_bytes',image_size-1),('type3_contract_sha256','f'*64)):
                bad=copy.deepcopy(bound);bad[key]=value
                with self.subTest(key=key),self.assertRaises(ValueError):typed.candidate_scope(bad,patched=True)
            with self.assertRaises(ValueError):ro3.producer_contract({},ro3.NATIVE_HEAD)
            with self.assertRaises(ValueError):ro3.producer_contract(dict(source_sha256={}),ro3.NATIVE_HEAD,historical_origin=ro3.NATIVE_HEAD)
            with self.assertRaises(ValueError):packer.payload_size(50870284,old.OLD_BYTES,2048,57671680)
            self.assertGreater(packer.payload_size(50870284,ro3.CAPACITY,2048,57671680),0)
            with self.assertRaises(ValueError):profile.validate_plan(result['plan'],'0'*64)
            generic_report=json.loads((Path(contract['output'])/'template/build-result.json').read_text())
            corrupt=bytearray(generic);corrupt[descriptor]^=1
            untrusted=dict(generic_report,image_sha256=digest(corrupt),type3_generic_image_sha256=digest(corrupt))
            with self.assertRaises(ValueError):typed.patch_image(bytes(corrupt),untrusted,plan['stages'][0]['cycle'],token_slot,bytes(compact))
            for field,value in (('native_source_head','6'*40),('execution_version','v107'),('caps',dict(typed.OFFLINE_CAPS,materializations=2))):
                wrong=dict(contract);wrong[field]=value;save(work/'wrong-contract.json',wrong)
                with self.assertRaises(ValueError):typed.load_offline(work/'wrong-contract.json',digest((work/'wrong-contract.json').read_bytes()))
            device=dict(schema=typed.DEVICE_SCHEMA,status='reviewed_ready',execution_version='v108',host_source_head='8'*40,native_source_head=ro3.NATIVE_HEAD,
                plan_sha256=result['plan_sha256'],packages=str(packages),package_result_sha256=digest((packages/'package-result.json').read_bytes()),
                bound_image_sha256=bound['image_sha256'],offline_contract_sha256=contract_sha,output=str((work/'synthetic-run').resolve()),minimum_battery=10,BOOT_write_max=1,reboot_max=1,
                user_availability_record_sha256='4a639d278836af88256a339d199b9fbe53ad65d354db4b8c4401796522e758e9')
            device_path=work/'device.json';save(device_path,device);device_sha=digest(device_path.read_bytes())
            ctx=typed.execution_context(bound,result['plan_sha256'],packages,'v108','8'*40,device_path,device_sha,work/'synthetic-run')
            old.require_device_scope(bound,True,type3_context=ctx)
            for bad in (dict(bound,diagnostic_kind=old.SPAN_KIND),dict(bound,diagnostic_kind='readonly-input-pc')):
                with self.assertRaises(ValueError):old.require_device_scope(bad,True,type3_context=ctx)
            for wrong in (dict(ctx,declared_version='v107'),dict(ctx,host_source_head='6'*40),dict(ctx,plan_sha256='0'*64)):
                with self.assertRaises(ValueError):old.require_device_scope(bound,True,type3_context=wrong)
            with self.assertRaises(ValueError):old.require_device_scope(bound,False,type3_context=ctx)
            # Standalone real entry points refuse absent reviewed context before transport.
            with patch('stage_phase2.preflight',side_effect=AssertionError('no device')),patch('run_probe.preflight',side_effect=AssertionError('no device')):
                with self.assertRaises(ValueError):stage_phase2.stage(packages,object(),ack_kernel_readonly_growth=True)
                with self.assertRaises(ValueError):profile.precheck(packages,Path(plan['stages'][0]['kernel_build']),backup,object(),{},ack_kernel_readonly_growth=True)
                with self.assertRaises(ValueError):profile.collect(packages,Path(plan['stages'][0]['kernel_build']),object(),ack_kernel_readonly_growth=True)
            calls=[];capture=work/'capture';capture.mkdir();(capture/'synthetic.txt').write_text('synthetic')
            class Transport:
                serial='synthetic-only'
                def text(self,*args):calls.append(('text',args));return '/sbin/twrp'
                def call(self,*args,**kwargs):calls.append(('call',args));return b''
            def staged(*args,**kwargs):self.assertEqual(kwargs['type3_context'],ctx);return dict(ram_directory='/synthetic')
            def checked(*args,**kwargs):
                self.assertEqual(kwargs['type3_context'],ctx);self.assertEqual(kwargs['battery_policy']['effective_minimum_percent'],10)
                return dict(ready_for_manual_access_test=True,partition_evidence=dict(status='pass'))
            def collected(*args,**kwargs):
                self.assertEqual(kwargs['type3_context'],ctx)
                return dict(diagnostic_passed=True,directory=str(capture),log_selections={'synthetic':dict(selected_file='synthetic.txt')})
            with patch('auto_cycle.validate_plan',return_value=plan),patch('auto_cycle.preflight',return_value=dict(twrp_version='synthetic')),patch('auto_cycle.stage',side_effect=staged),\
                patch('sha256_kat_device_profile.precheck',side_effect=checked),patch('sha256_kat_device_profile.collect',side_effect=collected),\
                patch('auto_cycle.boot_id',return_value='before'),patch('auto_cycle.wait_recovery',return_value='after'),\
                patch('auto_cycle.verify_partitions'),patch('auto_cycle.decode_return',return_value=dict(request_only=True)):
                journal=auto_cycle.run_plan(result['plan'],result['plan_sha256'],work/'synthetic-run',execute=True,adb=Transport(),
                    ack_kernel_readonly_growth=True,execution_host_source_head='8'*40,declared_test_version='v108',
                    type3_device_contract=device_path,type3_device_contract_sha256=device_sha)
                self.assertEqual(journal['status'],'complete');self.assertEqual(journal['effective_minimum_battery'],10)
            with patch('auto_cycle.validate_plan',return_value=plan),patch('auto_cycle.preflight',side_effect=AssertionError('negative path contacted device')):
                for changes in (dict(declared_test_version='v107'),dict(v105_battery_5pct_exception=True),dict(ack_kernel_readonly_growth=False),
                    dict(execution_host_source_head='6'*40),dict(type3_device_contract_sha256='0'*64)):
                    kwargs=dict(execute=True,adb=Transport(),ack_kernel_readonly_growth=True,execution_host_source_head='8'*40,declared_test_version='v108',
                        type3_device_contract=device_path,type3_device_contract_sha256=device_sha);kwargs.update(changes)
                    with self.assertRaises(ValueError):auto_cycle.run_plan(result['plan'],result['plan_sha256'],work/'must-not-run',**kwargs)
                with self.assertRaises(ValueError):auto_cycle.run_plan(result['plan'],'0'*64,work/'wrong-plan',execute=True,adb=Transport(),
                    ack_kernel_readonly_growth=True,execution_host_source_head='8'*40,declared_test_version='v108',
                    type3_device_contract=device_path,type3_device_contract_sha256=device_sha)
            self.assertEqual(counts['materializations'],1);self.assertEqual(counts['patches'],1);self.assertEqual(counts['patch_attempts'],2)
        from precheck_window_access import require_install_battery
        require_install_battery(10)
        for battery in (5,9):
            with self.assertRaises(ValueError):require_install_battery(battery)
        save(OUTPUT/'transaction-summary.json',dict(counts=counts,native_version='v107',execution_version='v108',mock_transport_calls=len(calls),
            actual_device_operations=[],actual_private_inputs_read=0,C_compiles=0,Image_builds=0,CI=0))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();OUTPUT=profile.private(args.output);OUTPUT.mkdir(parents=True,exist_ok=False)
    names=('kernel_readonly_span_candidate.py','kernel_readonly_input.py','sha256_kat_device_profile.py','linux_data_carrier.py',
        'materialize_auto_cycle.py','auto_cycle.py','prepare_linux_boot.py','stage_phase2.py','type3_admission.py','test_v108_type3_admission.py')
    save(OUTPUT/'source-sha256.json',{name:digest((Path(__file__).resolve().parent/name).read_bytes()) for name in names})
    result=unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite([Type3AdmissionTests(METHOD)]))
    save(OUTPUT/'result.json',dict(schema='v108-new-host-admission-tests-v1',selected=[METHOD],run=result.testsRun,failures=len(result.failures),errors=len(result.errors),
        passed=result.wasSuccessful(),old_test_methods_run=0,fixture_compiles=0,Image_builds=0,CI=0,actual_device_operations=[]))
    raise SystemExit(0 if result.wasSuccessful() else 1)
