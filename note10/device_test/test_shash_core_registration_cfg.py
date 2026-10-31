"""Only new connected registration-CFG fixtures, encoded words, no target execution."""
import argparse,copy,json,struct
from pathlib import Path
from pre_pm_archive_contract import require
from shash_core_registration_cfg import registration_cfg
CASES=('connected-register-rollback-positive','callee-saved-alias-positive','compare-error-branch-positive','disconnected-forward-stride-reject','wrong-forward-pointer-reject','disconnected-reverse-stride-reject','forward-backedge-skips-argument-reject','rollback-backedge-skips-reverse-reject','remaining-update-wrong-register-reject','registered-increment-wrong-register-reject','rollback-guard-wrong-counter-reject','failure-skips-rollback-reject','success-enters-rollback-reject','inverted-error-test-reject','wrong-error-save-source-reject','wrong-error-return-register-reject','missing-zero-rollback-guard-reject','unsigned-entry-count-reject','wrong-unregister-target-reject','wrong-count-input-reject','wrong-pointer-input-reject','nonzero-registered-initializer-reject','error-counter-alias-reject','result-clobbering-epilogue-reject','unsaved-return-address-reject','nonzero-success-return-reject','caller-clobbered-error-register-reject','extra-disconnected-word-reject')

def mov(rd,rn,width=64):return (0xaa0003e0 if width==64 else 0x2a0003e0)|(rn<<16)|rd

def arithmetic(rd,rn,imm,width=64,subtract=False,flags=False):return (0x91000000 if width==64 else 0x11000000)|(0x40000000 if subtract else 0)|(0x20000000 if flags else 0)|(imm<<10)|(rn<<5)|rd

def pair(rt,rt2,offset,load=False,mode=2):
 # Independent A64 fixed instruction encoding literals, not decoder output.
 base=0xa9000000|(0x400000 if load else 0)|((mode&1)<<23)
 if mode==1:base=0xa8800000|(0x400000 if load else 0)
 return base|(((offset//8)&127)<<15)|(rt2<<10)|(31<<5)|rt

def fixture(roles=(19,20,21,22),compare_error=False):
 p,r,i,e=roles;items=[];labels={}
 def label(name):labels[name]=len(items)*4
 def emit(name,word):labels[name]=len(items)*4;items.append(word)
 emit('save-lr',pair(29,30,-64,mode=3));emit('save-pr',pair(p,r,16));emit('save-ie',pair(i,e,32));emit('frame-pointer',arithmetic(29,31,0))
 emit('pointer-init',mov(p,0));emit('count-init',mov(r,1,32));emit('index-init',mov(i,31,32));emit('entry-compare',arithmetic(31,r,0,32,True,True));emit('entry-branch',('cond',13,'success'))
 label('forward');emit('register-argument',mov(0,p));emit('register-call',0x94000000)
 if compare_error:emit('error-compare',arithmetic(31,0,0,32,True,True));emit('error-branch',('cond',1,'failure'))
 else:emit('error-branch',('cb',0,True,'failure'))
 emit('forward-stride',arithmetic(p,p,768));emit('registered-increment',arithmetic(i,i,1,32));emit('remaining-decrement',arithmetic(r,r,1,32,True,True));emit('forward-backedge',('cond',1,'forward'))
 label('success');emit('success-result',mov(0,31,32));label('epilogue');emit('restore-pr',pair(p,r,16,True));emit('restore-ie',pair(i,e,32,True));emit('restore-lr',pair(29,30,64,True,1));emit('return',0xd65f03c0)
 label('failure');emit('error-save',mov(e,0,32));emit('rollback-zero-guard',('cb',i,False,'error-return'));label('rollback');emit('reverse-stride',arithmetic(p,p,768,subtract=True));emit('unregister-argument',mov(0,p));emit('unregister-call',0x94000000);emit('registered-decrement',arithmetic(i,i,1,32,True,True));emit('rollback-backedge',('cond',1,'rollback'))
 label('error-return');emit('error-result',mov(0,e,32));emit('error-epilogue',('b','epilogue'))
 words=[]
 for index,item in enumerate(items):
  pc=index*4
  if isinstance(item,tuple):
   if item[0]=='cond':word=0x54000000|((((labels[item[2]]-pc)//4)&0x7ffff)<<5)|item[1]
   elif item[0]=='cb':word=0x34000000|(0x1000000 if item[2] else 0)|((((labels[item[3]]-pc)//4)&0x7ffff)<<5)|item[1]
   else:word=0x14000000|(((labels[item[1]]-pc)//4)&0x3ffffff)
  else:word=item
  words.append(word)
 code=b''.join(struct.pack('<I',word) for word in words);fn={'name':'crypto_register_shashes','info':18,'section':1,'value':0,'size':len(code)};register={'name':'crypto_register_shash','info':18,'section':2,'value':0,'size':4};unregister={'name':'crypto_unregister_shash','info':18,'section':2,'value':4,'size':4}
 obj={'sections':[{'bytes':b''},{'bytes':code},{'bytes':bytes(8)}],'symbols':[fn,register,unregister],'relocations':[{'section':1,'offset':labels['register-call'],'type':283,'addend':0,'symbol':register},{'section':1,'offset':labels['unregister-call'],'type':283,'addend':0,'symbol':unregister}]}
 return obj,fn,labels

def replace(obj,labels,label,word):
 raw=bytearray(obj['sections'][1]['bytes']);struct.pack_into('<I',raw,labels[label],word);obj['sections'][1]['bytes']=bytes(raw)

def branch(pc,target,condition):return 0x54000000|((((target-pc)//4)&0x7ffff)<<5)|condition

def run_cases():
 completed=[]
 def check(index,obj,fn,reject=False):
  require(index==len(completed),'exact new CFG fixture inventory')
  try:proof=registration_cfg(obj,fn,768)
  except (ValueError,KeyError):
   if not reject:raise
  else:require(not reject and proof['connected_finite_CFG_verified'] is True,'invalid connected-CFG fixture accepted')
  completed.append(CASES[index])
 for index,options in enumerate(({},dict(roles=(23,24,25,26)),dict(compare_error=True))):
  obj,fn,labels=fixture(**options);check(index,obj,fn)
 def mutation(index,change):
  obj,fn,labels=fixture();change(obj,fn,labels);check(index,obj,fn,True)
 def disconnected(obj,fn,labels,which):
  old=struct.unpack_from('<I',obj['sections'][1]['bytes'],labels[which])[0];replace(obj,labels,which,0xd503201f);obj['sections'][1]['bytes']+=struct.pack('<I',old);fn['size']+=4
 mutation(3,lambda o,f,l:disconnected(o,f,l,'forward-stride'))
 mutation(4,lambda o,f,l:replace(o,l,'forward-stride',arithmetic(23,19,768)))
 mutation(5,lambda o,f,l:disconnected(o,f,l,'reverse-stride'))
 mutation(6,lambda o,f,l:replace(o,l,'forward-backedge',branch(l['forward-backedge'],l['register-call'],1)))
 mutation(7,lambda o,f,l:replace(o,l,'rollback-backedge',branch(l['rollback-backedge'],l['unregister-argument'],1)))
 mutation(8,lambda o,f,l:replace(o,l,'remaining-decrement',arithmetic(21,21,1,32,True,True)))
 mutation(9,lambda o,f,l:replace(o,l,'registered-increment',arithmetic(20,20,1,32)))
 mutation(10,lambda o,f,l:replace(o,l,'rollback-zero-guard',0x34000000|((((l['error-return']-l['rollback-zero-guard'])//4)&0x7ffff)<<5)|20))
 mutation(11,lambda o,f,l:replace(o,l,'error-branch',0x35000000|((((l['error-return']-l['error-branch'])//4)&0x7ffff)<<5)))
 mutation(12,lambda o,f,l:replace(o,l,'entry-branch',branch(l['entry-branch'],l['failure'],13)))
 mutation(13,lambda o,f,l:replace(o,l,'error-branch',0x34000000|((((l['failure']-l['error-branch'])//4)&0x7ffff)<<5)))
 mutation(14,lambda o,f,l:replace(o,l,'error-save',mov(22,1,32)))
 mutation(15,lambda o,f,l:replace(o,l,'error-result',mov(0,20,32)))
 mutation(16,lambda o,f,l:replace(o,l,'rollback-zero-guard',0xd503201f))
 mutation(17,lambda o,f,l:replace(o,l,'entry-branch',branch(l['entry-branch'],l['success'],9)))
 mutation(18,lambda o,f,l:o['relocations'][1].update(symbol=o['symbols'][1]))
 mutation(19,lambda o,f,l:replace(o,l,'count-init',mov(20,2,32)))
 mutation(20,lambda o,f,l:replace(o,l,'pointer-init',mov(19,1)))
 mutation(21,lambda o,f,l:replace(o,l,'index-init',0x52800035))
 mutation(22,lambda o,f,l:replace(o,l,'error-save',mov(21,0,32)))
 mutation(23,lambda o,f,l:replace(o,l,'restore-pr',pair(0,20,16,True)))
 mutation(24,lambda o,f,l:replace(o,l,'save-lr',pair(29,28,-64,mode=3)))
 mutation(25,lambda o,f,l:replace(o,l,'success-result',0x52800020))
 mutation(26,lambda o,f,l:replace(o,l,'error-save',mov(9,0,32)))
 def extra(o,f,l):o['sections'][1]['bytes']+=struct.pack('<I',0xd503201f);f['size']+=4
 mutation(27,extra)
 return {'passed':True,'cases':completed,'case_count':len(completed),'synthetic_only':True,'actual_target_compiler_or_old_suites_executed':False,'scope':'new word-connected CFG guard only; synthetic encoded functions never executed'}

def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();out=a.output.absolute();require(out.is_relative_to(Path(__file__).resolve().parents[2]/'note10/private') and not out.exists(),'fresh private new-CFG receipt');result=run_cases();out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf8',newline='\n')
if __name__=='__main__':main()
