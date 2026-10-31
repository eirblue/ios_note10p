"""New pure actual-object binding policy mutations; no kernel/models executed."""
import copy
from pre_pm_trial_object import owner,branch_target,decoded,local_target
from prepare_pre_pm_trial import require
CASES=('function-exact','function-interior-reject','function-ambiguous-reject','named-call','section-addend-call','undefined-addend-reject','wrong-reloc-reject','resolved-call','instruction-bytes-reject','conditional-target')
def run_cases():
 obj={'sections':[{'index':0,'name':'','bytes':b''},{'index':1,'name':'.text','bytes':bytes.fromhex('00000094')+b'\0'*12}],
 'symbols':[{'name':'callee','info':2,'section':1,'value':8,'size':4}],
 'relocations':[]};rows=[]
 def check(name,fn,reject=False):
  try:value=fn()
  except ValueError:require(reject,'unexpected rejection: '+name)
  else:require(not reject,'invalid accepted: '+name)
  rows.append({'name':name,'passed':True})
 check('function-exact',lambda:require(owner(obj,1,8)=='callee','exact target'))
 check('function-interior-reject',lambda:owner(obj,1,9),True)
 dup=copy.deepcopy(obj);dup['symbols']*=2;check('function-ambiguous-reject',lambda:owner(dup,1,8),True)
 row={'offset':0,'word':0x94000000,'mnemonic':'bl','operands':'0'}
 named=copy.deepcopy(obj);named['relocations']=[{'section':1,'offset':0,'type':283,'addend':0,'symbol':{'name':'real_kernel_api','info':18,'section':0,'value':0}}]
 check('named-call',lambda:require(branch_target(named,1,row)=='real_kernel_api','actual external named target'))
 section=copy.deepcopy(named);section['relocations'][0]['symbol']={'name':'','info':3,'section':1,'value':0};section['symbols']=[{'name':'provider','info':2,'section':1,'value':8,'size':4}];section['relocations'][0]['addend']=8
 check('section-addend-call',lambda:require(branch_target(section,1,row)=='provider','exact section symbol+addend'))
 bad=copy.deepcopy(named);bad['relocations'][0]['addend']=4;check('undefined-addend-reject',lambda:branch_target(bad,1,row),True)
 bad=copy.deepcopy(named);bad['relocations'][0]['type']=275;check('wrong-reloc-reject',lambda:branch_target(bad,1,row),True)
 resolved=copy.deepcopy(obj)
 check('resolved-call',lambda:require(branch_target(resolved,1,dict(row,word=0x94000002))=='callee','decoded immediate exact target'))
 check('instruction-bytes-reject',lambda:decoded('Disassembly of section .text:\n0: d65f03c0 ret\n',obj),True)
 check('conditional-target',lambda:require(local_target({'offset':8,'word':0x35000040,'mnemonic':'cbnz'})==16,'signed conditional immediate'))
 return rows
