"""New synthetic source/config provider mutations only; no provider compilation."""
import argparse,json
from pathlib import Path
from pre_pm_crypto_provider import provider_proof
from prepare_pre_pm_trial import ROOT,require
CASES=('provider-positive','config-module','make-wrong-object','make-missing-selector','driver-name','algorithm-name','digest-field','descriptor-field','digest-constant','descriptor-state','registration-array','module-init','duplicate-registration')
CONFIG=b'CONFIG_CRYPTO_SHA256=y\n'
MAKE=b'obj-$(CONFIG_CRYPTO_SHA256) += sha256_generic.o\n'
SOURCE=b'''static struct shash_alg sha256_algs[2] = { {
 .digestsize = SHA256_DIGEST_SIZE,
 .descsize = sizeof(struct sha256_state),
 .base = { .cra_name = "sha256", .cra_driver_name = "sha256-generic", .cra_flags = CRYPTO_ALG_TYPE_SHASH, }
}, { } };
static int __init sha256_generic_mod_init(void) {
 return crypto_register_shashes(sha256_algs, ARRAY_SIZE(sha256_algs));
}
module_init(sha256_generic_mod_init);
'''
HEADER=b'''#define SHA256_DIGEST_SIZE 32
#define SHA256_BLOCK_SIZE 64
struct sha256_state { u32 state[SHA256_DIGEST_SIZE / 4]; u64 count; u8 buf[SHA256_BLOCK_SIZE]; };
'''
def run_cases():
 result=[]
 for name in CASES:
  config,make,source,header=CONFIG,MAKE,SOURCE,HEADER
  if name=='config-module':config=config.replace(b'=y',b'=m')
  if name=='make-wrong-object':make=make.replace(b'sha256_generic.o',b'other.o')
  if name=='make-missing-selector':make=b'obj-y += sha256_generic.o\n'
  if name=='driver-name':source=source.replace(b'"sha256-generic"',b'"other-driver"')
  if name=='algorithm-name':source=source.replace(b'"sha256"',b'"sha224"')
  if name=='digest-field':source=source.replace(b'.digestsize = SHA256_DIGEST_SIZE',b'.digestsize = SHA224_DIGEST_SIZE')
  if name=='descriptor-field':source=source.replace(b'sizeof(struct sha256_state)',b'sizeof(struct other_state)')
  if name=='digest-constant':header=header.replace(b'DIGEST_SIZE 32',b'DIGEST_SIZE 28')
  if name=='descriptor-state':header=header.replace(b'u64 count;',b'u32 count;')
  if name=='registration-array':source=source.replace(b'crypto_register_shashes(sha256_algs,',b'crypto_register_shashes(other_algs,')
  if name=='module-init':source=source.replace(b'module_init(sha256_generic_mod_init)',b'module_init(other_init)')
  if name=='duplicate-registration':source+=b'void extra(void) { crypto_register_shashes(sha256_algs, 2); }\n'
  try:proof=provider_proof(config,make,source,header)
  except ValueError:require(name!='provider-positive','positive source registration plan rejected')
  else:
   require(name=='provider-positive','bad provider source accepted: '+name)
   require(proof['digest_size_source_constant']==32 and proof['runtime_provider_availability_proven'] is False,'source-only proof scope')
  result.append({'name':name,'passed':True})
 return result
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True);a=ap.parse_args();path=a.output.resolve()
 require(not path.exists() and path.is_relative_to(ROOT/'note10/private'),'fresh private provider-fixture result');path.parent.mkdir(parents=True,exist_ok=True)
 path.write_text(json.dumps({'passed':True,'fixture_only':True,'synthetic_only':True,'provider_object_compiled':False,'runtime_provider_executed':False,'cases':run_cases()},indent=2)+'\n',newline='\n')
if __name__=='__main__':main()
