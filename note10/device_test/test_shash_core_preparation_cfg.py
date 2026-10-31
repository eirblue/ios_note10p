"""New connected synthetic preparation fixtures only; no retained-object replay."""
import argparse,copy,hashlib,json,struct
from pathlib import Path
from pre_pm_archive_contract import require
from shash_core_instructions import decode
from shash_core_preparation_cfg import preparation_cfg,preparation_cfg_selected
from shash_core_object import function_facts,object_rows,preparation_proof
import shash_core_object as object_module

ROLES=((0,'digest-load'),(4,'digest-compare'),(8,'digest-HI'),(12,'desc-load'),(16,'desc-compare'),(20,'desc-HI'),(24,'state-load'),(28,'state-compare'),(32,'state-LS'),(36,'error-MOVN'),(40,'shared-copy'),(44,'RET'),(48,'flag-load'),(52,'type-ADRP'),(56,'finup-load'),(60,'type-ADD'),(64,'flag-mask'),(68,'flag-type'),(72,'type-store'),(76,'flag-store'),(80,'finup-guard'),(84,'finup-ADRP'),(88,'finup-ADD'),(92,'finup-store'),(96,'digest-load'),(100,'digest-guard'),(104,'digest-ADRP'),(108,'digest-ADD'),(112,'digest-store'),(116,'export-load'),(120,'export-guard'),(124,'export-ADRP'),(128,'import-ADRP'),(132,'export-ADD'),(136,'import-ADD'),(140,'state-copy'),(144,'export-import-STP'),(148,'setkey-load'),(152,'setkey-CBZ'),(156,'success-zero'),(160,'nonnull-return-B'),(164,'setkey-ADRP'),(168,'setkey-ADD'),(172,'setkey-store'),(176,'null-return-B'))
MUTATIONS=(('digest-load-width',0,1<<30),('desc-load-wrong-base',12,1<<5),('state-load-wrong-slot',24,1<<10),('compare64',4,1<<31),('compare-wrong-source',16,1<<5),('compare-no-flags',28,1<<29),('compare-bound',4,1<<10),('first-LS',8,1),('third-HI',32,1),('branch-middle-validation',8,1<<5),('MOVN64',36,1<<31),('MOVN-wrong-error',36,1<<5),('MOVN-shift',36,1<<21),('copy64',40,1<<31),('copy-wrong-temp',40,1<<16),('type-store32',72,1<<30),('flag-store64',76,1<<30),('wrong-mask',64,1<<10),('wrong-type-value',68,1<<10),('finup-guard32',80,1<<31),('finup-guard-inverted',80,1<<24),('digest-guard-wrong-source',100,1),('export-guard32',120,1<<31),('export-group-bypass',120,1<<5),('state-copy-wrong-source',140,1),('pair32',144,1<<31),('pair-preindex',144,1<<23),('pair-postindex',144,1<<24),('pair-load',144,1<<22),('pair-negative-offset',144,1<<21),('pair-wrong-stride',144,1<<15),('pair-base',144,1<<5),('pair-swapped-first',144,1),('pair-swapped-second',144,1<<10),('setkey-CBZ32',152,1<<31),('setkey-CBNZ',152,1<<24),('setkey-wrong-temp',152,1),('success-zero-wrong-source',156,1<<16),('return-edge-enters-MOVN',160,1),('null-return-cycle',176,1),('address-ADRP-immediate',52,1<<5),('address-ADD64-width',60,1<<31),('address-ADD-shifted',60,1<<22))
EXTRA_CASES=('duplicate-relocation','missing-relocation','extra-relocation','relocation-outside-extent','wrong-relocation-kind','wrong-relocation-section','wrong-relocation-target','compensating-relocation-addend','mismatched-pair-symbol','extra-instruction','truncated-function','wrong-symbol-name','wrong-symbol-type','duplicate-function-symbol','wrong-section-name','nonexecutable-section','nonzero-function-start','wrong-DWARF-width','wrong-DWARF-kind','wrong-DWARF-callback-target','wrong-DWARF-scalar-kind','duplicate-DWARF-member','overlapping-DWARF-slot','nonadjacent-import','wrong-DWARF-offset','wrong-oracle-bound','wrong-oracle-mask','wrong-oracle-type','descsize-clobbered-by-statesize','descsize-clobbered-by-default','pair-values-alias','setkey-address-clobbers-zero','export-present-import-absent-preserves','export-absent-import-present-overwrites','null-setkey-edge-zero-provenance','original-fact-retained','exact-section-symbol-relocations','full-function-facts-invalid-branch-reject')
R2_CASES=('wrong-base-structure-kind','wrong-base-structure-name','wrong-cra-type-target-tag','wrong-cra-type-target-name','dispatcher-missing-STP-no-legacy','dispatcher-STR-replacement-no-legacy','dispatcher-expanded-two-STR-no-legacy','dispatcher-pair-base-SP-no-legacy','legacy-envelope-route-only','envelope-marker-pair-load','envelope-marker-pair-store','envelope-marker-CBZ','envelope-marker-backward-B','envelope-marker-backward-HI','envelope-marker-backward-CBNZ','envelope-marker-non-HI','envelope-marker-MOVN-temporary','envelope-marker-MOVN64')
CASES=('connected-new-variant','full-function-facts-dispatcher')+tuple('presence-'+format(i,'04b') for i in range(16))+tuple('size-failure-'+n for n in ('digestsize','descsize','statesize'))+tuple('missing-'+format(pc,'03x')+'-'+role for pc,role in ROLES)+tuple(n+'-reject' for n,_,_ in MUTATIONS)+EXTRA_CASES+R2_CASES


def fixture():
 # Synthetic offsets/registers differ from any captured compiler function.
 slots={'finup':16,'digest':24,'export':48,'import':56,'setkey':72};sizes={'digestsize':152,'descsize':144,'statesize':148}
 def m(name,offset,size,kind='base'):
  typ=dict(kind=kind,byte_size=size,**({'target_tag':'DW_TAG_subroutine_type'} if kind=='pointer' else {}))
  if name=='base':typ['name']='crypto_alg'
  if name=='cra_type':typ.update(target_tag='DW_TAG_structure_type',target_name='crypto_type')
  return {'name':name,'offset':offset,'type':typ}
 layouts={'types':{'shash_alg':{'byte_size':256,'members':[m(n,o,8,'pointer') for n,o in slots.items()]+[m(n,o,4) for n,o in sizes.items()]+[m('base',192,48,'structure')]},'crypto_alg':{'byte_size':48,'members':[m('cra_flags',16,4),m('cra_type',24,8,'pointer')]}}}
 oracle={'values':{'PAGE_SIZE':4096,'CRYPTO_ALG_TYPE_MASK':15,'CRYPTO_ALG_TYPE_SHASH':14}}
 words={}
 def mem(pc,load,size,rd,offset):words[pc]=({(True,4):0xb9400000,(True,8):0xf9400000,(False,4):0xb9000000,(False,8):0xf9000000}[load,size])|((offset//size)<<10)|rd
 def cb(pc,r,target,nonzero):words[pc]=0xb4000000|(int(nonzero)<<24)|(((target-pc)//4&0x7ffff)<<5)|r
 def b(pc,target):words[pc]=0x14000000|((target-pc)//4&0x3ffffff)
 def address(hi,lo,r):words[hi]=0x90000000|r;words[lo]=0x91000000|(r<<5)|r
 for pc,name,r,condition,target in ((0,'digestsize',4,8,36),(12,'descsize',6,8,36),(24,'statesize',5,9,48)):
  mem(pc,True,4,r,sizes[name]);words[pc+4]=0x7100001f|(r<<5)|(512<<10);words[pc+8]=0x54000000|(((target-pc-8)//4&0x7ffff)<<5)|condition
 words[36]=0x12800000|(21<<5)|6;words[40]=0x2a0003e0|(6<<16);words[44]=0xd65f03c0
 mem(48,True,4,7,208);address(52,60,8);mem(56,True,8,9,slots['finup']);words[64]=0x12000000|(28<<16)|(27<<10)|(7<<5)|7;words[68]=0x32000000|(31<<16)|(2<<10)|(7<<5)|7;mem(72,False,8,8,216);mem(76,False,4,7,208)
 cb(80,9,96,True);address(84,88,10);mem(92,False,8,10,slots['finup']);mem(96,True,8,10,slots['digest']);cb(100,10,116,True);address(104,108,10);mem(112,False,8,10,slots['digest'])
 mem(116,True,8,10,slots['export']);cb(120,10,148,True);address(124,132,10);address(128,136,11);mem(140,False,4,6,sizes['statesize']);words[144]=0xa9000000|((slots['export']//8)<<15)|(11<<10)|10
 mem(148,True,8,6,slots['setkey']);cb(152,6,164,False);words[156]=0x2a1f03e0|6;b(160,40);address(164,168,10);mem(172,False,8,10,slots['setkey']);b(176,40)
 raw=b''.join(struct.pack('<I',words[p]) for p in range(0,180,4));fn={'name':'shash_prepare_alg','info':18,'section':1,'value':0,'size':180}
 targets=[{'name':n,'info':18,'section':2,'value':4*i,'size':4} for i,n in enumerate(('shash_finup_unaligned','shash_digest_unaligned','shash_default_export','shash_default_import','shash_no_setkey'))];targets.append({'name':'crypto_shash_type','info':17,'section':3,'value':0,'size':8});byname={t['name']:t for t in targets}
 refs=[]
 for hi,lo,name in ((52,60,'crypto_shash_type'),(84,88,'shash_finup_unaligned'),(104,108,'shash_digest_unaligned'),(124,132,'shash_default_export'),(128,136,'shash_default_import'),(164,168,'shash_no_setkey')):
  for pc,kind in ((hi,275),(lo,277)):refs.append({'section':1,'offset':pc,'type':kind,'symbol':byname[name],'addend':0})
 obj={'sha256':hashlib.sha256(raw).hexdigest(),'sections':[{'bytes':b'','name':'','index':0,'flags':0},{'bytes':raw,'name':'.text.shash_prepare_alg','index':1,'flags':6},{'bytes':bytes(20),'name':'.text.synthetic_defaults','index':2,'flags':6},{'bytes':bytes(8),'name':'.rodata.synthetic_type','index':3,'flags':2}],'symbols':[fn]+targets,'relocations':refs}
 return obj,{'symbol':fn},layouts,oracle


def replace(obj,pc,word):
 raw=bytearray(obj['sections'][1]['bytes']);struct.pack_into('<I',raw,pc,word);obj['sections'][1]['bytes']=bytes(raw)


def integration(obj,fact,layouts,oracle):
 rows=['Disassembly of section .text.shash_prepare_alg:']
 for pc in range(0,180,4):
  raw=obj['sections'][1]['bytes'][pc:pc+4];d=decode(struct.unpack('<I',raw)[0]);op=d['op'];mnemonic={'load':'ldr','store':'str','pair-store':'stp'}.get(op,op)
  if op=='cond':mnemonic='b.hi' if d['condition']==8 else 'b.ls'
  if op=='cb':mnemonic='cbnz' if d['nonzero'] else 'cbz'
  rows.append(format(pc,'x')+': '+raw.hex(' ')+' '+mnemonic+('' if op=='ret' else ' x0'))
 record=object_rows(obj,'\n'.join(rows));complete=function_facts(obj,fact['symbol'],record,{'shash_prepare_alg':{'bytes':0,'classification':'static','fixed_frame_only':True}})
 return preparation_proof(complete,layouts,oracle,obj),complete


def run_cases(completed=None):
 if completed is None:completed=[]
 def check(name,action,reject=False):
  require(name==CASES[len(completed)],'exact new-only preparation fixture inventory')
  try:action()
  except (ValueError,KeyError,IndexError):
   if not reject:raise
  else:require(not reject,'invalid preparation accepted: '+name)
  completed.append(name)
 def equal(a,b):require(a==b,'independent preparation expectation')
 def proof(args):return preparation_cfg(args[1],args[2],args[3],args[0])
 original=fixture();check('connected-new-variant',lambda:proof(original));check('full-function-facts-dispatcher',lambda:integration(*original))
 for i in range(16):
  def path_case(index=i):
   row=proof(original)['success_paths'][index];bits=tuple(bool(index&(1<<(3-j))) for j in range(4));equal(tuple(row['presence'].values()),bits);equal(row['W0'],0)
   for name,bit in zip(('finup','digest','export','setkey'),bits):equal(name in row['writes'],not bit)
   equal('import' in row['writes'],not bits[2]);equal('statesize' in row['writes'],not bits[2]);equal(row['path'][-2:],[40,44])
  check('presence-'+format(i,'04b'),path_case)
 for index,name in enumerate(('digestsize','descsize','statesize')):
  check('size-failure-'+name,lambda i=index:equal(proof(original)['size_failure_paths'][i]['W0'],0xffffffea))
 for pc,role in ROLES:
  args=fixture();replace(args[0],pc,0xd503201f);check('missing-'+format(pc,'03x')+'-'+role,lambda a=args:preparation_proof(a[1],a[2],a[3],a[0]),True)
 for name,pc,xor in MUTATIONS:
  args=fixture();word=struct.unpack_from('<I',args[0]['sections'][1]['bytes'],pc)[0];replace(args[0],pc,word^xor);check(name+'-reject',lambda a=args:proof(a),True)
 for name in EXTRA_CASES+R2_CASES:
  args=fixture();obj,fact,layouts,oracle=args;refs=obj['relocations'];fn=fact['symbol'];members=layouts['types']['shash_alg']['members'];get=lambda n:next(m for m in members if m['name']==n)
  if name=='duplicate-relocation':refs.append(copy.deepcopy(refs[0]))
  elif name=='missing-relocation':refs.pop()
  elif name=='extra-relocation':refs.append(dict(refs[0],offset=40))
  elif name=='relocation-outside-extent':refs[0]['offset']=180
  elif name=='wrong-relocation-kind':refs[0]['type']=283
  elif name=='wrong-relocation-section':refs[0]['section']=2
  elif name=='wrong-relocation-target':refs[0]['symbol']=refs[2]['symbol']
  elif name=='compensating-relocation-addend':refs[0]['addend']=4
  elif name=='mismatched-pair-symbol':refs[1]['symbol']=refs[2]['symbol']
  elif name=='extra-instruction':obj['sections'][1]['bytes']+=struct.pack('<I',0xd503201f);fn['size']+=4
  elif name=='truncated-function':fn['size']-=4
  elif name=='wrong-symbol-name':fn['name']='other'
  elif name=='wrong-symbol-type':fn['info']=17
  elif name=='duplicate-function-symbol':obj['symbols'].append(copy.deepcopy(fn))
  elif name=='wrong-section-name':obj['sections'][1]['name']='.text.other'
  elif name=='nonexecutable-section':obj['sections'][1]['flags']=2
  elif name=='nonzero-function-start':fn['value']=4
  elif name=='wrong-DWARF-width':get('digestsize')['type']['byte_size']=8
  elif name=='wrong-DWARF-kind':get('finup')['type']['kind']='base'
  elif name=='wrong-DWARF-callback-target':get('finup')['type']['target_tag']='DW_TAG_structure_type'
  elif name=='wrong-DWARF-scalar-kind':get('descsize')['type']['kind']='pointer'
  elif name=='duplicate-DWARF-member':members.append(copy.deepcopy(get('digestsize')))
  elif name=='overlapping-DWARF-slot':get('setkey')['offset']=get('digest')['offset']
  elif name=='nonadjacent-import':get('import')['offset']+=8
  elif name=='wrong-DWARF-offset':get('digestsize')['offset']+=4
  elif name=='wrong-oracle-bound':oracle['values']['PAGE_SIZE']=8192
  elif name=='wrong-oracle-mask':oracle['values']['CRYPTO_ALG_TYPE_MASK']=31
  elif name=='wrong-oracle-type':oracle['values']['CRYPTO_ALG_TYPE_SHASH']=13
  elif name=='descsize-clobbered-by-statesize':replace(obj,24,0xb9400000|((148//4)<<10)|6);replace(obj,28,0x7100001f|(6<<5)|(512<<10))
  elif name=='descsize-clobbered-by-default':replace(obj,84,0x90000006);replace(obj,88,0x910000c6);replace(obj,92,0xf9000806)
  elif name=='pair-values-alias':replace(obj,128,0x9000000a);replace(obj,136,0x9100014a);replace(obj,144,0xa9000000|(6<<15)|(10<<10)|10)
  elif name=='setkey-address-clobbers-zero':replace(obj,164,0x90000006);replace(obj,168,0x910000c6);replace(obj,172,0xf9002406)
  elif name=='wrong-base-structure-kind':get('base')['type']['kind']='union'
  elif name=='wrong-base-structure-name':get('base')['type']['name']='unrelated_same_size_structure'
  elif name=='wrong-cra-type-target-tag':layouts['types']['crypto_alg']['members'][1]['type']['target_tag']='DW_TAG_union_type'
  elif name=='wrong-cra-type-target-name':layouts['types']['crypto_alg']['members'][1]['type']['target_name']='unrelated_type'
  elif name.startswith('dispatcher-'):
   if name=='dispatcher-missing-STP-no-legacy':replace(obj,144,0xd503201f)
   elif name=='dispatcher-STR-replacement-no-legacy':replace(obj,144,0xf9000000|((48//8)<<10)|10)
   elif name=='dispatcher-pair-base-SP-no-legacy':replace(obj,144,0xa9000000|(6<<15)|(11<<10)|(31<<5)|10)
   else:
    raw=obj['sections'][1]['bytes'];obj['sections'][1]['bytes']=raw[:144]+struct.pack('<II',0xf9000000|((48//8)<<10)|10,0xf9000000|((56//8)<<10)|11)+raw[148:];fn['size']+=4
    # Retarget all affected edges in the expanded synthetic function.
    for pc,target in ((120,152),(156,168)):
     word=struct.unpack_from('<I',obj['sections'][1]['bytes'],pc)[0];replace(obj,pc,(word&~(0x7ffff<<5))|(((target-pc)//4&0x7ffff)<<5))
    for pc in (164,180):replace(obj,pc,0x14000000|((40-pc)//4&0x3ffffff))
    for r in refs:
     if r['offset']>=148:r['offset']+=4
   def forbidden_legacy(*unused):raise RuntimeError('CP7 mutation reached forbidden legacy fallback')
   def strict_dispatch(a=args):
    original_legacy=object_module.legacy_preparation_proof;object_module.legacy_preparation_proof=forbidden_legacy
    try:return preparation_proof(a[1],a[2],a[3],a[0])
    finally:object_module.legacy_preparation_proof=original_legacy
   check(name,strict_dispatch,True);continue
  elif name.startswith('envelope-marker-'):
   markers={'pair-load':0xa9402c0a,'pair-store':0xa9002c0a,'CBZ':0xb4000001,'backward-B':0x17ffffff,'backward-HI':0x54ffffe8,'backward-CBNZ':0xb5ffffe1,'non-HI':0x54000029,'MOVN-temporary':0x128002a1,'MOVN64':0x928002a0}
   obj['sections'][1]['bytes']=struct.pack('<I',markers[name.removeprefix('envelope-marker-')]);fn['size']=4;check(name,lambda:equal(preparation_cfg_selected(obj,fn),True));continue
  elif name=='full-function-facts-invalid-branch-reject':
   word=struct.unpack_from('<I',obj['sections'][1]['bytes'],152)[0];replace(obj,152,word^(1<<31));check(name,lambda:integration(*args),True);continue
  else:
   if name=='legacy-envelope-route-only':
    # New selector-only fixture; never invokes/replays the old proof or suites.
    words=[]
    for pc,offset,reg in ((0,152,4),(12,144,6),(24,148,5)):
     words.extend((0xb9400000|((offset//4)<<10)|reg,0x7100001f|(reg<<5)|(512<<10),0x54000008|(((60-pc-8)//4)<<5)))
    words.extend((0xf940080a,0xb500006a,0xd2800009,0xf9000809,0x2a1f03e0,0xd65f03c0,0x128002a0,0xd65f03c0));obj['sections'][1]['bytes']=b''.join(struct.pack('<I',w) for w in words);fn['size']=len(words)*4
    check(name,lambda:equal(preparation_cfg_selected(obj,fn),False));continue
   if name=='exact-section-symbol-relocations':
    for r in refs:
     target=r['symbol'];r['symbol']={'name':'','info':3,'section':target['section'],'value':0,'size':0};r['addend']=target['value']
   p=proof(args)
   if name=='export-present-import-absent-preserves':
    for row in p['success_paths']:
     if row['presence']['export']:
      equal(row['final_slots']['import'],('independent_original_import',));equal('import' in row['writes'],False)
      # Specialize the arbitrary independent original to an absent import.
      initial_import=0;final_import=initial_import if row['final_slots']['import']==('independent_original_import',) else row['final_slots']['import'];equal(final_import,0)
   elif name=='export-absent-import-present-overwrites':
    for row in p['success_paths']:
     if not row['presence']['export']:equal(row['final_slots']['import'],'shash_default_import');equal(row['final_slots']['statesize'],('original_descsize',))
   elif name=='null-setkey-edge-zero-provenance':
    for row in p['success_paths']:
     if not row['presence']['setkey']:require('taken CBZ' in row['zero_provenance'] and 156 not in row['path'],'null arm zero from edge equality')
   elif name=='original-fact-retained':
    result,complete=integration(*args);equal(len(complete['events']),45);equal(complete['ISA']['instruction_count'],45);equal(result['legacy_trace_used_for_variant_semantics'],False)
   elif name=='exact-section-symbol-relocations':equal(len(p['all_word_offsets']),45)
   check(name,lambda:None);continue
  check(name,lambda a=args:preparation_proof(a[1],a[2],a[3],a[0]),True)
 return {'passed':True,'case_count':len(completed),'cases':completed,'synthetic_only':True,'prior_fixture_modules_imported_or_replayed':False,'actual_retained_object_checker_or_compiler_replayed':False,'runtime_or_hardware_proven':False}


def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--checkpoint',type=Path,required=True);p.add_argument('--checkpoint-sha256',required=True);p.add_argument('--inventory',type=Path,required=True);p.add_argument('--inventory-sha256',required=True);a=p.parse_args();out=a.output.absolute();require(out.is_relative_to(Path(__file__).resolve().parents[2]/'note10/private') and not out.exists(),'fresh private new preparation receipt')
 completed=[];phase='attribution';attribution={'checkpoint_path':str(a.checkpoint.absolute()),'inventory_path':str(a.inventory.absolute()),'expected_checkpoint_sha256':a.checkpoint_sha256,'expected_inventory_sha256':a.inventory_sha256}
 try:
  checkpoint_raw=a.checkpoint.read_bytes();inventory_raw=a.inventory.read_bytes();attribution.update(checkpoint_sha256=hashlib.sha256(checkpoint_raw).hexdigest(),inventory_sha256=hashlib.sha256(inventory_raw).hexdigest())
  require(attribution['checkpoint_sha256']==a.checkpoint_sha256 and attribution['inventory_sha256']==a.inventory_sha256,'exact independently pinned checkpoint and inventory SHA256')
  checkpoint=json.loads(checkpoint_raw);inventory=json.loads(inventory_raw);fixture_key='note10/device_test/'+Path(__file__).name;fixture_sha=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
  require(inventory['cases']==list(CASES) and inventory['case_count']==len(CASES) and inventory['fixture_sha256']==fixture_sha and checkpoint['public_sources_sha256'][fixture_key]==fixture_sha and checkpoint['new_revision7_fixture_inventory']==list(CASES),'frozen new fixture/checkpoint/inventory attribution')
  phase='synthetic_cases';result=run_cases(completed);result.update(attribution)
 except BaseException as error:
  result=dict(attribution,passed=False,cases=list(completed),case_count=len(completed),completed_case_names=list(completed),completed_case_count=len(completed),failing_next_case=CASES[len(completed)] if len(completed)<len(CASES) else None,failure_phase=phase,exception_type=type(error).__name__,exception_message=str(error),automatic_retry_performed=False,synthetic_only=True)
  out.parent.mkdir(parents=True,exist_ok=True)
  with out.open('x',encoding='utf8',newline='\n') as stream:stream.write(json.dumps(result,indent=2)+'\n')
  raise
 out.parent.mkdir(parents=True,exist_ok=True)
 with out.open('x',encoding='utf8',newline='\n') as stream:stream.write(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':main()
