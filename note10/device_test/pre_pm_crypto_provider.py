"""Source/config-only SHA256 generic inclusion and registration plan, not availability."""
import hashlib,re
from prepare_pre_pm_trial import require

def digest(raw):return hashlib.sha256(raw).hexdigest()
def clean(raw):
 text=raw.decode('ascii');return re.sub(r'/\*.*?\*/|//[^\n]*','',text,flags=re.S)
def balanced(text,start):
 require(text[start]=='{','expected initializer/function brace');depth=0;quote=False;escape=False
 for i in range(start,len(text)):
  c=text[i]
  if quote:
   if escape:escape=False
   elif c=='\\':escape=True
   elif c=='"':quote=False
   continue
  if c=='"':quote=True;continue
  if c=='{':depth+=1
  elif c=='}':
   depth-=1
   if depth==0:return text[start+1:i],i+1
 raise ValueError('unterminated source structure')
def unique(pattern,text,message,flags=0):
 rows=list(re.finditer(pattern,text,flags));require(len(rows)==1,message);return rows[0]
def field(text,name,expected):
 m=unique(r'\.'+name+r'\s*=\s*([^,{}]+),',text,'unique source field: '+name)
 require(re.sub(r'\s+','',m[1])==re.sub(r'\s+','',expected),'source provider field: '+name)
 return expected

def provider_proof(config,makefile,source,header):
 require(re.findall(rb'^CONFIG_CRYPTO_SHA256=(.*)$',config,re.M)==[b'y'] and b'# CONFIG_CRYPTO_SHA256 is not set' not in config,'unique built-in CONFIG_CRYPTO_SHA256=y')
 make=makefile.decode('ascii');lines=[line.strip() for line in make.splitlines() if '$(CONFIG_CRYPTO_SHA256)' in line and not line.lstrip().startswith('#')]
 require(lines==['obj-$(CONFIG_CRYPTO_SHA256) += sha256_generic.o'],'exact source Makefile built-in object mapping')
 text=clean(source);sha=clean(header)
 declaration=unique(r'static\s+struct\s+shash_alg\s+sha256_algs\s*\[\s*2\s*\]\s*=\s*\{',text,'unique two-entry real shash array')
 array,end=balanced(text,declaration.end()-1);entries=[];position=0
 while position<len(array):
  while position<len(array) and array[position].isspace():position+=1
  if position==len(array):break
  require(array[position]=='{','explicit shash initializer entry');entry,position=balanced(array,position);entries.append(entry)
  while position<len(array) and array[position].isspace():position+=1
  if position<len(array):require(array[position]==',','shash initializer separator');position+=1
 require(len(entries)==2,'actual two algorithm entries');entry=entries[0]
 fields={k:field(entry,k,v) for k,v in {'digestsize':'SHA256_DIGEST_SIZE','descsize':'sizeof(struct sha256_state)'}.items()}
 base=unique(r'\.base\s*=\s*\{',entry,'unique sha256 base initializer');base,_=balanced(entry,base.end()-1)
 fields.update({k:field(base,k,v) for k,v in {'cra_name':'"sha256"','cra_driver_name':'"sha256-generic"','cra_flags':'CRYPTO_ALG_TYPE_SHASH'}.items()})
 unique(r'^#define\s+SHA256_DIGEST_SIZE\s+32\s*$',sha,'actual digest32 macro',re.M)
 unique(r'^#define\s+SHA256_BLOCK_SIZE\s+64\s*$',sha,'actual block64 macro',re.M)
 state=unique(r'struct\s+sha256_state\s*\{',sha,'actual descriptor state declaration');state,_=balanced(sha,state.end()-1)
 require(re.sub(r'\s+','',state)=='u32state[SHA256_DIGEST_SIZE/4];u64count;u8buf[SHA256_BLOCK_SIZE];','source-pinned sha256 descriptor-state fields')
 init=unique(r'static\s+int\s+__init\s+sha256_generic_mod_init\s*\(\s*void\s*\)\s*\{',text,'unique actual provider init function')
 init,_=balanced(text,init.end()-1)
 require(re.sub(r'\s+','',init)=='returncrypto_register_shashes(sha256_algs,ARRAY_SIZE(sha256_algs));','actual registration receives same entire shash array')
 unique(r'\bmodule_init\s*\(\s*sha256_generic_mod_init\s*\)\s*;',text,'module_init registration chain')
 require(len(re.findall(r'\bcrypto_register_shashes\s*\(',text))==1,'unique provider registration call')
 return {'CONFIG_CRYPTO_SHA256':'y','make_mapping':{'selector':'CONFIG_CRYPTO_SHA256','object':'sha256_generic.o','built_in_selection':True},
 'array':'sha256_algs','entry_count':2,'sha256_entry_index':0,'fields':fields,'digest_size_source_constant':32,
 'descriptor_size_expression':'sizeof(struct sha256_state)','descriptor_size_compiled_or_measured':False,'descriptor_state_source_fields':['u32 state[SHA256_DIGEST_SIZE / 4]','u64 count','u8 buf[SHA256_BLOCK_SIZE]'],
 'registration_chain':['module_init(sha256_generic_mod_init)','crypto_register_shashes(sha256_algs, ARRAY_SIZE(sha256_algs))'],
 'source_sha256':{'crypto/Makefile':digest(makefile),'crypto/sha256_generic.c':digest(source),'include/crypto/sha.h':digest(header)},
 'config_sha256':digest(config),'scope':'source/config inclusion and registration plan only','provider_object_built':False,'provider_object_executed':False,'runtime_provider_availability_proven':False}
