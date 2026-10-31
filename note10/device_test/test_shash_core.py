"""New v64 static-evidence fixtures only, no Kbuild/model/API/old suite execution."""
import argparse,copy,json
from pathlib import Path
from pre_pm_archive_contract import require
from shash_core_instructions import decode,trace,add,load
from shash_core_oracle import crosscheck,MEMBERS
from shash_core_object import descriptor_proof,dispatch_proof,frame_rows,table_proof,registration_proof,preparation_proof
from build_shash_core import command_origin,FLAGS,SETTINGS,SOURCE_TOP,TARGET,SOURCE
CASES=('word-load','word-store','word-stride','word-conditional','callback-word-trace','unknown-word-invalidates','new-layout-positive','missing-layout-size-reject','explicit-align-reject','member-offset-reject','member-type-size-reject','member-align-reject','missing-member-reject','descriptor-transfer-positive','descriptor-destination-reject','descriptor-size-reject','typed-dispatch-positive','typed-dispatch-slot-reject','typed-dispatch-desc-argument-reject','static-and-dynamic-frames','missing-frame-field-reject','duplicate-frame-reject','new-command-positive','old-target-reject','outliner-conflict-reject','no-stack-evidence-reject','new-type-table-positive','table-scalar-reject','table-target-reject','table-extra-relocation-reject','registration-loop-positive','registration-stride-reject','registration-pointer-argument-reject','registration-error-branch-reject','preparation-positive','preparation-default-target-reject','preparation-each-size-compare-reject','preparation-error-code-reject','preparation-default-guard-reject','preparation-type-flags-reject')

def layout_fixture():
 # Synthetic offsets exclusively for mutation fixtures, never a kernel ABI fallback.
 values={'PAGE_SIZE':4096,'CRYPTO_ALG_TYPE_MASK':15,'CRYPTO_ALG_TYPE_SHASH':14,'CRYPTO_TFM_NEED_KEY':1};records=[]
 for typ,fields in MEMBERS.items():
  members=[];values[typ+'.size']=256;values[typ+'.alignment']=8
  for i,field in enumerate(fields):
   offset=i*8;size=4 if (typ,field) in (('crypto_shash','descsize'),('crypto_tfm','crt_flags')) or typ=='crypto_type' and field in ('type','maskclear','maskset','tfmsize') else 8
   prefix=typ+'.'+field;values.update({prefix+'.offset':offset,prefix+'.size':size,prefix+'.type_alignment':size,prefix+'.member_alignment':size});members.append({'name':field,'offset':offset,'member_alignment':size,'type':{'kind':'pointer' if size==8 else 'base','byte_size':size,'alignment':size}})
  records.append({'name':typ,'byte_size':256,'alignment':None,'members':members})
 # Additional old types come only from synthetic test data; production requires actual DWARF.
 extra={'shash_alg':(('base',64,8),('descsize',32,4),('update',8,8)),'shash_desc':(('tfm',0,8),),'crypto_alg':(('cra_type',0,8),('cra_flags',8,4))}
 layouts={'types':{r['name']:r for r in records}}
 for typ,fields in extra.items():layouts['types'][typ]={'name':typ,'byte_size':128,'alignment':None,'members':[{'name':n,'offset':o,'type':{'kind':'pointer' if size==8 else 'base','byte_size':size,'alignment':None}} for n,o,size in fields]}
 return values,records,layouts

def table_fixture(layouts,values):
 section=bytearray(256);symbols=[];rels=[];table={'name':'crypto_shash_type','info':1,'section':1,'value':0,'size':256};symbols.append(table)
 for i,(name,target) in enumerate((('extsize','crypto_alg_extsize'),('init_tfm','crypto_shash_init_tfm'),('report','crypto_shash_report'))):
  member=next(m for m in layouts['types']['crypto_type']['members'] if m['name']==name);symbol={'name':target,'info':18,'section':0 if i==0 else 2,'value':i*4,'size':4 if i else 0};symbols.append(symbol);rels.append({'section':1,'offset':member['offset'],'type':257,'addend':0,'symbol':symbol})
 for name,value in (('type',14),('maskclear',0xfffffff0),('maskset',15),('tfmsize',8)):
  offset=next(m['offset'] for m in layouts['types']['crypto_type']['members'] if m['name']==name);section[offset:offset+4]=value.to_bytes(4,'little')
 obj={'sections':[{}, {'flags':2,'bytes':bytes(section)},{'flags':6,'bytes':bytes(16)}],'symbols':symbols,'relocations':rels}
 return obj,{'values':values},{'CONFIG_PROC_FS':'n'}

def run_cases():
 completed=[]
 def check(index,fn,reject=False):
  require(CASES[index]==CASES[len(completed)],'new case ordering')
  try:fn()
  except (ValueError,KeyError):
   if not reject:raise
  else:require(not reject,'invalid new shash fixture accepted: '+CASES[index])
  completed.append(CASES[index])
 def equal(actual,expected):require(actual==expected,'independent expected fixture value')
 check(0,lambda:equal(decode(0xf9400808),{'op':'load','rd':8,'rn':0,'offset':16,'size':8}))
 check(1,lambda:equal(decode(0xb9000408),{'op':'store','rd':8,'rn':0,'offset':4,'size':4}))
 check(2,lambda:equal(decode(0x910c0294)['imm'],768))
 check(3,lambda:equal(decode(0x54000041),{'op':'cond','delta':8,'condition':1}))
 def callback_trace():
  result=trace({0:0xf9400408,4:0xd63f0100,8:0xd65f03c0},{},{})
  equal(result[1]['target'],('load',('add',('arg',0),8),8))
 check(4,callback_trace)
 def unknown_trace():
  result=trace({0:0xffffffff,4:0xf9400408,8:0xd63f0100,12:0xd65f03c0},{},{})
  equal(result[2]['target'],None)
 check(5,unknown_trace)
 values,records,layouts=layout_fixture();oracle={'values':values}
 check(6,lambda:crosscheck(records[0],oracle))
 for index,mutation in ((7,lambda r:r.update(byte_size=128)),(8,lambda r:r.update(alignment=16)),(9,lambda r:r['members'][0].update(offset=4)),(10,lambda r:r['members'][0]['type'].update(byte_size=8)),(11,lambda r:r['members'][0].update(member_alignment=8)),(12,lambda r:r['members'].pop())):
  row=copy.deepcopy(records[0]);mutation(row);check(index,lambda:crosscheck(row,oracle),True)
 desc={'events':[{'offset':4,'decoded':{'op':'store'},'address':add(('arg',0),-8),'value':load(load(('arg',0),8,8),-32,4),'size':4}]}
 check(13,lambda:descriptor_proof(desc,layouts))
 changed=copy.deepcopy(desc);changed['events'][0]['address']=('arg',0);check(14,lambda:descriptor_proof(changed,layouts),True)
 changed=copy.deepcopy(desc);changed['events'][0]['size']=8;check(15,lambda:descriptor_proof(changed,layouts),True)
 dispatch={'events':[{'offset':8,'decoded':{'op':'blr'},'target':load(load(load(('arg',0),0,8),16,8),-56,8),'arguments':[('arg',0)]}]}
 check(16,lambda:dispatch_proof(dispatch,layouts,'update'))
 changed=copy.deepcopy(dispatch);changed['events'][0]['target']=load(('arg',0),8,8);check(17,lambda:dispatch_proof(changed,layouts,'update'),True)
 changed=copy.deepcopy(dispatch);changed['events'][0]['arguments']=[('arg',1)];check(18,lambda:dispatch_proof(changed,layouts,'update'),True)
 check(19,lambda:equal(frame_rows('a.c:1:1:f\t0\tstatic\na.c:2:1:g\t32\tdynamic\n')['g']['fixed_frame_only'],False))
 check(20,lambda:frame_rows('a.c:1:1:f\tunknown\tstatic'),True)
 check(21,lambda:frame_rows('a.c:1:1:f\t0\tstatic\na.c:2:1:f\t8\tstatic'),True)
 config='\n'.join(k+'='+v if v!='n' else '# '+k+' is not set' for k,v in SETTINGS.items()).encode()
 args='clang-14 --target=aarch64-linux-gnu -D__KERNEL__ -mno-implicit-float -Oz '+FLAGS+' -DKBUILD_BASENAME=\'"shash"\' -DKBUILD_MODNAME=\'"crypto_hash"\' -c -o crypto/.tmp_shash.o /fixture/'+SOURCE_TOP+'/'+SOURCE
 command='cmd_'+TARGET+' := '+args+'\n';check(22,lambda:command_origin(command,config))
 check(23,lambda:command_origin(command.replace('cmd_crypto/shash.o','cmd_crypto/sha256_generic.o'),config),True)
 check(24,lambda:command_origin(command.replace(' -c ',' -mllvm -enable-machine-outliner=always -c '),config),True)
 check(25,lambda:command_origin(command.replace('-fstack-usage ',''),config),True)
 obj,compiled,cfg=table_fixture(layouts,values);check(26,lambda:table_proof(obj,layouts,compiled,cfg))
 changed=copy.deepcopy(obj);raw=bytearray(changed['sections'][1]['bytes']);raw[64:68]=(1).to_bytes(4,'little');changed['sections'][1]['bytes']=bytes(raw);check(27,lambda:table_proof(changed,layouts,compiled,cfg),True)
 changed=copy.deepcopy(obj);changed['relocations'][1]['addend']=4;check(28,lambda:table_proof(changed,layouts,compiled,cfg),True)
 changed=copy.deepcopy(obj);changed['relocations'].append(dict(changed['relocations'][0]));check(29,lambda:table_proof(changed,layouts,compiled,cfg),True)
 def event(off,op,**kw):return {'offset':off,'decoded':dict(op=op,**kw)}
 events=[event(0,'mov',rd=19,rn=0,width=64),event(4,'mov',rd=20,rn=1,width=32),event(8,'mov',rd=0,rn=19,width=64),event(12,'bl'),event(16,'cb',rn=0,nonzero=True,delta=16),event(20,'add',rd=19,rn=19,width=64,imm=128),event(24,'sub',rd=20,rn=20,width=32,imm=1),event(28,'cond',condition=13,delta=-20),event(32,'mov',rd=21,rn=0,width=32),event(36,'sub',rd=19,rn=19,width=64,imm=128),event(40,'mov',rd=0,rn=19,width=64),event(44,'bl'),event(48,'sub',rd=20,rn=20,width=32,imm=1),event(52,'cond',condition=10,delta=-16),event(56,'mov',rd=0,rn=21,width=32)]
 events[0]['source_value']=('arg',0);events[1]['source_value']=('arg',1);events[8]['source_value']=('return',12,'crypto_register_shash')
 reg={'crypto_register_shashes':{'events':events,'direct_calls':[{'offset':12,'target':'crypto_register_shash'},{'offset':44,'target':'crypto_unregister_shash'}]},'crypto_register_shash':{'direct_calls':[{'target':'shash_prepare_alg'},{'target':'crypto_register_alg'}]},'crypto_unregister_shash':{'direct_calls':[{'target':'crypto_unregister_alg'}]}}
 check(30,lambda:registration_proof(reg,layouts))
 changed=copy.deepcopy(reg);changed['crypto_register_shashes']['events'][5]['decoded']['imm']=64;check(31,lambda:registration_proof(changed,layouts),True)
 changed=copy.deepcopy(reg);changed['crypto_register_shashes']['events'][2]['decoded']['rn']=18;check(32,lambda:registration_proof(changed,layouts),True)
 changed=copy.deepcopy(reg);changed['crypto_register_shashes']['events'][4]['decoded']['nonzero']=False;check(33,lambda:registration_proof(changed,layouts),True)
 pl=copy.deepcopy(layouts)
 for name,offset,size in (('finup',24,8),('digest',40,8),('export',48,8),('import',56,8),('setkey',88,8),('digestsize',80,4),('statesize',84,4)):
  pl['types']['shash_alg']['members'].append({'name':name,'offset':offset,'type':{'kind':'pointer' if size==8 else 'base','byte_size':size}})
 po=copy.deepcopy(obj);po['sections'][2]['bytes']=bytes(256);pe=[]
 for i,(name,offset) in enumerate((('digestsize',80),('descsize',32),('statesize',84))):
  pe += [dict(event(i*12,'load'),address=add(('arg',0),offset)),dict(event(i*12+4,'sub',flags=True,rd=31,imm=512),source_value=load(('arg',0),offset,4)),event(i*12+8,'cond',condition=8,delta=500-(i*12+8))]
 defaults=(('finup',24,'shash_finup_unaligned'),('digest',40,'shash_digest_unaligned'),('export',48,'shash_default_export'),('import',56,'shash_default_import'),('setkey',88,'shash_no_setkey'))
 for i,(field,offset,target) in enumerate(defaults):
  symbol={'name':target,'info':18,'section':2,'value':32+i*4,'size':4};po['symbols'].append(symbol);off=100+i*8
  if field!='import':pe.append(dict(event(off-4,'cb',nonzero=True,delta=40),condition_value=load(('arg',0),offset,8)))
  pe.append(dict(event(off,'store'),address=add(('arg',0),offset),value=('address',(target,2,symbol['value'],0,18,4)),size=8))
 pe += [dict(event(196,'store'),address=add(('arg',0),64),value=('address',('crypto_shash_type',1,0,0,1,256)),size=8),dict(event(200,'store'),address=add(('arg',0),72),value=('orr',('and',load(('arg',0),72,4),0xfffffff0,32),14,32),size=4),dict(event(204,'store'),address=add(('arg',0),84),value=load(('arg',0),32,4),size=4),event(500,'movn',rd=0,width=32,imm=21),event(504,'ret')]
 prep={'events':pe};check(34,lambda:preparation_proof(prep,pl,compiled,po))
 changed=copy.deepcopy(prep);next(e for e in changed['events'] if e['offset']==100)['value']=('address',('shash_finup_unaligned',2,32,4,18,4));check(35,lambda:preparation_proof(changed,pl,compiled,po),True)
 changed=copy.deepcopy(prep);next(e for e in changed['events'] if e['offset']==16)['source_value']=load(('arg',0),80,4);check(36,lambda:preparation_proof(changed,pl,compiled,po),True)
 changed=copy.deepcopy(prep);next(e for e in changed['events'] if e['offset']==500)['decoded']['imm']=20;check(37,lambda:preparation_proof(changed,pl,compiled,po),True)
 changed=copy.deepcopy(prep);next(e for e in changed['events'] if e['offset']==96)['decoded']['nonzero']=False;check(38,lambda:preparation_proof(changed,pl,compiled,po),True)
 changed=copy.deepcopy(prep);next(e for e in changed['events'] if e['offset']==200)['value']=14;check(39,lambda:preparation_proof(changed,pl,compiled,po),True)
 return {'passed':True,'cases':completed,'case_count':len(completed),'synthetic_only':True,'actual_target_or_compiler_executed':False,'old_suites_replayed':False}

def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();out=a.output.absolute();require(out.is_relative_to(Path(__file__).resolve().parents[2]/'note10/private') and not out.exists(),'fresh private new-only receipt');report=run_cases();out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
if __name__=='__main__':main()
