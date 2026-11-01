"""Only new v80 retained gate evidence, with controlled returns and no device."""
import argparse
from contextlib import ExitStack
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import auto_cycle as cycle
import sha256_kat_device_profile as profile
import run_probe
import stage_phase2
import prepare_linux_boot
import precheck_window_access

BOOT='b'*64
V78_PIN_DIGEST='2e4f355b738d1e6f4bacdf581cb2e9f1890f8ed8c0e38547f7d474323e3be301'


def call(api,*args,**kwargs):
    return dict(api=api,args=list(args),kwargs=kwargs)


def manifest():
    return dict(bootloader='N976NTEST',partitions=[dict(partition=name,block_node=f'/dev/block/sda{i}',
        size=4096,sha256='a'*64 if name=='boot' else 'c'*64)
        for i,name in enumerate(('boot','recovery','dtb','dtbo','vbmeta'),1)])


class ControlledAdb:
    """Strict returned-value fixture: no subprocess, native command or transport."""
    serial='synthetic-only'
    def __init__(self,baseline):
        self.baseline=baseline;self.calls=[];self.hash_phase=0
        self.node_overrides={};self.size_overrides={};self.hash_overrides={};self.bootloader='N976NTEST'
    @staticmethod
    def value(value):
        if isinstance(value,BaseException):raise value
        return value
    def text(self,*args,**kwargs):
        self.calls.append(call('text',*args,**kwargs))
        if args==('shell','getprop','ro.bootloader'):
            self.hash_phase+=1;return self.value(self.bootloader)
        if args==('shell','cat','/sys/class/power_supply/battery/capacity'):return '50'
        if args[:3]==('shell','readlink','-f'):
            name=args[3].rsplit('/',1)[1]
            row=next(r for r in self.baseline['partitions'] if r['partition']==name)
            return self.value(self.node_overrides.get(name,row['block_node']))
        if args[:3]==('shell','blockdev','--getsize64'):
            row=next(r for r in self.baseline['partitions'] if r['block_node']==args[3])
            return self.value(self.size_overrides.get(args[3],str(row['size'])))
        if args[:2]==('shell','sha256sum'):
            row=next(r for r in self.baseline['partitions'] if r['block_node']==args[2])
            digest=BOOT if row['partition']=='boot' else row['sha256']
            value=self.value(self.hash_overrides.get((self.hash_phase,args[2]),digest))
            return value+'  '+args[2]
        if args==('shell','command','-v','twrp'):return '/sbin/twrp'
        raise AssertionError('Unexpected extra device command in controlled test: '+repr(args))
    def call(self,*args,**kwargs):
        self.calls.append(call('call',*args,**kwargs))
        if args[:3]==('shell','twrp','install') or args==('shell','twrp','reboot'):return b''
        raise AssertionError('Unexpected native transport call')


def hash_commands(baseline):
    return [call('text','shell','getprop','ro.bootloader')]+[
        call('text','shell','sha256sum',row['block_node']) for row in baseline['partitions']]


class GateEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.scratch=tempfile.TemporaryDirectory(prefix='v80-controlled-',dir=profile.ROOT/'note10/private')
        self.addCleanup(self.scratch.cleanup);self.base=Path(self.scratch.name)
        self.backup=self.base/'backup';self.backup.mkdir();self.baseline=manifest()
        (self.backup/'backup-manifest.json').write_text(json.dumps(self.baseline),encoding='utf-8')
        self.adb=ControlledAdb(self.baseline)

    def precheck_setup(self):
        packages=self.base/'packages';packages.mkdir();kernel=self.base/'kernel';kernel.mkdir()
        pair=dict(device_profile=profile.AFFINITY_PROFILE,auto_cycle_token='1'*32,kernel_image_sha256='e'*64,
            backup_manifest_sha256=hashlib.sha256((self.backup/'backup-manifest.json').read_bytes()).hexdigest(),
            expected_current_boot_sha256=BOOT)
        (packages/'package-result.json').write_text(json.dumps(pair),encoding='utf-8')
        stack=ExitStack();self.addCleanup(stack.close)
        # Unchanged package/native/input gates are boundaries, not old tests.
        stack.enter_context(patch.object(stage_phase2,'verify_packages',return_value=[]))
        stack.enter_context(patch.object(prepare_linux_boot,'read_verified_backup',return_value={}))
        stack.enter_context(patch.object(run_probe,'preflight',return_value={'twrp_version':'synthetic'}))
        stack.enter_context(patch.object(precheck_window_access,'require_install_battery',return_value=None))
        stack.enter_context(patch.object(profile,'package_scope',return_value=None))
        stack.enter_context(patch.object(profile,'variant',return_value={'image_sha256':'e'*64}))
        stack.enter_context(patch.object(profile,'fields',return_value={}))
        staged=dict(native_archive_read_verified=True,packages=[],ram_directory='/tmp/note10-phase2-12345678')
        return packages,kernel,staged

    def test_hash_gate_success_retains_only_existing_read_domains(self):
        evidence=dict(phase='postreturn')
        self.assertIsNone(cycle.verify_partitions(self.adb,self.backup,BOOT,evidence=evidence))
        self.assertEqual(self.adb.calls,hash_commands(self.baseline))
        self.assertEqual(evidence['status'],'passed')
        self.assertEqual(len(evidence['hash_rows']),5)
        boot=evidence['hash_rows'][0]
        self.assertEqual(boot['observed_sha256'],BOOT)
        self.assertEqual(boot['expected_size_bytes'],4096)
        self.assertIsNone(boot['observed_size_bytes']);self.assertIsNone(boot['observed_canonical_node'])
        self.assertEqual(boot['hash_byte_domain'],'entire-block-device-stream-to-EOF')
        self.assertIsNone(boot['process_exit_code'])

    def test_hash_gate_mismatch_and_error_preserve_partial_rows(self):
        for fail,error,index in (('d'*64,ValueError,0),(RuntimeError('controlled transport'),RuntimeError,1)):
            with self.subTest(index=index):
                adb=ControlledAdb(self.baseline);node=self.baseline['partitions'][index]['block_node']
                adb.hash_overrides[(1,node)]=fail;evidence={}
                with self.assertRaises(error):cycle.verify_partitions(adb,self.backup,BOOT,evidence=evidence)
                self.assertEqual(adb.calls,hash_commands(self.baseline)[:index+2])
                self.assertEqual(len(evidence['hash_rows']),index+1)
                row=evidence['hash_rows'][-1]
                self.assertEqual(row['status'],'mismatch' if index==0 else 'error')
                self.assertEqual(row['observed_sha256'],'d'*64 if index==0 else None)
                if index:self.assertEqual(evidence['hash_rows'][0]['status'],'passed')

    def test_preinstall_success_keeps_node_size_and_command_order(self):
        packages,kernel,staged=self.precheck_setup()
        result=profile.precheck(packages,kernel,self.backup,self.adb,staged)
        expected=[call('text','shell','cat','/sys/class/power_supply/battery/capacity')]
        for row in self.baseline['partitions']:
            expected.extend([call('text','shell','readlink','-f','/dev/block/by-name/'+row['partition']),
                             call('text','shell','blockdev','--getsize64',row['block_node'])])
        self.assertEqual(self.adb.calls,expected+hash_commands(self.baseline))
        evidence=result['partition_evidence']
        self.assertTrue(result['ready_for_manual_access_test'])
        self.assertEqual([r['observed_size_bytes'] for r in evidence['node_size_rows']],[4096]*5)
        self.assertEqual(evidence['status'],'passed')
        self.assertEqual(profile.read(packages/'PREINSTALL-CHECK.json')['partition_evidence'],evidence)

    def test_preinstall_node_mismatch_short_circuits_size_and_hashes(self):
        packages,kernel,staged=self.precheck_setup();self.adb.node_overrides['boot']='/dev/block/sdb99'
        with self.assertRaisesRegex(ValueError,'paired partition node/size changed'):
            profile.precheck(packages,kernel,self.backup,self.adb,staged)
        self.assertEqual(self.adb.calls,[call('text','shell','cat','/sys/class/power_supply/battery/capacity'),
            call('text','shell','readlink','-f','/dev/block/by-name/boot')])
        saved=profile.read(packages/'PREINSTALL-CHECK.json');row=saved['partition_evidence']['node_size_rows'][0]
        self.assertFalse(saved['ready_for_manual_access_test'])
        self.assertEqual(row['status'],'mismatch');self.assertEqual(row['observed_canonical_node'],'/dev/block/sdb99')
        self.assertIsNone(row['observed_size_bytes'])
        self.assertNotIn('hash_rows',saved['partition_evidence'])

    def test_preinstall_size_error_finally_saves_partial_observations(self):
        packages,kernel,staged=self.precheck_setup();node=self.baseline['partitions'][1]['block_node']
        self.adb.size_overrides[node]=RuntimeError('controlled size error')
        with self.assertRaises(RuntimeError):profile.precheck(packages,kernel,self.backup,self.adb,staged)
        saved=profile.read(packages/'PREINSTALL-CHECK.json');rows=saved['partition_evidence']['node_size_rows']
        self.assertEqual(len(rows),2);self.assertEqual(rows[0]['status'],'passed');self.assertEqual(rows[1]['status'],'error')
        self.assertEqual(rows[1]['observed_canonical_node'],node);self.assertIsNone(rows[1]['observed_size_bytes'])
        self.assertEqual(len(self.adb.calls),5)
        self.assertFalse(any(c['args'][1:2]==['sha256sum'] for c in self.adb.calls))

    def journal_setup(self,fail_postreturn=False):
        output=self.base/'journal';capture=self.base/'capture';capture.mkdir()
        (capture/'selected.txt').write_bytes(b'controlled new diagnostic association')
        packages=self.base/'journal-packages';packages.mkdir()
        stage=dict(index=1,cycle='1'*32,kernel_build=str(self.base/'kernel'),packages=str(packages),image_sha256='e'*64)
        plan=dict(stages=[stage],image_sha256='e'*64,backup_manifest_sha256='f'*64,backup=str(self.backup),
                  identity='2'*32,return_timeout_seconds=240,device_profile=profile.AFFINITY_PROFILE)
        record=dict(mode='diagnostic',file='new-diagnostic.zip',payload_sha256=BOOT)
        pre=dict(phase='preinstall',status='passed',node_size_rows=[dict(observed_size_bytes=4096)])
        stack=ExitStack();self.addCleanup(stack.close)
        stack.enter_context(patch.object(cycle,'validate_plan',return_value=plan))
        stack.enter_context(patch.object(cycle,'verify_packages',return_value=[record]))
        stack.enter_context(patch.object(cycle,'stage',return_value={'ram_directory':'/tmp/controlled'}))
        stack.enter_context(patch.object(cycle,'preflight',return_value={'twrp_version':'synthetic'}))
        stack.enter_context(patch.object(cycle,'boot_id',return_value='00000000-0000-0000-0000-000000000001'))
        stack.enter_context(patch.object(cycle,'wait_recovery',return_value='00000000-0000-0000-0000-000000000002'))
        stack.enter_context(patch.object(cycle,'decode_return',return_value={'controlled_new_association':True}))
        stack.enter_context(patch.object(profile,'precheck',return_value={'ready_for_manual_access_test':True,'partition_evidence':pre}))
        stack.enter_context(patch.object(profile,'collect',return_value={'directory':str(capture),'diagnostic_passed':True,
            'log_selections':{'new':{'selected_file':'selected.txt'}}}))
        if fail_postreturn:self.adb.hash_overrides[(2,self.baseline['partitions'][0]['block_node'])]='d'*64
        return output,pre

    def test_journal_retains_phase_evidence_without_extra_device_commands(self):
        output,pre=self.journal_setup()
        observed=cycle.run_plan(self.base/'controlled-plan.json','9'*64,output,execute=True,adb=self.adb)
        phases=observed['partition_gate_evidence']
        self.assertEqual([p['phase'] for p in phases],['preinstall','postinstall-before-reboot','postreturn'])
        self.assertEqual(phases[0]['evidence'],pre)
        self.assertTrue(all(p['status']=='passed' for p in phases[1:]))
        expected=[call('text','shell','command','-v','twrp'),
            call('call','shell','twrp','install','/tmp/controlled/new-diagnostic.zip',timeout=180),
            *hash_commands(self.baseline),call('call','shell','twrp','reboot',timeout=30),*hash_commands(self.baseline)]
        self.assertEqual(self.adb.calls,expected)
        self.assertEqual(profile.read(output/'journal.json')['partition_gate_evidence'],phases)
        self.assertEqual(observed['status'],'complete')

    def test_journal_failure_preserves_partial_postreturn_gate(self):
        output,_=self.journal_setup(fail_postreturn=True)
        with self.assertRaisesRegex(ValueError,'Partition differs: boot'):
            cycle.run_plan(self.base/'controlled-plan.json','9'*64,output,execute=True,adb=self.adb)
        saved=profile.read(output/'journal.json');gate=saved['partition_gate_evidence'][-1]
        self.assertEqual(saved['status'],'stopped');self.assertEqual(gate['phase'],'postreturn')
        self.assertEqual(gate['status'],'mismatch');self.assertEqual(len(gate['hash_rows']),1)
        self.assertEqual(gate['hash_rows'][0]['observed_sha256'],'d'*64)
        self.assertIsNone(gate['hash_rows'][0]['observed_size_bytes'])
        self.assertEqual(self.adb.calls[-2:],hash_commands(self.baseline)[:2])
        self.assertEqual(sum(c['api']=='call' and c['args'][:3]==['shell','twrp','reboot'] for c in self.adb.calls),1)

    def test_v78_binding_is_immutable_while_new_heads_remain_live(self):
        with patch.object(profile,'sha',side_effect=AssertionError('historical head must not rehash live sources')):
            bound=profile.host_binding('a0674c29eaa2bc8938023fc2be590b9a4a84374e')
        pins=bound['host_profile_source_sha256']
        self.assertEqual(len(pins),16)
        self.assertEqual(hashlib.sha256(json.dumps(pins,sort_keys=True,separators=(',',':')).encode()).hexdigest(),V78_PIN_DIGEST)
        with patch.object(profile,'sha',return_value='e'*64):current=profile.host_binding('9'*40)
        self.assertEqual(current['host_profile_source_sha256']['note10/device_test/auto_cycle.py'],'e'*64)
        self.assertIn('note10/device_test/test_partition_gate_evidence.py',current['host_profile_source_sha256'])


CASE_NAMES=(
 'test_hash_gate_success_retains_only_existing_read_domains','test_hash_gate_mismatch_and_error_preserve_partial_rows',
 'test_preinstall_success_keeps_node_size_and_command_order','test_preinstall_node_mismatch_short_circuits_size_and_hashes',
 'test_preinstall_size_error_finally_saves_partial_observations','test_journal_retains_phase_evidence_without_extra_device_commands',
 'test_journal_failure_preserves_partial_postreturn_gate','test_v78_binding_is_immutable_while_new_heads_remain_live',
)


class Recorded(unittest.TextTestResult):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs);self.failed_methods=set();self.framework_errors=[]
    def addFailure(self,test,error):
        self.failed_methods.add(test._testMethodName);super().addFailure(test,error)
    def addError(self,test,error):
        if isinstance(test,GateEvidenceTests):self.failed_methods.add(test._testMethodName)
        else:self.framework_errors.append(test.id())
        super().addError(test,error)
    def addSubTest(self,test,subtest,error):
        if error is not None:self.failed_methods.add(test._testMethodName)
        super().addSubTest(test,subtest,error)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True)
    parser.add_argument('--case',action='append',choices=CASE_NAMES)
    args=parser.parse_args();selected=list(CASE_NAMES) if args.case is None else args.case
    if len(selected)!=len(set(selected)):parser.error('duplicate new case selection')
    output=profile.private(args.output);output.mkdir(parents=True,exist_ok=False)
    result=unittest.TextTestRunner(verbosity=2,resultclass=Recorded).run(unittest.TestSuite(GateEvidenceTests(name) for name in selected))
    passed=[name for name in selected if name not in result.failed_methods] if result.testsRun==len(selected) and not result.framework_errors else []
    sources=(Path(__file__),Path(cycle.__file__),Path(profile.__file__))
    receipt=dict(kind='v80-controlled-gate-evidence-tests',selected=selected,passed=passed,failed=sorted(result.failed_methods),
        framework_errors=result.framework_errors,tests_run=result.testsRun,old_suites_executed=0,
        device_calls=0,native_subprocess_calls=0,Image_builds=0,
        source_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
        success=result.wasSuccessful() and result.testsRun==len(selected) and not result.skipped)
    (output/'result.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    return 0 if receipt['success'] else 1


if __name__=='__main__':
    raise SystemExit(main())
