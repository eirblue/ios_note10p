"""Only new command-path and failure-capture fixtures; no kernel/native run."""
import argparse
import json
from pathlib import Path
import tempfile
import struct
import xnu_runtime_scratch_stack as p
from prepare_xnu_runtime_observation import sha

PATH_CASES=('recorded-modversion-path','direct-path','missing-output','duplicate-output','joined-output',
 'wrong-compiler','missing-stack-flag','disabled-stack-flag','shell-segment','wrong-object',
 'escaped-object','wrong-source','duplicate-command','config-conflict',
 'missing-sidecar-preserves-inputs','bad-command-preserves-inputs','invalid-usage-preserved')
PROVENANCE_CASES=('provenance-rename','provenance-crc-link','pinned-build-mutation','pinned-include-mutation',
 'pinned-lib-mutation','missing-script','modversions-off','lto-on','lto-clang-on','recordmcount-on',
 'stack-validation-on','config-duplicate','make-not-successful','invalid-final-ELF','compiler-object-not-claimed')
CASES=PATH_CASES+PROVENANCE_CASES
CONFIG=b'CONFIG_MODVERSIONS=y\n'

def fixture_object(exports=False):
    # Tiny synthetic ELF section table, not production code or THREAD_SIZE proof.
    names=b'\0.shstrtab\0'+(b'__ksymtab_fixture\0' if exports else b'')
    count=3 if exports else 2;start=64
    header=bytearray(64);header[:6]=b'\x7fELF\x02\x01'
    struct.pack_into('<HH',header,16,1,183);struct.pack_into('<Q',header,40,start)
    struct.pack_into('<HHH',header,58,64,count,1)
    sections=bytes(64)+struct.pack('<IIQQQQIIQQ',1,3,0,0,start+count*64,len(names),0,0,1,0)
    if exports:sections+=struct.pack('<IIQQQQIIQQ',11,1,0,0,start+count*64+len(names),0,0,0,1,0)
    return bytes(header)+sections+names

def provenance_cases(scripts):
    obj=fixture_object();result={}
    renamed=p.postprocess_provenance(CONFIG,scripts,obj,True)
    linked=p.postprocess_provenance(CONFIG,scripts,fixture_object(True),True)
    if renamed['inferred_branch']!='rename' or linked['inferred_branch']!='relocatable-crc-symbol-link':raise AssertionError('pinned branch inference differs')
    result.update({'provenance-rename':True,'provenance-crc-link':True})
    for name,path in zip(PROVENANCE_CASES[2:5],p.KBUILD_PINS):
        bad=dict(scripts);bad[path]+=b' changed';result[name]=reject(p.postprocess_provenance,CONFIG,bad,obj,True)
    bad=dict(scripts);bad.pop(next(iter(bad)));result['missing-script']=reject(p.postprocess_provenance,CONFIG,bad,obj,True)
    result['modversions-off']=reject(p.postprocess_provenance,b'# CONFIG_MODVERSIONS is not set\n',scripts,obj,True)
    for name,key in (('lto-on','LTO'),('lto-clang-on','LTO_CLANG'),('recordmcount-on','FTRACE_MCOUNT_RECORD'),('stack-validation-on','STACK_VALIDATION')):
        result[name]=reject(p.postprocess_provenance,CONFIG+('CONFIG_'+key+'=y\n').encode(),scripts,obj,True)
    result['config-duplicate']=reject(p.postprocess_provenance,CONFIG+b'# CONFIG_LTO is not set\nCONFIG_LTO=n\n',scripts,obj,True)
    result['make-not-successful']=reject(p.postprocess_provenance,CONFIG,scripts,obj,False)
    result['invalid-final-ELF']=reject(p.postprocess_provenance,CONFIG,scripts,b'not ELF',True)
    if (renamed['compiler_output_object_sha256'] is not None or renamed['raw_compiler_object_identity_claimed'] is not False or
        renamed['shell_branch_observed'] is not False or renamed['final_object_sha256']!=sha(obj)):
        raise AssertionError('inferred/independent object facts mislabeled')
    result['compiler-object-not-claimed']=True
    return result


def reject(call,*args):
    try:call(*args)
    except (ValueError,OSError):return True
    raise AssertionError('invalid new capture fixture accepted')

def focused(recorded,output,scripts_root,provenance_only=False):
    # Saved v55 production .cmd did not request stack usage. Only this flag is
    # added to a labeled parser fixture; no compiler or command is executed.
    raw=Path(recorded).read_bytes();command=raw.decode()
    first=command.splitlines()[0]
    if '-fstack-usage' not in first:
        command=command.replace(' := clang-14 ',' := clang-14 -fstack-usage ',1)
    (output/'recorded-command.fixture').write_text(command)
    results={}
    if not provenance_only:
        origin=p.command_origin(command,CONFIG)
        if origin['sidecar']!='arch/arm64/mm/.tmp_init.su':raise AssertionError('pinned modversion sidecar differs')
        results['recorded-modversion-path']=True
        direct=command.replace('arch/arm64/mm/.tmp_init.o','arch/arm64/mm/init.o')
        if p.command_origin(direct,b'# CONFIG_MODVERSIONS is not set\n')['sidecar']!='arch/arm64/mm/init.su':raise AssertionError('direct output differs')
        results['direct-path']=True
    mutations={
      'missing-output':command.replace('-o arch/arm64/mm/.tmp_init.o',''),
      'duplicate-output':command.replace('-c -o ','-c -o evil.o -o '),
      'joined-output':command.replace('-c -o ','-c -oevil.o -o '),
      'wrong-compiler':command.replace('clang-14','clang-23',1),
      'missing-stack-flag':command.replace('-fstack-usage',''),
      'disabled-stack-flag':command.replace('-fstack-usage','-fstack-usage -fno-stack-usage'),
      'shell-segment':command.replace(' -c -o ','; clang-14 -c -o ',1),
      'wrong-object':command.replace('arch/arm64/mm/.tmp_init.o','arch/arm64/mm/other.o'),
      'escaped-object':command.replace('arch/arm64/mm/.tmp_init.o','arch/arm64/mm/../.tmp_init.o'),
      'wrong-source':command.replace('/arch/arm64/mm/init.c','/arch/arm64/mm/other.c'),
      'duplicate-command':command+'\n'+command.splitlines()[0]+'\n',
    }
    if not provenance_only:
        for name,value in mutations.items():results[name]=reject(p.command_origin,value,CONFIG)
        results['config-conflict']=reject(p.command_origin,command,CONFIG+b'CONFIG_MODVERSIONS=n\n')
    scripts={n:(scripts_root/n).read_bytes() for n in p.KBUILD_PINS}
    for name in PATH_CASES[-3:]:
        with tempfile.TemporaryDirectory(dir=output) as temp:
            root=Path(temp);objects=root/'objects';directory=objects/'arch/arm64/mm';directory.mkdir(parents=True)
            source=root/'source';source.mkdir();(source/'fixture.c').write_bytes(b'synthetic source only\n')
            out=root/'output';out.mkdir();(out/'handoff.config').write_bytes(CONFIG)
            (directory/'init.o').write_bytes(fixture_object())
            for filename,content in scripts.items():
                dest=source/filename;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(content)
            (directory/'.init.o.cmd').write_text(mutations['shell-segment'] if name=='bad-command-preserves-inputs' else command)
            if name=='invalid-usage-preserved':(directory/'.tmp_init.su').write_bytes(b'not stack usage\n')
            build={'xnu_runtime_scratch_prepared_sha256':{'fixture.c':sha((source/'fixture.c').read_bytes())}}
            reject(p.preflight,objects,out,source,build,True)
            folder=out/p.FOLDER/'preflight';failure=json.loads((folder/'FAILURE.json').read_text());evidence=json.loads((folder/'evidence.json').read_text())
            if failure.get('accepted_full_build') is not False or failure.get('preliminary') is not True or failure.get('passed') is not False:raise AssertionError('failure mislabeled accepted')
            for filename in ('init.o','init.o.cmd','handoff.config','source/fixture.c')+tuple('kbuild/'+n for n in p.KBUILD_PINS):
                if not (folder/filename).is_file() or evidence['files_sha256'].get(filename)!=sha((folder/filename).read_bytes()):raise AssertionError('failure lost original inputs')
            if name=='invalid-usage-preserved' and (folder/'init.su').read_bytes()!=b'not stack usage\n':raise AssertionError('invalid usage bytes lost')
            if name=='missing-sidecar-preserves-inputs' and 'sidecar' not in failure['error']:raise AssertionError('wrong missing sidecar failure')
            results[name]=True
    results.update(provenance_cases(scripts))
    chosen=PATH_CASES[-3:]+PROVENANCE_CASES if provenance_only else CASES
    return {name:results[name] for name in chosen},sha(raw)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--recorded-command',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);parser.add_argument('--provenance-scripts',type=Path,required=True);parser.add_argument('--provenance-only',action='store_true')
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=False)
    results,recorded_sha=focused(args.recorded_command,args.output,args.provenance_scripts,args.provenance_only)
    (args.output/'result.json').write_text(json.dumps(dict(passed=True,fixture_only=True,synthetic_only=True,
      hardware_verified=False,compiler_executed=False,kernel_compiled=False,cases=results,recorded_command_sha256=recorded_sha,
      canonical_suite_complete=not args.provenance_only,skipped_unchanged_parser_cases=list(PATH_CASES[:14]) if args.provenance_only else [],
      source_sha256=sha(Path(p.__file__).read_bytes()),test_source_sha256=sha(Path(__file__).read_bytes())),indent=2)+'\n')
if __name__=='__main__':main()
