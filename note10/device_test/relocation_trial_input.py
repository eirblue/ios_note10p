"""Fetch exact authenticated upstream artifact bytes; materialize data only."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
import subprocess
import sys
import zipfile

ROOT=Path(__file__).resolve().parents[2]
RUN=39560904016
HEAD='ff5ace18bacd7bc916561d56a7a97315044b7953'
ARTIFACT=12820035987
DIGEST='e0ec2a08a143fb751b35870c972b113c31315ee78edff4d42737e3d0ec2c930c'
MACHO='b2c80dea6762dc8a388563a099810b48a9157533c6b9c9db8889c29bdddf8d3f'
PAYLOAD='7a573eb6d2f5efc87bd5c85af130ea854eb4bad8370d17a4247e54f9593a836a'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):p.write_text(json.dumps(v,indent=2)+'\n',encoding='utf-8')

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
    out=a.output.resolve()
    if not out.is_relative_to((ROOT/'note10/private').resolve()):raise ValueError('private output required')
    out.mkdir(parents=True,exist_ok=False)
    commands=[]
    def gh(endpoint,name):
        command=['gh','api',endpoint]
        completed=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        if completed.returncode:raise RuntimeError('authenticated GitHub request failed: '+endpoint)
        target=out/name;target.write_bytes(completed.stdout)
        commands.append({'command':command,'returncode':0,'file':name,'sha256':sha(target)})
        write(out/'retrieval.json',{'authenticated':True,'commands':commands,'whole_ci_accepted':False})
        return completed.stdout
    if not (os.environ.get('GH_TOKEN') or os.environ.get('GITHUB_TOKEN')):raise ValueError('authenticated token required')
    prefix='repos/eirblue/ios_note10p/actions/'
    run=json.loads(gh(prefix+f'runs/{RUN}/attempts/2','upstream-run.json'))
    if (run['id'],run['run_attempt'],run['head_sha'],run['status'],run['conclusion'])!=(RUN,2,HEAD,'completed','success'):raise ValueError('upstream run identity')
    artifact=json.loads(gh(prefix+f'artifacts/{ARTIFACT}','upstream-artifact.json'))
    if artifact['id']!=ARTIFACT or artifact['name']!='note10-experimental-native-build' or artifact['expired'] is not False or artifact['digest']!='sha256:'+DIGEST or artifact['workflow_run']['id']!=RUN or artifact['workflow_run']['head_sha']!=HEAD:raise ValueError('upstream artifact identity')
    gh(prefix+f'artifacts/{ARTIFACT}/zip','native.zip')
    if sha(out/'native.zip')!=DIGEST:raise ValueError('upstream archive digest')
    native=out/'native-artifact';native.mkdir()
    with zipfile.ZipFile(out/'native.zip') as z:
        seen=set()
        for item in z.infolist():
            p=PurePosixPath(item.filename)
            if p.as_posix()!=item.filename.rstrip('/') or item.filename in seen or '\\' in item.filename or p.is_absolute() or '..' in p.parts or ':' in item.filename or stat.S_ISLNK(item.external_attr>>16):raise ValueError('unsafe/duplicate archive member')
            seen.add(item.filename)
            if item.file_size>64*1024*1024 or sum(i.file_size for i in z.infolist())>128*1024*1024:raise ValueError('archive extent')
            if item.is_dir():continue
            dest=native.joinpath(*p.parts);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(z.read(item))
    if {p.name for p in native.iterdir()}!={'note10-experimental.macho','build-manifest.json','libNote10.architecture-candidates.a'}:raise ValueError('exact upstream archive files required')
    if sha(native/'note10-experimental.macho')!=MACHO or (native/'note10-experimental.macho').stat().st_size!=18522008:raise ValueError('MachO pin')
    sys.path.insert(0,str(ROOT/'note10/xnu26'))
    from materialize_stage_payload import build
    report=build(native,out/'payload')
    if report['payload_sha256']!=PAYLOAD or report['payload_size']!=19578880 or report['virtual_base']!='0xfffffff007004000' or report['entry_virtual_address']!='0xfffffff007340490':raise ValueError('materialized geometry pin')
    names=['materialize_stage_payload.py','handoff_bundle.py','verify_experimental_artifact.py','boot_contract.py','boot_adt.py']
    source=out/'materializer-source';source.mkdir()
    for n in names:(source/n).write_bytes((ROOT/'note10/xnu26'/n).read_bytes())
    write(out/'input-proof.json',{'schema':1,'run':RUN,'attempt':2,'head':HEAD,'artifact_id':ARTIFACT,
      'archive_sha256':DIGEST,'macho_sha256':MACHO,'payload_sha256':PAYLOAD,'payload_size':19578880,
      'materializer_source_sha256':{n:sha(source/n) for n in names},'physical_access':False,'xnu_executed':False,
      'files_sha256':{p.relative_to(out).as_posix():sha(p) for p in out.rglob('*') if p.is_file()},'whole_ci_accepted':False})

if __name__=='__main__':main()
