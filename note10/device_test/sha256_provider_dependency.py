"""Exact reviewed pyelftools input; never install packages from a verifier."""
import hashlib,json,sys,zipfile
from pathlib import Path
from email.parser import BytesParser
from email import policy
from pre_pm_archive_contract import require,regular
VERSION='0.32'
WHEEL_SHA='013df952a006db5e138b1edf6d8a68ecc50630adbd0d83a2d41e7f846163d738'
WHEEL_BYTES=188525

def wheel_contract(wheel):
 wheel=regular(wheel);raw=wheel.read_bytes();require(len(raw)==WHEEL_BYTES and hashlib.sha256(raw).hexdigest()==WHEEL_SHA,'exact official pyelftools0.32 wheel')
 with zipfile.ZipFile(wheel) as z:
  names=z.namelist();require(len(names)==len(set(names)),'dependency wheel duplicate members');metadata=[n for n in names if n.endswith('.dist-info/METADATA')]
  require(len(metadata)==1,'unique package metadata');info=BytesParser(policy=policy.default).parsebytes(z.read(metadata[0]))
  require(info.get_all('Name')==['pyelftools'] and info.get_all('Version')==[VERSION],'unique dependency distribution/version')
  files={n:z.read(n) for n in names if n.startswith('elftools/') and not n.endswith('/')}
 require(files and all('..' not in Path(n).parts and '\\' not in n for n in files),'canonical complete parser source input')
 return files

def load_parser(site,wheel):
 site=Path(site).absolute();files=wheel_contract(wheel)
 actual={p.relative_to(site).as_posix() for p in (site/'elftools').rglob('*') if p.is_file()}
 require(actual==set(files),'complete installed parser input; no missing/extra package code')
 for name,raw in files.items():require(regular(site/name).read_bytes()==raw,'installed parser source differs from pinned wheel')
 if 'elftools' in sys.modules:require(Path(sys.modules['elftools'].__file__).absolute().is_relative_to(site),'ambiguous preloaded parser')
 sys.dont_write_bytecode=True;sys.path.insert(0,str(site))
 import elftools
 require(elftools.__version__==VERSION and Path(elftools.__file__).absolute().is_relative_to(site),'pinned parser runtime/API version and path')
 from elftools.elf.elffile import ELFFile
 return ELFFile,{'package':'pyelftools','version':VERSION,'wheel_sha256':WHEEL_SHA,'wheel_bytes':WHEEL_BYTES,'package_files_sha256':{n:hashlib.sha256(raw).hexdigest() for n,raw in files.items()}}
