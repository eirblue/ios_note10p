"""Three new host-only fixed-span relation cases; no real artifact bytes/old suites."""
import argparse
import copy
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import early_fdt_binding as fdt
import builtin_init_profile as baseline
import sha256_kat_device_profile as profile

LINES={'CONFIG_NOTE10_EARLY_FDT_BINDING=y','CONFIG_HAVE_MEMBLOCK=y',
       'CONFIG_NO_BOOTMEM=y','CONFIG_ARM64_4K_PAGES=y'}


def synthetic(name=b'ccABC123.o'):
    elf=bytearray((i*17+11)&255 for i in range(1216))
    elf[fdt.TEMP_NAME_OFFSET:fdt.TEMP_NAME_OFFSET+10]=name
    elf[fdt.TEMP_NAME_OFFSET+10]=0
    archive=bytearray((i*13+7)&255 for i in range(2048))
    archive[fdt.INIT_PAYLOAD_OFFSET:fdt.INIT_PAYLOAD_OFFSET+len(elf)]=elf
    return bytes(elf),bytes(archive)


def measurements(elf,archive):
    raw=dict(minimal_init_elf_sha256=hashlib.sha256(elf).hexdigest(),
             initramfs_cpio_sha256=hashlib.sha256(archive).hexdigest())
    result=dict(raw,files_sha256={'minimal-init.elf':raw['minimal_init_elf_sha256'],
                                  'initramfs.cpio':raw['initramfs_cpio_sha256']})
    return result,raw


@contextmanager
def synthetic_pins():
    elf,archive=synthetic();start=fdt.TEMP_NAME_OFFSET;stop=start+10
    a=bytearray(elf);a[start:stop]=bytes(10)
    c=bytearray(archive);c[fdt.INIT_PAYLOAD_OFFSET+start:fdt.INIT_PAYLOAD_OFFSET+stop]=bytes(10)
    with patch.multiple(fdt,ELF_CANONICAL_SHA256=hashlib.sha256(a).hexdigest(),
                        CPIO_CANONICAL_SHA256=hashlib.sha256(c).hexdigest()), \
         patch.dict(fdt.ACCEPTED_BASELINE,{'config_sha256':fdt.placement_config_sha256(LINES)}):
        yield


def owned_producer(elf,archive):
    result,raw=measurements(elf,archive)
    result.update(version='v81',diagnostic_kind=fdt.KIND,raw_input_binding=False,
        fdt_capture_boundary=fdt.BOUNDARY,fdt_snapshot_capacity_bytes=fdt.CAPACITY,
        fdt_capture_revision=1,fdt_allocation_form=fdt.ALLOCATION,
        ci_context={'GITHUB_SHA':fdt.IMAGE_SOURCE_HEAD},image_sha256=fdt.IMAGE_SHA256,
        passed=True,Image_built=True,image_bytes=4096,
        fdt_snapshot_footprint=dict(snapshot_capacity_bytes=fdt.CAPACITY,allocation_form=fdt.ALLOCATION,
            snapshot_pointer_bytes=8,snapshot_state_bytes=25,linked_kernel_bytes=4096,
            image_text_offset=fdt.ACCEPTED_BASELINE['header']['text_offset'],
            image_flags=fdt.ACCEPTED_BASELINE['header']['flags']),
        source_sha256=dict(fdt.IMAGE_SOURCE_PINS),
        guarded_init_main_sha256=fdt.ACCEPTED_BASELINE['route_artifacts']['guarded_init_main_sha256'])
    result['source_sha256'].update(fdt.ACCEPTED_BASELINE['route_sources'])
    result['fdt_relative_placement']=fdt.relative_placement_admission(result,LINES,result['fdt_snapshot_footprint'])
    return result,raw


class HostRouteTests(unittest.TestCase):
    def test_fixed_filename_relation_read_only_and_current_payload(self):
        with synthetic_pins():
            hashes=[]
            for name in (b'ccABC123.o',b'ccZ9y8X7.o'):
                elf,archive=synthetic(name);result,raw=measurements(elf,archive)
                before=(elf,archive,copy.deepcopy(result),dict(raw))
                relation=fdt.fixed_route_relation(elf,archive,result,raw)
                self.assertEqual(relation['kind'],'fixed-nonloadable-STT_FILE-relation-v1')
                self.assertFalse(relation['raw_artifact_equality_claimed'])
                self.assertEqual((elf,archive,result,raw),before)
                hashes.append((relation['current_elf_sha256'],relation['current_cpio_sha256']))
            self.assertNotEqual(hashes[0],hashes[1])

    def test_code_header_layout_other_metadata_and_container_refused(self):
        with synthetic_pins():
            elf,archive=synthetic()
            variants=[]
            for offset in (0,64,fdt.TEMP_NAME_OFFSET-1,fdt.TEMP_NAME_OFFSET+11):
                altered=bytearray(elf);altered[offset]^=1
                container=bytearray(archive);container[fdt.INIT_PAYLOAD_OFFSET:fdt.INIT_PAYLOAD_OFFSET+1216]=altered
                variants.append((bytes(altered),bytes(container)))
            for name in (b'xxABC123.o',b'ccAB_123.o'):
                variants.append(synthetic(name))
            for offset in (0,6,2047):
                altered=bytearray(archive);altered[offset]^=1;variants.append((elf,bytes(altered)))
            variants.extend(((elf+b'0',archive),(elf,archive+b'0'),
                             (synthetic(b'ccZ9y8X7.o')[0],archive)))
            for first,second in variants:
                result,raw=measurements(first,second)
                with self.subTest(elf_bytes=len(first),cpio_bytes=len(second)):
                    with self.assertRaises(ValueError):fdt.fixed_route_relation(first,second,result,raw)

    def test_exact_raw_source_effective_admission_and_separate_host_head(self):
        with synthetic_pins():
            elf,archive=synthetic();result,raw=owned_producer(elf,archive)
            before=copy.deepcopy(result)
            bound=fdt.input_binding(result,LINES,elf=elf,archive=archive,raw_inputs=raw)
            self.assertEqual(result,before)
            self.assertFalse(result['fdt_relative_placement']['eligible'])
            effective=bound['fdt_effective_host_admission']
            self.assertTrue(effective['eligible']);self.assertFalse(effective['producer_reported_eligible'])
            self.assertFalse(effective['observed_runtime_base']);self.assertFalse(effective['absolute_FDT_extent_known'])
            for key,value in (('minimal_init_elf_sha256','0'*64),('initramfs_cpio_sha256','0'*64),('image_sha256','0'*64)):
                changed=copy.deepcopy(result);changed[key]=value
                with self.assertRaises(ValueError):fdt.input_binding(changed,LINES,elf=elf,archive=archive,raw_inputs=raw)
            changed=copy.deepcopy(result);changed['files_sha256']['minimal-init.elf']='0'*64
            with self.assertRaises(ValueError):fdt.input_binding(changed,LINES,elf=elf,archive=archive,raw_inputs=raw)
            changed=copy.deepcopy(result);changed['source_sha256'][next(iter(fdt.IMAGE_SOURCE_PINS))]='0'*64
            with self.assertRaises(ValueError):fdt.input_binding(changed,LINES,elf=elf,archive=archive,raw_inputs=raw)
            changed=copy.deepcopy(result);changed['ci_context']['GITHUB_SHA']='0'*40
            with self.assertRaises(ValueError):fdt.input_binding(changed,LINES,elf=elf,archive=archive,raw_inputs=raw)
            changed=copy.deepcopy(result);changed['fdt_relative_placement']['eligible']=True
            with self.assertRaises(ValueError):fdt.input_binding(changed,LINES,elf=elf,archive=archive,raw_inputs=raw)
            row={key:'a'*64 for key in (*profile.FIELDS,*baseline.EXTRA_FIELDS)}
            row.update(bound,device_profile=fdt.PROFILE,build_evidence_id='1'*32,
                kernel_banner='Linux version 4.14.113-v81-early-fdt synthetic-only',
                source_head=fdt.IMAGE_SOURCE_HEAD,**profile.host_binding('9'*40),
                auto_return_diagnostic=True,auto_cycle_token='2'*32,mode='diagnostic',test_purpose=fdt.KIND)
            profile.package_scope(row,'diagnostic')
            self.assertEqual(profile.host_binding(profile.V81_IMAGE_HEAD)['host_profile_source_sha256'],profile.V81_IMAGE_HOST_PINS)
            row.update(profile.host_binding(profile.V81_IMAGE_HEAD))
            with self.assertRaises(ValueError):profile.package_scope(row,'diagnostic')


CASE_NAMES=(
    'test_fixed_filename_relation_read_only_and_current_payload',
    'test_code_header_layout_other_metadata_and_container_refused',
    'test_exact_raw_source_effective_admission_and_separate_host_head',
)


class Recorded(unittest.TextTestResult):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs);self.failed_methods=set();self.framework_errors=[]
    def addFailure(self,test,error):
        self.failed_methods.add(test._testMethodName);super().addFailure(test,error)
    def addError(self,test,error):
        if isinstance(test,HostRouteTests):self.failed_methods.add(test._testMethodName)
        else:self.framework_errors.append(test.id())
        super().addError(test,error)
    def addSubTest(self,test,subtest,error):
        if error is not None:self.failed_methods.add(test._testMethodName)
        super().addSubTest(test,subtest,error)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True)
    parser.add_argument('--case',action='append',choices=CASE_NAMES)
    args=parser.parse_args();selected=args.case or list(CASE_NAMES)
    if len(selected)!=len(set(selected)):parser.error('duplicate new case selection')
    output=profile.private(args.output);output.mkdir(parents=True,exist_ok=False)
    result=unittest.TextTestRunner(verbosity=2,resultclass=Recorded).run(unittest.TestSuite(HostRouteTests(name) for name in selected))
    failed=sorted(result.failed_methods)
    passed=[name for name in selected if name not in failed] if result.testsRun==len(selected) and not result.framework_errors else []
    names=('early_fdt_binding.py','builtin_init_profile.py','sha256_kat_device_profile.py',Path(__file__).name)
    here=Path(__file__).parent
    receipt=dict(kind='v81-revision2-new-host-only-route-cases',selected=selected,passed=passed,failed=failed,
        tests_run=result.testsRun,framework_errors=result.framework_errors,old_suites_executed=0,
        compiler_calls=0,Image_readers=0,CI_calls=0,device_calls=0,
        source_sha256={name:hashlib.sha256((here/name).read_bytes()).hexdigest() for name in names},
        success=result.wasSuccessful() and result.testsRun==len(selected) and not result.skipped)
    (output/'result.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    return 0 if receipt['success'] else 1


if __name__=='__main__':
    raise SystemExit(main())
