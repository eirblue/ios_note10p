import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from decode_reservation import checksum
from decode_ufs_pm import decode
from ufs_pm_binding import assert_scope,validate_model
from prepare_ufs_pm import HERE,PINS,SOURCES,instrument_dma
ID='0123456789abcdef0123456789abcdef'

def evidence(change=None):
    result=''
    decimal={'seq','phase','generation','error','status'}
    for copy_index in range(2):
        for phase in range(3):
            row=dict(seq=copy_index*3+phase,phase=phase,generation=1,seen=1,error=0,
                requests=0,tasks=0,lrb=0,powered=1,irq=0 if phase==1 else 1,
                system=int(phase==1),busy=0,power=2 if phase==1 else 1,
                link=2 if phase==1 else 1,clock=0 if phase==1 else 1,gating=int(phase==1),runtime=2 if phase==1 else 0,status=0)
            if change:change(phase,copy_index,row)
            body=f'id={ID} '+' '.join(f'{k}={v:d}' if k in decimal else f'{k}={v:x}' for k,v in row.items())
            result+=f'N10UFS1 {body} checksum={checksum(body.encode()):08x}\n'
    return result

class DecoderTests(unittest.TestCase):
    def test_complete(self):
        r=decode(evidence(),ID,2)
        self.assertTrue(r['ufs_pm_driver_state_observed']);self.assertFalse(r['hardware_ufs_dma_idle_verified'])
    def test_runtime_suspend_reuses_system_helper(self):
        def change(phase,index,row):
            if phase==2:row.update(system=1,runtime=2,irq=0,clock=0,gating=1,power=2,link=2)
        self.assertTrue(decode(evidence(change),ID,2)['ufs_pm_driver_state_observed'])
    def test_faults(self):
        for key,value in [('requests',1),('tasks',1),('lrb',1),('busy',1),('powered',0),('generation',2),('seen',2),('error',1),('status',1),('power',4),('runtime',4),('clock',7)]:
            with self.subTest(key=key):
                def change(phase,index,row):row[key]=value
                with self.assertRaises(ValueError):decode(evidence(change),ID,2)
    def test_suspend_and_resume_predicates(self):
        for key,value in [('system',0),('irq',1),('clock',1),('gating',0),('link',1),('power',1)]:
            with self.subTest(key=key):
                def change(phase,index,row):
                    if phase==1:row[key]=value
                with self.assertRaises(ValueError):decode(evidence(change),ID,2)
        def failed_resume(phase,index,row):
            if phase==2:row['system']=1
        with self.assertRaises(ValueError):decode(evidence(failed_resume),ID,2)
    def test_missing_duplicate_corrupt_conflicting(self):
        text=evidence()
        for bad in (text+text,text.replace(ID,'f'*32),text.replace('requests=0','requests=1'),
            ''.join(l+'\n' for l in text.splitlines() if 'phase=1 ' not in l)):
            with self.assertRaises(ValueError):decode(bad,ID,2)
        def conflict(phase,index,row):
            if phase==0 and index==1:row['runtime']=2
        with self.assertRaises(ValueError):decode(evidence(conflict),ID,2)
    def test_generation_wrap(self):
        def change(phase,index,row):row['generation']=0xffffffff
        self.assertTrue(decode(evidence(change),ID,1)['ufs_pm_driver_state_observed'])
        with self.assertRaises(ValueError):decode(evidence(),ID,1)

class BindingTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        actual={n:hashlib.sha256((HERE/n).read_bytes()).hexdigest() for n in SOURCES}
        generated=hashlib.sha256(instrument_dma((HERE/'dma_pm_backend.c').read_bytes())).hexdigest()
        self.build=dict(ufs_pm_audit_diagnostic=True,ufs_pm_audit_evidence_version=1,dma_pm_audit_diagnostic=True,auto_return_diagnostic=True,
            ufs_pm_audit_sources_sha256=actual,ufs_pm_audit_source_pins=PINS,ufs_pm_generated_dma_sha256=generated)
        self.model=dict(passed=True,cases=27,outcomes=[dict(mode=i,passed=True,accepted=i in (0,19,20)) for i in range(27)],source_sha256=actual,
            actual_backend_executed=True,actual_probe_executed=True,generated_dma_hook_executed=True,hardware_verified=False,
            generated_dma_sha256=generated,harness_sha256=hashlib.sha256((HERE/'test_ufs_pm_native.py').read_bytes()).hexdigest())
        (self.root/'Image').write_bytes(b'PC FIXTURE N10UFS1');(self.root/'handoff.config').write_bytes(b'CONFIG_NOTE10_UFS_PM_AUDIT=y\n')
        (self.root/'ufs-pm-model').mkdir()
    def validate(self):
        (self.root/'ufs-pm-model/result.json').write_text(json.dumps(self.model));return validate_model(self.root,self.build)
    def test_complete(self):self.assertTrue(self.validate())
    def test_no_opt_out(self):
        with self.assertRaises(ValueError):assert_scope(self.root,{})
        (self.root/'handoff.config').unlink()
        with self.assertRaises(ValueError):assert_scope(self.root,{})
    def test_missing_prerequisites(self):
        for key in ('ufs_pm_audit_evidence_version','dma_pm_audit_diagnostic','auto_return_diagnostic'):
            b=copy.deepcopy(self.build);b.pop(key)
            with self.assertRaises(ValueError):assert_scope(self.root,b)
    def test_model_and_generated_hook_tampering(self):
        for key in ('actual_backend_executed','actual_probe_executed','generated_dma_hook_executed'):
            self.model[key]=False
            with self.assertRaises(ValueError):self.validate()
            self.model[key]=True
        self.model['generated_dma_sha256']=self.build['ufs_pm_generated_dma_sha256']='f'*64
        with self.assertRaises(ValueError):self.validate()
    def test_source_change(self):
        self.build['ufs_pm_audit_sources_sha256']={}
        with self.assertRaises(ValueError):self.validate()

if __name__=='__main__':unittest.main()
