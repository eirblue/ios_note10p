"""New STRW-pre/TST64/ORRW fixtures only; no old tests or native object replay."""
import argparse,copy,json
from pathlib import Path
from pre_pm_archive_contract import require
from shash_core_instructions import decode,trace,orr32_value,and64_flags,preindex_address,store_word32
from shash_core_object import descriptor_proof,dispatch_proof
CASES=('STRWpre-fields','TST-update-fields','TST-final-fields','TST-finup-digest-fields','ORRW-fields','STR-prestate-and-writeback','STR-W-source-truncation','STR-numeric-address-modulo64','STR-unknown-base','STR-unknown-data-known-writeback','STR-WZR-source','STR-symbolic-data-low32','STR-postindex-not-pre','STR-unscaled-remains-old-no-writeback','STR-unprivileged-reject','STR-load-reject','STR64pre-reject','STR-bytepre-reject','STR-vectorpre-reject','STR-SP-base-reject','STR-overlap-reject','TST-N-flags','TST-Z-flags','TST-unknown-replaces-stale','TST-preserves-GPRs','TST-XZR-source','TST32-reject','TST-shift-reject','TST-inverted-reject','TST-no-flags-reject','TST-non-XZR-reject','ORRW-numeric-low32-zext','ORRW-symbolic-pointer-bitnodes','ORRW-unknown-kills-destination','ORRW-preserves-source-pointers','ORRW-WZR-source','ORRW-prior-MOV-alias-priority','ORRW64-reject','ORRW-shift-reject','ORRW-inverted-reject','ORRW-other-opc-reject','ORRW-vector-reject','ORRW-and-STR-preserve-NZCV','typed-descriptor-preindex-positive','typed-descriptor-updated-call-base','typed-descriptor-wrong-slot-reject','typed-descriptor-wrong-value-reject','typed-descriptor-wrong-size-reject','typed-dispatch-after-ORR-TST-positive','typed-dispatch-saved-pointer-identity','typed-dispatch-wrong-slot-reject','typed-dispatch-wrong-descriptor-reject','typed-dispatch-W-pointer-clobber-reject')

def rows(words,calls=None):return trace({i*4:w for i,w in enumerate(words)},{},calls or {})
def only(events,op):return next(e for e in events if e['decoded']['op']==op)
def layout_fixture():
 # Synthetic consumer fields only, not ABI fallback or independently claimed kernel layout.
 fields={'crypto_tfm':(('__crt_alg',56,8),),'crypto_shash':(('base',128,8),('descsize',0,4)),'shash_alg':(('base',256,8),('descsize',64,4),('finup',24,8)),'shash_desc':(('tfm',0,8),)}
 return {'types':{typ:{'members':[{'name':name,'offset':offset,'type':{'kind':'pointer' if size==8 else 'base','byte_size':size}} for name,offset,size in members]} for typ,members in fields.items()}}

def descriptor_events(store=0xb8180c09):
 words=(0xf9401c08,0xb8540109,0xd1040101,store,0x94000000,0x2a1f03e0,0xd65f03c0)
 return rows(words,{16:'shash_set_needkey'})

def dispatch_events(slot=0xf85182e8,argument=0xaa1603e0,orr=0x2a150268):
 words=(0xaa0303f3,0xaa0103f5,0xaa0003f6,0xf9400009,0xf9405d37,0xb9402ef8,orr,0xea18011f,0x54000040,0x14000001,slot,argument,0xaa1503e1,0xaa1303e3,0xd63f0100,0xd65f03c0)
 return rows(words)

def run_cases():
 completed=[]
 def check(index,fn,reject=False):
  require(index==len(completed),'exact new observed-GPR case inventory')
  try:fn()
  except (ValueError,KeyError):
   if not reject:raise
  else:require(not reject,'invalid new observed-GPR case accepted: '+CASES[index])
  completed.append(CASES[index])
 def equal(actual,expected):require(actual==expected,'independent new fixture expectation')
 check(0,lambda:equal(decode(0xb8180c09),{'op':'store','rd':9,'rn':0,'offset':-128,'size':4,'mode':'preindex','writeback':True,'base_width':64}))
 for index,word,rn,rm in ((1,0xea1402ff,23,20),(2,0xea1302df,22,19),(3,0xea18011f,8,24)):
  check(index,lambda:equal(decode(word),{'op':'tst64','rn':rn,'rm':rm,'width':64,'flags':True}))
 check(4,lambda:equal(decode(0x2a150268),{'op':'orr32reg','rd':8,'rn':19,'rm':21,'width':32}))
 def prestate():
  events=descriptor_events();e=only(events,'store');equal(e['old_base'],('arg',0));equal(e['address'],('add',('arg',0),-128));equal(e['new_base'],e['address']);equal(e['value'],('load',('add',('load',('add',('arg',0),56),8),-192),4));require(e['writeback'] is True and e['size']==4 and e['address_width']==64 and e['address_modulo'] is True,'typed four-byte event and64-bit writeback')
 check(5,prestate)
 check(6,lambda:equal(store_word32(0x123456789abcdef0),0x9abcdef0))
 check(7,lambda:equal(preindex_address(0,-128),0xffffffffffffff80))
 def unknown_base():
  # A preceding call makes the caller-clobbered X2 base unknown.
  events=rows((0x94000000,0xb8180c49,0xd65f03c0));e=only(events,'store');require(e['old_base'] is None and e['new_base'] is None and e['address'] is None,'unknown base never becomes zero')
 check(8,unknown_base)
 def unknown_data():
  e=only(rows((0xb8180c09,0xd65f03c0)),'store');equal(e['new_base'],('add',('arg',0),-128));require(e['value'] is None,'unknown data retained with separately known writeback')
 check(9,unknown_data)
 check(10,lambda:equal(only(rows((0xb8180c1f,0xd65f03c0)),'store')['value'],0))
 check(11,lambda:equal(store_word32(('arg_pointer',7)),('low32',('arg_pointer',7))))
 check(12,lambda:equal(decode(0xb8180409)['op'],'unknown'))
 def old_unscaled():
  d=decode(0xb8180009);require(d['op']=='store' and d.get('mode') is None and d.get('writeback') is None,'unchanged old unscaled path, never pre-index')
 check(13,old_unscaled)
 for index,word in ((14,0xb8180809),(15,0xb8580c09),(16,0xf8180c09),(17,0x38180c09),(18,0xbc180c09),(19,0xb8180fe9),(20,0xb8180c00)):
  check(index,lambda:equal(decode(word)['op'],'unknown'))
 check(21,lambda:equal(and64_flags(0xffffffffffffffff,1<<63,12),{'operation':'and','left':0xffffffffffffffff,'right':1<<63,'width':64,'origin':12,'N':True,'Z':False,'C':False,'V':False}))
 check(22,lambda:equal(and64_flags(3,4,8)['Z'],True))
 def fresh_unknown_flags():
  events=rows((0x7100003f,0xea18011f,0xd65f03c0));flags=only(events,'tst64')['NZCV_result'];require(flags['operation']=='and' and flags['origin']==4 and flags['N'] is None and flags['Z'] is None and flags['C'] is False and flags['V'] is False,'fresh unknown AND flags, not old subtract')
 check(23,fresh_unknown_flags)
 def preserved():
  events=rows((0xaa0003f3,0xea1402ff,0xf9000053,0xd65f03c0));equal(only(events,'store')['value'],('arg',0))
 check(24,preserved)
 def zero_tst():
  flags=only(rows((0xea1f03ff,0xd65f03c0)),'tst64')['NZCV_result'];require(flags['Z'] is True and flags['N'] is False and flags['C'] is False and flags['V'] is False,'XZR input is zero, never SP')
 check(25,zero_tst)
 for index,word in ((26,0x6a1402ff),(27,0xea1406ff),(28,0xea3402ff),(29,0x8a1402ff),(30,0xea1402e0)):
  check(index,lambda:equal(decode(word)['op'],'unknown'))
 check(31,lambda:equal(orr32_value(0x1234567800000001,0xabcdef0000000002),3))
 check(32,lambda:equal(orr32_value(('arg',3),('arg',1)),('zero_extend32',('or32',('low32',('arg',3)),('low32',('arg',1))))))
 def kill_unknown():
  events=rows((0x528000e8,0x2a150268,0xf9000048,0xd65f03c0));require(only(events,'store')['value'] is None,'unknown new OR destination does not retain old constant')
 check(33,kill_unknown)
 def source_pointers():
  events=rows((0xaa0303f3,0xaa0103f5,0x2a150268,0xf9000053,0xf9000055,0xd65f03c0));values=[e['value'] for e in events if e['decoded']['op']=='store'];equal(values,[('arg',3),('arg',1)])
 check(34,source_pointers)
 check(35,lambda:equal(orr32_value(0,0x100000003),3))
 check(36,lambda:equal(decode(0x2a1503e8),{'op':'mov','rd':8,'rn':21,'width':32}))
 for index,word in ((37,0xaa150268),(38,0x2a150668),(39,0x2a350268),(40,0x4a150268),(41,0x4eb51e68)):
  check(index,lambda:equal(decode(word)['op'],'unknown'))
 def preserved_flags():
  events=rows((0x7100003f,0x2a150268,0xb8180c09,0x1a9fc037,0xf9000057,0xd65f03c0));select=only(events,'csel32gt');equal(select['NZCV_source']['origin'],0);equal([e['value'] for e in events if e['decoded']['op']=='store'][-1],('zero_extended_signed_positive_clamp32',('arg',1)))
 check(42,preserved_flags)
 layouts=layout_fixture();descriptor={'events':descriptor_events()};check(43,lambda:descriptor_proof(descriptor,layouts))
 def call_base():
  call=only(descriptor['events'],'bl');equal(call['arguments'][0],('add',('arg',0),-128));equal(call['arguments'][1],('add',('load',('add',('arg',0),56),8),-256))
 check(44,call_base)
 check(45,lambda:descriptor_proof({'events':descriptor_events(0xb8184c09)},layouts),True)
 check(46,lambda:descriptor_proof({'events':descriptor_events(0xb8180c08)},layouts),True)
 changed=copy.deepcopy(descriptor);only(changed['events'],'store')['size']=8;check(47,lambda:descriptor_proof(changed,layouts),True)
 dispatch={'events':dispatch_events()};check(48,lambda:dispatch_proof(dispatch,layouts,'finup'))
 def saved_arguments():
  call=only(dispatch['events'],'blr');equal(call['arguments'][0],('arg',0));equal(call['arguments'][1],('arg',1));equal(call['arguments'][3],('arg',3));flags=only(dispatch['events'],'tst64')['NZCV_result'];equal(flags['left'],('zero_extend32',('or32',('low32',('arg',3)),('low32',('arg',1)))))
 check(49,saved_arguments)
 check(50,lambda:dispatch_proof({'events':dispatch_events(slot=0xf85202e8)},layouts,'finup'),True)
 check(51,lambda:dispatch_proof({'events':dispatch_events(argument=0xaa1303e0)},layouts,'finup'),True)
 check(52,lambda:dispatch_proof({'events':dispatch_events(orr=0x2a150276)},layouts,'finup'),True)
 return {'passed':True,'cases':completed,'case_count':len(completed),'scope':'new three-family fields/semantics and directly affected typed store/dispatch dataflow only','synthetic_only':True,'old49_28_14_76_replayed':False,'actual_native_artifact_checker_compiler_model_or_target_replayed':False,'runtime_or_hardware_proven':False}

def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();out=a.output.absolute();require(out.is_relative_to(Path(__file__).resolve().parents[2]/'note10/private') and not out.exists(),'fresh private observed-GPR receipt');result=run_cases();out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf8',newline='\n')
if __name__=='__main__':main()
