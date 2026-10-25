import unittest
import tempfile
from pathlib import Path
from observed_profile import derive,check_tcr,create,load,ROOT


def fixture():
    lines=['Linux version 4.14.113-note10-handoff-pc (fixture)','N10CAP1 BEGIN online=8']
    for cpu in range(8):
        lines.extend([f'N10CAP1 CPU cpu={cpu} el=4 mpidr={cpu:x} mmfr0=100002 mmfr1=0 isar1=0 clidr=3 ctr=84448004 cntfrq=18cba80',
                      f'N10CAP1 CACHE cpu={cpu} selector=0 value=2',
                      f'N10CAP1 CACHE cpu={cpu} selector=1 value={3 if cpu==7 else 2}',
                      f'N10CAP1 RESTORE cpu={cpu} before=0 after=0'])
    return '\n'.join([*lines,'N10CAP1 END online=8'])


class ObservedTests(unittest.TestCase):
    def test_heterogeneous_cache_maximum(self):
        p=derive(fixture());self.assertEqual(p['defines']['N10_MAX_CACHE_LINE_LOG2'],7)
        self.assertEqual(p['defines']['N10_ICACHE_LINE_LOG2'],6)
        self.assertEqual(p['minimum_pa_bits'],40);self.assertEqual(p['compiled_cpu_limit'],1)

    def test_incompatible_or_incomplete_register_views(self):
        t=fixture()
        changes=[t.replace('mmfr0=100002','mmfr0=2',1),t.replace('mmfr0=100002','mmfr0=100001',1),
                 t.replace('el=4','el=8',1),t.replace('mpidr=1 ','mpidr=0 ',1),
                 t.replace('cntfrq=18cba80','cntfrq=18cba81',1),t.replace('ctr=84448004','ctr=84448005',1),
                 t.replace('4.14.113-note10-handoff-pc','stock'),t+'\nLinux version stock',
                 t.replace('N10CAP1 RESTORE cpu=0 before=0 after=0',''),
                 t.replace('selector=1 value=2','selector=1 value=1',1)]
        for text in changes:
            with self.subTest(text=text[:80]),self.assertRaises(ValueError):derive(text)

    def test_affinity_alias_is_recorded_without_enabling_smp(self):
        p=derive(fixture().replace('mpidr=1 ','mpidr=1000000 ',1))
        self.assertEqual(p['affinity_alias_groups'],[[0,1]])
        self.assertFalse(p['cpu_topology_mapping_verified']);self.assertEqual(p['compiled_cpu_limit'],1)

    def test_real_tcr_geometry_and_rejections(self):
        p=derive(fixture());tcr=(2<<32)|(1<<30)|(2<<14)
        self.assertEqual(check_tcr(p,tcr)['tcr_pa_bits'],40)
        for invalid in (tcr|(1<<59),(tcr&~(7<<32))|(5<<32),tcr&~(3<<14),tcr&~(3<<30),True,-1,1<<64):
            with self.subTest(tcr=invalid),self.assertRaises(ValueError):check_tcr(p,invalid)

    def test_log_and_header_provenance_corruption(self):
        parent=ROOT/'note10/private/observed-profile-tests';parent.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=parent) as name:
            directory=Path(name);self.assertTrue(directory.resolve().is_relative_to(parent.resolve()))
            log=directory/'input.log';log.write_text(fixture(),encoding='utf-8')
            expected=create(log,directory/'bundle');path=directory/'bundle/observed-profile.json'
            self.assertEqual(load(path),expected)
            log.write_text(fixture()+'\nmodified',encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'hash changed'):load(path)
            log.write_text(fixture(),encoding='utf-8')
            (path.parent/'observed-board.h').write_text('#define N10_KERNEL_PAGE_SHIFT 12',encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'header differs'):load(path)

    def test_output_cannot_escape_private_or_overwrite(self):
        with self.assertRaisesRegex(ValueError,'Private output'):create(Path('unused'),ROOT/'public-profile-output')
        parent=ROOT/'note10/private/observed-profile-tests';parent.mkdir(parents=True,exist_ok=True)
        with self.assertRaisesRegex(ValueError,'overwrite'):create(Path('unused'),parent)


if __name__=='__main__':unittest.main()
