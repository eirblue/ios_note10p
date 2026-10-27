import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from decode_reservation import checksum
from decode_abox_pm import decode,FIELDS
from abox_pm_binding import assert_scope,validate_model
from prepare_abox_pm import HERE,PINS,SOURCES,PATCHED_SHA,event_digest,instrument
from prepare_ufs_pm import instrument_dma
ID='0123456789abcdef0123456789abcdef'

def evidence(change=None):
    result='';decimal={'seq','phase','generation','error','status'}
    for copy_index in range(2):
        for phase in range(3):
            row=dict(seq=copy_index*3+phase,phase=phase,generation=1,seen=1,error=0)
            row.update({k:0 for k in FIELDS});row.update(runtime=2,interfaces=1,rdma=4,wdma=4,events=3,enables=1,disables=1,status=0)
            if change:change(phase,copy_index,row)
            body=f'id={ID} '+' '.join(f'{k}={v:d}' if k in decimal else f'{k}={v:x}' for k,v in row.items())
            result+=f'N10ABX1 {body} checksum={checksum(body.encode()):08x}\n'
    return result

class DecoderTests(unittest.TestCase):
    def test_idle_is_driver_state_not_hardware_shutdown(self):
        result=decode(evidence(),ID,2)
        self.assertTrue(result['abox_driver_idle_state_observed']);self.assertFalse(result['audio_dsp_shutdown_verified'])
    def test_valid_busy_error_and_unbalanced_usage_remain_observations(self):
        for change_row in (dict(enabled=1,firmware=3,runtime=0,usage=1),dict(ipc_seen=1,ipc_called=1,ipc_error=5),dict(usage=1,usage_negative=1),dict(tail=1,queued=1),dict(depth=1)):
            def change(phase,copy,row):row.update(change_row)
            result=decode(evidence(change),ID,2)
            self.assertTrue(result['abox_pm_driver_observed']);self.assertFalse(result['abox_driver_idle_state_observed'])
    def test_invalid_or_incomplete_observations(self):
        for key,value in [('firmware',4),('runtime',4),('head',128),('queued',1),('interfaces',9),('rdma',17),('wdma',17),('enabled',2),('seen',2),('error',1),('generation',2),('status',1),('ipc_called',1),('usage_negative',1),('ipc_error',5)]:
            def change(phase,copy,row):row[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):decode(evidence(change),ID,2)
        text=evidence()
        for bad in (text+text,text.replace(ID,'f'*32),text.replace('runtime=2','runtime=0'),
            '\n'.join(line for line in text.splitlines() if 'phase=1 ' not in line)):
            with self.assertRaises(ValueError):decode(bad,ID,2)
    def test_conflicting_copy_and_generation_wrap(self):
        def conflict(phase,copy,row):
            if phase==1 and copy==1:row['audio']=1
        with self.assertRaises(ValueError):decode(evidence(conflict),ID,2)
        def wrap(phase,copy,row):row['generation']=0xffffffff
        self.assertTrue(decode(evidence(wrap),ID,1)['abox_pm_driver_observed'])
        with self.assertRaises(ValueError):decode(evidence(),ID,1)

class BindingTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        actual={n:hashlib.sha256((HERE/n).read_bytes()).hexdigest() for n in SOURCES}
        self.build=dict(abox_pm_audit_diagnostic=True,abox_pm_audit_evidence_version=1,iommu_pm_audit_diagnostic=True,
            abox_pm_source_pins=PINS,abox_pm_sources_sha256=actual,abox_patched_sha256=PATCHED_SHA)
        self.model=dict(passed=True,cases=25,outcomes=[dict(mode=i,passed=True,accepted=i in (0,15,17,18,19,20,23,24)) for i in range(25)],
            source_sha256=actual,patched_driver_sha256=PATCHED_SHA,event_blocks_sha256=event_digest(),
            generated_dma_sha256=hashlib.sha256(instrument_dma((HERE/'dma_pm_backend.c').read_bytes())).hexdigest(),
            harness_sha256=hashlib.sha256((HERE/'test_abox_pm_native.py').read_bytes()).hexdigest(),actual_backend_executed=True,
            actual_probe_executed=True,generated_event_blocks_executed=True,default_off_blocks_executed=True,generated_dma_hook_executed=True,hardware_verified=False)
        (self.root/'Image').write_bytes(b'PC FIXTURE N10ABX1');(self.root/'handoff.config').write_bytes(b'CONFIG_NOTE10_ABOX_PM_AUDIT=y\n');(self.root/'abox-pm-model').mkdir()
    def validate(self):
        (self.root/'abox-pm-model/result.json').write_text(json.dumps(self.model));return validate_model(self.root,self.build)
    def test_complete(self):self.assertTrue(self.validate())
    def test_scope_cannot_be_opted_out(self):
        with self.assertRaises(ValueError):assert_scope(self.root,{})
        (self.root/'handoff.config').unlink()
        with self.assertRaises(ValueError):assert_scope(self.root,{})
    def test_source_and_native_tampering(self):
        for key in self.build:
            old=self.build[key];self.build[key]=None
            with self.assertRaises(ValueError):self.validate()
            self.build[key]=old
        for key in ('generated_dma_sha256','patched_driver_sha256','event_blocks_sha256','generated_event_blocks_executed','default_off_blocks_executed','actual_backend_executed','actual_probe_executed','generated_dma_hook_executed','harness_sha256'):
            old=self.model[key];self.model[key]=None
            with self.assertRaises(ValueError):self.validate()
            self.model[key]=old

class PinnedRecipeTests(unittest.TestCase):
    def test_exact_original_callback_recipe(self):
        import urllib.request
        raw=urllib.request.urlopen('https://raw.githubusercontent.com/corsicanu/android_kernel_samsung_universal9820/55f042627bb7030c93550faafa117674d32b21d1/sound/soc/samsung/abox/abox.c',timeout=40).read()
        self.assertEqual(hashlib.sha256(instrument(raw)).hexdigest(),PATCHED_SHA)
        with self.assertRaises(ValueError):instrument(raw+b'changed')

if __name__=='__main__':unittest.main()
