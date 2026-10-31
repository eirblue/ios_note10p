"""Only changed full-prefix lowering fixtures and optional retained-object static reread."""
import argparse,copy,hashlib,json,tarfile
from pathlib import Path
from prepare_pre_pm_trial import ROOT,require
from pre_pm_trial_lowering import restore_lowering,bcmp_source_proof,AFFECTED,advance_obligation
CASES=('bcmp-positive','memcmp-positive','restore-short','compare-short','compare-wrong-buffer','compare-swapped-buffer','return-equal-condition','return-discarded','aggregate-masked','missing-barrier','early-postcheck-exit','unknown-comparator','wrong-trial-backup-capacity','truncated-window-pointer','bcmp-provider-positive','bcmp-provider-wrong-span','bcmp-provider-wrong-return','completion-null-event','completion-unmatched-event','missing-obligation-null-event','word-short-restore-shown-full','word-short-compare-shown-full','word-other-pointer-shown-window','word-eq-condition-shown-ne','word-aggregate-drop-shown-full','word-branch-other-register-shown-aggregate','word-w-truncation-shown-x','word-stack-slot-shown-backup')
NEW_CASES=CASES[-8:]
HEADER=b'extern int bcmp(const void *,const void *,__kernel_size_t);'
PROVIDER=b'int bcmp(const void *a, const void *b, size_t len) { return memcmp(a, b, len); } EXPORT_SYMBOL(bcmp);'
def fixture():
 operations=[('mov','x6, x21'),('mov','w7, #268435456'),('ldr','x23, [sp, #40]'),('mov','w10, #36372480'),('stp','x23, x10, [sp]'),('bl','trial'),
 ('mov','x0, x21'),('mov','x1, x23'),('mov','w2, #36372480'),('bl','restore'),('dsb','sy'),
 ('mov','x1, x23'),('bl','hash1'),('mov','w25, w0'),('mov','x1, x21'),('bl','hash2'),('orr','w22, w0, w25'),
 ('mov','x0, x21'),('mov','x1, x23'),('mov','w2, #36372480'),('bl','compare'),('cmp','w0, #0'),('cset','w23, ne'),
 ('mov','w1, #165'),('bl','guard1'),('mov','w21, w0'),('mov','w1, #90'),('bl','guard2'),
 ('orr','w8, w22, w21'),('orr','w8, w8, w23'),('orr','w8, w8, w0'),('cbnz','w8, #0')]
 targets={'trial':'n10_rt_trial','restore':'memcpy','hash1':'n10_pre_pm_hash','hash2':'n10_pre_pm_hash','compare':'bcmp','guard1':'n10_pre_pm_guard','guard2':'n10_pre_pm_guard'}
 # Independent encoding literals lifted from the observed instruction forms;
 # no decoder/encoder constructs the positive oracle.
 words=(0xaa1503e6,0x52a20007,0xf94017f7,0x52a0456a,0xa9002bf7,0x94000000,
 0xaa1503e0,0xaa1703e1,0x52a04562,0x94000000,0xd5033f9f,0xaa1703e1,0x94000000,
 0x2a0003f9,0xaa1503e1,0x94000000,0x2a190016,0xaa1503e0,0xaa1703e1,0x52a04562,
 0x94000000,0x7100001f,0x1a9f07f7,0x528014a1,0x94000000,0x2a0003f5,0x52800b41,
 0x94000000,0x2a1502c8,0x2a170108,0x2a000108,0x35000008)
 require(len(words)==len(operations),'independent literal fixture inventory')
 code={i*4:{'offset':i*4,'mnemonic':m,'operands':o,'word':words[i]} for i,(m,o) in enumerate(operations)};calls={off:targets[r['operands']] for off,r in code.items() if r['mnemonic']=='bl'}
 for off,row in code.items():
  if row['mnemonic']=='bl':row['operands']=f'0x{off:x}'
 code[124]['operands']='w8, 0x7c'
 return code,calls,20

def run_cases():
 result=[]
 for name in NEW_CASES:
  if name in ('completion-null-event','completion-unmatched-event','missing-obligation-null-event'):
   obligations=('restore','barrier','hash','hash','equality','guard','guard')
   state,event=(7,None) if name=='completion-null-event' else (7,'irrelevant') if name=='completion-unmatched-event' else (6,None)
   require(advance_obligation(state,event,obligations)==state,'complete state saturates; missing obligation never supplied by null')
   result.append({'name':name,'passed':True});continue
  code,calls,trial=fixture()
  if name=='memcmp-positive':calls[80]='memcmp'
  if name=='restore-short':code[32].update(operands='w2, #64',word=0x52800802)
  if name=='compare-short':code[76].update(operands='w2, #64',word=0x52800802)
  if name=='compare-wrong-buffer':code[68].update(operands='x0, x20',word=0xaa1403e0)
  if name=='compare-swapped-buffer':code[68].update(operands='x0, x23',word=0xaa1703e0);code[72].update(operands='x1, x21',word=0xaa1503e1)
  if name=='return-equal-condition':code[88].update(operands='w23, eq',word=0x1a9f17f7)
  if name=='return-discarded':code[116].update(operands='w8, w8, wzr',word=0x2a1f0108)
  if name=='aggregate-masked':code[116].update(mnemonic='and',operands='w8, w8, #1',word=0x12000108)
  if name=='missing-barrier':code[40].update(mnemonic='nop',operands='',word=0xd503201f)
  if name=='early-postcheck-exit':code[92].update(mnemonic='cbnz',operands='w0, 0x5c',word=0x35000000)
  if name=='unknown-comparator':calls[80]='strcmp'
  if name=='truncated-window-pointer':code[0].update(operands='w6, w21',word=0x2a1503e6)
  if name=='wrong-trial-backup-capacity':code[12].update(operands='w10, #64',word=0x5280080a)
  # Negative metadata keeps machine words fixed while claiming favorable operands.
  if name=='word-short-restore-shown-full':code[32]['word']=0x52800802
  if name=='word-short-compare-shown-full':code[76]['word']=0x52800802
  if name=='word-other-pointer-shown-window':code[68]['word']=0xaa1403e0
  if name=='word-eq-condition-shown-ne':code[88]['word']=0x1a9f17f7
  if name=='word-aggregate-drop-shown-full':code[116]['word']=0x2a1f0108
  if name=='word-branch-other-register-shown-aggregate':code[124]['word']=0x35000009
  if name=='word-w-truncation-shown-x':code[0]['word']=0x2a1503e6
  if name=='word-stack-slot-shown-backup':code[16]['word']=0xa9012bf7
  provider=PROVIDER
  if name=='bcmp-provider-wrong-span':provider=provider.replace(b'len);',b'len - 1);')
  if name=='bcmp-provider-wrong-return':provider=provider.replace(b'return memcmp(a, b, len);',b'return 0;')
  positive=name in ('bcmp-positive','memcmp-positive','bcmp-provider-positive')
  try:
   proof=bcmp_source_proof(HEADER,provider) if name.startswith('bcmp-provider-') else restore_lowering(code,calls,trial)
  except ValueError:require(not positive,'valid exact observed lowering rejected: '+name)
  else:
   require(positive,'invalid lowering/provider accepted: '+name)
   if not name.startswith('bcmp-provider-'):require(proof['compared_bytes']==AFFECTED and proof['restore_and_compare_arguments_equal_trial_window_backup'],'full-span dataflow')
  result.append({'name':name,'passed':True})
 return result

def actual_decoder_check(evidence):
 # Only the newly added word/text validator is exercised on retained real rows.
 # No old wrapper-unwind, argument-flow, ABI, provider or model proof is rerun.
 from kernel_trial_object import parse_elf
 from relocation_trial_instructions import ROW
 from pre_pm_trial_decode import validate_word
 require(evidence.resolve().is_relative_to(ROOT/'note10/private/cloud-runs'),'retained private CI evidence only')
 raw=(evidence/'kbuild/arch/arm64/mm/init.o').read_bytes();disassembly=(evidence/'disassembly.log').read_bytes()
 object_sha=hashlib.sha256(raw).hexdigest();text_sha=hashlib.sha256(disassembly).hexdigest()
 require(object_sha=='9c05e7257834fe67faf8ea83ad227c44f4dacfde7344740518cb953eb1664a42' and text_sha=='23ede0af2db3f56f2f5c8d6b48295cf8237b506c4d4148c139d9040f441fbe44','exact authenticated retained failed-object rows')
 obj=parse_elf(raw,1);section=next(s for s in obj['sections'] if s['name']=='.text.n10_pre_pm_trial');selected=False;checks=[]
 for line in disassembly.decode().splitlines():
  if line.startswith('Disassembly of section '):selected=line=='Disassembly of section .text.n10_pre_pm_trial:';continue
  if not selected:continue
  match=ROW.fullmatch(line)
  if not match:continue
  off=int(match[1],16)
  if not 0x4c8<=off<=0x58c:continue
  encoded=bytes.fromhex(match[2]);encoded=encoded[::-1] if len(match[2])==8 else encoded
  require(section['bytes'][off:off+4]==encoded,'retained row word matches exact object bytes')
  checks.append(validate_word({'offset':off,'word':int.from_bytes(encoded,'little'),'mnemonic':match[3],'operands':match[4]}))
 require([c['offset'] for c in checks]==list(range(0x4c8,0x590,4)),'complete original observed instruction block only')
 return {'object_sha256':object_sha,'disassembly_sha256':text_sha,'section':section['name'],'word_checks':checks,'new_decoder_positive_only':True,
 'old_wrapper_unwind_argument_ABI_provider_or_model_proofs_replayed':False,'original_CI_still_failed':True,'compiler_or_target_executed':False}

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True);ap.add_argument('--actual-evidence',type=Path);ap.add_argument('--new-only',action='store_true',help='Explicit new-only scope; default also selects only the eight new cases');a=ap.parse_args();out=a.output.resolve();require(not out.exists() and out.is_relative_to(ROOT/'note10/private'),'fresh private result');out.parent.mkdir(parents=True,exist_ok=True)
 rows=run_cases();actual=actual_decoder_check(a.actual_evidence.resolve()) if a.actual_evidence else None
 out.write_text(json.dumps({'passed':True,'fixture_only':actual is None,'synthetic_only':actual is None,'cases_fixture_only':True,'cases_synthetic_only':True,'cases':rows,'selected_case_inventory':list(NEW_CASES),'skipped_case_inventory':list(CASES[:-8]),'canonical_case_count':len(CASES),'prior_cases_rerun':False,'new_only':True,'passed_scope':'selected-new-eight-only','all_logical_cases_executed':False,'new_decoder_actual_rows':actual,'compiler_or_model_executed':False,'physical_memory_or_hardware_accessed':False},indent=2)+'\n',newline='\n')
if __name__=='__main__':main()
