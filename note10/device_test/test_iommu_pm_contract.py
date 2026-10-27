import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from decode_reservation import checksum
from decode_iommu_pm import decode
from iommu_pm_binding import assert_scope,validate_model
from prepare_iommu_pm import HERE,PINS,SOURCES,HELPERS_SHA,inline_helpers
from prepare_ufs_pm import instrument_dma
ID='0123456789abcdef0123456789abcdef'

def evidence(change=None):
    result='';decimal={'seq','phase','generation','error','status'}
    for copy_index in range(2):
        for phase in range(3):
            row=dict(seq=copy_index*3+phase,phase=phase,generation=1,seen=1,error=0,total=3,
                active=3,suspended=0,runtime=1,manual_off=1,manual_on=1,boot_hold=1,secure_configured=1,mapped=1,syscore=1,
                prepared=3 if phase==1 else 0,pm_suspended=3 if phase==1 else 0,runtime_other=0,names_xor=123,names_sum=456,status=0)
            if change:change(phase,copy_index,row)
            body=f'id={ID} '+' '.join(f'{k}={v:d}' if k in decimal else f'{k}={v:x}' for k,v in row.items())
            result+=f'N10MMU1 {body} checksum={checksum(body.encode()):08x}\n'
    return result

class DecoderTests(unittest.TestCase):
    def test_all_active_observation_is_not_shutdown(self):
        result=decode(evidence(),ID,2)
        self.assertTrue(result['iommu_pm_driver_inventory_observed'])
        self.assertTrue(result['registered_controllers_only'])
        self.assertFalse(result['hardware_iommu_shutdown_verified'])
        self.assertFalse(result['global_dma_shutdown_verified'])
    def test_invalid_counts_status_and_stale_generation(self):
        for key,value in [('total',0),('total',65),('active',4),('suspended',4),('manual_on',4),('seen',2),('error',1),('status',1),('generation',2),('names_xor',1<<32)]:
            def change(phase,index,row):row[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):decode(evidence(change),ID,2)
    def test_inventory_change_or_conflicting_copy(self):
        for conflict in (False,True):
            def change(phase,index,row):
                if phase==1 and (index==1 or not conflict):row['names_sum']+=1
            with self.assertRaises(ValueError):decode(evidence(change),ID,2)
    def test_missing_duplicate_corrupt_and_wrong_identity(self):
        text=evidence()
        for bad in (text+text,text.replace(ID,'f'*32),text.replace('active=3','active=4'),
            ''.join(line+'\n' for line in text.splitlines() if 'phase=1 ' not in line)):
            with self.assertRaises(ValueError):decode(bad,ID,2)
    def test_generation_wrap(self):
        def change(phase,index,row):row['generation']=0xffffffff
        self.assertTrue(decode(evidence(change),ID,1)['iommu_pm_driver_inventory_observed'])
        with self.assertRaises(ValueError):decode(evidence(),ID,1)

class BindingTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        actual={n:hashlib.sha256((HERE/n).read_bytes()).hexdigest() for n in SOURCES}
        generated=hashlib.sha256(instrument_dma((HERE/'dma_pm_backend.c').read_bytes())).hexdigest()
        self.build=dict(iommu_pm_audit_diagnostic=True,iommu_pm_audit_evidence_version=1,ufs_pm_audit_diagnostic=True,
            iommu_pm_sources_sha256=actual,iommu_pm_source_pins=PINS)
        self.model=dict(passed=True,cases=21,outcomes=[dict(mode=i,passed=True,accepted=i in (0,14,18,19)) for i in range(21)],
            source_sha256=actual,pinned_helpers_sha256=HELPERS_SHA,generated_dma_sha256=generated,
            actual_backend_executed=True,actual_probe_executed=True,pinned_helpers_executed=True,generated_dma_hook_executed=True,
            hardware_verified=False,harness_sha256=hashlib.sha256((HERE/'test_iommu_pm_native.py').read_bytes()).hexdigest())
        (self.root/'Image').write_bytes(b'PC FIXTURE N10MMU1');(self.root/'handoff.config').write_bytes(b'CONFIG_NOTE10_IOMMU_PM_AUDIT=y\n')
        (self.root/'iommu-pm-model').mkdir()
    def validate(self):
        (self.root/'iommu-pm-model/result.json').write_text(json.dumps(self.model));return validate_model(self.root,self.build)
    def test_complete(self):self.assertTrue(self.validate())
    def test_actual_scope_cannot_be_opted_out(self):
        with self.assertRaises(ValueError):assert_scope(self.root,{})
        (self.root/'handoff.config').unlink()
        with self.assertRaises(ValueError):assert_scope(self.root,{})
    def test_prerequisite_and_source_binding(self):
        for key in self.build:
            old=self.build[key];self.build[key]=None
            with self.assertRaises(ValueError):self.validate()
            self.build[key]=old
    def test_native_and_hook_tampering(self):
        for key in ('actual_backend_executed','actual_probe_executed','pinned_helpers_executed','generated_dma_hook_executed','pinned_helpers_sha256','generated_dma_sha256','harness_sha256'):
            old=self.model[key];self.model[key]=None
            with self.assertRaises(ValueError):self.validate()
            self.model[key]=old
        self.model['outcomes'][19]['accepted']=False
        with self.assertRaises(ValueError):self.validate()

class PinnedHelpersTests(unittest.TestCase):
    def test_actual_helpers(self):
        import urllib.request
        raw=urllib.request.urlopen('https://raw.githubusercontent.com/corsicanu/android_kernel_samsung_universal9820/55f042627bb7030c93550faafa117674d32b21d1/drivers/iommu/exynos-iommu.h',timeout=40).read()
        self.assertEqual(hashlib.sha256(inline_helpers(raw).encode()).hexdigest(),HELPERS_SHA)
        with self.assertRaises(ValueError):inline_helpers(raw+b'changed')

if __name__=='__main__':unittest.main()
