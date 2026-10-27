"""Validate the real pinned two-stage PM recipe and reject mixed/tampered hashes."""
import hashlib
from pathlib import Path
import tempfile
import unittest
import urllib.request
from precheck_window_access import pm_suspend_patch_bound,BASE_GUARDED_SUSPEND_SHA,DMA_GUARDED_SUSPEND_SHA
from prepare_pm_diagnostic import patch_suspend,SUSPEND_SHA
from test_pm_timer_contract import pinned_source
from prepare_dma_pm import prepare,HERE,PIN

class SuspendBindingTests(unittest.TestCase):
    def model(self):return dict(source_sha256=SUSPEND_SHA,patched_sha256=BASE_GUARDED_SUSPEND_SHA)
    def build(self):return dict(dma_pm_audit_diagnostic=True,patched_suspend_sha256=DMA_GUARDED_SUSPEND_SHA,
        dma_pm_audit_patched_sha256={'kernel/power/suspend.c':DMA_GUARDED_SUSPEND_SHA})
    def test_base_unchanged(self):
        self.assertTrue(pm_suspend_patch_bound(dict(patched_suspend_sha256=BASE_GUARDED_SUSPEND_SHA),self.model()))
        self.assertFalse(pm_suspend_patch_bound(dict(patched_suspend_sha256='f'*64),self.model()))
    def test_composition(self):self.assertTrue(pm_suspend_patch_bound(self.build(),self.model()))
    def test_wrong_base(self):
        for key in ('source_sha256','patched_sha256'):
            model=self.model();model[key]='f'*64
            self.assertFalse(pm_suspend_patch_bound(self.build(),model))
    def test_wrong_final_or_missing_composition(self):
        build=self.build();build['patched_suspend_sha256']=BASE_GUARDED_SUSPEND_SHA
        self.assertFalse(pm_suspend_patch_bound(build,self.model()))
        build=self.build();build['dma_pm_audit_patched_sha256']={}
        self.assertFalse(pm_suspend_patch_bound(build,self.model()))
        build=self.build();build['dma_pm_audit_diagnostic']=False
        self.assertFalse(pm_suspend_patch_bound(build,self.model()))
    def test_actual_pinned_two_stage_recipe(self):
        base=patch_suspend(pinned_source())
        self.assertEqual(hashlib.sha256(base).hexdigest(),BASE_GUARDED_SUSPEND_SHA)
        raw=urllib.request.urlopen('https://raw.githubusercontent.com/corsicanu/android_kernel_samsung_universal9820/55f042627bb7030c93550faafa117674d32b21d1/drivers/base/power/main.c',timeout=45).read()
        self.assertEqual(hashlib.sha256(raw).hexdigest(),PIN)
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            for directory in ('drivers/base/power','kernel/power','include/linux','arch/arm64/mm'):(root/directory).mkdir(parents=True)
            (root/'drivers/base/power/main.c').write_bytes(raw)
            (root/'kernel/power/suspend.c').write_bytes(base)
            (root/'kernel/power/Kconfig').write_bytes(b'# PC integration fixture\n')
            (root/'arch/arm64/mm/note10_pm_timer_roundtrip.c').write_bytes((HERE/'pm_timer_roundtrip.c').read_bytes())
            report=prepare(root)
            final=(root/'kernel/power/suspend.c').read_bytes()
            self.assertEqual(hashlib.sha256(final).hexdigest(),DMA_GUARDED_SUSPEND_SHA)
            self.assertEqual(report['dma_pm_audit_patched_sha256']['kernel/power/suspend.c'],DMA_GUARDED_SUSPEND_SHA)
            self.assertIn(b'error = -EPERM;',final)
            self.assertIn(b'pm_test_level = TEST_DEVICES;',final)

if __name__=='__main__':unittest.main()
