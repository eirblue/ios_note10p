"""Focused .cmd parser/proof-retention fixtures only; no compiler or old suites.

The separately recorded source_ assignment and continued deps_ layout follow
the preserved actual Kbuild .cmd. These generated fixtures are not actual kernel
proof; later CI supplies its own separately preserved object/config/.cmd bytes.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import tempfile
sys.dont_write_bytecode=True
import build_xnu_runtime_plan_component as component

ROOT=Path(__file__).resolve().parents[2]
SLASH=chr(92)


def continued(lines,source_path=None):
    return ('cmd_arch/arm64/mm/init.o := clang-14 -D__KERNEL__ -c init.c\n\n'
            +('source_arch/arm64/mm/init.o := '+source_path.as_posix()+'\n\n' if source_path else '')+
            'deps_arch/arm64/mm/init.o := '+SLASH+'\n'+
            ''.join('  '+line+' '+SLASH+'\n' for line in lines)+'\n'
            'arch/arm64/mm/init.o: $(deps_arch/arm64/mm/init.o)\n\n'
            '$(deps_arch/arm64/mm/init.o):\n')


def rejected(call,*args,contains=None):
    try:call(*args)
    except ValueError as error:
        if contains and contains not in str(error):raise AssertionError('unexpected rejection: '+str(error))
        return
    raise AssertionError('malformed dependency fixture accepted')


def cases(work):
    results=[]
    paths=['arch/arm64/mm/init.c','arch/arm64/mm/note10_xnu_reserve.c','include/linux/types.h']
    raw=continued([paths[0],'$(wildcard include/config/arm64.h)',paths[1],
                   '$(wildcard include/config/foo.h include/config/bar.h)',paths[2]])
    ordinary,wildcard=component.parse_dependencies(raw)
    if ordinary!=paths or wildcard!=[['include/config/arm64.h'],['include/config/foo.h','include/config/bar.h']]:
        raise AssertionError('final continuation or multiple optional headers parsed incorrectly')
    results.append('final-continued-line-blank-terminator-multiple-wildcards')
    if component.parse_dependencies('deps_init.o := one.h two.h\n')!=(['one.h','two.h'],[]):
        raise AssertionError('noncontinued dependency assignment differs')
    results.append('single-logical-line')
    if component.parse_dependencies('deps_init.o := '+SLASH+'\n a.h '+SLASH+'\n')!=(['a.h'],[]):
        raise AssertionError('continued final line at EOF differs')
    results.append('final-continued-line-EOF')
    malformed={
      'no-assignment':'cmd_init.o := clang-14\n',
      'duplicate-assignment':'deps_a.o := a.h\ndeps_b.o := b.h\n',
      'empty-assignment':'deps_init.o := '+SLASH+'\n\n',
      'unclosed-wildcard':'deps_init.o := a.h $(wildcard include/config/a.h\n',
      'nested-expression':'deps_init.o := a.h $(wildcard $(unknown))\n',
      'unresolved-variable':'deps_init.o := a.h $(unknown)\n',
      'unknown-function':'deps_init.o := a.h $(shell echo bad)\n',
      'bare-final-backslash':'deps_init.o := a.h '+SLASH,
      'escape-before-space':'deps_init.o := a'+SLASH+' b.h\n',
      'space-after-continuation':'deps_init.o := a.h '+SLASH+' \n b.h\n',
      'literal-backslash-n':'deps_init.o := a.h '+SLASH+'n b.h\n',
      'trailing-expression':'deps_init.o := a.h $(wildcard include/config/a.h)$(other)\n',
      'make-semicolon':'deps_init.o := a.h; echo bad\n',
      'unsupported-glob':'deps_init.o := a.h $(wildcard include/config/*.h)\n'}
    for label,text in malformed.items():
        rejected(component.parse_dependencies,text);results.append('reject-'+label)
    source=work/'source';objects=work/'objects';compiler=work/'compiler'
    compiler.mkdir()
    for base,name in [(source,name) for name in paths]+[(objects,name) for name in
            ('include/generated/autoconf.h','include/config/auto.conf','.config')]:
        path=base/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(('fixture-only '+name+'\n').encode())
    # Actual fixdep excludes init.c from deps_; the unique source_ assignment
    # binds that required primary TU to the same object as cmd_ and deps_.
    raw=continued([paths[1],'$(wildcard include/config/arm64.h)',
        '$(wildcard include/config/foo.h include/config/bar.h)',paths[2]],source/paths[0])
    if paths[0] in component.parse_dependencies(raw)[0]:raise AssertionError('regression fixture accidentally duplicates primary TU in deps')
    if component.source_dependency(raw,source)!=(source/paths[0]).as_posix():raise AssertionError('actual-format primary TU not bound')
    results.append('actual-format-separate-primary-source-not-in-deps')
    cmd=objects/component.CMD;cmd.parent.mkdir(parents=True,exist_ok=True);cmd.write_text(raw)
    closure=component.dependency_closure(source,objects,cmd,False,compiler)
    if len(closure['files_sha256'])!=6 or len(closure['optional_config_headers_absent'])!=3:
        raise AssertionError('fixture required/generated/optional header closure differs')
    results.append('strict-fixture-source-generated-optional-closure')
    source_line='source_'+component.TARGET+' := '+(source/paths[0]).as_posix()+'\n'
    primary_bad={
      'missing-source':raw.replace(source_line,''),
      'duplicate-source':raw+source_line,
      'wrong-source-object':raw.replace('source_'+component.TARGET,'source_arch/arm64/mm/other.o'),
      'wrong-deps-object':raw.replace('deps_'+component.TARGET,'deps_arch/arm64/mm/other.o'),
      'wrong-command-object':raw.replace('cmd_'+component.TARGET,'cmd_arch/arm64/mm/other.o'),
      'wrong-source':raw.replace(source_line,'source_'+component.TARGET+' := '+(source/'other.c').as_posix()+'\n'),
      'relative-source':raw.replace(source_line,'source_'+component.TARGET+' := '+paths[0]+'\n'),
      'malformed-source':raw.replace(source_line,'source_'+component.TARGET+' := $(source)/init.c\n'),
      'multiple-source-paths':raw.replace(source_line,source_line.rstrip()+' second.c\n'),
      'missing-kernel-command':raw.replace('-D__KERNEL__','-DNOT_KERNEL')}
    for label,text in primary_bad.items():
        rejected(component.source_dependency,text,source);results.append('reject-'+label)
    for label,lines,enabled in (
      ('missing-required-header',[paths[1]],False),
      ('missing-enabled-component',paths[1:],True),
      ('outside-root-path',[*paths[1:],'../outside.h'],False),
      ('outside-root-optional',[*paths[1:],'$(wildcard ../outside-missing.h)'],False),
      ('missing-required-file',[*paths[1:],'absent.h'],False)):
        cmd.write_text(continued(lines,source/paths[0]));rejected(component.dependency_closure,source,objects,cmd,enabled,compiler)
        results.append('reject-'+label)
    # Dummy bytes certify capture behavior only, never an ELF/Kbuild verdict.
    cmd.write_text(raw);object_file=objects/component.TARGET;object_file.write_bytes(b'fixture-object-not-executable')
    proof=work/'proof';component.preserve_kbuild(objects,proof)
    for name in (component.TARGET,component.CMD,'.config','include/generated/autoconf.h','include/config/auto.conf'):
        if (proof/'kbuild'/name).read_bytes()!=(objects/name).read_bytes():raise AssertionError('early proof capture differs')
    # A subsequent gate rejection must not remove already captured bytes.
    cmd.write_text(continued([*paths[1:],'../outside.h'],source/paths[0]))
    rejected(component.dependency_closure,source,objects,cmd,False,compiler)
    if (proof/'kbuild'/component.CMD).read_text()!=raw:raise AssertionError('failed validation lost original proof bytes')
    results.append('capture-survives-later-gate-rejection')
    partial=work/'partial';partial.mkdir();(partial/'.config').write_bytes(b'partial config')
    component.preserve_kbuild(partial,work/'partial-proof')
    captured=json.loads((work/'partial-proof/kbuild-capture.json').read_text())
    if list(captured['files_sha256'])!=['.config']:raise AssertionError('partial failed-compile capture differs')
    results.append('partial-compile-proof-retained')
    return results


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();private=(ROOT/'note10/private').resolve();output=args.output.resolve()
    if args.output.exists() or args.output.is_symlink() or output==private or not output.is_relative_to(private):
        raise ValueError('fresh project-private parser proof output required')
    output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='v55-dependencies-',dir=output.parent) as temporary:
        checks=cases(Path(temporary))
    result={'schema':1,'passed':True,'cases':checks,'case_count':len(checks),
      'fixture_kind':'generated fixture of preserved actual Kbuild source_/deps_/cmd_ layout',
      'fixture_bytes_are_actual_kernel_proof':False,'compiler_or_native_program_executed':False,
      'old_wrapper_preparer_or_v54_suites_replayed':False,
      'source_sha256':{path.name:hashlib.sha256(path.read_bytes()).hexdigest() for path in
        (Path(__file__),Path(component.__file__))}}
    output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
    print(json.dumps({'passed':True,'dependency_parser_cases':len(checks)}))


if __name__=='__main__':main()
