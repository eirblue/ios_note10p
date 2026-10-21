"""Sequentially apply/reverse the local patch series in an isolated minimal source stage."""
import hashlib
import json
from pathlib import Path
import subprocess
from prepare_build_selection import ROOT

def main():
    target=json.loads((ROOT/'note10/target.json').read_text())
    research=ROOT/target['research_directory']
    reference=json.loads((research/'xnu-reference.json').read_text())
    source=ROOT/reference['source_directory']
    patches=ROOT/'note10/xnu26/patches'
    names=[s.strip() for s in (patches/'series').read_text().splitlines() if s.strip() and not s.startswith('#')]
    stage=ROOT/'note10/private/xnu26-series-stage';stage.mkdir(exist_ok=True)
    paths=set()
    for name in names:
        if Path(name).name!=name:raise ValueError('Unexpected patch filename')
        for line in (patches/name).read_text(encoding='utf-8').splitlines():
            if line.startswith('--- a/') or line.startswith('+++ b/'):
                rel=Path(line[6:])
                if rel.is_absolute() or '..' in rel.parts or '.git' in rel.parts:
                    raise ValueError('Unsafe patch path')
                paths.add(rel)
    original={}
    for rel in paths:
        p=stage/rel
        if not p.resolve().is_relative_to(stage.resolve()):raise ValueError('Stage path escaped')
        p.parent.mkdir(parents=True,exist_ok=True)
        original[rel]=(source/rel).read_bytes() if (source/rel).is_file() else None
        if original[rel] is not None:p.write_bytes(original[rel])
        elif p.exists():p.unlink()
    command=['git','-c','core.autocrlf=false','apply','--directory',stage.relative_to(ROOT).as_posix()]
    for name in names:
        rel=(patches/name).relative_to(ROOT).as_posix()
        subprocess.run([*command,'--check',rel],cwd=ROOT,check=True)
        subprocess.run([*command,rel],cwd=ROOT,check=True)
    applied={rel.as_posix():hashlib.sha256((stage/rel).read_bytes()).hexdigest() for rel in paths}
    for name in reversed(names):
        subprocess.run([*command,'--reverse',(patches/name).relative_to(ROOT).as_posix()],cwd=ROOT,check=True)
    for rel,raw in original.items():
        assert (stage/rel).read_bytes()==raw if raw is not None else not (stage/rel).exists()
        assert (source/rel).read_bytes()==raw if raw is not None else not (source/rel).exists()
    report={'reference_commit':reference['commit'],'series':names,'patched_files_sha256':applied,
        'patch_sha256':{name:hashlib.sha256((patches/name).read_bytes()).hexdigest() for name in names},
        'sequential_apply_reverse_passed':True,'pristine_source_unchanged':True,'whole_kernel_build':False}
    (ROOT/'note10/private/xnu26-series-result.json').write_text(json.dumps(report,indent=2))
    print(json.dumps({'patches':len(names),'files':len(paths),'sequential_apply_reverse_passed':True}))
if __name__=='__main__':main()
