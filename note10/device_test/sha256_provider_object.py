"""Actual provider table, registration and scoped code facts; no execution/link claim."""
import io,re,struct
from kernel_trial_object import parse_elf,usage_frames
from relocation_trial_instructions import ROW
from relocation_trial_kernel_profile import gpr_only
from pre_pm_archive_contract import require
from sha256_provider_dwarf import extract_layouts

def one_symbol(obj,name,kind=None):
 rows=[s for s in obj['symbols'] if s['name']==name and (kind is None or s['info']&15==kind)]
 require(len(rows)==1,'unique actual symbol: '+name);s=rows[0];require(0<s['section']<len(obj['sections']),'defined actual symbol: '+name)
 require(s['value']+s['size']<=len(obj['sections'][s['section']]['bytes']),'symbol actual extent');return s

def reference(obj,section,offset,width=8):
 require(width==8,'actual AArch64 absolute pointer width');refs=[r for r in obj['relocations'] if r['section']==section and r['offset']==offset]
 require(len(refs)==1 and refs[0]['type']==257,'unique actual absolute pointer relocation');r=refs[0];s=r['symbol'];target=s['value']+r['addend']
 require(0<s['section']<len(obj['sections']) and 0<=target<len(obj['sections'][s['section']]['bytes']),'defined exact reference target')
 return {'section':s['section'],'offset':target,'addend':r['addend'],'symbol_name':s['name'],'symbol_value':s['value'],'symbol_info':s['info'],'symbol_size':s['size'],'relocation_type':r['type']}
def exact_target(ref,target):
 require(ref['section']==target['section'] and ref['offset']==target['value'],'exact target section/location')
 direct=ref['symbol_name']==target['name'] and ref['symbol_value']==target['value'] and ref['symbol_size']==target['size'] and ref['addend']==0
 section=ref['symbol_name']=='' and ref['symbol_info']&15==3 and ref['symbol_value']==0 and ref['symbol_size']==0 and ref['addend']==target['value']
 require(direct or section,'no compensating symbol/addend or arbitrary alias target')

def member(layout,name):
 found=[m for m in layout['members'] if m['name']==name];require(len(found)==1,'essential actual member: '+name);return found[0]
def integer(data,at,typ):
 require(typ['kind'] in ('base','enumeration') and 0<typ['byte_size']<=8,'actual scalar type extent');return int.from_bytes(data[at:at+typ['byte_size']],'little')
def inline_name(data,at,typ,expected):
 require(typ['kind']=='array' and typ['element']['byte_size']==1 and typ['count'] is not None,'actual inline character array')
 raw=expected.encode()+b'\0';require(len(raw)<=typ['byte_size'] and data[at:at+typ['byte_size']]==raw+b'\0'*(typ['byte_size']-len(raw)),'actual provider inline name/padding')

def table_proof(obj,layouts,constants):
 table=one_symbol(obj,'sha256_algs',1);alg=layouts['types']['shash_alg'];base=layouts['types']['crypto_alg'];state=layouts['types']['sha256_state'];size=alg['byte_size']
 require(table['size']==2*size and obj['sections'][table['section']]['flags']&2,'actual allocated provider array extent')
 data=obj['sections'][table['section']]['bytes'];start=table['value'];entries=[];covered=set();expected_relocations=set()
 callbacks=({'init':'sha256_base_init','update':'crypto_sha256_update','final':'sha256_final','finup':'crypto_sha256_finup'},
 {'init':'sha224_base_init','update':'crypto_sha256_update','final':'sha256_final','finup':'crypto_sha256_finup'})
 for i,callback in enumerate(callbacks):
  at=start+i*size;entry={'index':i,'callbacks':{}};base_member=member(alg,'base');require(base_member['type']['name']=='crypto_alg' and base_member['type']['byte_size']==base['byte_size'],'real nested crypto_alg type')
  for name,wanted in (('digestsize',constants['SHA256_DIGEST_SIZE'] if i==0 else constants['SHA224_DIGEST_SIZE']),('descsize',state['byte_size'])):
   m=member(alg,name);actual=integer(data,at+m['offset'],m['type']);require(actual==wanted,'actual registered digest/descriptor size: '+name);entry[name]=actual;covered.update(range(i*size+m['offset'],i*size+m['offset']+m['type']['byte_size']))
  for name,target_name in callback.items():
   m=member(alg,name);require(m['type']['kind']=='pointer' and m['type']['target_tag']=='DW_TAG_subroutine_type','actual function-pointer member type')
   require(data[at+m['offset']:at+m['offset']+m['type']['byte_size']]==b'\0'*m['type']['byte_size'],'actual RELA pointer placeholder bytes')
   ref=reference(obj,table['section'],at+m['offset'],m['type']['byte_size']);target=one_symbol(obj,target_name,2)
   exact_target(ref,target);entry['callbacks'][name]=dict(ref,target_name=target_name)
   expected_relocations.add(at+m['offset']);covered.update(range(i*size+m['offset'],i*size+m['offset']+m['type']['byte_size']))
  for name,value in (('cra_name','sha256' if i==0 else 'sha224'),('cra_driver_name','sha256-generic' if i==0 else 'sha224-generic')):
   m=member(base,name);where=base_member['offset']+m['offset'];inline_name(data,at+where,m['type'],value);entry[name]=value;covered.update(range(i*size+where,i*size+where+m['type']['byte_size']))
  for name,wanted in (('cra_flags',constants['CRYPTO_ALG_TYPE_SHASH']),('cra_blocksize',constants['SHA256_BLOCK_SIZE'] if i==0 else constants['SHA224_BLOCK_SIZE'])):
   m=member(base,name);where=base_member['offset']+m['offset'];require(integer(data,at+where,m['type'])==wanted,'actual algorithm source constant: '+name);entry[name]=wanted;covered.update(range(i*size+where,i*size+where+m['type']['byte_size']))
  entries.append(entry)
 actual={r['offset'] for r in obj['relocations'] if r['section']==table['section'] and start<=r['offset']<start+table['size']}
 require(actual==expected_relocations,'exact registered table relocation inventory; no extra fields')
 require(all(data[start+j]==0 for j in range(table['size']) if j not in covered),'source-uninitialized provider fields/padding zero')
 return {'symbol':table,'element_size_from_DWARF':size,'entries':entries,'registered_array_mutable_data':bool(obj['sections'][table['section']]['flags']&1)}

def registration_proof(obj,table):
 init=one_symbol(obj,'sha256_generic_mod_init',2);section=obj['sections'][init['section']];begin=init['value'];end=begin+init['size'];rels=[r for r in obj['relocations'] if r['section']==init['section'] and begin<=r['offset']<end]
 call=[r for r in rels if r['type'] in (282,283) and r['symbol']['section']==0 and r['symbol']['name']=='crypto_register_shashes' and r['addend']==0];require(len(call)==1,'actual unique unresolved registration call')
 call=call[0];code=section['bytes'];word=lambda off:struct.unpack_from('<I',code,off)[0]
 require(word(call['offset'])>>26==(37 if call['type']==283 else 5),'actual registration branch opcode/type')
 pairs=[]
 for high in rels:
  if high['type']!=275:continue
  lows=[r for r in rels if high['offset']<r['offset']<call['offset'] and r['type']==277 and r['symbol']==high['symbol'] and r['addend']==high['addend']]
  if len(lows)!=1:continue
  low=lows[0]
  require(high['symbol']==low['symbol'] and high['addend']==low['addend'],'paired registration address relocation identity/addend')
  s=high['symbol'];target=(s['section'],s['value']+high['addend'])
  if target!=(table['section'],table['value']):continue
  exact_target({'section':s['section'],'offset':target[1],'symbol_name':s['name'],'symbol_value':s['value'],'symbol_info':s['info'],'symbol_size':s['size'],'addend':high['addend']},table)
  require(word(high['offset'])&0x9f00001f==0x90000000 and word(low['offset'])&0xffc003ff==0x91000000,'actual ADRP/ADD target argument x0')
  pairs.append((high,low))
 require(len(pairs)==1,'actual unique array pointer argument pair');high,low=pairs[0];require(low['offset']<call['offset'],'array pointer before registration call')
 counts=[off for off in range(begin,call['offset'],4) if word(off)==0x52800041]
 require(len(counts)==1,'actual registration count2')
 for off in range(min(high['offset'],counts[0]),call['offset'],4):
  if off in (high['offset'],low['offset'],counts[0]):continue
  require(word(off) in (0xd503201f,0xa9bf7bfd,0x910003fd),'unrecognized intervening registration argument/control instruction')
 initcall=[s for s in obj['symbols'] if s['name'].startswith('__initcall_sha256_generic_mod_init') and s['info']&15==1]
 require(len(initcall)==1 and initcall[0]['size']==8,'actual unique initcall pointer symbol');root=initcall[0]
 require(obj['sections'][root['section']]['name'].startswith('.initcall'),'real initcall allocated section')
 ref=reference(obj,root['section'],root['value']);exact_target(ref,init)
 return {'init_function':init,'array_argument_relocations':[{'offset':r['offset'],'type':r['type'],'symbol':r['symbol'],'addend':r['addend']} for r in (high,low)],'count_argument_offset':counts[0],'count':2,'registration_call_offset':call['offset'],'registration_external_symbol':'crypto_register_shashes','initcall_symbol':root,'initcall_target':ref,'runtime_registration_or_init_order_proven':False}

def code_proof(obj,text,usage):
 functions=[s for s in obj['symbols'] if s['info']&15==2 and s['section']!=0];require(0<len(functions)<256 and len({s['name'] for s in functions})==len(functions),'finite actual provider functions')
 sections={s['name']:s for s in obj['sections']};rows={};current=None
 for line in text.splitlines():
  if line.startswith('Disassembly of section '):current=sections.get(line.removeprefix('Disassembly of section ').removesuffix(':'));continue
  m=ROW.fullmatch(line)
  if not m:continue
  require(current is not None,'actual disassembly section');off=int(m[1],16);raw=bytes.fromhex(m[2]);raw=raw[::-1] if len(m[2])==8 else raw
  require(current['bytes'][off:off+4]==raw and (current['index'],off) not in rows,'actual object/instruction byte binding');rows[current['index'],off]=line
 frames=usage_frames(usage);facts=[];external=[];edges=[];code_refs=[]
 for fn in functions:
  require(fn['size']>0 and fn['size']%4==0 and not fn['name'].startswith('OUTLINED_FUNCTION_'),'complete nonoutlined actual function')
  selected=[rows.get((fn['section'],off)) for off in range(fn['value'],fn['value']+fn['size'],4)];require(all(selected),'every provider function instruction decoded')
  section=obj['sections'][fn['section']];start=fn['value'];end=start+fn['size']
  for off in range(start,end,4):
   word=struct.unpack_from('<I',section['bytes'],off)[0];rels=[r for r in obj['relocations'] if r['section']==fn['section'] and r['offset']==off]
   if word>>26 in (5,37):
    if rels:
     require(len(rels)==1 and rels[0]['type']==(283 if word>>26==37 else 282),'actual branch relocation kind/opcode')
     rel=rels[0];sym=rel['symbol'];target=sym['value']+rel['addend']
     if sym['section']==0:require(sym['name'] and rel['addend']==0,'named unresolved external edge');target_name=sym['name']
     else:
      owners=[f for f in functions if f['section']==sym['section'] and f['value']==target];require(len(owners)==1,'actual defined call/tail target');target_name=owners[0]['name']
     edges.append({'caller':fn['name'],'offset':off,'target':target_name,'relocation_type':rel['type'],'unresolved':sym['section']==0})
    else:
     delta=word&0x3ffffff;delta=delta-(1<<26) if delta&(1<<25) else delta;target=off+4*delta
     require(start<=target<end,'resolved direct provider branch escapes its function without relocation');edges.append({'caller':fn['name'],'offset':off,'local_target':target,'unresolved':False})
   elif word&0xff000010==0x54000000 or word&0x7e000000 in (0x34000000,0x36000000):
    bits=14 if word&0x7e000000==0x36000000 else 19;imm=(word>>5)&((1<<bits)-1);imm=imm-(1<<bits) if imm&(1<<(bits-1)) else imm;target=off+4*imm
    require(not rels and start<=target<end,'bounded actual local conditional branch')
   elif word&0xfffffc1f in (0xd61f0000,0xd63f0000):raise ValueError('essential provider indirect control target unavailable')
   for rel in rels:
    require(rel['type'] in (275,277,278,282,283,284,285,286),'unsupported actual code relocation')
    if rel['type'] not in (282,283):
     sym=rel['symbol'];target=sym['value']+rel['addend'];require(0<sym['section']<len(obj['sections']) and 0<=target<len(obj['sections'][sym['section']]['bytes']),'actual code data/reference target bound')
     code_refs.append({'function':fn['name'],'offset':off,'type':rel['type'],'target_section':obj['sections'][sym['section']]['name'],'target_offset':target,'symbol':sym['name'],'addend':rel['addend']})
  policy=gpr_only('Disassembly of section .text:\n'+'\n'.join(selected));require(type(frames.get(fn['name'])) is int,'actual static scoped .su frame missing/dynamic: '+fn['name'])
  for r in obj['relocations']:
   if r['section']==fn['section'] and fn['value']<=r['offset']<fn['value']+fn['size'] and r['type'] in (282,283):
    require(r['addend']==0 or r['symbol']['section']!=0,'unresolved external addend')
    if r['symbol']['section']==0:external.append({'caller':fn['name'],'offset':r['offset'],'symbol':r['symbol']['name'],'type':r['type'],'unresolved':True})
  facts.append({'name':fn['name'],'section':obj['sections'][fn['section']]['name'],'value':fn['value'],'size':fn['size'],'compiler_frame':frames[fn['name']],'ISA':policy})
 return {'functions':facts,'actual_control_edges':edges,'actual_code_references':code_refs,'external_calls':external,'sum_scoped_emitted_frames':sum(x['compiler_frame'] for x in facts),'external_whole_path_stack_bounded':False,'physical_stack_safety_proven':False}

def constants_from(headers):
 result={}
 for name in ('SHA256_DIGEST_SIZE','SHA224_DIGEST_SIZE','SHA256_BLOCK_SIZE','SHA224_BLOCK_SIZE','CRYPTO_ALG_TYPE_SHASH'):
  found=[]
  for raw in headers:
   found+=re.findall(rb'^#define[ \t]+'+name.encode()+rb'[ \t]+(0x[0-9a-fA-F]+|[0-9]+)(?:[uUlL]*)[ \t]*$',raw,re.M)
  require(len(found)==1,'unique real source constant: '+name);result[name]=int(found[0],0)
 return result

def provider_object_proof(raw,text,usage,ELFFile,headers):
 obj=parse_elf(raw,1);layouts=extract_layouts(ELFFile(io.BytesIO(raw)));constants=constants_from(headers)
 table=table_proof(obj,layouts,constants);registration=registration_proof(obj,table['symbol']);code=code_proof(obj,text,usage)
 return {'object_sha256':obj['sha256'],'DWARF':layouts,'source_constants':constants,'table':table,'registration':registration,'code':code,'instrumented_analysis_object_only':True,'provider_executed':False,'full_Image_link_or_runtime_availability_proven':False}
