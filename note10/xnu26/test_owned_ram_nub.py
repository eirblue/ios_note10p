"""One new factory/actual-nub host transaction batch; no old suite."""
import json
import os
from pathlib import Path
import subprocess

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
CASE_NAMES=('private_copy_isolated_owned_and_initially_unstarted','requested_copy_limit_before_allocation','OSData_width_before_allocation','invalid_source_geometry_before_allocation','OSData_object_allocation_failure','OSData_initialization_failure_cleanup','nub_object_allocation_failure_cleanup','nub_initialization_failure_cleanup')


def command(output,compiler):
    out=Path(output)
    return [str(compiler),'--driver-mode=g++','-std=c++17','-Wall','-Wextra','-Werror','-pthread','-DKERNEL=1','-I',str(out/'fixture-includes'),'-I',str(HERE),str(HERE/'note10_owned_ram_nub.cpp'),str(HERE/'note10_readonly_ram_block_device.cpp'),str(HERE/'owned_ram_nub_fixture.cpp'),'-o',str(out/'owned-ram-nub-fixture.exe')]


def save(path,value):
    with Path(path).open('x',encoding='utf-8')as stream:json.dump(value,stream,sort_keys=True);stream.write('\n')


def run(output,compiler_argv):
    out=Path(output)
    if compiler_argv!=command(out,compiler_argv[0]):raise ValueError('exact new host compile argv required')
    for name in ('IOKit/storage/IOBlockStorageDevice.h','IOKit/storage/IOStorage.h','IOKit/IOLocks.h','libkern/c++/OSData.h'):
        target=out/'fixture-includes'/name;target.parent.mkdir(parents=True,exist_ok=True)
        with target.open('x',encoding='utf-8')as stream:stream.write('#include "owned_ram_nub_fixture_support.h"\n')
    env=dict(os.environ);env['PATH']=str(Path(compiler_argv[0]).parent)+os.pathsep+env.get('PATH','');completed=[]
    try:
        save(out/'COMPILE-STARTED.json',dict(attempt=1,argv=compiler_argv))
        with (out/'compile.stdout').open('xb')as stdout,(out/'compile.stderr').open('xb')as stderr:done=subprocess.run(compiler_argv,cwd=ROOT,env=env,stdout=stdout,stderr=stderr,timeout=120,check=False)
        save(out/'COMPILE-COMPLETED.json',dict(returncode=done.returncode));done.check_returncode()
        if sum((out/name).stat().st_size for name in ('compile.stdout','compile.stderr'))>1048576:raise ValueError('compile log admission cap')
        argv=[str(out/'owned-ram-nub-fixture.exe')];save(out/'C-FIXTURE-STARTED.json',dict(attempt=1,argv=argv))
        with (out/'fixture.stdout').open('xb')as stdout,(out/'fixture.stderr').open('xb')as stderr:done=subprocess.run(argv,cwd=ROOT,env=env,stdout=stdout,stderr=stderr,timeout=120,check=False)
        save(out/'C-FIXTURE-COMPLETED.json',dict(returncode=done.returncode));raw=(out/'fixture.stdout').read_bytes()
        if len(raw)+(out/'fixture.stderr').stat().st_size>65536:raise ValueError('fixture log admission cap')
        lines=raw.decode().splitlines();completed=[line[5:]for line in lines if line.startswith('PASS|')];done.check_returncode();results=[json.loads(line[7:])for line in lines if line.startswith('RESULT|')]
        if tuple(completed)!=CASE_NAMES or results!=[dict(groups=1,variants=8,assertions=8)]or len(lines)!=9:raise ValueError('exact eight new logical verdicts required')
    except BaseException as error:
        path=out/'fixture.stdout'
        if path.exists()and path.stat().st_size<=65536:
            completed=[line[5:]for line in path.read_text(errors='replace').splitlines()if line.startswith('PASS|')]
        error.fixture_progress=dict(groups=1,variants=8,assertions=8,completed_variants=len(completed),completed_assertions=len(completed),case_names=completed);raise
    return dict(groups=1,variants=8,assertions=8,completed_variants=8,completed_assertions=8,case_names=completed,host_compile_attempts=1,host_fixture_process_attempts=1,native_ABI_verified=False,runtime_backing_owner_verified=False,registered_provider=False,native_activation=False,physical_ready=False)
