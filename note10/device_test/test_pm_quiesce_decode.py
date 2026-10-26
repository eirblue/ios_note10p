"""Reject absent, stale, conflicting or failed quiesce/restore evidence."""
import unittest
from decode_pm_timer import decode, decode_quiescence
from test_pm_timer_contract import pm, timers
from test_cpu_cache_decode import summary, snapshots, SHA, SIZE, frame
from test_cpu_cache_native import prefix, IDENTITY


def record(seq, **changes):
    values=dict(id=IDENTITY,seq=seq,attempt=1,version=1,generation=7,epoch=0,
                phase=10,called=1,restored=1,screen=0,display=0,usb=0,wake=0,
                r_usb=0,r_display=0,r_screen=0)
    values.update(changes)
    return frame('N10QSC1',values)


def stage(seq,**changes):
    values=dict(id=IDENTITY,seq=seq,attempt=1,stage=21,error=0)
    values.update(changes)
    return frame('N10PMS1',values)


def attempt(seq,**changes):
    values=dict(id=IDENTITY,seq=seq,attempt=1,error=0,devices=1,resume=1,
                blocked=0,oldlevel=0,newlevel=0,resume_errors=0)
    values.update(changes)
    return frame('N10TRY1',values)


class QuiesceDecodeTests(unittest.TestCase):
    def chain(self):
        return (prefix(SHA,SIZE)+summary(0)+summary(1)+snapshots()+pm(0)+pm(1)+timers()+
                stage(0)+stage(1)+attempt(0)+attempt(1))

    def test_complete_new_contract(self):
        result=decode(self.chain()+record(0)+record(1),IDENTITY,SHA,SIZE,require_quiesce=True)
        self.assertTrue(result['quiescence']['normal_driver_quiesce_observed'])
        self.assertFalse(result['xnu_executed'])
        self.assertFalse(result['dma_quiescence_verified'])

    def test_new_build_requires_quiescence(self):
        for text in ('',record(0)):
            with self.subTest(text=text),self.assertRaises(ValueError):
                decode(self.chain()+text,IDENTITY,SHA,SIZE,require_quiesce=True)
        self.assertTrue(decode(self.chain(),IDENTITY,SHA,SIZE)['previous_boot_pm_timer_observed'])

    def test_each_failure_prevents_success(self):
        faults=[{k:5} for k in ('screen','display','usb','wake','r_usb','r_display','r_screen')]
        faults += [dict(called=0),dict(restored=0),dict(phase=11),dict(generation=0)]
        for changes in faults:
            with self.subTest(changes=changes),self.assertRaises(ValueError):
                decode_quiescence(record(0,**changes)+record(1,**changes),IDENTITY)
            # Failure observations are useful, but never imply success.
            result=decode_quiescence(record(0,**changes)+record(1,**changes),IDENTITY,False)
            self.assertFalse(result['normal_driver_quiesce_observed'])

    def test_wrong_sequence_duplicate_conflict_or_version(self):
        for text in (record(0)+record(0),record(0)+record(1,generation=8),
                     record(0)+record(1,attempt=2),record(8,attempt=2)+record(9,attempt=2),
                     record(0,version=2)+record(1,version=2),record(0,called=2)+record(1,called=2)):
            with self.subTest(text=text),self.assertRaises(ValueError):
                decode_quiescence(text,IDENTITY)

    def test_checksums_and_identity_are_not_repaired(self):
        for text in (record(0)+record(1,id='f'*32),
                     record(0)+record(1).replace('checksum=','checksum=f')):
            with self.subTest(text=text),self.assertRaises(ValueError):
                decode_quiescence(text,IDENTITY)

    def test_retry_history_must_be_contiguous_and_final_successful(self):
        failed=record(0,called=0,wake=16)+record(1,called=0,wake=16)
        good=record(8,attempt=2,generation=9)+record(9,attempt=2,generation=9)
        self.assertEqual(len(decode_quiescence(failed+good,IDENTITY)['attempts']),2)
        with self.assertRaises(ValueError):
            decode_quiescence(good,IDENTITY)
        for changes in (dict(restored=0),dict(r_usb=5),dict(r_display=5),dict(r_screen=5)):
            with self.subTest(changes=changes),self.assertRaises(ValueError):
                decode_quiescence(record(0,**changes)+record(1,**changes)+good,IDENTITY)

    def test_stage_attempt_quiesce_histories_are_bound(self):
        chain=self.chain()
        for text in (chain.replace(stage(1),''),
                     chain.replace(stage(0)+stage(1),stage(0,stage=11,error=16)+stage(1,stage=11,error=16)),
                     chain.replace(attempt(1),''),
                     chain.replace(attempt(0)+attempt(1),attempt(0,error=16)+attempt(1,error=16))):
            with self.subTest(text=text),self.assertRaises(ValueError):
                decode(text+record(0)+record(1),IDENTITY,SHA,SIZE,require_quiesce=True)

    def test_full_retry_chain_requires_previous_clean_ebusy(self):
        chain=self.chain().replace(stage(0)+stage(1)+attempt(0)+attempt(1),'')
        old=stage(0,stage=11,error=16)+stage(1,stage=11,error=16)
        old+=attempt(0,error=16,devices=0,resume=0)+attempt(1,error=16,devices=0,resume=0)
        old+=record(0)+record(1)
        last=stage(8,attempt=2)+stage(9,attempt=2)+attempt(8,attempt=2)+attempt(9,attempt=2)
        last+=record(8,attempt=2,generation=9)+record(9,attempt=2,generation=9)
        self.assertTrue(decode(chain+old+last,IDENTITY,SHA,SIZE,True)['previous_boot_pm_timer_observed'])
        with self.assertRaises(ValueError):
            decode(chain+stage(0)+stage(1)+attempt(0)+attempt(1)+record(0)+record(1)+last,
                   IDENTITY,SHA,SIZE,True)


if __name__=='__main__':
    unittest.main()
