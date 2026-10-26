"""Screen models must execute the production pause function and bind current sources."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from prepare_screen_log import HERE, validate_model

class ScreenPauseBindingTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        (self.root/'screen-log-model').mkdir()
        (self.root/'pm-timer-model').mkdir()
        (self.root/'pm-timer-model/result.json').write_text(json.dumps({'screen_pause_verified':True}))
        (self.root/'Image').write_bytes(b'N10DSP1')
        (self.root/'handoff.config').write_text('CONFIG_NOTE10_SCREEN_LOG=y\n')
        sources={name:hashlib.sha256((HERE/name).read_bytes()).hexdigest()
            for name in ('screen_log.c','screen_log_core.h','prepare_screen_log.py','xnu_reserve.c')}
        self.build={'screen_log_sources_sha256':sources,'screen_log_version':1,'screen_log_layout':'top-left-quarter'}
        self.model={'passed':True,'renderer_cases':9,'bridge_cases':6,'hardware_cases':8,'source_contracts':29,
            'pause_cases':5,'actual_screen_pause_executed':True,'source_sha256':sources}
    def save(self):
        (self.root/'screen-log-model/result.json').write_text(json.dumps(self.model))
    def test_actual_pause_model_accepted(self):
        self.save();validate_model(self.root,self.build)
    def test_stub_pause_only_rejected(self):
        del self.model['actual_screen_pause_executed'];self.save()
        with self.assertRaises(ValueError):validate_model(self.root,self.build)
    def test_incomplete_pause_coverage_rejected(self):
        self.model['pause_cases']=4;self.save()
        with self.assertRaises(ValueError):validate_model(self.root,self.build)

if __name__=='__main__':unittest.main()
