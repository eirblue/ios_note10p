"""Only crypto_alg.cra_type's single const pointee, bound to extracted layout."""
import hashlib,json
from pre_pm_archive_contract import require

RAW_KEYS=frozenset(('kind','name','byte_size','alignment','target_tag','target_name'))
SCHEMA='crypto_alg.cra_type.single-const-v1'


def canonical(record):return {k:v for k,v in record.items() if k not in ('die_offset','CU_offset')}


def layout_digest(layout):
 require(layout['name']=='crypto_type' and type(layout['byte_size']) is int and layout['byte_size']>0 and layout['members'],'actual complete crypto_type layout identity')
 return hashlib.sha256(json.dumps(canonical(layout),sort_keys=True,separators=(',',':')).encode('utf8')).hexdigest()


def qualified_member_type(owner,name,type_die,descriptor,pending):
 """Called from actual member extraction; retain the six raw pointer fields."""
 if owner!='crypto_alg' or name!='cra_type' or descriptor.get('kind')!='pointer' or descriptor.get('target_tag')!='DW_TAG_const_type':return descriptor
 require(set(descriptor)==RAW_KEYS and type(descriptor['byte_size']) is int and descriptor['byte_size']==8 and descriptor['target_name']=='','exact raw scoped pointer metadata')
 seen=set();chain=[]
 def take(die):
  require(die is not None and len(chain)<3,'bounded non-null single-const type chain')
  require(die.cu is type_die.cu and die.cu['version']==4 and die.cu['address_size']==8,'same actual DWARF4/address8 type graph')
  require(type(die.cu.cu_offset) is int and die.cu.cu_offset>=0 and type(die.offset) is int and die.offset>=die.cu.cu_offset,'actual bounded DIE/CU identity')
  key=(die.cu.cu_offset,die.offset);require(key not in seen,'no qualified type cycle');seen.add(key);chain.append(die);return die
 def text(die):
  a=die.attributes.get('DW_AT_name');require(a is None or type(a.value) is bytes,'actual type name bytes');return '' if a is None else a.value.decode('utf8')
 def reference(die):
  a=die.attributes.get('DW_AT_type');require(a is not None and a.form in ('DW_FORM_ref1','DW_FORM_ref2','DW_FORM_ref4','DW_FORM_ref8','DW_FORM_ref_udata') and type(a.value) is int and a.value>=0,'actual bounded same-unit type reference')
  try:target=die.get_DIE_from_attribute('DW_AT_type')
  except Exception as error:raise ValueError('broken actual qualified type reference') from error
  require(target is not None and target.offset==die.cu.cu_offset+a.value,'resolved DIE agrees with actual CU-relative reference value')
  return take(target)
 pointer=take(type_die);require(pointer.tag=='DW_TAG_pointer_type' and text(pointer)==descriptor['name'],'raw member reference is the actual pointer DIE')
 size=pointer.attributes.get('DW_AT_byte_size');require(size is None or type(size.value) is int and size.value==8,'actual pointer/CU size coherence')
 alignment=pointer.attributes.get('DW_AT_alignment');require((alignment is None or type(alignment.value) is int and alignment.value>0) and (None if alignment is None else alignment.value)==descriptor['alignment'],'actual raw pointer alignment metadata')
 wrapper=reference(pointer);require(wrapper.tag==descriptor['target_tag']=='DW_TAG_const_type' and text(wrapper)==descriptor['target_name']=='','one unnamed const qualifier only')
 terminal=reference(wrapper);require(terminal.tag=='DW_TAG_structure_type' and text(terminal)=='crypto_type','single const directly references named crypto_type structure')
 declaration=terminal.attributes.get('DW_AT_declaration');require(declaration is None or declaration.value in (False,0),'complete qualified terminal, no declaration-only type')
 size=terminal.attributes.get('DW_AT_byte_size');require(size is not None and type(size.value) is int and size.value>0,'positive actual terminal structure size')
 pending.append({'descriptor':descriptor,'terminal_key':(terminal.cu.cu_offset,terminal.offset),'terminal_byte_size':size.value})
 return descriptor


def bind_qualified_targets(pending,records,layouts):
 """Resolve transient DIE identity against actual complete extraction records."""
 for item in pending:
  matches=[r for r in records if (r['CU_offset'],r['die_offset'])==item['terminal_key']]
  require(len(matches)==1,'qualified terminal references exactly one actually extracted complete type')
  record=matches[0];layout=layouts['crypto_type'];require(record['name']=='crypto_type' and record['byte_size']==item['terminal_byte_size'] and canonical(record)==canonical(layout),'actual referenced terminal record equals selected full crypto_type layout')
  digest=layout_digest(layout);raw=item['descriptor'];require(set(raw)==RAW_KEYS,'qualified evidence emitted only once from raw extraction')
  raw['qualified_pointee']={'schema':SCHEMA,'raw_pointer':dict(raw),'qualifiers':[{'tag':'DW_TAG_const_type','name':''}],'terminal':{'tag':'DW_TAG_structure_type','name':'crypto_type','byte_size':record['byte_size'],'declaration':False,'layout_sha256':digest},'binding':'actual_DIE_reference_to_complete_extracted_layout'}


def require_qualified_target(type_pointer,layouts):
 require(set(type_pointer)==RAW_KEYS|{'qualified_pointee'},'exact qualified pointer descriptor schema')
 evidence=type_pointer['qualified_pointee'];require(type(evidence) is dict and set(evidence)=={'schema','raw_pointer','qualifiers','terminal','binding'},'exact scoped qualified evidence schema')
 raw={k:type_pointer[k] for k in RAW_KEYS};require(evidence['schema']==SCHEMA and evidence['raw_pointer']==raw and raw['kind']=='pointer' and type(raw['byte_size']) is int and raw['byte_size']==8 and raw['target_tag']=='DW_TAG_const_type' and raw['target_name']=='','qualified evidence agrees with preserved actual raw pointer')
 require(type(evidence['qualifiers']) is list and evidence['qualifiers']==[{'tag':'DW_TAG_const_type','name':''}],'exact single-const qualifier evidence')
 terminal=evidence['terminal'];require(type(terminal) is dict and set(terminal)=={'tag','name','byte_size','declaration','layout_sha256'},'exact complete qualified terminal schema')
 layout=layouts['types']['crypto_type'];require(terminal['tag']=='DW_TAG_structure_type' and terminal['name']=='crypto_type' and terminal['declaration'] is False and type(terminal['byte_size']) is int and terminal['byte_size']>0 and terminal['byte_size']==layout['byte_size'] and terminal['layout_sha256']==layout_digest(layout) and evidence['binding']=='actual_DIE_reference_to_complete_extracted_layout','qualified terminal bound to actual full selected crypto_type layout')
