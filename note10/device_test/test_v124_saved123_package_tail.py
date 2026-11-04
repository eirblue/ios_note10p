"""One NEW generated-BOOT role/packager entry test; no real Image or device."""
import argparse
import ast
from contextlib import ExitStack
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import build_boot_test_packages as builder
import class3_native_origin as origins
import kernel_readonly_span_candidate as ro3
import linux_data_carrier as data
import native_prefree_output_admission as native
import native_scoped_output_admission as shared
import prepare_linux_boot as boot_writer
import sha256_kat_device_profile as profile
import type3_admission as typed
import type3_remaining_template as prior
import type3_remaining_packages as packages
from builtin_init_profile import EXTRA_FIELDS
METHOD='test_generated_boot_projection_and_one_saved123_package_tail'
SCOPE='v124-native121-saved123-package-tail'
RESULT_SCHEMA='v124-native121-saved123-package-test-v1'
CAPS={'local_tests':1,'local_C_compiles':0,'CI':0,'new_grouped_methods':1,'new_fixture_compiles':0,'new_fixture_processes':0,'old_fixture_runs':0,'old_methods':0,'native_target_builds':0,'kernel_builds':0,'Image_builds':0,'real_decoder':0,'MachO':0,'private_payload':0,'Linux_integration':0,'target_RAM_reservation':0,'device_queries':0,'BOOT_writes':0,'reboots':0,'max_requested_PC_payload_bytes':4096}
OUTPUT=None

def sha(raw):return hashlib.sha256(raw).hexdigest()
def save(path,row):Path(path).write_text(json.dumps(row,indent=2)+'\n',encoding='utf-8')
def pin(path):return dict(path=str(path),sha256=sha(path.read_bytes()))

def generated_boot_metadata(variant,backup,parts,prototype,payload,cycle):
    # Evaluate the exact reviewed producer's report-construction expression with
    # initialized synthetic buffers/locals, then its actual KAT field projection.
    # This is the generated BOOT shape, NOT a full template/variant row.
    tree=ast.parse(Path(boot_writer.__file__).read_text(encoding='utf-8'))
    f=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='pack_verified')
    expression=next(n.value for n in ast.walk(f) if isinstance(n,ast.Assign) and any(isinstance(x,ast.Name) and x.id=='report' for x in n.targets) and isinstance(n.value,ast.Dict))
    namespace=dict(MKBOOTIMG_SHA256=boot_writer.MKBOOTIMG_SHA256,auto_cycle_token=cycle,auto_return=True,backup=backup,bool=bool,boot=dict(os_version=0,security_patch_month=0),build=variant,builtin=False,command=['synthetic-only'],embedded_check=None,hashlib=hashlib,len=len,notifier_counts_scope=False,notifier_trace_scope=False,output=prototype,packed=payload,parts=parts,ramdisk=b'synthetic',roundtrip_scope=False,str=str,xnu_stage=False)
    result=eval(compile(ast.Expression(expression),str(boot_writer.__file__),'eval'),{'__builtins__':{}},namespace)
    result.update(profile.fields(variant))
    return result

class SavedBootPackageTests(unittest.TestCase):
    completed_sections=[]
    def done(self,name):
        type(self).completed_sections.append(name);save(OUTPUT/'progress.json',dict(schema=RESULT_SCHEMA,completed_sections=list(type(self).completed_sections)))

    def test_generated_boot_projection_and_one_saved123_package_tail(self):
        with tempfile.TemporaryDirectory(prefix='v124-new-',dir=OUTPUT) as temporary,ExitStack() as stack:
            root=Path(temporary);oldroot=root/'saved123';template=root/'saved122/template';variant=oldroot/'plan/cycle-01/kernel-build';prototype=oldroot/'plan/cycle-01/boot.img';backup=root/'backup';current=root/'current'
            for p in (template,variant,backup,current):p.mkdir(parents=True,exist_ok=True)
            h='a'*64;host='c'*40;cycle='2'*32;cfg=b'# synthetic retained config\n';image_sha='b'*64
            parts={n:(bytes([65+i])*1024) for i,n in enumerate(('boot','recovery','dtb','dtbo','vbmeta'))}
            baseline=dict(bootloader='N976NTEST1',partitions=[dict(partition=n,block_node='/dev/block/sda'+str(i+1),sha256=sha(body),size=len(body)) for i,(n,body) in enumerate(parts.items())]);save(backup/'backup-manifest.json',baseline);backup_sha=sha((backup/'backup-manifest.json').read_bytes())
            save(current/'package-result.json',dict(backup_manifest_sha256=backup_sha))
            for n in prior.FILES:
                if n.endswith('.config'):(template/n).write_bytes(cfg)
                else:save(template/n,{'synthetic_metadata':n})
            item=native.record();item['result']=sha((template/'result.json').read_bytes());stack.enter_context(patch.object(native,'_NATIVE121',native._freeze(item)))
            original=dict(schema=typed.OFFLINE_SCHEMA,status='reviewed_ready',execution_version='v122',host_source_head=prior.HEAD,native_source_head=item['head'],accepted_result_sha256=item['result'],producer_root=str(root/'generic'),ci_success_context=str(template/'ci-success-context.json'),ci_success_context_sha256=sha((template/'ci-success-context.json').read_bytes()),compact_manifest=str(template/'kernel-readonly-compact.json'),compact_manifest_sha256=sha((template/'kernel-readonly-compact.json').read_bytes()),backup=str(backup),backup_manifest_sha256=backup_sha,current_packages=str(current),current_package_result_sha256=sha((current/'package-result.json').read_bytes()),current_boot_sha256=h,reference_twrp=str(root/'reference.img'),mkbootimg=str(Path(typed.__file__).resolve().parents[2]/'research/twrp-d2x-reference/aosp-mkbootimg.py'),output=str(template.parent),caps=typed.OFFLINE_CAPS)
            save(root/'original122.json',original);(template/'type3-contract.json').write_bytes((root/'original122.json').read_bytes());original_sha=sha((root/'original122.json').read_bytes())
            keys=(*profile.FIELDS,*EXTRA_FIELDS,*data.FIELDS,*data.CARRIER_FIELDS,*typed.BINDING_FIELDS,*shared.SCOPED_FIELDS,*native.FIELDS)
            binding=dict.fromkeys(keys,h)
            binding.update(device_profile=data.PROFILE,diagnostic_kind='kernel-prefree-output-zero-observation-candidate',data_input_kind='kernel-prefree-output-zero-observation-candidate',storage_input_kind='kernel-prefree-output-zero-observation-candidate',source_head=item['head'],native_source_head=item['head'],native_producer_version='v121',version='v122',execution_version='v122',native_producer_PC_first_use=True,PC_only=False,host_profile_source_head=prior.HEAD,host_profile_source_sha256=dict(prior.PINS),**shared.stage_fields(item['head']),type3_native_origin=origins.origin(item['head']),image_size=item['image_bytes'],kernel_readonly3_image_bytes=item['image_bytes'],image_sha256=item['image_sha256'],effective_config_sha256=sha(cfg),type3_contract_path=str(root/'original122.json'),type3_contract_sha256=original_sha,type3_generic_image_sha256=item['image_sha256'],type3_external_choice='compact-v1',type3_compact_bytes=ro3.CAPACITY,image_expectation_patched=False,data_expectation_mode=ro3.MODE,data_relative_placement_admitted=False,raw_input_binding=False,build_evidence_id='1'*32,kernel_banner=origins.banner({'diagnostic_kind':'kernel-prefree-output-zero-observation-candidate'})+'synthetic')
            save(template/'device-profile.json',binding);report=profile.common_report(binding,sha((template/'device-profile.json').read_bytes()));save(template/'build-result.json',report)
            old=dict(schema=prior.SCHEMA,status='reviewed_ready',execution_version='v123',execution_host_source_head=packages.HEAD,execution_host_source_sha256=dict(packages.PINS),original_contract=pin(root/'original122.json'),failed_transaction={'path':str(root/'old122-transaction.json'),'sha256':h},operator_failure={'path':str(root/'old122-operator.json'),'sha256':h},trace={'path':str(root/'old122-trace.txt'),'sha256':h},template_root=str(template),template_files={n:sha((template/n).read_bytes()) for n in prior.FILES},output=str(oldroot),caps=prior.CAPS)
            save(root/'remaining123.json',old);old_sha=sha((root/'remaining123.json').read_bytes());oldctx=dict(contract=old,path=str(root/'remaining123.json'),sha256=old_sha,host=dict(host_profile_source_head=packages.HEAD,host_profile_source_sha256=dict(packages.PINS)))
            bound=dict(report,version='v123',execution_version='v123',host_profile_source_head=packages.HEAD,host_profile_source_sha256=dict(packages.PINS),image_sha256=image_sha,image_expectation_patched=True,auto_cycle_variant=True,auto_cycle_token=cycle,auto_cycle_template=str(template),auto_cycle_template_report_sha256=old['template_files']['build-result.json'],auto_cycle_template_image_sha256=item['image_sha256'],**{prior.FIELD:prior.marker(oldctx)})
            bound['type3_materialization']=typed.materialization(bound,cycle,item['image_sha256'],image_sha,old['template_files']['build-result.json'])
            save(variant/'build-result.json',bound);(variant/'handoff.config').write_bytes(cfg)
            payload=b'N10RET1'+b'Q'*505;prototype.write_bytes(payload)
            metadata=generated_boot_metadata(bound,backup,parts,prototype,payload,cycle)
            self.assertEqual(set(metadata),packages.BOOT_KEYS);self.assertNotIn('effective_config_sha256',metadata);self.assertNotIn('image_size',metadata)
            save(prototype.with_suffix('.json'),metadata)
            failed=dict(schema='saved122-template-remaining-journal-v1',status='failed_no_restart',phase='plan_reserved',contract_sha256=old_sha,counts=dict(template_tail=1,materializations=1,variant_validations=1,packs=1,plans=1));save(oldroot/'transaction.json',failed)
            (root/'trace.txt').write_text('package_scope: frozen122/native121 template fields differ\n',encoding='utf-8')
            failure=dict(schema='v123-remaining-template-operator-receipt-v1',success=False,invocation_attempts=1,invocation_exit_code=1,contract_sha256=old_sha,transaction_sha256=sha((oldroot/'transaction.json').read_bytes()),stderr_sha256=sha((root/'trace.txt').read_bytes()));save(root/'operator.json',failure)
            st=prototype.stat();live=dict(host_profile_source_head=host,host_profile_source_sha256={'synthetic/live.py':h})
            stack.enter_context(patch.object(profile,'host_binding',side_effect=lambda head:live if head==host else (_ for _ in ()).throw(ValueError('exact synthetic live host'))))
            contract=dict(schema=packages.SCHEMA,status='reviewed_ready',execution_version='v124',execution_host_source_head=host,execution_host_source_sha256=live['host_profile_source_sha256'],prior_contract=pin(root/'remaining123.json'),prior_transaction=pin(oldroot/'transaction.json'),prior_operator=pin(root/'operator.json'),prior_trace=pin(root/'trace.txt'),variant_report=pin(variant/'build-result.json'),variant_config=pin(variant/'handoff.config'),boot_metadata=pin(prototype.with_suffix('.json')),boot_path=str(prototype),boot_stat=dict(device=st.st_dev,inode=st.st_ino,size=st.st_size,mtime_ns=st.st_mtime_ns,ctime_ns=st.st_ctime_ns),output=str(root/'new124'),caps=packages.CAPS)
            save(root/'contract.json',contract);ctx=packages._start(root/'contract.json',sha((root/'contract.json').read_bytes()))
            before={p:sha(p.read_bytes()) for p in (prototype.with_suffix('.json'),variant/'build-result.json',oldroot/'transaction.json')}
            with packages.read_scope(ctx):
                self.assertIsNone(prior._ACTIVE.get());self.assertIsNone(profile.package_scope(metadata,'diagnostic'))
                for bad in (dict(metadata,unknown_role_key=True),dict(metadata,host_profile_source_head='e'*40),dict(metadata,sha256='f'*64),dict(metadata,prototype_created=False)):
                    with self.assertRaises(ValueError):profile.package_scope(bad,'diagnostic')
                self.done('actual_generated_boot_projection_and_closed_role_refusals')
                with self.assertRaises(ValueError):packages.require_finish(ctx)
                stack.enter_context(patch.object(builder,'read_verified_backup',return_value=parts))
                stack.enter_context(patch('stage_phase2.verify_packages',return_value=[dict(mode='diagnostic',payload_size=len(parts['boot']),payload_sha256=h)]))
                original_bytes=prototype.with_suffix('.json').read_bytes()
                with patch.object(builder.zipfile,'ZipFile',side_effect=AssertionError('wrong role must fail before ZIP')) as zipped:
                    for bad in (dict(metadata,unknown_role_key=True),dict(metadata,host_profile_source_head='e'*40),dict(metadata,sha256='f'*64)):
                        save(prototype.with_suffix('.json'),bad)
                        with self.assertRaises(ValueError):builder.build(backup,prototype,ctx['output']/'packages',current)
                    self.assertEqual(zipped.call_count,0)
                prototype.with_suffix('.json').write_bytes(original_bytes)
                self.done('actual_packager_entry_refuses_bad_metadata_before_zip')
                pair=builder.build(backup,prototype,ctx['output']/'packages',current);packages.record_pair(ctx,pair)
                self.assertEqual({x['mode'] for x in pair['packages']},{'diagnostic','rollback'})
                self.assertEqual(pair[packages.FIELD]['variant_BOOT_producer']['host_profile_source_head'],packages.HEAD)
                self.assertEqual(pair[packages.FIELD]['operation_host']['host_profile_source_head'],host)
                self.assertEqual(pair['host_profile_source_head'],packages.HEAD)
                packages.require_finish(ctx)
                with self.assertRaises(ValueError):builder.build(backup,prototype,ctx['output']/'packages',current)
                self.assertEqual(packages.read(ctx['output']/'transaction.json')['completed'],dict(pairs=1,plans=0))
                self.done('one_actual_synthetic_pair_then_unfinished_plan_gate')
            self.assertIsNone(prior._ACTIVE.get());self.assertIsNone(packages._SCOPE.get());self.assertEqual({p:sha(p.read_bytes()) for p in before},before)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--scope',required=True,choices=(SCOPE,));p.add_argument('--output',required=True,type=Path);a=p.parse_args();OUTPUT=a.output.resolve();root=Path(__file__).resolve().parents[2]
    if not OUTPUT.is_relative_to(root/'note10/private'):raise ValueError('fresh private synthetic output required')
    OUTPUT.mkdir(parents=True,exist_ok=False);result=unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite([SavedBootPackageTests(METHOD)]))
    save(OUTPUT/'result.json',dict(schema=RESULT_SCHEMA,scope=SCOPE,selected=[METHOD],run=result.testsRun,errors=len(result.errors),failures=len(result.failures),passed=result.wasSuccessful(),completed_sections=SavedBootPackageTests.completed_sections,caps=CAPS,old_methods_run=0,fixture_compiles=0,fixture_processes=0,actual_private_inputs=0,actual_device_operations=[],Image_builds=0,error_tracebacks=[dict(test=t.id(),traceback=v) for t,v in result.errors],failure_tracebacks=[dict(test=t.id(),traceback=v) for t,v in result.failures]))
    raise SystemExit(0 if result.wasSuccessful() else 1)
