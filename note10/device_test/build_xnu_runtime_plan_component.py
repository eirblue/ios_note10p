"""PC-only pinned Kbuild init.o integration; never builds Image or runs objects."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
import tarfile
import urllib.request
sys.dont_write_bytecode=True
import prepare_xnu_runtime_plan as prepare

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
COMMIT='55f042627bb7030c93550faafa117674d32b21d1'
ARCHIVE_SHA='46d6a563af04e0c2ed9c96c2a1af8cab2344b458c9554b09098e6a9e7219ae4c'
ARCHIVE_URL='https://codeload.github.com/corsicanu/android_kernel_samsung_universal9820/tar.gz/'+COMMIT
SOURCE_TOP='android_kernel_samsung_universal9820-'+COMMIT
TARGET='arch/arm64/mm/init.o'
CMD='arch/arm64/mm/.init.o.cmd'
DEFCONFIG='exynos9820-d2x_defconfig'
OPTION=prepare.OPTION
SOURCE_FILES=('note10/device_test/build_xnu_runtime_plan_component.py',
 'note10/device_test/prepare_xnu_runtime_plan.py','note10/device_test/test_xnu_runtime_plan.py',
 'note10/device_test/test_xnu_runtime_plan_dependencies.py',
 'note10/device_test/xnu_runtime_plan.c','note10/device_test/xnu_runtime_plan_payload.json',
 'note10/device_test/xnu_reserve.c','note10/device_test/prepare_reservation_kernel.py',
 'note10/xnu26/runtime_relocation.c','note10/xnu26/runtime_relocation.h',
 '.github/workflows/note10-xnu-runtime-plan-component.yml')


def digest(path):
    if path.is_symlink() or not path.is_file():raise ValueError('missing/unsafe proof input: '+str(path))
    value=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):value.update(block)
    return value.hexdigest()


def save(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data,indent=2,sort_keys=True)+'\n',encoding='utf8')


def private_output(path,inputs):
    private=(ROOT/'note10/private').resolve();resolved=path.resolve()
    if path.exists() or path.is_symlink() or resolved==private or not resolved.is_relative_to(private):
        raise ValueError('output must be a fresh project-private directory')
    for original in inputs:
        other=original.resolve()
        if resolved.is_relative_to(other) or other.is_relative_to(resolved):
            raise ValueError('output and input artifacts must be disjoint')
    return resolved


def acquire(path):
    if path is None:raise ValueError('archive destination missing')
    with urllib.request.urlopen(ARCHIVE_URL,timeout=120) as response,path.open('xb') as output:
        size=0
        while True:
            block=response.read(1024*1024)
            if not block:break
            size+=len(block)
            if size>1500*1024*1024:raise ValueError('pinned kernel archive exceeds bound')
            output.write(block)
    if digest(path)!=ARCHIVE_SHA:raise ValueError('pinned kernel archive digest differs')


def extract(archive,destination):
    destination.mkdir(parents=True)
    with tarfile.open(archive,'r:gz') as bundle:
        members=bundle.getmembers();total=0
        for member in members:
            target=(destination/member.name).resolve()
            if not target.is_relative_to(destination.resolve()) or member.name.split('/')[0]!=SOURCE_TOP:
                raise ValueError('archive path escapes pinned source root')
            if member.issym() or member.islnk():
                link=(target.parent/member.linkname).resolve() if member.issym() else (destination/member.linkname).resolve()
                if not link.is_relative_to((destination/SOURCE_TOP).resolve()):raise ValueError('archive link escapes source root')
            elif not member.isfile() and not member.isdir():raise ValueError('non-source kernel archive member')
            total+=member.size
            if total>5*1024**3:raise ValueError('expanded source exceeds bound')
        bundle.extractall(destination,members=members,filter='data')
    source=destination/SOURCE_TOP
    if not source.is_dir():raise ValueError('pinned source root absent')
    return source


def run(command,log,environment,commands,cwd=None):
    command=[str(value) for value in command]
    commands.append({'argv':command,'cwd':str(cwd or ROOT),'log':str(log)})
    log.parent.mkdir(parents=True,exist_ok=True)
    with log.open('wb') as output:
        result=subprocess.run(command,cwd=cwd or ROOT,env=environment,stdout=output,stderr=subprocess.STDOUT,timeout=1800)
    if result.returncode:raise ValueError('component command failed: '+log.name)


def capture(command,path,environment,commands):
    run(command,path,environment,commands)
    return path.read_text(encoding='utf8',errors='strict')


def config_gate(path,enabled):
    text=path.read_text();lines=[line for line in text.splitlines() if line.startswith(OPTION+'=') or line=='# '+OPTION+' is not set']
    expected=[OPTION+'=y'] if enabled else []
    if enabled and lines!=expected:raise ValueError('runtime opt-in not uniquely enabled')
    if not enabled and lines not in ([],['# '+OPTION+' is not set']):raise ValueError('disabled runtime opt-in unexpectedly present')
    return {'option':OPTION,'enabled':enabled,'lines':lines,'sha256':digest(path)}


def parse_dependencies(text):
    """Join physical continuations before capturing the logical deps assignment.

    Capturing up to a blank line first drops the final continuation's newline,
    leaving a lone backslash. No backslash token is silently discarded here.
    Only literal paths and Kbuild's optional-header wildcard form are admitted.
    """
    logical=text.replace(chr(92)+'\n',' ')
    assignments=re.findall(r'^deps_[^\s:=]+[ \t]*:=[ \t]*([^\n]*)$',logical,re.M)
    if len(assignments)!=1:raise ValueError('unique actual Kbuild dependency assignment missing')
    remaining=assignments[0].strip();ordinary=[];wildcard=[]
    path=r'[^\s$()\\;:#*?\[\]]+'
    token=re.compile(r'(?:\$\(wildcard[ \t]+('+path+r'(?:[ \t]+'+path+r')*)[ \t]*\)|('+path+r'))(?=[ \t]|$)')
    while remaining:
        match=token.match(remaining)
        if not match:raise ValueError('malformed/unresolved Kbuild dependency expression or escape')
        if match.group(1) is not None:wildcard.append(match.group(1).split())
        else:ordinary.append(match.group(2))
        remaining=remaining[match.end():].lstrip(' \t')
    if not ordinary:raise ValueError('actual Kbuild dependency paths missing')
    return ordinary,wildcard


def dependency_closure(source,objects,path,enabled,compiler_include):
    """Hash actual .cmd prerequisites, including generated configuration headers."""
    text=path.read_text()
    primary=source_dependency(text,source)
    ordinary,wildcard=parse_dependencies(text)
    records={};missing=[]
    def resolve(name,optional=False):
        if '$' in name:raise ValueError('unresolved dependency expression')
        original=Path(name)
        candidates=[original] if original.is_absolute() else [objects/original,source/original]
        allowed=(objects.resolve(),source.resolve(),compiler_include.resolve())
        if not any(any(candidate.resolve().is_relative_to(root) for root in allowed) for candidate in candidates):
            raise ValueError('dependency path escapes isolated roots')
        found=[candidate for candidate in candidates if candidate.is_file() and not candidate.is_symlink()]
        if not found:
            if optional:missing.append(name);return
            raise ValueError('actual dependency absent: '+name)
        selected=found[0].resolve()
        if selected.is_relative_to(objects.resolve()):key='objects/'+selected.relative_to(objects.resolve()).as_posix()
        elif selected.is_relative_to(source.resolve()):key='source/'+selected.relative_to(source.resolve()).as_posix()
        elif selected.is_relative_to(compiler_include):key='compiler-include/'+selected.relative_to(compiler_include).as_posix()
        else:raise ValueError('actual dependency outside isolated source/output or compiler include roots')
        records[key]=digest(selected)
    # fixdep records the primary TU separately, not inside deps_. Preserve the
    # required init.c closure check by resolving and hashing that exact source.
    resolve(primary)
    for name in ordinary:resolve(name)
    for group in wildcard:
        for name in group:resolve(name,True)
    for name in ('include/generated/autoconf.h','include/config/auto.conf','.config'):resolve(name)
    required={'source/'+prepare.INIT,'source/'+prepare.RESERVE,'source/include/linux/types.h'}
    runtime={'source/arch/arm64/mm/'+name for name in (*prepare.COPIES,prepare.GEOMETRY)}
    if not required.issubset(records):raise ValueError('real source/Linux-header closure incomplete')
    if enabled and not runtime.issubset(records):raise ValueError('enabled production runtime dependency closure incomplete')
    if not enabled and runtime.intersection(records):raise ValueError('disabled object depends on runtime component')
    return {'cmd_sha256':digest(path),'target':TARGET,'primary_source':'source/'+prepare.INIT,
            'files_sha256':records,'optional_config_headers_absent':sorted(missing)}


def source_dependency(text,source):
    """Bind fixdep's unique source_, deps_ and cmd_ assignments to init.o."""
    logical=text.replace(chr(92)+'\n',' ')
    fields={prefix:re.findall(r'^'+prefix+r'_([^\s:=]+)[ \t]*:=[ \t]*([^\n]*)$',logical,re.M)
            for prefix in ('source','deps','cmd')}
    if any(len(values)!=1 or values[0][0]!=TARGET for values in fields.values()):
        raise ValueError('unique Kbuild source/deps/cmd object target differs')
    if '-D__KERNEL__' not in fields['cmd'][0][1].split():raise ValueError('actual Kbuild kernel command record missing')
    primary=fields['source'][0][1].strip()
    if (not primary or re.search(r'[\s$()\\;*?\[\]]',primary) or not Path(primary).is_absolute() or
            Path(primary).resolve()!=(source/prepare.INIT).resolve()):
        raise ValueError('actual primary TU differs from pinned source/init.c path')
    return primary


def preserve_kbuild(objects,proof):
    """Persist available actual bytes before any post-compile gate can fail."""
    captured={}
    for name in (TARGET,CMD,'.config','include/generated/autoconf.h','include/config/auto.conf'):
        original=objects/name
        if original.is_file() and not original.is_symlink():
            target=proof/'kbuild'/name;target.parent.mkdir(parents=True,exist_ok=True)
            target.write_bytes(original.read_bytes());captured[name]=digest(target)
    save(proof/'kbuild-capture.json',{'schema':1,'stage':'before post-compile validation','files_sha256':captured})


def inspect_object(path,enabled,proof,environment,commands):
    raw=path.read_bytes()
    if len(raw)<64 or raw[:7]!=b'\x7fELF\x02\x01\x01' or struct.unpack_from('<HH',raw,16)!=(1,183):
        raise ValueError('actual kernel output is not ELF64 AArch64 relocatable')
    symbols=capture(['aarch64-linux-gnu-nm','-a',path],proof/'symbols.txt',environment,commands)
    relocations=capture(['aarch64-linux-gnu-objdump','-r',path],proof/'relocations.txt',environment,commands)
    disassembly=capture(['aarch64-linux-gnu-objdump','-dr',path],proof/'disassembly.txt',environment,commands)
    names={line.split()[-1] for line in symbols.splitlines() if line.split()}
    defined={line.split()[-1] for line in symbols.splitlines() if len(line.split())>=3 and line.split()[-2].upper()!='U'}
    # Names follow the immutable hosted API, checked from the actual production source.
    functions=set(re.findall(r'^int (n10_rt_\w+)\(',prepare.COPIES['runtime_relocation.c'].read_text(),re.M))
    runtime={name for name in names if name.startswith('n10_rt_') or name.startswith('n10_xnu_runtime') or name.startswith('n10_runtime_plan')}
    if enabled:
        wrappers={name for name in defined if name=='n10_xnu_runtime_plan_check' or name.startswith('n10_xnu_runtime_plan_check.')}
        if not functions.issubset(defined) or not wrappers or b'N10XRP1' not in raw:
            raise ValueError('actual enabled component symbols/marker missing')
        if not re.search(r'R_AARCH64_CALL26\s+n10_rt_plan(?:\s|\+|$)',relocations):
            raise ValueError('actual wrapper-to-planner relocation absent')
        bodies=re.findall(r'^[0-9a-f]+ <(n10_xnu_runtime_plan_check(?:\.[^>]*)?)>:\n(.*?)(?=^[0-9a-f]+ <|\Z)',disassembly,re.M|re.S)
        if not bodies or not any(re.search(r'R_AARCH64_CALL26\s+n10_rt_plan(?:\s|\+|$)',body) for _,body in bodies):
            raise ValueError('planner call is not bound to actual wrapper instructions')
        if any(name.startswith('n10_rt_') and name not in defined for name in names):raise ValueError('unresolved planner API')
        if any(('ksymtab' in name or 'kstrtab' in name) and 'n10_rt_' in name for name in names):raise ValueError('runtime API exported from kernel')
    elif runtime or b'N10XRP1' in raw:raise ValueError('disabled object contains runtime component')
    return {'sha256':digest(path),'elf64_aarch64_relocatable':True,'runtime_symbols':sorted(runtime),
            'planner_call_relocation':enabled,'executed':False}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--archive',type=Path)
    parser.add_argument('--payload-manifest',type=Path,default=HERE/'xnu_runtime_plan_payload.json')
    parser.add_argument('--jobs',type=int,default=2)
    args=parser.parse_args()
    if sys.platform!='linux':raise ValueError('actual component build requires Linux Kbuild host')
    if not 1<=args.jobs<=16:raise ValueError('bounded make parallelism required')
    prepare.validate_manifest(args.payload_manifest)
    output=private_output(args.output,[args.payload_manifest,*([args.archive] if args.archive else [])]);output.mkdir(parents=True)
    temporary=output/'tmp';temporary.mkdir()
    environment=dict(os.environ,TMP=str(temporary),TEMP=str(temporary),TMPDIR=str(temporary),PLATFORM_VERSION='11',ANDROID_MAJOR_VERSION='r')
    commands=[];archive=args.archive.resolve() if args.archive else output/'kernel-source.tar.gz'
    if args.archive is None:acquire(archive)
    if digest(archive)!=ARCHIVE_SHA:raise ValueError('exact pinned kernel archive digest differs')
    versions={}
    for tool in ('clang-14','aarch64-linux-gnu-gcc','arm-linux-gnueabi-gcc','gcc','make','aarch64-linux-gnu-nm','aarch64-linux-gnu-objdump'):
        if shutil.which(tool) is None:raise ValueError('required pinned build tool missing: '+tool)
        executable=Path(shutil.which(tool)).resolve()
        versions[tool]={'version':capture([tool,'--version'],output/'toolchain'/(tool+'.txt'),environment,commands),
                        'executable':str(executable),'executable_sha256':digest(executable)}
    compiler_include=Path(capture(['clang-14','-print-file-name=include'],output/'toolchain/compiler-include.txt',environment,commands).strip()).resolve()
    if not compiler_include.is_dir() or not compiler_include.is_absolute():raise ValueError('actual compiler include root missing')
    sources={mode:extract(archive,output/mode/'source') for mode in ('disabled','enabled')}
    run([sys.executable,HERE/'test_xnu_runtime_plan_dependencies.py','--output',output/'toolchain/dependency-parser.json'],
        output/'toolchain/dependency-parser.log',environment,commands)
    run([sys.executable,HERE/'test_xnu_runtime_plan.py','--kernel-source',sources['disabled'],
        '--payload-manifest',args.payload_manifest.resolve(),'--output',output/'host-wrapper','--cc','clang-14'],
        output/'host-wrapper-driver.log',environment,commands)
    host=json.loads((output/'host-wrapper/result.json').read_text())
    if host.get('passed') is not True or host.get('production_planner_executed_in_host') is not False:
        raise ValueError('new host-wrapper proof missing or scope invalid')
    modes={};compiled_modes={}
    for mode,source in sources.items():
        enabled=mode=='enabled';base=output/mode;objects=base/'objects';objects.mkdir();proof=base/'proof';proof.mkdir()
        canonical=prepare.canonical_reservation(source)
        prepared=prepare.prepare(source,canonical,args.payload_manifest,enabled=enabled)
        if not enabled and prepared['before_sha256']!=prepared['after_sha256']:raise ValueError('disabled canonical source/config mutated')
        save(proof/'canonical-reservation.json',canonical);save(proof/'preparation.json',prepared)
        for name in prepared['after_sha256']:
            target=proof/'prepared-source'/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((source/name).read_bytes())
        make=['make','-C',source,'O='+str(objects),'ARCH=arm64','CC=clang-14',
              'CROSS_COMPILE=aarch64-linux-gnu-','CLANG_TRIPLE=aarch64-linux-gnu-',
              'CROSS_COMPILE_ARM32=arm-linux-gnueabi-','GCC_TOOLCHAIN_DIR=/usr/aarch64-linux-gnu/bin/',
              'HOSTCC=gcc','HOSTCFLAGS=-Wno-error=deprecated-declarations','KCFLAGS=-gdwarf-4']
        run([*make,DEFCONFIG],proof/'01-defconfig.log',environment,commands)
        if enabled:run([source/'scripts/config','--file',objects/'.config','--enable',OPTION.removeprefix('CONFIG_')],proof/'02-opt-in.log',environment,commands)
        run([*make,'olddefconfig'],proof/'03-olddefconfig.log',environment,commands)
        try:
            configuration=config_gate(objects/'.config',enabled)
            run([*make,'V=1','-j'+str(args.jobs),TARGET],proof/'04-init-object.log',environment,commands)
        finally:
            # Also retain partial output when make/configuration itself fails.
            preserve_kbuild(objects,proof)
        compiled_modes[mode]={'canonical':canonical,'prepared':prepared,'configuration':configuration}
    # Compile and capture both isolated modes before parser/object acceptance.
    # A proof-format failure must not hide enabled real-header compatibility.
    for mode,source in sources.items():
        enabled=mode=='enabled';base=output/mode;objects=base/'objects';proof=base/'proof'
        canonical=compiled_modes[mode]['canonical'];prepared=compiled_modes[mode]['prepared']
        configuration=compiled_modes[mode]['configuration']
        dependency=dependency_closure(source,objects,objects/CMD,enabled,compiler_include)
        save(proof/'dependencies.json',dependency)
        roots={'source':source,'objects':objects,'compiler-include':compiler_include}
        for name,expected in dependency['files_sha256'].items():
            prefix,relative=name.split('/',1);original=roots[prefix]/relative
            target=proof/'dependency-files'/name;target.parent.mkdir(parents=True,exist_ok=True)
            target.write_bytes(original.read_bytes())
            if digest(target)!=expected:raise ValueError('dependency bytes changed during proof capture')
        object_proof=inspect_object(objects/TARGET,enabled,proof,environment,commands)
        if any(objects.rglob('Image')) or any(objects.rglob('*.cpio')):raise ValueError('unexpected full-image/initramfs output')
        modes[mode]={'enabled':enabled,'canonical':canonical,'preparation':prepared,'configuration':configuration,
            'dependencies':dependency,'object':object_proof,'proof_files_sha256':{
                path.relative_to(proof).as_posix():digest(path) for path in sorted(proof.rglob('*')) if path.is_file()}}
    source_map={name:digest(ROOT/name) for name in SOURCE_FILES}
    result={'schema':1,'passed':True,'verdict':'actual-kernel object integration plus host-wrapper evidence',
      'github_sha':os.environ.get('GITHUB_SHA'),'github_run_id':os.environ.get('GITHUB_RUN_ID'),
      'github_run_attempt':os.environ.get('GITHUB_RUN_ATTEMPT'),'kernel_commit':COMMIT,
      'kernel_archive_sha256':digest(archive),'kernel_archive_url':ARCHIVE_URL,'target':TARGET,
      'toolchain':versions,'source_sha256':source_map,'modes':modes,'commands':commands,
      'host_wrapper_result_sha256':digest(output/'host-wrapper/result.json'),
      'dependency_parser_result_sha256':digest(output/'toolchain/dependency-parser.json'),
      'actual_kernel_objects_executed':False,'old_v54_or_pm_suites_replayed':False,
      'full_image_built':False,'minimal_init_or_cpio_generated':False,'materialized':False,
      'physical_reservation_verified':False,'hardware_verified':False,'xnu_executed':False,
      'deployment_ready':False,'device_operations':[]}
    save(output/'result.json',result)
    print(json.dumps({'passed':True,'target':TARGET,'modes':list(modes),'actual_kernel_objects_executed':False}))


if __name__=='__main__':main()
