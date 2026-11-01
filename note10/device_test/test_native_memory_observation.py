"""One maximal NEW v82 metadata/frame/source/package batch; no old suites."""
import argparse
import copy
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import native_memory_observation as native
import early_fdt_binding as route
import builtin_init_profile as baseline
import sha256_kat_device_profile as profile
from decode_reservation import checksum

HERE=Path(__file__).resolve().parent
ID,CYCLE,BOOT,SOURCE='1'*32,'2'*32,'3'*32,'4'*40
BANNER='Linux version 4.14.113-v82-native-memory synthetic-only'
LINES={'CONFIG_NOTE10_NATIVE_MEMORY_OBSERVATION=y','CONFIG_HAVE_MEMBLOCK=y','CONFIG_OF_FLATTREE=y','CONFIG_ARM64_4K_PAGES=y'}
SYNTHETIC_SEAMS=b"""int __init of_scan_flat_dt(int (*it)(unsigned long node,
                                     const char *uname, int depth, void *data),
                           void *data)
{
\tconst void *blob = initial_boot_params;
\tconst char *pathp;
\tint offset, rc = 0, depth = -1;
\tif (!blob)
\t\treturn 0;
\tfor (offset = fdt_next_node(blob, -1, &depth);
\t     offset >= 0 && depth >= 0 && !rc;
\t     offset = fdt_next_node(blob, offset, &depth)) {
\t\tpathp = fdt_get_name(blob, offset, NULL);
\t\trc = it(offset, pathp, depth, data);
\t}
\treturn rc;
}
int __init early_init_dt_scan_memory(unsigned long node, const char *uname,
                                   int depth, void *data)
{
\tconst u64 *reg;
\tint l;
\tunsigned int i;
\tbool hotpluggable;
\t(void)uname; (void)depth; (void)data;
\treg = of_get_flat_dt_prop(node, "linux,usable-memory", &l);
\tif (reg == NULL)
\t\treg = of_get_flat_dt_prop(node, "reg", &l);
\tif (reg == NULL)
\t\treturn 0;
\thotpluggable = of_get_flat_dt_prop(node, "hotpluggable", NULL);
\tfor (i = 0; i < tuple_count; ++i) {
\t\tu64 base = tuples[i][0], size = tuples[i][1];
\t\tif (size == 0)
\t\t\tcontinue;
\t\tearly_init_dt_add_memory_arch(base, size);
\t\tif (!hotpluggable)
\t\t\tcontinue;
\t\t(void)early_init_dt_mark_hotplug_memory_arch(base, size);
\t}
\treturn 0;
}
"""


def bodies():
    return [f'id={ID} cycle={CYCLE} kind=begin stage={native.STAGE} ac=2 sc=1 capacity=16 attempted=1 raw_binding=0',
        f'id={ID} cycle={CYCLE} kind=row ordinal=0 base=0000000000001003 size=0000000000002007 source=1 hotplug=1',
        f'id={ID} cycle={CYCLE} kind=end seen=1 stored=1 dropped=0 flags=00000000 ended=1 offset=20 depth=-1 rc=0 complete=1 raw_binding=0 add_success=0 reservations=0 ownership=0']


def frame(body,boot=BOOT,marker='N10MEMARGS1'):
    return f'N10BOOTLINK2 boot={boot} {marker} {body} checksum={checksum(body.encode()):08x}\n'


def logs(rows=None):return ''.join(frame(row) for row in (bodies() if rows is None else rows))


def associated(payload=None):
    def ret(phase):return ''.join(frame(f'id={ID} cycle={CYCLE} phase={phase} seq={seq} delay_ms=90000 status=0',marker='N10RET1') for seq in (0,1))
    startup=(f'N10ROUTE2 id={ID} boot={BOOT} cycle={CYCLE} route=builtin exec_attempt=1\n'
             f'N10INIT2 id={ID} boot={BOOT} cycle={CYCLE} route=builtin started=1\n')
    return ('[    0.000000] '+BANNER+'\n'+ret(0)+startup+(logs() if payload is None else payload)+ret(1)).encode()


def synthetic_route():
    elf=bytearray((i*17+11)&255 for i in range(1216));start=route.TEMP_NAME_OFFSET
    elf[start:start+10]=b'ccABC123.o';elf[start+10]=0
    archive=bytearray((i*13+7)&255 for i in range(2048));archive[route.INIT_PAYLOAD_OFFSET:route.INIT_PAYLOAD_OFFSET+1216]=elf
    return bytes(elf),bytes(archive)


@contextmanager
def synthetic_pins():
    elf,archive=synthetic_route();start=route.TEMP_NAME_OFFSET
    a=bytearray(elf);a[start:start+10]=bytes(10)
    c=bytearray(archive);c[route.INIT_PAYLOAD_OFFSET+start:route.INIT_PAYLOAD_OFFSET+start+10]=bytes(10)
    config=[line for line in LINES if not line.startswith('CONFIG_NOTE10_NATIVE_MEMORY_OBSERVATION=')]
    with patch.multiple(route,ELF_CANONICAL_SHA256=hashlib.sha256(a).hexdigest(),CPIO_CANONICAL_SHA256=hashlib.sha256(c).hexdigest()), \
         patch.dict(route.ACCEPTED_BASELINE,{'config_sha256':route.placement_config_sha256(config)}):yield


def producer():
    elf,archive=synthetic_route()
    raw=dict(minimal_init_elf_sha256=hashlib.sha256(elf).hexdigest(),initramfs_cpio_sha256=hashlib.sha256(archive).hexdigest())
    result=dict(raw,version='v82',diagnostic_kind=native.KIND,raw_input_binding=False,native_memory_stage=native.STAGE,
        native_memory_capacity=16,ci_context={'GITHUB_SHA':SOURCE},image_sha256='f'*64,image_bytes=4096,
        source_sha256={'note10/device_test/'+name:hashlib.sha256((HERE/name).read_bytes()).hexdigest() for name in native.SOURCES},
        guarded_init_main_sha256=route.ACCEPTED_BASELINE['route_artifacts']['guarded_init_main_sha256'],
        files_sha256={'minimal-init.elf':raw['minimal_init_elf_sha256'],'initramfs.cpio':raw['initramfs_cpio_sha256']},
        native_memory_footprint=dict(native_state_bytes=432,linked_kernel_bytes=4096,
            image_text_offset=route.ACCEPTED_BASELINE['header']['text_offset'],image_flags=route.ACCEPTED_BASELINE['header']['flags']))
    result['source_sha256'].update(route.ACCEPTED_BASELINE['route_sources'])
    result['native_relative_placement']=native.relative_admission(result,LINES,result['native_memory_footprint'],elf=elf,archive=archive,raw_inputs=raw)
    return result,elf,archive,raw


class NativeMemoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        parent=profile.ROOT/'note10/private';parent.mkdir(parents=True,exist_ok=True)
        cls.scratch=tempfile.TemporaryDirectory(prefix='v82-new-',dir=parent)
        cls.work=Path(cls.scratch.name);cls.binaries={};cls.commands=[]
    @classmethod
    def tearDownClass(cls):cls.scratch.cleanup()
    @classmethod
    def run_native(cls,case,enabled=True):
        if enabled not in cls.binaries:
            cc=shutil.which('cc')
            if not cc:raise RuntimeError('native compiler required for NEW metadata fixture')
            with patch.dict(native.API_PINS,{'drivers/of/fdt.c':hashlib.sha256(SYNTHETIC_SEAMS).hexdigest()}):
                (cls.work/'synthetic-native-seams.c').write_bytes(native.overlay_fdt(SYNTHETIC_SEAMS))
            binary=cls.work/('enabled' if enabled else 'default-off')
            cmd=[cc,'-std=gnu11','-O1','-Wall','-Wextra','-Werror','-I'+str(HERE),'-I'+str(cls.work),
                 *(('-DCONFIG_NOTE10_NATIVE_MEMORY_OBSERVATION=1',) if enabled else ()),str(HERE/'native_memory_fixture.c'),'-o',str(binary)]
            cls.commands.append(cmd);run=subprocess.run(cmd,capture_output=True,timeout=60)
            if run.returncode:raise AssertionError(run.stderr.decode(errors='replace'))
            cls.binaries[enabled]=binary
        run=subprocess.run([str(cls.binaries[enabled]),case],capture_output=True,timeout=30)
        if run.returncode:raise AssertionError(run.stderr.decode(errors='replace'))
        lines=run.stdout.decode('ascii').splitlines()
        return native.decode('\n'.join(lines[:-1]),ID,CYCLE),json.loads(lines[-1])

    def test_decoded_nonzero_arguments_before_normalization_and_late_only(self):
        observed,trace=self.run_native('ordinary')
        self.assertTrue(observed['passed']);self.assertEqual([(x['base'],x['size']) for x in observed['rows']],[(0x1003,0x2007),(0xf000,0x1000)])
        self.assertEqual(trace,dict(trace='NGCURHATATN',added=2,hotplugged=2,rc=0,state_bytes=432))
        self.assertFalse(observed['architecture_normalized']);self.assertFalse(observed['memblock_add_success_known'])
        self.assertFalse(observed['raw_input_binding']);self.assertFalse(observed['reservations_complete'])

    def test_existing_source_choice_and_hotplug_call_trace(self):
        observed,trace=self.run_native('usable')
        self.assertEqual(trace['trace'],'NGCUHATATN');self.assertTrue(all(x['source']=='linux,usable-memory' for x in observed['rows']))
        observed,trace=self.run_native('no-hotplug')
        self.assertEqual(trace['trace'],'NGCURHAAN');self.assertEqual(trace['hotplugged'],0)
        self.assertTrue(all(not x['hotpluggable'] for x in observed['rows']))

    def test_overflow_preserves_all_native_calls_and_marks_incomplete(self):
        observed,trace=self.run_native('overflow')
        self.assertFalse(observed['passed']);self.assertEqual((observed['seen'],observed['stored'],observed['dropped']),(18,16,2))
        self.assertEqual(trace['added'],18);self.assertEqual(trace['hotplugged'],18);self.assertTrue(observed['flags']&1)

    def test_first_pass_repeat_never_mixes_rows_or_suppresses_native_calls(self):
        observed,trace=self.run_native('repeat')
        self.assertFalse(observed['passed']);self.assertTrue(observed['flags']&2)
        self.assertEqual(observed['seen'],2);self.assertEqual(len(observed['rows']),2);self.assertEqual(trace['added'],4)
        self.assertEqual(trace['trace'],'NGCURHATATNNGCURHATATN')

    def test_native_exit_missing_blob_missing_end_and_nontarget_callback(self):
        observed,trace=self.run_native('negative-exit')
        self.assertFalse(observed['passed']);self.assertTrue(observed['flags']&32);self.assertEqual(observed['native_exit']['offset'],-9)
        self.assertEqual(trace['rc'],0)
        observed,trace=self.run_native('no-blob')
        self.assertTrue(observed['flags']&16);self.assertEqual(trace['trace'],'');self.assertEqual(trace['rc'],0)
        observed,trace=self.run_native('no-end');self.assertTrue(observed['flags']&64)
        observed,trace=self.run_native('other')
        self.assertTrue(observed['flags']&64);self.assertEqual(trace['trace'],'NGON');self.assertEqual(trace['rc'],7)

    def test_unsupported_width_hints_and_counter_saturation(self):
        observed,_=self.run_native('width')
        self.assertEqual(observed['native_address_cells'],3);self.assertTrue(observed['flags']&4);self.assertFalse(observed['passed'])
        observed,_=self.run_native('saturated')
        self.assertTrue(observed['flags']&8);self.assertEqual(observed['seen'],0xffffffff);self.assertFalse(observed['passed'])

    def test_default_off_preserves_original_seam_trace_without_capture(self):
        observed,trace=self.run_native('ordinary',False)
        self.assertEqual(trace['trace'],'NGCURHATATN');self.assertEqual(trace['added'],2);self.assertEqual(trace['rc'],0)
        self.assertEqual(observed['rows'],[]);self.assertTrue(observed['flags']&64)
        with self.assertRaises(ValueError):native.overlay_fdt(SYNTHETIC_SEAMS)

    def test_closed_frame_schema_counts_sequence_and_nonclaims(self):
        rows=bodies()
        variants=[]
        for index,old,new in ((0,native.STAGE,'successful_memblock_add'),(0,'raw_binding=0','raw_binding=1'),
                              (1,'ordinal=0','ordinal=1'),(1,'size=0000000000002007','size=0000000000000000'),
                              (2,'stored=1','stored=2'),(2,'complete=1','complete=0'),(2,'ownership=0','ownership=1')):
            changed=list(rows);changed[index]=changed[index].replace(old,new);variants.append(changed)
        variants.extend((rows+[rows[1]],rows[:1]+rows[2:],rows[:1]+[rows[1]+' extra=1']+rows[2:]))
        for changed in variants:
            with self.assertRaises(ValueError):native.decode(logs(changed),ID,CYCLE)
        with self.assertRaises(ValueError):native.decode(logs().replace('seen=1','seen=2',1),ID,CYCLE)

    def test_current_boot_pid1_recovery_stage_association(self):
        _,observed=native.decode_selected(associated(),BANNER,ID,CYCLE)
        self.assertTrue(observed['minimal_PID1_start_observed']);self.assertTrue(observed['kat']['passed'])
        for data in (associated().replace(b'N10INIT2',b'MISSING2'),associated(logs().replace('boot='+BOOT,'boot='+'5'*32)),
                     associated(logs().replace('cycle='+CYCLE,'cycle='+'6'*32)),associated()+b'[    0.000000] Linux version other\n'):
            with self.assertRaises(ValueError):native.decode_selected(data,BANNER,ID,CYCLE)

    def test_new_mode_own_source_current_route_and_relative_gates(self):
        with synthetic_pins():
            result,elf,archive,raw=producer()
            self.assertNotEqual(result['ci_context']['GITHUB_SHA'],route.IMAGE_SOURCE_HEAD)
            bound=native.input_binding(result,LINES,elf=elf,archive=archive,raw_inputs=raw)
            self.assertTrue(bound['native_relative_placement_admitted']);self.assertFalse(bound['raw_input_binding'])
            for key,value in (('version','v81'),('diagnostic_kind','early-fdt-binding'),('native_memory_stage','successful_add'),('raw_input_binding',True)):
                changed=copy.deepcopy(result);changed[key]=value
                with self.assertRaises(ValueError):native.input_binding(changed,LINES,elf=elf,archive=archive,raw_inputs=raw)
            changed=copy.deepcopy(result);changed['source_sha256']['note10/device_test/native_memory_observation.c']='0'*64
            with self.assertRaises(ValueError):native.input_binding(changed,LINES,elf=elf,archive=archive,raw_inputs=raw)
            for config in (LINES|{'CONFIG_NOTE10_EARLY_FDT_BINDING=y'},LINES|{'CONFIG_RANDOMIZE_BASE=n'},
                           LINES|{'CONFIG_NOTE10_NATIVE_MEMORY_OBSERVATION_EXTRA=y'}):
                self.assertFalse(native.relative_admission(result,config,result['native_memory_footprint'],elf=elf,archive=archive,raw_inputs=raw)['eligible'])

    def test_state_budget_linked_footprint_package_label_and_exact_v81_predecessor(self):
        system='1000 T _text\n2000 B __bss_start\n3000 b n10_memory\n4000 B __bss_stop\n5000 B _end\n'
        self.assertEqual(native.linked_footprint(system,'0000 000001b0 b n10_memory\n',0x4000,524288,10)['native_state_bytes'],432)
        with self.assertRaises(ValueError):native.linked_footprint(system,'0000 00000201 b n10_memory\n',0x4000,524288,10)
        row={key:'a'*64 for key in (*profile.FIELDS,*baseline.EXTRA_FIELDS)}
        row.update(device_profile=native.PROFILE,build_evidence_id=ID,kernel_banner=BANNER,source_head=SOURCE,
            **profile.host_binding(SOURCE),native_memory_stage=native.STAGE,native_memory_capacity=16,raw_input_binding=False,
            native_relative_placement_admitted=True,auto_return_diagnostic=True,auto_cycle_token=CYCLE,mode='diagnostic',test_purpose=native.KIND)
        profile.package_scope(row,'diagnostic')
        from build_boot_test_packages import updater
        parts=[dict(partition=name,block_node=f'/dev/block/sda{i}',size=4096,sha256='a'*64) for i,name in enumerate(('boot','recovery','dtb','dtbo','vbmeta'),1)]
        script=updater(mode='diagnostic',bootloader='N976NTEST',partitions=parts,payload_sha='b'*64,current_boot_sha='a'*64,auto_return=True,device_profile=native.PROFILE)
        self.assertIn(b'Temporary Linux native memory argument diagnostic; not iOS/XNU.',script)
        pair=dict(device_profile=profile.FDT_PROFILE,source_head=profile.V81_IMAGE_HEAD,host_profile_source_head=profile.V81_HOST_HEAD)
        plan=dict(device_profile=native.PROFILE,current_boot_payload_sha256='a'*64)
        baseline.current_boot_binding(plan,pair,{'payload_sha256':'a'*64})
        self.assertEqual(profile.host_binding(profile.V81_HOST_HEAD)['host_profile_source_sha256'],profile.V81_HOST_PINS)
        self.assertEqual(len(profile.V81_HOST_PINS),20)
        for changed in (dict(pair,device_profile=profile.AFFINITY_PROFILE),dict(pair,source_head=profile.V73_HOST_HEAD),dict(pair,host_profile_source_head=profile.V81_IMAGE_HEAD)):
            with self.assertRaises(ValueError):baseline.current_boot_binding(plan,changed,{'payload_sha256':'a'*64})

    def test_native_ci_context_job_run_image_and_config_binding(self):
        binding=dict(device_profile=native.PROFILE,source_head=SOURCE,accepted_result_sha256='a'*64,image_sha256='b'*64,
            image_size=4096,effective_config_sha256='c'*64,build_evidence_id=ID,kernel_banner=BANNER)
        context=dict(schema=1,kind=native.PROFILE+'-ci-success-context',accepted=True,producer_source_head=SOURCE,
            ci_result_sha256='a'*64,image_sha256='b'*64,image_bytes=4096,effective_config_sha256='c'*64,build_evidence_id=ID,
            run_id=1,attempt=1,workflow_id=2,job_id=3,artifact_id=4,artifact_zip_sha256='d'*64,artifact_zip_bytes=500)
        result=dict(version='v82',diagnostic_kind=native.KIND,passed=True,Image_built=True,image_sha256='b'*64,image_bytes=4096,
            build_evidence_id=ID,files_sha256={'actual-effective.config':'c'*64},
            ci_context=dict(GITHUB_SHA=SOURCE,GITHUB_RUN_ID='1',GITHUB_RUN_ATTEMPT='1',GITHUB_JOB=native.KIND))
        self.assertEqual(profile.ci_success_receipt(context,'e'*64,binding,result)['kind'],native.PROFILE+'-accepted-image')
        for key,value in (('accepted',False),('producer_source_head','f'*40),('run_id',2),('effective_config_sha256','0'*64)):
            changed=dict(context);changed[key]=value
            with self.assertRaises(ValueError):profile.ci_success_receipt(changed,'e'*64,binding,result)


CASE_NAMES=(
    'test_decoded_nonzero_arguments_before_normalization_and_late_only',
    'test_existing_source_choice_and_hotplug_call_trace',
    'test_overflow_preserves_all_native_calls_and_marks_incomplete',
    'test_first_pass_repeat_never_mixes_rows_or_suppresses_native_calls',
    'test_native_exit_missing_blob_missing_end_and_nontarget_callback',
    'test_unsupported_width_hints_and_counter_saturation',
    'test_default_off_preserves_original_seam_trace_without_capture',
    'test_closed_frame_schema_counts_sequence_and_nonclaims',
    'test_current_boot_pid1_recovery_stage_association',
    'test_new_mode_own_source_current_route_and_relative_gates',
    'test_state_budget_linked_footprint_package_label_and_exact_v81_predecessor',
    'test_native_ci_context_job_run_image_and_config_binding',
)


class Recorded(unittest.TextTestResult):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs);self.failed_methods=set();self.framework_errors=[]
    def addFailure(self,test,error):self.failed_methods.add(test._testMethodName);super().addFailure(test,error)
    def addError(self,test,error):
        if isinstance(test,NativeMemoryTests):self.failed_methods.add(test._testMethodName)
        else:self.framework_errors.append(test.id())
        super().addError(test,error)
    def addSubTest(self,test,subtest,error):
        if error is not None:self.failed_methods.add(test._testMethodName)
        super().addSubTest(test,subtest,error)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True);parser.add_argument('--case',action='append',choices=CASE_NAMES)
    args=parser.parse_args();selected=args.case
    if selected is None:
        selected=json.loads(os.environ.get('N10_NEW_CASES_JSON','[]'))
        if type(selected) is not list or any(type(name) is not str or name not in CASE_NAMES for name in selected):parser.error('closed new case ID array required')
        selected=selected or list(CASE_NAMES)
    if len(selected)!=len(set(selected)):parser.error('duplicate new case selection')
    out=profile.private(args.output);out.mkdir(parents=True,exist_ok=False)
    result=unittest.TextTestRunner(verbosity=2,resultclass=Recorded).run(unittest.TestSuite(NativeMemoryTests(name) for name in selected))
    failed=sorted(result.failed_methods)
    passed=[name for name in selected if name not in failed] if result.testsRun==len(selected) and not result.framework_errors else []
    receipt=dict(kind='v82-new-native-argument-observation',selected=selected,passed=passed,failed=failed,tests_run=result.testsRun,
        framework_errors=result.framework_errors,old_suites_executed=0,native_fixture_compiles=len(getattr(NativeMemoryTests,'commands',[])),
        native_compile_commands=getattr(NativeMemoryTests,'commands',[]),device_calls=0,
        source_sha256={name:hashlib.sha256((HERE/name).read_bytes()).hexdigest() for name in (*native.SOURCES,'sha256_kat_device_profile.py','builtin_init_profile.py','build_boot_test_packages.py')},
        success=result.wasSuccessful() and result.testsRun==len(selected) and not result.skipped)
    (out/'result.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    return 0 if receipt['success'] else 1


if __name__=='__main__':raise SystemExit(main())
