"""v81 revision1: changed allocator/boundary/placement cases only; initial pass preserved."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from contextlib import contextmanager

import early_fdt_binding as fdt
import builtin_init_profile as baseline
import sha256_kat_device_profile as profile
from decode_reservation import checksum

HERE = Path(__file__).resolve().parent
ID, CYCLE, BOOT, SOURCE = '1'*32, '2'*32, '3'*32, '4'*40
BANNER = 'Linux version 4.14.113-v81-early-fdt synthetic-only'
SETUP = b"""void __init setup_arch(char **cmdline_p)
{
\t(void)cmdline_p;
\tarm64_memblock_init();
\tpaging_init();
\tsetup_order = 3;
}
"""
LINES = {'CONFIG_NOTE10_EARLY_FDT_BINDING=y','CONFIG_HAVE_MEMBLOCK=y',
         'CONFIG_NO_BOOTMEM=y','CONFIG_ARM64_4K_PAGES=y'}


@contextmanager
def matching_config():
    with patch.dict(fdt.ACCEPTED_BASELINE,{'config_sha256':fdt.placement_config_sha256(LINES)}):
        yield


def footprint():
    system='1000 T _text\n2000 B __bss_start\n3000 b n10_fdt_snapshot\n4000 B __bss_stop\n5000 B _end\n'
    symbols='00000000 00000008 b n10_fdt_snapshot\n00000008 00000010 b n10_fdt_other_state\n'
    return fdt.linked_footprint(system,symbols,0x4000,
        fdt.ACCEPTED_BASELINE['header']['text_offset'],fdt.ACCEPTED_BASELINE['header']['flags'])



def body(status='ok', length=64, digest=None, error=0):
    digest = ('c'*64 if status=='ok' else 'none') if digest is None else digest
    return (f'id={ID} cycle={CYCLE} boundary=post_paging_reservations status={status} error={error} '
            f'length={length} sha256={digest} raw_binding=0')


def frame(value=None, boot=BOOT, marker='N10FDT1'):
    value = body() if value is None else value
    return f'N10BOOTLINK2 boot={boot} {marker} {value} checksum={checksum(value.encode()):08x}\n'


def associated(payload=None):
    def ret(phase):
        return ''.join(frame(f'id={ID} cycle={CYCLE} phase={phase} seq={seq} delay_ms=90000 status=0',marker='N10RET1') for seq in (0,1))
    startup = (f'N10ROUTE2 id={ID} boot={BOOT} cycle={CYCLE} route=builtin exec_attempt=1\n'
               f'N10INIT2 id={ID} boot={BOOT} cycle={CYCLE} route=builtin started=1\n')
    return ('[    0.000000] '+BANNER+'\n'+ret(0)+startup+(frame() if payload is None else payload)+ret(1)).encode()


def producer():
    result=dict(version='v81',diagnostic_kind=fdt.KIND,raw_input_binding=False,
        fdt_capture_boundary=fdt.BOUNDARY,fdt_snapshot_capacity_bytes=fdt.CAPACITY,
        fdt_capture_revision=fdt.REVISION,fdt_allocation_form=fdt.ALLOCATION,
        fdt_snapshot_footprint=footprint(),image_bytes=4096,
        source_sha256={'note10/device_test/'+name:hashlib.sha256((HERE/name).read_bytes()).hexdigest() for name in fdt.SOURCES},
        **fdt.ACCEPTED_BASELINE['route_artifacts'])
    result['source_sha256'].update(fdt.ACCEPTED_BASELINE['route_sources'])
    result['fdt_relative_placement']=fdt.relative_placement_admission(result,LINES,result['fdt_snapshot_footprint'])
    return result



class EarlyFdtTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        parent=profile.ROOT/'note10/private';parent.mkdir(parents=True,exist_ok=True)
        cls.scratch=tempfile.TemporaryDirectory(prefix='v81-new-',dir=parent)
        cls.work=Path(cls.scratch.name);cls.executables={};cls.compile_commands=[]

    @classmethod
    def tearDownClass(cls):
        cls.scratch.cleanup()

    @classmethod
    def native(cls, case, enabled=True):
        if enabled not in cls.executables:
            cc=shutil.which('cc')
            if not cc:raise RuntimeError('native C compiler required for NEW snapshot fixture')
            pin=hashlib.sha256(SETUP).hexdigest()
            with patch.dict(fdt.API_PINS,{'arch/arm64/kernel/setup.c':pin}):
                (cls.work/'test-setup.c').write_bytes(fdt.overlay_setup(SETUP))
            binary=cls.work/('fixture-enabled' if enabled else 'fixture-default-off')
            command=[cc,'-std=gnu11','-O1','-Wall','-Wextra','-Werror','-I'+str(HERE),'-I'+str(cls.work),
                     *(('-DCONFIG_NOTE10_EARLY_FDT_BINDING=1',) if enabled else ()),
                     str(HERE/'early_fdt_fixture.c'),'-o',str(binary)]
            result=subprocess.run(command,capture_output=True,timeout=60)
            cls.compile_commands.append(command)
            if result.returncode:raise AssertionError(result.stderr.decode(errors='replace'))
            cls.executables[enabled]=binary
        result=subprocess.run([str(cls.executables[enabled]),case],capture_output=True,timeout=30)
        if result.returncode:raise AssertionError(result.stderr.decode(errors='replace'))
        lines=result.stdout.decode('ascii').splitlines()
        return fdt.decode(lines[0],ID,CYCLE),json.loads(lines[1])

    def test_owned_snapshot_late_hash_and_clear(self):
        observed,row=self.native('ordinary')
        self.assertTrue(observed['passed']);self.assertEqual(observed['length'],64)
        self.assertEqual(observed['capture_boundary'],'post_paging_reservations')
        self.assertEqual(observed['sha256'],bytes((448+i)&255 for i in range(32)).hex())
        self.assertEqual(row,dict(copies=1,allocations=1,hashes=1,verified=1,crc_calls=1,cleared=1,
            memblock_calls=1,memblock_bytes=4096,setup_order=3))
        self.assertFalse(observed['raw_input_binding']);self.assertFalse(observed['pristine_firmware_claimed'])
        with self.assertRaises(ValueError):
            fdt.decode(frame(body().replace('post_paging_reservations','post_arch_crc')),ID,CYCLE)


    def test_capture_header_cap_and_oversize_refusal_preserve_admission(self):
        for name,length in (('minimum',40),('maximum',fdt.CAPACITY)):
            with self.subTest(case=name):
                observed,row=self.native(name);self.assertEqual(observed['length'],length)
                self.assertEqual(row['memblock_calls'],1);self.assertEqual(row['memblock_bytes'],(length+4095)//4096*4096)
                self.assertEqual(row['cleared'],1);self.assertEqual(row['verified'],1)
        for name in ('short','oversized'):
            observed,row=self.native(name);self.assertEqual(observed['status'],'refused')
            self.assertEqual(row,dict(copies=0,allocations=0,hashes=0,verified=1,crc_calls=1,cleared=1,
                memblock_calls=0,memblock_bytes=0,setup_order=3))


    def test_post_paging_overlay_invalid_input_and_default_off_admission(self):
        for case in ('null','invalid-header'):
            observed,row=self.native(case);self.assertEqual(observed['status'],'unavailable')
            self.assertEqual(row,dict(copies=0,allocations=0,hashes=0,verified=0,crc_calls=0,cleared=1,
                memblock_calls=0,memblock_bytes=0,setup_order=0))
        observed,row=self.native('ordinary',False)
        self.assertEqual(observed['status'],'unavailable')
        self.assertEqual(row,dict(copies=0,allocations=0,hashes=0,verified=1,crc_calls=1,cleared=1,
            memblock_calls=0,memblock_bytes=0,setup_order=3))
        with self.assertRaises(ValueError):fdt.overlay_setup(SETUP)


    def test_repeat_ambiguous_retains_first_then_clears_without_hash(self):
        observed,row=self.native('repeat');self.assertEqual(observed['status'],'ambiguous')
        self.assertFalse(observed['passed']);self.assertIsNone(observed['sha256'])
        self.assertEqual(row,dict(copies=1,allocations=0,hashes=0,verified=1,crc_calls=1,cleared=1,
            memblock_calls=1,memblock_bytes=4096,setup_order=3))


    def test_late_provider_alloc_and_hash_failures_clear_snapshot(self):
        for number,error in ((1,-2),(2,-22),(3,-22),(4,-7),(5,-12),(6,-5)):
            with self.subTest(failure=number):
                observed,row=self.native('hash-failure-'+str(number))
                self.assertEqual(observed['status'],'hash_error');self.assertEqual(observed['error'],error)
                self.assertEqual(observed['length'],0);self.assertIsNone(observed['sha256'])
                self.assertEqual(row['memblock_calls'],1);self.assertEqual(row['memblock_bytes'],4096)
                self.assertEqual(row['copies'],1);self.assertEqual(row['allocations'],1)
                self.assertEqual(row['hashes'],int(number==6));self.assertEqual(row['cleared'],1)





    def test_new_producer_kind_config_source_and_boundary_binding(self):
        with matching_config():
            row=producer()
            bound=fdt.input_binding(row,LINES)
            self.assertEqual(bound['fdt_capture_revision'],1);self.assertEqual(bound['fdt_allocation_form'],'memblock-owned')
            self.assertTrue(bound['fdt_relative_placement_admitted']);self.assertFalse(bound['raw_input_binding'])
            for key,value in (('fdt_capture_revision',0),('fdt_capture_revision',True),('fdt_capture_boundary','post_arch_crc'),
                              ('fdt_allocation_form','fixed-bss'),('raw_input_binding',True)):
                changed=copy.deepcopy(row);changed[key]=value
                with self.assertRaises(ValueError):fdt.input_binding(changed,LINES)
            changed=copy.deepcopy(row);changed['source_sha256']['note10/device_test/early_fdt_binding.c']='0'*64
            with self.assertRaises(ValueError):fdt.input_binding(changed,LINES)
            for config in (LINES-{'CONFIG_NO_BOOTMEM=y'},LINES|{'CONFIG_NOTE10_CPU_AFFINITY_BINDING=y'}):
                with self.assertRaises(ValueError):fdt.input_binding(row,config)


    def test_tiny_linked_state_and_retained_baseline_extent(self):
        with matching_config():
            result=producer();observed=result['fdt_snapshot_footprint']
            self.assertEqual(observed['snapshot_pointer_bytes'],8);self.assertEqual(observed['snapshot_state_bytes'],24)
            accepted=fdt.relative_placement_admission(result,LINES,observed)
            self.assertTrue(accepted['eligible']);self.assertFalse(accepted['observed_runtime_base'])
            self.assertFalse(accepted['absolute_FDT_extent_known']);self.assertFalse(accepted['global_RAM_ownership'])
            for size in (fdt.ACCEPTED_BASELINE['linked_kernel_bytes'],fdt.ACCEPTED_BASELINE['linked_kernel_bytes']+4096):
                changed=dict(observed,linked_kernel_bytes=size)
                admitted=fdt.relative_placement_admission(result,LINES,changed)
                self.assertEqual(admitted['eligible'],size==fdt.ACCEPTED_BASELINE['linked_kernel_bytes'])
            for size in (fdt.ACCEPTED_BASELINE['image_file_bytes'],fdt.ACCEPTED_BASELINE['image_file_bytes']+1):
                changed=dict(result,image_bytes=size)
                self.assertEqual(fdt.relative_placement_admission(changed,LINES,observed)['eligible'],size==fdt.ACCEPTED_BASELINE['image_file_bytes'])
        system='1000 T _text\n2000 B __bss_start\n3000 b n10_fdt_snapshot\n4000 B __bss_stop\n5000 B _end\n'
        with self.assertRaises(ValueError):fdt.linked_footprint(system,'0000 00080000 b n10_fdt_snapshot\n',0x4000,0,0)



    def test_new_package_scope_label_and_exact_v78_predecessor(self):
        row={key:'a'*64 for key in (*profile.FIELDS,*baseline.EXTRA_FIELDS)}
        row.update(device_profile=fdt.PROFILE,build_evidence_id=ID,kernel_banner=BANNER,source_head=SOURCE,
            **profile.host_binding(SOURCE),fdt_capture_boundary=fdt.BOUNDARY,fdt_snapshot_capacity_bytes=fdt.CAPACITY,
            raw_input_binding=False,fdt_capture_revision=1,fdt_allocation_form=fdt.ALLOCATION,
            fdt_relative_placement_admitted=True,auto_return_diagnostic=True,auto_cycle_token=CYCLE,mode='diagnostic',test_purpose=fdt.KIND)
        profile.package_scope(row,'diagnostic');self.assertFalse(profile.fields(row)['raw_input_binding'])
        from build_boot_test_packages import updater
        partitions=[dict(partition=name,block_node=f'/dev/block/sda{i}',size=4096,sha256='a'*64)
                    for i,name in enumerate(('boot','recovery','dtb','dtbo','vbmeta'),1)]
        script=updater(mode='diagnostic',bootloader='N976NTEST',partitions=partitions,payload_sha='b'*64,
            current_boot_sha='a'*64,auto_return=True,device_profile=fdt.PROFILE)
        self.assertIn(b'Temporary Linux early FDT snapshot diagnostic; not iOS/XNU.',script)
        pair=dict(device_profile=profile.AFFINITY_PROFILE,source_head='24f0fb9c4680517d6b0411a9985847c42b692376',
                  host_profile_source_head=profile.V78_HOST_HEAD)
        plan=dict(device_profile=fdt.PROFILE,current_boot_payload_sha256='a'*64)
        baseline.current_boot_binding(plan,pair,{'payload_sha256':'a'*64})
        for key,value in (('source_head','0'*40),('host_profile_source_head',SOURCE),('device_profile',profile.STREAM_PROFILE)):
            changed=dict(pair);changed[key]=value
            with self.assertRaises(ValueError):baseline.current_boot_binding(plan,changed,{'payload_sha256':'a'*64})
        for key,value in (('raw_input_binding',True),('fdt_capture_boundary','pristine'),('test_purpose','cpu-affinity-binding')):
            changed=dict(row);changed[key]=value
            with self.assertRaises(ValueError):profile.package_scope(changed,'diagnostic')

    def test_memblock_exhaustion_unavailable_without_hash_or_release(self):
        observed,row=self.native('memblock-failure')
        self.assertEqual(observed['status'],'unavailable');self.assertFalse(observed['passed'])
        self.assertEqual(row,dict(copies=0,allocations=0,hashes=0,verified=1,crc_calls=1,cleared=1,
            memblock_calls=1,memblock_bytes=4096,setup_order=3))

    def test_relative_load_config_header_and_route_mismatch_block(self):
        with matching_config():
            result=producer();observed=result['fdt_snapshot_footprint']
            variants=[]
            for key in ('image_text_offset','image_flags'):
                changed=dict(observed);changed[key]^=1;variants.append((result,LINES,changed))
            changed=copy.deepcopy(result);changed['source_sha256']['note10/device_test/auto_return.c']='0'*64
            variants.append((changed,LINES,observed))
            changed=copy.deepcopy(result);changed['initramfs_cpio_sha256']='0'*64;variants.append((changed,LINES,observed))
            variants.append((result,LINES|{'CONFIG_RANDOMIZE_BASE=n'},observed))
            for candidate,config,linked in variants:
                admission=fdt.relative_placement_admission(candidate,config,linked)
                self.assertFalse(admission['eligible'])
            # Generated paths and diagnostic selection are the only config exclusions.
            config=LINES|{'CONFIG_LOCALVERSION="synthetic"','CONFIG_INITRAMFS_SOURCE="/synthetic/initramfs.cpio"'}
            self.assertTrue(fdt.relative_placement_admission(result,config,observed)['eligible'])


CASE_NAMES = ('test_owned_snapshot_late_hash_and_clear', 'test_capture_header_cap_and_oversize_refusal_preserve_admission', 'test_post_paging_overlay_invalid_input_and_default_off_admission', 'test_repeat_ambiguous_retains_first_then_clears_without_hash', 'test_late_provider_alloc_and_hash_failures_clear_snapshot', 'test_new_producer_kind_config_source_and_boundary_binding', 'test_tiny_linked_state_and_retained_baseline_extent', 'test_new_package_scope_label_and_exact_v78_predecessor', 'test_memblock_exhaustion_unavailable_without_hash_or_release', 'test_relative_load_config_header_and_route_mismatch_block')


class Recorded(unittest.TextTestResult):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs);self.failed_methods=set();self.framework_errors=[]
    def addFailure(self,test,error):
        self.failed_methods.add(test._testMethodName);super().addFailure(test,error)
    def addError(self,test,error):
        if isinstance(test,EarlyFdtTests):self.failed_methods.add(test._testMethodName)
        else:self.framework_errors.append(test.id())
        super().addError(test,error)
    def addSubTest(self,test,subtest,error):
        if error is not None:self.failed_methods.add(test._testMethodName)
        super().addSubTest(test,subtest,error)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True)
    parser.add_argument('--case',action='append',choices=CASE_NAMES)
    args=parser.parse_args();selected=args.case
    if selected is None:
        selected=json.loads(os.environ.get('N10_NEW_CASES_JSON','[]'))
        if type(selected) is not list or any(type(name) is not str or name not in CASE_NAMES for name in selected):
            parser.error('closed JSON array of new case IDs required')
        selected=selected or list(CASE_NAMES)
    if len(selected)!=len(set(selected)):parser.error('duplicate new case selection')
    out=profile.private(args.output);out.mkdir(parents=True,exist_ok=False)
    result=unittest.TextTestRunner(verbosity=2,resultclass=Recorded).run(unittest.TestSuite(EarlyFdtTests(name) for name in selected))
    failed=sorted(result.failed_methods)
    passed=[name for name in selected if name not in failed] if result.testsRun==len(selected) and not result.framework_errors else []
    receipt=dict(kind='v81-revision1-memblock-owned-FDT-snapshot',selected=selected,passed=passed,failed=failed,tests_run=result.testsRun,
        framework_errors=result.framework_errors,old_suites_executed=0,native_fixture_compiles=len(getattr(EarlyFdtTests,'compile_commands',[])),
        native_compile_commands=getattr(EarlyFdtTests,'compile_commands',[]),device_calls=0,
        source_sha256={name:hashlib.sha256((HERE/name).read_bytes()).hexdigest() for name in (*fdt.SOURCES,'sha256_kat_device_profile.py','builtin_init_profile.py','build_boot_test_packages.py')},
        success=result.wasSuccessful() and result.testsRun==len(selected) and not result.skipped)
    (out/'result.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    return 0 if receipt['success'] else 1


if __name__=='__main__':
    raise SystemExit(main())
