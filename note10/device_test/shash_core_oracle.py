"""Mandatory actual-header constant object; no numeric ABI fallback or execution."""
import struct
from kernel_trial_object import parse_elf
from pre_pm_archive_contract import require
TARGET='crypto/n10_shash_core_layout_oracle.o'
SOURCE='crypto/n10_shash_core_layout_oracle.c'
CMD='crypto/.n10_shash_core_layout_oracle.o.cmd'
PUBLIC_SOURCE='note10/device_test/shash_core_layout_oracle.c'
MEMBERS={'crypto_shash':('descsize','base'),'crypto_tfm':('crt_flags','__crt_alg'),'crypto_type':('ctxsize','extsize','init','init_tfm','show','report','lookup','free','type','maskclear','maskset','tfmsize')}
MAGIC=0x4e3634434f524531

def labels():
 names=['tag','schema','storage_word_bytes']
 for typ,fields in MEMBERS.items():
  names += [typ+'.size',typ+'.alignment']
  for field in fields:names += [typ+'.'+field+'.'+kind for kind in ('offset','size','type_alignment','member_alignment')]
 return names+['PAGE_SIZE','CRYPTO_ALG_TYPE_MASK','CRYPTO_ALG_TYPE_SHASH','CRYPTO_TFM_NEED_KEY']

def parse_oracle(raw):
 obj=parse_elf(raw,1);matches=[s for s in obj['symbols'] if s['name']=='n10_shash_core_layout'];require(len(matches)==1,'unique new real-header oracle');s=matches[0]
 require(s['info']==17 and 0<s['section']<len(obj['sections']),'actual global data-only oracle')
 sec=obj['sections'][s['section']];require(sec['name']=='.n10_shash_core_layout' and sec['flags']&2 and not sec['flags']&5,'readonly NX actual constants')
 names=labels();require(s['value']==0 and s['size']==len(names)*8==len(sec['bytes']),'whole exact new oracle schema')
 require(not any(r['section']==s['section'] for r in obj['relocations']) and not any(x['info']&15==2 and x['section'] for x in obj['symbols']),'constants only; no functions or pointer relocations')
 values=dict(zip(names,struct.unpack('<'+'Q'*len(names),sec['bytes'])));require(values['tag']==MAGIC and values['schema']==1 and values['storage_word_bytes']==8,'new compiler oracle schema')
 for typ,fields in MEMBERS.items():
  align=values[typ+'.alignment'];size=values[typ+'.size'];require(size>0 and align>0 and align&(align-1)==0 and size%align==0,'actual compiler type size/alignment')
  for field in fields:
   base=typ+'.'+field;require(values[base+'.size']>0 and values[base+'.offset']+values[base+'.size']<=size,'actual consumed member extent')
   for key in ('type_alignment','member_alignment'):
    a=values[base+'.'+key];require(a>0 and a&(a-1)==0,'actual compiler member alignment')
 require(values['PAGE_SIZE']>=4096 and values['PAGE_SIZE']&(values['PAGE_SIZE']-1)==0,'actual compiler page-size constant')
 return {'object_sha256':obj['sha256'],'values':values,'source':'actual identical-Kbuild defining-header constant expressions','executed':False,'numeric_ABI_substitute':False}

def crosscheck(record,oracle):
 name=record['name'];values=oracle['values'];require(name in MEMBERS,'only three new compiler-oracle types')
 require(record['byte_size']==values[name+'.size'],'mandatory actual DWARF/compiler size agreement')
 row=dict(record)
 if row['alignment'] is None:row['alignment']=values[name+'.alignment'];row['alignment_source']='compiled header constant; DW_AT_alignment absent'
 else:require(row['alignment']==values[name+'.alignment'],'explicit DWARF/compiler alignment agreement');row['alignment_source']='explicit DWARF crosschecked with compiler'
 by={m['name']:m for m in row['members']};require(len(by)==len(row['members']) and set(MEMBERS[name])<=set(by),'mandatory consumed DWARF members')
 for field in MEMBERS[name]:
  member=by[field];prefix=name+'.'+field
  require(member['offset']==values[prefix+'.offset'] and member['type']['byte_size']==values[prefix+'.size'],'actual DWARF/compiler member offset and type size')
  if member.get('member_alignment') is not None:require(member['member_alignment']==values[prefix+'.member_alignment'],'explicit member alignment agreement')
  if member['type'].get('alignment') is not None:require(member['type']['alignment']==values[prefix+'.type_alignment'],'explicit member type alignment agreement')
 return row
