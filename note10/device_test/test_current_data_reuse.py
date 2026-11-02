"""Only new historical-source/current-subject forwarding paths; no old suite/artifact execution."""
import argparse
import copy
import json
import runpy
import sys
from pathlib import Path
import tempfile
import types
import unittest
from unittest import mock
import current_data_reuse as reuse
import linux_data_carrier as data
import sha256_kat_device_profile as profile
from materialize_auto_cycle import bound_image

CASE_IDS=('test_exact_historical_sources_generic_and_PC_refusals',
          'test_current_subject_and_root_record_binding',
          'test_fresh_two_patch_variant_and_plan_field_forwarding',
          'test_script_entry_forwards_canonical_context_to_real_raw_binding')


def store(path,value):
    raw=(json.dumps(value,indent=2)+'\n').encode();path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
    return reuse.sha(raw)


class ReuseTests(unittest.TestCase):
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory(prefix='v97-new-synthetic-',dir=reuse.ROOT/'note10/private')
        self.addCleanup(self.temporary.cleanup);self.root=Path(self.temporary.name)
    def fixture(self,name):
        root=self.root/name;root.mkdir()
        original=root/'v91-linux-data-carrier-20261102'
        producer=original/'evidence-v91-once/extracted-private-evidence/image-producer';producer.mkdir(parents=True)
        pins={}
        for n in data.SOURCES:
            p=producer/'source/note10/device_test'/n;p.parent.mkdir(parents=True,exist_ok=True)
            p.write_bytes(('synthetic producing source '+n).encode());pins['note10/device_test/'+n]=reuse.sha(p.read_bytes())
        admission={'eligible':True,'checks':{},'route_relation':{}}
        result=dict(version='v91',diagnostic_kind='linux-data-carrier',passed=True,Image_built=True,BOOT_built=False,
            cycle_slot_patched=False,image_expectation_patched=False,data_expectation_mode=data.MODE,
            data_expectation_slot={'generic':True},data_footprint={'data_state_bytes':88},
            data_carrier_stage=data.STAGE,raw_input_binding=False,data_relative_placement=admission,
            ci_context=dict(GITHUB_SHA=reuse.IMAGE_HEAD,GITHUB_RUN_ID='41404110966',GITHUB_RUN_ATTEMPT='1',GITHUB_JOB='linux-data-carrier'),
            image_sha256='1'*64,image_bytes=512,build_evidence_id='a'*32,source_sha256=pins)
        result_sha=store(producer/'result.json',result)
        accepted={k:result[k] for k in ('image_sha256','image_bytes','build_evidence_id')}
        accepted.update(result_path=str(producer/'result.json'),result_sha256=result_sha)
        linux=dict(schema='note10-v91-ci-operator-receipt-v1',source=dict(commit=reuse.IMAGE_HEAD,observed_producer_source_sha256=pins),
            workflow=dict(head_sha=reuse.IMAGE_HEAD,run_id=41404110966,attempt=1,conclusion='success',job_name='linux-data-carrier'),
            original_artifact_and_extraction_directory=str(original),image_producer=accepted)
        linux_path=root/'linux-receipt.json';linux_sha=store(linux_path,linux)
        ci={'GITHUB_SHA':reuse.PAYLOAD_HEAD,'GITHUB_RUN_ID':'201'}
        inputs=dict(actual_producer_context=dict(kind='v84-current-native',producer_id='2'*64,input_binding='3'*64,
            producer=dict(candidate_kind='v94-exynos-checked-ptpage-pc',ci_context=ci,source_commit=reuse.PAYLOAD_HEAD)),
            producer_context_sha256='4'*64,producer_result_sha256_reused_from_accepted_receipt='5'*64)
        input_path=root/'inputs.json';input_sha=store(input_path,inputs)
        fit=dict(current_producer_kind='v94-exynos-checked-ptpage-pc',ci_context=ci,producer_id='2'*64,input_binding='3'*64,
            producer_context_sha256='4'*64,producer_result_sha256='5'*64,payload_bytes=19136512,payload_sha256='6'*64,fits_budget=True,PC_only=True,physical_ready=False)
        fit_path=root/'fit.json';fit_sha=store(fit_path,fit)
        carrier=dict(purpose='fixed-data-carrier-host-preparation',accepted=True,decoder_calls=1,payload_bytes=19136512,
            payload_manifest_sha256=fit_sha,input_ci_context=ci,producer_id='2'*64,input_binding='3'*64,carrier_bytes=10962166,
            carrier_admitted=False,deployment_ready=False,decode={'status':0},decoded_bytes=19136512,decoded_sha256='6'*64,payload_sha256='6'*64,carrier_sha256='7'*64)
        carrier_path=root/'carrier/carrier-manifest.json';carrier_sha=store(carrier_path,carrier)
        made=dict(kind='v95-fresh-current-payload-carrier-pc',accepted=True,decoder_calls=1,fits_budget=True,payload_bytes=19136512,
            payload_manifest_sha256=fit_sha,input_binding_metadata_sha256=input_sha,PC_only=True,physical_ready=False,
            carrier_manifest='carrier/carrier-manifest.json',carrier_manifest_sha256=carrier_sha)
        made_path=root/'made.json';made_sha=store(made_path,made)
        host=dict(schema='note10-v95-host-operator-receipt-v1',actual_transform=dict(command_invocations=1,exit_code=0,
            result_path=str(made_path),result_manifest_sha256=made_sha,fit_report_path=str(fit_path),fit_report_sha256=fit_sha,
            input_binding_path=str(input_path),input_binding_sha256=input_sha))
        host_path=root/'current-receipt.json';host_sha=store(host_path,host)
        return dict(root=root,producer=producer,result=result,linux=linux,linux_path=linux_path,linux_sha=linux_sha,
            host=host,host_path=host_path,host_sha=host_sha,inputs=inputs,input_path=input_path,made=made,made_path=made_path,
            carrier_path=carrier_path,carrier_sha=carrier_sha,admission=admission)
    def context(self,f):return reuse.ProducingSources(f['linux_path'],f['linux_sha'],f['host_path'],f['host_sha'])
    def test_exact_historical_sources_generic_and_PC_refusals(self):
        f=self.fixture('source');context=self.context(f);context.verify_sources(f['result'],data.SOURCES)
        with mock.patch.object(data,'relative_admission',return_value=f['admission']):
            got=data.input_binding(f['result'],[],elf=b'',archive=b'',raw_inputs={},producing_sources=context)
        self.assertEqual(got['data_expectation_mode'],data.MODE)
        with self.assertRaises(ValueError):
            data.input_binding(f['result'],[],elf=b'',archive=b'',raw_inputs={},producing_sources=f['producer'])
        for delta in ({'image_expectation_patched':True},{'PC_only':True},
                      {'version':'v96','diagnostic_kind':'current-owned-staging-pc'}):
            with self.assertRaises(ValueError):
                context.require_result(f['producer'],context.result_sha,reuse.IMAGE_HEAD,dict(f['result'],**delta))
        for kind in ('owned-contiguous-staging-pc','current-owned-staging-pc'):
            with self.assertRaises(ValueError):profile.physical_input_scope({'PC_only':False,'diagnostic_kind':kind})
        with self.assertRaises(ValueError):
            context.require_result(f['producer'],context.result_sha,'b'*40,f['result'])
        with self.assertRaises(ValueError):reuse.ProducingSources(f['linux_path'],'0'*64,f['host_path'],f['host_sha'])
        (f['producer']/'source/note10/device_test/linux_data_carrier.c').write_bytes(b'changed')
        with self.assertRaises(ValueError):context.verify_sources(f['result'],data.SOURCES)
    def test_current_subject_and_root_record_binding(self):
        f=self.fixture('record');context=self.context(f);output=f['root']/'template';output.mkdir()
        record=context.write_record(output,'b'*40)
        binding=dict(record,source_head=reuse.IMAGE_HEAD,host_profile_source_head='b'*40)
        loaded=reuse.load_record(output,binding);loaded.check_carrier(context.carrier_fields)
        self.assertEqual(loaded.carrier_path,f['carrier_path'])
        with self.assertRaises(ValueError):loaded.check_carrier(dict(context.carrier_fields,data_payload_bytes=19546112))
        for i,wrong in enumerate(('v85-current-native','v93-exynos-leaf-bootstrap-pc')):
            f=self.fixture('wrong'+str(i));f['inputs']['actual_producer_context']['producer']['candidate_kind']=wrong
            new_pin=store(f['input_path'],f['inputs']);f['host']['actual_transform']['input_binding_sha256']=new_pin
            f['made']['input_binding_metadata_sha256']=new_pin
            f['host']['actual_transform']['result_manifest_sha256']=store(f['made_path'],f['made'])
            f['host_sha']=store(f['host_path'],f['host'])
            with self.assertRaises(ValueError):self.context(f)
    def test_fresh_two_patch_variant_and_plan_field_forwarding(self):
        f=self.fixture('plan');context=self.context(f);template=f['root']/'template';template.mkdir()
        side=context.write_record(template,'b'*40)
        raw=b'prefix!'+profile.SLOT+b'\0'+bytes(24)+data.SLOT_PREIMAGE+bytes(27)
        offset=raw.index(data.SLOT_PREIMAGE)
        slot=dict(kind=data.MODE,bytes=64,symbol_bytes=64,expectation_bytes=40,logical_bytes=8,boot_page=2048,
            preimage_sha256=data.sha(data.SLOT_PREIMAGE),symbol=data.SLOT_SYMBOL,section=data.SLOT_SECTION,generic=True,
            readonly_flags='A',offset=offset,expectation_offset=offset+24,logical_offset=offset+56)
        keys=(*profile.FIELDS,'minimal_init_elf_sha256','initramfs_cpio_sha256','builtin_init_manifest_sha256','guarded_init_main_sha256')
        binding={k:'8'*64 for k in keys}
        binding.update(device_profile=profile.DATA_PROFILE,build_evidence_id='a'*32,source_head=reuse.IMAGE_HEAD,
            host_profile_source_head='b'*40,host_profile_source_sha256={},kernel_banner='Linux version 4.14.113-v91-trusted-logical synthetic',
            data_carrier_stage=data.STAGE,data_relative_placement_admitted=True,raw_input_binding=False,
            data_expectation_mode=data.MODE,data_expectation_slot=slot,image_expectation_patched=False,
            image_sha256=data.sha(raw),image_size=len(raw),**context.carrier_fields,**side)
        report=profile.common_report(binding,'8'*64);store(template/'build-result.json',report)
        backup=f['root']/'backup';backup.mkdir();store(backup/'backup-manifest.json',{'synthetic':True})
        current=f['root']/'current';current.mkdir();store(current/'package-result.json',{'synthetic':True})
        seen={}
        def materialize(source,target,token):
            self.assertEqual(Path(source),template);target.mkdir()
            patched=bound_image(raw,report,token);seen.update(token=token,patched=patched)
            variant=dict(report,image_sha256=data.sha(patched),image_expectation_patched=True,
                auto_cycle_token=token,auto_cycle_variant=True,auto_cycle_template=str(template))
            store(target/'build-result.json',variant);return variant
        def prepare(backup,target,twrp,mkbootimg,boot,cycle):Path(boot).write_bytes(b'synthetic BOOT placeholder')
        def build(backup,boot,packages,prior):
            packages.mkdir();variant=json.loads((Path(boot).parent/'kernel-build/build-result.json').read_text())
            fields=profile.fields(variant);self.assertEqual(fields[reuse.FIELD],side[reuse.FIELD])
            self.assertEqual(fields[reuse.MODE_FIELD],reuse.MODE);store(packages/'package-result.json',fields)
        modules={'materialize_auto_cycle':types.SimpleNamespace(materialize=materialize),
            'prepare_linux_boot':types.SimpleNamespace(prepare=prepare),
            'build_boot_test_packages':types.SimpleNamespace(build=build),
            'stage_phase2':types.SimpleNamespace(verify_packages=lambda path:[{'mode':'diagnostic','payload_sha256':'9'*64}])}
        with mock.patch.dict('sys.modules',modules),mock.patch.object(profile,'validate_template',return_value=report), \
             mock.patch.object(profile,'validate_plan',return_value={}) as selfvalidation:
            made=profile.prepare_plan(template,backup,f['root']/'twrp',f['root']/'mkbootimg',current,f['root']/'fresh-plan',1)
        selfvalidation.assert_called_once()
        plan=json.loads(Path(made['plan']).read_text());self.assertEqual(plan['build_result_sha256'],profile.sha(template/'build-result.json'))
        self.assertEqual(len(plan['stages']),1);self.assertEqual(plan['stages'][0]['cycle'],seen['token'])
        expected=bytearray(raw);cycle=raw.index(profile.SLOT+b'\0')
        expected[cycle:cycle+32]=seen['token'].encode()
        expected[offset+24:offset+64]=bytes.fromhex(context.carrier_fields['data_carrier_sha256'])+context.carrier_fields['data_carrier_bytes'].to_bytes(8,'little')
        self.assertEqual(seen['patched'],bytes(expected));self.assertEqual(raw[offset:offset+64],data.SLOT_PREIMAGE)
        with self.assertRaises(ValueError):bound_image(seen['patched'],report,'c'*32)
        with mock.patch.dict('sys.modules',modules),mock.patch.object(profile,'validate_template',return_value=report):
            with self.assertRaisesRegex(ValueError,'fresh KAT plan required'):
                profile.prepare_plan(template,backup,self.root/'t',self.root/'m',current,f['root']/'fresh-plan',1)


    def test_script_entry_forwards_canonical_context_to_real_raw_binding(self):
        f=self.fixture('real-cli-chain')
        f['result'].update(kernel_or_provider_executed=False,
            kernel_commit='55f042627bb7030c93550faafa117674d32b21d1',make_target='Image',
            integration_object='drivers/misc/note10_sha256_kat.o')
        f['linux']['image_producer']['result_sha256']=store(f['producer']/'result.json',f['result'])
        f['linux_sha']=store(f['linux_path'],f['linux'])
        ci=f['root']/'ci.json';ci_sha=store(ci,{})
        output=f['root']/'fresh-template'
        argv=[str(Path(reuse.__file__)), '--build',str(f['producer']),'--output',str(output),
            '--linux-receipt',str(f['linux_path']),'--linux-receipt-sha256',f['linux_sha'],
            '--current-receipt',str(f['host_path']),'--current-receipt-sha256',f['host_sha'],
            '--ci-success-context',str(ci),'--ci-success-context-sha256',ci_sha,'--host-source-head','b'*40]
        # Execute the actual script entry -> prepare_template -> raw_binding/type gate.
        # A deliberately absent artifact inventory stops immediately AFTER that gate;
        # there are no Image/carrier binaries, and no downstream gate is mocked out.
        with mock.patch.object(sys,'argv',argv):
            with self.assertRaises(KeyError) as stopped:
                runpy.run_path(str(Path(reuse.__file__)),run_name='__main__')
        self.assertEqual(stopped.exception.args,('files_sha256',))
        self.assertFalse(output.exists())


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--case',action='append',choices=CASE_IDS,required=True);a=p.parse_args();out=reuse.private(a.output)
    if out.exists() or len(a.case)!=len(set(a.case)):p.error('fresh private output and unique NEW cases required')
    out.mkdir(parents=True)
    result=unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(ReuseTests(n) for n in a.case))
    failed={t._testMethodName for t,_ in result.failures+result.errors if hasattr(t,'_testMethodName')};complete=result.testsRun==len(a.case)
    report=dict(kind='v97-new-host-reuse-tests',selected=a.case,tests_run=result.testsRun,
        passed=[n for n in a.case if n not in failed] if complete else [],failed=sorted(failed),
        success=result.wasSuccessful() and complete and not result.skipped,fixture_compiles=0,old_tests_executed=0,
        actual_Image_or_carrier_inputs=0,actual_payload_transforms=0,device_operations=[],
        source_sha256={n:reuse.sha((reuse.ROOT/'note10/device_test'/n).read_bytes()) for n in
            ('current_data_reuse.py','test_current_data_reuse.py','sha256_kat_device_profile.py','builtin_init_profile.py','linux_data_carrier.py')})
    store(out/'result.json',report);return 0 if report['success'] else 1
if __name__=='__main__':raise SystemExit(main())
