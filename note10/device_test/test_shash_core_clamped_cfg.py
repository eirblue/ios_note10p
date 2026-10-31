"""Only new observed opcodes/clamped-CFG fixtures. No old test module or object replay."""
import argparse,copy,json,struct
from pathlib import Path
from pre_pm_archive_contract import require
from shash_core_instructions import decode,compare_provenance,compare_nzcv,csel32_gt,umaddl_value,trace
from shash_core_clamped_cfg import clamped_registration_cfg,registration_cfg_dispatch
CASES=('csel-fields','cmpr64-fields','umaddl-fields','clamp-negative-one','clamp-zero','clamp-intmin','clamp-one','clamp-intmax','clamp-W-zero-extension','compare-equal-NZCV','compare-unequal-NZCV','umaddl-unsigned-W','umaddl-modulo64','unknown-select-kills-destination','flag-writer-invalidates','call-invalidates','unknown-word-invalidates','nonflag-MOV-gap-preserves','unknown-flags-are-not-false','CSEL64-reject','CSINC-reject','CSINV-reject','CSNEG-reject','reserved-CSEL-reject','wrong-CSEL-condition-reject','CMP32-reject','shifted-CMP-reject','extended-CMP-reject','non-XZR-CMP-reject','SMADDL-reject','UMSUBL-reject','MADD64-reject','observed-connected-CFG-positive','new-dispatch-path-positive','CSEL-wrong-source-reject','CSEL-wrong-zero-source-reject','CSEL-wrong-destination-reject','wrong-clamp-flags-origin-reject','intervening-NZCV-writer-reject','wrong-loop-index-compare-reject','wrong-loop-count-compare-reject','wrong-equality-exit-reject','forward-index-before-call-reject','forward-stride-reject','rollback-stride-register-reject','wrong-DWARF-stride-reject','forward-backedge-reject','failure-to-success-reject','inverted-call-result-reject','missing-signed-guard-reject','wrong-signed-guard-reject','error-through-success-zero-reject','rollback-address-before-guard-reject','rollback-decrement-register-reject','umaddl-base-register-reject','umaddl-index-register-reject','umaddl-stride-register-reject','rollback-backedge-reject','wrong-error-save-source-reject','wrong-common-result-reject','wrong-original-STR-slot-reject','wrong-original-LDR-slot-reject','wrong-original-STR-width-reject','X23-save-after-clamp-reject','wrong-pair-mode-reject','missing-original-restore-reject','restore-before-result-reject','unbalanced-SP-reject','extra-call-edge-reject','extra-function-word-reject','distinct-entry-X23-frame-provenance','rollback-zero-signed-guard-arithmetic','rollback-positive-signed-guard-arithmetic','stale-loop-NZCV-reject','stale-rollback-NZCV-reject','UMADDL-zero-register-is-not-SP')
# Exact observed function words, copied as immutable test literals; never executed.
WORDS=(0xa9bc7bfd,0xf9000bf7,0x910003fd,0xa90257f6,0xa9034ff4,0x7100003f,0xaa0003f3,0xaa1f03f6,0x1a9fc037,0xaa0003f5,0xeb1602ff,0x540000e0,0xaa1503e0,0x94000000,0x35000160,0x910006d6,0x910c02b5,0x17fffff9,0x2a1f03f4,0x2a1403e0,0xf9400bf7,0xa9434ff4,0xa94257f6,0xa8c47bfd,0xd65f03c0,0x2a0003f4,0x52806015,0x710006d6,0x54fffeeb,0x9bb54ec0,0x94000000,0x17fffffc)

def fixture():
 raw=b''.join(struct.pack('<I',word) for word in WORDS);fn={'name':'crypto_register_shashes','info':18,'section':1,'value':0,'size':128};register={'name':'crypto_register_shash','info':18,'section':2,'value':0,'size':4};unregister={'name':'crypto_unregister_shash','info':18,'section':2,'value':4,'size':4}
 return {'sections':[{'bytes':b''},{'bytes':raw},{'bytes':bytes(8)}],'symbols':[fn,register,unregister],'relocations':[{'section':1,'offset':52,'type':283,'symbol':register,'addend':0},{'section':1,'offset':120,'type':283,'symbol':unregister,'addend':0}]},fn

def replace(obj,pc,word):
 raw=bytearray(obj['sections'][1]['bytes']);struct.pack_into('<I',raw,pc,word);obj['sections'][1]['bytes']=bytes(raw)

def run_cases():
 completed=[]
 def check(index,fn,reject=False):
  require(index==len(completed),'exact new opcode/CFG fixture inventory')
  try:fn()
  except (ValueError,KeyError):
   if not reject:raise
  else:require(not reject,'invalid new clamped fixture accepted: '+CASES[index])
  completed.append(CASES[index])
 def equal(actual,expected):require(actual==expected,'independent new fixture expectation')
 check(0,lambda:equal(decode(0x1a9fc037),{'op':'csel32gt','rd':23,'rn':1,'rm':31,'condition':12,'width':32}))
 check(1,lambda:equal(decode(0xeb1602ff),{'op':'cmpreg64','rn':23,'rm':22,'width':64,'flags':True}))
 check(2,lambda:equal(decode(0x9bb54ec0),{'op':'umaddl','rd':0,'rn':22,'rm':21,'ra':19,'input_width':32,'accumulator_width':64,'width':64}))
 for index,value,expected in ((3,-1,0),(4,0,0),(5,-2147483648,0),(6,1,1),(7,2147483647,2147483647),(8,0x100000001,1)):
  check(index,lambda:equal(csel32_gt(value,0,compare_provenance(value,0,32,20)),expected))
 check(9,lambda:equal(compare_nzcv(7,7,64),{'N':False,'Z':True,'C':True,'V':False}))
 check(10,lambda:equal(compare_nzcv(3,7,64),{'N':True,'Z':False,'C':False,'V':False}))
 check(11,lambda:equal(umaddl_value(-1,-1,0),0xfffffffe00000001))
 check(12,lambda:equal(umaddl_value(1,1,0xffffffffffffffff),0))
 # STR X23,[X2] exposes the new destination state; fixture is static word analysis only.
 def destination(words):
  rows=trace({i*4:word for i,word in enumerate(words)},{},{})
  return next(row.get('value') for row in rows if row['decoded']['op']=='store')
 select=0x1a9fc037;store=0xf9000057;ret=0xd65f03c0;initial=0x528000f7
 check(13,lambda:equal(destination((initial,select,store,ret)),None))
 check(14,lambda:equal(destination((initial,0x7100003f,0x31000463,select,store,ret)),None))
 def call_flags():
  words=(initial,0x7100003f,0x94000000,select,store,ret);rows=trace({i*4:word for i,word in enumerate(words)},{},{})
  equal(rows[3]['NZCV_source'],None);equal(rows[4].get('value'),None)
 check(15,call_flags)
 check(16,lambda:equal(destination((initial,0x7100003f,0xffffffff,select,store,ret)),None))
 check(17,lambda:equal(destination((0x7100003f,0xaa0003f3,0xaa1f03f6,select,store,ret)),('zero_extended_signed_positive_clamp32',('arg',1))))
 check(18,lambda:equal(csel32_gt(7,0,None),None))
 for index,word in ((19,0x9a9fc037),(20,0x1a9fc437),(21,0x5a9fc037),(22,0x5a9fc437),(23,0x3a9fc037),(24,0x1a9fd037),(25,0x6b1602ff),(26,0xeb1606ff),(27,0xeb3602ff),(28,0xeb1602e0),(29,0x9b354ec0),(30,0x9bb5cec0),(31,0x9b154ec0)):
  check(index,lambda:equal(decode(word)['op'],'unknown'))
 obj,fn=fixture();check(32,lambda:clamped_registration_cfg(obj,fn,768));check(33,lambda:registration_cfg_dispatch(obj,fn,768))
 def mutation(index,pc,word):
  changed,owned=fixture();replace(changed,pc,word);check(index,lambda:clamped_registration_cfg(changed,owned,768),True)
 for index,pc,word in ((34,32,0x1a9fc057),(35,32,0x1a81c037),(36,32,0x1a9fc036),(37,20,0x7100001f),(38,28,0x310006d6),(39,40,0xeb1502ff),(40,40,0xeb1602df),(41,44,0x540000e1),(42,48,0x910006d6),(43,64,0x910802b5),(44,104,0x52804015)):
  mutation(index,pc,word)
 check(45,lambda:clamped_registration_cfg(obj,fn,512),True)
 for index,pc,word in ((46,68,0x17fffffa),(47,56,0x35000080),(48,56,0x34000160),(49,112,0xd503201f),(50,112,0x54fffee9),(51,112,0x54fffecb),(52,112,0x9bb54ec0),(53,108,0x710006b5),(54,116,0x9bb54ac0),(55,116,0x9bb54ea0),(56,116,0x9bb64ec0),(57,124,0x17fffffd),(58,100,0x2a0103f4),(59,76,0x2a1303e0),(60,4,0xf9000ff7),(61,80,0xf9400ff7),(62,4,0xb90013f7),(63,4,0x1a9fc037),(64,12,0xa98257f6),(65,80,0xd503201f),(66,76,0xf9400bf7),(67,92,0xa8c37bfd)):
  mutation(index,pc,word)
 changed,owned=fixture();changed['relocations'].append(dict(changed['relocations'][0]));check(68,lambda:clamped_registration_cfg(changed,owned,768),True)
 changed,owned=fixture();changed['sections'][1]['bytes']+=struct.pack('<I',0xd503201f);owned['size']+=4;check(69,lambda:clamped_registration_cfg(changed,owned,768),True)
 def provenance():
  proof=clamped_registration_cfg(obj,fn,768);original=next(row for row in proof['frame_original_entry_saves'] if row['register']==23);restored=next(row for row in proof['error_return']['restored_entry_values'] if row['register']==23)
  equal(original['entry_identity'],('entry_X',23));equal(restored['identity'],('entry_X',23));require(original['slot_from_entry_SP']==restored['slot_from_entry_SP']==-48,'original X23 exact save/load slot')
 check(70,provenance)
 def rollback_guard(value,expected):
  flags=compare_nzcv(value,1,32);equal(flags['N']!=flags['V'],expected)
 check(71,lambda:rollback_guard(0,True));check(72,lambda:rollback_guard(1,False))
 mutation(73,40,0xd503201f);mutation(74,108,0x510006d6)
 check(75,lambda:equal(destination((0xd28000b3,0x52800135,0x9bb54fe0,0xf9000040,ret)),5))
 return {'passed':True,'cases':completed,'case_count':len(completed),'synthetic_only':True,'actual_failed_object_checker_model_or_compiler_replayed':False,'old49_28_14_replayed':False,'scope':'only three new word forms, fresh flags, width semantics and observed clamped CFG/frame guard','runtime_or_hardware_proven':False}

def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();out=a.output.absolute();require(out.is_relative_to(Path(__file__).resolve().parents[2]/'note10/private') and not out.exists(),'fresh private new-clamped receipt');result=run_cases();out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf8',newline='\n')
if __name__=='__main__':main()
