"""Actual disabled/enabled init.o Kbuild, closed original-object projection, PC only."""
import argparse
import json
import os
import posixpath
from pathlib import Path,PurePosixPath
import re
import shutil
import struct
import subprocess
import sys
import tarfile
from build_xnu_runtime_plan_component import acquire,extract,parse_dependencies,source_dependency,COMMIT,ARCHIVE_SHA,SOURCE_TOP,DEFCONFIG,TARGET,CMD
import prepare_xnu_runtime_plan as canonical
from prepare_kernel_trial_component import prepare,render,OPTION,ENTRY,FILES,EXTRAS
from kernel_trial_object import parse_elf,component_closure,projection_proof,usage_frames,stack_estimate,linker_script
from xnu_runtime_scratch_stack import command_origin,postprocess_provenance,KBUILD_PINS
from relocation_trial_aarch64_model import ROOT,CASES,LEAF,IMAGE,PAYLOAD_SHA,TIMEOUT_SECONDS,private_path,require,sha,digest,write,elf_image,verify_report,wheel_metadata
from relocation_trial_kernel_profile import PROFILE_ID,kernel_profile,gpr_only
from test_relocation_trial_aarch64 import disassembly_binding,PRODUCTION
from test_kernel_trial_component import run_cases,CASE_INVENTORY
from test_kernel_trial_relocation_binding import run_cases as relocation_binding_cases

PUBLIC=('note10/device_test/relocation_trial_aarch64_model.py','note10/device_test/kernel_trial_adapter.c','note10/device_test/kernel_trial_stack_oracle.c',
 'note10/device_test/prepare_kernel_trial_component.py','note10/device_test/kernel_trial_object.py','note10/device_test/build_kernel_trial_component.py',
 'note10/device_test/test_kernel_trial_component.py','note10/device_test/test_kernel_trial_relocation_binding.py','.github/workflows/note10-kbuild-trial-component.yml')
IMMUTABLE=('note10/xnu26/runtime_relocation.c','note10/xnu26/runtime_relocation.h','note10/xnu26/runtime_relocation_trial.c','note10/xnu26/runtime_relocation_trial.h','note10/device_test/relocation_trial_aarch64_abi.c')
SHARED=('note10/device_test/build_xnu_runtime_plan_component.py','note10/device_test/prepare_xnu_runtime_plan.py','note10/device_test/prepare_reservation_kernel.py','note10/device_test/xnu_reserve.c',
 'note10/device_test/xnu_runtime_scratch_stack.py','note10/device_test/prepare_xnu_runtime_observation.py',
 'note10/device_test/relocation_trial_kernel_profile.py','note10/device_test/relocation_trial_kernel_profile.json','note10/device_test/relocation_trial_instructions.py',
 'note10/device_test/test_relocation_trial_aarch64.py','note10/device_test/test_relocation_trial_wheel_metadata.py','note10/device_test/test_relocation_trial_aarch64_binding.py','note10/device_test/relocation_trial_input.py')
INSTRUMENTATION='-gdwarf-4 -fstack-usage -ffunction-sections -fdata-sections'
KBUILD_SOURCE_FILES=(*KBUILD_PINS,'scripts/basic/fixdep.c','Makefile','arch/arm64/Makefile','arch/arm64/mm/Makefile','arch/arm64/configs/'+DEFCONFIG)

def immutable_sources():
    for name,value in PRODUCTION.items():require(sha(ROOT/name)==value,'immutable planner/trial C/H changed')
    require(sha(ROOT/'note10/device_test/relocation_trial_aarch64_abi.c')=='e20258dfbb8cc93793c974a4386df5e8dda32a9db77c3d14e0c3456601b7b0d7','immutable ABI oracle changed')
    require(len(LEAF)==56 and digest(LEAF)=='37154617c91027ac8e52fea9924579df6f135b0c1179892aad1fe77fb0936d80','immutable modeled leaf ADT call path')

def canonical_key(name,roots):
    p=PurePosixPath(name)
    require(p.is_absolute() and '..' not in p.parts,'absolute canonical prerequisite path')
    matches=[(prefix,PurePosixPath(root)) for prefix,root in roots.items() if p.is_relative_to(PurePosixPath(root))]
    require(len(matches)==1,'dependency escapes or ambiguously overlaps actual roots')
    prefix,root=matches[0];return prefix+'/'+p.relative_to(root).as_posix()

def capture_dependencies(source,objects,compiler,proof):
    command=(objects/CMD).read_text();primary=source_dependency(command,source);ordinary,wildcard=parse_dependencies(command)
    roots={'source':source.resolve(),'objects':objects.resolve(),'compiler-include':compiler.resolve()};records={};tokens={};missing=[]
    def capture(name,optional=False):
        p=Path(name);candidates=[p] if p.is_absolute() else [objects/p,source/p]
        found=[p for p in candidates if p.is_file() and not p.is_symlink()]
        if not found:
            require(optional,'actual nonoptional prerequisite missing');missing.append(name);return
        p=found[0].resolve();key=canonical_key(str(p),roots);target=proof/'dependency-files'/key
        target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(p.read_bytes());records[key]=sha(target);tokens[name]=key
    capture(primary)
    for name in ordinary:capture(name)
    for group in wildcard:
        for name in group:capture(name,True)
    for name in ('.config','include/generated/autoconf.h','include/config/auto.conf'):capture(str(objects/name))
    required={'source/'+canonical.INIT,'source/'+canonical.RESERVE,'source/include/linux/types.h','objects/.config','objects/include/generated/autoconf.h','objects/include/config/auto.conf'}
    require(required<=set(records),'complete real TU/config/header closure')
    report={'roots':{k:str(v) for k,v in roots.items()},'files_sha256':records,'dependency_token_to_canonical_key':tokens,'optional_absent':missing,
      'ordinary':ordinary,'wildcard':wildcard,'primary_source':primary,'cmd_sha256':sha(objects/CMD)}
    write(proof/'dependencies.json',report);return report

def capture_available(source,objects,proof):
    names=(TARGET,CMD,'arch/arm64/mm/.init.o.d','arch/arm64/mm/.tmp_init.su','arch/arm64/mm/init.su','.config','include/generated/autoconf.h','include/config/auto.conf')
    captured={}
    for name in names:
        original=objects/name
        if original.is_file() and not original.is_symlink():
            target=proof/'kbuild'/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(original.read_bytes());captured[name]=sha(target)
    for name in KBUILD_SOURCE_FILES:
        original=source/name
        if original.is_file():
            target=proof/'kbuild-source'/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(original.read_bytes())
    raw_d=any(name.endswith('.d') for name in captured)
    write(proof/'available-capture.json',{'files_sha256':captured,'before_post_compile_assertions':True,'raw_temporary_compiler_object_identity_claimed':False,
      'raw_dependency_d_captured':raw_d,'raw_d_scope':'Only surviving observed raw .d copied. Absent/consumed raw .d is unavailable; full fixdep .cmd and resolved prerequisites retained.',
      'fixdep_command_is_not_raw_compiler_d':True,'consumption_shell_event_observed':False})

def mode_proof(proof,enabled):
    obj=proof/'kbuild'/TARGET;config=(proof/'kbuild/.config').read_bytes();cmd=(proof/'kbuild'/CMD).read_text()
    option=[x for x in config.decode().splitlines() if x.startswith(OPTION+'=') or x=='# '+OPTION+' is not set']
    require(option==[OPTION+'=y'] if enabled else option in ([],['# '+OPTION+' is not set']),'actual default-off config identity')
    origin=command_origin(cmd,config);tokens=re.findall(r'^cmd_[^\n]+ := (.*)$',cmd,re.M);require(len(tokens)==1,'actual unique compile command')
    available=json.loads((proof/'available-capture.json').read_text())
    actual={p.relative_to(proof/'kbuild').as_posix() for p in (proof/'kbuild').rglob('*') if p.is_file()}
    require(actual==set(available['files_sha256']) and all(sha(proof/'kbuild'/name)==h for name,h in available['files_sha256'].items()),'exact surviving actual Kbuild capture bytes')
    require(available['raw_dependency_d_captured']==any(n.endswith('.d') for n in actual) and
      available['fixdep_command_is_not_raw_compiler_d'] is True and available['consumption_shell_event_observed'] is False,'truthful raw dependency versus fixdep scope')
    require((proof/'kbuild-source/scripts/basic/fixdep.c').is_file(),'exact pinned fixdep source required')
    import shlex
    args=shlex.split(tokens[0]);settings=kernel_profile(PROFILE_ID)
    require('-D__KERNEL__' in args,'actual real-header kernel TU compile required')
    for flag in settings['selected_flags']:require(flag in args,'actual TU missing reviewed codegen flag: '+flag)
    require([x for x in args if re.fullmatch('-O[0-3szg]',x)][-1:] == ['-Oz'],'actual optimization order differs; no hidden override')
    groups=(('-mlittle-endian',{'-mlittle-endian','-mbig-endian'}),('-fno-common',{'-fno-common','-fcommon'}),
      ('-fno-PIE',{'-fno-PIE','-fPIE','-fpie','-fno-pie'}),('-mno-implicit-float',{'-mno-implicit-float','-mimplicit-float'}),
      ('-fno-pic',{'-fno-pic','-fpic','-fPIC','-fno-PIC'}),('-mno-global-merge',{'-mno-global-merge','-mglobal-merge'}))
    for expected,group in groups:require([x for x in args if x in group][-1:]==[expected],'actual selected-option ordering override: '+expected)
    require([x for x in args if x.startswith('-march=')][-1:]==['-march=armv8-a+lse'] and
      [x for x in args if x.startswith(('-fstack-protector','-fno-stack-protector'))][-1:]==['-fno-stack-protector'],'actual architecture/protector option ordering override')
    for flag in INSTRUMENTATION.split():require(args.count(flag)==1,'actual projection instrumentation differs: '+flag)
    scripts={name:(proof/'kbuild-source'/name).read_bytes() for name in KBUILD_PINS}
    provenance=postprocess_provenance(config,scripts,obj.read_bytes(),True)
    parsed=parse_elf(obj.read_bytes(),1);closure=component_closure(parsed,enabled)
    sidecar=proof/'kbuild'/origin['sidecar'];require(sidecar.is_file(),'actual compiler-output-derived stack sidecar missing')
    report={'enabled':enabled,'object_sha256':sha(obj),'config_sha256':digest(config),'command_origin':origin,'actual_ordered_compiler_tokens':args,
      'postprocess_provenance':provenance,'component':closure,'sidecar_file':'kbuild/'+origin['sidecar'],'sidecar_sha256':sha(sidecar),
      'instrumentation':INSTRUMENTATION,'unchanged_production_Image_command':False,'kernel_TU_headers':True}
    return report

def archive_files(path,names):
    wanted={SOURCE_TOP+'/'+name:name for name in names};result={};total=0
    with tarfile.open(path,'r|gz') as archive:
        for member in archive:
            if member.name not in wanted:continue
            require(member.isfile(),'canonical dependency must be a regular pinned archive member')
            raw=archive.extractfile(member).read();total+=len(raw);require(total<=128*1024*1024,'bounded selected source/header proof')
            result[wanted[member.name]]=raw
    require(set(result)==set(names),'missing selected original archive source/header');return result

def source_contract(root,mode,archive_source):
    proof=root/'evidence'/mode;enabled=mode=='enabled';base=json.loads((proof/'canonical.json').read_text());identifier=base['reservation_build_id']
    require(re.fullmatch('[0-9a-f]{32}',identifier) and base['canonical_reservation_only'] is True and base['older_preparer_executed'] is False and
      base['ancillary_init_or_cpio_generated'] is False,'source-only canonical recipe identity')
    upstream=archive_source[canonical.INIT];config=archive_source[canonical.KCONFIG]
    require(digest(upstream)==canonical.INIT_SHA,'exact upstream init.c source')
    transformed=canonical.once(canonical.once(upstream,canonical.DECL,canonical.CANON_INCLUDE),canonical.CALL,canonical.CANON_CALL)
    reservation=b'#define N10_RESERVE_BUILD_ID "'+identifier.encode()+b'"\n'+canonical.reservation_body()
    init,kconfig=render(transformed,config,enabled)
    expected={canonical.INIT:init,canonical.KCONFIG:kconfig,canonical.RESERVE:reservation}
    if enabled:
        for name in FILES+EXTRAS:expected['arch/arm64/mm/'+name]=(ROOT/('note10/xnu26/' if name in FILES else 'note10/device_test/')/name).read_bytes()
    prepared=proof/'prepared-source';actual={p.relative_to(prepared).as_posix() for p in prepared.rglob('*') if p.is_file()}
    require(actual==set(expected),'exact prepared TU/source files')
    for name,raw in expected.items():require((prepared/name).read_bytes()==raw,'prepared source/header differs from exact disabled/enabled transform')
    before={canonical.INIT:digest(transformed),canonical.KCONFIG:digest(config),canonical.RESERVE:digest(reservation)}
    preparation=json.loads((proof/'preparation.json').read_text())
    require(base['canonical_source_sha256']==before and preparation['before_sha256']==before and preparation['enabled'] is enabled and
      preparation['after_sha256']=={name:digest(expected[name]) for name in before} and
      preparation['copied_sha256']==({name:digest(expected['arch/arm64/mm/'+name]) for name in FILES+EXTRAS} if enabled else {}),'exact source-only preparation identity/maps')
    for path in (proof/'kbuild-source').rglob('*'):
        if path.is_file():require(path.read_bytes()==archive_source[path.relative_to(proof/'kbuild-source').as_posix()],'actual Kbuild script/defconfig archive binding')
    require({p.relative_to(proof/'kbuild-source').as_posix() for p in (proof/'kbuild-source').rglob('*') if p.is_file()}==set(KBUILD_SOURCE_FILES),'exact required Kbuild/fixdep source inventory')
    return expected

def verify_component_bundle(root,payload):
    immutable_sources()
    result=json.loads((root/'result.json').read_text());require(result['passed'] is True and result['deployment_ready'] is False and result['whole_ci_accepted'] is False,'PC-only component report')
    require(result['kernel_archive_sha256']==ARCHIVE_SHA and sha(root/'kernel-source.tar.gz')==ARCHIVE_SHA,'actual pinned kernel archive')
    special={canonical.INIT,canonical.RESERVE,canonical.KCONFIG,*('arch/arm64/mm/'+n for n in FILES+EXTRAS)}
    wanted={canonical.INIT,canonical.KCONFIG}
    for mode in ('disabled','enabled'):
        proof=root/'evidence'/mode;deps=json.loads((proof/'dependencies.json').read_text())
        wanted.update(key[7:] for key in deps['files_sha256'] if key.startswith('source/') and key[7:] not in special)
        wanted.update(p.relative_to(proof/'kbuild-source').as_posix() for p in (proof/'kbuild-source').rglob('*') if p.is_file())
    archive_source=archive_files(root/'kernel-source.tar.gz',wanted)
    modes={}
    for mode in ('disabled','enabled'):
        proof=root/'evidence'/mode;mode_report=mode_proof(proof,mode=='enabled');modes[mode]=mode_report
        expected_source=source_contract(root,mode,archive_source)
        require(mode_report==result['modes'][mode],'independent mode command/object/config proof')
        deps=json.loads((proof/'dependencies.json').read_text())
        command=(proof/'kbuild'/CMD).read_text();ordinary,wildcard=parse_dependencies(command)
        logical=command.replace('\\\n',' ')
        assignments={prefix:re.findall(r'^'+prefix+r'_([^\s:=]+)\s*:=\s*([^\n]*)$',logical,re.M) for prefix in ('source','deps','cmd')}
        require(all(len(rows)==1 and rows[0][0]==TARGET for rows in assignments.values()) and
          assignments['source'][0][1].strip()==deps['primary_source']==mode_report['command_origin']['source']==str(PurePosixPath(deps['roots']['source'])/canonical.INIT),
          'cross-platform actual source/deps/cmd target and root binding')
        require(ordinary==deps['ordinary'] and wildcard==deps['wildcard'] and deps['cmd_sha256']==sha(proof/'kbuild'/CMD),'actual dependency-expression identity')
        for name,h in deps['files_sha256'].items():require(sha(proof/'dependency-files'/name)==h,'complete retained dependency bytes')
        for name in ('.config','include/generated/autoconf.h','include/config/auto.conf'):
            require(deps['files_sha256']['objects/'+name]==sha(proof/'kbuild'/name),'generated config/header versus actual object capture')
        required={'source/'+name for name in expected_source if name!=canonical.KCONFIG}
        require(required<=set(deps['files_sha256']),'actual enabled/disabled source dependency closure')
        for name,raw in expected_source.items():
            key='source/'+name
            if key in deps['files_sha256']:require(deps['files_sha256'][key]==digest(raw),'actual dependency source versus prepared-source binding')
        require(set(deps['dependency_token_to_canonical_key'])==set([deps['primary_source'],*ordinary,*[x for group in wildcard for x in group]])-set(deps['optional_absent'])|{str(PurePosixPath(deps['roots']['objects'])/name) for name in ('.config','include/generated/autoconf.h','include/config/auto.conf')},'full dependency-token coverage')
        for name,key in deps['dependency_token_to_canonical_key'].items():
            p=PurePosixPath(name)
            if p.is_absolute():require(canonical_key(name,deps['roots'])==key,'canonical dependency path identity')
            else:
                possibilities=[]
                for prefix in ('objects','source'):
                    candidate=posixpath.normpath(posixpath.join(deps['roots'][prefix],name))
                    if PurePosixPath(candidate).is_relative_to(PurePosixPath(deps['roots'][prefix])):possibilities.append(canonical_key(candidate,deps['roots']))
                require(key in possibilities,'relative dependency canonical path identity')
            require(key in deps['files_sha256'],'dependency token missing bytes')
        for key,h in deps['files_sha256'].items():
            if not key.startswith('source/') or key[7:] in special:continue
            require(digest(archive_source[key[7:]])==h,'source-header dependency differs from exact archive')
    projection=root/'projection';original=parse_elf((root/'evidence/enabled/kbuild'/TARGET).read_bytes(),1)
    require(result['entry_symbol']==ENTRY and result['codegen_profile']==kernel_profile(PROFILE_ID),'caller/source-pinned adapter entry and explicit subset model profile')
    linked=parse_elf((projection/'with-relocations.elf').read_bytes(),2);final=parse_elf((projection/'production.elf').read_bytes(),2)
    recomputed=projection_proof(original,linked,final);require(recomputed==result['projection'],'original bytes/relocations projection proof')
    image=elf_image(projection/'production.elf',expected_entry=ENTRY)
    stack_symbol=[s for s in original['symbols'] if s['name']=='n10_kernel_stack_oracle'];require(len(stack_symbol)==1,'exact actual kernel header stack oracle')
    s=stack_symbol[0];raw=original['sections'][s['section']]['bytes'][s['value']:s['value']+s['size']];require(len(raw)==16,'actual stack oracle size')
    thread,irq=struct.unpack('<QQ',raw);usage=(root/'evidence/enabled'/modes['enabled']['sidecar_file']).read_text()
    estimate=stack_estimate(usage_frames(usage),recomputed['closure']['functions'],thread)
    require(result['stack']==dict(estimate,IRQ_STACK_SIZE=irq,IRQ_scope='constant only; no OS/IRQ safety claim'),'independent actual component stack estimate')
    require(result['modeled_stack_leaf_proof']=={'ADT_bytes':56,'ADT_sha256':digest(LEAF),'model_source_sha256':sha(ROOT/'note10/device_test/relocation_trial_aarch64_model.py'),
      'parser_source_sha256':PRODUCTION['note10/xnu26/runtime_relocation.c'],'all_case_arguments_and_readonly_ADT_verified':True,'generic_bound_includes_rejecting_frame':True},'immutable caller/parser leaf specialization binding')
    text=(projection/'production-disassembly.log').read_text();require(gpr_only(text)==result['gpr_analysis'],'closed-component GPR-only instructions')
    require(result['case_inventory']==list(CASES) and len(result['cases'])==4,'four actual-object adapter cases')
    used=set();reports=[]
    for name,record in zip(CASES,result['cases']):
        path=root/record['report'];require(record['case']==name and record['report']=='model/cases/'+name+'/result.json' and sha(path)==record['sha256'],'new case binding')
        report=json.loads(path.read_text());used|=verify_report(root/'model',report,payload,image,expected_profile=PROFILE_ID,expected_entry=ENTRY);reports.append(report)
    require({p.relative_to(root/'model').as_posix() for p in (root/'model/blobs').iterdir()}==used,'exact full compressed observations')
    require(disassembly_binding(text,image,reports)==result['instruction_binding'],'core PCs remain bound to actual trial function')
    return {'verified_component_cases':4,'actual_kernel_object_projection':True,'emulator_replayed':False,'deployment_ready':False}

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--output',type=Path,required=True);ap.add_argument('--payload',type=Path,required=True);ap.add_argument('--dependency-wheels',type=Path,required=True);ap.add_argument('--archive',type=Path);ap.add_argument('--jobs',type=int,default=2);a=ap.parse_args()
    require(sys.platform=='linux' and 1<=a.jobs<=16,'actual bounded Linux Kbuild required');out=private_path(a.output);out.mkdir(parents=True,exist_ok=False)
    commands=[];environment=dict(os.environ,PLATFORM_VERSION='11',ANDROID_MAJOR_VERSION='r')
    def run(cmd,name,timeout=1800):
        record={'command':list(map(str,cmd)),'log':name,'completed':False};commands.append(record);write(out/'commands.json',commands);path=out/name;path.parent.mkdir(parents=True,exist_ok=True)
        with path.open('wb') as log:process=subprocess.run(record['command'],env=environment,stdout=log,stderr=subprocess.STDOUT,timeout=timeout)
        record.update({'completed':True,'returncode':process.returncode});write(out/'commands.json',commands);require(process.returncode==0,'actual component command failed: '+name)
    try:
        immutable_sources()
        source_map={name:sha(ROOT/name) for name in (*PUBLIC,*IMMUTABLE,*SHARED)};source_out=out/'source';source_out.mkdir()
        for name in source_map:shutil.copyfile(ROOT/name,source_out/Path(name).name)
        fixtures=run_cases(canonical_key)+relocation_binding_cases();write(out/'fixtures.json',{'fixture_only':True,'synthetic_only':True,'cases':fixtures,'whole_ci_accepted':False})
        archive=out/'kernel-source.tar.gz'
        if a.archive:shutil.copyfile(a.archive,archive)
        else:acquire(archive)
        require(sha(archive)==ARCHIVE_SHA,'pinned real kernel archive')
        toolchain={}
        for tool in ('clang-14','gcc','make','aarch64-linux-gnu-gcc','arm-linux-gnueabi-gcc','aarch64-linux-gnu-ld','ld.lld-14','llvm-objcopy-14','llvm-objdump-14'):
            actual=Path(shutil.which(tool) or '').resolve(strict=True);run([tool,'--version'],'toolchain/'+tool+'.log');toolchain[tool]={'path':str(actual),'sha256':sha(actual)}
        run(['clang-14','-print-file-name=include'],'toolchain/compiler-include.log');compiler=Path((out/'toolchain/compiler-include.log').read_text().strip()).resolve(strict=True)
        modes={}
        for mode in ('disabled','enabled'):
            base=out/'work'/mode;source=extract(archive,base/'source');objects=base/'objects';objects.mkdir();proof=out/'evidence'/mode;proof.mkdir(parents=True)
            baseline=canonical.canonical_reservation(source);prepared=prepare(source,baseline,mode=='enabled');write(proof/'canonical.json',baseline);write(proof/'preparation.json',prepared)
            for name in (canonical.INIT,canonical.RESERVE,canonical.KCONFIG,*('arch/arm64/mm/'+n for n in (FILES+EXTRAS if mode=='enabled' else ()))):
                target=proof/'prepared-source'/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((source/name).read_bytes())
            make=['make','-C',source,'O='+str(objects),'ARCH=arm64','CC=clang-14','CROSS_COMPILE=aarch64-linux-gnu-','CLANG_TRIPLE=aarch64-linux-gnu-',
              'CROSS_COMPILE_ARM32=arm-linux-gnueabi-','GCC_TOOLCHAIN_DIR=/usr/aarch64-linux-gnu/bin/','HOSTCC=gcc','HOSTCFLAGS=-Wno-error=deprecated-declarations','KCFLAGS='+INSTRUMENTATION]
            try:
                run([*make,DEFCONFIG],'evidence/'+mode+'/01-configure.log')
                if mode=='enabled':run([source/'scripts/config','--file',objects/'.config','--enable',OPTION.removeprefix('CONFIG_')],'evidence/'+mode+'/02-opt-in.log')
                run([*make,'olddefconfig'],'evidence/'+mode+'/03-olddefconfig.log');run([*make,'V=1','-j'+str(a.jobs),TARGET],'evidence/'+mode+'/04-init-object.log')
            finally:capture_available(source,objects,proof)
            capture_dependencies(source,objects,compiler,proof);modes[mode]=mode_proof(proof,mode=='enabled');write(proof/'mode.json',modes[mode])
        projection=out/'projection';projection.mkdir();script=projection/'component.ld';script.write_text(linker_script(),encoding='utf-8',newline='\n');obj=out/'evidence/enabled/kbuild'/TARGET
        run(['ld.lld-14','-static','--gc-sections','--no-relax','--emit-relocs','--strip-debug','--no-undefined','-z','max-page-size=4096','-T',script,obj,'-o',projection/'with-relocations.elf'],'projection/link.log')
        linked=parse_elf((projection/'with-relocations.elf').read_bytes(),2);remove=[s['name'] for s in linked['sections'] if s['type']==4]
        run(['llvm-objcopy-14',*[x for name in remove for x in ('--remove-section',name)],projection/'with-relocations.elf',projection/'production.elf'],'projection/strip-relocations.log')
        proof=projection_proof(parse_elf(obj.read_bytes(),1),linked,parse_elf((projection/'production.elf').read_bytes(),2));image=elf_image(projection/'production.elf',expected_entry=ENTRY)
        original=parse_elf(obj.read_bytes(),1);symbol=next(s for s in original['symbols'] if s['name']=='n10_kernel_stack_oracle');raw=original['sections'][symbol['section']]['bytes'];thread,irq=struct.unpack_from('<QQ',raw,symbol['value'])
        frames=usage_frames((out/'evidence/enabled'/modes['enabled']['sidecar_file']).read_text());estimate=stack_estimate(frames,proof['closure']['functions'],thread)
        run(['llvm-objdump-14','-d',projection/'production.elf'],'projection/production-disassembly.log');text=(projection/'production-disassembly.log').read_text();gpr=gpr_only(text)
        require(a.payload.stat().st_size==IMAGE and sha(a.payload)==PAYLOAD_SHA,'pinned actual flat payload');wheels=list(a.dependency_wheels.glob('*.whl'));require(len(wheels)==1 and wheels[0].name.startswith('unicorn-2.1.4-'),'one pinned Unicorn wheel')
        (out/'dependencies').mkdir();wheel=out/'dependencies'/wheels[0].name;shutil.copyfile(wheels[0],wheel)
        import zipfile
        with zipfile.ZipFile(wheel) as z:
            names=[n for n in z.namelist() if n.endswith('.dist-info/METADATA')];require(len(names)==1,'wheel metadata');wheel_metadata(z.read(names[0]))
        (out/'model/cases').mkdir(parents=True);reports=[]
        for name in CASES:
            run([sys.executable,ROOT/'note10/device_test/relocation_trial_aarch64_model.py','--profile',PROFILE_ID,'--entry-symbol',ENTRY,'--elf',projection/'production.elf','--payload',a.payload.resolve(),
              '--case',name,'--output',out/'model/cases'/name,'--blobs',out/'model/blobs'],'model/'+name+'.log',TIMEOUT_SECONDS+30)
            reports.append(json.loads((out/'model/cases'/name/'result.json').read_text()))
        result={'schema':1,'version':'v61','passed':True,'whole_ci_accepted':False,'deployment_ready':False,'kernel_commit':COMMIT,'kernel_archive_sha256':sha(archive),'source_sha256':source_map,
          'modes':modes,'projection':proof,'stack':dict(estimate,IRQ_STACK_SIZE=irq,IRQ_scope='constant only; no OS/IRQ safety claim'),'gpr_analysis':gpr,'entry_symbol':ENTRY,'codegen_profile':kernel_profile(PROFILE_ID),
          'case_inventory':list(CASES),'cases':[{'case':n,'report':'model/cases/'+n+'/result.json','sha256':sha(out/'model/cases'/n/'result.json')} for n in CASES],
          'instruction_binding':disassembly_binding(text,image,reports),'fixture_cases':fixtures,'toolchain':toolchain,'wheel':{'file':'dependencies/'+wheel.name,'sha256':sha(wheel)},
          'ci_context':{k:os.environ.get(k) for k in ('GITHUB_RUN_ID','GITHUB_RUN_ATTEMPT','GITHUB_SHA','GITHUB_JOB')},'hardware_verified':False,'physical_memory_or_hardware_accessed':False,'xnu_executed':False,'full_Image_or_BOOT_built':False,
          'limits':'Actual real-header instrumented init.o component only, uninvoked in Linux. No allocator/crypto/PM/live caller/IRQ/physical-writer safety proof.'}
        result['modeled_stack_leaf_proof']={'ADT_bytes':56,'ADT_sha256':digest(LEAF),'model_source_sha256':sha(ROOT/'note10/device_test/relocation_trial_aarch64_model.py'),
          'parser_source_sha256':PRODUCTION['note10/xnu26/runtime_relocation.c'],'all_case_arguments_and_readonly_ADT_verified':True,'generic_bound_includes_rejecting_frame':True}
        result['files_sha256']={p.relative_to(out).as_posix():sha(p) for p in out.rglob('*') if p.is_file() and 'work' not in p.relative_to(out).parts}
        write(out/'result.json',result);write(out/'independent-verification.json',verify_component_bundle(out,a.payload.read_bytes()))
    except Exception as error:write(out/'failure.json',{'error':repr(error),'completed':False,'accepted':False,'deployment_ready':False});raise

if __name__=='__main__':main()
