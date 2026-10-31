"""New oracle/alignment and upload-staging fixtures only; no old suites or compilation."""
import argparse,copy,json,os,stat,struct
from types import SimpleNamespace
from unittest import mock
from pathlib import Path
from sha256_provider_oracle import MEMBERS,MAGIC,labels,parse_oracle,supplement
from stage_sha256_provider import stage,inventory,safe
CASES=('oracle-readonly-positive','oracle-writable','oracle-executable','oracle-schema','oracle-symbol-size','oracle-truncated','alignment-missing-positive','alignment-explicit-positive','alignment-size-mismatch','alignment-explicit-mismatch','member-offset-mismatch','member-alignment-mismatch','member-type-alignment-mismatch','member-size-mismatch','member-missing','flexible-context-mismatch','staging-complete-positive','staging-no-overwrite','staging-overlap','staging-source-symlink-metadata','staging-parent-reparse-metadata','staging-failure-preserves-source')

def fixture():
 # Synthetic data only, deliberately not a description of any kernel ABI.
 values={'tag':MAGIC,'schema':1,'storage_word_bytes':8};records=[]
 for name,fields in MEMBERS.items():
  values.update({name+'.size':4096,name+'.alignment':128});members=[]
  for i,member in enumerate(fields):
   prefix=name+'.'+member;off=4096 if member=='__ctx' else 128*(i+1);align=128 if (name,member) in (('shash_alg','digestsize'),('shash_alg','base'),('shash_desc','__ctx')) else 8
   values.update({prefix+'.offset':off,prefix+'.member_alignment':align})
   typ={'kind':'array','byte_size':0,'alignment':None,'flexible_bound_unspecified':True} if member=='__ctx' else {'kind':'scalar','byte_size':8,'alignment':8}
   if member!='__ctx':values.update({prefix+'.size':8,prefix+'.type_alignment':8})
   members.append({'name':member,'offset':off,'type':typ,'member_alignment':align})
  records.append({'name':name,'byte_size':4096,'alignment':128 if name=='crypto_alg' else None,'members':members})
 return values,records

def elf(values,flags=2,symbol_size=None):
 payload=struct.pack('<'+'Q'*len(labels()),*[values[n] for n in labels()]);names=b'\0.shstrtab\0.strtab\0.symtab\0.n10_sha256_layout\0';strings=b'\0n10_sha256_layout_values\0'
 symbols=bytes(24)+struct.pack('<IBBHQQ',1,17,0,4,0,len(payload) if symbol_size is None else symbol_size)
 parts=[b'',names,strings,symbols,payload];offset=64;headers=[]
 for i,data in enumerate(parts):
  name=0 if i==0 else names.index((b'.shstrtab',b'.strtab',b'.symtab',b'.n10_sha256_layout')[i-1]);headers.append(struct.pack('<IIQQQQIIQQ',name,(0,3,3,2,1)[i],flags if i==4 else 0,0,offset,len(data),2 if i==3 else 0,1 if i==3 else 0,8 if i in (3,4) else 1,24 if i==3 else 0));offset+=len(data)
 header=bytearray(64);header[:16]=b'\x7fELF\x02\x01\x01'+bytes(9);struct.pack_into('<HHIQQQIHHHHHH',header,16,1,183,1,0,0,offset,0,64,0,0,64,5,1)
 return bytes(header)+b''.join(parts)+b''.join(headers)

def run_cases(root,metadata_only=False):
 require=__import__('pre_pm_archive_contract').require
 root=safe(root,True);require(root.is_relative_to(Path(__file__).resolve().parents[2]/'note10/private') and not root.exists(),'fresh private fixture case root');root.mkdir(parents=True);completed=[];selected=CASES[-3:] if metadata_only else CASES
 def check(name,fn,reject=False):
  require(name==selected[len(completed)],'exact new fixture ordering')
  try:fn()
  except (ValueError,FileNotFoundError):
   if not reject:raise
  else:require(not reject,'invalid new oracle/staging fixture accepted: '+name)
  completed.append(name);(root/'progress.json').write_text(json.dumps({'passed':False,'completed':completed,'synthetic_only':True})+'\n',encoding='utf8')
 source=root/'source';source.mkdir();(source/'empty').mkdir();(source/'.hidden').write_bytes(b'actual\x00evidence');(source/'nested').mkdir();(source/'nested/file').write_bytes(b'123')
 if not metadata_only:
  values,records=fixture();raw=elf(values);oracle=parse_oracle(raw)
  check(CASES[0],lambda:parse_oracle(raw))
  check(CASES[1],lambda:parse_oracle(elf(values,3)),True)
  check(CASES[2],lambda:parse_oracle(elf(values,6)),True)
  changed=dict(values,schema=2);check(CASES[3],lambda:parse_oracle(elf(changed)),True)
  check(CASES[4],lambda:parse_oracle(elf(values,symbol_size=8)),True)
  check(CASES[5],lambda:parse_oracle(raw[:-1]),True)
  check(CASES[6],lambda:supplement(records,oracle))
  explicit=copy.deepcopy(records)
  for row in explicit:row['alignment']=128
  check(CASES[7],lambda:supplement(explicit,oracle))
  def mutation(index,change):
   rows=copy.deepcopy(records);change(rows);check(CASES[index],lambda:supplement(rows,oracle),True)
  mutation(8,lambda r:r[0].update(byte_size=2048))
  mutation(9,lambda r:r[0].update(alignment=64))
  mutation(10,lambda r:r[0]['members'][0].update(offset=0))
  mutation(11,lambda r:r[0]['members'][8].update(member_alignment=8))
  mutation(12,lambda r:r[0]['members'][0]['type'].update(alignment=16))
  mutation(13,lambda r:r[0]['members'][0]['type'].update(byte_size=4))
  mutation(14,lambda r:r[0]['members'].pop())
  mutation(15,lambda r:r[3]['members'][-1]['type'].update(flexible_bound_unspecified=False))
  check(CASES[16],lambda:stage(source,root/'upload'))
  check(CASES[17],lambda:stage(source,root/'upload'),True)
  check(CASES[18],lambda:stage(source,source/'upload'),True)
 else:
  # Necessary staged-file setup only; do not invoke previous19 case checks.
  child=root/'upload/v63-ci-provider';child.mkdir(parents=True);(child/'.hidden').write_bytes(b'actual\x00evidence')
 def metadata_refusal(path,parent_mode=False):
  # Synthetic filesystem metadata, not a real OS symlink/reparse capability test.
  original=Path.lstat;hits=[]
  def lstat(candidate,*args,**kwargs):
   if candidate==path:
    hits.append(str(candidate))
    return SimpleNamespace(st_mode=(stat.S_IFDIR|0o755) if parent_mode else (stat.S_IFLNK|0o777),st_file_attributes=0x400 if parent_mode else 0)
   return original(candidate,*args,**kwargs)
  with mock.patch.object(Path,'lstat',autospec=True,side_effect=lstat):
   try:
    if parent_mode:stage(source,path)
    else:stage(path,root/'bad-upload')
   except ValueError as error:require(str(error)=='no staging symlink/reparse' and bool(hits),'actual safe refusal branch with synthetic metadata')
   else:raise AssertionError('production safe accepted synthetic link metadata')
 check(CASES[19],lambda:metadata_refusal(source))
 metadata_parent=root/'metadata-parent';metadata_parent.mkdir()
 check(CASES[20],lambda:metadata_refusal(metadata_parent,True))
 def preservation():
  before=inventory(source)
  refused=False
  try:stage(source,root/'upload')
  except ValueError as error:refused=str(error)=='fresh separate staging parent; no overwrite'
  require(refused,'actual production no-overwrite failure required')
  require(inventory(source)==before and (root/'upload/v63-ci-provider/.hidden').read_bytes()==b'actual\x00evidence','failure preserves original and already-staged evidence')
 check(CASES[21],preservation)
 return {'passed':True,'cases':completed,'case_count':len(completed),'selected_cases':list(selected),'canonical_case_count':len(CASES),'selection':'metadata-only' if metadata_only else 'all-new-oracle-staging','synthetic_lstat_metadata_cases':list(CASES[19:21]),'real_OS_symlink_capability_tested':False,'synthetic_only':True,'old_suites_replayed':False,'compiler_or_provider_executed':False}

def main():
 p=argparse.ArgumentParser();p.add_argument('--case-root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--metadata-only',action='store_true',help='Only two synthetic lstat refusal cases and actual staging-failure preservation');a=p.parse_args()
 a.output=safe(a.output,True)
 if a.output.exists() or not a.output.is_relative_to(Path(__file__).resolve().parents[2]/'note10/private'):raise ValueError('fresh private result only')
 try:report=run_cases(a.case_root,a.metadata_only)
 except Exception as error:
  a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps({'passed':False,'error':repr(error),'partial_fixture_evidence_preserved':True})+'\n',encoding='utf8');raise
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
if __name__=='__main__':main()
