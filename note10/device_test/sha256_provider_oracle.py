"""Parse only compiled real-header constants, crosschecked with mandatory DWARF."""
import hashlib,struct
from kernel_trial_object import parse_elf
from pre_pm_archive_contract import require
TARGET='crypto/n10_sha256_layout_oracle.o'
SOURCE='crypto/n10_sha256_layout_oracle.c'
CMD='crypto/.n10_sha256_layout_oracle.o.cmd'
PUBLIC_SOURCE='note10/device_test/sha256_provider_layout_oracle.c'
MEMBERS={'shash_alg': ('init', 'update', 'final', 'finup', 'digest', 'export', 'import', 'setkey', 'digestsize', 'statesize', 'descsize', 'base'), 'crypto_alg': ('cra_list', 'cra_users', 'cra_flags', 'cra_blocksize', 'cra_ctxsize', 'cra_alignmask', 'cra_priority', 'cra_refcnt', 'cra_name', 'cra_driver_name', 'cra_type', 'cra_u', 'cra_init', 'cra_exit', 'cra_destroy', 'cra_module'), 'sha256_state': ('state', 'count', 'buf'), 'shash_desc': ('tfm', 'flags', '__ctx')}
MAGIC=0x4e36334c41594f31

def labels():
 result=['tag','schema','storage_word_bytes']
 for name,fields in MEMBERS.items():
  result += [name+'.size',name+'.alignment']
  for member in fields:
   result += [name+'.'+member+'.offset',name+'.'+member+'.member_alignment']
   if member!='__ctx':result += [name+'.'+member+'.size',name+'.'+member+'.type_alignment']
 return result

def parse_oracle(raw):
 obj=parse_elf(raw,1);symbols=[s for s in obj['symbols'] if s['name']=='n10_sha256_layout_values'];require(len(symbols)==1,'unique real compiled header oracle')
 s=symbols[0];require(s['info']==17 and 0<s['section']<len(obj['sections']),'defined global readonly oracle object')
 section=obj['sections'][s['section']];require(section['name']=='.n10_sha256_layout' and section['flags']&2 and not section['flags']&5,'allocated readonly/NX oracle constants')
 names=labels();require(s['size']==len(names)*8 and s['value']+s['size']<=len(section['bytes']),'exact fixed oracle schema extent')
 require(not any(r['section']==s['section'] for r in obj['relocations']),'oracle must contain only compiler constant values, no pointers')
 require(not any(x['info']&15==2 and x['section']!=0 for x in obj['symbols']),'oracle emits no executable functions')
 values=dict(zip(names,struct.unpack_from('<'+'Q'*len(names),section['bytes'],s['value'])))
 require(values['tag']==MAGIC and values['schema']==1 and values['storage_word_bytes']==8,'compiler oracle schema/storage')
 for name,fields in MEMBERS.items():
  size=values[name+'.size'];align=values[name+'.alignment'];require(size>0 and align>0 and align&(align-1)==0 and size%align==0,'actual compiler struct size/alignment')
  for member in fields:
   base=name+'.'+member;alignment=values[base+'.member_alignment'];require(alignment>0 and alignment&(alignment-1)==0 and values[base+'.offset']<=size,'actual compiler member fact')
   if member!='__ctx':require(values[base+'.offset']+values[base+'.size']<=size and values[base+'.type_alignment']>0,'actual complete compiler member storage/type alignment')
 return {'object_sha256':obj['sha256'],'symbol':s,'values':values,'source':'actual same-Kbuild defining-header constant expressions','provider_or_oracle_executed':False,'handwritten_ABI_fallback_used':False}

def supplement(records,oracle):
 require(oracle is not None and oracle['handwritten_ABI_fallback_used'] is False,'verified real-header oracle required')
 result=[];crosschecks=[]
 for record in records:
  name=record['name'];require(name in MEMBERS,'only essential actual DWARF structs supplemented');row=dict(record);base=oracle['values']
  require(record['byte_size']==base[name+'.size'],'available DWARF/compiler struct size mismatch')
  supplied=base[name+'.alignment']
  if record['alignment'] is not None:require(record['alignment']==supplied,'explicit DWARF/compiler struct alignment mismatch');row['alignment_source']='DWARF and compiled real-header oracle'
  else:row['alignment']=supplied;row['alignment_source']='compiled real-header oracle; DW_AT_alignment absent'
  require({m['name'] for m in record['members']}==set(MEMBERS[name]),'complete exact essential DWARF member set still mandatory')
  for member in record['members']:
   prefix=name+'.'+member['name'];require(member['offset']==base[prefix+'.offset'],'DWARF/compiler member offset mismatch')
   if member.get('member_alignment') is not None:require(member['member_alignment']==base[prefix+'.member_alignment'],'explicit DWARF/compiler member alignment mismatch')
   if member['name']=='__ctx':require(member['type'].get('flexible_bound_unspecified') and member['type']['byte_size']==0 and member['offset']==record['byte_size'],'actual DWARF flexible context; no sizeof-incomplete-array substitute')
   else:
    require(member['type']['byte_size']==base[prefix+'.size'],'DWARF/compiler member type extent mismatch')
    if member['type'].get('alignment') is not None:require(member['type']['alignment']==base[prefix+'.type_alignment'],'available DWARF/compiler member type alignment mismatch')
   crosschecks.append({'type':name,'member':member['name'],'offset':member['offset'],'member_alignment_DWARF':member.get('member_alignment'),'compiler_member_alignment':base[prefix+'.member_alignment']})
  result.append(row)
 return result,crosschecks
