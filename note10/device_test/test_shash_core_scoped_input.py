"""New scoped-input formatting/binding fixtures only. No old test modules."""
import argparse,copy,json
from pathlib import Path
from pre_pm_archive_contract import require
from shash_core_object import object_rows,scoped_input
from relocation_trial_kernel_profile import gpr_only
HEADER='Disassembly of section .text.crypto_register_shashes:'
FIRST_ROW='       0: fd 7b bc a9  \tstp\tx29, x30, [sp, #-64]!'
ACTUAL_DIAGNOSIS_SHA256='52ef4043b910eb687c440b5ec1956e7a2e8433d95228c49ad183a5b7e4487926'
CASES=('observed-header-first-row-positive','new-formatted-input-consumer-positive','missing-observed-header-reject','wrong-observed-section-reject','tampered-retained-header-reject','cross-section-row-reject','missing-scoped-row-reject','changed-encoded-bytes-reject','changed-retained-address-reject','duplicate-section-header-reject','unknown-object-section-reject','ambiguous-object-section-name-reject','function-extent-overflow-reject','neighbor-row-excluded-positive')

def fixture():
 # Only the exact first instruction bytes/line are copied from authenticated failure evidence.
 # This small structured object is synthetic fixture data and is never executed.
 sections=[{'index':0,'name':'','bytes':b''},{'index':1,'name':'.text.crypto_register_shashes','bytes':bytes.fromhex('fd7bbca9')},{'index':2,'name':'.text.other','bytes':bytes.fromhex('fd7bbca9')}]
 return {'sections':sections},{'name':'crypto_register_shashes','info':18,'section':1,'value':0,'size':4}

def run_cases():
 completed=[]
 def check(index,fn,reject=False):
  require(index==len(completed),'exact new scoped-input case inventory')
  try:fn()
  except (ValueError,KeyError):
   if not reject:raise
  else:require(not reject,'invalid scoped input accepted: '+CASES[index])
  completed.append(CASES[index])
 obj,fn=fixture();text=HEADER+'\n0000000000000000 <crypto_register_shashes>:\n'+FIRST_ROW;record=object_rows(obj,text)
 def positive():
  words,formatted=scoped_input(obj,fn,record);require(words=={0:0xa9bc7bfd} and formatted==HEADER+'\n'+FIRST_ROW,'exact observed header/row/word preservation')
 check(0,positive)
 def consumer():
  _,formatted=scoped_input(obj,fn,record);result=gpr_only(formatted);require(result['instruction_count']==1 and result['mnemonics']==['stp'],'unchanged consumer accepts newly formatted actual-context fixture')
 check(1,consumer)
 check(2,lambda:object_rows(obj,FIRST_ROW),True)
 check(3,lambda:scoped_input(obj,fn,object_rows(obj,'Disassembly of section .text.other:\n'+FIRST_ROW)),True)
 changed=copy.deepcopy(record);changed['observed_section_headers'][1]='Disassembly of section .text.other:';check(4,lambda:scoped_input(obj,fn,changed),True)
 cross=object_rows(obj,HEADER+'\nDisassembly of section .text.other:\n'+FIRST_ROW);check(5,lambda:scoped_input(obj,fn,cross),True)
 changed=copy.deepcopy(record);changed['instruction_rows'].clear();check(6,lambda:scoped_input(obj,fn,changed),True)
 check(7,lambda:object_rows(obj,HEADER+'\n'+FIRST_ROW.replace('fd 7b','fc 7b')),True)
 changed=copy.deepcopy(record);changed['instruction_rows'][1,0]=FIRST_ROW.replace('0:','4:');check(8,lambda:scoped_input(obj,fn,changed),True)
 check(9,lambda:object_rows(obj,text+'\n'+HEADER),True)
 check(10,lambda:object_rows(obj,'Disassembly of section .text.absent:\n'+FIRST_ROW),True)
 ambiguous=copy.deepcopy(obj);ambiguous['sections'][2]['name']=ambiguous['sections'][1]['name'];check(11,lambda:object_rows(ambiguous,text),True)
 extent=dict(fn,size=8);check(12,lambda:scoped_input(obj,extent,record),True)
 def neighbor():
  larger=copy.deepcopy(obj);larger['sections'][1]['bytes']+=bytes.fromhex('c0035fd6');rows=object_rows(larger,text+'\n       4: c0 03 5f d6  \tret');words,formatted=scoped_input(larger,fn,rows);require(words=={0:0xa9bc7bfd} and formatted==HEADER+'\n'+FIRST_ROW,'no neighboring function/section rows enter scope')
 check(13,neighbor)
 return {'passed':True,'cases':completed,'case_count':len(completed),'scope':'new scoped-input formatter and its direct unchanged consumer contract only','synthetic_structured_object':True,'first_header_and_row_origin_diagnosis_sha256':ACTUAL_DIAGNOSIS_SHA256,'actual_failed_checker_target_or_compiler_replayed':False,'old49_or28_replayed':False,'failed_CI_retroaccepted':False}

def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();out=a.output.absolute();require(out.is_relative_to(Path(__file__).resolve().parents[2]/'note10/private') and not out.exists(),'fresh private new scoped-input receipt');result=run_cases();out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf8',newline='\n')
if __name__=='__main__':main()
