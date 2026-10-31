"""New shash registration, typed callback slots and descriptor bridge: static only."""
import hashlib,io,json,re,struct
from kernel_trial_object import parse_elf
from pre_pm_archive_contract import require
from sha256_provider_object import one_symbol,exact_target
from relocation_trial_kernel_profile import gpr_only
from shash_core_dwarf import extract_layouts
from shash_core_clamped_cfg import registration_cfg_dispatch
from shash_core_instructions import decode,trace,add,load
ESSENTIAL=('crypto_register_shashes','crypto_register_shash','crypto_unregister_shash','shash_prepare_alg','crypto_shash_init_tfm','crypto_alloc_shash','crypto_shash_update','crypto_shash_final','crypto_shash_finup','crypto_shash_digest')
ROW=re.compile(r'\s*([0-9a-f]+):\s+((?:[0-9a-f]{2} ){3}[0-9a-f]{2}|[0-9a-f]{8})\s+([a-zA-Z.][a-zA-Z0-9.]*)\s*(.*?)\s*')
SOURCE_SHA='0f4c16dc648eedd16f8eadbbf6877d2b15c57d68d303e05d4859519d9e0ae8ea'

def raw_reference(obj,section,offset):
 refs=[r for r in obj['relocations'] if r['section']==section and r['offset']==offset]
 require(len(refs)==1 and refs[0]['type']==257,'unique actual ABS64 callback relocation');return refs[0]

def exact_reference(rel,target):
 sym=rel['symbol'];ref={'section':sym['section'],'offset':sym['value']+rel['addend'],'addend':rel['addend'],'symbol_name':sym['name'],'symbol_value':sym['value'],'symbol_info':sym['info'],'symbol_size':sym['size']}
 exact_target(ref,target)

def member(layouts,typ,name):
 matches=[m for m in layouts['types'][typ]['members'] if m['name']==name];require(len(matches)==1,'actual unique typed member '+typ+'.'+name);return matches[0]

def frame_rows(text):
 result={}
 for line in text.splitlines():
  if not line:continue
  fields=line.rsplit('\t',2);require(len(fields)==3 and fields[1].isdigit() and fields[2] in ('static','dynamic','dynamic,bounded'),'actual known stack-usage classification')
  name=fields[0].rsplit(':',1)[-1];require(name and name not in result,'unique actual emitted stack frame');result[name]={'bytes':int(fields[1]),'classification':fields[2],'fixed_frame_only':fields[2]=='static'}
 return result

def configuration(raw):
 values={}
 for line in raw.decode('ascii').splitlines():
  if line.startswith('CONFIG_') and '=' in line:
   k,v=line.split('=',1);require(k not in values,'unambiguous config');values[k]=v
  elif line.startswith('# CONFIG_') and line.endswith(' is not set'):values[line[2:-11]]='n'
 return {key:values.get(key,'n') for key in ('CONFIG_CRYPTO_FIPS','CONFIG_NET','CONFIG_PROC_FS','CONFIG_ARM64_4K_PAGES','CONFIG_CRYPTO_HASH','CONFIG_CRYPTO_HASH2')}

def table_proof(obj,layouts,oracle,config):
 symbol=one_symbol(obj,'crypto_shash_type',1);section=obj['sections'][symbol['section']];require(section['flags']&2 and not section['flags']&5,'actual passive type table readonly NX')
 size=layouts['types']['crypto_type']['byte_size'];require(symbol['size']==size,'real crypto_type table extent');raw=bytearray(section['bytes'][symbol['value']:symbol['value']+size]);expected={}
 targets={'extsize':'crypto_alg_extsize','init_tfm':'crypto_shash_init_tfm','report':'crypto_shash_report'}
 if config['CONFIG_PROC_FS']=='y':targets['show']='crypto_shash_show'
 facts=[]
 for field,target in targets.items():
  m=member(layouts,'crypto_type',field);require(m['type']['kind']=='pointer' and m['type']['byte_size']==8,'actual function pointer table member');rel=raw_reference(obj,symbol['section'],symbol['value']+m['offset']);sym=rel['symbol']
  if target=='crypto_alg_extsize':require(sym['name']==target and sym['section']==0 and rel['addend']==0,'named unresolved extsize edge')
  else:exact_reference(rel,one_symbol(obj,target,2))
  require(raw[m['offset']:m['offset']+8]==bytes(8),'actual RELA callback storage');expected[symbol['value']+m['offset']]=rel;facts.append({'member':field,'offset':m['offset'],'target':target,'external_execution_edge':True})
 constants={'type':oracle['values']['CRYPTO_ALG_TYPE_SHASH'],'maskclear':(~oracle['values']['CRYPTO_ALG_TYPE_MASK'])&0xffffffff,'maskset':oracle['values']['CRYPTO_ALG_TYPE_MASK'],'tfmsize':oracle['values']['crypto_shash.base.offset']}
 for field,value in constants.items():
  m=member(layouts,'crypto_type',field);require(m['type']['byte_size']==4 and int.from_bytes(raw[m['offset']:m['offset']+4],'little')==value,'actual type-table scalar '+field);raw[m['offset']:m['offset']+4]=bytes(4)
 require(not any(raw),'all unused table fields/padding zero')
 rels=[r for r in obj['relocations'] if r['section']==symbol['section'] and symbol['value']<=r['offset']<symbol['value']+size];require(len(rels)==len(expected) and {r['offset'] for r in rels}==set(expected),'exact active table relocation inventory')
 return {'symbol':symbol,'callbacks':facts,'scalars':constants,'initcall_invented':False,'runtime_type_available':False}

def object_rows(obj,text):
 rows={};headers={};current=None
 for line in text.splitlines():
  if line.startswith('Disassembly of section '):
   match=re.fullmatch(r'Disassembly of section ([A-Za-z0-9_.$]+):',line);require(match is not None,'exact observed disassembly section header')
   found=[section for section in obj['sections'] if section['name']==match[1]];require(len(found)==1,'observed header binds unique actual object section');current=found[0]
   require(current['index'] not in headers,'one observed header per actual section');headers[current['index']]=line;continue
  match=ROW.fullmatch(line)
  if not match:continue
  require(current is not None,'new instruction section');off=int(match[1],16);encoded=bytes.fromhex(match[2]);encoded=encoded[::-1] if len(match[2])==8 else encoded
  require(len(encoded)==4 and current['bytes'][off:off+4]==encoded and (current['index'],off) not in rows,'actual new object/disassembly bytes');rows[current['index'],off]=line
 return {'instruction_rows':rows,'observed_section_headers':headers}

def scoped_input(obj,fn,record):
 require(fn['info']&15==2 and 0<fn['section']<len(obj['sections']),'actual scoped function section/type')
 section=obj['sections'][fn['section']];start=fn['value'];end=start+fn['size'];require(start%4==0 and fn['size']>0 and fn['size']%4==0 and end<=len(section['bytes']),'actual scoped function extent')
 header=record['observed_section_headers'].get(fn['section']);require(header is not None and header=='Disassembly of section '+section['name']+':','preserve exact observed header for actual function section')
 words={};selected=[]
 for off in range(start,end,4):
  row=record['instruction_rows'].get((fn['section'],off));require(row is not None,'every scoped instruction present in its actual section');match=ROW.fullmatch(row);require(match is not None and int(match[1],16)==off,'preserve actual scoped row address')
  encoded=bytes.fromhex(match[2]);encoded=encoded[::-1] if len(match[2])==8 else encoded;require(len(encoded)==4 and encoded==section['bytes'][off:off+4],'preserve actual scoped instruction bytes')
  words[off]=struct.unpack_from('<I',section['bytes'],off)[0];selected.append(row)
 return words,header+'\n'+'\n'.join(selected)


def function_facts(obj,fn,rows,frames):
 require(fn['size']>0 and fn['size']%4==0 and fn['name'] in frames,'actual essential function and stack row; no missing zero inference');sec=obj['sections'][fn['section']];start=fn['value'];end=start+fn['size'];require(end<=len(sec['bytes']),'actual function extent');words,text=scoped_input(obj,fn,rows)
 isa=gpr_only(text)
 for off,word in words.items():
  if decode(word)['op']=='unknown':raise ValueError('unsupported finite GPR word: function='+fn['name']+' section='+sec['name']+' offset='+hex(off)+' word='+hex(word)+' object_sha256='+obj.get('sha256','unavailable'))
 rels={};calls={};external=[]
 for rel in obj['relocations']:
  if rel['section']!=fn['section'] or not start<=rel['offset']<end:continue
  require(rel['offset'] not in rels and rel['type'] in (275,277,282,283),'finite scoped new relocation kinds');sym=rel['symbol'];identity=(sym['name'],sym['section'],sym['value'],rel['addend'],sym['info'],sym['size']);rels[rel['offset']]={'type':rel['type'],'identity':identity}
  if rel['type'] in (282,283):
   require(decode(words[rel['offset']])['op']==('b' if rel['type']==282 else 'bl'),'actual direct edge opcode/relocation')
   if sym['section']==0:require(sym['name'] and rel['addend']==0,'named external edge');name=sym['name'];external.append(name)
   else:
    found=[s for s in obj['symbols'] if s['info']&15==2 and s['section']==sym['section'] and s['value']==sym['value']+rel['addend']];require(len(found)==1,'exact defined direct-edge target');name=found[0]['name']
   calls[rel['offset']]=name
 events=trace(words,rels,calls)
 return {'symbol':fn,'frame':frames[fn['name']],'ISA':isa,'events':events,'direct_calls':[{'offset':off,'target':name,'external':name in external} for off,name in sorted(calls.items())],'external_execution_edges':external,'whole_path_stack_bound':None}

def require_calls(fact,names):
 observed=[r['target'] for r in fact['direct_calls']]
 for name in names:require(name in observed,'essential actual direct call edge '+name)

def descriptor_proof(fact,layouts):
 tfm_alg=member(layouts,'crypto_tfm','__crt_alg')['offset'];alg_base=member(layouts,'shash_alg','base')['offset'];descsize=member(layouts,'shash_alg','descsize')['offset'];hashbase=member(layouts,'crypto_shash','base')['offset'];hashsize=member(layouts,'crypto_shash','descsize')['offset']
 expected=load(load(('arg',0),tfm_alg,8),descsize-alg_base,4);address=add(('arg',0),hashsize-hashbase)
 stores=[e for e in fact['events'] if e['decoded']['op']=='store' and e.get('address')==address and e.get('value')==expected and e.get('size')==4];require(len(stores)==1,'actual typed descsize load/store transfer')
 return {'store_offset':stores[0]['offset'],'value':expected,'destination':address,'descriptor_allocation_proven':False}

def dispatch_proof(fact,layouts,field):
 tfm=load(('arg',0),member(layouts,'shash_desc','tfm')['offset'],8);base=member(layouts,'crypto_shash','base')['offset'];alg=load(tfm,base+member(layouts,'crypto_tfm','__crt_alg')['offset'],8);slot=member(layouts,'shash_alg',field)
 require(slot['type']['kind']=='pointer' and slot['type']['byte_size']==8,'actual typed synchronous callback slot');expected=load(alg,slot['offset']-member(layouts,'shash_alg','base')['offset'],8)
 selected=[e for e in fact['events'] if e['decoded']['op'] in ('blr','br') and e.get('target')==expected and e.get('arguments',[None])[0]==('arg',0)];require(len(selected)==1,'actual finite typed callback load/call/desc argument '+field)
 return {'call_offset':selected[0]['offset'],'slot':field,'slot_offset':slot['offset'],'actual_target_expression':expected,'callback_execution_unresolved':True,'aligned_path_only':True}

def registration_proof(facts,layouts):
 many=facts['crypto_register_shashes'];single=facts['crypto_register_shash'];unregister=facts['crypto_unregister_shash'];require_calls(many,('crypto_register_shash','crypto_unregister_shash'));require_calls(single,('shash_prepare_alg','crypto_register_alg'));require_calls(unregister,('crypto_unregister_alg',))
 stride=layouts['types']['shash_alg']['byte_size'];events=many['events'];forward=[e for e in events if e['decoded']['op']=='add' and e['decoded'].get('imm')==stride and e['decoded'].get('width')==64];backward=[e for e in events if e['decoded']['op']=='sub' and e['decoded'].get('imm')==stride and e['decoded'].get('width')==64]
 require(forward and backward,'actual register/rollback pointer stride equal actual DWARF shash_alg size')
 backward_edges=[e for e in events if e['decoded']['op'] in ('b','cond','cb') and e['decoded'].get('delta',0)<0];require(len(backward_edges)>=2,'actual registration and rollback loop backedges')
 counters=[e for e in events if e['decoded']['op'] in ('add','sub') and e['decoded'].get('imm')==1 and e['decoded'].get('width')==32];require(len(counters)>=2,'actual finite element-count induction operations')
 # Require both error-dependent and count-dependent branch evidence, never source text alone.
 branches=[e for e in events if e['decoded']['op'] in ('cond','cb')];require(any(e['decoded']['op']=='cb' and e['decoded']['rn']==0 for e in branches),'actual registration return-value branch')
 require(any(e['decoded']['op']=='cond' and e['decoded']['condition'] in (10,11,12,13) for e in branches),'actual signed count/rollback termination branch')
 register_call=next(r['offset'] for r in many['direct_calls'] if r['target']=='crypto_register_shash');unregister_call=next(r['offset'] for r in many['direct_calls'] if r['target']=='crypto_unregister_shash')
 by={e['offset']:e for e in events}
 def pointer_argument(call):
  previous=by.get(call-4,{}).get('decoded',{})
  require(previous.get('op')=='mov' and previous.get('rd')==0 and previous.get('width')==64 and previous.get('rn',0)>=19,'actual callee-saved pointer argument immediately before registration call')
  return previous['rn']
 pointer=pointer_argument(register_call);require(pointer_argument(unregister_call)==pointer,'same actual registration/rollback pointer induction register')
 require(any(e['decoded'].get('op')=='mov' and e['decoded'].get('rd')==pointer and e.get('source_value')==('arg',0) for e in events),'actual initial array pointer argument')
 require(any(e['decoded']['rd']==pointer and e['decoded']['rn']==pointer for e in forward) and any(e['decoded']['rd']==pointer and e['decoded']['rn']==pointer for e in backward),'actual stride updates the passed pointer')
 branch=by.get(register_call+4,{}).get('decoded',{});require(branch.get('op')=='cb' and branch.get('rn')==0 and branch.get('nonzero') is True,'actual registration failure return branch immediately after call')
 count_regs={e['decoded']['rd'] for e in events if e['decoded']['op']=='mov' and e['decoded'].get('width')==32 and e.get('source_value')==('arg',1)}
 require(count_regs and any(e['decoded']['rd'] in count_regs and e['decoded']['rn']==e['decoded']['rd'] for e in counters),'actual count argument supplies induction register')
 saved_errors={e['decoded']['rd'] for e in events if e['decoded']['op']=='mov' and e['decoded'].get('width')==32 and e['decoded'].get('rd',0)>=19 and e.get('source_value')==('return',register_call,'crypto_register_shash')}
 require(saved_errors and any(e['decoded']['op']=='mov' and e['decoded'].get('rd')==0 and e['decoded'].get('rn') in saved_errors for e in events),'actual error return preserved across rollback calls')
 return {'direct_registration_edges':many['direct_calls'],'actual_element_stride':stride,'forward_stride_offsets':[e['offset'] for e in forward],'rollback_stride_offsets':[e['offset'] for e in backward],'loop_branch_offsets':[e['offset'] for e in backward_edges],'count_induction_offsets':[e['offset'] for e in counters],'existential_event_scan_only':True,'connected_CFG_claim':False,'arbitrary_count_runtime_safety_proven':False,'registration_success_proven':False}

def address_target(value,obj,name,kind):
 if not isinstance(value,tuple) or value[0]!='address':return False
 identity=value[1]
 rel={'symbol':dict(zip(('name','section','value'),identity[:3]),info=identity[4],size=identity[5]),'addend':identity[3]}
 exact_reference(rel,one_symbol(obj,name,kind));return True

def preparation_proof(fact,layouts,oracle,obj):
 events=fact['events'];bound=oracle['values']['PAGE_SIZE']//8;loads={e.get('address'):e for e in events if e['decoded']['op']=='load'}
 for field in ('digestsize','descsize','statesize'):require(add(('arg',0),member(layouts,'shash_alg',field)['offset']) in loads,'actual preparation size field read '+field)
 comparisons=[e for e in events if e['decoded']['op']=='sub' and e['decoded'].get('flags') and e['decoded'].get('rd')==31 and e['decoded'].get('imm')==bound];by={e['offset']:e for e in events}
 for field in ('digestsize','descsize','statesize'):
  expected=load(('arg',0),member(layouts,'shash_alg',field)['offset'],4);matches=[e for e in comparisons if e.get('source_value')==expected];require(matches,'each actual size compared to PAGE_SIZE/8 '+field)
  for compare in matches:
   branch=by.get(compare['offset']+4,{});d=branch.get('decoded',{});require(d.get('op')=='cond' and d.get('condition')==8,'finite immediate unsigned-too-large validation branch')
   target=branch['offset']+d['delta'];error=by.get(target,{}).get('decoded',{});require(error.get('op')=='movn' and error.get('rd')==0 and error.get('width')==32 and error.get('imm')==21 and by.get(target+4,{}).get('decoded',{}).get('op')=='ret','actual EINVAL return target for each size failure')
 stores=[e for e in events if e['decoded']['op']=='store'];defaults={'finup':'shash_finup_unaligned','digest':'shash_digest_unaligned','export':'shash_default_export','import':'shash_default_import','setkey':'shash_no_setkey'};offsets={member(layouts,'shash_alg',name)['offset']:name for name in defaults}
 for offset,name in offsets.items():
  selected=[e for e in stores if e.get('address')==add(('arg',0),offset) and address_target(e.get('value'),obj,defaults[name],2)];require(selected,'actual default callback address store '+name)
  tested='export' if name=='import' else name;condition=load(('arg',0),member(layouts,'shash_alg',tested)['offset'],8)
  require(any(e['decoded']['op']=='cb' and e['decoded'].get('nonzero') and e.get('condition_value')==condition and e['offset']<store['offset']<e['offset']+e['decoded']['delta'] for e in events for store in selected),'actual absent-callback guard skips default store '+name)
 algbase=member(layouts,'shash_alg','base')['offset'];cra_type=algbase+member(layouts,'crypto_alg','cra_type')['offset'];require(any(e.get('address')==add(('arg',0),cra_type) and address_target(e.get('value'),obj,'crypto_shash_type',1) for e in stores),'actual crypto_shash_type pointer store')
 flags_offset=algbase+member(layouts,'crypto_alg','cra_flags')['offset'];mask=oracle['values']['CRYPTO_ALG_TYPE_MASK'];shash=oracle['values']['CRYPTO_ALG_TYPE_SHASH']
 flags_value=('orr',('and',load(('arg',0),flags_offset,4),(~mask)&0xffffffff,32),shash,32)
 require(any(e.get('address')==add(('arg',0),flags_offset) and e.get('value')==flags_value and e.get('size')==4 for e in stores),'actual typed SHASH flag mask and value store')
 statesize=member(layouts,'shash_alg','statesize')['offset'];descsize=member(layouts,'shash_alg','descsize')['offset'];require(any(e.get('address')==add(('arg',0),statesize) and e.get('value')==load(('arg',0),descsize,4) for e in stores),'actual default statesize transfer')
 return {'bound_compiler_PAGE_SIZE_div8':bound,'compare_offsets':[e['offset'] for e in comparisons],'actual_callback_store_offsets':[e['offset'] for e in stores if e.get('address') in [add(('arg',0),n) for n in offsets]],'runtime_admission_or_default_behavior_executed':False}

def shash_object_proof(raw,text,usage,ELFFile,headers,oracle,config):
 require(hashlib.sha256(headers['crypto/shash.c']).hexdigest()==SOURCE_SHA,'unmodified pinned new stock source');obj=parse_elf(raw,1);layouts=extract_layouts(ELFFile(io.BytesIO(raw)),oracle);cfg=configuration(config);require(cfg['CONFIG_ARM64_4K_PAGES']=='y' and cfg['CONFIG_CRYPTO_HASH']=='y' and cfg['CONFIG_CRYPTO_HASH2']=='y','actual core configuration')
 require(b'crypto_hash-y += shash.o' in headers['crypto/Makefile'] and b'obj-$(CONFIG_CRYPTO_HASH2) += crypto_hash.o' in headers['crypto/Makefile'],'actual composite source inclusion plan')
 rows=object_rows(obj,text);frames=frame_rows(usage);facts={name:function_facts(obj,one_symbol(obj,name,2),rows,frames) for name in ESSENTIAL};table=table_proof(obj,layouts,oracle,cfg)
 dispatch={field:dispatch_proof(facts['crypto_shash_'+field],layouts,field) for field in ('update','final','finup','digest')};desc=descriptor_proof(facts['crypto_shash_init_tfm'],layouts);registration=registration_cfg_dispatch(obj,facts['crypto_register_shashes']['symbol'],layouts['types']['shash_alg']['byte_size']);prepare=preparation_proof(facts['shash_prepare_alg'],layouts,oracle,obj)
 require_calls(facts['crypto_alloc_shash'],('crypto_alloc_tfm',))
 alloc_calls=[e for e in facts['crypto_alloc_shash']['events'] if e.get('target')=='crypto_alloc_tfm']
 require(len(alloc_calls)==1 and address_target(alloc_calls[0]['arguments'][1],obj,'crypto_shash_type',1),'actual alloc_shash type argument; allocation still external/unproved')
 return json.loads(json.dumps({'object_sha256':obj['sha256'],'layouts':layouts,'configuration_branches':cfg,'type_table':table,'functions':facts,'registration':registration,'preparation':prepare,'typed_callback_dispatch':dispatch,'descriptor_size_bridge':desc,'all_actual_stack_rows':frames,'external_and_dynamic_stack_bound':None,'source_header_init_inline':'source-only header inline; no fabricated init symbol or stack frame','runtime_registration_provider_allocation_or_callback_execution_proven':False,'whole_OS_stack_safety_proven':False,'object_or_oracle_executed':False}))
