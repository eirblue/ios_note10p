"""Only new composite-policy and real function_facts integration fixtures."""
import argparse,copy,hashlib,json,struct
from pathlib import Path
from pre_pm_archive_contract import require
from shash_core_object import object_rows,function_facts,dispatch_proof
from shash_core_gpr_policy import EXPECTED,POLICY,gpr_partition,bind_typed_coverage
CASES=('update-function-facts-integration','final-function-facts-integration','finup-function-facts-integration','digest-function-facts-integration','four-typed-edges-final-join','ordinary-no-BLR-delegation','exact-row-partition-counts','original-BLR-row-retained','unapproved-function-reject','wrong-owned-site-reject','extra-BLR-reject','missing-BLR-reject','BLR-word-fake-NOP-text-reject','wrong-operand-register-reject','wrong-word-register-reject','W-operand-reject','BR-tail-reject','authenticated-branch-reject','authenticated-word-fake-NOP-reject','FP-ordinary-row-reject','missing-header-integration-reject','wrong-header-integration-reject','row-byte-mismatch-integration-reject','row-address-mismatch-integration-reject','duplicate-policy-row-reject','missing-policy-row-reject','cross-section-policy-header-reject','ordinary-count-tamper-reject','missing-separated-row-reject','duplicate-typed-coverage-reject','cross-function-row-reject','wrong-slot-proof-reject','wrong-call-offset-proof-reject','missing-dispatch-proof-reject','extra-dispatch-proof-reject','missing-callback-function-reject','extra-BLR-trace-event-reject','wrong-trace-register-reject','wrong-trace-descriptor-reject','unknown-trace-target-reject','wrong-proof-target-reject','actual-wrong-slot-integration-reject','actual-wrong-descriptor-integration-reject','incomplete-word-map-reject','out-of-extent-policy-row-reject','BR-trace-event-reject','runtime-resolved-claim-reject','wrong-row-section-reject','full-word-count-tamper-reject','duplicate-function-identity-reject')
SITES=(('crypto_shash_update',96,'update',8),('crypto_shash_final',80,'final',16),('crypto_shash_finup',112,'finup',24),('crypto_shash_digest',132,'digest',32))

def line(pc,word,mnemonic,operand=''):
 encoded=' '.join(f'{byte:02x}' for byte in struct.pack('<I',word));return f'{pc:8x}: {encoded}  \t{mnemonic}\t{operand}'

def fixture():
 obj={'sections':[{'index':0,'name':'','bytes':b'','flags':0}],'symbols':[],'relocations':[]};display={};frames={};symbols={}
 for index,(name,site,field,offset) in enumerate(SITES,1):
  definitions={0:(0xa9bf7bfd,'stp','x29, x30, [sp, #-16]!'),4:(0x910003fd,'mov','x29, sp'),8:(0xf9400008,'ldr','x8, [x0]'),12:(0xf9405d09,'ldr','x9, [x8, #184]'),16:(0xf8400000|(((offset-256)&511)<<12)|(9<<5)|8,'ldur',f'x8, [x9, #{offset-256}]')}
  for pc in range(20,site,4):definitions[pc]=(0xd503201f,'nop','')
  definitions[site]=(0xd63f0100,'blr','x8');definitions[site+4]=(0xa8c17bfd,'ldp','x29, x30, [sp], #16');definitions[site+8]=(0xd65f03c0,'ret','')
  raw=b''.join(struct.pack('<I',definitions[pc][0]) for pc in sorted(definitions));symbol={'name':name,'info':18,'section':index,'value':0,'size':len(raw)};obj['sections'].append({'index':index,'name':'.text.'+name,'bytes':raw,'flags':6});obj['symbols'].append(symbol);symbols[name]=symbol;display[name]=definitions;frames[name]={'bytes':16,'classification':'static','fixed_frame_only':True}
 fields={'shash_desc':(('tfm',0,8),),'crypto_shash':(('base',128,8),),'crypto_tfm':(('__crt_alg',56,8),),'shash_alg':(('base',256,8),('update',8,8),('final',16,8),('finup',24,8),('digest',32,8))}
 layouts={'types':{name:{'members':[{'name':field,'offset':off,'type':{'kind':'pointer','byte_size':size}} for field,off,size in members]} for name,members in fields.items()}}
 return obj,symbols,display,frames,layouts

def text_for(obj,symbol,definitions):
 return 'Disassembly of section '+obj['sections'][symbol['section']]['name']+':\n'+'\n'.join(line(pc,*definitions[pc]) for pc in sorted(definitions))

def altered(obj,symbol,definitions,pc,word,mnemonic,operand=''):
 raw=bytearray(obj['sections'][symbol['section']]['bytes']);struct.pack_into('<I',raw,pc,word);obj['sections'][symbol['section']]['bytes']=bytes(raw);definitions[pc]=(word,mnemonic,operand)

def run_cases():
 completed=[];obj,symbols,display,frames,layouts=fixture();facts={};proofs={}
 def check(index,fn,reject=False):
  require(index==len(completed),'exact new policy fixture inventory')
  try:fn()
  except (ValueError,KeyError):
   if not reject:raise
  else:require(not reject,'invalid new typed policy fixture accepted: '+CASES[index])
  completed.append(CASES[index])
 def equal(actual,expected):require(actual==expected,'independent new policy fixture expectation')
 def analyze(o,s,d):return function_facts(o,s,object_rows(o,text_for(o,s,d)),frames)
 for index,(name,site,field,offset) in enumerate(SITES):
  def integration():
   fact=analyze(obj,symbols[name],display[name]);require(fact['ISA']['typed_proof_required'] is True and fact['ISA']['old_helper_accepted_BLR'] is False,'function_facts stays provisional; ordinary helper accepted no BLR');facts[name]=fact;proofs[field]=dispatch_proof(fact,layouts,field)
  check(index,integration)
 check(4,lambda:bind_typed_coverage(facts,proofs))
 def ordinary():
  symbol={'name':'fixture_ordinary','info':18,'section':1,'value':0,'size':4};o={'sections':[{'name':'','bytes':b''},{'name':'.text.fixture_ordinary','bytes':struct.pack('<I',0xd65f03c0)}],'symbols':[symbol]};text='Disassembly of section .text.fixture_ordinary:\n'+line(0,0xd65f03c0,'ret');p=gpr_partition(o,symbol,{0:0xd65f03c0},text);require(p['ordinary_instruction_count']==p['instruction_count']==1 and p['typed_indirect_count']==0 and p['ordinary_subset_is_full_scope'] is True and p['old_helper_accepted_BLR'] is False,'no-BLR ordinary scope/count')
 check(5,ordinary)
 def counts():
  for fact in facts.values():
   p=fact['ISA'];require(p['instruction_count']==fact['symbol']['size']//4==p['ordinary_instruction_count']+p['typed_indirect_count'] and p['ordinary_subset']['instruction_count']==p['ordinary_instruction_count'],'exhaustive full/ordinary/typed counts')
 check(6,counts)
 update='crypto_shash_update';site=96;symbol=symbols[update];definitions=display[update];header='Disassembly of section .text.crypto_shash_update:';text=text_for(obj,symbol,definitions);words={pc:definition[0] for pc,definition in definitions.items()}
 check(7,lambda:equal(facts[update]['ISA']['typed_indirect_sites'][0]['original_row'],line(site,0xd63f0100,'blr','x8')))
 def code_mutation(index,pc,word,mnemonic,operand=''):
  o=copy.deepcopy(obj);s=copy.deepcopy(symbol);d=copy.deepcopy(definitions);altered(o,s,d,pc,word,mnemonic,operand);check(index,lambda:analyze(o,s,d),True)
 def unapproved():
  o=copy.deepcopy(obj);s=o['symbols'][0];s['name']='fixture_unapproved';o['sections'][1]['name']='.text.fixture_unapproved';function_facts(o,s,object_rows(o,text_for(o,s,definitions)),{**frames,'fixture_unapproved':frames[update]})
 check(8,unapproved,True)
 def wrong_site():
  o=copy.deepcopy(obj);s=o['symbols'][0];d=copy.deepcopy(definitions);altered(o,s,d,92,0xd63f0100,'blr','x8');altered(o,s,d,96,0xd503201f,'nop');analyze(o,s,d)
 check(9,wrong_site,True)
 code_mutation(10,92,0xd63f0100,'blr','x8');code_mutation(11,96,0xd503201f,'nop');code_mutation(12,96,0xd63f0100,'nop');code_mutation(13,96,0xd63f0100,'blr','x9');code_mutation(14,96,0xd63f0120,'blr','x9');code_mutation(15,96,0xd63f0100,'blr','w8');code_mutation(16,96,0xd61f0100,'br','x8');code_mutation(17,96,0xd73f0900,'blraa','x8, x9');code_mutation(18,96,0xd73f0900,'nop');code_mutation(19,20,0x9e670000,'fmov','d0, x0')
 check(20,lambda:function_facts(obj,symbol,object_rows(obj,'\n'.join(text.splitlines()[1:])),frames),True)
 check(21,lambda:function_facts(obj,symbol,object_rows(obj,text.replace(header,'Disassembly of section .text.crypto_shash_final:')),frames),True)
 check(22,lambda:function_facts(obj,symbol,object_rows(obj,text.replace('00 01 3f d6','20 01 3f d6')),frames),True)
 check(23,lambda:function_facts(obj,symbol,object_rows(obj,text.replace(line(96,*definitions[96]),line(100,*definitions[96]))),frames),True)
 check(24,lambda:gpr_partition(obj,symbol,words,text+'\n'+line(96,*definitions[96])),True)
 check(25,lambda:gpr_partition(obj,symbol,words,text.replace(line(20,*definitions[20])+'\n','')),True)
 check(26,lambda:gpr_partition(obj,symbol,words,text+'\nDisassembly of section .text.crypto_shash_final:'),True)
 def join_mutation(index,change):
  fs=copy.deepcopy(facts);ds=copy.deepcopy(proofs);change(fs,ds);check(index,lambda:bind_typed_coverage(fs,ds),True)
 join_mutation(27,lambda f,d:f[update]['ISA'].update(ordinary_instruction_count=999))
 join_mutation(28,lambda f,d:f[update]['ISA']['typed_indirect_sites'].clear())
 join_mutation(29,lambda f,d:f[update]['ISA']['typed_indirect_sites'].append(copy.deepcopy(f[update]['ISA']['typed_indirect_sites'][0])))
 join_mutation(30,lambda f,d:f[update]['ISA']['typed_indirect_sites'][0].update(function='crypto_shash_final'))
 join_mutation(31,lambda f,d:d['update'].update(slot='final'))
 join_mutation(32,lambda f,d:d['update'].update(call_offset=100))
 join_mutation(33,lambda f,d:d.pop('update'))
 join_mutation(34,lambda f,d:d.update(setkey=copy.deepcopy(d['update'])))
 join_mutation(35,lambda f,d:f.pop('crypto_shash_digest'))
 def trace_event(f):return next(e for e in f[update]['events'] if e['decoded']['op']=='blr')
 join_mutation(36,lambda f,d:f[update]['events'].append(copy.deepcopy(trace_event(f))))
 join_mutation(37,lambda f,d:trace_event(f)['decoded'].update(rn=9))
 join_mutation(38,lambda f,d:trace_event(f)['arguments'].__setitem__(0,('arg',1)))
 join_mutation(39,lambda f,d:trace_event(f).update(target=None))
 join_mutation(40,lambda f,d:d['update'].update(actual_target_expression=('wrong-slot',)))
 def wrong_slot():
  o=copy.deepcopy(obj);s=o['symbols'][0];d=copy.deepcopy(definitions);word=0xf8400000|(((-240)&511)<<12)|(9<<5)|8;altered(o,s,d,16,word,'ldur','x8, [x9, #-240]');dispatch_proof(analyze(o,s,d),layouts,'update')
 check(41,wrong_slot,True)
 def wrong_descriptor():
  o=copy.deepcopy(obj);s=o['symbols'][0];d=copy.deepcopy(definitions);altered(o,s,d,92,0xaa0103e0,'mov','x0, x1');dispatch_proof(analyze(o,s,d),layouts,'update')
 check(42,wrong_descriptor,True)
 incomplete=dict(words);incomplete.pop(20);check(43,lambda:gpr_partition(obj,symbol,incomplete,text),True)
 check(44,lambda:gpr_partition(obj,symbol,words,text+'\n'+line(symbol['size'],0xd503201f,'nop')),True)
 join_mutation(45,lambda f,d:trace_event(f)['decoded'].update(op='br'))
 join_mutation(46,lambda f,d:d['update'].update(callback_execution_unresolved=False))
 join_mutation(47,lambda f,d:f[update]['ISA']['typed_indirect_sites'][0].update(section_index=2))
 join_mutation(48,lambda f,d:f[update]['ISA'].update(instruction_count=1))
 join_mutation(49,lambda f,d:f.update(unexpected_alias=copy.deepcopy(f[update])))
 return {'passed':True,'cases':completed,'case_count':len(completed),'synthetic_only':True,'actual_function_facts_header_policy_finite_word_trace_dispatch_and_final_binder_exercised':True,'old49_28_14_76_53_replayed':False,'actual_retained_object_checker_decoder_model_compiler_or_target_replayed':False,'runtime_or_hardware_proven':False}

def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();out=a.output.absolute();require(out.is_relative_to(Path(__file__).resolve().parents[2]/'note10/private') and not out.exists(),'fresh private composite-policy receipt');result=run_cases();out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf8',newline='\n')
if __name__=='__main__':main()
