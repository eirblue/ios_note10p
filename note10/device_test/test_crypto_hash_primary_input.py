"""CP6 new synthetic mandatory-primary cases; no prior fixtures or tools."""
import argparse,builtins,json,stat,tempfile
import crypto_hash_input_contract as primary_contract
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from crypto_hash_composite import require,digest
from crypto_hash_input_contract import prerequisite_capture,mandatory_primary,primary_stat_identity,primary_api_stability
from build_crypto_hash_composite import PUBLIC

CASES=('symlink-primary-ancestor-stat-reject', 'oversize-primary-before-open-reject', 'growing-primary-before-open-reject', 'growing-primary-during-read-reject', 'optional-primary-duplicate-reject', 'primary-alias-dependency-reject', 'primary-other-root-overlap-reject', 'mandatory-primary-no-optional-downgrade-positive', 'nonprimary-dependency-semantics-positive', 'copy-from-one-buffer-positive', 'conflicting-primary-dependency-reject', 'identity-windows-compatible-ctime-positive', 'identity-posix-exact-positive', 'identity-windows-fd-ctime-change-reject', 'identity-windows-path-ctime-change-reject', 'identity-cross-device-reject', 'identity-cross-inode-reject', 'identity-cross-nlink-reject', 'identity-cross-size-reject', 'identity-cross-mtime-reject', 'identity-cross-birthtime-reject', 'identity-posix-cross-ctime-reject', 'identity-windows-missing-birthtime-reject', 'identity-windows-noninteger-birthtime-reject', 'identity-noninteger-nlink-reject', 'identity-missing-ctime-reject', 'identity-unsupported-platform-reject', 'identity-windows-fd-birthtime-change-reject', 'identity-posix-fd-ctime-change-reject', 'identity-posix-path-ctime-change-reject', 'identity-cross-field-mutation-reject', 'late-primary-nlink-mutation-reject', 'late-primary-windows-birthtime-mutation-reject')


def fixture(root,leaf='shash'):
 source=root/'source';objects=root/'objects';include=root/'compiler';dest=root/'captured';primary=source/'crypto'/(leaf+'.c');primary.parent.mkdir(parents=True);primary.write_bytes(b'/* SYNTHETIC '+leaf.encode()+b' primary */\n');header=source/'include/synthetic.h';header.parent.mkdir();header.write_bytes(b'/* synthetic header */\n');include.mkdir();(objects/'crypto').mkdir(parents=True)
 for name in ('.config','include/generated/autoconf.h','include/config/auto.conf'):
  path=objects/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b'SYNTHETIC config\n')
 target='crypto/'+leaf+'.o';token=primary.as_posix();text='cmd_'+target+' := clang-14 -DSYNTHETIC=1 -c -o crypto/.tmp_'+leaf+'.o '+token+'\nsource_'+target+' := '+token+'\ndeps_'+target+' := \\\n  '+header.as_posix()+' \\\n\n';cmd=objects/'crypto'/('.'+leaf+'.o.cmd');cmd.write_text(text,encoding='utf8',newline='\n');return source,objects,include,dest,primary,target,text,cmd,header


def run_cases(completed=None):
 if completed is None:completed=[]
 def reject(fn):
  try:fn()
  except (ValueError,KeyError,TypeError,OSError):return
  raise ValueError('invalid synthetic primary input accepted')
 for name in CASES:
  with tempfile.TemporaryDirectory() as tmp:
   source,objects,include,dest,primary,target,text,cmd,header=fixture(Path(tmp));token=primary.as_posix();key='source/crypto/'+primary.name;raw=primary.read_bytes();capture=lambda:prerequisite_capture(objects,source,include,target,dest)
   if name.startswith('late-primary-'):
    original_identity=primary_contract.primary_stat_identity;original_read=Path.read_bytes;state={'late':False}
    def read_then_mutate(candidate):
     data=original_read(candidate)
     if candidate==header:state['late']=True
     return data
    def late_identity(st,platform):
     fields={field:getattr(st,field) for field in ('st_dev','st_ino','st_nlink','st_size','st_mtime_ns','st_ctime_ns')}
     if name=='late-primary-windows-birthtime-mutation-reject':fields['st_birthtime_ns']=101 if state['late'] else 100;platform='nt'
     else:
      if platform=='nt':fields['st_birthtime_ns']=st.st_birthtime_ns
      if state['late']:fields['st_nlink']+=1
     return original_identity(SimpleNamespace(**fields),platform)
    with patch.object(primary_contract,'primary_stat_identity',late_identity),patch.object(Path,'read_bytes',read_then_mutate):reject(capture)
    require(state['late'],'new late mutation occurs after bounded primary read during nonprimary dependency capture')
   elif name.startswith('identity-'):
    path_before=SimpleNamespace(st_dev=1,st_ino=2,st_nlink=1,st_size=32,st_mtime_ns=300,st_ctime_ns=100,st_birthtime_ns=100);fd_before=SimpleNamespace(**vars(path_before));platform='posix' if 'posix' in name else 'nt'
    if platform=='nt':fd_before.st_ctime_ns=200
    path_after=SimpleNamespace(**vars(path_before));fd_after=SimpleNamespace(**vars(fd_before))
    if name=='identity-windows-compatible-ctime-positive':require(primary_api_stability(path_before,fd_before,fd_after,path_after,platform)==primary_stat_identity(path_before,platform)[0],'Windows compatible fields/birth exact; API-local different ctime meanings independently stable')
    elif name=='identity-posix-exact-positive':primary_api_stability(path_before,fd_before,fd_after,path_after,platform)
    else:
     if name in ('identity-windows-fd-ctime-change-reject','identity-posix-fd-ctime-change-reject'):fd_after.st_ctime_ns+=1
     elif name in ('identity-windows-path-ctime-change-reject','identity-posix-path-ctime-change-reject'):path_after.st_ctime_ns+=1
     elif name.startswith('identity-cross-') and name!='identity-cross-field-mutation-reject':
      field={'device':'st_dev','inode':'st_ino','nlink':'st_nlink','size':'st_size','mtime':'st_mtime_ns','birthtime':'st_birthtime_ns'}[name[len('identity-cross-'):-len('-reject')]];setattr(fd_before,field,getattr(fd_before,field)+1);setattr(fd_after,field,getattr(fd_before,field))
     elif name=='identity-posix-cross-ctime-reject':fd_before.st_ctime_ns+=1;fd_after.st_ctime_ns=fd_before.st_ctime_ns
     elif name=='identity-windows-missing-birthtime-reject':del fd_before.st_birthtime_ns
     elif name=='identity-windows-noninteger-birthtime-reject':fd_before.st_birthtime_ns=float(fd_before.st_birthtime_ns)
     elif name=='identity-noninteger-nlink-reject':fd_before.st_nlink=True
     elif name=='identity-missing-ctime-reject':del fd_before.st_ctime_ns
     elif name=='identity-unsupported-platform-reject':platform='unknown'
     elif name=='identity-windows-fd-birthtime-change-reject':fd_after.st_birthtime_ns+=1
     elif name=='identity-cross-field-mutation-reject':fd_after.st_ino+=1;path_after.st_nlink+=1
     else:raise ValueError('undefined identity case '+name)
     reject(lambda:primary_api_stability(path_before,fd_before,fd_after,path_after,platform))
   elif name in ('mandatory-primary-no-optional-downgrade-positive','nonprimary-dependency-semantics-positive','copy-from-one-buffer-positive'):
    report=capture();require(report['primary_source']=={'token':token,'key':key,'bytes':len(raw),'sha256':digest(raw)} and report['files_sha256'][key]==digest(raw) and report['token_to_key'][token]==key and (dest/key).read_bytes()==raw and key not in report['optional_absent'],'mandatory actual bound source bytes/key/token/SHA/copy');require(len(report['files_sha256'])==5 and report['files_sha256']['source/include/synthetic.h']==digest(header.read_bytes()),'all ordinary nonprimary and three generated entries preserved')
   elif name=='duplicate-primary-single-bounded-read-positive':
    text=text.replace('\n\n','\n  '+token+' \\\n\n');cmd.write_text(text,encoding='utf8',newline='\n');original_open=Path.open;reads=[]
    def counted(candidate,*args,**kwargs):
     if candidate==primary:
      reads.append(args);require(len(reads)==1,'duplicate primary never reopened')
     return original_open(candidate,*args,**kwargs)
    with patch.object(Path,'open',counted):report=capture()
    require(len(reads)==1 and len(report['files_sha256'])==5 and report['files_sha256'][key]==digest(raw),'one primary buffer, one complete map entry')
   elif name=='primary-exact-8MiB-positive':
    raw=b'x'*(8*1024*1024);primary.write_bytes(raw);report=capture();require(report['primary_source']['bytes']==len(raw) and (dest/key).read_bytes()==raw,'exact 8MiB accepted and copied')
   elif name=='new-primary-fixture-public-closure':require('note10/device_test/test_crypto_hash_primary_input.py' in PUBLIC,'new standalone fixture closure')
   elif name in ('symlink-primary-stat-reject','reparse-primary-stat-reject','symlink-primary-ancestor-stat-reject'):
    original=Path.lstat;unsafe=primary.parent if name=='symlink-primary-ancestor-stat-reject' else primary
    def fake(candidate,*args,**kwargs):
     st=original(candidate,*args,**kwargs)
     return SimpleNamespace(st_mode=stat.S_IFLNK if name!='reparse-primary-stat-reject' else st.st_mode,st_file_attributes=1024 if name=='reparse-primary-stat-reject' else 0) if candidate==unsafe else st
    with patch.object(Path,'lstat',fake):reject(lambda:mandatory_primary(text,target,objects,source))
   elif name=='oversize-primary-before-open-reject':
    with primary.open('wb') as stream:stream.truncate(8*1024*1024+1)
    with patch.object(Path,'open',side_effect=AssertionError('oversized primary must reject before opening')):reject(lambda:mandatory_primary(text,target,objects,source))
   elif name in ('growing-primary-before-open-reject','growing-primary-during-read-reject'):
    original_open=Path.open
    class GrowingStream:
     def __init__(self,stream):self.stream=stream
     def __enter__(self):return self
     def __exit__(self,*args):return self.stream.__exit__(*args)
     def fileno(self):return self.stream.fileno()
     def read(self,count):
      require(count==8*1024*1024+1,'primary read uses cap-plus-one');data=self.stream.read(count)
      with builtins.open(primary,'ab') as writer:writer.write(b'growth')
      return data
    def growing(candidate,*args,**kwargs):
     if name=='growing-primary-before-open-reject':
      with builtins.open(primary,'ab') as writer:writer.write(b'growth')
      return original_open(candidate,*args,**kwargs)
     return GrowingStream(original_open(candidate,*args,**kwargs))
    with patch.object(Path,'open',growing):reject(lambda:mandatory_primary(text,target,objects,source))
   elif name=='primary-other-root-overlap-reject':reject(lambda:prerequisite_capture(objects,source,primary.parent,target,dest))
   else:
    if name=='missing-source-assignment-reject':text=text.replace('source_'+target+' := '+token+'\n','')
    elif name=='multiple-source-assignments-reject':text+='source_'+target+' := '+token+'\n'
    elif name=='wrong-source-target-assignment-reject':text=text.replace('source_'+target,'source_crypto/other.o')
    elif name=='foreign-extra-source-assignment-reject':text+='source_crypto/other.o := '+token+'\n'
    elif name=='empty-source-assignment-reject':text=text.replace('source_'+target+' := '+token,'source_'+target+' := ')
    elif name=='dynamic-source-assignment-reject':text=text.replace('source_'+target+' := '+token,'source_'+target+' := $(wildcard '+token+')')
    elif name in ('wrong-declared-primary-reject','foreign-source-root-reject','sibling-root-prefix-reject','escaping-source-token-reject','unsupported-C-source-reject'):
     other={'wrong-declared-primary-reject':source/'crypto/ahash.c','foreign-source-root-reject':source.parent/'foreign/crypto/shash.c','sibling-root-prefix-reject':source.parent/'source-sibling/crypto/shash.c','escaping-source-token-reject':source/'crypto/../crypto/shash.c','unsupported-C-source-reject':source/'crypto/other.c'}[name];text=text.replace(token,other.as_posix())
    elif name=='unsupported-leaf-target-reject':text=text.replace(target,'crypto/other.o');cmd.write_text(text,encoding='utf8');reject(lambda:mandatory_primary(text,'crypto/other.o',objects,source));completed.append(name);continue
    elif name=='missing-CC-primary-reject':text=text.replace(' '+token+'\nsource_','\nsource_',1)
    elif name=='duplicate-CC-primary-reject':text=text.replace(' '+token+'\nsource_',' '+token+' '+token+'\nsource_',1)
    elif name=='wrong-CC-primary-reject':text=text.replace(' '+token+'\nsource_',' '+(source/'crypto/ahash.c').as_posix()+'\nsource_',1)
    elif name=='missing-compile-flag-reject':text=text.replace(' -c -o ',' -o ',1)
    elif name=='missing-primary-file-reject':primary.unlink()
    elif name=='directory-primary-reject':primary.unlink();primary.mkdir()
    elif name=='optional-primary-duplicate-reject':text=text.replace('\n\n','\n  $(wildcard '+token+') \\\n\n')
    elif name=='primary-alias-dependency-reject':text=text.replace('\n\n','\n  '+(source/'crypto/../crypto/shash.c').as_posix()+' \\\n\n')
    elif name=='conflicting-primary-dependency-reject':text=text.replace('\n\n','\n  '+(source/'crypto/foreign.c').as_posix()+' \\\n\n')
    else:raise ValueError('undefined new primary case '+name)
    cmd.write_text(text,encoding='utf8',newline='\n');reject(capture)
   completed.append(name)
 return {'passed':True,'cases':completed,'case_count':len(completed),'synthetic_only':True,'completed_CP6_R1_R3_28_replayed':False,'prior120_42_53_58_16_89_import_or_replay':False,'make_shell_compiler_object_parse_network_API_Git_device_execution':False}


def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--checkpoint',type=Path,required=True);p.add_argument('--checkpoint-sha256',required=True);p.add_argument('--inventory',type=Path,required=True);p.add_argument('--inventory-sha256',required=True);a=p.parse_args();root=Path(__file__).resolve().parents[2];require(not a.output.exists() and a.output.absolute().is_relative_to(root/'note10/private'),'fresh private CP6 result');completed=[];phase='attribution';attribution={'checkpoint_path':str(a.checkpoint.absolute()),'inventory_path':str(a.inventory.absolute())}
 try:
  cpraw=a.checkpoint.read_bytes();invraw=a.inventory.read_bytes();require(digest(cpraw)==a.checkpoint_sha256 and digest(invraw)==a.inventory_sha256,'exact frozen CP6 checkpoint/inventory SHA256');cp=json.loads(cpraw);inventory=json.loads(invraw);attribution.update(checkpoint_sha256=digest(cpraw),inventory_sha256=digest(invraw));require(cp['version']=='v65' and cp['checkpoint']==6 and cp['new_primary_input_fixture_inventory']==list(CASES) and inventory['cases']==list(CASES) and inventory['case_count']==len(CASES) and inventory['fixture_sha256']==digest(Path(__file__).read_bytes()),'exact new-only CP6 ordered inventory')
  for group in ('public_sources_sha256','private_sources_sha256','shared_sources_sha256'):
   for name,expected in cp[group].items():require(digest((root/name).read_bytes())==expected,'current frozen source/import closure')
  phase='new_primary_input_cases';result=run_cases(completed);result.update(attribution)
 except BaseException as error:
  a.output.parent.mkdir(parents=True,exist_ok=True)
  with a.output.open('x',encoding='utf8',newline='\n') as stream:stream.write(json.dumps(dict(attribution,passed=False,cases=completed,case_count=len(completed),completed_case_names=completed,completed_case_count=len(completed),failing_next_case=CASES[len(completed)] if len(completed)<len(CASES) else None,failure_phase=phase,exception_type=type(error).__name__,exception_message=str(error),automatic_retry=False),indent=2)+'\n')
  raise
 a.output.parent.mkdir(parents=True,exist_ok=True)
 with a.output.open('x',encoding='utf8',newline='\n') as stream:stream.write(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':main()
