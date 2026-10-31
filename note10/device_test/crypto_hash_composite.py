"""Bounded mapless relocatable-link origin, without instruction/type semantics."""
import hashlib,struct

OWNED=('crypto_register_shashes','crypto_register_shash','crypto_unregister_shash','shash_prepare_alg','crypto_shash_init_tfm','crypto_alloc_shash','crypto_shash_update','crypto_shash_final','crypto_shash_finup','crypto_shash_digest','crypto_shash_type')
RELOCATION_BYTES={257:8,275:4,277:4,282:4,283:4}


def require(ok,message):
 if not ok:raise ValueError(message)


def digest(raw):return hashlib.sha256(raw).hexdigest()


def parse_object(raw):
 require(type(raw) is bytes and 64<=len(raw)<=16*1024*1024,'bounded complete ELF object')
 require(raw[:16]==b'\x7fELF\x02\x01\x01'+bytes(9),'ELF64 little-endian current SYSV header')
 h=struct.unpack_from('<HHIQQQIHHHHHH',raw,16);kind,machine,version,entry,phoff,shoff,flags,ehsize,phentsize,phnum,shentsize,shnum,shstr=h
 require((kind,machine,version,entry,phoff,flags,ehsize,phentsize,phnum,shentsize)==(1,183,1,0,0,0,64,0,0,64) and 0<shnum<=4096 and 0<shstr<shnum,'finite AArch64 ET_REL, no extended indices/program headers')
 def span(offset,size):require(type(offset) is int and type(size) is int and offset>=0 and size>=0 and offset+size<=len(raw),'ELF file extent');return raw[offset:offset+size]
 span(shoff,shnum*64);sections=[];expanded=0
 for i in range(shnum):
  name,typ,sflags,address,offset,size,link,info,align,entsize=struct.unpack_from('<IIQQQQIIQQ',raw,shoff+i*64)
  require(address==0 and (align==0 or align&(align-1)==0) and align<=1<<20 and size<=16*1024*1024 and link<shnum,'finite section metadata')
  require(typ not in (9,17,18),'no REL/groups/extended symbol indices')
  expanded+=size;require(expanded<=16*1024*1024,'bounded aggregate section bytes including NOBITS');data=bytes(size) if typ==8 else span(offset,size)
  sections.append(dict(index=i,name_offset=name,type=typ,flags=sflags,offset=offset,size=size,link=link,info=info,alignment=align,entsize=entsize,bytes=data))
 ranges=sorted([(0,64),(shoff,shoff+shnum*64)]+[(s['offset'],s['offset']+s['size']) for s in sections if s['type']!=8 and s['size']]);require(all(a[1]<=b[0] for a,b in zip(ranges,ranges[1:])),'disjoint actual ELF file section/header ranges')
 require(all(v==0 for v in struct.unpack_from('<IIQQQQIIQQ',raw,shoff)),'canonical null section')
 def string(table,index):
  require(type(index) is int and 0<=index<len(table),'bounded string-table reference');end=table.find(b'\0',index);require(end>=index,'terminated ELF string');return table[index:end].decode('utf8')
 names=sections[shstr];require(names['type']==3 and names['bytes'][:1]==b'\0','actual section-name string table')
 for s in sections:s['name']=string(names['bytes'],s['name_offset'])
 tables=[s for s in sections if s['type']==2];require(len(tables)==1,'one actual symbol table');table=tables[0];require(table['entsize']==24 and table['size']%24==0 and 0<table['size']//24<=65536 and sections[table['link']]['type']==3,'bounded linked symbol/string tables')
 symbols=[];strings=sections[table['link']]['bytes'];require(strings[:1]==b'\0','symbol string table starts empty')
 for i in range(table['size']//24):
  off,info,other,section,value,size=struct.unpack_from('<IBBHQQ',table['bytes'],i*24)
  require(section<shnum or section in (0xfff1,0xfff2),'no reserved/extended section index')
  require(other<=3 and info>>4<=2 and info&15 in (0,1,2,3,4),'supported ELF symbol metadata')
  if 0<section<shnum:require(value+size<=sections[section]['size'],'defined symbol bounded by complete section')
  symbols.append(dict(index=i,name=string(strings,off),info=info,other=other,section=section,value=value,size=size))
 require(symbols[0]==dict(index=0,name='',info=0,other=0,section=0,value=0,size=0),'canonical null symbol');require(table['info']<=len(symbols) and all((s['info']>>4==0)==(s['index']<table['info']) for s in symbols),'symbol local/global partition')
 relocations=[]
 for s in sections:
  if s['type']!=4:continue
  require(s['link']==table['index'] and 0<s['info']<shnum and s['entsize']==24 and s['size']%24==0,'exact RELA section target/table binding')
  for i in range(s['size']//24):
   place,info,addend=struct.unpack_from('<QQq',s['bytes'],i*24);symbol=info>>32;typ=info&0xffffffff;require(symbol<len(symbols) and place<sections[s['info']]['size'],'bounded RELA place/symbol')
   relocations.append(dict(section=s['info'],offset=place,type=typ,addend=addend,symbol=symbol,relocation_section=s['index'],entry=i));require(len(relocations)<=131072,'bounded complete relocation inventory')
 return {'sha256':digest(raw),'bytes':len(raw),'sections':sections,'symbols':symbols,'relocations':relocations}


def symbol_attributes(s):return {k:s[k] for k in ('name','info','other','value','size')}


def section_identity(obj,index,active=None):
 require(0<index<len(obj['sections']),'defined section identity');active=set() if active is None else active;require(index not in active,'acyclic section-header references');cache=obj.setdefault('_section_identity_cache',{})
 if index in cache:return cache[index]
 s=obj['sections'][index]
 def reference(i):return None if i==0 else section_identity(obj,i,active|{index})
 # sh_info is an index only for relocation/SHF_INFO_LINK sections.
 info=reference(s['info']) if s['type'] in (4,9) or s['flags']&64 else s['info']
 result=(s['name'],s['type'],s['flags'],s['size'],s['alignment'],s['entsize'],digest(s['bytes']),reference(s['link']),info);cache[index]=result;return result


def unique_section(obj,index):
 identity=section_identity(obj,index);checked=obj.setdefault('_unique_section_cache',set())
 if index not in checked:
  counts=obj.setdefault('_section_identity_counts',{})
  if not counts:
   for s in obj['sections'][1:]:key=section_identity(obj,s['index']);counts[key]=counts.get(key,0)+1
  require(counts[identity]==1,'unique same-object complete section identity');todo=[index];visited=set()
  while todo:
   current=todo.pop()
   if current in visited:continue
   visited.add(current);s=obj['sections'][current];references=([s['link']] if s['link'] else [])+([s['info']] if (s['type'] in (4,9) or s['flags']&64) and s['info'] else [])
   for target in references:require(counts[section_identity(obj,target)]==1,'unique validated section/table identity for every sh_link/sh_info reference');todo.append(target)
  checked.add(index)
 return identity


def owned(obj,name):
 matches=[s for s in obj['symbols'] if s['name']==name and s['section']!=0];require(len(matches)==1,'one typed selected definition '+name);symbol=matches[0];kind=1 if name=='crypto_shash_type' else 2
 require(symbol['info']&15==kind and symbol['info']>>4 in (0,1) and 0<symbol['section']<len(obj['sections']) and symbol['value']==0 and symbol['size']>0,'typed full selected symbol extent')
 sec=obj['sections'][symbol['section']];expected='.rodata.'+name if kind==1 else '.text.'+name
 require(sec['name']==expected and sec['type']==1 and sec['size']==symbol['size'] and sec['alignment']>0 and not sec['flags']&(1|16|32|512) and sec['flags']&2 and bool(sec['flags']&4)==(kind==2),'whole passive table or executable function section, no merge/group/write')
 unique_section(obj,symbol['section']);return symbol


def selected_relocations(obj,section):
 rows=[r for r in obj['relocations'] if r['section']==section];used=set();spans=[]
 for r in rows:
  require(r['type'] in RELOCATION_BYTES and r['offset'] not in used,'one supported relocation per selected place');used.add(r['offset']);width=RELOCATION_BYTES[r['type']];require(r['offset']%width==0 and r['offset']+width<=obj['sections'][section]['size'],'whole aligned selected relocation field');spans.append((r['offset'],r['offset']+width))
 require(all(a[1]<=b[0] for a,b in zip(sorted(spans),sorted(spans)[1:])),'disjoint selected relocation fields');return {r['offset']:r for r in rows}


def reference_identity(obj,r):
 s=obj['symbols'][r['symbol']];require(s['section'] not in (0xfff1,0xfff2) and s['info']>>4!=2,'no weak/common/absolute selected targets')
 if s['section']==0:
  require(s['name'] and s['info']>>4==1 and s['value']==s['size']==0,'named strong undefined target');return ('undefined',s['name'],s['info'],s['other'],r['addend'])
 section=unique_section(obj,s['section']);coordinate=s['value']+r['addend'];require(0<=coordinate<obj['sections'][s['section']]['size'],'signed addend targets exact bounded input span')
 if s['info']&15==3:require(s['name']=='' and s['value']==s['size']==0 and s['info']>>4==0 and s['other']==0,'canonical anonymous local section target')
 else:require(s['name'] and s['info']&15 in (0,1,2),'named supported defined target')
 return ('defined',section,coordinate,symbol_attributes(s))


def baseline_identity(baseline,leaf):
 rows=[]
 for name in OWNED:
  old=owned(baseline,name);new=owned(leaf,name);require(symbol_attributes(old)==symbol_attributes(new) and unique_section(baseline,old['section'])==unique_section(leaf,new['section']),'selected baseline/new-leaf complete symbol/section bytes identity')
  a=selected_relocations(baseline,old['section']);b=selected_relocations(leaf,new['section']);require(set(a)==set(b),'complete baseline/new-leaf relocation places')
  for place,r in a.items():require(r['type']==b[place]['type'] and reference_identity(baseline,r)==reference_identity(leaf,b[place]),'exact baseline/new-leaf raw target/addend identity')
  rows.append({'name':name,'baseline_symbol':old,'new_leaf_symbol':new,'section_sha256':digest(leaf['sections'][new['section']]['bytes']),'relocations':[{'baseline':a[p],'leaf':b[p]} for p in sorted(a)]})
 return rows


def link_origin(baseline,shash,ahash,composite):
 baseline_rows=baseline_identity(baseline,shash);inputs={'shash':shash,'ahash':ahash};mapping={};mapped_symbols=[]
 def map_section(origin,index):
  key=(origin,index)
  if key in mapping:return mapping[key]
  obj=inputs[origin];s=obj['sections'][index];identity=unique_section(obj,index)
  require(s['type'] in (1,8) and s['size']>0 and not s['flags']&(16|32|512),'whole unmerged referenced input section')
  candidates=[(o,x['index']) for o,v in inputs.items() for x in v['sections'][1:] if x['name']==s['name']];require(candidates==[key],'sole same-name input contribution across both leafs')
  outputs=[x for x in composite['sections'][1:] if x['name']==s['name']];require(len(outputs)==1 and unique_section(composite,outputs[0]['index'])==identity,'sole exact full output span, no concatenation/rewriting')
  mapping[key]=outputs[0]['index'];return mapping[key]
 def map_symbol(origin,s):
  index=map_section(origin,s['section']);matches=[t for t in composite['symbols'] if t['section']==index and symbol_attributes(t)==symbol_attributes(s)];require(len(matches)==1,'one section/coordinate-qualified output definition retaining original symbol');mapped_symbols.append({'origin':origin,'input_symbol':s,'output_symbol':matches[0]});return matches[0]
 def check_defined(origin,s,addend,out_symbol,out_addend):
  obj=inputs[origin];reference_identity(obj,{'symbol':s['index'],'addend':addend});out_section=map_section(origin,s['section']);coordinate=s['value']+addend
  if s['info']&15!=3:map_symbol(origin,s)
  require(out_symbol['section']==out_section and out_symbol['value']+out_addend==coordinate and 0<=coordinate<composite['sections'][out_section]['size'],'exact origin-aware output target coordinate')
  if out_symbol['info']&15==3:require(out_symbol['name']=='' and out_symbol['info']==3 and out_symbol['other']==0 and out_symbol['value']==out_symbol['size']==0,'only canonical section-symbol rebasing')
  else:require(symbol_attributes(out_symbol)==symbol_attributes(s) and out_addend==addend,'only unchanged named target or exact section-symbol rebase')
 def relocation(origin,r,out):
  obj=inputs[origin];s=obj['symbols'][r['symbol']];t=composite['symbols'][out['symbol']];require(r['type']==out['type'] and r['offset']==out['offset'],'one-to-one relocation field/type/place');reference_identity(obj,r)
  if s['section']!=0:check_defined(origin,s,r['addend'],t,out['addend']);return
  definitions=[(o,u) for o,v in inputs.items() for u in v['symbols'] if u['name']==s['name'] and u['section']!=0]
  require(all(u['section']<len(inputs[o]['sections']) and u['info']>>4==1 for o,u in definitions),'no weak/common/absolute resolution precedence')
  if not definitions:require(t['section']==0 and symbol_attributes(t)==symbol_attributes(s) and out['addend']==r['addend'],'strong undefined identity remains exactly unresolved');return
  require(len(definitions)==1,'unique eligible strong input definition');o,u=definitions[0];require(u['info']==s['info'] and u['other']==s['other'],'no symbol type/binding/visibility resolution drift');map_symbol(o,u);check_defined(o,u,r['addend'],t,out['addend'])
 projected=[]
 for name in OWNED:
  s=owned(shash,name);t=owned(composite,name);require(map_symbol('shash',s)==t,'selected symbol maps to sole owned output definition');out_section=map_section('shash',s['section']);a=selected_relocations(shash,s['section']);b=selected_relocations(composite,out_section);require(set(a)==set(b),'no extra/missing output selected relocations')
  for place in sorted(a):relocation('shash',a[place],b[place])
  projected.append({'name':name,'input_symbol':s,'output_symbol':t,'relocations':[{'input':a[p],'output':b[p]} for p in sorted(a)]})
 return {'schema':1,'object_sha256':{'baseline_shash':baseline['sha256'],'shash':shash['sha256'],'ahash':ahash['sha256'],'composite':composite['sha256']},'baseline_selected_byte_relocation_identity':baseline_rows,'selected_link_origin':projected,'section_ownership':[{'origin':o,'input_section':i,'output_section':v} for (o,i),v in sorted(mapping.items())],'required_target_definitions':mapped_symbols,'all_composite_defined_symbols':[s for s in composite['symbols'] if s['section']!=0],'all_composite_unresolved_symbols':[s for s in composite['symbols'] if s['section']==0 and s['name']],'old_semantic_proofs_replayed':False,'ahash_semantics_runtime_provider_stack_Image_BOOT_XNU_iOS_proven':False}
