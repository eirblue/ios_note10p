import unittest
from decode_linux_caps import decode


def sample(count=8,granule=1):
    lines=['N10CAP1 BEGIN online='+str(count)]
    for cpu in reversed(range(count)):
        lines += [f'N10CAP1 CPU cpu={cpu} el=4 mpidr={cpu:x} mmfr0={granule<<20:x} mmfr1=0 isar1=0 clidr=3 ctr=8444c004 cntfrq=18cba80',
                  f'N10CAP1 CACHE cpu={cpu} selector=0 value=2',
                  f'N10CAP1 CACHE cpu={cpu} selector=1 value=3',
                  f'N10CAP1 RESTORE cpu={cpu} before=0 after=0']
    return '\n'.join(lines+['N10CAP1 END online='+str(count)])


class CapsTests(unittest.TestCase):
    def test_all_eight_and_cache_lines(self):
        result=decode(sample());self.assertTrue(result['all_target_cpus_support_16k'])
        self.assertEqual(result['cpus'][0]['caches'][0]['maintenance_line_bytes'],64)
        self.assertEqual(result['cpus'][0]['caches'][1]['maintenance_line_bytes'],128)
        self.assertEqual(result['cpus'][0]['ctr_data_minimum_line_bytes'],64)
        self.assertEqual(result['cpus'][0]['physical_address_bits'],32)
        self.assertFalse(result['cpus'][0]['compiled_40bit_ips_supported'])
        self.assertFalse(result['boot_contract_verified'])

    def test_partial_cpu_set_does_not_prove_full_support(self):
        result=decode(sample(6));self.assertIsNone(result['all_target_cpus_support_16k'])
        self.assertFalse(result['all_target_cpus_observed'])

    def test_unsupported_and_unknown_granule(self):
        self.assertFalse(decode(sample(granule=0))['all_target_cpus_support_16k'])
        self.assertIsNone(decode(sample(granule=15))['all_target_cpus_support_16k'])

    def test_missing_or_duplicate_records(self):
        good=sample()
        bad=[good.rsplit('\n',1)[0],good+'\n'+good,
             good.replace('N10CAP1 CACHE cpu=0 selector=1 value=3\n',''),
             good.replace('N10CAP1 RESTORE cpu=0 before=0 after=0','N10CAP1 RESTORE cpu=0 before=0 after=1'),
             good.replace('END online=8','END online=7'),good.replace('clidr=3','clidr=7')]
        for text in bad:
            with self.assertRaises(ValueError):decode(text)


if __name__=='__main__':unittest.main()
