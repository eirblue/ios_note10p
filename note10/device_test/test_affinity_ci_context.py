"""Only new host CI-context receipt integration; no v78 diagnostic suite replay."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import sha256_kat_device_profile as profile

SOURCE='1'*40
BANNER='Linux version 4.14.113-v78-cpu-affinity synthetic-package-binding'


def fixture():
    context=dict(schema=1,kind=profile.AFFINITY_PROFILE+'-ci-success-context',accepted=True,
        producer_source_head=SOURCE,ci_result_sha256='a'*64,image_sha256='b'*64,image_bytes=4096,
        effective_config_sha256='c'*64,build_evidence_id='2'*32,run_id=17,attempt=1,
        workflow_id=23,job_id=29,artifact_id=31,artifact_zip_sha256='d'*64,artifact_zip_bytes=1024)
    binding=dict(device_profile=profile.AFFINITY_PROFILE,source_head=SOURCE,accepted_result_sha256='a'*64,
        image_sha256='b'*64,image_size=4096,effective_config_sha256='c'*64,
        build_evidence_id='2'*32,kernel_banner=BANNER)
    producer=dict(version='v78',diagnostic_kind='cpu-affinity-binding',passed=True,Image_built=True,
        image_sha256='b'*64,image_bytes=4096,build_evidence_id='2'*32,
        files_sha256={'actual-effective.config':'c'*64},
        ci_context={'GITHUB_SHA':SOURCE,'GITHUB_RUN_ID':'17','GITHUB_RUN_ATTEMPT':'1','GITHUB_JOB':'cpu-affinity-binding'})
    raw=(json.dumps(context,sort_keys=True)+'\n').encode()
    return context,hashlib.sha256(raw).hexdigest(),binding,producer


class CiContextTests(unittest.TestCase):
    def test_approved_context_uses_package_banner_and_atomic_legacy_receipt(self):
        context,digest,binding,producer=fixture()
        self.assertNotIn('kernel_banner',context)
        receipt=profile.ci_success_receipt(context,digest,binding,producer)
        self.assertEqual(receipt['kernel_banner'],BANNER)
        self.assertEqual(receipt['root_reader_result_sha256'],digest)
        with tempfile.TemporaryDirectory(prefix='v78-ci-context-',dir=profile.ROOT/'note10/private') as scratch:
            out=Path(scratch)
            (out/'result.json').write_text(json.dumps(producer),encoding='utf-8')
            fields=profile.write_ci_success_receipt(out,receipt)
            self.assertEqual(fields,profile.root_receipt_binding(out,out/'image-root-receipt.json',
                fields['image_root_receipt_sha256'],binding))
            self.assertEqual(profile.read(out/'image-root-receipt.json'),receipt)
            self.assertFalse((out/'.image-root-receipt.json.tmp').exists())

    def test_context_tuple_rejections_and_fresh_output(self):
        context,digest,binding,producer=fixture()
        mutations=(('producer_source_head','3'*40),('run_id',18),('attempt',2),
            ('effective_config_sha256','e'*64),('accepted',False),('accepted',1),('schema',True),
            ('ci_result_sha256','e'*64),('image_sha256','e'*64),('image_bytes',4097),
            ('build_evidence_id','4'*32),('run_id',True),('artifact_zip_sha256','bad'))
        with tempfile.TemporaryDirectory(prefix='v78-ci-context-reject-',dir=profile.ROOT/'note10/private') as scratch:
            out=Path(scratch)
            for key,value in mutations:
                changed=copy.deepcopy(context);changed[key]=value
                with self.subTest(key=key,value=value):
                    with self.assertRaises(ValueError):
                        receipt=profile.ci_success_receipt(changed,digest,binding,producer)
                        profile.write_ci_success_receipt(out,receipt)
                    self.assertFalse((out/'image-root-receipt.json').exists())
            changed=dict(context,kernel_banner='invented')
            with self.assertRaises(ValueError):profile.ci_success_receipt(changed,digest,binding,producer)
            other=dict(binding,device_profile=profile.STREAM_PROFILE)
            with self.assertRaises(ValueError):profile.ci_success_receipt(context,digest,other,producer)
            altered=copy.deepcopy(producer);altered['ci_context']['GITHUB_RUN_ID']='99'
            with self.assertRaises(ValueError):profile.ci_success_receipt(context,digest,binding,altered)
            receipt=profile.ci_success_receipt(context,digest,binding,producer)
            profile.write_ci_success_receipt(out,receipt)
            original=(out/'image-root-receipt.json').read_bytes()
            with self.assertRaises(ValueError):profile.write_ci_success_receipt(out,receipt)
            self.assertEqual((out/'image-root-receipt.json').read_bytes(),original)


CASE_NAMES=('test_approved_context_uses_package_banner_and_atomic_legacy_receipt',
            'test_context_tuple_rejections_and_fresh_output')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True)
    parser.add_argument('--case',action='append',choices=CASE_NAMES,required=True)
    args=parser.parse_args()
    if len(args.case)!=len(set(args.case)):parser.error('duplicate host-only case selection')
    output=profile.private(args.output);output.mkdir(parents=True,exist_ok=False)
    result=unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(CiContextTests(name) for name in args.case))
    failed=[test.id() for test,_ in result.failures];errors=[test.id() for test,_ in result.errors]
    passed=not failed and not errors and not result.skipped and result.testsRun==len(args.case)
    sources=(Path(__file__),Path(profile.__file__))
    receipt=dict(kind='v78-host-only-ci-success-context',selected=args.case,tests_run=result.testsRun,
        success=passed,failed=failed,errors=errors,old_v78_methods_executed=0,Image_builds=0,device_calls=0,
        source_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sources})
    (output/'result.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    return 0 if passed else 1


if __name__=='__main__':
    raise SystemExit(main())
