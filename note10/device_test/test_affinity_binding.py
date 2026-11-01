"""One new v78 framing/association/input-binding/private-transport batch only."""
import argparse
import base64
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
import unittest
import zipfile

import affinity_binding as affinity
import builtin_init_profile as baseline
import sha256_kat_device_profile as profile
from decode_reservation import checksum

HERE = Path(__file__).resolve().parent
ID, CYCLE, BOOT, SOURCE = '1'*32, '2'*32, '3'*32, '4'*40
BANNER = 'Linux version 4.14.113-v78-cpu-affinity synthetic-only'


def frame(body, boot=BOOT, marker='N10AFF1'):
    return f'N10BOOTLINK2 boot={boot} {marker} {body} checksum={checksum(body.encode()):08x}\n'


def bodies(cpus=(0,31), mismatch=True):
    mask = sum(1 << cpu for cpu in cpus)
    rows = [f'id={ID} cycle={CYCLE} kind=begin online={mask:08x} count={len(cpus)} capacity=32 fdt=unavailable raw_binding=0 status=0']
    for cpu in cpus:
        logical_map = cpu ^ int(mismatch and cpu == cpus[-1])
        rows.append(f'id={ID} cycle={CYCLE} kind=row cpu={cpu} map={logical_map:016x} mpidr={0x80000000|cpu:016x} cntfrq=123456 equal={int(logical_map==cpu)}')
    rows.append(f'id={ID} cycle={CYCLE} kind=end online={mask:08x} seen={mask:08x} count={len(cpus)} status=0 fdt=unavailable raw_binding=0')
    return rows


def log(rows=None):
    return ''.join(frame(body) for body in (bodies() if rows is None else rows))


def associated(payload=None):
    def ret(phase):
        return ''.join(frame(f'id={ID} cycle={CYCLE} phase={phase} seq={seq} delay_ms=90000 status=0', marker='N10RET1') for seq in (0,1))
    startup = (f'N10ROUTE2 id={ID} boot={BOOT} cycle={CYCLE} route=builtin exec_attempt=1\n'
               f'N10INIT2 id={ID} boot={BOOT} cycle={CYCLE} route=builtin started=1\n')
    return ('[    0.000000] '+BANNER+'\n'+ret(0)+startup+(log() if payload is None else payload)+ret(1)).encode()


class AffinityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        profile.private(profile.ROOT/'note10/private/v78-test-scratch-parent').parent.mkdir(parents=True,exist_ok=True)
        cls.scratch = tempfile.TemporaryDirectory(prefix='v78-new-',dir=profile.ROOT/'note10/private')
        cls.work = Path(cls.scratch.name)
        cls.node = shutil.which('node')
        if not cls.node:
            raise RuntimeError('Node24 required for new sealed transport integration')
        cls.primary = cls.command('keygen',cls.work/'recipient')
        cls.command('keygen',cls.work/'wrong-recipient')

    @classmethod
    def tearDownClass(cls):
        cls.scratch.cleanup()

    @classmethod
    def command(cls,*args,recipient=None,success=True):
        env = dict(os.environ)
        if recipient is not None:
            env['N10_RECIPIENT_PUBLIC_KEY_B64'] = recipient
        result = subprocess.run([cls.node,str(HERE/'sealed_affinity_artifact.cjs'),*map(str,args)],
                                capture_output=True,env=env,timeout=60)
        if (result.returncode==0) != success:
            raise AssertionError('sealed transport unexpected exit: '+str(result.returncode))
        return json.loads(result.stdout) if result.returncode==0 else None

    def reject(self,rows):
        with self.assertRaises(ValueError):
            affinity.decode(log(rows),ID,CYCLE)

    def test_sparse_tuple_mismatch_observed_without_repair(self):
        observed=affinity.decode(log(),ID,CYCLE)
        self.assertTrue(observed['passed'])
        self.assertEqual([row['cpu'] for row in observed['cpus']],[0,31])
        self.assertEqual(observed['mapping_mismatches'],1)
        self.assertEqual(observed['cpus'][-1]['logical_map'],30)
        self.assertEqual(observed['cpus'][-1]['raw_mpidr'],0x8000001f)
        self.assertFalse(observed['raw_input_binding'])
        self.assertIsNone(observed['original_fdt_digest'])
        self.assertFalse(observed['cpu_shutdown_state_known'])

    def test_capacity32_including_index31(self):
        observed=affinity.decode(log(bodies(tuple(range(32)),False)),ID,CYCLE)
        self.assertEqual(len(observed['cpus']),32)
        self.assertEqual(observed['online_mask'],0xffffffff)

    def test_missing_duplicate_unexpected_and_reordered_rows(self):
        rows=bodies()
        variants=[rows[:1]+rows[2:],rows[:2]+[rows[1]]+rows[3:],
                  [rows[0],rows[1],rows[2].replace('cpu=31','cpu=32'),rows[-1]],
                  [rows[0],rows[2],rows[1],rows[-1]]]
        for variant in variants:
            with self.subTest(rows=variant):self.reject(variant)

    def test_checksum_and_closed_schema(self):
        with self.assertRaises(ValueError):
            affinity.decode(log().replace('cntfrq=123456','cntfrq=123457',1),ID,CYCLE)
        rows=bodies();rows[1]+=' extra=1';self.reject(rows)

    def test_build_cycle_and_boot_binding(self):
        for identity,cycle in (('5'*32,CYCLE),(ID,'6'*32)):
            with self.subTest(identity=identity,cycle=cycle):
                with self.assertRaises(ValueError):affinity.decode(log(),identity,cycle)
        for changed in (log().replace('boot='+BOOT,'boot='+'0'*32),
                        log().replace('boot='+BOOT,'boot='+'7'*32,1)):
            with self.assertRaises(ValueError):affinity.decode(changed,ID,CYCLE)

    def test_status_frequency_masks_relation_and_fdt_scope(self):
        variants=[]
        for old,new,index in (('status=0','status=-5',0),('cntfrq=123456','cntfrq=0',1),
                              ('cntfrq=123456','cntfrq=100000000',1),('equal=0','equal=1',2),
                              ('seen=80000001','seen=00000001',3),('fdt=unavailable','fdt=present',0),
                              ('raw_binding=0','raw_binding=1',3)):
            rows=bodies();rows[index]=rows[index].replace(old,new);variants.append(rows)
        for rows in variants:
            with self.subTest(rows=rows):self.reject(rows)

    def test_minimal_pid1_recovery_and_current_boot_association(self):
        data=associated();_,observed=affinity.decode_selected(data,BANNER,ID,CYCLE)
        self.assertTrue(observed['kat']['passed'])
        self.assertTrue(observed['minimal_PID1_start_observed'])
        for changed in (data.replace(b'N10INIT2',b'MISSING2'),
                        associated(log().replace('boot='+BOOT,'boot='+'7'*32)),
                        data+b'[    0.000000] Linux version other\n'):
            with self.assertRaises(ValueError):affinity.decode_selected(changed,BANNER,ID,CYCLE)

    def test_new_kind_producer_source_and_config_binding(self):
        result=dict(version='v78',diagnostic_kind=affinity.KIND,raw_input_binding=False,
                    original_fdt_digest_unavailable=True,
                    source_sha256={'note10/device_test/'+name:hashlib.sha256((HERE/name).read_bytes()).hexdigest() for name in affinity.SOURCES})
        lines={'CONFIG_NOTE10_CPU_AFFINITY_BINDING=y','CONFIG_SMP=y'}
        self.assertFalse(affinity.input_binding(result,lines)['raw_input_binding'])
        variants=[]
        for key,value in (('version','v73'),('diagnostic_kind','sha256-stream-state'),('raw_input_binding',True),('original_fdt_digest_unavailable',False)):
            changed=copy.deepcopy(result);changed[key]=value;variants.append((changed,lines))
        changed=copy.deepcopy(result);changed['source_sha256']['note10/device_test/cpu_affinity_binding.c']='0'*64
        variants.extend(((changed,lines),(result,{'CONFIG_SMP=y'}),(result,lines|{'CONFIG_NOTE10_SHA256_STREAM_STATE=y'})))
        for changed,config in variants:
            with self.assertRaises(ValueError):affinity.input_binding(changed,config)

    def test_new_current_v73_chain_only(self):
        plan=dict(device_profile=affinity.PROFILE,current_boot_payload_sha256='a'*64)
        pair=dict(device_profile=profile.STREAM_PROFILE,source_head=profile.V73_HOST_HEAD,
                  host_profile_source_head=profile.V73_HOST_HEAD)
        baseline.current_boot_binding(plan,pair,{'payload_sha256':'a'*64})
        for key,value in (('device_profile',profile.BUILTIN_PROFILE),('source_head','b'*40),('host_profile_source_head','b'*40)):
            changed=dict(pair);changed[key]=value
            with self.assertRaises(ValueError):baseline.current_boot_binding(plan,changed,{'payload_sha256':'a'*64})
        with self.assertRaises(ValueError):baseline.current_boot_binding(plan,pair,{'payload_sha256':'b'*64})

    def test_new_package_scope_and_nonclaim_fields(self):
        row={key:'a'*64 for key in (*profile.FIELDS,*baseline.EXTRA_FIELDS)}
        row.update(device_profile=affinity.PROFILE,build_evidence_id=ID,kernel_banner=BANNER,source_head=SOURCE,
                   **profile.host_binding(SOURCE),raw_input_binding=False,original_fdt_digest_unavailable=True,
                   auto_return_diagnostic=True,auto_cycle_token=CYCLE,mode='diagnostic',test_purpose=affinity.KIND)
        profile.package_scope(row,'diagnostic')
        self.assertFalse(profile.fields(row)['raw_input_binding'])
        from build_boot_test_packages import updater
        partitions=[dict(partition=name,block_node=f'/dev/block/sda{index}',size=4096,sha256='a'*64)
                    for index,name in enumerate(('boot','recovery','dtb','dtbo','vbmeta'),1)]
        script=updater(mode='diagnostic',bootloader='N976NTEST',partitions=partitions,
                       payload_sha='b'*64,current_boot_sha='a'*64,auto_return=True,device_profile=affinity.PROFILE)
        self.assertIn(b'ui "Temporary Linux CPU affinity diagnostic; not iOS/XNU."',script)
        self.assertNotIn(b'Temporary Linux SHA256 diagnostic;',script)
        for key,value in (('test_purpose','sha256-stream-state'),('raw_input_binding',True),('original_fdt_digest_unavailable',False)):
            changed=dict(row);changed[key]=value
            with self.assertRaises(ValueError):profile.package_scope(changed,'diagnostic')

    def test_sealed_transport_roundtrip_and_authentication_refusal(self):
        plain=self.work/'synthetic.zip';sealed=self.work/'synthetic.sealed';opened=self.work/'authenticated.zip'
        with zipfile.ZipFile(plain,'x') as archive:archive.writestr('synthetic.txt',b'v78 synthetic evidence only')
        self.command('seal',plain,sealed,SOURCE,recipient=self.primary['recipient_public_key_b64'])
        envelope=sealed.read_bytes()
        length=struct.unpack_from('>I',envelope,8)[0]
        header=json.loads(envelope[12:12+length]);header['source_commit']='c'*40
        header_bytes=json.dumps(header,separators=(',',':')).encode()
        self.assertEqual(len(header_bytes),length)
        aad_changed=envelope[:12]+header_bytes+envelope[12+length:]
        variants=[('wrong-key',envelope,self.work/'wrong-recipient/private-key.pem',SOURCE),
                  ('tamper',envelope[:-1]+bytes([envelope[-1]^1]),self.work/'recipient/private-key.pem',SOURCE),
                  ('truncated',envelope[:-1],self.work/'recipient/private-key.pem',SOURCE),
                  ('source',envelope,self.work/'recipient/private-key.pem','d'*40),
                  ('authenticated-header',aad_changed,self.work/'recipient/private-key.pem','c'*40)]
        for label,data,key,source in variants:
            attempt=self.work/(label+'.sealed');attempt.write_bytes(data)
            output=self.work/(label+'.zip')
            self.command('open',attempt,key,output,source,success=False)
            self.assertFalse(output.exists())
        result=self.command('open',sealed,self.work/'recipient/private-key.pem',opened,SOURCE)
        self.assertTrue(result['authenticated'])
        self.assertEqual(opened.read_bytes(),plain.read_bytes())

    def test_sealed_transport_private_output_and_freshness(self):
        plain=self.work/'scope.zip';plain.write_bytes(b'synthetic bounded transport input')
        outside=profile.ROOT/('v78-public-output-'+self.work.name)
        self.command('seal',plain,outside,SOURCE,recipient=self.primary['recipient_public_key_b64'],success=False)
        self.assertFalse(outside.exists())
        existing=self.work/'existing.sealed';existing.write_bytes(b'preserved')
        self.command('seal',plain,existing,SOURCE,recipient=self.primary['recipient_public_key_b64'],success=False)
        self.assertEqual(existing.read_bytes(),b'preserved')
        private_pem=(self.work/'recipient/private-key.pem').read_bytes()
        self.command('recipient',recipient=base64.b64encode(private_pem).decode('ascii'),success=False)
        self.command('open',existing,self.work/'recipient/private-key.pem',outside,SOURCE,success=False)
        self.assertFalse(outside.exists())


CASE_NAMES = (
    'test_sparse_tuple_mismatch_observed_without_repair','test_capacity32_including_index31',
    'test_missing_duplicate_unexpected_and_reordered_rows','test_checksum_and_closed_schema',
    'test_build_cycle_and_boot_binding','test_status_frequency_masks_relation_and_fdt_scope',
    'test_minimal_pid1_recovery_and_current_boot_association','test_new_kind_producer_source_and_config_binding',
    'test_new_current_v73_chain_only','test_new_package_scope_and_nonclaim_fields',
    'test_sealed_transport_roundtrip_and_authentication_refusal','test_sealed_transport_private_output_and_freshness',
)


class Recorded(unittest.TextTestResult):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs);self.failed_methods=set();self.framework_errors=[]
    def addFailure(self,test,error):
        self.failed_methods.add(test._testMethodName);super().addFailure(test,error)
    def addError(self,test,error):
        if isinstance(test,AffinityTests):self.failed_methods.add(test._testMethodName)
        else:self.framework_errors.append(test.id())
        super().addError(test,error)
    def addSubTest(self,test,subtest,error):
        if error is not None:self.failed_methods.add(test._testMethodName)
        super().addSubTest(test,subtest,error)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True)
    parser.add_argument('--case',action='append',choices=CASE_NAMES)
    args=parser.parse_args()
    selected=args.case
    if selected is None:
        selected=json.loads(os.environ.get('N10_NEW_CASES_JSON','[]'))
        if type(selected) is not list or any(type(name) is not str or name not in CASE_NAMES for name in selected):
            parser.error('closed JSON array of new method names required')
        selected=selected or list(CASE_NAMES)
    if len(selected)!=len(set(selected)):parser.error('duplicate new method selection')
    out=profile.private(args.output);out.mkdir(parents=True,exist_ok=False)
    result=unittest.TextTestRunner(verbosity=2,resultclass=Recorded).run(unittest.TestSuite(AffinityTests(name) for name in selected))
    failed=sorted(result.failed_methods)
    passed=[name for name in selected if name not in failed] if result.testsRun==len(selected) and not result.framework_errors else []
    sources=[Path(__file__),HERE/'affinity_binding.py',HERE/'sealed_affinity_artifact.cjs',HERE/'sha256_kat_device_profile.py',HERE/'builtin_init_profile.py']
    receipt=dict(kind='v78-new-affinity-binding-and-private-transport',selected=selected,passed=passed,failed=failed,
                 tests_run=result.testsRun,framework_errors=result.framework_errors,
                 old_suites_executed=0,native_fixture_compiles=0,device_calls=0,
                 source_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
                 success=result.wasSuccessful() and result.testsRun==len(selected) and not result.skipped)
    (out/'result.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    return 0 if receipt['success'] else 1


if __name__=='__main__':
    raise SystemExit(main())
