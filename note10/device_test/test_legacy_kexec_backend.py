"""One explicitly selected NEW production-core host batch. Never build/operate a phone."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tarfile
import traceback
import prepare_legacy_kexec_recovery as prepare

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
SCOPE='v128-legacy-kexec-recovery-new-only'
SCHEMA='note10-v128-new-backend-test-v1'
SOURCES=('legacy_kexec_core.h','legacy_kexec_core.c','legacy_kexec_fixture.c','legacy_kexec_loader.c',
         'legacy_kexec_syscall.S','kexec_recovery_park.S','legacy_kexec_return.h','legacy_kexec_reservation.c',
         'legacy_kexec_marker.c','legacy_kexec_watchdog.c','prepare_legacy_kexec_recovery.py','test_legacy_kexec_backend.py')
ARCHIVE_SHA='46d6a563af04e0c2ed9c96c2a1af8cab2344b458c9554b09098e6a9e7219ae4c'


def file_sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--scope',required=True,choices=(SCOPE,));p.add_argument('--output',required=True,type=Path)
    p.add_argument('--compiler',required=True,type=Path)
    p.add_argument('--compiler-arg',action='append',default=[])
    p.add_argument('--archive',type=Path,default=ROOT/'note10/private/required-inputs/kernel-source-55f042627bb7030c93550faafa117674d32b21d1.tar.gz')
    a=p.parse_args();out=a.output.absolute();compiler=a.compiler.absolute();archive=a.archive.absolute()
    if out!=out.resolve() or out.exists() or not out.is_relative_to(ROOT/'note10/private'):
        p.error('canonical fresh private test output required')
    if not a.compiler.is_absolute() or compiler!=compiler.resolve() or not compiler.is_file():
        p.error('explicit canonical absolute compiler file required')
    if not archive.is_file() or archive.is_symlink():p.error('immutable pinned archive required')
    out.mkdir(parents=True,exist_ok=False)
    result=dict(schema=SCHEMA,scope=SCOPE,passed=False,run=1,selected=['new_reservation_loader_marker_watchdog_and_source_boundaries'],
                fixture_compiles=0,fixture_processes=0,old_methods_run=0,old_fixture_runs=0,CI=0,Image_builds=0,
                device_operations=[],source_sha256={name:file_sha(HERE/name) for name in SOURCES},
                compiler=dict(path=str(compiler),sha256=file_sha(compiler)),compiler_args=a.compiler_arg,
                physical_ready=False,XNU_execution_allowed=False)
    try:
        if file_sha(archive)!=ARCHIVE_SHA:raise ValueError('actual source archive pin differs')
        prefix='android_kernel_samsung_universal9820-55f042627bb7030c93550faafa117674d32b21d1/'
        with tarfile.open(archive,'r:gz') as tar:
            stock={name:tar.extractfile(prefix+name).read() for name in prepare.PINS}
        overlay=prepare.render(stock,'1'*32)
        init=overlay['arch/arm64/mm/init.c'];machine=overlay['arch/arm64/kernel/machine_kexec.c']
        reservation_call=init.index(b'    n10_early_kexec_destination();')
        if not init.index(b'\tdma_contiguous_reserve(')<reservation_call<init.index(b'\tmemblock_allow_resize();'):
            raise ValueError('new early reservation source phase differs')
        final=machine.index(b'    if (n10_kexec_final_return(kimage))')
        if not machine.index(b'kexec_list_flush(kimage);')<final<machine.index(b'\t/* Disable all DAIF exceptions. */')<machine.index(b'\tcpu_soft_restart('):
            raise ValueError('actual new final hook order differs')
        if b' default n' not in prepare.KCONFIG or b'CONFIG_NOTE10_LEGACY_KEXEC_RECOVERY_PROOF' not in init:
            raise ValueError('new backend not guarded/default off')
        bad=dict(stock);bad['arch/arm64/mm/init.c']=stock['arch/arm64/mm/init.c']+b'\n'
        try:prepare.render(bad,'1'*32)
        except ValueError:pass
        else:raise ValueError('new changed-source refusal missing')
        result['source_boundary_checks']=['early-after-CMA-before-allocator','late-after-flush-before-native-MMU-off','default-off','changed-source-refused']
        exe=out/('new-backend-fixture.exe' if __import__('os').name=='nt' else 'new-backend-fixture')
        command=[str(compiler),'-std=c11','-O0','-Wall','-Wextra','-Werror','-fno-stack-protector','-fno-builtin',
                 '-I',str(HERE),str(HERE/'legacy_kexec_fixture.c'),'-o',str(exe),*a.compiler_arg]
        (out/'compile-command.json').write_text(json.dumps(command,indent=2)+'\n',encoding='utf-8')
        result['fixture_compiles']=1
        built=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,timeout=120)
        (out/'compile.log').write_text(built.stdout+built.stderr,encoding='utf-8')
        if built.returncode:raise ValueError('NEW production-core fixture compile failed')
        result['fixture_processes']=1
        ran=subprocess.run([str(exe)],cwd=ROOT,capture_output=True,text=True,timeout=30)
        (out/'fixture.stdout').write_text(ran.stdout,encoding='utf-8');(out/'fixture.stderr').write_text(ran.stderr,encoding='utf-8')
        if ran.returncode:raise ValueError('NEW production-core fixture failed')
        row=json.loads(ran.stdout)
        if row.get('schema')!='note10-v128-new-backend-fixture-v1' or row.get('passed') is not True or row.get('hardware_operations')!=0:
            raise ValueError('new fixture result schema differs')
        result.update(passed=True,fixture=row,overlay_sha256={name:hashlib.sha256(raw).hexdigest() for name,raw in overlay.items()})
    except Exception:result['error']=traceback.format_exc()
    with (out/'result.json').open('x',encoding='utf-8',newline='\n') as stream:stream.write(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(passed=result['passed'],fixture_compiles=result['fixture_compiles'],fixture_processes=result['fixture_processes'])))
    return 0 if result['passed'] else 1


if __name__=='__main__':raise SystemExit(main())
