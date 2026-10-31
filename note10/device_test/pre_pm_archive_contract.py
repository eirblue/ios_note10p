"""Explicit complete external immutable kernel-archive input, never embedded evidence."""
import hashlib,os,stat
from pathlib import Path
PROFILE='external-protected-kernel-archive-v1'
COMMIT='55f042627bb7030c93550faafa117674d32b21d1'
ARCHIVE_SHA='46d6a563af04e0c2ed9c96c2a1af8cab2344b458c9554b09098e6a9e7219ae4c'
ARCHIVE_BYTES=212648376

def require(ok,message):
 if not ok:raise ValueError(message)
def regular(path):
 path=Path(os.path.abspath(path))
 for p in (*reversed(path.parents),path):
  s=p.lstat();require(not stat.S_ISLNK(s.st_mode) and not getattr(s,'st_file_attributes',0)&0x400,'external archive symlink/reparse path')
 require(stat.S_ISREG(path.stat().st_mode),'external archive must be a regular file');return path
def file_id(path):
 s=regular(path).stat();return [s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_nlink]
def archive_identity(path,expected_sha=ARCHIVE_SHA,expected_bytes=ARCHIVE_BYTES):
 path=regular(path);before=file_id(path);require(before[2]==expected_bytes and before[4]>=1,'external archive size/link count')
 value=hashlib.sha256()
 with path.open('rb') as f:
  for chunk in iter(lambda:f.read(1024*1024),b''):value.update(chunk)
 require(value.hexdigest()==expected_sha and file_id(path)==before,'external complete archive hash/stable identity')
 return {'profile':PROFILE,'kernel_commit':COMMIT,'sha256':expected_sha,'bytes':expected_bytes,'file_identity':before}
def stable_archive(path,snapshot,expected_sha=ARCHIVE_SHA,expected_bytes=ARCHIVE_BYTES):
 current=archive_identity(path,expected_sha,expected_bytes);require(current==snapshot,'external archive identity/nlink changed during use');return current
def no_embedded_archive(rows):
 # Exact immutable input payload is forbidden regardless of filename; conventional
 # source-archive member names are also forbidden even if damaged/truncated.
 for name,row in rows.items():
  require(Path(name).name not in ('kernel-source.tar.gz','v62-kernel-source-input.tar.gz') and
   row['sha256']!=ARCHIVE_SHA,'external profile contains embedded source archive')
def pinned_archive(pins,cache):
 require(pins['archive_profile']==PROFILE,'explicit parent external archive profile required')
 expected=pins['protected_archive'];require(isinstance(expected['file_identity'],list) and len(expected['file_identity'])==5 and all(type(v) is int and v>=0 for v in expected['file_identity']) and expected['file_identity'][4]>=1,'exact file identity/link-count types')
 require(set(expected)=={'path','profile','kernel_commit','sha256','bytes','file_identity'},'exact protected input identity schema')
 require(regular(expected['path'])==regular(cache) and expected['profile']==PROFILE and expected['kernel_commit']==COMMIT and expected['sha256']==ARCHIVE_SHA and expected['bytes']==ARCHIVE_BYTES,'fixed protected path/commit/archive identity')
 snapshot=archive_identity(cache);require(snapshot=={k:expected[k] for k in snapshot},'parent-pinned complete protected archive identity/nlink')
 return snapshot

def match_prerequisite(name,retained,archive_bytes):
 require(retained==archive_bytes,'external archive prerequisite bytes differ: '+name)
 return hashlib.sha256(retained).hexdigest()
