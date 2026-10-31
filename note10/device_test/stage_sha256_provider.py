"""Fresh, no-follow byte-identical staging with one provider child directory."""
import argparse,hashlib,json,os,stat
from pathlib import Path
from pre_pm_archive_contract import require
CHILD='v63-ci-provider'

def safe(path,missing=False):
 path=Path(os.path.abspath(path))
 for p in (*reversed(path.parents),path):
  try:s=p.lstat()
  except FileNotFoundError:
   require(missing,'missing staging input');continue
  require(not stat.S_ISLNK(s.st_mode) and not getattr(s,'st_file_attributes',0)&0x400,'no staging symlink/reparse')
 return path

def inventory(root):
 root=safe(root);require(root.is_dir(),'staging root is directory');files={};directories=[]
 for base,dirs,names in os.walk(root,followlinks=False):
  for name in sorted(dirs):
   p=safe(Path(base)/name);require(stat.S_ISDIR(p.lstat().st_mode),'only real staging directories');directories.append(p.relative_to(root).as_posix())
  for name in sorted(names):
   p=safe(Path(base)/name);s=p.lstat();require(stat.S_ISREG(s.st_mode),'only regular staging files')
   h=hashlib.sha256()
   with os.fdopen(os.open(p,os.O_RDONLY|getattr(os,'O_BINARY',0)|getattr(os,'O_NOFOLLOW',0)),'rb') as stream:
    opened=os.fstat(stream.fileno());require((opened.st_dev,opened.st_ino,opened.st_size)==(s.st_dev,s.st_ino,s.st_size),'stable opened staging input')
    for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
   after=p.lstat();require((s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns)==(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns),'staging input unchanged during hashing')
   files[p.relative_to(root).as_posix()]={'bytes':s.st_size,'sha256':h.hexdigest()}
 return {'files':files,'directories':sorted(directories)}

def stage(source,parent):
 source=safe(source);parent=safe(parent,True)
 require(not parent.exists() and not parent.is_relative_to(source) and not source.is_relative_to(parent),'fresh separate staging parent; no overwrite')
 before=inventory(source);require(before['files'],'nonempty provider evidence');parent.mkdir();child=parent/CHILD;child.mkdir()
 for name in before['directories']:(child/name).mkdir(parents=True,exist_ok=True)
 for name in sorted(before['files']):
  src=safe(source/name);dest=child/name;dest.parent.mkdir(parents=True,exist_ok=True)
  flags=os.O_RDONLY|getattr(os,'O_BINARY',0)|getattr(os,'O_NOFOLLOW',0)
  descriptor=os.open(src,flags)
  with os.fdopen(descriptor,'rb') as incoming,dest.open('xb') as outgoing:
   require(stat.S_ISREG(os.fstat(incoming.fileno()).st_mode),'regular opened staging source')
   for block in iter(lambda:incoming.read(1024*1024),b''):outgoing.write(block)
 require(inventory(source)==before==inventory(child),'exact complete path/byte staging identity')
 require([p.name for p in parent.iterdir()]==[CHILD],'single child staging namespace')
 return {'passed':True,'child':CHILD,'inventory':before,'source_or_target_execution':False,'old_failed_artifact_rewritten':False}

def main():
 p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--staging-parent',type=Path,required=True);p.add_argument('--receipt',type=Path,required=True);a=p.parse_args()
 receipt=safe(a.receipt,True);source=safe(a.source);parent=safe(a.staging_parent,True)
 require(not receipt.exists() and not receipt.is_relative_to(parent) and not receipt.is_relative_to(source),'fresh receipt outside uploaded parent and source')
 receipt.parent.mkdir(parents=True,exist_ok=True)
 try:result=stage(source,parent)
 except Exception as error:
  receipt.write_text(json.dumps({'passed':False,'error':repr(error),'partial_staging_preserved':True})+'\n',encoding='utf8',newline='\n');raise
 receipt.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n',encoding='utf8',newline='\n')
if __name__=='__main__':main()
