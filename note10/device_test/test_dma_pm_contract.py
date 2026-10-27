import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from decode_reservation import checksum
from decode_dma_pm import decode
from dma_pm_binding import assert_scope,validate_model
from prepare_dma_pm import HERE,PIN,SOURCES

ID='0123456789abcdef0123456789abcdef'
def evidence(change=None):
    lines=[]
    decimal={'seq','phase','generation','error','status'}
    for seq in range(2):
        for phase in range(3):
            row=dict(seq=seq*3+phase,phase=phase,generation=2,seen=1,error=0,total=24,dma=16,
                suspended=16 if phase==1 else 0,direct=0,syscore=0,uncovered=0 if phase==1 else 16,
                prepared=16 if phase==1 else 0,active=8,idle=4,other=4,names_xor=0x1234,names_sum=0x87654321,status=0)
            if change:change(phase,seq,row)
            body=f'id={ID} '+' '.join(f'{k}={v:d}' if k in decimal else f'{k}={v:x}' for k,v in row.items())
            lines.append(f'N10DMA1 {body} checksum={checksum(body.encode()):08x}\n')
    return ''.join(lines)

class DecoderTests(unittest.TestCase):
    def test_complete(self):
        result=decode(evidence(),ID,2)
        self.assertEqual(result['dma_capable_devices'],16)
        self.assertFalse(result['hardware_dma_shutdown_verified'])
    def test_uncovered_is_observation(self):
        def change(phase,seq,row):
            if phase==1:row.update(suspended=15,uncovered=1)
        self.assertEqual(decode(evidence(change),ID,2)['uncovered_at_suspend'],1)
    def test_bad_snapshots(self):
        for key,value in [('seen',2),('generation',3),('error',1),('total',4097),('dma',0),('active',19),('status',1),('names_sum',1<<32)]:
            with self.subTest(key=key):
                def change(phase,seq,row):row[key]=value
                with self.assertRaises(ValueError):decode(evidence(change),ID,2)
    def test_restore_inventory_faults(self):
        for key in ('names_xor','prepared','suspended'):
            with self.subTest(key=key):
                def change(phase,seq,row):
                    if phase==2:row[key]+=1
                with self.assertRaises(ValueError):decode(evidence(change),ID,2)
    def test_missing_conflicting_duplicate_foreign(self):
        text=evidence()
        for bad in (text+text,text.replace(ID,'f'*32),''.join(l+'\n' for l in text.splitlines() if 'phase=1 ' not in l),text.replace('dma=10','dma=11')):
            with self.assertRaises(ValueError):decode(bad,ID,2)
        def conflict(phase,seq,row):
            if phase==1 and seq==1:row.update(active=7,idle=5)
        with self.assertRaises(ValueError):decode(evidence(conflict),ID,2)

class BindingTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        actual={n:hashlib.sha256((HERE/n).read_bytes()).hexdigest() for n in SOURCES}
        self.build=dict(dma_pm_audit_diagnostic=True,dma_pm_audit_evidence_version=1,gic_roundtrip_diagnostic=True,
            pm_quiesce_diagnostic=True,auto_return_diagnostic=True,dma_pm_audit_sources_sha256=actual,dma_pm_audit_source_pin=PIN)
        self.model=dict(passed=True,cases=13,outcomes=[dict(mode=i,passed=True,accepted=i in (0,9,10)) for i in range(13)],source_sha256=actual,
            actual_backend_executed=True,actual_probe_executed=True,strict_decoder_verified=True,hardware_verified=False,
            harness_sha256=hashlib.sha256((HERE/'test_dma_pm_native.py').read_bytes()).hexdigest())
        (self.root/'Image').write_bytes(b'PC FIXTURE N10DMA1');(self.root/'handoff.config').write_bytes(b'CONFIG_NOTE10_DMA_PM_AUDIT=y\n')
        (self.root/'dma-pm-model').mkdir()
    def validate(self):
        (self.root/'dma-pm-model/result.json').write_text(json.dumps(self.model));return validate_model(self.root,self.build)
    def test_complete(self):self.assertTrue(self.validate())
    def test_no_opt_out(self):
        with self.assertRaises(ValueError):assert_scope(self.root,{})
        (self.root/'handoff.config').unlink()
        with self.assertRaises(ValueError):assert_scope(self.root,{})
    def test_prerequisites(self):
        for key in ('dma_pm_audit_evidence_version','gic_roundtrip_diagnostic','pm_quiesce_diagnostic','auto_return_diagnostic'):
            with self.subTest(key=key):
                build=copy.deepcopy(self.build);build.pop(key)
                with self.assertRaises(ValueError):assert_scope(self.root,build)
    def test_tampering(self):
        for key in ('actual_backend_executed','actual_probe_executed','strict_decoder_verified'):
            self.model[key]=False
            with self.assertRaises(ValueError):self.validate()
            self.model[key]=True
        self.model['outcomes'].pop()
        with self.assertRaises(ValueError):self.validate()
    def test_source_change(self):
        self.build['dma_pm_audit_sources_sha256']={}
        with self.assertRaises(ValueError):self.validate()

if __name__=='__main__':unittest.main()
