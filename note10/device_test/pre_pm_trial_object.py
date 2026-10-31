"""Full diagnostic TU static evidence. Never links, executes, or invents OS frames."""
import re,struct
from kernel_trial_object import parse_elf,usage_frames
from relocation_trial_instructions import ROW
from relocation_trial_kernel_profile import gpr_only
from prepare_pre_pm_trial import require
CALLER='note10_check_xnu_window'
ORDER=('n10_arm_auto_return','n10_stage_xnu_payload','n10_test_cpu_cache','n10_pre_pm_trial','n10_start_pm_timer')
KERNEL_CONTEXT={('mrs','sp_el0'),('mrs','tpidr_el1'),('mrs','daif'),('msr','daifset'),('msr','daifclr')}
def function(obj,name):
 found=[s for s in obj['symbols'] if s['name']==name and s['info']&15==2]
 require(len(found)==1,'unique actual function range: '+name);s=found[0]
 require(s['size']>0 and s['section']<len(obj['sections']) and s['value']+s['size']<=len(obj['sections'][s['section']]['bytes']),'bounded actual function extent')
 return s
def owner(obj,section,offset):
 require(0<section<len(obj['sections']) and 0<=offset<len(obj['sections'][section]['bytes']),'call target section/position bounded')
 matches=[s for s in obj['symbols'] if s['info']&15==2 and s['section']==section and s['value']<=offset<s['value']+s['size']]
 require(len(matches)==1,'ambiguous/missing function owning branch target');require(matches[0]['value']==offset,'call into function interior rejected');return matches[0]['name']
def decoded(text,obj):
 sections={s['name']:s for s in obj['sections']};section=None;rows={}
 for line in text.splitlines():
  if line.startswith('Disassembly of section '):
   name=line.removeprefix('Disassembly of section ').removesuffix(':');require(name in sections,'actual disassembly section');section=sections[name];continue
  m=ROW.fullmatch(line)
  if not m:continue
  require(section is not None,'instruction without section');off=int(m[1],16);enc=bytes.fromhex(m[2]);enc=enc[::-1] if len(m[2])==8 else enc
  require(off%4==0 and section['bytes'][off:off+4]==enc and (section['index'],off) not in rows,'disassembly instruction bytes/extent/duplicates')
  rows[section['index'],off]={'offset':off,'mnemonic':m[3],'operands':m[4],'word':int.from_bytes(enc,'little')}
 return rows
def branch_target(obj,section,row):
 off=row['offset'];rels=[r for r in obj['relocations'] if r['section']==section and r['offset']==off]
 if rels:
  require(len(rels)==1 and rels[0]['type']==(283 if row['mnemonic']=='bl' else 282) and row['word']>>26==(37 if row['mnemonic']=='bl' else 5),'actual call relocation/opcode kind');r=rels[0];s=r['symbol']
  if s['section']==0:
   require(s['name'] and r['addend']==0,'unresolved OS call must have exact named zero-addend target');return s['name']
  return owner(obj,s['section'],s['value']+r['addend'])
 word=row['word'];require(word>>26 in (5,37),'resolved direct B/BL opcode');delta=word&0x3ffffff;delta=delta-(1<<26) if delta&(1<<25) else delta
 return owner(obj,section,off+4*delta)
def local_target(row):
 w=row['word'];off=row['offset'];m=row['mnemonic']
 if m=='b':imm=w&0x3ffffff;bits=26
 elif m.startswith('b.') or m in ('cbz','cbnz'):imm=(w>>5)&0x7ffff;bits=19
 elif m in ('tbz','tbnz'):imm=(w>>5)&0x3fff;bits=14
 else:raise ValueError('not a finite conditional branch')
 if imm&(1<<(bits-1)):imm-=1<<bits
 return off+imm*4

def cfg_order(obj,rows,enabled):
 caller=function(obj,CALLER);sec=caller['section'];start=caller['value'];end=start+caller['size'];code={o:r for (s,o),r in rows.items() if s==sec and start<=o<end}
 require(set(code)==set(range(start,end,4)),'complete caller instruction decoding')
 calls={};edges={};allcalls=[]
 for off,row in code.items():
  m=row['mnemonic'];successors=[]
  if m in ('bl','b'):
   if m=='b' and start<=local_target(row)<end and not any(r['section']==sec and r['offset']==off for r in obj['relocations']):successors=[local_target(row)]
   else:
    target=branch_target(obj,sec,row);calls[off]=target;allcalls.append({'offset':off,'target':target,'encoding':f"{row['word']:08x}"})
    if m=='bl':successors=[off+4]
  elif m=='ret':pass
  elif m.startswith('b.') or m in ('cbz','cbnz','tbz','tbnz'):successors=[off+4,local_target(row)]
  elif m in ('br','blr'):raise ValueError('indirect caller control flow rejected')
  else:successors=[off+4]
  require(all(x in code for x in successors),'caller branch escapes bounded function');edges[off]=successors
 required=ORDER if enabled else tuple(n for n in ORDER if n!='n10_pre_pm_trial')
 positions={n:[o for o,t in calls.items() if t==n] for n in required}
 require(all(len(v)==1 for v in positions.values()),'unique actual named provider calls')
 if not enabled:require('n10_pre_pm_trial' not in calls.values(),'disabled wrapper call absent')
 # Every path reaching each stage must have traversed all preceding required calls.
 seen=set();todo=[(start,0)]
 while todo:
  off,mask=todo.pop()
  if (off,mask) in seen:continue
  seen.add((off,mask));target=calls.get(off)
  if target in required:
   i=required.index(target);require(mask&((1<<i)-1)==(1<<i)-1,'actual CFG provider dominance/order');mask|=1<<i
  todo.extend((n,mask) for n in edges[off])
 require(any(calls.get(o)==required[-1] for o,_ in seen),'PM path actually reachable')
 # Return-status guards: W0 CBZ/CBNZ immediately after each guarded BL.
 guards=[]
 for name in ('n10_arm_auto_return','n10_stage_xnu_payload','n10_test_cpu_cache',*(['n10_pre_pm_trial'] if enabled else [])):
  off=positions[name][0];row=code[off+4];require(row['mnemonic'] in ('cbz','cbnz') and re.match(r'w0,',row['operands']),'actual W0 success guard immediately after call')
  failure=local_target(row) if row['mnemonic']=='cbnz' else off+8
  todo=[failure];visited=set()
  while todo:
   p=todo.pop()
   if p in visited:continue
   visited.add(p);require(calls.get(p)!='n10_start_pm_timer','failure can queue PM');todo.extend(edges[p])
  guards.append({'provider':name,'call_offset':off,'guard_offset':off+4,'failure_successors':sorted(visited),'PM_unreachable_on_failure':True})
 return {'function':caller,'calls':allcalls,'required_order':list(required),'guarded_failures':guards,'actual_CFG_verified':True}

def wrapper_unwind(obj,rows):
 wrapper=function(obj,'n10_pre_pm_trial');sec=wrapper['section'];start=wrapper['value'];end=start+wrapper['size'];code={o:r for (s,o),r in rows.items() if s==sec and start<=o<end}
 calls={};edges={}
 for off,row in code.items():
  m=row['mnemonic'];nexts=[]
  if m in ('bl','b'):
   rel=any(r['section']==sec and r['offset']==off for r in obj['relocations'])
   if m=='b' and not rel and start<=local_target(row)<end:nexts=[local_target(row)]
   else:
    calls[off]=branch_target(obj,sec,row)
    if m=='bl':nexts=[off+4]
  elif m=='ret':pass
  elif m.startswith('b.') or m in ('cbz','cbnz','tbz','tbnz'):nexts=[off+4,local_target(row)]
  elif m in ('br','blr'):raise ValueError('unknown indirect wrapper flow')
  else:nexts=[off+4]
  require(all(p in code for p in nexts),'bounded wrapper CFG');edges[off]=nexts
 trial=[o for o,n in calls.items() if n=='n10_rt_trial'];require(len(trial)==1,'single admitted actual production trial call')
 # The post-call path must always restore, barrier, both full hashes, byte compare,
 # and both guards before freeing or returning. No short-circuit evidence claim.
 obligations=['restore','barrier','n10_pre_pm_hash','n10_pre_pm_hash','memcmp','n10_pre_pm_guard','n10_pre_pm_guard']
 todo=[(trial[0]+4,0)];seen=set();restore_sites=[]
 while todo:
  off,state=todo.pop()
  if (off,state) in seen:continue
  seen.add((off,state));target=calls.get(off);row=code[off]
  expected=obligations[state] if state<len(obligations) else None
  event='restore' if target in ('memcpy','__memcpy') else 'barrier' if row['mnemonic'] in ('dmb','dsb') else target
  if event==expected:
   if event=='restore':restore_sites.append(off)
   state+=1
  if target in ('vfree','kfree','crypto_free_shash') or not edges[off]:require(state==len(obligations),'post-trial path bypasses complete restore/check/unwind sequence')
  require(target!='n10_start_pm_timer','wrapper cannot queue PM')
  todo.extend((n,state) for n in edges[off])
 require(restore_sites and any(not edges[o] for o,_ in seen),'actual restoration and exit reachable')
 return {'trial_offset':trial[0],'unconditional_full_restore_sites':sorted(set(restore_sites)),'sequenced_postcheck_obligations':obligations,'all_post_trial_exits_verified':True,'backup_corruption_DMA_restoration_guarantee':False}

def reachable_functions(obj,rows):
 todo=['n10_pre_pm_trial','n10_pre_pm_cmp'];seen=set();external=[];indirect=[]
 defined={s['name'] for s in obj['symbols'] if s['info']&15==2 and s['section']!=0}
 while todo:
  name=todo.pop()
  if name in seen:continue
  require(len(seen)<512,'finite actual source helper closure');seen.add(name);s=function(obj,name)
  for off in range(s['value'],s['value']+s['size'],4):
   require((s['section'],off) in rows,'complete reachable helper instruction range');r=rows[s['section'],off];m=r['mnemonic']
   if m=='blr':indirect.append({'function':name,'offset':off,'operands':r['operands'],'OS_provider_stack_unresolved':True})
   if m not in ('bl','b'):continue
   rel=any(x['section']==s['section'] and x['offset']==off for x in obj['relocations'])
   if m=='b' and not rel and s['value']<=local_target(r)<s['value']+s['size']:continue
   target=branch_target(obj,s['section'],r)
   if target in defined:todo.append(target)
   else:external.append({'function':name,'offset':off,'target':target})
 callback=function(obj,'n10_pre_pm_cmp');wrapper=function(obj,'n10_pre_pm_trial')
 refs=[r for r in obj['relocations'] if r['section']==wrapper['section'] and wrapper['value']<=r['offset']<wrapper['value']+wrapper['size'] and r['symbol']['section']==callback['section'] and r['symbol']['value']+r['addend']==callback['value']]
 require(refs and all(r['type'] in (275,277) for r in refs),'actual source-bound sort comparator address references')
 return sorted(seen),external,indirect

def selected_isa(obj,rows):
 selected=[];context=[];functions=[];reachable,external,indirect=reachable_functions(obj,rows)
 for s in obj['symbols']:
  if s['info']&15!=2 or s['name'] not in reachable:continue
  functions.append(s['name']);require(s['size']>0,'selected function extent')
  for off in range(s['value'],s['value']+s['size'],4):
   require((s['section'],off) in rows,'all selected instructions decoded');r=rows[s['section'],off];m=r['mnemonic'];oper=r['operands'];clean=re.sub(r'<[^<>]*>','',oper)
   if m=='blr':
    require(re.fullmatch(r'x(?:[0-9]|[12][0-9]|30)',clean.strip()) is not None,'actual indirect kernel provider GPR operand');context.append({'function':s['name'],'offset':off,'mnemonic':m,'operands':oper,'provider_target_unresolved':True});continue
   if m in ('mrs','msr'):
    fields=[x.strip().lower() for x in clean.split(',')];reg=fields[1] if m=='mrs' else fields[0]
    require((m,reg) in KERNEL_CONTEXT,'source-bound kernel context register only');context.append({'function':s['name'],'offset':off,'mnemonic':m,'operands':oper});continue
   if m in ('dmb','dsb','isb'):
    require(clean.strip() in ('ish','ishst','sy'),'source-bound kernel barrier');context.append({'function':s['name'],'offset':off,'mnemonic':m,'operands':oper});continue
   text='Disassembly of section .text:\n'+f"{off:x}: {r['word']:08x} {m} {oper}\n"
   gpr_only(text);selected.append({'function':s['name'],'offset':off,'word':r['word']})
 require('n10_pre_pm_trial' in functions and 'n10_rt_trial' in functions,'actual enabled scoped ISA symbols')
 return {'functions':sorted(set(functions)),'ordinary_instruction_count':len(selected),'kernel_context_instructions':context,'external_provider_calls':external,'indirect_provider_calls':indirect,'whole_TU_GPR_claim':False,'hardware_FP_permission_claim':False}

def object_proof(raw,text,usage,enabled):
 obj=parse_elf(raw,1);rows=decoded(text,obj);names={s['name'] for s in obj['symbols']};frames=usage_frames(usage)
 if not enabled:require(not any(n.startswith('n10_pre_pm_') or n=='n10_rt_trial' for n in names),'disabled no wrapper/trial objects')
 ordering=cfg_order(obj,rows,enabled)
 required=[CALLER,'n10_stage_xnu_payload','n10_test_cpu_cache','n10_arm_auto_return','n10_start_pm_timer']
 if enabled:required+=['n10_pre_pm_trial','n10_rt_trial','n10_rt_plan','n10_rt_validate_adt','adt_node']
 for n in required:function(obj,n);require(n in frames,'actual required function frame missing: '+n)
 reachable,external_calls,indirect_calls=reachable_functions(obj,rows) if enabled else ([],[],[])
 require(all(n in frames and type(frames[n]) is int for n in set(required)|set(reachable)),'complete static actual scoped frame rows; never infer inlined/unknown zero')
 scoped={n:frames[n] for n in sorted(set(required)|set(reachable))}
 oracle=None;leaf_proof=None
 if enabled:
  expected_tree=struct.pack('<II32sI12s',1,0,b'name',12,b'device-tree\0')
  readonly={}
  for name,expected in (('n10_pre_pm_tree',expected_tree),('n10_pre_pm_expected',bytes.fromhex('3b3e7299672928ebe7086582891ddf35878e1cd5ed60bfd9ce710d8a864e7b36'))):
   found=[s for s in obj['symbols'] if s['name']==name];require(len(found)==1,'unique readonly leaf/digest symbol');sym=found[0];section=obj['sections'][sym['section']]
   require(sym['info']==1 and section['flags']&2 and not section['flags']&5 and sym['size']==len(expected) and section['bytes'][sym['value']:sym['value']+sym['size']]==expected,'actual immutable readonly leaf/digest bytes')
   readonly[name]={'section':section['name'],'offset':sym['value'],'size':sym['size']}
  leaf_proof={'readonly_symbols':readonly,'children':0,'parser_frames':1,'source_pinned_production_parser_required':True}

  candidates=[s for s in obj['symbols'] if s['name']=='n10_kernel_stack_oracle'];require(len(candidates)==1,'actual-header stack oracle')
  sym=candidates[0];section=obj['sections'][sym['section']];require(not section['flags']&5 and section['flags']&2 and sym['size']==16,'readonly actual-header oracle');thread,irq=struct.unpack_from('<QQ',section['bytes'],sym['value']);oracle={'THREAD_SIZE':thread,'IRQ_STACK_SIZE':irq,'whole_OS_IRQ_stack_safety_proven':False}
 frame_facts={'sum_retained_scoped_frames':sum(scoped.values()),'actual_scoped_frames':scoped,'incoming_trial_stack_argument_bytes':32,'generic_extra_ADT_frames':9,'generic_extra_ADT_bytes':9*frames.get('adt_node',0),'external_provider_stack_bounded':False,'whole_path_bound_claimed':False}
 external=sorted({r['symbol']['name'] for r in obj['relocations'] if r['symbol']['section']==0 and r['symbol']['name']})
 require(not any(n.startswith('OUTLINED_FUNCTION_') for n in names),'no inferred outlined helper frames')
 return {'object_sha256':obj['sha256'],'order':ordering,'frames':scoped,'frame_facts':frame_facts,'actual_header_oracle':oracle,'immutable_leaf_proof':leaf_proof,'generic_ADT_maximum_frames':10,'modeled_leaf_ADT_frames':1,
  'external_kernel_symbols':external,'selected_ISA':selected_isa(obj,rows) if enabled else None,'post_trial_unwind':wrapper_unwind(obj,rows) if enabled else None,'external_OS_IRQ_stack_bounded':False,
  'physical_stack_safety_proven':False,'fixed_external_stack_allowance_used':False,'wrapper_executed':False}
