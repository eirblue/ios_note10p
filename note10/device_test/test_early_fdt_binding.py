"""One new v81 snapshot/frame/producer/package batch, with selective retry IDs."""
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

import early_fdt_binding as fdt
import builtin_init_profile as baseline
import sha256_kat_device_profile as profile
from decode_reservation import checksum

HERE = Path(__file__).resolve().parent
ID, CYCLE, BOOT, SOURCE = '1'*32, '2'*32, '3'*32, '4'*40
BANNER = 'Linux version 4.14.113-v81-early-fdt synthetic-only'
VERIFIER = b"""bool __init early_init_dt_verify(void *params)
{
\tif (!params)
\t\treturn false;
\tif (fdt_check_header(params))
\t\treturn false;
\tinitial_boot_params = params;
\tof_fdt_crc32 = crc32_be(~0, initial_boot_params,
\t\t\t\tfdt_totalsize(initial_boot_params));
\treturn true;
}
"""


def body(status='ok', length=64, digest=None, error=0):
    digest = ('c'*64 if status=='ok' else 'none') if digest is None else digest
    return (f'id={ID} cycle={CYCLE} boundary=post_arch_crc status={status} error={error} '
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
    return dict(version='v81',diagnostic_kind=fdt.KIND,raw_input_binding=False,
        fdt_capture_boundary=fdt.BOUNDARY,fdt_snapshot_capacity_bytes=fdt.CAPACITY,
        fdt_snapshot_footprint={'snapshot_capacity_bytes':fdt.CAPACITY},
        source_sha256={'note10/device_test/'+name:hashlib.sha256((HERE/name).read_bytes()).hexdigest() for name in fdt.SOURCES})


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
            pin=hashlib.sha256(VERIFIER).hexdigest()
            with patch.dict(fdt.API_PINS,{'drivers/of/fdt.c':pin}):
                (cls.work/'test-verifier.c').write_bytes(fdt.overlay_fdt(VERIFIER))
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
        self.assertEqual(observed['sha256'],bytes((448+i)&255 for i in range(32)).hex())
        self.assertEqual(row,dict(copies=1,allocations=1,hashes=1,verified=1,crc_calls=1,cleared=1))
        self.assertFalse(observed['raw_input_binding']);self.assertFalse(observed['pristine_firmware_claimed'])

    def test_capture_header_cap_and_oversize_refusal_preserve_admission(self):
        for name,length in (('minimum',40),('maximum',fdt.CAPACITY)):
            with self.subTest(case=name):
                observed,row=self.native(name);self.assertEqual(observed['length'],length)
                self.assertTrue(observed['passed']);self.assertEqual(row['copies'],1);self.assertEqual(row['cleared'],1)
        for name in ('short','oversized'):
            with self.subTest(case=name):
                observed,row=self.native(name);self.assertEqual(observed['status'],'refused')
                self.assertEqual(row,dict(copies=0,allocations=0,hashes=0,verified=1,crc_calls=1,cleared=1))

    def test_overlay_invalid_input_and_default_off_admission(self):
        for case in ('null','invalid-header'):
            observed,row=self.native(case);self.assertEqual(observed['status'],'unavailable')
            self.assertEqual(row,dict(copies=0,allocations=0,hashes=0,verified=0,crc_calls=0,cleared=1))
        observed,row=self.native('ordinary',False)
        self.assertEqual(observed['status'],'unavailable')
        self.assertEqual(row,dict(copies=0,allocations=0,hashes=0,verified=1,crc_calls=1,cleared=1))
        with self.assertRaises(ValueError):fdt.overlay_fdt(VERIFIER)

    def test_repeat_ambiguous_retains_first_then_clears_without_hash(self):
        observed,row=self.native('repeat');self.assertEqual(observed['status'],'ambiguous')
        self.assertFalse(observed['passed']);self.assertIsNone(observed['sha256'])
        self.assertEqual(row,dict(copies=1,allocations=0,hashes=0,verified=1,crc_calls=2,cleared=1))

    def test_late_provider_alloc_and_hash_failures_clear_snapshot(self):
        for number,error in ((1,-2),(2,-22),(3,-22),(4,-7),(5,-12),(6,-5)):
            with self.subTest(failure=number):
                observed,row=self.native('hash-failure-'+str(number))
                self.assertEqual(observed['status'],'hash_error');self.assertEqual(observed['error'],error)
                self.assertEqual(observed['length'],0);self.assertIsNone(observed['sha256'])
                self.assertEqual(row['copies'],1);self.assertEqual(row['allocations'],1)
                self.assertEqual(row['hashes'],int(number==6));self.assertEqual(row['cleared'],1)

    def test_closed_status_length_provenance_and_checksum(self):
        for value in (body().replace('boundary=post_arch_crc','boundary=pristine'),
                      body().replace('raw_binding=0','raw_binding=1'),body(length=39),body(length=fdt.CAPACITY+1),
                      body(status='ambiguous',length=0,error=-5),body(status='hash_error',length=0,error=0),
                      body()+ ' extra=1',body().replace('sha256=','sha256=0',1)):
            with self.subTest(body=value):
                with self.assertRaises(ValueError):fdt.decode(frame(value),ID,CYCLE)
        for text in (frame()+frame(),frame().replace('length=64','length=65',1),frame(boot='0'*32)):
            with self.assertRaises(ValueError):fdt.decode(text,ID,CYCLE)
        for status in ('unavailable','refused','ambiguous'):
            self.assertFalse(fdt.decode(frame(body(status=status,length=0)),ID,CYCLE)['passed'])

    def test_pid1_recovery_current_boot_association(self):
        _,observation=fdt.decode_selected(associated(),BANNER,ID,CYCLE)
        self.assertTrue(observation['minimal_PID1_start_observed']);self.assertTrue(observation['kat']['passed'])
        for changed in (associated().replace(b'N10INIT2',b'MISSING2'),associated(frame(boot='5'*32)),
                        associated(frame(body().replace(CYCLE,'6'*32))),associated()+b'[    0.000000] Linux version other\n',
                        associated(frame(body(status='refused',length=0)))):
            with self.assertRaises(ValueError):fdt.decode_selected(changed,BANNER,ID,CYCLE)

    def test_exact_saved_bytes_binding_never_joins_old_cpu(self):
        raw=b'new synthetic post-architecture FDT bytes'+b'0'*24;pin=hashlib.sha256(raw).hexdigest()
        observation=fdt.decode(frame(body(length=len(raw),digest=pin)),ID,CYCLE)
        bound=fdt.bind_saved_bytes(observation,raw,pin)
        self.assertTrue(bound['raw_input_binding']);self.assertFalse(bound['historical_cpu_join'])
        self.assertFalse(bound['pristine_firmware_claimed']);self.assertFalse(bound['handoff_ready'])
        for data,expected in ((raw+b'x',pin),(raw,'0'*64)):
            with self.assertRaises(ValueError):fdt.bind_saved_bytes(observation,data,expected)

    def test_new_producer_kind_config_source_and_boundary_binding(self):
        row=producer();lines={'CONFIG_NOTE10_EARLY_FDT_BINDING=y'}
        self.assertEqual(fdt.input_binding(row,lines),dict(fdt_capture_boundary=fdt.BOUNDARY,
            fdt_snapshot_capacity_bytes=fdt.CAPACITY,raw_input_binding=False))
        for key,value in (('version','v78'),('diagnostic_kind','cpu-affinity-binding'),('raw_input_binding',True),
                          ('fdt_capture_boundary','pristine'),('fdt_snapshot_capacity_bytes',2*1024*1024)):
            changed=copy.deepcopy(row);changed[key]=value
            with self.assertRaises(ValueError):fdt.input_binding(changed,lines)
        changed=copy.deepcopy(row);changed['source_sha256']['note10/device_test/early_fdt_binding.c']='0'*64
        for changed,config in ((changed,lines),(row,set()),(row,lines|{'CONFIG_NOTE10_CPU_AFFINITY_BINDING=y'})):
            with self.assertRaises(ValueError):fdt.input_binding(changed,config)

    def test_linked_snapshot_extent_and_package_overlap_refusal(self):
        system='1000 T _text\n2000 B __bss_start\n3000 b n10_fdt_snapshot\n83000 B __bss_stop\n84000 B _end\n'
        symbols='00000000 00080000 b n10_fdt_snapshot\n'
        result=fdt.linked_footprint(system,symbols,0x83000)
        admitted=fdt.placement_admission(result,0x100000,0x200000,0x1000)
        self.assertFalse(admitted['external_ramdisk_overlap']);self.assertFalse(admitted['all_firmware_placement_established'])
        for address in (0x100000,0x182fff):
            with self.assertRaises(ValueError):fdt.placement_admission(result,0x100000,address,0x1000)
        for changed,syms,size in ((system,symbols.replace('00080000','00040000'),0x83000),
                                  (system.replace('83000','4000'),symbols,0x83000),(system,symbols,0x82000)):
            with self.assertRaises(ValueError):fdt.linked_footprint(changed,syms,size)

    def test_ci_context_integrated_receipt_source_run_and_config(self):
        binding=dict(device_profile=fdt.PROFILE,source_head=SOURCE,accepted_result_sha256='a'*64,
            image_sha256='b'*64,image_size=4096,effective_config_sha256='c'*64,build_evidence_id=ID,kernel_banner=BANNER)
        context=dict(schema=1,kind=fdt.PROFILE+'-ci-success-context',accepted=True,producer_source_head=SOURCE,
            ci_result_sha256='a'*64,image_sha256='b'*64,image_bytes=4096,effective_config_sha256='c'*64,
            build_evidence_id=ID,run_id=1,attempt=1,workflow_id=2,job_id=3,artifact_id=4,
            artifact_zip_sha256='d'*64,artifact_zip_bytes=500)
        result=dict(version='v81',diagnostic_kind=fdt.KIND,passed=True,Image_built=True,image_sha256='b'*64,image_bytes=4096,
            build_evidence_id=ID,files_sha256={'actual-effective.config':'c'*64},
            ci_context=dict(GITHUB_SHA=SOURCE,GITHUB_RUN_ID='1',GITHUB_RUN_ATTEMPT='1',GITHUB_JOB=fdt.KIND))
        receipt=profile.ci_success_receipt(context,'e'*64,binding,result)
        self.assertEqual(receipt['kind'],fdt.PROFILE+'-accepted-image');self.assertEqual(receipt['kernel_banner'],BANNER)
        for key,value in (('accepted',False),('producer_source_head','f'*40),('run_id',2),('effective_config_sha256','0'*64)):
            changed=dict(context);changed[key]=value
            with self.assertRaises(ValueError):profile.ci_success_receipt(changed,'e'*64,binding,result)

    def test_new_package_scope_label_and_exact_v78_predecessor(self):
        row={key:'a'*64 for key in (*profile.FIELDS,*baseline.EXTRA_FIELDS)}
        row.update(device_profile=fdt.PROFILE,build_evidence_id=ID,kernel_banner=BANNER,source_head=SOURCE,
            **profile.host_binding(SOURCE),fdt_capture_boundary=fdt.BOUNDARY,fdt_snapshot_capacity_bytes=fdt.CAPACITY,
            raw_input_binding=False,auto_return_diagnostic=True,auto_cycle_token=CYCLE,mode='diagnostic',test_purpose=fdt.KIND)
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


CASE_NAMES = (
    'test_owned_snapshot_late_hash_and_clear',
    'test_capture_header_cap_and_oversize_refusal_preserve_admission',
    'test_overlay_invalid_input_and_default_off_admission',
    'test_repeat_ambiguous_retains_first_then_clears_without_hash',
    'test_late_provider_alloc_and_hash_failures_clear_snapshot',
    'test_closed_status_length_provenance_and_checksum',
    'test_pid1_recovery_current_boot_association',
    'test_exact_saved_bytes_binding_never_joins_old_cpu',
    'test_new_producer_kind_config_source_and_boundary_binding',
    'test_linked_snapshot_extent_and_package_overlap_refusal',
    'test_ci_context_integrated_receipt_source_run_and_config',
    'test_new_package_scope_label_and_exact_v78_predecessor',
)


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
    receipt=dict(kind='v81-new-owned-FDT-snapshot',selected=selected,passed=passed,failed=failed,tests_run=result.testsRun,
        framework_errors=result.framework_errors,old_suites_executed=0,native_fixture_compiles=len(getattr(EarlyFdtTests,'compile_commands',[])),
        native_compile_commands=getattr(EarlyFdtTests,'compile_commands',[]),device_calls=0,
        source_sha256={name:hashlib.sha256((HERE/name).read_bytes()).hexdigest() for name in (*fdt.SOURCES,'sha256_kat_device_profile.py','builtin_init_profile.py','build_boot_test_packages.py')},
        success=result.wasSuccessful() and result.testsRun==len(selected) and not result.skipped)
    (out/'result.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    return 0 if receipt['success'] else 1


if __name__=='__main__':
    raise SystemExit(main())
