"""Three new receipt/geometry/composition paths; no compiled decoder or old suite runs."""
import argparse
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import prepare_fresh_current_carrier as fresh

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
CASE_IDS=('test_current_receipt_context_and_historical_decoder_binding',
          'test_fresh_zero_tail_carrier_and_capacity_relation',
          'test_geometry_fit_failure_and_fresh_output_refusals')


def store(path, value):
    raw=(json.dumps(value,indent=2)+'\n').encode();path.write_bytes(raw)
    return fresh.sha(raw)


class ControlledDecoder:
    def __init__(self,payload):
        self.payload=payload;self.calls=0;self.sha256='a'*64
    def decode(self,stream,expected_bytes):
        self.calls+=1
        return dict(status=0,reported_status=0,version=1,consumed=len(stream),written=len(self.payload)),self.payload


class FreshCarrierTests(unittest.TestCase):
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory(prefix='v95-new-synthetic-',dir=ROOT/'note10/private')
        self.addCleanup(self.temporary.cleanup);self.root=Path(self.temporary.name)
    def fixture(self,name):
        root=self.root/name;root.mkdir();producer=root/'producer';producer.mkdir()
        page=fresh.PAGE;base=0xfffffff000000000
        raw=b'T'*64+b'D'*page
        (producer/'current-native.macho').write_bytes(raw)
        ci=dict(GITHUB_SHA='1'*40,GITHUB_RUN_ID='101',GITHUB_RUN_ATTEMPT='1',
            GITHUB_JOB='current-native-selected-link',GITHUB_REPOSITORY='eirblue/ios_note10p',
            GITHUB_WORKFLOW_REF='eirblue/ios_note10p/'+fresh.WORKFLOW+'@refs/heads/main',GITHUB_WORKFLOW_SHA='1'*40)
        component={'exynos_checked_ptpage.c':'3'*64,'prepare_exynos_checked_ptpage.py':'4'*64,
            'patches/0013-exynos9825-checked-dynamic-ptpage.patch':'5'*64}
        prod=dict(candidate_kind=fresh.KIND,source_commit='1'*40,ci_context=ci,public_source_commit='2'*40,
            configuration='DEVELOPMENT_ARM64_EXYNOS9825',fresh_work_root='/synthetic/fresh',
            recipe_sha256={k:v for k,v in component.items() if not k.startswith('patches/')},
            patch_sha256={'0013-exynos9825-checked-dynamic-ptpage.patch':'5'*64})
        bindings={'config':'6'*64}
        context=dict(kind='v84-current-native',producer=prod,bindings=bindings,
            producer_id=fresh.digest(prod),input_binding=fresh.digest(bindings))
        pool=dict(segment='__DATA',address=base+3*page,bytes=10*page,alignment_log2=14,flags=1,
            segment_start=base+2*page,segment_end=base+13*page,segment_protection=3,segment_maximum_protection=3)
        result=dict(kind=fresh.KIND,phase='complete',passed=True,ci_context=ci,public_source_commit='2'*40,
            producer_id=context['producer_id'],input_binding=context['input_binding'],candidate_archive_used=False,
            architecture='arm64',mach_o_type='MH_EXECUTE',undefined_symbols=[],old_suites_executed=0,
            PC_only=True,physical_ready=False,deployment_ready=False,hardware_verified=False,
            whole_XNU_kernel_entry_executed=False,hardware_XNU_executed=False,device_operations=[],
            output_bytes=len(raw),output_sha256=fresh.sha(raw),memory_image_virtual_base=hex(base),
            memory_image_span_bytes=13*page,entry_virtual_address=hex(base+4),entry_offset=4,
            bootstrap_pool_relative_offset=3*page,bootstrap_pool=pool,
            segments=[dict(name='__TEXT',virtual_address=base,virtual_size=page,file_offset=0,file_size=64,initial_protection=5),
                dict(name='__DATA',virtual_address=base+2*page,virtual_size=11*page,file_offset=64,file_size=page,initial_protection=3)],
            link=dict(producer_id=context['producer_id'],input_binding=context['input_binding'],attempted=True,
                link_succeeded=True,returncode=0,candidate_archive_used=False))
        result_path=producer/'result.json';result_sha=store(result_path,result)
        context_path=producer/'producer-context.json';context_sha=store(context_path,context)
        accepted={k:result[k] for k in ('kind','phase','passed','producer_id','input_binding',
            'memory_image_virtual_base','memory_image_span_bytes','entry_virtual_address','entry_offset',
            'bootstrap_pool_relative_offset','bootstrap_pool')}
        accepted.update(result_path=str(result_path),result_sha256=result_sha,
            producer_declared_output_bytes=len(raw),producer_declared_output_sha256=fresh.sha(raw))
        receipt=dict(schema=fresh.RECEIPT_SCHEMA,
            source_binding=dict(project_source_commit='1'*40,underlying_public_xnu_commit='2'*40,test_source_component_pins=component),
            workflow=dict(head_sha='1'*40,conclusion='success',event='workflow_dispatch',workflow_path=fresh.WORKFLOW,
                job_name='current-native-selected-link',run_id=101,attempt=1),new_xnu_producer=accepted)
        receipt_path=root/'receipt.json';receipt_sha=store(receipt_path,receipt)
        binding=dict(schema=fresh.BINDING_SCHEMA,accepted_ci_receipt_path=str(receipt_path),
            accepted_ci_receipt_sha256=receipt_sha,producer_result_path=str(result_path),
            producer_result_sha256_reused_from_accepted_receipt=result_sha,
            producer_context_path=str(context_path),producer_context_sha256=context_sha)
        binding_path=root/'binding.json';binding_sha=store(binding_path,binding)
        expected=bytearray(13*page);expected[:64]=raw[:64];expected[2*page:3*page]=raw[64:]
        return dict(root=root,producer=producer,binding=binding,binding_path=binding_path,binding_sha=binding_sha,
            context=context,context_path=context_path,result=result,receipt=receipt,payload=bytes(expected))
    def historical(self,root):
        tests=root/'historical-tests';tests.mkdir()
        pins={'old-header':'7'*64,'old-core':'8'*64}
        compiled=dict(returncode=0,dll_file='carrier_lzma.dll',dll_sha256='a'*64)
        test=dict(kind='current-data-carrier-new-tests',success=True,selected=list(fresh.carrier.CASE_NAMES),
            passed=list(fresh.carrier.CASE_NAMES),failed=[],tests_run=6,fixture_compiles=1,source_sha256=pins,compiled=compiled)
        test_sha=store(tests/'result.json',test)
        names=['CurrentDataCarrierTests.'+n for n in fresh.carrier.CASE_NAMES]
        receipt=dict(schema='v87-host-operator-receipt-v1',source_pins=pins,
            selected_batch=dict(result_path='historical-tests/result.json',result_sha256=test_sha,
                selected_method_ids=names,passed_method_ids=names,failed_count=0,tests_run=6),
            compiler=dict(successful_C_compilations=1,corrected_attempt=dict(dll_sha256='a'*64)))
        p=root/'historical.json';return p,store(p,receipt)
    def args(self,f,output='out'):
        decoder_receipt,decoder_sha=self.historical(f['root'])
        return dict(input_binding=f['binding_path'],input_binding_sha256=f['binding_sha'],
            decoder_receipt=decoder_receipt,decoder_receipt_sha256=decoder_sha,output=f['root']/output)
    def test_current_receipt_context_and_historical_decoder_binding(self):
        f=self.fixture('valid');self.assertEqual(fresh.current_inputs(f['binding_path'],f['binding_sha'])[2]['kind'],fresh.KIND)
        p,pin=self.historical(f['root']);decoder=ControlledDecoder(f['payload'])
        with mock.patch.object(fresh.carrier,'Decoder',return_value=decoder) as constructor:
            got,binding=fresh.historical_decoder(p,pin)
        self.assertIs(got,decoder)
        self.assertTrue(binding['live_header_is_not_compiled_input'])
        constructor.assert_called_once_with(p.parent/'historical-tests/carrier_lzma.dll','a'*64)
        for i,change in enumerate(('kind','run','source')):
            f=self.fixture('foreign'+str(i));context=f['context']
            if change=='kind':context['producer']['candidate_kind']='v93-exynos-leaf-bootstrap-pc'
            if change=='run':context['producer']['ci_context']['GITHUB_RUN_ID']='102'
            if change=='source':context['producer']['source_commit']='9'*40
            f['binding']['producer_context_sha256']=store(f['context_path'],context)
            pin=store(f['binding_path'],f['binding'])
            with mock.patch.object(fresh,'bounded_read',side_effect=AssertionError('kernel must not be read')):
                with self.assertRaises(ValueError):fresh.current_inputs(f['binding_path'],pin)
        f=self.fixture('selfapproved');f['binding'].pop('accepted_ci_receipt_sha256');f['binding']['root_reviewed']=True
        pin=store(f['binding_path'],f['binding'])
        with self.assertRaises((ValueError,KeyError)):fresh.current_inputs(f['binding_path'],pin)
    def test_fresh_zero_tail_carrier_and_capacity_relation(self):
        f=self.fixture('functional');args=self.args(f);decoder=ControlledDecoder(f['payload'])
        with mock.patch.object(fresh,'historical_decoder',return_value=(decoder,{'historical':True})), \
             mock.patch.object(fresh,'materialize_kernel',wraps=fresh.materialize_kernel) as materialize, \
             mock.patch.object(fresh,'bounded_read',wraps=fresh.bounded_read) as kernel_read, \
             mock.patch.object(fresh.lzma,'compress',wraps=fresh.lzma.compress) as compress:
            report=fresh.prepare(**args)
        self.assertTrue(report['accepted']);self.assertFalse(report['physical_ready'])
        self.assertFalse(report['linux_current_capacity_match'])
        self.assertEqual((decoder.calls,materialize.call_count,kernel_read.call_count,compress.call_count),(1,1,1,1))
        self.assertEqual((args['output']/'kernel.mem').read_bytes(),f['payload'])
        manifest=json.loads((args['output']/'payload-fit.json').read_text())
        self.assertEqual(manifest['payload_bytes'],f['result']['memory_image_span_bytes'])
        self.assertEqual(manifest['entry_offset'],4)
        self.assertEqual((args['output']/'carrier/carrier.data').stat().st_size,fresh.BUDGET)
        with mock.patch.object(fresh,'current_inputs',side_effect=AssertionError('no replay')):
            with self.assertRaises(ValueError):fresh.prepare(**args)
    def test_geometry_fit_failure_and_fresh_output_refusals(self):
        f=self.fixture('badgeometry')
        for field,value in (('memory_image_span_bytes',14*fresh.PAGE),('entry_offset',8),
                            ('bootstrap_pool_relative_offset',2*fresh.PAGE)):
            result=copy.deepcopy(f['result']);result[field]=value
            with self.assertRaises(ValueError):fresh.pool_geometry(result)
        result=copy.deepcopy(f['result']);result['bootstrap_pool']['address']=result['segments'][1]['virtual_address']
        with self.assertRaises(ValueError):fresh.pool_geometry(result)
        f=self.fixture('fit');args=self.args(f)
        with mock.patch.object(fresh,'BUDGET',256),mock.patch.object(fresh.lzma,'compress',return_value=b'x'*256), \
             mock.patch.object(fresh,'historical_decoder',side_effect=AssertionError('no decode on failed fit')):
            report=fresh.prepare(**args)
        self.assertFalse(report['accepted']);self.assertFalse(report['fits_budget']);self.assertEqual(report['decoder_calls'],0)
        self.assertTrue((args['output']/'kernel.mem').is_file())
        self.assertTrue((args['output']/'kernel.mem.lzma').is_file())
        self.assertFalse((args['output']/'carrier').exists())
        f=self.fixture('changedinput');args=self.args(f)
        p=f['producer']/'current-native.macho';p.write_bytes(b'!'+p.read_bytes()[1:])
        with self.assertRaises(ValueError):fresh.prepare(**args)
        self.assertFalse(args['output'].exists())


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--case',action='append',choices=CASE_IDS,required=True);a=p.parse_args()
    out=fresh.private(a.output)
    if out.exists() or len(a.case)!=len(set(a.case)):p.error('fresh private output and unique new cases required')
    out.mkdir(parents=True)
    result=unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(FreshCarrierTests(n) for n in a.case))
    failed={t._testMethodName for t,_ in result.failures+result.errors}
    complete=result.testsRun==len(a.case)
    report=dict(kind='v95-new-host-adapter-tests',selected=a.case,tests_run=result.testsRun,
        passed=[n for n in a.case if n not in failed] if complete else [],failed=sorted(failed),
        success=result.wasSuccessful() and complete and not result.skipped,fixture_compiles=0,
        actual_compiled_decoder_calls=0,old_tests_executed=0,actual_payload_inputs=0,
        source_sha256={n:fresh.sha((HERE/n).read_bytes()) for n in
            ('prepare_fresh_current_carrier.py','test_fresh_current_carrier.py')},PC_only=True,
        physical_ready=False,whole_XNU_kernel_entry_executed=False,hardware_XNU_executed=False,device_operations=[])
    fresh.write_json(out/'result.json',report)
    return 0 if report['success'] else 1
if __name__=='__main__':raise SystemExit(main())
