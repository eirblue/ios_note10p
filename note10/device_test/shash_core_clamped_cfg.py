"""Exact observed signed-clamp/index registration CFG, from owned object words only."""
import struct
from pre_pm_archive_contract import require
from sha256_provider_object import one_symbol,exact_target
from shash_core_instructions import decode,compare_provenance,csel32_gt
from shash_core_registration_cfg import registration_cfg


def registration_cfg_dispatch(obj,fn,stride):
 section=obj['sections'][fn['section']];start=fn['value'];end=start+fn['size'];require(start%4==0 and end<=len(section['bytes']) and fn['size']%4==0,'owned dispatcher function words')
 family=any(struct.unpack_from('<I',section['bytes'],pc)[0]&0x1fe00000==0x1a800000 for pc in range(start,end,4))
 if family:return clamped_registration_cfg(obj,fn,stride)
 return registration_cfg(obj,fn,stride)


def clamped_registration_cfg(obj,fn,stride):
 require(fn['name']=='crypto_register_shashes' and fn['info']&15==2 and fn['size']==128 and type(stride) is int and 0<stride<4096,'exact observed clamped function and actual DWARF stride')
 section=obj['sections'][fn['section']];start=fn['value'];require(start%4==0 and start+128<=len(section['bytes']),'actual owned clamped function extent');words={pc:struct.unpack_from('<I',section['bytes'],start+pc)[0] for pc in range(0,128,4)};used=set()
 def expect(pc,op,**fields):
  d=decode(words[pc]);used.add(pc);require(d['op']==op and all(d.get(key)==value for key,value in fields.items()),'observed clamped CFG word/operand mismatch at '+hex(pc));return d
 # Each callee-saved entry value is distinct, including X23 before its W23 clamp write.
 entry={r:('entry_X',r) for r in range(31)};regs=dict(entry);regs[0]=('arg_pointer',0);regs[1]=('arg',1);memory={};sp=0;saves=[]
 def saved(register,at):
  value=regs.get(register);require(value is not None and value==entry[register] and at not in memory,'save exact original entry-register identity once');memory[at]=(register,value);saves.append({'register':register,'slot_from_entry_SP':at,'entry_identity':value})
 def pair_store(pc,rd,rt2,delta,mode):
  nonlocal sp
  expect(pc,'pair-store',rd=rd,rt2=rt2,rn=31);word=words[pc];require((word>>30)&3==2 and (word>>23)&3==mode,'exact GPR64 frame-pair mode');encoded=(word>>15)&127;actual=(encoded-128 if encoded&64 else encoded)*8;require(actual==delta,'exact frame-pair offset')
  if mode==3:sp+=delta;at=sp
  else:at=sp+delta
  saved(rd,at);saved(rt2,at+8)
 pair_store(0,29,30,-64,3)
 expect(4,'store',rd=23,rn=31,offset=16,size=8);require(words[4]&0xffc00000==0xf9000000,'plain unsigned-offset STR X23; no writeback');saved(23,sp+16)
 expect(8,'add',rd=29,rn=31,imm=0,width=64,flags=False);regs[29]=('frame_pointer',sp)
 pair_store(12,22,21,32,2);pair_store(16,20,19,48,2)
 require(sp==-64 and set(memory)=={-64,-56,-48,-32,-24,-16,-8},'exact observed original frame slots')
 expect(20,'sub',rd=31,rn=1,imm=0,width=32,flags=True);nzcv=compare_provenance(regs[1],0,32,start+20)
 expect(24,'mov',rd=19,rn=0,width=64);regs[19]=regs[0]
 expect(28,'mov',rd=22,rn=31,width=64);regs[22]=0
 expect(32,'csel32gt',rd=23,rn=1,rm=31,condition=12,width=32);regs[23]=csel32_gt(regs[1],0,nzcv);require(regs[23]==('zero_extended_signed_positive_clamp32',('arg',1)) and nzcv['origin']==start+20,'fresh same-input signed clamp; no alternate NZCV producer')
 expect(36,'mov',rd=21,rn=0,width=64);regs[21]=regs[0]
 expect(40,'cmpreg64',rn=23,rm=22,width=64,flags=True);nzcv=compare_provenance(regs[23],regs[22],64,start+40)
 expect(44,'cond',condition=0,delta=72-44);require(nzcv['origin']==start+40 and nzcv['left']==regs[23] and nzcv['right']==regs[22],'immediate fresh 64-bit equality loop edge')
 expect(48,'mov',rd=0,rn=21,width=64)
 def call(pc,name):
  expect(pc,'bl');refs=[r for r in obj['relocations'] if r['section']==fn['section'] and r['offset']==start+pc];require(len(refs)==1 and refs[0]['type']==283,'exact clamped call relocation');r=refs[0];symbol=r['symbol'];target=one_symbol(obj,name,2)
  exact_target({'section':symbol['section'],'offset':symbol['value']+r['addend'],'addend':r['addend'],'symbol_name':symbol['name'],'symbol_value':symbol['value'],'symbol_size':symbol['size'],'symbol_info':symbol['info']},target)
 call(52,'crypto_register_shash');expect(56,'cb',rn=0,width=32,nonzero=True,delta=100-56)
 expect(60,'add',rd=22,rn=22,imm=1,width=64,flags=False);expect(64,'add',rd=21,rn=21,imm=stride,width=64,flags=False);expect(68,'b',delta=40-68)
 # Success writes zero only at72; failures return through76 and cannot enter72.
 expect(72,'mov',rd=20,rn=31,width=32);expect(76,'mov',rd=0,rn=20,width=32)
 expect(100,'mov',rd=20,rn=0,width=32);expect(104,'movz',rd=21,imm=stride,shift=0,width=32)
 expect(108,'sub',rd=22,rn=22,imm=1,width=32,flags=True);rollback_flags=compare_provenance(('registered_index_low32',22),1,32,start+108)
 expect(112,'cond',condition=11,delta=76-112);require(rollback_flags['origin']==start+108,'signed rollback edge consumes exact immediate decrement flags')
 expect(116,'umaddl',rd=0,rn=22,rm=21,ra=19,input_width=32,accumulator_width=64,width=64);call(120,'crypto_unregister_shash');expect(124,'b',delta=108-124)
 # A per-path abstract return check preserves the original entry tokens, never None equality.
 def return_frame(error):
  current=dict(regs);current[20]=('register_call_W0',start+52) if error else 0;current[0]=current[20];result=current[0];restored=set();local_sp=sp;facts=[]
  def restore(register,at):
   row=memory.get(at);require(row is not None and row[0]==register and row[1] is not None and row[1]==entry[register] and register not in restored,'restore same distinct original register token and exact slot');current[register]=row[1];restored.add(register);facts.append({'register':register,'slot_from_entry_SP':at,'identity':row[1]})
  expect(80,'load',rd=23,rn=31,offset=16,size=8);require(words[80]&0xffc00000==0xf9400000,'plain unsigned-offset LDR X23; no writeback');restore(23,local_sp+16)
  for pc,rd,rt2,delta,mode in ((84,20,19,48,2),(88,22,21,32,2),(92,29,30,64,1)):
   expect(pc,'pair-load',rd=rd,rt2=rt2,rn=31);word=words[pc];require((word>>30)&3==2 and (word>>23)&3==mode,'exact restore-pair mode');encoded=(word>>15)&127;actual=(encoded-128 if encoded&64 else encoded)*8;require(actual==delta,'exact restore-pair offset');at=local_sp if mode==1 else local_sp+delta;restore(rd,at);restore(rt2,at+8)
   if mode==1:local_sp+=delta
  expect(96,'ret');require(local_sp==0 and restored=={19,20,21,22,23,29,30} and current[0]==result,'balanced original frame, all callee tokens restored after result copy')
  require(result==(('register_call_W0',start+52) if error else 0),'exact saved error or zero success W result')
  return {'result':result,'restored_entry_values':facts,'SP_delta_on_return':local_sp}
 success=return_frame(False);failure=return_frame(True)
 require(used==set(words),'all128 bytes belong to connected observed grammar');refs=[r for r in obj['relocations'] if r['section']==fn['section'] and start<=r['offset']<start+128];require(len(refs)==2 and {r['offset'] for r in refs}=={start+52,start+120} and all(r['type']==283 for r in refs),'only two exact bound call sites; no extra edge')
 return {'connected_finite_CFG_verified':True,'variant':'observed-signed-clamp-index-loop','actual_function':fn,'all_word_offsets':[start+pc for pc in sorted(used)],'roles':{'base':19,'forward_pointer_then_stride':21,'registered_index':22,'clamped_count':23,'saved_error':20},'actual_DWARF_stride':stride,'clamp':'max(signed32(W1),0), zero-extended to X23','forward_invariant':'0<=I<=C<=INT_MAX; only zero call return advances I and P=base+I*stride','rollback_invariant':'signed low32 decrement exits before address/call when I=0; guarded nonnegative index uses unsigned32*stride+base modulo64; exact saved W error returns','frame_original_entry_saves':saves,'success_return':success,'error_return':failure,'callee_preservation_is_static_ABI_assumption':True,'arbitrary_count_pointer_validity_or_no_overflow_proven':False,'runtime_external_call_or_whole_path_stack_safety_proven':False}
