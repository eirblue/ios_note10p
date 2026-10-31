"""Only new provider parser fixtures; all layouts/objects here are synthetic."""
import argparse,copy,json,struct
from pathlib import Path
from sha256_provider_dwarf import choose_layout
from sha256_provider_object import reference,exact_target,registration_proof,code_proof
from pre_pm_archive_contract import require
ROOT=Path(__file__).resolve().parents[2]
CASES=('layout-positive','layout-missing','layout-alignment-missing','layout-member-extent','layout-conflict','layout-no-members','layout-overlap','pointer-positive','pointer-duplicate','pointer-kind','pointer-undefined','pointer-compensation','registration-positive','registration-count','registration-array-location','registration-initcall-location','scalar-function-positive','scalar-function-missing-frame','scalar-function-FP-reject','command-positive','command-wrong-target','command-alternate-output','command-missing-stack','command-source-mismatch')
def fixture():
 code=struct.pack('<IIIII',0x90000000,0x91000000,0x52800041,0x94000000,0xd65f03c0)
 null={'name':'','index':0,'flags':0,'bytes':b''};text={'name':'.init.text','index':1,'flags':6,'bytes':code};data={'name':'.data','index':2,'flags':3,'bytes':b'\0'*256};initcall={'name':'.initcall6.init','index':3,'flags':2,'bytes':b'\0'*8}
 init={'name':'sha256_generic_mod_init','info':2,'section':1,'value':0,'size':20};table={'name':'sha256_algs','info':1,'section':2,'value':0,'size':256};root={'name':'__initcall_sha256_generic_mod_init6','info':1,'section':3,'value':0,'size':8};api={'name':'crypto_register_shashes','info':16,'section':0,'value':0,'size':0}
 rels=[{'section':1,'offset':0,'type':275,'symbol':table,'addend':0},{'section':1,'offset':4,'type':277,'symbol':table,'addend':0},{'section':1,'offset':12,'type':283,'symbol':api,'addend':0},{'section':3,'offset':0,'type':257,'symbol':init,'addend':0}]
 return {'sections':[null,text,data,initcall],'symbols':[init,table,root,api],'relocations':rels},table

def run_cases():
 rows=[]
 for name in CASES:
  obj,table=fixture();layout={'name':'fixture_struct','byte_size':16,'alignment':8,'members':[{'name':'field','offset':0,'type':{'kind':'base','byte_size':8}}]};records=[layout]
  if name=='layout-missing':records=[]
  if name=='layout-alignment-missing':layout['alignment']=None
  if name=='layout-member-extent':layout['members'][0]['offset']=12
  if name=='layout-conflict':records.append(dict(copy.deepcopy(layout),byte_size=24))
  if name=='layout-no-members':layout['members']=[]
  if name=='layout-overlap':layout['members'].append({'name':'overlap','offset':4,'type':{'kind':'base','byte_size':8}})
  if name=='pointer-duplicate':obj['relocations'].append(copy.deepcopy(obj['relocations'][-1]))
  if name=='pointer-kind':obj['relocations'][-1]['type']=261
  if name=='pointer-undefined':obj['relocations'][-1]['symbol']=obj['symbols'][-1]
  if name=='pointer-compensation':obj['relocations'][-1]['symbol']=dict(obj['symbols'][0],value=4);obj['relocations'][-1]['addend']=-4
  if name=='registration-count':obj['sections'][1]['bytes']=struct.pack('<IIIII',0x90000000,0x91000000,0x52800021,0x94000000,0xd65f03c0)
  if name=='registration-array-location':obj['relocations'][0]['addend']=8;obj['relocations'][1]['addend']=8
  if name=='registration-initcall-location':obj['relocations'][-1]['addend']=4
  positive=name in ('layout-positive','pointer-positive','registration-positive','scalar-function-positive','command-positive')
  try:
   if name.startswith('layout-'):choose_layout(records,'fixture_struct')
   elif name.startswith('pointer-'):exact_target(reference(obj,3,0),obj['symbols'][0])
   elif name.startswith('registration-'):registration_proof(obj,table)
   elif name.startswith('command-'):
    from build_sha256_provider import command_origin,FLAGS,SETTINGS,SOURCE_TOP
    line='cmd_crypto/sha256_generic.o := clang-14 --target=aarch64-linux-gnu -D__KERNEL__ -mno-implicit-float -Oz '+FLAGS+' -c -o crypto/.tmp_sha256_generic.o /tmp/'+SOURCE_TOP+'/crypto/sha256_generic.c'
    config='\n'.join(k+'='+v for k,v in SETTINGS.items()).encode()
    if name=='command-wrong-target':line=line.replace('cmd_crypto/sha256_generic.o','cmd_crypto/other.o')
    if name=='command-alternate-output':line=line.replace('crypto/.tmp_sha256_generic.o','../outside.o')
    if name=='command-missing-stack':line=line.replace('-fstack-usage','')
    if name=='command-source-mismatch':line=line.replace('/crypto/sha256_generic.c','/crypto/other.c')
    command_origin(line,config)
   else:
    word=0x1e602800 if name=='scalar-function-FP-reject' else 0xd65f03c0;raw=struct.pack('<I',word);s={'index':1,'name':'.text.fixture_fn','flags':6,'bytes':raw};fn={'name':'fixture_fn','info':2,'section':1,'value':0,'size':4}
    toy={'sections':[{'index':0,'name':'','bytes':b'','flags':0},s],'symbols':[fn],'relocations':[]};instruction='fadd d0, d0, d0' if name=='scalar-function-FP-reject' else 'ret';line=' '.join(f'{b:02x}' for b in raw)
    code_proof(toy,'Disassembly of section .text.fixture_fn:\n0: '+line+' '+instruction+'\n','' if name=='scalar-function-missing-frame' else 'fixture.c:1:1:fixture_fn\t0\tstatic\n')
  except (ValueError,KeyError):require(not positive,'new parser positive rejected: '+name)
  else:require(positive,'new parser negative accepted: '+name)
  rows.append({'name':name,'passed':True})
 return rows

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True);a=ap.parse_args();out=a.output.absolute();require(not out.exists() and out.is_relative_to(ROOT/'note10/private'),'fresh private new-parser result');out.parent.mkdir(parents=True,exist_ok=True)
 out.write_text(json.dumps({'passed':True,'fixture_only':True,'synthetic_only':True,'actual_DWARF_or_provider_object_substituted':False,'compiler_provider_or_model_executed':False,'prior_suites_replayed':False,'cases':run_cases()},indent=2)+'\n',newline='\n')
if __name__=='__main__':main()
