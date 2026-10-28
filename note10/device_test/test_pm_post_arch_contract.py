"""Strict parser and scope tests for the post-PM CPU observations."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from decode_pm_post_arch import decode
from decode_reservation import checksum
from pm_post_arch_binding import assert_scope, validate_model
from prepare_pm_post_arch import HERE, PINS, SOURCES

IDENTITY='0123456789abcdef0123456789abcdef'
CONFIG=b'CONFIG_NOTE10_PM_POST_ARCH=y\nCONFIG_NOTE10_PM_CPUS_TEST=y\nCONFIG_NOTE10_GIC_ROUNDTRIP=y\nCONFIG_ARM64_4K_PAGES=y\nCONFIG_ARM64_VA_BITS=39\nCONFIG_PGTABLE_LEVELS=3\n# CONFIG_UNMAP_KERNEL_AT_EL0 is not set\n# CONFIG_ARM64_SW_TTBR0_PAN is not set\n'

def sample(copies=2,change=None):
    lines=[]
    for cpu in range(8):
        for seq in range(copies):
            for tag,fields in [('N10PAR1',dict(generation='2',cpu=str(cpu),pre_seen='1',seen='1',el='4',mpidr=f'{0x80000000+cpu:x}',sctlr='1005',tcr='abc',ttbr1='1234000012345000',mair='ff',status='0')),
                               ('N10PCL1',dict(generation='2',cpu=str(cpu),pre_seen='1',seen='1',words='8',fnv='1234',status='0'))]:
                if change:change(tag,cpu,seq,fields)
                body='id='+IDENTITY+' seq='+str(seq)+' '+' '.join(k+'='+v for k,v in fields.items())
                lines.append(tag+' '+body+' checksum='+format(checksum(body.encode()),'08x'))
    return '\n'.join(lines)+'\n'

def baseline():
    return {'cpus':{i:{'snapshot':dict(el=4,mpidr=0x80000000+i,sctlr=0x1005,tcr=0xabc,ttbr1=0x1234000012345000,mair=0xff,words=8,fnv=0x1234)} for i in range(8)}}

class DecoderTests(unittest.TestCase):
    def test_valid_and_asid_change(self):
        self.assertTrue(decode(sample(),IDENTITY,2,baseline(),64)['pm_cpus_arch_restore_observed'])
        data=sample(change=lambda tag,cpu,seq,f:f.update(ttbr1='ffff000012345000') if tag=='N10PAR1' else None)
        self.assertTrue(decode(data,IDENTITY,2,baseline(),64)['pm_cpus_payload_readback_observed'])
    def test_missing_duplicate_conflict_and_mismatch(self):
        good=sample()
        variants=[sample(1),good+good,good.replace(IDENTITY,'f'*32),
            sample(change=lambda t,c,s,f:f.update(tcr='abb') if t=='N10PAR1' and c==3 else None),
            sample(change=lambda t,c,s,f:f.update(fnv='1235') if t=='N10PCL1' and c==3 else None),
            sample(change=lambda t,c,s,f:f.update(ttbr1='1234000012345001') if t=='N10PAR1' and c==3 else None),
            sample(change=lambda t,c,s,f:f.update(mair='fe') if t=='N10PAR1' and c==3 and s==1 else None)]
        for bad in variants:
            with self.subTest(sample=bad[:60]),self.assertRaises(ValueError):decode(bad,IDENTITY,2,baseline(),64)
        with self.assertRaises(ValueError):decode(good,IDENTITY,3,baseline(),64)
        with self.assertRaises(ValueError):decode(good,IDENTITY,2,baseline(),63)

class BindingTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        (self.root/'handoff.config').write_bytes(CONFIG);(self.root/'Image').write_bytes(b'N10PAR1 N10PCL1')
        self.hashes={n:hashlib.sha256((HERE/n).read_bytes()).hexdigest() for n in SOURCES}
        self.build=dict(pm_post_arch_diagnostic=True,pm_post_arch_evidence_version=1,pm_cpus_diagnostic=True,
            gic_roundtrip_diagnostic=True,cpu_cache_roundtrip_diagnostic=True,pm_post_arch_sources_sha256=self.hashes,pm_post_arch_source_pins=PINS,pm_post_arch_worker_sha256='f'*64)
        model=dict(passed=True,cases=37,outcomes=[dict(mode=i,passed=True,accepted=i in (0,1)) for i in range(37)],
            actual_producer_executed=True,asid_only_change_accepted=True,per_cpu_faults_refused=True,no_register_writes=True,online_set_locked=True,hardware_verified=False,source_sha256=self.hashes)
        model['worker_model']=dict(cases=9,outcomes=[dict(mode=i,passed=True,accepted=i==0) for i in (*range(8),9)],worker_sha256='f'*64,
            actual_prepared_worker_executed=True,pm_failure_blocks_observer=True,before_and_after_sha_failures_refused=True,observer_failure_refused=True,gic_failure_blocks_observers=True)
        (self.root/'pm-post-arch-model').mkdir();(self.root/'pm-post-arch-model/result.json').write_text(json.dumps(model))
    def test_required_configuration_and_markers(self):
        self.assertTrue(validate_model(self.root,self.build))
        for line in CONFIG.splitlines():
            (self.root/'handoff.config').write_bytes(CONFIG.replace(line+b'\n',b''))
            with self.assertRaises(ValueError):assert_scope(self.root,self.build)
        (self.root/'handoff.config').write_bytes(CONFIG)
        for marker in (b'N10PAR1',b'N10PCL1'):
            (self.root/'Image').write_bytes(b'N10PAR1 N10PCL1'.replace(marker,b''))
            with self.assertRaises(ValueError):assert_scope(self.root,self.build)

if __name__=='__main__':unittest.main()
