"""PC fixtures for rejecting incomplete quiesce model/source contracts."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from pm_quiesce_binding import HERE,SOURCES,DCORE,validate_model,assert_scope
from prepare_pm_quiesce import PINS


class BindingTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        actual={n:hashlib.sha256((HERE/n).read_bytes()).hexdigest() for n in SOURCES}
        self.build=dict(pm_quiesce_diagnostic=True,pm_quiesce_evidence_version=1,
            pm_timer_diagnostic=True,
            pm_quiesce_sources_sha256=actual,pm_quiesce_source_pins=PINS,
            pm_quiesce_upstream_sha256=PINS,interruptible_sync_guard_preserved=True,
            low_level_suspend_unchanged=True,
            pm_quiesce_patched_sha256={DCORE:'a'*64,'drivers/usb/dwc3/otg.c':'b'*64,'drivers/usb/dwc3/dwc3-exynos.c':'c'*64})
        self.models={}
        cases=[dict(configuration=f'quiesce-{q}-screen-{s}',case=c,passed=True)
               for q in (0,1) for s in (0,1) for c in (range(38) if q else (0,8,24,25))
               if s or c not in (7,11,23)]
        cases += [dict(configuration='generated-driver-error-blocks',case=c,passed=True) for c in range(6)]
        self.models['pm-quiesce-model']=dict(passed=True,case_count=len(cases),cases=cases,
            source_sha256={n:actual[n] for n in ('pm_devices_backend.c','pm_decon_quiesce.c','pm_test_contract.h','pm_quiesce_core.h')},
            harness_sha256=hashlib.sha256((HERE/'test_pm_quiesce_native.py').read_bytes()).hexdigest(),
            actual_backend_executed=True,actual_decon_helper_executed=True,
            generated_decon_executed=True,generated_decon_sha256='a'*64,hardware_verified=False)
        cases=[dict(case=c,passed=True) for c in list(range(23))+['generated-runtime-get-0','generated-runtime-get-1']+['generated-after-pm-'+str(i) for i in range(16)]]
        self.models['pm-usb-model']=dict(passed=True,case_count=len(cases),cases=cases,
            source_sha256={n:actual[n] for n in ('usb_notify_quiesce.c','pm_test_contract.h')},
            harness_sha256=hashlib.sha256((HERE/'test_pm_usb_native.py').read_bytes()).hexdigest(),
            actual_usb_helper_executed=True,generated_runtime_block_executed=True,
            generated_after_pm_block_executed=True,generated_exynos_sha256='c'*64,
            generated_otg_sha256='b'*64,hardware_verified=False)
        cases=[dict(mode=c,passed=True,real_frame_checksums_verified=True,strict_decoder_require_quiesce=True) for c in range(100,108)]
        self.models['pm-timer-model']=dict(passed=True,quiesce_evidence_verified=True,
            source_sha256=hashlib.sha256((HERE/'pm_timer_roundtrip.c').read_bytes()).hexdigest(),
            backend_source_sha256=actual['pm_devices_backend.c'],contract_sha256=actual['pm_test_contract.h'],
            quiesce_core_sha256=actual['pm_quiesce_core.h'],quiesce_evidence_cases=cases)
        (self.root/'Image').write_bytes(b'PC FIXTURE ONLY N10QSC1')
        (self.root/'handoff.config').write_text('CONFIG_NOTE10_PM_QUIESCE=y\n')

    def validate(self):
        for name,model in self.models.items():
            path=self.root/name/'result.json';path.parent.mkdir(exist_ok=True)
            path.write_text(json.dumps(model))
        return validate_model(self.root,self.build)

    def test_complete_fixture(self):
        self.assertTrue(self.validate()['quiesce_models_bound'])

    def test_missing_build_contract(self):
        for key in ('pm_quiesce_diagnostic','pm_quiesce_evidence_version','pm_quiesce_sources_sha256',
                    'interruptible_sync_guard_preserved','low_level_suspend_unchanged'):
            with self.subTest(key=key):
                old=self.build.pop(key)
                with self.assertRaises(ValueError):self.validate()
                self.build[key]=old

    def test_missing_or_duplicated_required_case(self):
        for name in ('pm-quiesce-model','pm-usb-model'):
            original=copy.deepcopy(self.models[name])
            for duplicate in (False,True):
                with self.subTest(name=name,duplicate=duplicate):
                    self.models[name]=copy.deepcopy(original)
                    rows=self.models[name]['cases']
                    if duplicate:rows[-1]=copy.deepcopy(rows[0])
                    else:rows.pop()
                    self.models[name]['case_count']=len(rows)
                    with self.assertRaises(ValueError):self.validate()
            self.models[name]=original

    def test_source_or_generated_digest_differs(self):
        for name,key in (('pm-quiesce-model','generated_decon_sha256'),('pm-usb-model','generated_otg_sha256'),
                         ('pm-usb-model','generated_exynos_sha256'),
                         ('pm-usb-model','harness_sha256'),('pm-timer-model','quiesce_core_sha256')):
            with self.subTest(name=name,key=key):
                old=self.models[name][key];self.models[name][key]='f'*64
                with self.assertRaises(ValueError):self.validate()
                self.models[name][key]=old

    def test_unexecuted_or_failed_actual_c(self):
        for name,key in (('pm-quiesce-model','actual_backend_executed'),('pm-quiesce-model','generated_decon_executed'),
                         ('pm-usb-model','generated_runtime_block_executed'),('pm-timer-model','quiesce_evidence_verified')):
            with self.subTest(name=name,key=key):
                self.models[name][key]=False
                with self.assertRaises(ValueError):self.validate()
                self.models[name][key]=True

    def test_post_pm_runtime_model_must_execute(self):
        self.models['pm-usb-model']['generated_after_pm_block_executed']=False
        with self.assertRaises(ValueError):self.validate()

    def test_marker_and_configuration_required(self):
        for name in ('Image','handoff.config'):
            with self.subTest(name=name):
                path=self.root/name;old=path.read_bytes();path.write_bytes(b'')
                with self.assertRaises(ValueError):self.validate()
                path.write_bytes(old)

    def test_missing_metadata_cannot_downgrade_the_actual_kernel(self):
        downgraded={k:v for k,v in self.build.items() if not k.startswith('pm_quiesce')}
        with self.assertRaises(ValueError):assert_scope(self.root,downgraded)
        (self.root/'handoff.config').unlink()
        with self.assertRaises(ValueError):assert_scope(self.root,downgraded)
        (self.root/'Image').write_bytes(b'LEGACY PC FIXTURE')
        self.assertFalse(assert_scope(self.root,downgraded))


if __name__=='__main__':unittest.main()
