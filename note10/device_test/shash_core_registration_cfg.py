"""Connected finite registration/rollback CFG template from actual machine words.

This is a static verifier, not an executor. Unsupported compiler shapes reject.
"""
import struct
from pre_pm_archive_contract import require
from shash_core_instructions import decode,signed
from sha256_provider_object import one_symbol,exact_target


def registration_cfg(obj,fn,stride):
 require(type(stride) is int and 0<stride<4096,'finite actual shash_alg stride')
 section=obj['sections'][fn['section']];start=fn['value'];end=start+fn['size'];require(fn['name']=='crypto_register_shashes' and fn['size']>0 and fn['size']%4==0 and end<=len(section['bytes']),'complete actual registration function')
 words={pc:struct.unpack_from('<I',section['bytes'],pc)[0] for pc in range(start,end,4)};used=set();blocks={};roles={};saved={};stack=0;frame_pointer_written=False
 def instruction(pc):
  require(pc in words,'CFG target within actual registration function');used.add(pc);return decode(words[pc])
 def expect(pc,op,**fields):
  d=instruction(pc);require(d['op']==op and all(d.get(k)==v for k,v in fields.items()),'connected registration instruction/operand mismatch at '+hex(pc));return d
 def jump(pc,target):expect(pc,'b',delta=target-pc)
 def frame_pair(pc,load,sp,slots):
  word=words[pc];d=instruction(pc);require(d['op']==('pair-load' if load else 'pair-store') and d['rn']==31 and (word>>30)&3==2,'only actual 64-bit SP-based frame pairs')
  mode=(word>>23)&3;require(mode in (1,2,3),'finite frame addressing mode');delta=signed((word>>15)&127,7)*8;address=sp+delta if mode in (2,3) else sp;newsp=sp+delta if mode in (1,3) else sp
  for register,at in ((d['rd'],address),(d['rt2'],address+8)):
   require(19<=register<=30,'frame pairs cannot overwrite input/result registers')
   if load:require(slots.get(at)==register,'restore exact originally saved register from same stack slot')
   else:require(at not in slots and (register!=29 or not frame_pointer_written),'save original callee state once');slots[at]=register
  return newsp
 def call(pc,name):
  expect(pc,'bl');refs=[r for r in obj['relocations'] if r['section']==fn['section'] and r['offset']==pc];require(len(refs)==1 and refs[0]['type']==283,'one exact registration call relocation');r=refs[0];s=r['symbol'];target=one_symbol(obj,name,2)
  exact_target({'section':s['section'],'offset':s['value']+r['addend'],'addend':r['addend'],'symbol_name':s['name'],'symbol_value':s['value'],'symbol_size':s['size'],'symbol_info':s['info']},target)
 def zero(pc,rd):
  d=instruction(pc);require(d=={'op':'mov','rd':rd,'rn':31,'width':32} or d=={'op':'movz','rd':rd,'imm':0,'shift':0,'width':32},'exact W-register zero initialization')
 def epilogue(pc):
  local_sp=stack;restored=set();visited=set()
  while True:
   require(pc not in visited,'acyclic exact return epilogue');visited.add(pc);d=instruction(pc)
   if d['op']=='pair-load':
    require(d['rd'] not in restored and d['rt2'] not in restored,'restore each callee-saved register once');restored.update((d['rd'],d['rt2']));local_sp=frame_pair(pc,True,local_sp,saved);pc+=4
   elif d['op']=='add' and d.get('rd')==31 and d.get('rn')==31 and d.get('width')==64 and not d.get('flags'):local_sp+=d['imm'];pc+=4
   elif d['op']=='b':pc+=d['delta']
   elif d['op']=='ret':
    require(local_sp==0 and restored==set(saved.values()) and set(roles.values())<=restored,'balanced actual frame and all role registers restored on return');return
   else:raise ValueError('unsupported or result-clobbering return epilogue')
 # Frame changes are allowed only before any input/role mutation.
 pc=start
 while True:
  d=decode(words[pc])
  if d['op']=='pair-store':stack=frame_pair(pc,False,stack,saved);pc+=4
  elif d['op']=='sub' and d.get('rd')==31 and d.get('rn')==31 and d.get('width')==64 and not d.get('flags'):instruction(pc);stack-=d['imm'];pc+=4
  elif d['op']=='add' and d.get('rd')==29 and d.get('rn')==31 and d.get('width')==64 and not d.get('flags'):instruction(pc);frame_pointer_written=True;pc+=4
  else:break
 require(stack<0 and 30 in saved.values() and (not frame_pointer_written or 29 in saved.values()) and all(at>=stack and at+8<=0 for at in saved),'bounded original frame slots and saved return/frame state')
 # Exactly the input pointer, signed remaining count and zero successful-count.
 init=pc;d=expect(pc,'mov',rn=0,width=64);roles['pointer']=d['rd'];pc+=4;d=expect(pc,'mov',rn=1,width=32);roles['remaining']=d['rd'];pc+=4;d=instruction(pc);roles['registered']=d.get('rd');zero(pc,roles['registered']);pc+=4
 p=roles['pointer'];r=roles['remaining'];i=roles['registered'];require(len({p,r,i})==3 and all(type(v) is int and 19<=v<=28 for v in (p,r,i)),'distinct preserved pointer/count/index role registers')
 expect(pc,'sub',rd=31,rn=r,width=32,imm=0,flags=True);pc+=4;d=expect(pc,'cond',condition=13);success=pc+d['delta'];pc+=4;loop=pc
 # Forward induction invariant: P=algs+I*stride; R=count-I; I starts zero.
 expect(pc,'mov',rd=0,rn=p,width=64);pc+=4;register_call=pc;call(pc,'crypto_register_shash');pc+=4
 d=instruction(pc)
 if d['op']=='cb':expect(pc,'cb',rn=0,width=32,nonzero=True);failure=pc+d['delta'];pc+=4
 else:
  expect(pc,'sub',rd=31,rn=0,width=32,imm=0,flags=True);pc+=4;d=expect(pc,'cond',condition=1);failure=pc+d['delta'];pc+=4
 expect(pc,'add',rd=p,rn=p,width=64,imm=stride,flags=False);pc+=4;expect(pc,'add',rd=i,rn=i,width=32,imm=1,flags=False);pc+=4;expect(pc,'sub',rd=r,rn=r,width=32,imm=1,flags=True);pc+=4;expect(pc,'cond',condition=1,delta=loop-pc);pc+=4
 # Exhaustion reaches success; it must never enter rollback.
 if pc!=success:jump(pc,success)
 zero(success,0);epilogue(success+4)
 # Nonzero registration result is copied before any unregister call can clobber W0.
 pc=failure;d=expect(pc,'mov',rn=0,width=32);e=d['rd'];roles['error']=e;require(19<=e<=28 and e not in (p,r,i),'distinct preserved error result');pc+=4
 d=expect(pc,'cb',rn=i,width=32,nonzero=False);error_return=pc+d['delta'];pc+=4;rollback=pc
 # I>0 guard dominates unregister. Reverse P before call, decrement I after call.
 expect(pc,'sub',rd=p,rn=p,width=64,imm=stride,flags=False);pc+=4;expect(pc,'mov',rd=0,rn=p,width=64);pc+=4;unregister_call=pc;call(pc,'crypto_unregister_shash');pc+=4;expect(pc,'sub',rd=i,rn=i,width=32,imm=1,flags=True);pc+=4;expect(pc,'cond',condition=1,delta=rollback-pc);pc+=4
 if pc!=error_return:jump(pc,error_return)
 expect(error_return,'mov',rd=0,rn=e,width=32);epilogue(error_return+4)
 # Recheck success now all four role registers are known, including error storage.
 epilogue(success+4)
 require(set(words)==used,'every actual instruction connected to the proved entry/forward/rollback/return grammar; no disconnected evidence')
 allowed_calls={register_call,unregister_call};rels=[r for r in obj['relocations'] if r['section']==fn['section'] and start<=r['offset']<end];require(len(rels)==2 and {x['offset'] for x in rels}==allowed_calls and all(x['type']==283 for x in rels),'exact two call sites; no unsupported extra code/data edges')
 blocks.update(entry=init,forward_loop=loop,success=success,failure=failure,rollback_loop=rollback,error_return=error_return)
 return {'connected_finite_CFG_verified':True,'actual_function':fn,'blocks':blocks,'role_registers':roles,'register_call':register_call,'unregister_call':unregister_call,'actual_element_stride':stride,'all_word_offsets':sorted(used),'forward_invariant':'P=algs+I*stride; R=count-I; initial I=0; only zero call result advances P/I and decrements R','rollback_invariant':'nonzero call result saved; I=0 skips cleanup; I>0 decrements P before unregister and I after; returns exact saved W result','success_return':'W0=0 with balanced original frame','arbitrary_count_storage_or_pointer_validity_proven':False,'runtime_registration_or_whole_path_stack_safety_proven':False}
