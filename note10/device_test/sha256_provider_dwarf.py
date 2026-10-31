"""Strict real-object DWARF type extraction. No handwritten layout fallback."""
from pre_pm_archive_contract import require
ESSENTIAL=('shash_alg','crypto_alg','sha256_state','shash_desc')

def choose_layout(records,name):
 candidates=[r for r in records if r['name']==name]
 require(candidates,'essential complete DWARF type missing: '+name)
 canonical=[]
 for r in candidates:
  require(type(r['byte_size']) is int and r['byte_size']>0 and type(r['alignment']) is int and r['alignment']>0,'essential DWARF size/alignment missing: '+name)
  require(r['alignment']&(r['alignment']-1)==0 and r['byte_size']%r['alignment']==0,'DWARF type size/alignment inconsistent')
  require(r['members'],'essential DWARF members missing: '+name)
  names=set()
  for m in r['members']:
   require(m['name'] not in names and m['name'],'duplicate/anonymous essential member');names.add(m['name'])
   require(type(m['offset']) is int and m['offset']>=0 and m['type']['byte_size'] is not None and m['offset']+m['type']['byte_size']<=r['byte_size'],'DWARF member extent')
  intervals=sorted((m['offset'],m['offset']+m['type']['byte_size']) for m in r['members'] if m['type']['byte_size'])
  require(all(intervals[i-1][1]<=intervals[i][0] for i in range(1,len(intervals))),'overlapping essential DWARF struct members')
  canonical.append({k:v for k,v in r.items() if k not in ('die_offset','CU_offset')})
 require(all(c==canonical[0] for c in canonical),'conflicting complete DWARF definitions: '+name)
 return canonical[0]

def extract_layouts(elf,oracle=None):
 require(elf.has_dwarf_info(),'actual provider DWARF absent');dwarf=elf.get_dwarf_info();records=[];variables=[]
 def text(a):return a.value.decode('utf8')
 def scalar(die,key,required=True):
  attr=die.attributes.get(key)
  if attr is None:require(not required,'essential DWARF attribute missing: '+key);return None
  require(type(attr.value) is int and attr.value>=0,'unsupported DWARF constant: '+key);return attr.value
 def offset(attr):
  if type(attr.value) is int:return attr.value
  raw=bytes(attr.value);require(raw and raw[0]==0x23,'only actual constant DW_OP_plus_uconst member offset supported');value=0;shift=0
  for i,b in enumerate(raw[1:]):
   require(i<10,'bounded ULEB offset');value|=(b&127)<<shift
   if not b&128:require(i+2==len(raw),'trailing member expression');return value
   shift+=7
  raise ValueError('truncated member offset')
 def describe(die,depth=0):
  require(die is not None and depth<32,'complete bounded DWARF type reference')
  if die.tag in ('DW_TAG_typedef','DW_TAG_const_type','DW_TAG_volatile_type','DW_TAG_restrict_type'):return describe(die.get_DIE_from_attribute('DW_AT_type'),depth+1)
  name=text(die.attributes['DW_AT_name']) if 'DW_AT_name' in die.attributes else ''
  alignment=scalar(die,'DW_AT_alignment',False)
  if die.tag=='DW_TAG_pointer_type':
   size=scalar(die,'DW_AT_byte_size',False) or die.cu['address_size'];require(size==die.cu['address_size'],'actual DWARF pointer/address size disagreement')
   target=die.get_DIE_from_attribute('DW_AT_type') if 'DW_AT_type' in die.attributes else None
   return {'kind':'pointer','name':name,'byte_size':size,'alignment':alignment,'target_tag':target.tag if target else 'void','target_name':text(target.attributes['DW_AT_name']) if target and 'DW_AT_name' in target.attributes else ''}
  if die.tag=='DW_TAG_array_type':
   item=describe(die.get_DIE_from_attribute('DW_AT_type'),depth+1);bounds=[c for c in die.iter_children() if c.tag=='DW_TAG_subrange_type'];require(len(bounds)==1,'unambiguous one-dimensional actual array')
   bound=bounds[0];lower=scalar(bound,'DW_AT_lower_bound',False) or 0;require(lower==0,'zero-based actual array')
   count=scalar(bound,'DW_AT_count',False);upper=scalar(bound,'DW_AT_upper_bound',False)
   if count is None and upper is not None:count=upper+1
   require(count is None or count>=0,'array bound')
   return {'kind':'array','name':name,'byte_size':0 if count is None else item['byte_size']*count,'alignment':alignment,'count':count,'element':item,'flexible_bound_unspecified':count is None}
  require(die.tag in ('DW_TAG_base_type','DW_TAG_enumeration_type','DW_TAG_structure_type','DW_TAG_union_type'),'unsupported essential member DWARF type: '+die.tag)
  return {'kind':die.tag.removeprefix('DW_TAG_').removesuffix('_type'),'name':name,'byte_size':scalar(die,'DW_AT_byte_size'),'alignment':alignment}
 for cu in dwarf.iter_CUs():
  require(cu['version']==4 and cu['address_size']==8,'actual reviewed DWARF4/AArch64 unit')
  top=cu.get_top_DIE();require('DW_AT_name' in top.attributes and (text(top.attributes['DW_AT_name'])=='crypto/sha256_generic.c' or text(top.attributes['DW_AT_name']).endswith('/crypto/sha256_generic.c')),'actual primary provider DWARF compilation unit')
  for die in cu.iter_DIEs():
   name=text(die.attributes['DW_AT_name']) if 'DW_AT_name' in die.attributes else ''
   if die.tag=='DW_TAG_variable' and name=='sha256_algs':variables.append(describe(die.get_DIE_from_attribute('DW_AT_type')))
   if die.tag!='DW_TAG_structure_type' or name not in ESSENTIAL or die.attributes.get('DW_AT_declaration'):continue
   size=scalar(die,'DW_AT_byte_size');alignment=scalar(die,'DW_AT_alignment',False);members=[]
   for member in die.iter_children():
    if member.tag!='DW_TAG_member':continue
    require(not any(k in member.attributes for k in ('DW_AT_bit_size','DW_AT_bit_offset','DW_AT_data_bit_offset')),'essential bitfield layout unsupported')
    require('DW_AT_name' in member.attributes and 'DW_AT_data_member_location' in member.attributes,'complete named member location')
    typ=describe(member.get_DIE_from_attribute('DW_AT_type'));off=offset(member.attributes['DW_AT_data_member_location'])
    if typ.get('flexible_bound_unspecified'):require(off==size,'unspecified array only at actual struct end')
    members.append({'name':text(member.attributes['DW_AT_name']),'offset':off,'type':typ,'member_alignment':scalar(member,'DW_AT_alignment',False)})
   records.append({'name':name,'byte_size':size,'alignment':alignment,'members':members,'die_offset':die.offset,'CU_offset':cu.cu_offset})
 crosschecks=[]
 if oracle is not None:
  from sha256_provider_oracle import supplement
  records,crosschecks=supplement(records,oracle)
 layouts={n:choose_layout(records,n) for n in ESSENTIAL}
 required={'sha256_state':{'state','count','buf'},'shash_desc':{'tfm','flags','__ctx'},'shash_alg':{'init','update','final','finup','digestsize','descsize','base'},'crypto_alg':{'cra_name','cra_driver_name','cra_flags','cra_blocksize','cra_module'}}
 for name,names in required.items():require(names<={m['name'] for m in layouts[name]['members']},'complete essential DWARF member set: '+name)
 require(variables and all(v==variables[0] for v in variables),'unambiguous actual array variable DWARF')
 array=variables[0];require(array['kind']=='array' and array['count']==2 and array['element']['name']=='shash_alg' and array['byte_size']==2*layouts['shash_alg']['byte_size'],'actual provider array type/count/extent')
 return {'types':layouts,'array_variable':array,'layout_source':'mandatory actual DWARF; absent alignments only from same-Kbuild real-header oracle' if oracle is not None else 'actual complete DWARF only','oracle_crosschecks':crosschecks,'handwritten_ABI_fallback_used':False}
