"""One NEW native109/host110 integration method; all inputs and transport synthetic."""
import argparse
from contextlib import redirect_stdout
import io
import runpy
import sys
from contextlib import ExitStack
import copy
import hashlib
import json
from pathlib import Path
import struct
import unittest
from unittest.mock import patch

import auto_cycle
import builtin_init_profile as builtin
import class3_native_origin as origins
import kernel_readonly_input as old
import kernel_readonly_span_candidate as ro3
import linux_data_carrier as data
import materialize_auto_cycle as materializer
import prepare_linux_boot as packer
import readonly_stage_witness as stages
import retained_v108_origin as retained
import sha256_kat_device_profile as profile
import stage_phase2
import type3_admission as typed
import type3_remaining_pack as remaining
from decode_reservation import checksum

METHOD='test_native109_host110_admission_witness_join_and_pretransport_scope'
SCOPE='v110-native109-host-admission'
RECEIPT_METHOD='test_raw_context_copy_and_exact_receipt_regeneration'
RECEIPT_SCOPE='v110-ci-context-byte-copy-rev1'
PACK_METHOD='test_stage_kind_compact_dispatch_and_exact_remaining_pack_scope'
PACK_SCOPE='v110-remaining-pack-dispatch-rev2'
CLI_METHOD='test_script_main_uses_canonical_remaining_pack_context'
CLI_SCOPE='v110-canonical-remaining-cli-rev4'
OUTPUT=None
IDENTITY,BOOT,HOST='1'*32,'3'*32,'8'*40

def digest(raw):return hashlib.sha256(raw).hexdigest()
def save(path,row):Path(path).write_text(json.dumps(row,sort_keys=True,indent=2)+'\n')
def read(path):return json.loads(Path(path).read_text())
def frame(marker,body,boot=BOOT):return f'N10BOOTLINK2 boot={boot} {marker} {body} checksum={checksum(body.encode()):08x}'

class Native109AdmissionTests(unittest.TestCase):
    def test_native109_host110_admission_witness_join_and_pretransport_scope(self):
        work=OUTPUT/'synthetic';work.mkdir();source=work/'producer';source.mkdir()
        backup=work/'backup';backup.mkdir();prior=work/'prior108';prior.mkdir();compact_dir=work/'compact';compact_dir.mkdir()
        tool_root=work/'tool-repository';tool=tool_root/'research/twrp-d2x-reference/aosp-mkbootimg.py'
        tool.parent.mkdir(parents=True);tool.write_bytes(b'# inert synthetic tool; never executed\n')
        tool_module=tool_root/'note10/device_test/type3_admission.py';tool_module.parent.mkdir(parents=True)
        tool_module.write_bytes(b'# inert dependency root; never imported\n')
        slot_start=8192;desc=slot_start+ro3.CAPACITY;image_size=desc+80+4096;linked=image_size+2048
        generic=bytearray(image_size);generic[56:60]=b'ARM\x64';generic[1024:1057]=materializer.SLOT+b'\0'
        generic[512:519]=b'N10RET1';generic[desc:desc+80]=ro3.DESCRIPTOR
        (source/'Image').write_bytes(generic);(source/'prerequisites/objects').mkdir(parents=True)
        config=b'CONFIG_SYNTHETIC_ONLY=y\n';(source/'prerequisites/objects/.config').write_bytes(config)
        slot=dict(slot=dict(offset=slot_start,bytes=ro3.CAPACITY),descriptor=dict(offset=desc,bytes=80),boot_page=2048)
        span=dict(schema=old.SPAN_SCHEMA,kernel_bytes=image_size,text_prefix_bytes=2048,slot_contained=True,
            descriptor_contained=True,disjoint=True,source='linked-kernel',phase='pre_descriptor',hardware=False,ownership=False)
        native=dict(origins._NATIVE109);native.update(image_bytes=image_size,linked_bytes=linked,run_id=123,attempt=1,job_id=3,artifact_id=4)
        native['pins']=dict(native['pins'])
        accepted_contract=dict(temporary_outcome_bytes=128)
        producer=dict(version='v109',diagnostic_kind=stages.KIND,source_sha256=native['pins'],image_bytes=image_size,
            image_sha256=digest(generic),kernel_readonly3_linked_bytes=linked,data_footprint=dict(data_state_bytes=88),
            files_sha256={'actual-effective.config':digest(config)},build_evidence_id=IDENTITY,kernel_readonly3_candidate_contract=accepted_contract)
        save(source/'result.json',producer);native['result']=digest((source/'result.json').read_bytes())
        base=dict(device_profile=data.PROFILE,diagnostic_kind=stages.KIND,data_input_kind=stages.KIND,storage_input_kind=stages.KIND,
            readonly_stage_schema=stages.SCHEMA,readonly_stage_marker='N10DATASTAGE1',native_producer_provenance=origins.provenance(),
            kernel_readonly3_schema=ro3.SCHEMA,kernel_readonly3_slot=slot,kernel_readonly3_span_schema=old.SPAN_SCHEMA,
            kernel_readonly3_span=span,kernel_readonly3_linked_bytes=linked,kernel_readonly3_image_bytes=image_size,
            kernel_readonly3_requires_ack=True,kernel_readonly3_marker='N10DATARO3',data_carrier_stage=data.STAGE,
            data_relative_placement_admitted=False,raw_input_binding=False,data_expectation_mode=ro3.MODE,data_expectation_slot=slot,
            image_expectation_patched=False,accepted_result_sha256=native['result'],source_head=native['head'],image_sha256=digest(generic),
            image_size=image_size,effective_config_sha256=digest(config),build_evidence_id=IDENTITY,
            kernel_banner='Linux version 4.14.113-v109-readonly-stage-witness-candidate synthetic',
            **{key:'a'*64 for key in builtin.EXTRA_FIELDS})
        compact=bytearray(ro3.CAPACITY);compact[:8]=b'N10DATA1'
        struct.pack_into('<HHIQQQQ',compact,8,1,128,0,ro3.CAPACITY,128,old.STREAM_BYTES,old.PAYLOAD_BYTES)
        compact[128]=0x5d;struct.pack_into('<IQ',compact,129,1<<23,old.PAYLOAD_BYTES)
        compact[48:80]=hashlib.sha256(compact[128:128+old.STREAM_BYTES]).digest();compact[80:112]=bytes.fromhex('99'*32)
        manifest=dict(schema=old.COMPACT_SCHEMA,source_manifest_sha256='b'*64,source_carrier_sha256='c'*64,source_carrier_bytes=old.OLD_BYTES,
            compact_sha256=digest(compact),compact_bytes=ro3.CAPACITY,stream_bytes=old.STREAM_BYTES,stream_sha256=compact[48:80].hex(),
            payload_bytes=old.PAYLOAD_BYTES,payload_sha256='99'*32,header_bytes=128,zero_padding_bytes=2733,decoder_calls=0,
            recompressions=0,device_operations=[],physical_ready=False)
        (compact_dir/'kernel-readonly.data').write_bytes(compact);save(compact_dir/'compact-manifest.json',manifest)
        context={key:None for key in origins._CONTEXT_KEYS}
        context.update(schema='note10-root-native109-ci-success-context-v1',native_version='v109',native_source_head=native['head'],
            accepted_result_sha256=native['result'],producer_result_file_sha256=native['result'],source_sha256=native['pins'],
            run_id=123,run_attempt=1,job_id=3,artifact_id=4,workflow_id=404040749,repository='eirblue/ios_note10p',
            workflow_ref='eirblue/ios_note10p/'+ro3.WORKFLOW+'@refs/heads/main',run_conclusion='success',job_conclusion='success',
            Image_bytes=image_size,generic_image_sha256=digest(generic),candidate_contract=accepted_contract,
            both_methods_executed_at_current_source=False,native_Image_executed=False,producer_physical_ready=False,
            producer_admission_blocked=True,global_RAM_ownership_or_hardware_mapping_attested=False,authenticated_plaintext_zip_sha256='d'*64,
            source_manifest_sha256='a'*64,root_PC_acceptance_sha256='a'*64,operator_metadata_sha256='a'*64,operator_projection_sha256='a'*64,
            current_host_method=dict(passed=True,run=1,errors=0,failures=0,selected=['test_closed_witness_and_retained_v108_read_scope'],
                fixture_compiles=0,fixture_processes=0,old_test_methods_run=0,real_decoder_calls=0,actual_private_input_reads=0),
            carried_fixture=dict(source_head='595bc927f39424bbe659deef2957b90ec4a13091',run_id=41676621074,job_id=126058869018,cases=12,
                fixture_compiles=1,fixture_processes=1,replayed_in_rev1=False,overall_prior_CI_conclusion='failure',specific_method_passed=True,
                passed_method='test_actual_class3_stage_witness_and_existing_cleanup',native_dependencies={name:native['pins']['note10/device_test/'+name]
                    for name in ('linux_data_carrier.c','readonly_stage_witness.h','readonly_stage_witness_fixture.c')}))
        save(work/'ci-context.json',context)
        full_size=5*1024*1024;oldboot=b'BASE'+bytes(full_size-4);restoreboot=b'ROLL'+bytes(full_size-4)
        official=b'OFFI'+bytes(252+old.OLD_BYTES)
        twrp=work/'twrp';twrp.write_bytes(official);save(backup/'backup-manifest.json',dict(bootloader='N976N-synthetic',partitions={}))
        prior_pair=dict(device_profile=data.PROFILE,diagnostic_kind=ro3.KIND,data_input_kind=ro3.KIND,storage_input_kind=ro3.KIND,
            source_head=ro3.NATIVE_HEAD,native_source_head=ro3.NATIVE_HEAD,version='v108',execution_version='v108',native_producer_version='v107',
            host_profile_source_head=retained.HEAD,host_profile_source_sha256=dict(retained.PINS),
            backup_manifest_sha256=digest((backup/'backup-manifest.json').read_bytes()),
            packages=[dict(mode='diagnostic',payload_sha256=digest(oldboot),payload_size=full_size)])
        save(prior/'package-result.json',prior_pair)
        contract=dict(schema=typed.OFFLINE_SCHEMA,status='reviewed_ready',execution_version='v110',host_source_head=HOST,
            native_source_head=native['head'],accepted_result_sha256=native['result'],producer_root=str(source),
            ci_success_context=str(work/'ci-context.json'),ci_success_context_sha256=digest((work/'ci-context.json').read_bytes()),
            compact_manifest=str(compact_dir/'compact-manifest.json'),compact_manifest_sha256=digest((compact_dir/'compact-manifest.json').read_bytes()),
            backup=str(backup),backup_manifest_sha256=prior_pair['backup_manifest_sha256'],current_packages=str(prior),
            current_package_result_sha256=digest((prior/'package-result.json').read_bytes()),current_boot_sha256=digest(oldboot),
            reference_twrp=str(twrp),mkbootimg=str(tool),output=str(work/'transaction'),caps=dict(typed.OFFLINE_CAPS))
        contract_path=work/'offline.json';save(contract_path,contract);contract_sha=digest(contract_path.read_bytes())
        counts=dict(templates=0,variants=0,patches=0,plans=0,BOOTs=0,packages=0,raw_bindings=0,snapshots=0,selected_buffers=0)
        payloads={};host_pins={'note10/device_test/synthetic-host.py':'8'*64}
        actual_template=typed.prepare_template;actual_materialize=materializer.materialize;actual_patch=typed.patch_image;actual_plan=profile.validate_plan
        def host_binding(head):
            if head!=HOST:raise ValueError('only closed synthetic host publication')
            return dict(host_profile_source_head=HOST,host_profile_source_sha256=dict(host_pins))
        def raw_binding(root,expected,head,**kwargs):
            counts['raw_bindings']+=1;self.assertEqual((head,expected,kwargs.get('readonly_origin')),(native['head'],native['result'],native['head']))
            self.assertEqual(digest((Path(root)/'result.json').read_bytes()),expected)
            origins.producer(read(Path(root)/'result.json'),head);return copy.deepcopy(base)
        def template(*args,**kwargs):counts['templates']+=1;return actual_template(*args,**kwargs)
        def materialize(*args,**kwargs):counts['variants']+=1;return actual_materialize(*args,**kwargs)
        def patch_image(*args,**kwargs):counts['patches']+=1;return actual_patch(*args,**kwargs)
        def validate_plan(*args,**kwargs):counts['plans']+=1;return actual_plan(*args,**kwargs)
        header=dict(kernel_addr=0x1000,tags_addr=0x2000,page_size=2048,name='synthetic',os_version=0,security_patch_month=0,
            header_version=1,recovery_dtbo_size=0,second_size=0,cmdline='synthetic',ramdisk_addr=0x3000,arm64_text_offset=0,
            ramdisk_file_offset=256,ramdisk_size=old.OLD_BYTES,second_file_offset=256+ro3.CAPACITY)
        def boot_header(payload):
            row=dict(header)
            if payload[:4]==b'DIAG':row.update(ramdisk_size=ro3.CAPACITY,kernel_sha256=payloads['bound']['image_sha256'])
            return row
        def prepare(backup_arg,variant,twrp_arg,tool_arg,path,token):
            counts['BOOTs']+=1;payloads['bound']=read(variant/'build-result.json')
            raw=bytearray(full_size);raw[:4]=b'DIAG';raw[256:256+ro3.CAPACITY]=compact
            raw[header['second_file_offset']:header['second_file_offset']+16]=b'SEANDROIDENFORCE'
            path.write_bytes(raw);payloads['diagnostic']=bytes(raw)
        def build(backup_arg,boot,packages,current):
            counts['packages']+=1;packages.mkdir();bound=payloads['bound'];fields=profile.fields(bound);records=[]
            for mode,payload in (('diagnostic',payloads['diagnostic']),('rollback',restoreboot)):
                row=dict(fields,mode=mode,file=mode+'.zip',payload_sha256=digest(payload),payload_size=full_size,
                    kernel_image_sha256=bound['image_sha256'],auto_return_diagnostic=mode=='diagnostic',
                    auto_cycle_token=bound['auto_cycle_token'] if mode=='diagnostic' else None,test_purpose='linux-data-carrier' if mode=='diagnostic' else 'rollback')
                profile.package_scope(row,mode);records.append(row)
            pair=dict(fields,auto_return_diagnostic=True,auto_cycle_token=bound['auto_cycle_token'],kernel_image_sha256=bound['image_sha256'],
                backup_manifest_sha256=contract['backup_manifest_sha256'],expected_current_boot_sha256=digest(oldboot),packages=records)
            profile.package_scope(pair);save(packages/'package-result.json',pair)
        def verify(packages):
            pair=read(Path(packages)/'package-result.json')
            if Path(packages)==prior:
                with retained.read_scope():retained.origin(pair)
            else:
                profile.package_scope(pair)
                for row in pair['packages']:profile.package_scope(row,row['mode'])
            return pair['packages']
        class Archive:
            def __init__(self,path):self.path=Path(path)
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def read(self,name):
                if name=='META-INF/com/google/android/update-binary':return b'WRITER'
                if name=='boot.img':return restoreboot if self.path.name=='rollback.zip' else payloads['diagnostic']
                raise AssertionError(name)
        with ExitStack() as stack:
            for target,value in (('class3_native_origin._NATIVE109',native),('sha256_kat_device_profile.host_binding',host_binding),
                ('sha256_kat_device_profile.raw_binding',raw_binding),('kernel_readonly_span_candidate.producer_contract',lambda *a,**k:dict(temporary_outcome_bytes=128)),
                ('kernel_readonly_span_candidate.metadata_contract',lambda *a:None),('type3_admission.__file__',str(tool_module)),
                ('prepare_linux_boot.MKBOOTIMG_SHA256',digest(tool.read_bytes())),('prepare_linux_boot.TWRP_SHA256',digest(official)),
                ('type3_admission.prepare_template',template),('materialize_auto_cycle.materialize',materialize),('type3_admission.patch_image',patch_image),
                ('sha256_kat_device_profile.validate_plan',validate_plan),('prepare_linux_boot.prepare',prepare),('build_boot_test_packages.build',build),
                ('stage_phase2.verify_packages',verify),('auto_cycle.verify_packages',verify),('zipfile.ZipFile',Archive),
                ('prepare_linux_boot.read_verified_backup',lambda _:dict(boot=restoreboot,recovery=official)),('prepare_linux_boot.boot_header',boot_header),
                ('build_boot_test_packages.updater',lambda **_:b'WRITER')):
                stack.enter_context(patch(target,value))
            # New origin/host/predecessor refusals precede transaction creation or compact consumption.
            wrong_producer=copy.deepcopy(producer);wrong_producer['source_sha256'][next(iter(native['pins']))]='0'*64
            with self.assertRaises(ValueError):origins.producer(wrong_producer,native['head'])
            for key,value in (('native_source_head',ro3.NATIVE_HEAD),('accepted_result_sha256','0'*64),('execution_version','v109'),('host_source_head',native['head'])):
                bad=dict(contract);bad[key]=value;path=work/'bad-offline.json';save(path,bad)
                with self.subTest(contract=key),self.assertRaises(ValueError):typed.prepare_offline(path,digest(path.read_bytes()))
            bad=dict(contract,current_boot_sha256='0'*64);path=work/'bad-current.json';save(path,bad)
            with self.assertRaises(ValueError):typed.prepare_offline(path,digest(path.read_bytes()))
            corrupted=copy.deepcopy(prior_pair);corrupted['host_profile_source_sha256'][next(iter(retained.PINS))]='0'*64
            save(prior/'package-result.json',corrupted);bad=dict(contract,current_package_result_sha256=digest((prior/'package-result.json').read_bytes()))
            save(path,bad)
            with self.assertRaises(ValueError):typed.prepare_offline(path,digest(path.read_bytes()))
            save(prior/'package-result.json',prior_pair)
            self.assertFalse(Path(contract['output']).exists());self.assertEqual(counts['templates'],0)
            result=typed.prepare_offline(contract_path,contract_sha);plan=read(result['plan']);bound=payloads['bound']
            packages=Path(plan['stages'][0]['packages']);pair=read(packages/'package-result.json');token=plan['stages'][0]['cycle']
            self.assertEqual((counts['templates'],counts['variants'],counts['patches'],counts['plans'],counts['BOOTs'],counts['packages']),(1,1,1,1,1,1))
            self.assertEqual((result['native_version'],bound['native_producer_version'],bound['execution_version']),('v109','v109','v110'))
            self.assertEqual(bound['native_producer_provenance'],origins.provenance());self.assertEqual((source/'Image').read_bytes(),bytes(generic))
            for key,value in (('native_source_head',ro3.NATIVE_HEAD),('native_producer_version','v107'),('diagnostic_kind',ro3.KIND),
                ('kernel_readonly3_linked_bytes',linked+2048),('kernel_readonly3_image_bytes',image_size+1),('host_profile_source_head','7'*40)):
                wrong=copy.deepcopy(bound);wrong[key]=value
                with self.subTest(binding=key),self.assertRaises(ValueError):typed.candidate_scope(wrong,patched=True)
            wrong=copy.deepcopy(bound);wrong['type3_native_origin']['source_sha256'][next(iter(native['pins']))]='0'*64
            with self.assertRaises(ValueError):typed.candidate_scope(wrong,patched=True)
            wrong=copy.deepcopy(bound);wrong['native_producer_provenance']['physical_ready']=True
            with self.assertRaises(ValueError):typed.candidate_scope(wrong,patched=True)
            device=dict(schema=typed.DEVICE_SCHEMA,status='reviewed_ready',execution_version='v110',host_source_head=HOST,native_source_head=native['head'],
                plan_sha256=result['plan_sha256'],packages=str(packages),package_result_sha256=digest((packages/'package-result.json').read_bytes()),
                bound_image_sha256=bound['image_sha256'],offline_contract_sha256=contract_sha,output=str(work/'device-output'),minimum_battery=10,
                BOOT_write_max=1,reboot_max=1,user_availability_record_sha256='4a639d278836af88256a339d199b9fbe53ad65d354db4b8c4401796522e758e9')
            device_path=work/'device.json';save(device_path,device);device_sha=digest(device_path.read_bytes())
            ctx=typed.execution_context(bound,result['plan_sha256'],packages,'v110',HOST,device_path,device_sha,work/'device-output')
            old.require_device_scope(pair,True,type3_context=ctx)
            with patch('auto_cycle.validate_plan',return_value=plan),patch('auto_cycle.preflight',side_effect=AssertionError('no transport')):
                for changes in (dict(declared_test_version='v109'),dict(execution_host_source_head='7'*40),dict(ack_kernel_readonly_growth=False),
                    dict(type3_device_contract_sha256='0'*64),dict(type3_device_contract=None),dict(v105_battery_5pct_exception=True)):
                    kwargs=dict(execute=True,adb=object(),ack_kernel_readonly_growth=True,execution_host_source_head=HOST,declared_test_version='v110',
                        type3_device_contract=device_path,type3_device_contract_sha256=device_sha);kwargs.update(changes)
                    with self.subTest(context=changes),self.assertRaises(ValueError):auto_cycle.run_plan(result['plan'],result['plan_sha256'],work/'denied',**kwargs)
            with patch('stage_phase2.preflight',side_effect=AssertionError('no transport')),patch('run_probe.preflight',side_effect=AssertionError('no transport')):
                with self.assertRaises(ValueError):stage_phase2.stage(prior,object(),ack_kernel_readonly_growth=True)
                with self.assertRaises(ValueError):old.require_device_scope(prior_pair,True,type3_context=ctx)
                with self.assertRaises(ValueError):stage_phase2.stage(packages,object(),ack_kernel_readonly_growth=True)
                with self.assertRaises(ValueError):profile.precheck(packages,Path(plan['stages'][0]['kernel_build']),backup,object(),{},ack_kernel_readonly_growth=True)
                with self.assertRaises(ValueError):profile.collect(packages,Path(plan['stages'][0]['kernel_build']),object(),ack_kernel_readonly_growth=True)
            core=' '.join(f'{key}={value}' for key,value in dict(id=IDENTITY,cycle=token,kind='result',source=ro3.MODE,status='ok',carrier=ro3.CAPACITY,
                logical=ro3.CAPACITY,carrier_rc=0,stream=old.STREAM_BYTES,payload=old.PAYLOAD_BYTES,consumed=old.STREAM_BYTES-7,written=old.PAYLOAD_BYTES,
                calls=1,digest='99'*32,reasons='00000000',expectations=1,captures=0,retained=1,ownership=0,executed=0).items())
            span_body=f'id={IDENTITY} cycle={token} kind=span source=linked-kernel phase=pre_descriptor state=checked attempted=1 kernel_checked=1 kernel_bytes={image_size} extents_checked=1 slot_contained=1 descriptor_contained=1 disjoint=1 admission_called=1 reasons=00000000 ownership=0 hardware=0 executed=0'
            stage_body=f'id={IDENTITY} cycle={token} kind=stages schema={stages.WIRE_SCHEMA} bits={stages.ALL:08x} work_cleanup=void_returned output_cleanup=void_returned ownership=0 hardware=0 executed=0'
            text='\n'.join((frame('N10DATARO3',core),frame('N10DATASPAN1',span_body),frame('N10DATASTAGE1',stage_body)))
            def baseline(raw,banner,identity,cycle,*,digest_decoder,digest_marker,component_evidence):
                counts['selected_buffers']+=1;self.assertEqual((identity,cycle,digest_marker),(IDENTITY,token,b'N10DATARO3'))
                observed=digest_decoder(raw.decode('ascii'),identity)
                component_evidence.update(pid1_validation='validated',return_validation='validated_request_records',return_boot_association='validated')
                return raw,dict(kat=observed,boot_identity=BOOT,minimal_PID1_start_observed=True,auto_return=dict(request_only=True))
            def snapshot(adb,out,report,cycle,*,decode_fn):
                counts['snapshots']+=1;_,observed=decode_fn(text.encode(),report['kernel_banner'],IDENTITY,cycle)
                return dict(diagnostic_passed=True,observation=observed,device_operations=[])
            with patch('builtin_init_profile.decode',side_effect=baseline),patch('linux_data_carrier.structural_presence',return_value=dict(synthetic=True)),\
                patch('builtin_init_profile.snapshot',side_effect=snapshot),patch('run_probe.preflight',return_value=dict(twrp_version='synthetic')):
                collected=profile._collect_into(packages,Path(plan['stages'][0]['kernel_build']),object(),work/'synthetic-capture',
                    ack_kernel_readonly_growth=True,type3_context=ctx)
                self.assertTrue(collected['observation']['component_evidence']['readonly_stage_witness']['passed'])
                for bad_text in (text.rsplit('\n',1)[0],text.rsplit('\n',1)[0]+'\n'+frame('N10DATASTAGE1',stage_body,boot='4'*32),
                    text.rsplit('\n',1)[0]+'\n'+frame('N10DATASTAGE1',stage_body.replace(token,'5'*32)),
                    text.rsplit('\n',1)[0]+'\n'+frame('N10DATASTAGE1',stage_body.replace(f'{stages.ALL:08x}',f'{stages.ALL^(1<<10):08x}'))):
                    with self.assertRaises(data.ComponentObservationError) as caught:
                        stages.decode_selected(bad_text.encode(),bound['kernel_banner'],IDENTITY,token,expected=bound)
                    self.assertIn('kernel_readonly3_data',caught.exception.component_evidence)
                    self.assertIn('kernel_readonly3_span',caught.exception.component_evidence)
                    self.assertEqual(caught.exception.component_evidence['readonly_stage_witness']['state'],'invalid_or_missing')
            self.assertEqual((counts['snapshots'],counts['patches'],counts['variants']),(1,1,1))
            self.assertEqual(len([row for row in typed.IO_EVENTS if row['operation']=='attach_existing_compact_once']),1)
            with self.assertRaises(ValueError):typed.prepare_offline(contract_path,contract_sha)
        save(OUTPUT/'integration-summary.json',dict(counts=counts,synthetic_registry=True,actual_private_inputs=0,actual_device_operations=[],
            C_compiles=0,fixture_processes=0,Image_builds=0,CI=0,old_methods_run=0,missing_companion_core_only_fallback=False))


    def test_raw_context_copy_and_exact_receipt_regeneration(self):
        work=OUTPUT/'synthetic-receipt';work.mkdir()
        reviewed_raw=b'{\r\n  "synthetic": true,\r\n  "native_version": "v109"\r\n}\r\n'
        reviewed_context=json.loads(reviewed_raw.decode('utf-8-sig'));reviewed_sha=digest(reviewed_raw)
        reviewed_receipt=dict(schema='native109-root-ci-receipt-v1',kind='synthetic-accepted-image',
            root_reader_result_sha256=reviewed_sha,accepted=True)
        normalized=work/'normalized';normalized.mkdir();correct=work/'exact';correct.mkdir()
        for directory in (normalized,correct):
            save(directory/'result.json',dict(synthetic=True))
            save(directory/'image-root-receipt.json',reviewed_receipt)
        # Reproduce the new failed metadata-only path, without native inputs or the passed integration method.
        typed.save(normalized/'ci-success-context.json',reviewed_context)
        self.assertEqual(read(normalized/'ci-success-context.json'),reviewed_context)
        self.assertNotEqual(digest((normalized/'ci-success-context.json').read_bytes()),reviewed_sha)
        def checked_receipt(context,context_sha,binding,producer):
            if context!=reviewed_context or producer!=dict(synthetic=True):raise ValueError('synthetic reviewed metadata differs')
            return dict(reviewed_receipt,root_reader_result_sha256=context_sha)
        def validate(directory):
            receipt=directory/'image-root-receipt.json'
            return profile.root_receipt_binding(directory,receipt,digest(receipt.read_bytes()),{})
        # Unchanged native CI-authority validation is isolated; exercise real copy/hash/receipt equality logic.
        with patch('class3_native_origin.ci_receipt',side_effect=checked_receipt):
            with self.assertRaisesRegex(ValueError,'native109 stored CI receipt differs'):validate(normalized)
            typed._copy_ci_context(correct,reviewed_raw)
            self.assertEqual((correct/'ci-success-context.json').read_bytes(),reviewed_raw)
            result=validate(correct);self.assertEqual(result['root_reader_result_sha256'],reviewed_sha)
            with self.assertRaises(FileExistsError):typed._copy_ci_context(correct,reviewed_raw)
            self.assertEqual((correct/'ci-success-context.json').read_bytes(),reviewed_raw)
            save(correct/'image-root-receipt.json',dict(reviewed_receipt,root_reader_result_sha256='0'*64))
            with self.assertRaisesRegex(ValueError,'native109 stored CI receipt differs'):validate(correct)
            save(correct/'image-root-receipt.json',reviewed_receipt)
            typed.save(correct/'ci-success-context.json',dict(reviewed_context,native_version='v110'))
            with self.assertRaisesRegex(ValueError,'synthetic reviewed metadata differs'):validate(correct)
        save(OUTPUT/'receipt-summary.json',dict(raw_reviewed_bytes_preserved=True,normalized_object_equality_insufficient=True,
            exact_receipt_equality_required=True,exclusive_copy=True,old_integration_method_run=0,actual_private_inputs=0,
            actual_device_operations=[],Image_builds=0,CI=0,fixture_compiles=0,fixture_processes=0))


    def test_stage_kind_compact_dispatch_and_exact_remaining_pack_scope(self):
        work=OUTPUT/'synthetic-remaining';work.mkdir()
        saved=work/'spent';template=saved/'template';variant=saved/'plan/cycle-01/kernel-build'
        template.mkdir(parents=True);variant.mkdir(parents=True)
        backup=work/'backup';backup.mkdir();prior=work/'prior108';prior.mkdir();producer=work/'producer';producer.mkdir()
        tool_root=work/'canonical-tool';tool=tool_root/'research/twrp-d2x-reference/aosp-mkbootimg.py'
        tool.parent.mkdir(parents=True);tool.write_bytes(b'# synthetic, never executed\n')
        tool_module=tool_root/'note10/device_test/type3_admission.py';tool_module.parent.mkdir(parents=True)
        config=b'CONFIG_BLK_DEV_INITRD=y\nCONFIG_RD_LZMA=y\nCONFIG_ARM64_4K_PAGES=y\n'
        compact=bytes(ro3.CAPACITY);manifest=b'{"synthetic_compact_metadata":true}\n';native=dict(origins._NATIVE109)
        result_raw=b'{"synthetic_producer_metadata":true}\n';native['result']=digest(result_raw)
        slot=dict(schema=ro3.SCHEMA,source=ro3.MODE,capacity=ro3.CAPACITY,descriptor_bytes=80,generic=True,patched=False,
            permanent_input_bytes=ro3.CAPACITY,permanent_descriptor_bytes=80,physical_ready=False,descriptor_class=3,boot_page=2048)
        for index,key,symbol,section,size,preimage,offset in (
            (1,'slot',ro3.SLOT,'.rodata.n10_kernel_readonly3_input',ro3.CAPACITY,digest(compact),4096),
            (2,'descriptor',ro3.DESC,'.rodata.n10_kernel_readonly3_descriptor',80,digest(ro3.DESCRIPTOR),4096+ro3.CAPACITY)):
            slot[key]=dict(symbol=symbol,section=section,offset=offset,bytes=size,alignment=16,readonly_flags='A',
                preimage_sha256=preimage,object_section_index=index,object_symbol_offset=0)
        span=dict(schema=old.SPAN_SCHEMA,kernel_bytes=native['linked_bytes']-2048,text_prefix_bytes=2048,slot_contained=True,
            descriptor_contained=True,disjoint=True,source='linked-kernel',phase='pre_descriptor',hardware=False,ownership=False)
        original_path=work/'spent-offline.json';context_raw=b'{"synthetic_context":true}\n'
        save(backup/'backup-manifest.json',dict(synthetic=True));save(prior/'package-result.json',dict(
            device_profile=data.PROFILE,diagnostic_kind=ro3.KIND,data_input_kind=ro3.KIND,storage_input_kind=ro3.KIND,
            source_head=retained.NATIVE,native_source_head=retained.NATIVE,version='v108',execution_version='v108',native_producer_version='v107',
            host_profile_source_head=retained.HEAD,host_profile_source_sha256=dict(retained.PINS),
            backup_manifest_sha256=profile.sha(backup/'backup-manifest.json'),packages=[dict(mode='diagnostic',payload_sha256='d'*64)]))
        (work/'context.json').write_bytes(context_raw);(work/'compact.json').write_bytes(manifest)
        twrp=work/'twrp';twrp.write_bytes(b'synthetic-unopened-reference')
        offline=dict(schema=typed.OFFLINE_SCHEMA,status='reviewed_ready',execution_version='v110',host_source_head=remaining.HEAD,
            native_source_head=native['head'],accepted_result_sha256=native['result'],producer_root=str(producer),
            ci_success_context=str(work/'context.json'),ci_success_context_sha256=digest(context_raw),compact_manifest=str(work/'compact.json'),
            compact_manifest_sha256=digest(manifest),backup=str(backup),backup_manifest_sha256=profile.sha(backup/'backup-manifest.json'),
            current_packages=str(prior),current_package_result_sha256=profile.sha(prior/'package-result.json'),current_boot_sha256='d'*64,
            reference_twrp=str(twrp),mkbootimg=str(tool),output=str(saved),caps=dict(typed.OFFLINE_CAPS))
        save(original_path,offline);old_sha=profile.sha(original_path)
        receipt_raw=b'{"synthetic_previously_accepted_receipt":true}\n'
        binding=dict(device_profile=data.PROFILE,diagnostic_kind=stages.KIND,data_input_kind=stages.KIND,storage_input_kind=stages.KIND,
            **origins.stage_fields(),kernel_readonly3_schema=ro3.SCHEMA,kernel_readonly3_slot=slot,kernel_readonly3_span_schema=old.SPAN_SCHEMA,
            kernel_readonly3_span=span,kernel_readonly3_linked_bytes=native['linked_bytes'],kernel_readonly3_image_bytes=native['image_bytes'],
            kernel_readonly3_requires_ack=True,kernel_readonly3_marker='N10DATARO3',data_carrier_stage=data.STAGE,
            data_relative_placement_admitted=False,raw_input_binding=False,data_expectation_mode=ro3.MODE,data_expectation_slot=slot,
            image_expectation_patched=False,accepted_result_sha256=native['result'],source_head=native['head'],native_source_head=native['head'],
            version='v110',execution_version='v110',native_producer_version='v109',native_producer_PC_first_use=True,
            type3_native_origin=dict(source_head=native['head'],accepted_result_sha256=native['result'],source_sha256=dict(native['pins']),native_version='v109'),
            host_profile_source_head=remaining.HEAD,host_profile_source_sha256=dict(remaining.PINS),image_sha256='a'*64,image_size=native['image_bytes'],
            type3_generic_image_sha256='a'*64,type3_contract_path=str(original_path),type3_contract_sha256=old_sha,type3_external_choice='compact-v1',
            type3_compact_sha256=digest(compact),type3_compact_bytes=ro3.CAPACITY,type3_compact_manifest_sha256=digest(manifest),
            data_carrier_bytes=old.OLD_BYTES,data_payload_bytes=old.PAYLOAD_BYTES,data_manifest_sha256='b'*64,data_carrier_sha256='c'*64,
            data_payload_sha256='e'*64,effective_config_sha256=digest(config),build_evidence_id=IDENTITY,
            kernel_banner=origins.banner(dict(data_input_kind=stages.KIND))+'synthetic',image_root_receipt_sha256=digest(receipt_raw),
            root_reader_result_sha256=digest(context_raw),**{key:'a'*64 for key in builtin.EXTRA_FIELDS})
        save(template/'device-profile.json',binding);generic=profile.common_report(binding,profile.sha(template/'device-profile.json'))
        save(template/'build-result.json',generic)
        for root in (template,variant):
            (root/'device-profile.json').write_bytes((template/'device-profile.json').read_bytes())
            (root/'handoff.config').write_bytes(config);(root/'image-root-receipt.json').write_bytes(receipt_raw)
            (root/'kernel-readonly-compact.json').write_bytes(manifest)
        (template/'type3-contract.json').write_bytes(original_path.read_bytes());(template/'ci-success-context.json').write_bytes(context_raw)
        (template/'result.json').write_bytes(result_raw)
        token='6'*32;bound=dict(generic,auto_cycle_variant=True,auto_cycle_token=token,auto_cycle_template=str(template),
            auto_cycle_template_report_sha256=profile.sha(template/'build-result.json'),auto_cycle_template_image_sha256=generic['image_sha256'],
            image_sha256='f'*64,image_expectation_patched=True)
        bound['type3_materialization']=typed.materialization(generic,token,generic['image_sha256'],bound['image_sha256'],bound['auto_cycle_template_report_sha256'])
        save(variant/'build-result.json',bound)
        journal=dict(schema='type3-offline-journal-v1',status='failed_no_restart',phase='plan_reserved',error_type='ValueError',
            device_operations=[],contract_sha256=old_sha,attempts=dict(templates=1,plans=1,materializations=1))
        save(saved/'transaction.json',journal)
        projection=dict(schema='v110-offline-receipt-copy-rev1-failure-projection-v1',status='failed_no_restart',host_source_head=remaining.HEAD,
            native_source_head=native['head'],native_result_sha256=native['result'],offline_contract_sha256=old_sha,
            offline_transaction_sha256=profile.sha(saved/'transaction.json'),offline_transaction_path=str(saved/'transaction.json'),phase='plan_reserved',error_type='ValueError',
            failure_diagnosis=dict(message='bounded private DATA input required',template_and_variant_completed_before_failure=True),
            operation_counts=dict(cycles_prepared=0,materializations=1,decoder_calls=0,device_operations=0,plan_attempts=1,packages_created=0,
                compact_copy_operations=1,variants=1,compact_validation_operations=1,completed_plan=False,templates=1))
        projection_path=work/'failure.json';save(projection_path,projection)
        contract=dict(schema=remaining.SCHEMA,status='reviewed_ready',execution_version='v110',packaging_host_source_head=HOST,
            retained_host_source_head=remaining.HEAD,native_source_head=native['head'],accepted_result_sha256=native['result'],
            original_contract=str(original_path),original_contract_sha256=old_sha,original_transaction_sha256=profile.sha(saved/'transaction.json'),
            failure_projection=str(projection_path),failure_projection_sha256=profile.sha(projection_path),
            template_profile_sha256=profile.sha(template/'device-profile.json'),template_report_sha256=profile.sha(template/'build-result.json'),
            variant_report_sha256=profile.sha(variant/'build-result.json'),variant_config_sha256=digest(config),bound_image_sha256=bound['image_sha256'],
            cycle=token,output=str(work/'fresh-remaining'),caps=dict(remaining.CAPS))
        contract_path=work/'remaining.json';save(contract_path,contract)
        host=dict(host_profile_source_head=HOST,host_profile_source_sha256={'synthetic/live-packer.py':'8'*64})
        def host_binding(head):
            if head!=HOST:raise ValueError('closed synthetic live packaging host required')
            return copy.deepcopy(host)
        class ReachedCompactDispatch(Exception):pass
        class StopBeforePacking(Exception):pass
        with patch('class3_native_origin._NATIVE109',native),patch('sha256_kat_device_profile.host_binding',side_effect=host_binding),\
             patch('type3_admission.__file__',str(tool_module)),patch('prepare_linux_boot.MKBOOTIMG_SHA256',digest(tool.read_bytes())):
            frozen={str(p):p.read_bytes() for p in saved.rglob('*') if p.is_file()}
            def load_contract(row):
                save(contract_path,row);return remaining.load(contract_path,profile.sha(contract_path))
            context=load_contract(contract);self.assertEqual(context['report'],bound);self.assertEqual(context['host'],host)
            self.assertFalse((variant/'Image').exists())  # Metadata admission never opens Image.
            for key,value in (('retained_host_source_head',HOST),('packaging_host_source_head',remaining.HEAD),('cycle','7'*32),
                ('variant_report_sha256','0'*64),('original_transaction_sha256','0'*64),('failure_projection_sha256','0'*64)):
                with self.subTest(reject=key),self.assertRaises(ValueError):load_contract(dict(contract,**{key:value}))
            wrong=copy.deepcopy(contract);wrong['caps']['materializations']=1
            with self.assertRaises(ValueError):load_contract(wrong)
            wrong=copy.deepcopy(context['binding']);wrong['packaging_host']['host_profile_source_sha256']['arbitrary.py']='0'*64
            load_contract(contract)
            with self.assertRaises(ValueError):remaining.checked_binding(wrong)
            changed=dict(journal,attempts=dict(templates=1,plans=2,materializations=1));save(saved/'transaction.json',changed)
            with self.assertRaises(ValueError):load_contract(dict(contract,original_transaction_sha256=profile.sha(saved/'transaction.json')))
            (saved/'transaction.json').write_bytes(frozen[str(saved/'transaction.json')]);context=load_contract(contract)
            for action in (lambda:origins.live_host(remaining.HEAD),lambda:typed.prepare_template(offline,original_path,old_sha),
                lambda:remaining.saved_metadata(variant,token),lambda:remaining.require_pack(variant,work/'boot.img',token),
                lambda:typed.require_device_scope(bound,True),lambda:profile.package_scope(bound)):
                with self.assertRaises(ValueError):action()
            with remaining._scope(context):
                self.assertEqual(remaining.saved_metadata(variant,token),bound)
                with self.assertRaises(ValueError):remaining.saved_metadata(variant,'7'*32)
            # Exercise the actual failed packer dispatch up to its unchanged pre-write size boundary.
            # Only the unchanged header/compact I/O adapters are synthetic; no packer subprocess executes.
            image=bytearray(64);(variant/'Image').write_bytes(image)
            header=dict(header_version=1,page_size=2048,recovery_dtbo_size=0,second_size=0,kernel_addr=4096,tags_addr=8192,
                arm64_text_offset=0,ramdisk_file_offset=64,ramdisk_size=old.OLD_BYTES,cmdline='synthetic')
            official=bytes(64+old.OLD_BYTES);vbmeta=bytearray(128);vbmeta[:4]=b'AVB0';struct.pack_into('>I',vbmeta,120,2)
            parts=dict(boot=b'BOOT',vbmeta=bytes(vbmeta));destination=Path(contract['output']);destination.mkdir()
            pack_journal=dict(schema='type3-remaining-pack-journal-v1',status='started',phase='pack_reserved',
                contract_sha256=context['binding']['contract_sha256'],attempts=dict(BOOT_packings=1,package_pair_builds=0,plans=0,intrinsic_variant_data_consumptions=1,intrinsic_packer_compact_validations=1),device_operations=[])
            save(destination/'transaction.json',pack_journal)
            def size_boundary(kernel_size,ramdisk_size,*args,**kwargs):
                self.assertEqual((kernel_size,ramdisk_size),(64,ro3.CAPACITY));raise ReachedCompactDispatch()
            existing_bounded_read=data.bounded_private_read
            def closed_read(path,*args,**kwargs):
                if Path(path).name=='carrier.data':raise AssertionError('carrier.data fallback forbidden')
                return existing_bounded_read(path,*args,**kwargs)
            with remaining._scope(context),patch('prepare_linux_boot.boot_header',return_value=header),\
                 patch('type3_admission.read_compact',return_value=(compact,{})) as compact_reader,\
                 patch('linux_data_carrier.bounded_private_read',side_effect=closed_read),\
                 patch('prepare_linux_boot.payload_size',side_effect=size_boundary),\
                 patch('prepare_linux_boot.subprocess.run',side_effect=AssertionError('no subprocess')):
                with self.assertRaises(ReachedCompactDispatch):packer.pack_verified(backup,variant,official,tool,destination/'cycle-01/boot.img',parts,bound,config,token,kat_profile=True)
                self.assertEqual(compact_reader.call_count,1)
                with self.assertRaises(ValueError):packer.pack_verified(backup,variant,official,tool,destination/'other.img',parts,bound,config,token,kat_profile=True)
            wrapper=dict(bound,**{remaining.FIELD:context['binding']})
            plan=dict(kernel_build=str(template),backup=str(backup),current_packages=str(prior),
                current_package_result_sha256=offline['current_package_result_sha256'],current_boot_payload_sha256=offline['current_boot_sha256'],
                stages=[dict(kernel_build=str(variant),cycle=token,build_result_sha256=contract['variant_report_sha256'],
                    image_sha256=bound['image_sha256'],packages=str(destination/'cycle-01/packages'),package_result_sha256='0'*64)],
                **{remaining.FIELD:context['binding']})
            with remaining._scope(context):
                remaining.package_scope(wrapper);remaining.plan_pair(plan,wrapper,bound,destination/'plan.json')
                wrong=copy.deepcopy(plan);wrong[remaining.FIELD]['packaging_host']['host_profile_source_head']='7'*40
                with self.assertRaises(ValueError):remaining.plan_pair(wrong,wrapper,bound,destination/'plan.json')
            packages=destination/'cycle-01/packages';packages.mkdir(parents=True);save(packages/'package-result.json',wrapper)
            plan['stages'][0]['package_result_sha256']=profile.sha(packages/'package-result.json');save(destination/'plan.json',plan)
            plan_sha=profile.sha(destination/'plan.json')
            device=dict(schema=remaining.DEVICE_SCHEMA,status='reviewed_ready',execution_version='v110',producer_host_source_head=remaining.HEAD,
                packaging_host_source_head=HOST,native_source_head=native['head'],plan_sha256=plan_sha,packages=str(packages),
                package_result_sha256=profile.sha(packages/'package-result.json'),bound_image_sha256=bound['image_sha256'],offline_contract_sha256=old_sha,
                remaining_contract_sha256=context['binding']['contract_sha256'],output=str(work/'future-device'),minimum_battery=10,BOOT_write_max=1,reboot_max=1,
                user_availability_record_sha256='4a639d278836af88256a339d199b9fbe53ad65d354db4b8c4401796522e758e9')
            device_path=work/'future-device-contract.json';save(device_path,device)
            with self.assertRaises(ValueError):typed.execution_context(wrapper,plan_sha,packages,'v110',HOST,device_path,profile.sha(device_path),work/'future-device')
            complete=dict(pack_journal,status='complete',phase='complete',attempts=dict(BOOT_packings=1,package_pair_builds=1,plans=1,intrinsic_variant_data_consumptions=1,intrinsic_packer_compact_validations=1),result=dict(plan_sha256=plan_sha))
            save(destination/'transaction.json',complete)
            execution=typed.execution_context(wrapper,plan_sha,packages,'v110',HOST,device_path,profile.sha(device_path),work/'future-device')
            self.assertEqual(execution['schema'],remaining.CONTEXT_SCHEMA)
            self.assertTrue(typed.require_device_scope(bound,True,execution))
            for ack,ctx in ((False,execution),(True,None)):
                with self.assertRaises(ValueError):typed.require_device_scope(bound,ack,ctx)
            wrong=copy.deepcopy(device);wrong['packaging_host_source_head']=remaining.HEAD;save(device_path,wrong)
            with self.assertRaises(ValueError):typed.execution_context(wrapper,plan_sha,packages,'v110',HOST,device_path,profile.sha(device_path),work/'future-device')
            # A fresh remaining-stage reservation invokes only packing, preserving all saved metadata.
            fresh=dict(contract,output=str(work/'fresh-reservation'));load_contract(fresh)
            with patch('prepare_linux_boot.prepare',side_effect=StopBeforePacking()) as pack_io,\
                 patch('materialize_auto_cycle.materialize',side_effect=AssertionError('no rematerialization')),\
                 patch('type3_admission.patch_image',side_effect=AssertionError('no repatch')),\
                 patch('type3_admission.prepare_template',side_effect=AssertionError('no template')):
                with self.assertRaises(StopBeforePacking):remaining.prepare(contract_path,profile.sha(contract_path))
                self.assertEqual(pack_io.call_count,1)
                with self.assertRaises(ValueError):remaining.prepare(contract_path,profile.sha(contract_path))
                self.assertEqual(pack_io.call_count,1)
            for path,raw in frozen.items():self.assertEqual(Path(path).read_bytes(),raw)
            self.assertEqual(read(Path(fresh['output'])/'transaction.json')['status'],'failed_no_restart')
        save(OUTPUT/'remaining-summary.json',dict(actual_failed_dispatch_exercised=True,exact_retained_host_map_count=len(remaining.PINS),
            intrinsic_variant_data_consumptions=1,intrinsic_packer_compact_validations=1,original_compact_source_consumptions=0,
            immutable_saved_metadata=True,separate_live_packing_origin=True,prewrite_mismatch_rejection=True,spent_transaction_restart=0,
            old_methods_run=0,actual_private_inputs=0,actual_device_operations=[],Image_builds=0,CI=0,fixture_compiles=0,fixture_processes=0))


    def test_script_main_uses_canonical_remaining_pack_context(self):
        work=OUTPUT/'synthetic-cli';work.mkdir()
        contract=work/'inert-contract.json';pin='9'*64;token='6'*32
        variant=work/'saved-variant';template=work/'saved-template'
        report=dict(synthetic_metadata_only=True)
        context=dict(template=template,variant=variant,generic=dict(synthetic_generic=True),report=report,
            contract=dict(variant_report_sha256='a'*64,template_report_sha256='b'*64,variant_config_sha256='c'*64,cycle=token))
        calls=[]
        def metadata_pin(path):
            path=Path(path)
            if path==variant/'build-result.json':return 'a'*64
            if path==variant/'handoff.config':return 'c'*64
            raise AssertionError('unexpected input read: '+str(path))
        def canonical_prepare(path,expected):
            calls.append((path,expected));self.assertEqual((path,expected),(contract,pin))
            self.assertIs(typed.remaining,remaining);self.assertIs(profile.remaining,remaining)
            self.assertIsNone(remaining._ACTIVE.get())
            with remaining._scope(context):
                self.assertIs(typed.remaining._ACTIVE.get(),context)
                self.assertIs(profile.remaining._ACTIVE.get(),context)
                # Exercise the same saved-metadata context guard reached by the failed script path.
                with patch('sha256_kat_device_profile.private',side_effect=lambda value:Path(value)),\
                     patch('sha256_kat_device_profile.sha',side_effect=metadata_pin):
                    self.assertEqual(typed.remaining.saved_metadata(variant,token,template),report)
                    with self.assertRaises(ValueError):typed.remaining.saved_metadata(variant,'7'*32,template)
            self.assertIsNone(remaining._ACTIVE.get())
            return dict(canonical_prepare_called=True,shared_active_context=True,actual_input_reads=0,packer_calls=0)
        argv=[str(Path(remaining.__file__).resolve()),'--contract',str(contract),'--contract-sha256',pin]
        captured=io.StringIO()
        with patch.object(remaining,'prepare',side_effect=canonical_prepare) as canonical,patch.object(sys,'argv',argv),redirect_stdout(captured),\
             patch('prepare_linux_boot.prepare',side_effect=AssertionError('no packing operation')),\
             patch('type3_admission.prepare_template',side_effect=AssertionError('no template operation')),\
             patch('materialize_auto_cycle.materialize',side_effect=AssertionError('no materialization operation')):
            namespace=runpy.run_path(str(Path(remaining.__file__).resolve()),run_name='__main__')
        self.assertEqual(canonical.call_count,1);self.assertEqual(calls,[(contract,pin)])
        self.assertIsNot(namespace['_ACTIVE'],remaining._ACTIVE)
        self.assertIsNone(namespace['_ACTIVE'].get());self.assertIsNone(remaining._ACTIVE.get())
        self.assertEqual(json.loads(captured.getvalue()),dict(canonical_prepare_called=True,shared_active_context=True,actual_input_reads=0,packer_calls=0))
        self.assertFalse(contract.exists());self.assertFalse(variant.exists());self.assertFalse(template.exists())
        save(OUTPUT/'canonical-cli-summary.json',dict(script_main_route=True,canonical_prepare_calls=1,canonical_context_shared=True,
            separate_script_namespace_not_used_for_transaction=True,real_saved_metadata_context_guard=True,
            actual_private_inputs=0,actual_device_operations=[],packer_calls=0,compact_reads=0,fixture_compiles=0,fixture_processes=0,
            Image_builds=0,CI=0,old_methods_run=0))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--scope',required=True,choices=(CLI_SCOPE,));parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();OUTPUT=profile.private(args.output);OUTPUT.mkdir(parents=True,exist_ok=False)
    names=('class3_native_origin.py','type3_admission.py','sha256_kat_device_profile.py','kernel_readonly_span_candidate.py',
        'readonly_stage_witness.py','linux_data_carrier.py','kernel_readonly_input.py','auto_cycle.py','materialize_auto_cycle.py','test_v110_native109_admission.py','type3_remaining_pack.py','prepare_linux_boot.py')
    save(OUTPUT/'source-sha256.json',{name:digest((Path(__file__).resolve().parent/name).read_bytes()) for name in names})
    result=unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite([Native109AdmissionTests(CLI_METHOD)]))
    save(OUTPUT/'result.json',dict(schema='v110-canonical-remaining-cli-regression-v1',scope=args.scope,selected=[CLI_METHOD],run=result.testsRun,
        errors=len(result.errors),failures=len(result.failures),passed=result.wasSuccessful(),fixture_compiles=0,fixture_processes=0,Image_builds=0,CI=0,
        actual_private_inputs=0,actual_device_operations=[],old_methods_run=0,error_tracebacks=[dict(test=test.id(),traceback=trace) for test,trace in result.errors],
        failure_tracebacks=[dict(test=test.id(),traceback=trace) for test,trace in result.failures]))
    raise SystemExit(0 if result.wasSuccessful() else 1)
