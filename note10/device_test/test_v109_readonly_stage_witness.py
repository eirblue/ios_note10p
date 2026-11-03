"""Exactly NEW2; one controlled class3 fixture compile/process; no device."""
import argparse
from contextlib import ExitStack
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch
import zipfile

import builtin_init_profile as builtin
import kernel_readonly_input as old
import kernel_readonly_span_candidate as ro3
import linux_data_carrier as data
import prepare_linux_boot as packer
import readonly_stage_witness as stage
import retained_v108_origin as retained
import sha256_kat_device_profile as profile
import stage_phase2
import type3_admission as typed
from decode_reservation import checksum

HERE=Path(__file__).resolve().parent
OUTPUT=None
IDENTITY,CYCLE,BOOT='1'*32,'2'*32,'3'*32
METHODS=('test_actual_class3_stage_witness_and_existing_cleanup','test_closed_witness_and_retained_v108_read_scope')

def digest(raw):return hashlib.sha256(raw).hexdigest()
def save(path,row):Path(path).write_text(json.dumps(row,sort_keys=True,indent=2)+'\n')
def frame(marker,body,boot=BOOT):return f'N10BOOTLINK2 boot={boot} {marker} {body} checksum={checksum(body.encode()):08x}'
def data_body(**changes):
    row=dict(id=IDENTITY,cycle=CYCLE,kind='result',source=ro3.MODE,status='ok',carrier=ro3.CAPACITY,logical=ro3.CAPACITY,
        carrier_rc=0,stream=18,payload=32,consumed=18,written=32,calls=1,digest='a'*64,reasons='00000000',
        expectations=1,captures=0,retained=1,ownership=0,executed=0)
    row.update(changes);return ' '.join(f'{key}={value}' for key,value in row.items())
def stage_body(bits=stage.ALL,*,work_cleanup=None,output_cleanup=None):
    work_cleanup=work_cleanup if work_cleanup is not None else ('void_returned' if bits&(1<<14) else 'not_called')
    output_cleanup=output_cleanup if output_cleanup is not None else ('void_returned' if bits&(1<<18) else 'not_called')
    return f'id={IDENTITY} cycle={CYCLE} kind=stages schema={stage.WIRE_SCHEMA} bits={bits:08x} work_cleanup={work_cleanup} output_cleanup={output_cleanup} ownership=0 hardware=0 executed=0'

class StageWitnessTests(unittest.TestCase):
    compiles=0
    processes=0

    def test_actual_class3_stage_witness_and_existing_cleanup(self):
        command=['clang-14','-std=gnu11','-O2','-Wall','-Wextra','-Werror',str(HERE/'readonly_stage_witness_fixture.c'),
            '-o',str(OUTPUT/'readonly-stage-witness-fixture')]
        save(OUTPUT/'fixture-command.json',command)
        type(self).compiles+=1;built=subprocess.run(command,capture_output=True,text=True,timeout=60)
        (OUTPUT/'fixture-compile.log').write_text(built.stdout+built.stderr)
        self.assertEqual(built.returncode,0,built.stderr)
        type(self).processes+=1;ran=subprocess.run([str(OUTPUT/'readonly-stage-witness-fixture')],capture_output=True,text=True,timeout=30)
        (OUTPUT/'fixture-output.json').write_text(ran.stdout);(OUTPUT/'fixture-stderr.log').write_text(ran.stderr)
        self.assertEqual(ran.returncode,0,ran.stderr);row=json.loads(ran.stdout)
        self.assertEqual((row['cases'],row['outcome_bytes'],row['state_bytes'],row['real_decoder_calls']),(12,128,88,0))
        self.assertTrue(all(row[key] for key in ('actual_n10_data_run','synthetic_only','call_order_counts','canaries','no_double_free')))

    def test_closed_witness_and_retained_v108_read_scope(self):
        good=frame('N10DATARO3',data_body())+'\n'+frame('N10DATASTAGE1',stage_body())
        decode=lambda text:stage.decode(text,IDENTITY,CYCLE,expected_schema=stage.SCHEMA)
        self.assertTrue(decode(good)['passed']);self.assertEqual(decode(good)['cleanup_result']['output'],'void_returned')
        # Old closed DATA remains readable without any invented witness.
        self.assertTrue(data.decode(frame('N10DATARO3',data_body()),IDENTITY,CYCLE,_source_class=ro3.MODE)['passed'])
        for bits in (stage.ALL|1<<20,stage.ALL^1,stage.ALL^(1<<3),stage.ALL^(1<<4),stage.ALL^(1<<12),1<<18):
            with self.subTest(bits=bits),self.assertRaises(ValueError):
                decode(frame('N10DATARO3',data_body())+'\n'+frame('N10DATASTAGE1',stage_body(bits)))
        malformed=(good+'\n'+frame('N10DATASTAGE1',stage_body()),good.split('\n')[0],good[:-1]+('0' if good[-1]!='0' else '1'),
            good.split('\n')[0]+'\n'+frame('N10DATASTAGE1',stage_body().replace(IDENTITY,'4'*32)),
            good.split('\n')[0]+'\n'+frame('N10DATASTAGE1',stage_body(),boot='4'*32),
            good.split('\n')[0]+'\n'+frame('N10DATASTAGE1',stage_body()+' bits=00000000'),
            frame('N10DATARO3',data_body(calls=0))+'\n'+frame('N10DATASTAGE1',stage_body()),
            frame('N10DATARO3',data_body(status='decode'))+'\n'+frame('N10DATASTAGE1',stage_body()))
        for text in malformed:
            with self.subTest(malformed=text[-60:]),self.assertRaises(ValueError):decode(text)
        partial=frame('N10DATARO3',data_body(status='header',stream=0,payload=0,consumed=0,written=0,calls=0,digest='0'*64))
        partial_result=decode(partial+'\n'+frame('N10DATASTAGE1',stage_body(1)))
        self.assertFalse(partial_result['passed']);self.assertEqual(partial_result['cleanup_result']['output'],'not_called')
        self.assertEqual(partial_result['cleanup_result']['work'],'not_called')
        allocation=frame('N10DATARO3',data_body(status='allocation',calls=0,consumed=0,written=0,digest='0'*64))
        for resource,shift in (('work',11),('output',15)):
            bits=1|2|(1<<19)|(15<<shift)
            parsed=decode(allocation+'\n'+frame('N10DATASTAGE1',stage_body(bits)))
            self.assertEqual(parsed['cleanup_result'][resource],'void_returned')
            self.assertEqual(parsed['cleanup_result']['output' if resource=='work' else 'work'],'not_called')
        for resource in ('work','output'):
            with self.subTest(cleanup=resource),self.assertRaises(ValueError):
                decode(partial+'\n'+frame('N10DATASTAGE1',stage_body(1,**{resource+'_cleanup':'void_returned'})))
            with self.subTest(cleanup=resource,phase='ok'),self.assertRaises(ValueError):
                decode(good.split('\n')[0]+'\n'+frame('N10DATASTAGE1',stage_body(**{resource+'_cleanup':'not_called'})))
        with self.assertRaises(ValueError):stage.decode(good,IDENTITY,CYCLE,expected_schema=ro3.SCHEMA)

        work=OUTPUT/'synthetic-retained';work.mkdir();contract_path=work/'contract.json'
        paths={key:str((work/key).resolve()) for key in ('producer_root','ci_success_context','compact_manifest','backup','current_packages','reference_twrp','output')}
        tool=HERE.parents[1]/'research/twrp-d2x-reference/aosp-mkbootimg.py'
        contract=dict(schema=typed.OFFLINE_SCHEMA,status='reviewed_ready',execution_version='v108',host_source_head=retained.HEAD,
            native_source_head=ro3.NATIVE_HEAD,accepted_result_sha256=ro3.NATIVE_RESULT_SHA256,**paths,mkbootimg=str(tool),caps=dict(typed.OFFLINE_CAPS),
            **{key:'a'*64 for key in ('ci_success_context_sha256','compact_manifest_sha256','backup_manifest_sha256','current_package_result_sha256','current_boot_sha256')})
        save(contract_path,contract);contract_sha=digest(contract_path.read_bytes())
        slot=dict(slot=dict(offset=4096,bytes=ro3.CAPACITY),descriptor=dict(offset=4096+ro3.CAPACITY,bytes=80))
        row=dict(device_profile=data.PROFILE,diagnostic_kind=ro3.KIND,data_input_kind=ro3.KIND,storage_input_kind=ro3.KIND,
            kernel_readonly3_schema=ro3.SCHEMA,kernel_readonly3_marker='N10DATARO3',kernel_readonly3_span_schema=old.SPAN_SCHEMA,
            kernel_readonly3_requires_ack=True,source_head=ro3.NATIVE_HEAD,native_source_head=ro3.NATIVE_HEAD,native_producer_version='v107',
            type3_native_origin=typed.native_origin(),native_producer_PC_first_use=True,PC_only=False,version='v108',execution_version='v108',
            host_profile_source_head=retained.HEAD,host_profile_source_sha256=dict(retained.PINS),kernel_readonly3_slot=slot,
            kernel_readonly3_image_bytes=5000000,kernel_readonly3_linked_bytes=6000000,
            kernel_readonly3_span=dict(schema=old.SPAN_SCHEMA,kernel_bytes=6000000,text_prefix_bytes=0,slot_contained=True,descriptor_contained=True,
                disjoint=True,source='linked-kernel',phase='pre_descriptor',hardware=False,ownership=False),
            data_expectation_mode=ro3.MODE,data_expectation_slot=slot,data_carrier_stage=data.STAGE,data_relative_placement_admitted=False,
            raw_input_binding=False,type3_external_choice='compact-v1',type3_compact_bytes=ro3.CAPACITY,data_carrier_bytes=old.OLD_BYTES,
            data_payload_bytes=old.PAYLOAD_BYTES,image_expectation_patched=True,type3_contract_path=str(contract_path),type3_contract_sha256=contract_sha,
            auto_return_diagnostic=True,auto_cycle_token=CYCLE,build_evidence_id=IDENTITY,kernel_banner='Linux version 4.14.113-v107-readonly-span-candidate synthetic',
            **{key:'a'*64 for key in ('type3_generic_image_sha256','type3_compact_sha256','type3_compact_manifest_sha256',
                'data_manifest_sha256','data_carrier_sha256','data_payload_sha256','profile_sha256','accepted_result_sha256','image_root_receipt_sha256',
                'root_reader_result_sha256',*builtin.EXTRA_FIELDS)})
        row['type3_materialization']=dict(schema='type3-fixed-patch-v1',generic_image_sha256='a'*64,bound_image_sha256='b'*64,
            template_report_sha256='a'*64,cycle=CYCLE)
        with ExitStack() as stack:
            # Old geometry and public tool hash are unchanged dependencies, not new test subjects.
            stack.enter_context(patch('kernel_readonly_span_candidate.metadata_contract'))
            stack.enter_context(patch('sha256_kat_device_profile.sha',side_effect=lambda p:packer.MKBOOTIMG_SHA256 if Path(p)==tool else 'e'*64))
            stack.enter_context(patch('stage_phase2.preflight',side_effect=AssertionError('no transport')))
            with self.assertRaises(ValueError):profile.host_binding(retained.HEAD)
            with self.assertRaises(ValueError):profile.host_binding(retained.STOPPED_HEAD)
            with self.assertRaises(ValueError):typed.candidate_scope(row,patched=True)
            self.assertNotEqual(profile.host_binding('7'*40)['host_profile_source_sha256'],row['host_profile_source_sha256'])
            with retained.read_scope():
                self.assertEqual(typed.candidate_scope(row,patched=True),contract)
                self.assertEqual(profile.host_profile_origin(row)['host_profile_source_sha256'],dict(retained.PINS))
                for key,value in (('native_source_head','7'*40),('native_producer_version','v109'),('execution_version','v109'),
                    ('host_profile_source_head','7'*40),('type3_contract_sha256','0'*64)):
                    bad=copy.deepcopy(row);bad[key]=value
                    with self.subTest(binding=key),self.assertRaises(ValueError):typed.candidate_scope(bad,patched=True)
                bad=copy.deepcopy(row);bad['host_profile_source_sha256'][next(iter(retained.PINS))]='0'*64
                with self.assertRaises(ValueError):typed.candidate_scope(bad,patched=True)
                # Explicit read purpose never enables constructors or a spent transaction.
                with self.assertRaises(ValueError):typed.prepare_offline(contract_path,contract_sha)
                with self.assertRaises(ValueError):typed.require_device_scope(row,True,{})
                with self.assertRaises(ValueError):typed.patch_image(b'',row,CYCLE,b'',b'')
            self.assertFalse(Path(contract['output']).exists())
            plan=dict(device_profile=data.PROFILE,current_boot_payload_sha256='b'*64)
            diagnostic=dict(payload_sha256='b'*64)
            builtin.current_boot_binding(plan,row,diagnostic)
            for bad_plan in (dict(plan,current_boot_payload_sha256='c'*64),dict(plan,current_boot_payload_sha256='0'*64)):
                with self.assertRaises(ValueError):builtin.current_boot_binding(bad_plan,row,diagnostic)
            bad=copy.deepcopy(row);bad['host_profile_source_head']=profile.V104_PROFILE_ORIGIN_HEAD
            with self.assertRaises(ValueError):builtin.current_boot_binding(plan,bad,diagnostic)
            # Actual common verifier visits synthetic pair/records/embedded manifests under retained read scope.
            packages=work/'packages';packages.mkdir();records=[]
            for mode in ('diagnostic','rollback'):
                meta=dict(row,mode=mode,test_purpose='linux-data-carrier' if mode=='diagnostic' else 'rollback',
                    auto_return_diagnostic=mode=='diagnostic',auto_cycle_token=CYCLE if mode=='diagnostic' else None,
                    writes=['boot'],automatic_reboot=False,payload_sha256=digest(b'BOOT'),updater_sha256=digest(b'WRITER'))
                path=packages/f'note10-phase2-{mode}.zip'
                with zipfile.ZipFile(path,'x') as archive:
                    archive.writestr('manifest.json',json.dumps(meta));archive.writestr('boot.img',b'BOOT')
                    archive.writestr('META-INF/com/google/android/update-binary',b'WRITER')
                records.append(dict(meta,file=path.name,sha256=digest(path.read_bytes())))
            save(packages/'package-result.json',dict(row,packages=records))
            self.assertEqual(len(stage_phase2.verify_packages(packages)),2)
            with self.assertRaises(ValueError):stage_phase2.stage(packages,object(),ack_kernel_readonly_growth=True)
            # New producer identity has no current offline/device admission, even with forged readiness flags.
            new=dict(row,version='v109',execution_version='v109',diagnostic_kind=stage.KIND,data_input_kind=stage.KIND,
                storage_input_kind=stage.KIND,readonly_stage_schema=stage.SCHEMA,PC_only=False,physical_ready=True,admission_blocked=False)
            with self.assertRaises(ValueError):profile.physical_input_scope(new)
            with self.assertRaises(ValueError):old.require_device_scope(new,True)
            with self.assertRaises(ValueError):typed.candidate_scope(new)
            for pc_kind in ('readonly-input-pc','kernel-readonly-span-pc','owned-contiguous-staging-pc','current-owned-staging-pc'):
                with self.subTest(pc_kind=pc_kind),self.assertRaises(ValueError):
                    old.require_device_scope(dict(PC_only=False,diagnostic_kind=pc_kind),True)
            required=(*ro3.SOURCES,*stage.SOURCES,'kernel_readonly_input.py','kernel_readonly_span.h','linux_data_carrier.py',
                'linux_data_carrier.c','linux_data_carrier_composition.c','build_builtin_init_image.py')
            pins={'note10/device_test/'+name:'d'*64 for name in required}
            producer={key:copy.deepcopy(row[key]) for key in ro3.FIELDS}
            producer.update(version='v109',diagnostic_kind=stage.KIND,data_input_kind=stage.KIND,storage_input_kind=stage.KIND,
                readonly_stage_schema=stage.SCHEMA,readonly_stage_marker='N10DATASTAGE1',operation_scope_PC_only=True,admission_blocked=True,
                kernel_readonly3_default_enabled=False,PC_only=False,PC_first_use=True,physical_ready=False,deployment_ready=False,
                passed=True,Image_built=True,BOOT_built=False,device_authorized=False,device_operations=[],data_expectation_mode=ro3.MODE,
                data_expectation_slot=slot,image_expectation_patched=False,external_initrd_capture=False,
                input_capture_source='late-kernel-readonly-span-class3',permanent_input_storage_bytes=ro3.CAPACITY,permanent_descriptor_bytes=80,
                additional_linked_storage_bytes=ro3.CAPACITY+80,class2_PC_storage_absent=True,image_bytes=5000000,
                data_footprint=dict(linked_kernel_bytes=6000000,data_state_bytes=88),source_sha256=pins,
                settings=dict(NOTE10_KERNEL_READONLY_SPAN_CANDIDATE='y',**{key:'n' for key in ('NOTE10_KERNEL_READONLY_INPUT',
                    'NOTE10_KERNEL_READONLY_SPAN_PC','NOTE10_READONLY_INPUT_PC','NOTE10_OWNED_CONTIGUOUS_STAGING','NOTE10_CURRENT_OWNED_STAGING')}),
                ci_context=dict(GITHUB_SHA='7'*40,GITHUB_WORKFLOW_SHA='7'*40,GITHUB_JOB='linux-data-carrier',GITHUB_REPOSITORY='eirblue/ios_note10p',
                    GITHUB_WORKFLOW_REF='eirblue/ios_note10p/'+ro3.WORKFLOW+'@refs/heads/main',GITHUB_RUN_ID='123',GITHUB_RUN_ATTEMPT='1'))
            accepted=ro3.producer_contract(producer,'7'*40,producing_sources=pins)
            self.assertEqual(accepted['candidate_kind'],stage.KIND);self.assertFalse(accepted['PC_only'])
            self.assertTrue(accepted['operation_scope_PC_only']);self.assertTrue(accepted['admission_blocked'])
            for changes in (dict(PC_only=True),dict(admission_blocked=False),dict(version='v107'),dict(readonly_stage_schema=ro3.SCHEMA),
                dict(data_footprint=dict(linked_kernel_bytes=6000000,data_state_bytes=96))):
                bad=copy.deepcopy(producer);bad.update(changes)
                with self.subTest(producer=changes),self.assertRaises(ValueError):ro3.producer_contract(bad,'7'*40,producing_sources=pins)
        save(OUTPUT/'host-summary.json',dict(retained_host_pin_count=len(retained.PINS),retained_read_only=True,
            current_baseline='synthetic-v108',new_candidate_admission=False,actual_private_input_reads=0,device_operations=[]))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--scope',required=True,choices=(stage.SELECTOR,));parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();OUTPUT=profile.private(args.output);OUTPUT.mkdir(parents=True,exist_ok=False)
    names=(*stage.SOURCES,'linux_data_carrier.c','kernel_readonly_span_candidate.py','kernel_readonly_input.py',
        'sha256_kat_device_profile.py','type3_admission.py','stage_phase2.py','builtin_init_profile.py','materialize_auto_cycle.py',
        'build_builtin_init_image.py','build_kernel_readonly_span_candidate.py')
    save(OUTPUT/'source-sha256.json',{name:digest((HERE/name).read_bytes()) for name in names})
    result=unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(StageWitnessTests(name) for name in METHODS))
    save(OUTPUT/'result.json',dict(schema='v109-new-readonly-stage-witness-tests-v1',selected=list(METHODS),run=result.testsRun,
        failures=len(result.failures),errors=len(result.errors),passed=result.wasSuccessful(),fixture_compiles=StageWitnessTests.compiles,
        fixture_processes=StageWitnessTests.processes,old_test_methods_run=0,real_decoder_calls=0,actual_private_input_reads=0,
        Image_builds=0,CI=0,device_operations=[]))
    raise SystemExit(0 if result.wasSuccessful() else 1)
