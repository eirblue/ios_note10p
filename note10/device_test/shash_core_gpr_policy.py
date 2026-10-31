"""v64 composite policy: unchanged ordinary GPR subset plus four typed BLR sites.

A partition is provisional. The final callback join is mandatory for bundle acceptance.
"""
import hashlib,struct
from pre_pm_archive_contract import require
from relocation_trial_instructions import ROW
from relocation_trial_kernel_profile import gpr_only
from sha256_provider_object import one_symbol
POLICY='v64-shash-GPR-and-typed-BLR-v1'
EXPECTED={'crypto_shash_update':(96,'update'),'crypto_shash_final':(80,'final'),'crypto_shash_finup':(112,'finup'),'crypto_shash_digest':(132,'digest')}


def gpr_partition(obj,fn,words,text):
 require(one_symbol(obj,fn['name'],2)==fn,'policy owns exact unique actual function symbol');sec=obj['sections'][fn['section']];start=fn['value'];end=start+fn['size'];addresses=list(range(start,end,4));require(fn['size']>0 and fn['size']%4==0 and end<=len(sec['bytes']) and set(words)==set(addresses),'exact complete policy word extent')
 lines=text.splitlines();header='Disassembly of section '+sec['name']+':';require(lines and lines[0]==header,'retained exact actual policy section header');ordinary=[];ordinary_addresses=[];typed=[];seen=[]
 for line in lines[1:]:
  match=ROW.fullmatch(line);require(match is not None,'every policy input row is an original instruction');off=int(match[1],16);require(len(seen)<len(addresses) and off==addresses[len(seen)],'exact ordered policy row addresses, no missing/extra/duplicate row');seen.append(off)
  encoded=bytes.fromhex(match[2]);encoded=encoded[::-1] if len(match[2])==8 else encoded;word=words[off];require(len(encoded)==4 and encoded==sec['bytes'][off:off+4] and word==struct.unpack('<I',encoded)[0],'policy row/word/original-object bytes agree')
  mnemonic=match[3];operand=match[4].strip();is_blr=word&0xfffffc1f==0xd63f0000
  if is_blr:
   require(mnemonic=='blr' and operand=='x8' and word==0xd63f0100,'exact64-bit BLR x8 word/mnemonic/sole operand');require(fn['name'] in EXPECTED and sec['name']=='.text.'+fn['name'],'BLR belongs only to an expected owned callback function/section');relative,slot=EXPECTED[fn['name']];require(off-start==relative,'exact frozen observed callback relative site')
   typed.append({'function':fn['name'],'section_index':fn['section'],'section_name':sec['name'],'section_offset':off,'function_relative_offset':off-start,'word':word,'register':8,'slot':slot,'original_row':line})
  else:
   require(mnemonic!='blr' and not mnemonic.startswith(('blra','bra','retaa','retab')),'no mislabeled/authenticated/tail callback row')
   require(word&0xfe000000!=0xd6000000 or word==0xd65f03c0,'register branch/authentication policy permits only bound BLR and canonical RET')
   ordinary.append(line);ordinary_addresses.append(off)
 require(seen==addresses and len(typed)==(1 if fn['name'] in EXPECTED else 0),'complete owned rows and exact expected typed-site count')
 subset=header+'\n'+'\n'.join(ordinary);delegated=gpr_only(subset);require(delegated['instruction_count']==len(ordinary),'unchanged helper count is ordinary subset only')
 typed_addresses=[r['section_offset'] for r in typed];require(set(ordinary_addresses).isdisjoint(typed_addresses) and set(ordinary_addresses)|set(typed_addresses)==set(addresses) and len(ordinary)+len(typed)==fn['size']//4,'full ordinary/typed partition is disjoint and exhaustive')
 return {'policy':POLICY,'status':'partition only; mandatory final typed callback join before bundle acceptance','instruction_count':len(addresses),'ordinary_instruction_count':len(ordinary),'ordinary_addresses':ordinary_addresses,'ordinary_subset':delegated,'ordinary_subset_text_sha256':hashlib.sha256(subset.encode()).hexdigest(),'typed_indirect_count':len(typed),'typed_indirect_sites':typed,'full_addresses':addresses,'observed_section_header':header,'typed_proof_required':bool(typed),'old_helper_accepted_BLR':False,'ordinary_subset_is_full_scope':not typed,'runtime_callback_or_FP_permission_proven':False}


def bind_typed_coverage(facts,dispatch):
 fields={slot for _,slot in EXPECTED.values()};require(set(dispatch)==fields and set(EXPECTED)<=set(facts),'all four and only four actual callback proof fields')
 covered=[];totals={'full':0,'ordinary':0,'typed':0}
 for name,fact in facts.items():
  fn=fact['symbol'];isa=fact['ISA'];require(fn['name']==name and isa['policy']==POLICY,'typed join actual function/policy identity');full=list(range(fn['value'],fn['value']+fn['size'],4));ordinary=isa['ordinary_addresses'];sites=isa['typed_indirect_sites'];site_offsets=[s['section_offset'] for s in sites]
  require(isa['full_addresses']==full and len(ordinary)==len(set(ordinary)) and len(site_offsets)==len(set(site_offsets)) and set(ordinary).isdisjoint(site_offsets) and set(ordinary)|set(site_offsets)==set(full),'final disjoint exact instruction-row partition')
  require(isa['instruction_count']==len(full)==fn['size']//4 and isa['ordinary_instruction_count']==len(ordinary)==isa['ordinary_subset']['instruction_count'] and isa['typed_indirect_count']==len(sites) and len(full)==len(ordinary)+len(sites),'final actual full/subset/typed counts agree')
  indirect=[e for e in fact['events'] if e['decoded']['op'] in ('blr','br')]
  require(not any(e['decoded']['op']=='br' for e in indirect) and len(indirect)==len(sites)==(1 if name in EXPECTED else 0),'all trace indirect events exactly accounted; no tail/extra/missing site')
  totals['full']+=len(full);totals['ordinary']+=len(ordinary);totals['typed']+=len(sites)
  if name not in EXPECTED:continue
  relative,slot=EXPECTED[name];site=sites[0];event=indirect[0];proof=dispatch[slot];off=fn['value']+relative
  require(site['function']==name and site['section_index']==fn['section'] and site['section_name']=='.text.'+name and site['section_offset']==off and site['function_relative_offset']==relative and site['word']==0xd63f0100 and site['register']==8 and site['slot']==slot,'typed row belongs to its actual function/section/frozen slot')
  require(event['offset']==off and event['decoded']['op']=='blr' and event['decoded']['rn']==8 and event['arguments'][0]==('arg',0),'exact real BLR event/register and descriptor argument')
  require(proof['slot']==slot and proof['call_offset']==off and event['target'] is not None and proof['actual_target_expression']==event['target'] and proof['callback_execution_unresolved'] is True,'one-to-one unchanged typed callback-slot/descriptor/call-offset proof')
  covered.append({'function':name,'section_index':fn['section'],'section_offset':off,'function_relative_offset':relative,'register':8,'slot':slot,'actual_target_expression':event['target'],'descriptor_argument':event['arguments'][0],'runtime_execution_unresolved':True})
 require(len(covered)==4 and len({(r['function'],r['section_offset']) for r in covered})==4 and totals['typed']==4 and totals['full']==totals['ordinary']+totals['typed'],'exactly four covered typed sites and complete combined scope')
 return {'policy':POLICY,'full_scope_partition_and_typed_calls_verified':True,'counts':totals,'typed_callback_sites':covered,'ordinary_helper_scope':'ordinary subsets only; no BLR was passed to or accepted by legacy helper','arbitrary_indirect_call_or_runtime_provider_proven':False,'FP_permission_hardware_or_whole_path_stack_safety_proven':False}
