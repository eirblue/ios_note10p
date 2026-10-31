"""Finite, owned preparation lowering; unsupported shapes fail closed.

This variant never consumes the path-insensitive legacy trace as semantic proof.
The original fact and its original rows remain in the enclosing object evidence.
"""
import hashlib,itertools,struct
from pre_pm_archive_contract import require
from sha256_provider_object import one_symbol,exact_target
from shash_core_instructions import decode,signed
from shash_core_qualified_target import require_qualified_target


def preparation_cfg_selected(obj,fn):
 """Select a separate family without catching a failed legacy proof."""
 section=obj['sections'][fn['section']];start=fn['value'];end=start+fn['size']
 require(start>=0 and start%4==0 and fn['size']>0 and fn['size']%4==0 and end<=len(section['bytes']),'owned preparation dispatcher extent')
 if fn['size']==180:return True
 for pc in range(start,end,4):
  d=decode(struct.unpack_from('<I',section['bytes'],pc)[0]);op=d['op']
  if op in ('pair-store','pair-load') and d['rn']!=31:return True
  if op=='cb' and not d['nonzero']:return True
  if op in ('b','cond','cb') and d['delta']<0:return True
  if op=='cond' and d['condition']!=8:return True
  if op=='movn' and (d['rd']!=0 or d['width']!=32):return True
 return False


def preparation_type_target(type_pointer,layouts):
 if type_pointer['target_tag']=='DW_TAG_const_type':require_qualified_target(type_pointer,layouts)
 else:require(type_pointer['target_tag']=='DW_TAG_structure_type' and type_pointer['target_name']=='crypto_type','actual cra_type points to the crypto_type structure')


def preparation_cfg(fact,layouts,oracle,obj):
 fn=fact['symbol'];require(fn['name']=='shash_prepare_alg' and one_symbol(obj,fn['name'],2)==fn and fn['info']&15==2,'unique actual preparation function identity')
 require(type(fn['section']) is int and 0<fn['section']<len(obj['sections']),'actual preparation section')
 sec=obj['sections'][fn['section']];start=fn['value'];end=start+fn['size']
 require(sec['name']=='.text.shash_prepare_alg' and start==0 and fn['size']==180 and len(sec['bytes'])==180 and sec['flags']&6==6,'isolated complete45-word executable preparation extent')
 require(not any(s['info']&15==2 and s['section']==fn['section'] and s!=fn for s in obj['symbols']),'no other function owns any preparation word')
 words={pc:struct.unpack_from('<I',sec['bytes'],start+pc)[0] for pc in range(0,180,4)};used=set();consumed=set();edges={}
 def expect(pc,op,**fields):
  require(pc in words,'owned preparation instruction');d=decode(words[pc]);used.add(pc)
  require(d==dict(op=op,**fields),'exact preparation role/operands at '+hex(pc));return d
 def member(typ,name,size,kind=None):
  rows=[m for m in layouts['types'][typ]['members'] if m['name']==name];require(len(rows)==1,'unique typed preparation member '+typ+'.'+name);m=rows[0]
  require(type(m['offset']) is int and m['offset']>=0 and m['offset']+size<=layouts['types'][typ]['byte_size'] and m['type']['byte_size']==size and (kind is None or m['type']['kind']==kind),'typed preparation member width/kind/extent')
  if size==4:require(m['type']['kind'] in ('base','enumeration'),'typed scalar preparation member')
  return m['offset']
 slots={name:member('shash_alg',name,8,'pointer') for name in ('finup','digest','export','import','setkey')}
 require(all(next(m for m in layouts['types']['shash_alg']['members'] if m['name']==n)['type']['target_tag']=='DW_TAG_subroutine_type' for n in slots),'typed callback slots point to subroutine types')
 sizes={name:member('shash_alg',name,4) for name in ('digestsize','descsize','statesize')}
 base=member('shash_alg','base',layouts['types']['crypto_alg']['byte_size']);flags=base+member('crypto_alg','cra_flags',4);type_slot=base+member('crypto_alg','cra_type',8,'pointer')
 base_type=next(m for m in layouts['types']['shash_alg']['members'] if m['name']=='base')['type'];type_pointer=next(m for m in layouts['types']['crypto_alg']['members'] if m['name']=='cra_type')['type']
 require(base_type['kind']=='structure' and base_type['name']=='crypto_alg','actual nested base is the crypto_alg structure')
 preparation_type_target(type_pointer,layouts)
 locations=[(off,size) for off,size in [(n,8) for n in slots.values()]+[(n,4) for n in sizes.values()]+[(flags,4),(type_slot,8)]]
 require(all(a+s<=b or b+t<=a for i,(a,s) in enumerate(locations) for b,t in locations[i+1:]),'all typed preparation destinations disjoint')
 require(all(off+size<=layouts['types']['shash_alg']['byte_size'] for off,size in locations),'all preparation members within actual type')
 values=oracle['values'];page=values['PAGE_SIZE'];mask=values['CRYPTO_ALG_TYPE_MASK'];shash=values['CRYPTO_ALG_TYPE_SHASH']
 require(type(page) is int and page>0 and page%8==0 and type(mask) is int and type(shash) is int and 0<=mask<=0xffffffff and 0<shash<=mask and shash&~mask==0,'exact compiler preparation constants');bound=page//8
 refs=[r for r in obj['relocations'] if r['section']==fn['section']]
 require(len(refs)==12 and all(type(r['offset']) is int and start<=r['offset']<end for r in refs) and len({r['offset'] for r in refs})==12,'exact complete preparation relocation inventory')
 byrel={r['offset']-start:r for r in refs};addresses={}
 def pair(hi,lo,name,kind):
  high=byrel.get(hi);low=byrel.get(lo);require(high is not None and low is not None and high['type']==275 and low['type']==277,'one ADRP/ADD address pair')
  target=one_symbol(obj,name,kind)
  for r in (high,low):
   s=r['symbol'];exact_target({'section':s['section'],'offset':s['value']+r['addend'],'addend':r['addend'],'symbol_name':s['name'],'symbol_value':s['value'],'symbol_size':s['size'],'symbol_info':s['info']},target)
  require(high['symbol']==low['symbol'] and high['addend']==low['addend'],'matching exact address relocation identities')
  d=decode(words[hi]);r=d.get('rd');require(type(r) is int and 1<=r<19,'finite scratch address register')
  expect(hi,'adrp',rd=r);require(words[hi]==0x90000000|r,'zero RELA ADRP immediate');expect(lo,'add',rd=r,rn=r,imm=0,flags=False,width=64);require(words[lo]==0x91000000|(r<<5)|r,'canonical unshifted address ADD');consumed.update((hi,lo));addresses[hi]=(r,name);return r
 def memory(pc,op,size,offset,rd=None):
  d=decode(words[pc]);r=d.get('rd') if rd is None else rd
  expect(pc,op,rd=r,rn=0,offset=offset,size=size)
  require(words[pc]&0xffc00000=={('load',4):0xb9400000,('load',8):0xf9400000,('store',4):0xb9000000,('store',8):0xf9000000}[op,size] and 1<=r<19,'unsigned-offset typed W/X transfer, original arg0 and scratch register')
  return r
 def branch(pc,op,target,**fields):
  expect(pc,op,delta=target-pc,**fields);edges[pc]=[target] if op=='b' else [pc+4,target]
 # Exact connected size phase. The second load must survive until export absence.
 digest_reg=memory(0,'load',4,sizes['digestsize']);desc_reg=memory(12,'load',4,sizes['descsize']);state_reg=memory(24,'load',4,sizes['statesize'])
 require(desc_reg!=state_reg,'statesize load must preserve descsize for grouped copy')
 for pc,r in ((4,digest_reg),(16,desc_reg),(28,state_reg)):
  expect(pc,'sub',rd=31,rn=r,imm=bound,flags=True,width=32);require(0<bound<4096 and words[pc]==0x7100001f|(r<<5)|(bound<<10),'canonical immediate W comparison')
 branch(8,'cond',36,condition=8);branch(20,'cond',36,condition=8);branch(32,'cond',48,condition=9)
 temp=decode(words[36]).get('rd');require(temp==desc_reg,'shared error/result temporary aliases retained descsize register')
 expect(36,'movn',rd=temp,imm=21,shift=0,width=32);expect(40,'mov',rd=0,rn=temp,width=32);expect(44,'ret')
 flag_reg=memory(48,'load',4,flags);type_reg=pair(52,60,'crypto_shash_type',1);finup_reg=memory(56,'load',8,slots['finup'])
 require(len({temp,flag_reg,type_reg,finup_reg})==4,'live descsize,flags,type,finup values cannot alias')
 expect(64,'and',rd=flag_reg,rn=flag_reg,imm=(~mask)&0xffffffff,width=32);expect(68,'orr',rd=flag_reg,rn=flag_reg,imm=shash,width=32)
 memory(72,'store',8,type_slot,type_reg);memory(76,'store',4,flags,flag_reg)
 branch(80,'cb',96,rn=finup_reg,nonzero=True,width=64);finup_default=pair(84,88,'shash_finup_unaligned',2);require(finup_default!=temp,'finup address preserves descsize');memory(92,'store',8,slots['finup'],finup_default)
 digest=memory(96,'load',8,slots['digest']);require(digest!=temp,'digest load preserves descsize');branch(100,'cb',116,rn=digest,nonzero=True,width=64)
 digest_default=pair(104,108,'shash_digest_unaligned',2);require(digest_default!=temp,'digest address preserves descsize');memory(112,'store',8,slots['digest'],digest_default)
 export=memory(116,'load',8,slots['export']);require(export!=temp,'export guard preserves descsize');branch(120,'cb',148,rn=export,nonzero=True,width=64)
 export_default=pair(124,132,'shash_default_export',2);import_default=pair(128,136,'shash_default_import',2)
 require(len({temp,export_default,import_default})==3,'both pair-store values and descsize retain distinct provenance');memory(140,'store',4,sizes['statesize'],temp)
 d=decode(words[144]);expect(144,'pair-store',rd=export_default,rt2=import_default,rn=0);w=words[144];delta=signed((w>>15)&127,7)*8
 require(w&0xffc00000==0xa9000000 and (w>>23)&3==2 and delta==slots['export'] and slots['import']==delta+8,'GPR64 signed scaled offset STP, no writeback, exact adjacent ordered export/import slots')
 memory(148,'load',8,slots['setkey'],temp);branch(152,'cb',164,rn=temp,nonzero=False,width=64)
 expect(156,'mov',rd=temp,rn=31,width=32);branch(160,'b',40)
 setkey_default=pair(164,168,'shash_no_setkey',2);require(setkey_default!=temp,'null-setkey arm preserves CBZ-refined X/W zero');memory(172,'store',8,slots['setkey'],setkey_default);branch(176,'b',40)
 require(used==set(words) and consumed==set(byrel),'every owned instruction and relocation consumed once by exact roles')
 for pc in words:
  if pc==44:edges[pc]=[]
  elif pc not in edges:edges[pc]=[pc+4]
 require(all(t in words for targets in edges.values() for t in targets),'every CFG successor aligned and owned')
 # An independent finite edge walk proves complete ownership and absence of cycles.
 reached=set()
 def visit(pc,active):
  require(pc not in active,'acyclic preparation CFG')
  reached.add(pc)
  for nxt in edges[pc]:visit(nxt,active|{pc})
 visit(0,set());require(reached==set(words),'no disconnected instruction or unhandled predecessor')
 failures=[]
 for failing in range(3):
  path=[]
  for index in range(failing+1):path.extend((12*index,12*index+4,12*index+8))
  path.extend((36,40,44));require(all(b in edges[a] for a,b in zip(path,path[1:])),'connected per-size failure path')
  require(not any(decode(words[pc])['op'] in ('store','pair-store','bl','blr') for pc in path),'size failure has no side effect')
  result=(~21)&0xffffffff;require(result==0xffffffea,'failure MOVN W then exact W0 copy is EINVAL');failures.append({'field':('digestsize','descsize','statesize')[failing],'path':[start+p for p in path],'W0':result})
 # Paths stay separate. Import initially has an independent arbitrary value.
 success=[]
 for presence in itertools.product((False,True),repeat=4):
  present=dict(zip(('finup','digest','export','setkey'),presence));initial={name:('original_callback',name) if present.get(name,True) else 0 for name in slots};initial['import']=('independent_original_import',)
  memory_state=dict(initial,statesize=('original_statesize',));writes={'cra_type':'crypto_shash_type','cra_flags':('orr',('and',('original_flags',),(~mask)&0xffffffff,32),shash,32)}
  path=list(range(0,36,4))+list(range(48,84,4))
  for name,arm,join in (('finup',84,96),('digest',104,116)):
   if name=='digest':path.extend((96,100))
   if not present[name]:path.extend(range(arm,join,4));memory_state[name]='shash_'+name+'_unaligned';writes[name]=memory_state[name]
  path.extend((116,120))
  if not present['export']:
   path.extend(range(124,148,4));memory_state.update(export='shash_default_export',**{'import':'shash_default_import','statesize':('original_descsize',)});writes.update({n:memory_state[n] for n in ('export','import','statesize')})
  path.extend((148,152))
  if present['setkey']:path.extend((156,160));return_value=0;zero_origin='explicit Wtemporary=WZR'
  else:path.extend((164,168,172,176));memory_state['setkey']='shash_no_setkey';writes['setkey']='shash_no_setkey';return_value=0;zero_origin='Xtemporary loaded setkey; taken CBZ Xtemporary refines Xtemporary=0, hence Wtemporary=0'
  path.extend((40,44));require(all(b in edges[a] for a,b in zip(path,path[1:])) and return_value==0,'connected per-presence successful zero return')
  for name in ('finup','digest','setkey'):require((name in writes)==(not present[name]) and (not present[name] or memory_state[name]==initial[name]),'default iff original own callback absent; supplied callback retained')
  require(all((n in writes)==(not present['export']) for n in ('export','import','statesize')),'export guard alone owns grouped defaults and statesize')
  success.append({'presence':present,'initial_import':initial['import'],'path':[start+p for p in path],'writes':writes,'final_slots':memory_state,'W0':return_value,'zero_provenance':zero_origin})
 return {'variant':'finite-preparation-grouped-defaults-shared-return-v1','connected_finite_CFG_verified':True,'actual_function':fn,'object_sha256':obj['sha256'],'function_bytes_sha256':hashlib.sha256(sec['bytes']).hexdigest(),'all_word_offsets':[start+p for p in sorted(used)],'successors':{start+p:[start+t for t in v] for p,v in edges.items()},'bound_compiler_PAGE_SIZE_div8':bound,'size_failure_paths':failures,'success_paths':success,'original_fact_retained_in_enclosing_functions':True,'legacy_trace_used_for_variant_semantics':False,'runtime_admission_or_default_behavior_executed':False}
