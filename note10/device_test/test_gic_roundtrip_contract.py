import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from decode_reservation import checksum
from decode_gic_roundtrip import decode
from gic_roundtrip_binding import assert_scope,validate_model
from prepare_gic_roundtrip import HERE,PIN,SOURCES

ID='0123456789abcdef0123456789abcdef'
def frame(tag,body):return f'{tag} {body} checksum={checksum(body.encode()):08x}\n'
def evidence(change=None):
    out=''
    for seq in range(2):
        out+=frame('N10GIC2',f'id={ID} seq={seq} before=ff after=ff cpus=8 error=0 status=0')
        for cpu in range(8):
            r=dict(ctlr=0x201,pmr=240,masked=0,restored=240,bpr=0,ctlr_after=0x201,bpr_after=0,dist=1,typer=0x467,iidr=0x20243b,irq_before=1,irq_after=1,seen=1,status=0)
            if change:change(cpu,seq,r)
            body=f'id={ID} seq={seq} cpu={cpu} '+' '.join(f'{k}={v:d}' if k=='status' else f'{k}={v:x}' for k,v in r.items())
            out+=frame('N10GIC1',body)
    return out

class DecoderTests(unittest.TestCase):
    def test_complete(self):self.assertTrue(decode(evidence(),ID)['gic_cpu_pmr_roundtrip_observed'])
    def test_restore_faults_rejected(self):
        for key,value in [('masked',1),('restored',0),('ctlr_after',1),('bpr_after',1),('irq_after',0),('seen',0),('status',5),('pmr',0),('dist',0),('iidr',1<<32)]:
            with self.subTest(key=key):
                def change(cpu,seq,row):
                    if cpu==3:row[key]=value
                with self.assertRaises(ValueError):decode(evidence(change),ID)
    def test_missing_cpu(self):
        text='\n'.join(l for l in evidence().splitlines() if 'cpu=4 ' not in l)
        with self.assertRaises(ValueError):decode(text,ID)
    def test_duplicate_or_foreign(self):
        text=evidence()
        with self.assertRaises(ValueError):decode(text+text,ID)
        with self.assertRaises(ValueError):decode(text,'f'*32)
    def test_conflicting_snapshot(self):
        def change(cpu,seq,row):
            if cpu==0 and seq==1:row['pmr']=row['restored']=128
        with self.assertRaises(ValueError):decode(evidence(change),ID)
    def test_bad_checksum(self):
        with self.assertRaises(ValueError):decode(evidence().replace('pmr=f0','pmr=e0'),ID)

class BindingTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        actual={n:hashlib.sha256((HERE/n).read_bytes()).hexdigest() for n in SOURCES}
        self.build=dict(gic_roundtrip_diagnostic=True,gic_roundtrip_evidence_version=1,pm_quiesce_diagnostic=True,auto_return_diagnostic=True,gic_roundtrip_sources_sha256=actual,gic_roundtrip_source_pin=PIN)
        self.model=dict(passed=True,cases=19,outcomes=[dict(mode=i,passed=True,accepted=i in (0,15,17)) for i in range(19)],source_sha256=actual,
            actual_backend_executed=True,actual_probe_executed=True,strict_decoder_verified=True,hardware_verified=False,
            harness_sha256=hashlib.sha256((HERE/'test_gic_roundtrip_native.py').read_bytes()).hexdigest())
        (self.root/'Image').write_bytes(b'PC FIXTURE N10GIC1 N10GIC2');(self.root/'handoff.config').write_bytes(b'CONFIG_NOTE10_GIC_ROUNDTRIP=y\n')
        (self.root/'gic-roundtrip-model').mkdir()
    def validate(self):
        (self.root/'gic-roundtrip-model/result.json').write_text(json.dumps(self.model));return validate_model(self.root,self.build)
    def test_complete(self):self.assertTrue(self.validate())
    def test_no_metadata_opt_out(self):
        with self.assertRaises(ValueError):assert_scope(self.root,{})
        (self.root/'handoff.config').unlink()
        with self.assertRaises(ValueError):assert_scope(self.root,{})
        (self.root/'Image').write_bytes(b'PC FIXTURE N10GIC1')
        with self.assertRaises(ValueError):assert_scope(self.root,{})
    def test_prerequisites(self):
        for key in ['auto_return_diagnostic','pm_quiesce_diagnostic','gic_roundtrip_evidence_version']:
            with self.subTest(key=key):
                b=copy.deepcopy(self.build);b.pop(key)
                with self.assertRaises(ValueError):assert_scope(self.root,b)
    def test_model_tampering(self):
        for key in ['actual_backend_executed','actual_probe_executed','strict_decoder_verified']:
            self.model[key]=False
            with self.assertRaises(ValueError):self.validate()
            self.model[key]=True
        self.model['outcomes'].pop()
        with self.assertRaises(ValueError):self.validate()
    def test_source_change(self):
        self.build['gic_roundtrip_sources_sha256']={}
        with self.assertRaises(ValueError):self.validate()

if __name__=='__main__':unittest.main()
