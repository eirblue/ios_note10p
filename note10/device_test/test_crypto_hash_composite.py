"""Only new synthetic ELF/origin/input cases; no old fixtures or target code."""
import argparse,copy,json,struct,tempfile,zipfile
from pathlib import Path
from crypto_hash_composite import OWNED,parse_object,link_origin,require,digest
from crypto_hash_input_contract import composite_command,command_line,normalized,protected,stable,separate,disk_budget,extract_zip,verify_extraction,tree_inventory,api_validate,write,leaf_equality,config_contract
from build_crypto_hash_composite import postprocess_commands,make_command

ORIGIN_NEGATIVES=('missing-selected','wrong-selected-kind','wrong-selected-binding','wrong-selected-visibility','selected-nonzero-start','selected-short-extent','changed-selected-bytes','changed-section-alignment','changed-section-flags','merge-section','group-section','input-same-name-collision','output-same-name-collision','output-section-concatenated','missing-output-definition','ambiguous-output-local-definition','wrong-output-symbol-size','missing-output-relocation','extra-output-relocation','duplicate-output-place','unsupported-relocation','wrong-relocation-type','relocation-field-overrun','relocation-field-overlap','negative-target-outside','target-past-end','wrong-output-target-coordinate','wrong-output-named-target','missing-named-target-definition','wrong-section-symbol-rebase','undefined-weak','undefined-absolute','undefined-common','undefined-resolution-ambiguous','undefined-resolution-type-drift','undefined-resolution-visibility-drift','undefined-output-name-drift','undefined-output-addend-drift','referenced-origin-collision')
PARSER_NEGATIVES=('short-ELF','archive-not-ELF','big-endian','ELF32','wrong-machine','ET_DYN','extended-section-count','extended-shstr','bad-section-table-offset','wrong-section-entry-size','bad-symbol-table-size','duplicate-symtab','bad-symbol-reference','bad-relocation-table-link','bad-relocation-target-section')
INPUT_NEGATIVES=('composite-input-order','composite-extra-input','composite-missing-no-relax','composite-wrong-linker','composite-LLD-profile','composite-version-drift','cmd-postfix','cmd-duplicate-assignment','root-map-ambiguous','protected-size','protected-digest','protected-after-mutation','protected-alias','overlapping-roots','insufficient-disk','ZIP-wrong-root','ZIP-duplicate','ZIP-traversal','ZIP-symlink','ZIP-member-count','ZIP-expanded-bytes','ZIP-extra-extracted-file','API-wrong-run','API-failed-job','API-failed-step','API-metadata-disagreement','API-expired','API-digest','API-head','API-incomplete-jobs')
PROVENANCE_CASES=('authenticated-baseline-positive','exact-GNU-composite-command-positive','mapped-leaf-prerequisites-positive','source-thin-y-effective-empty-positive','CC-option-order','CC-unknown-option','CC-root-boundary','prerequisite-extra','prerequisite-missing','prerequisite-byte-drift','source-thin-off','source-LTO-on','source-modversions-off')
POSTPROCESS_CASES=('exact-expanded-GNU-leaf-and-composite-recipes','leaf-wrong-GNU-flags','leaf-wrong-temp-object','leaf-wrong-version-script','leaf-extra-postprocess-option','missing-leaf-postprocess','duplicate-selected-postprocess','composite-expanded-input-order','anonymous-section-target-origin','output-function-bytes-rewritten','output-table-bytes-rewritten','output-table-relocation-missing','weak-definition-resolution-reject','absolute-definition-resolution-reject')
CASES=('synthetic-parser-and-mapless-origin','output-section-index-reordering','coordinate-qualified-local-duplicates','named-to-section-symbol-rebase','signed-addend-translation','undefined-strong-resolution','undefined-strong-preserved','full-table-byte-and-relocation-origin','complete-ZIP-and-protected-input')+ORIGIN_NEGATIVES+PARSER_NEGATIVES+INPUT_NEGATIVES+PROVENANCE_CASES+POSTPROCESS_CASES


def elf_bytes(sections,symbols,relocations):
 """Construct ELF64 records, never captured instructions or an executable."""
 sections=copy.deepcopy(sections);symbols=copy.deepcopy(symbols);index={s['key']:i+1 for i,s in enumerate(sections)};ordered=sorted(symbols,key=lambda s:s['info']>>4);symindex={s['key']:i+1 for i,s in enumerate(ordered)};strings=bytearray(b'\0');symraw=bytearray(24)
 for s in ordered:
  name=len(strings);strings.extend(s['name'].encode()+b'\0');symraw.extend(struct.pack('<IBBHQQ',name,s['info'],s.get('other',0),index[s['section']] if s['section'] else 0,s.get('value',0),s.get('size',0)))
 symtab_index=len(sections)+1;strtab_index=symtab_index+1
 entries=[dict(name=s['name'],type=1,flags=s['flags'],alignment=s.get('alignment',4),entsize=0,link=0,info=0,bytes=s['bytes']) for s in sections]
 entries.extend((dict(name='.symtab',type=2,flags=0,alignment=8,entsize=24,link=strtab_index,info=1+sum(s['info']>>4==0 for s in ordered),bytes=bytes(symraw)),dict(name='.strtab',type=3,flags=0,alignment=1,entsize=0,link=0,info=0,bytes=bytes(strings))))
 for key in dict.fromkeys(r['section'] for r in relocations):
  raw=b''.join(struct.pack('<QQq',r['offset'],(symindex[r['symbol']]<<32)|r['type'],r.get('addend',0)) for r in relocations if r['section']==key);entries.append(dict(name='.rela'+sections[index[key]-1]['name'],type=4,flags=64,alignment=8,entsize=24,link=symtab_index,info=index[key],bytes=raw))
 names=bytearray(b'\0')
 for s in entries:s['name_offset']=len(names);names.extend(s['name'].encode()+b'\0')
 name_offset=len(names);names.extend(b'.shstrtab\0');entries.append(dict(name='.shstrtab',name_offset=name_offset,type=3,flags=0,alignment=1,entsize=0,link=0,info=0,bytes=bytes(names)))
 raw=bytearray(64);headers=[bytes(64)]
 for s in entries:
  while len(raw)%max(s['alignment'],1):raw.append(0)
  offset=len(raw);raw.extend(s['bytes']);headers.append(struct.pack('<IIQQQQIIQQ',s['name_offset'],s['type'],s['flags'],0,offset,len(s['bytes']),s['link'],s['info'],s['alignment'],s['entsize']))
 while len(raw)%8:raw.append(0)
 shoff=len(raw);raw.extend(b''.join(headers));raw[:16]=b'\x7fELF\x02\x01\x01'+bytes(9);struct.pack_into('<HHIQQQIHHHHHH',raw,16,1,183,1,0,0,shoff,0,64,0,0,64,len(headers),len(headers)-1);return bytes(raw)


def fixture():
 sections=[];symbols=[];relocations=[]
 for i,name in enumerate(OWNED):
  table=name=='crypto_shash_type';key='s'+str(i);sections.append({'key':key,'name':('.rodata.' if table else '.text.')+name,'flags':2 if table else 6,'alignment':8 if table else 4,'bytes':bytes(8) if table else struct.pack('<I',i+1)});symbols.append({'key':name,'name':name,'info':1 if table else 18,'section':key,'size':8 if table else 4})
 sections.append({'key':'helper','name':'.text.synthetic_shash_helper','flags':6,'alignment':4,'bytes':bytes(8)});symbols.extend(({'key':'helper','name':'duplicate_local','info':2,'section':'helper','size':8},{'key':'resolved','name':'synthetic_shared','info':16,'section':None},{'key':'unresolved','name':'synthetic_external','info':16,'section':None}))
 relocations=[{'section':'s0','offset':0,'type':283,'symbol':'helper'},{'section':'s1','offset':0,'type':283,'symbol':'resolved'},{'section':'s10','offset':0,'type':257,'symbol':'unresolved'}]
 ahash_sections=[{'key':'ahelper','name':'.text.synthetic_ahash_helper','flags':6,'alignment':4,'bytes':b'abcde123'}];ahash_symbols=[{'key':'adef','name':'synthetic_shared','info':16,'section':'ahelper','size':8},{'key':'alocal','name':'duplicate_local','info':2,'section':'ahelper','size':8}]
 output_sections=ahash_sections+sections;output_symbols=copy.deepcopy(symbols)
 output_symbols=[s for s in output_symbols if s['key']!='resolved']+ahash_symbols
 out_reloc=copy.deepcopy(relocations)
 for r in out_reloc:
  if r['symbol']=='resolved':r['symbol']='adef'
 raw=elf_bytes(sections,symbols,relocations);return [parse_object(raw),parse_object(raw),parse_object(elf_bytes(ahash_sections,ahash_symbols,[])),parse_object(elf_bytes(output_sections,output_symbols,out_reloc))],raw


def api_fixture():
 pins={'repository':'synthetic/project','run_id':1,'run_attempt':1,'workflow_id':2,'job_id':3,'artifact_id':4,'zip_bytes':8,'ordinary_members':1,'expanded_bytes':1,'source_commit':'a'*40,'zip_sha256':'b'*64,'object_sha256':'c'*64,'artifact_name':'note10-shash-core-pc-only','required_steps':['synthetic-required']};run={'id':1,'run_attempt':1,'workflow_id':2,'head_sha':'a'*40,'status':'completed','conclusion':'success','repository':{'full_name':'synthetic/project'}};job={'id':3,'run_id':1,'run_attempt':1,'head_sha':'a'*40,'name':'shash-core','status':'completed','conclusion':'success','steps':[{'name':'synthetic-required','status':'completed','conclusion':'success'}]};artifact={'id':4,'name':pins['artifact_name'],'expired':False,'size_in_bytes':8,'digest':'sha256:'+'b'*64,'workflow_run':{'id':1,'head_sha':'a'*40}};return pins,run,{'total_count':1,'jobs':[job]},{'total_count':1,'artifacts':[copy.deepcopy(artifact)]},artifact


def run_cases(completed=None):
 if completed is None:completed=[]
 def check(name,fn,reject=False):
  require(name==CASES[len(completed)],'exact frozen new case order')
  try:fn()
  except (ValueError,KeyError,IndexError,struct.error,FileExistsError):
   if not reject:raise
  else:require(not reject,'invalid synthetic origin/input accepted: '+name)
  completed.append(name)
 for name in CASES[:9]:
  objects,raw=fixture();b,s,a,o=objects
  if name=='named-to-section-symbol-rebase':
   rel=o['relocations'][0];original=o['symbols'][rel['symbol']];o['symbols'].append(dict(index=len(o['symbols']),name='',info=3,other=0,section=original['section'],value=0,size=0));rel['symbol']=len(o['symbols'])-1
  if name=='signed-addend-translation':
   for obj in (b,s,o):obj['relocations'][0]['addend']=4
  if name=='complete-ZIP-and-protected-input':
   def complete():
    with tempfile.TemporaryDirectory() as tmp:
     root=Path(tmp);z=root/'source.zip'
     with zipfile.ZipFile(z,'w') as f:f.writestr('synthetic-root/a',b'x')
     record=protected(z,'synthetic',z.stat().st_size,digest(z.read_bytes()));extract_zip(z,root/'expanded','synthetic-root',1,1);verify_extraction(z,root/'expanded','synthetic-root',1,1);require(stable(record)==record,'stable synthetic input')
   check(name,complete)
  else:check(name,lambda x=objects:link_origin(*x))
 for name in ORIGIN_NEGATIVES:
  objects,_=fixture();b,s,a,o=objects;first=s['symbols'][next(i for i,t in enumerate(s['symbols']) if t['name']==OWNED[0])];section=s['sections'][first['section']];r=o['relocations'][0];target=o['symbols'][r['symbol']]
  if name=='missing-selected':s['symbols'].remove(first)
  elif name=='wrong-selected-kind':first['info']=17
  elif name=='wrong-selected-binding':first['info']=34
  elif name=='wrong-selected-visibility':first['other']=2
  elif name=='selected-nonzero-start':first['value']=1
  elif name=='selected-short-extent':first['size']=3
  elif name=='changed-selected-bytes':section['bytes']=b'abcd'
  elif name=='changed-section-alignment':section['alignment']=8
  elif name=='changed-section-flags':section['flags']=2
  elif name=='merge-section':section['flags']|=16
  elif name=='group-section':section['flags']|=512
  elif name=='input-same-name-collision':a['sections'].append(copy.deepcopy(section))
  elif name=='output-same-name-collision':o['sections'].append(copy.deepcopy(o['sections'][r['section']]))
  elif name=='output-section-concatenated':o['sections'][r['section']]['size']+=4
  elif name=='missing-output-definition':o['symbols']=[t for t in o['symbols'] if t['name']!=OWNED[0]]
  elif name=='ambiguous-output-local-definition':o['symbols'].append(copy.deepcopy(target))
  elif name=='wrong-output-symbol-size':next(t for t in o['symbols'] if t['name']==OWNED[0])['size']=3
  elif name=='missing-output-relocation':o['relocations'].pop(0)
  elif name=='extra-output-relocation':o['relocations'].append(dict(r,offset=1))
  elif name=='duplicate-output-place':o['relocations'].append(copy.deepcopy(r))
  elif name=='unsupported-relocation':r['type']=999
  elif name=='wrong-relocation-type':r['type']=282
  elif name=='relocation-field-overrun':r['offset']=4
  elif name=='relocation-field-overlap':
   for obj in (b,s,o):
    symbol=next(t for t in obj['symbols'] if t['name']==OWNED[0]);sec=obj['sections'][symbol['section']];sec['size']=symbol['size']=12;sec['bytes']=bytes(12);rel=next(t for t in obj['relocations'] if t['section']==symbol['section']);rel['type']=257;obj['relocations'].append(dict(rel,type=283,offset=4))
  elif name=='negative-target-outside':s['relocations'][0]['addend']=b['relocations'][0]['addend']=-1
  elif name=='target-past-end':s['relocations'][0]['addend']=b['relocations'][0]['addend']=8
  elif name=='wrong-output-target-coordinate':r['addend']=4
  elif name=='wrong-output-named-target':target['name']='wrong'
  elif name=='missing-named-target-definition':o['symbols'].remove(target)
  elif name=='wrong-section-symbol-rebase':target['info']=3;target['name']='';target['size']=0;target['value']=1
  elif name in ('undefined-weak','undefined-absolute','undefined-common'):
   for obj in (b,s):
    u=next(t for t in obj['symbols'] if t['name']=='synthetic_external')
    if name=='undefined-weak':u['info']=32
    else:u['section']=0xfff1 if name=='undefined-absolute' else 0xfff2
  elif name=='undefined-resolution-ambiguous':a['symbols'].append(copy.deepcopy(next(t for t in a['symbols'] if t['name']=='synthetic_shared')))
  elif name=='undefined-resolution-type-drift':next(t for t in a['symbols'] if t['name']=='synthetic_shared')['info']=18
  elif name=='undefined-resolution-visibility-drift':next(t for t in a['symbols'] if t['name']=='synthetic_shared')['other']=2
  elif name=='undefined-output-name-drift':next(t for t in o['symbols'] if t['name']=='synthetic_external')['name']='wrong'
  elif name=='undefined-output-addend-drift':o['relocations'][-1]['addend']=1
  elif name=='referenced-origin-collision':a['sections'].append(copy.deepcopy(s['sections'][target['section']-1] if target['section']>1 else s['sections'][1]));a['sections'][-1]['name']='.text.synthetic_shash_helper'
  check(name,lambda x=objects:link_origin(*x),True)
 for name in PARSER_NEGATIVES:
  _,raw=fixture();raw=bytearray(raw);shoff=struct.unpack_from('<Q',raw,40)[0];count=struct.unpack_from('<H',raw,60)[0]
  if name=='short-ELF':raw=raw[:10]
  elif name=='archive-not-ELF':raw[:8]=b'!<arch>\n'
  elif name=='big-endian':raw[5]=2
  elif name=='ELF32':raw[4]=1
  elif name=='wrong-machine':struct.pack_into('<H',raw,18,62)
  elif name=='ET_DYN':struct.pack_into('<H',raw,16,3)
  elif name=='extended-section-count':struct.pack_into('<H',raw,60,0)
  elif name=='extended-shstr':struct.pack_into('<H',raw,62,0xffff)
  elif name=='bad-section-table-offset':struct.pack_into('<Q',raw,40,len(raw)+1)
  elif name=='wrong-section-entry-size':struct.pack_into('<H',raw,58,32)
  else:
   table=next(i for i in range(count) if struct.unpack_from('<I',raw,shoff+i*64+4)[0]==2);rela=next(i for i in range(count) if struct.unpack_from('<I',raw,shoff+i*64+4)[0]==4)
   if name=='bad-symbol-table-size':struct.pack_into('<Q',raw,shoff+table*64+32,25)
   elif name=='duplicate-symtab':struct.pack_into('<I',raw,shoff+(table+1)*64+4,2)
   elif name=='bad-symbol-reference':offset=struct.unpack_from('<Q',raw,shoff+rela*64+24)[0];struct.pack_into('<Q',raw,offset+8,0xffffffff0000011b)
   elif name=='bad-relocation-table-link':struct.pack_into('<I',raw,shoff+rela*64+40,0)
   elif name=='bad-relocation-target-section':struct.pack_into('<I',raw,shoff+rela*64+44,0)
  check(name,lambda data=bytes(raw):parse_object(data),True)
 for name in INPUT_NEGATIVES:
  linker={'role':'aarch64-linux-gnu-ld','path':'/synthetic/bin/aarch64-linux-gnu-ld','sha256':'a'*64,'version':'GNU ld synthetic 2.38'};args=['aarch64-linux-gnu-ld','-m','aarch64linux','--no-relax','-r','-o','crypto/crypto_hash.o','crypto/ahash.o','crypto/shash.o']
  if name.startswith('composite-'):
   if name=='composite-input-order':args[-2:]=reversed(args[-2:])
   elif name=='composite-extra-input':args.append('other.o')
   elif name=='composite-missing-no-relax':args.remove('--no-relax')
   elif name=='composite-wrong-linker':args[0]='ld.lld-14'
   elif name=='composite-LLD-profile':linker['version']='LLD 14'
   elif name=='composite-version-drift':linker['version']='GNU ld synthetic 2.40'
   check(name,lambda x=args,l=linker:composite_command(x,l),True);continue
  if name.startswith('cmd-'):
   text='cmd_crypto/crypto_hash.o := '+' '.join(args)
   text+='; echo unsupported' if name=='cmd-postfix' else '\n'+text
   check(name,lambda t=text:command_line(t,'crypto/crypto_hash.o'),True);continue
  if name=='root-map-ambiguous':check(name,lambda:normalized(['/root/a'],{'source':'/root','objects':'/root','compiler-include':'/other'}),True);continue
  if name.startswith('API-'):
   values=list(api_fixture());pins,run,jobs,listing,artifact=values
   if name=='API-wrong-run':run['id']=9
   elif name=='API-failed-job':jobs['jobs'][0]['conclusion']='failure'
   elif name=='API-failed-step':jobs['jobs'][0]['steps'][0]['conclusion']='failure'
   elif name=='API-metadata-disagreement':artifact['name']='different'
   elif name=='API-expired':artifact['expired']=True;listing['artifacts'][0]['expired']=True
   elif name=='API-digest':artifact['digest']='sha256:'+'0'*64;listing['artifacts'][0]['digest']=artifact['digest']
   elif name=='API-head':artifact['workflow_run']['head_sha']='d'*40;listing['artifacts'][0]['workflow_run']['head_sha']='d'*40
   elif name=='API-incomplete-jobs':jobs['total_count']=2
   check(name,lambda v=values:api_validate(*v),True);continue
  def filesystem_case(case=name):
   with tempfile.TemporaryDirectory() as tmp:
    root=Path(tmp);file=root/'input';file.write_bytes(b'x');record=protected(file,'synthetic',1,digest(b'x'))
    if case=='protected-size':return protected(file,'synthetic',2,digest(b'x'))
    if case=='protected-digest':return protected(file,'synthetic',1,'0'*64)
    if case=='protected-after-mutation':file.write_bytes(b'y');return stable(record)
    if case=='protected-alias':return separate([file,root/'other'],[record['file_identity'],record['file_identity']])
    if case=='overlapping-roots':return separate([root,root/'child'])
    if case=='insufficient-disk':return disk_budget(root,1<<100)
    z=root/'input.zip';entry='root/a'
    with zipfile.ZipFile(z,'w') as bundle:
     if case=='ZIP-wrong-root':entry='other/a'
     if case=='ZIP-traversal':entry='root/../outside'
     if case=='ZIP-symlink':
      info=zipfile.ZipInfo(entry);info.external_attr=0o120777<<16;bundle.writestr(info,b'target')
     else:bundle.writestr(entry,b'x')
     if case=='ZIP-duplicate':bundle.writestr(entry,b'x')
    count=2 if case=='ZIP-member-count' else 1;size=2 if case=='ZIP-expanded-bytes' else 1;extract_zip(z,root/'expanded','root',count,size)
    if case=='ZIP-extra-extracted-file':(root/'expanded/extra').write_bytes(b'x');verify_extraction(z,root/'expanded','root',1,1)
  check(name,filesystem_case,True)
 for name in PROVENANCE_CASES:
  if name=='authenticated-baseline-positive':check(name,lambda:api_validate(*api_fixture()));continue
  if name=='exact-GNU-composite-command-positive':
   check(name,lambda:composite_command(['aarch64-linux-gnu-ld','-m','aarch64linux','--no-relax','-r','-o','crypto/crypto_hash.o','crypto/ahash.o','crypto/shash.o'],{'role':'aarch64-linux-gnu-ld','path':'/synthetic/bin/aarch64-linux-gnu-ld','sha256':'a'*64,'version':'GNU ld synthetic 2.38'}));continue
  if name=='source-thin-y-effective-empty-positive' or name.startswith('source-'):
   config='\n'.join(('CONFIG_CRYPTO_HASH2=y','CONFIG_LTO_NONE=y','CONFIG_THIN_ARCHIVES=y','CONFIG_MODVERSIONS=y','# CONFIG_LTO is not set','# CONFIG_LTO_CLANG is not set','# CONFIG_DEBUG_SECTION_MISMATCH is not set'))+'\n'
   if name=='source-thin-off':config=config.replace('CONFIG_THIN_ARCHIVES=y','CONFIG_THIN_ARCHIVES=n')
   elif name=='source-LTO-on':config=config.replace('# CONFIG_LTO is not set','CONFIG_LTO=y')
   elif name=='source-modversions-off':config=config.replace('CONFIG_MODVERSIONS=y','CONFIG_MODVERSIONS=n')
   check(name,lambda raw=config.encode():config_contract(raw),name!='source-thin-y-effective-empty-positive');continue
  oldroots={'source':'/synthetic/old/source','objects':'/synthetic/old/objects','compiler-include':'/synthetic/old/compiler'};newroots={k:v.replace('/old/','/new/') for k,v in oldroots.items()};args=['clang-14','-I'+oldroots['source']+'/include','-c',oldroots['source']+'/crypto/shash.c'];old={'command_origin':{'args':args}};deps={'roots':oldroots,'files_sha256':{'source/crypto/shash.c':'a'*64}};new={'roots':newroots,'files_sha256':dict(deps['files_sha256']),'actual_CC_argv':[v.replace('/old/','/new/') for v in args]}
  if name=='CC-option-order':new['actual_CC_argv'][1:3]=reversed(new['actual_CC_argv'][1:3])
  elif name=='CC-unknown-option':new['actual_CC_argv'].insert(1,'-unsupported')
  elif name=='CC-root-boundary':new['actual_CC_argv'][-1]=newroots['source']+'-unmapped/crypto/shash.c'
  elif name=='prerequisite-extra':new['files_sha256']['source/extra']='b'*64
  elif name=='prerequisite-missing':new['files_sha256'].clear()
  elif name=='prerequisite-byte-drift':new['files_sha256']['source/crypto/shash.c']='b'*64
  check(name,lambda o=old,d=deps,n=new:leaf_equality(o,d,n),name!='mapped-leaf-prerequisites-positive')
 for name in POSTPROCESS_CASES:
  if name in POSTPROCESS_CASES[:8]:
   linker={'role':'aarch64-linux-gnu-ld','path':'/synthetic/bin/aarch64-linux-gnu-ld','sha256':'a'*64,'version':'GNU ld synthetic 2.38'};lines=['if synthetic; then aarch64-linux-gnu-ld -m aarch64linux --no-relax -r -o crypto/'+leaf+'.o crypto/.tmp_'+leaf+'.o -T crypto/.tmp_'+leaf+'.ver; fi;' for leaf in ('shash','ahash')];lines.append('aarch64-linux-gnu-ld -m aarch64linux --no-relax -r -o crypto/crypto_hash.o crypto/ahash.o crypto/shash.o')
   if name=='leaf-wrong-GNU-flags':lines[0]=lines[0].replace('--no-relax','--relax')
   elif name=='leaf-wrong-temp-object':lines[0]=lines[0].replace('crypto/.tmp_shash.o','crypto/other.o')
   elif name=='leaf-wrong-version-script':lines[0]=lines[0].replace('crypto/.tmp_shash.ver','crypto/other.ver')
   elif name=='leaf-extra-postprocess-option':lines[0]=lines[0].replace('-r -o','-unexpected -r -o')
   elif name=='missing-leaf-postprocess':lines.pop(0)
   elif name=='duplicate-selected-postprocess':lines.append(lines[0])
   elif name=='composite-expanded-input-order':lines[-1]=lines[-1].replace('crypto/ahash.o crypto/shash.o','crypto/shash.o crypto/ahash.o')
   check(name,lambda text='\n'.join(lines),l=linker:postprocess_commands(text,l),name!='exact-expanded-GNU-leaf-and-composite-recipes');continue
  objects,_=fixture();b,s,a,o=objects
  if name=='anonymous-section-target-origin':
   for obj in (b,s,o):
    rel=obj['relocations'][0];symbol=obj['symbols'][rel['symbol']];obj['symbols'].append(dict(index=len(obj['symbols']),name='',info=3,other=0,section=symbol['section'],value=0,size=0));rel['symbol']=len(obj['symbols'])-1
  elif name=='output-function-bytes-rewritten':o['sections'][o['relocations'][0]['section']]['bytes']=b'xxxx'
  elif name=='output-table-bytes-rewritten':symbol=next(t for t in o['symbols'] if t['name']=='crypto_shash_type');o['sections'][symbol['section']]['bytes']=b'x'*8
  elif name=='output-table-relocation-missing':symbol=next(t for t in o['symbols'] if t['name']=='crypto_shash_type');o['relocations']=[r for r in o['relocations'] if r['section']!=symbol['section']]
  elif name=='weak-definition-resolution-reject':next(t for t in a['symbols'] if t['name']=='synthetic_shared')['info']=32
  elif name=='absolute-definition-resolution-reject':next(t for t in a['symbols'] if t['name']=='synthetic_shared')['section']=0xfff1
  check(name,lambda x=objects:link_origin(*x),name!='anonymous-section-target-origin')
 return {'passed':True,'cases':completed,'case_count':len(completed),'synthetic_only':True,'old_fixture_semantic_object_checker_or_target_replayed':False}


def frozen_main(cases,runner,inventory_key):
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--checkpoint',type=Path,required=True);p.add_argument('--checkpoint-sha256',required=True);p.add_argument('--inventory',type=Path,required=True);p.add_argument('--inventory-sha256',required=True);a=p.parse_args();require(not a.output.exists() and a.output.absolute().is_relative_to(Path(__file__).resolve().parents[2]/'note10/private'),'fresh private new-only result');completed=[];phase='attribution';attribution={'checkpoint_path':str(a.checkpoint.absolute()),'inventory_path':str(a.inventory.absolute())}
 try:
  cpraw=a.checkpoint.read_bytes();invraw=a.inventory.read_bytes();require(digest(cpraw)==a.checkpoint_sha256 and digest(invraw)==a.inventory_sha256,'exact reviewed checkpoint/inventory SHA256');cp=json.loads(cpraw);inventory=json.loads(invraw);attribution.update(checkpoint_sha256=digest(cpraw),inventory_sha256=digest(invraw));require(inventory['cases']==list(cases) and inventory['case_count']==len(cases) and cp[inventory_key]==list(cases),'frozen complete new case order');require(digest(Path(inventory['fixture_path']).read_bytes())==inventory['fixture_sha256'],'exact frozen fixture source')
  root=Path(__file__).resolve().parents[2]
  for group in ('public_sources_sha256','private_sources_sha256','shared_sources_sha256'):
   for name,expected in cp[group].items():require(digest((root/name).read_bytes())==expected,'current frozen new source/import closure')
  phase='synthetic_cases';result=runner(completed);result.update(attribution)
 except BaseException as error:
  write(a.output,dict(attribution,passed=False,cases=list(completed),case_count=len(completed),completed_case_names=list(completed),completed_case_count=len(completed),failing_next_case=cases[len(completed)] if len(completed)<len(cases) else None,failure_phase=phase,exception_type=type(error).__name__,exception_message=str(error),automatic_retry=False));raise
 write(a.output,result)


if __name__=='__main__':frozen_main(CASES,run_cases,'new_public_fixture_inventory')
