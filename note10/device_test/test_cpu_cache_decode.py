import unittest
from decode_cpu_cache import decode
from decode_reservation import checksum
from test_cpu_cache_native import IDENTITY,prefix

SHA='a'*64
SIZE=0x4000


def frame(tag,values):
    body=' '.join(k+'='+str(v) for k,v in values.items())
    return tag+' '+body+f' checksum={checksum(body.encode()):08x}\n'


def summary(seq,**changes):
    values=dict(id=IDENTITY,seq=seq,before='ff',stopped='1',restored='ff',cpus=8,
                words=SIZE//8,fnv='123',sha256=SHA,clean=1,status=0)
    values.update(changes)
    return frame('N10QUI1',values)


def cpu(seq,index,**changes):
    values=dict(id=IDENTITY,seq=seq,cpu=index,el='4',mpidr=hex(index)[2:],sctlr='1005',
                tcr='123',ttbr1='456',mair='ff',cntkctl='0',cntfrq='18cba80',words=SIZE//8,fnv='123')
    values.update(changes)
    return frame('N10CPU2',values)


def snapshots():
    return ''.join(cpu(seq,index) for index in range(8) for seq in range(2))


class CpuCacheDecodeTests(unittest.TestCase):
    def parse(self,text):return decode(prefix(SHA,SIZE)+text,IDENTITY,SHA,SIZE)

    def test_all_eight_cpus_and_summaries_required(self):
        result=self.parse(summary(0)+summary(1)+snapshots())
        self.assertTrue(result['previous_boot_cpu_cache_roundtrip_observed'])
        self.assertFalse(result['dma_quiescence_verified'])
        self.assertFalse(result['cache_mmu_shutdown_verified'])
        self.assertFalse(result['xnu_executed'])

    def test_bad_stop_restore_hash_cache_and_status_rejected(self):
        for changes in (dict(stopped='3'),dict(restored='7f'),dict(sha256='b'*64),
                        dict(clean=0),dict(status=4),dict(cpus=7)):
            with self.subTest(changes=changes),self.assertRaises(ValueError):
                self.parse(summary(0)+summary(1,**changes)+snapshots())

    def test_missing_duplicate_or_bad_cpu_frames_rejected(self):
        good=summary(0)+summary(1)
        cases=[snapshots().replace(cpu(1,7),''),snapshots()+cpu(0,3),
               snapshots().replace(cpu(1,4),cpu(1,4,fnv='124')),
               snapshots().replace(cpu(1,3),cpu(1,3,tcr='124')),
               snapshots().replace(cpu(1,3),cpu(1,3,el='8'))]
        for text in cases:
            with self.subTest(text=text[-50:]),self.assertRaises(ValueError):self.parse(good+text)

    def test_duplicate_summary_not_repaired_or_deduplicated(self):
        with self.assertRaises(ValueError):self.parse(summary(0)+summary(1)+summary(0)+snapshots())

    def test_mpidr_alias_is_recorded_without_inventing_mapping(self):
        text=snapshots().replace(cpu(0,1),cpu(0,1,mpidr='0')).replace(cpu(1,1),cpu(1,1,mpidr='0'))
        result=self.parse(summary(0)+summary(1)+text)
        self.assertEqual(result['cpus'][0]['snapshot']['mpidr'],result['cpus'][1]['snapshot']['mpidr'])

    def test_corrupt_copies_need_two_intact_sequences(self):
        with self.assertRaises(ValueError):
            self.parse(summary(0)+summary(1).replace('checksum=','checksum=f')+snapshots())


if __name__=='__main__':unittest.main()
