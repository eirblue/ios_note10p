"""Focused new full-path production-C, adapter and strict decoder cases only."""
import argparse
import copy
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
sys.dont_write_bytecode=True
import prepare_xnu_runtime_observation as prepare
from decode_xnu_runtime_observation import decode
from decode_reservation import checksum

NATIVE_CASES=('minimum','different-base','upper-base','status-refused','below-minimum','bad-count','partial-reserved','invalid-page')
PARSER_CASES=('valid','missing','one-copy','duplicate','conflict','wrong-id','wrong-generation','wrong-phase',
 'pm-claim','bad-checksum','truncated','wrong-payload','wrong-size','wrong-geometry','wrong-base','bad-bound',
 'materialized','ownership','wrong-kernel-offset','wrong-entry-offset','wrong-end-offset','wrong-VA','wrong-map','wrong-synthetic')
PREPARER_CASES=('valid-full-composition','duplicate','default-off-byte-identical','body-guard','init-pin','stage-provider','stage-header','timer-provider','window-provider','window-core',
 'missing-timer-composition','auto-return-disabled','trace-disabled','wrong-payload','wrong-source-hash','stray-config',
 'unsafe-fixture-read','unsafe-fixture-write')
PREFIX=r'''
#include <stdint.h>
#include <stdio.h>
#include <stdarg.h>
#include <stdlib.h>
#define __init
#define noinline __attribute__((noinline))
#define __used __attribute__((used))
#define PAGE_SHIFT 12
#define N10_RESERVE_BUILD_ID "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
typedef uint32_t u32;
static uint64_t n10_window_base;
static int n10_window_status;
static int scnprintf(char *out,size_t capacity,const char *format,...)
{
 va_list args;int result;va_start(args,format);result=vsnprintf(out,capacity,format,args);va_end(args);
 return result<0?result:((size_t)result>=capacity?(int)capacity-1:result);
}
static void pr_info(const char *format,...)
{
 va_list args;va_start(args,format);vprintf(format,args);va_end(args);
}
#define pr_err pr_info
'''
DRIVER=r'''
static void one(const char *name,uint64_t base,int status,unsigned long reserved,unsigned long count,unsigned long invalid)
{
 n10_window_base=base;n10_window_status=status;
 printf("CASE|%s\n",name);n10_observe_runtime_plan(reserved,count,invalid);
 if(n10_window_base!=base || n10_window_status!=status)abort();
}
int main(void)
{
 unsigned long pages=N10_RT_WINDOW>>PAGE_SHIFT;
 one("minimum",N10_RT_MIN_BASE,1,pages,pages,0);
 one("different-base",UINT64_C(0x100000000),1,pages,pages,0);
 one("upper-base",N10_RT_LIMIT-N10_RT_WINDOW,1,pages,pages,0);
 one("status-refused",N10_RT_MIN_BASE,0,pages,pages,0);
 one("below-minimum",N10_RT_MIN_BASE-N10_RT_BLOCK,1,pages,pages,0);
 one("bad-count",N10_RT_MIN_BASE,1,pages-1,pages-1,0);
 one("partial-reserved",N10_RT_MIN_BASE,1,pages-1,pages,0);
 one("invalid-page",N10_RT_MIN_BASE,1,pages,pages,1);
 return 0;
}
'''


def native_source(prepared):
    prepared=Path(prepared)/'arch/arm64/mm'
    reserve=(prepare.HERE/'xnu_reserve.c').read_bytes();start=reserve.index(b'static u32 n10_frame_checksum(')
    end=reserve.index(b'\n}',start)+2;checksum_source=reserve[start:end]
    header=(prepared/'runtime_relocation.h').read_bytes()
    geometry=(prepared/'note10_xnu_runtime_geometry.h').read_bytes()+(prepared/'note10_xnu_observation_geometry.h').read_bytes()
    parts=[]
    for name in ('runtime_relocation.c','note10_xnu_runtime_plan.c','note10_xnu_runtime_observation.c'):
        raw=(prepared/name).read_bytes()
        for include in (b'#include "runtime_relocation.h"\n',b'#include "note10_xnu_runtime_geometry.h"\n',b'#include "note10_xnu_observation_geometry.h"\n'):raw=raw.replace(include,b'')
        parts.append(raw)
    return PREFIX.encode()+header+geometry+checksum_source+b'\n'+b'\n'.join(parts)+DRIVER.encode()


def ram_frames(base):
    lines=[]
    for seq in (0,1):
        body=f'id={"a"*32} seq={seq} base={base:x} size=10000000 align=2000000 pages=65536 reserved=65536 invalid=0 shift=12'
        lines.append(f'N10RAM2 {body} checksum={checksum(body.encode()):08x}')
    return '\n'.join(lines)+'\n'


def frame(body):return 'N10XPO1 '+body+' checksum='+format(checksum(body.encode()),'08x')


def reject(call,*args,**kwargs):
    try:call(*args,**kwargs)
    except (ValueError,FileNotFoundError,UnicodeError):return True
    raise AssertionError('invalid new observation accepted')


def parser_cases(text,build):
    args=('a'*32,build['xnu_payload_sha256'],build['xnu_payload_size'],build[prepare.FLAG+'_geometry_sha256'])
    decode(text,*args);results={'valid':True}
    companion=[line for line in text.splitlines() if line.startswith('N10XPO1 ')]
    prefix='\n'.join(line for line in text.splitlines() if not line.startswith('N10XPO1 '))+'\n'
    bodies=[line.split(' ',1)[1].rsplit(' checksum=',1)[0] for line in companion]
    changes={'wrong-id':('id='+'a'*32,'id='+'b'*32),'wrong-generation':('plan_generation=1','plan_generation=2'),
      'wrong-phase':('phase=late-init','phase=post-pm'),'pm-claim':('pm_completion_claimed=0','pm_completion_claimed=1'),
      'wrong-payload':('payload_sha='+args[1],'payload_sha='+'0'*64),'wrong-size':('payload_size='+str(args[2]),'payload_size=1'),
      'wrong-geometry':('geometry_sha='+args[3],'geometry_sha='+'0'*64),'wrong-base':('base=80000000','base=100000000'),
      'bad-bound':('base=80000000','base=ffffffffffffffff'),'materialized':('materialized=0','materialized=1'),
      'ownership':('ownership=0','ownership=1'),'wrong-kernel-offset':('kernel_offset=1004000','kernel_offset=0'),
      'wrong-entry-offset':('entry_offset=1340490','entry_offset=0'),'wrong-end-offset':('end_offset=22b0000','end_offset=0'),
      'wrong-VA':('virt=fffffff006000000','virt=fffffff000000000'),'wrong-map':('mapped=7','mapped=8'),
      'wrong-synthetic':('synthetic=1','synthetic=0')}
    for name in PARSER_CASES[1:]:
        chosen=list(companion)
        if name=='missing':chosen=[]
        elif name=='one-copy':chosen=chosen[:1]
        elif name=='duplicate':chosen=[chosen[0],chosen[0]]
        elif name=='conflict':chosen[1]=frame(bodies[1].replace('base=80000000','base=100000000'))
        elif name=='bad-checksum':chosen[0]=chosen[0][:-1]+('0' if chosen[0][-1]!='0' else '1')
        elif name=='truncated':chosen[0]=chosen[0][:80]
        else:chosen=[frame(body.replace(*changes[name])) for body in bodies]
        results[name]=reject(decode,prefix+'\n'.join(chosen)+'\n',*args)
    return results


def preparer_cases(artifact,build,workspace):
    results={};before=build[prepare.FLAG+'_before_sha256']
    composition=dict(build['cpu_pm_roundtrip_snapshot_sha256']);composition.update(build['cpu_pm_notifier_trace_prepared_sha256'])
    def fixture(label):
        root=workspace/label;source=root/'source';output=root/'output';output.mkdir(parents=True)
        for mapping,folder in ((composition,'cpu-pm-roundtrip-prepared'),(build['cpu_pm_notifier_trace_prepared_sha256'],'cpu-pm-notifier-trace-prepared'),(before,prepare.BASE)):
            for name in mapping:
                if name in build['cpu_pm_notifier_trace_prepared_sha256'] and folder=='cpu-pm-roundtrip-prepared':continue
                original=prepare.safe_path(artifact/folder,name)
                target=prepare.safe_path(source,name,exists=False)
                target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(original.read_bytes())
        return source,output
    manifest=prepare.HERE/'xnu_runtime_plan_payload.json'
    source,output=fixture('enabled');report=copy.deepcopy(build)
    report['reservation_source_sha256']=build['reservation_source_before_runtime_sha256']
    result=prepare.prepare(source,output,report,manifest,True)
    if result[prepare.FLAG] is not True:raise AssertionError('full adapter did not opt in')
    results['valid-full-composition']=True;results['duplicate']=reject(prepare.prepare,source,output,report,manifest,True)
    source,output=fixture('default-off')
    unchanged={p.relative_to(source).as_posix():p.read_bytes() for p in source.rglob('*') if p.is_file()}
    if prepare.prepare(source,output,report,manifest)!={} or unchanged!={p.relative_to(source).as_posix():p.read_bytes() for p in source.rglob('*') if p.is_file()}:
        raise AssertionError('default-off full adapter changed prior source/schema')
    results['default-off-byte-identical']=True
    for name in PREPARER_CASES[3:-2]:
        source,output=fixture(name);report=copy.deepcopy(build)
        report['reservation_source_sha256']=build['reservation_source_before_runtime_sha256']
        mutations={'body-guard':prepare.RESERVE,'init-pin':prepare.canonical.INIT,'stage-provider':'arch/arm64/mm/note10_xnu_payload_stage.c',
          'stage-header':'arch/arm64/mm/note10_xnu_payload_stage.h','timer-provider':'arch/arm64/mm/note10_pm_timer_roundtrip.c',
          'window-provider':'arch/arm64/mm/note10_xnu_window_access.c','window-core':'arch/arm64/mm/note10_window_access_core.h','stray-config':prepare.KCONFIG}
        if name in mutations:
            path=source/mutations[name];path.write_bytes(path.read_bytes()+(prepare.BLOCK if name=='stray-config' else b'\n'))
        elif name=='missing-timer-composition':report['cpu_pm_roundtrip_snapshot_sha256'].pop('arch/arm64/mm/note10_pm_timer_roundtrip.c')
        elif name=='auto-return-disabled':report['auto_return_diagnostic']=False
        elif name=='trace-disabled':report['cpu_pm_notifier_trace']=False
        elif name=='wrong-payload':report['xnu_payload_sha256']='0'*64
        elif name=='wrong-source-hash':report['reservation_source_sha256']='0'*64
        original={p.relative_to(source).as_posix():p.read_bytes() for p in source.rglob('*') if p.is_file()}
        try:results[name]=reject(prepare.prepare,source,output,report,manifest,True)
        except Exception as error:raise AssertionError('preparer case '+name+': '+str(error)) from error
        if original!={p.relative_to(source).as_posix():p.read_bytes() for p in source.rglob('*') if p.is_file()}:raise AssertionError('failed adapter mutated old provider')
    results['unsafe-fixture-read']=reject(prepare.safe_path,artifact/prepare.BASE,'../build-result.json')
    results['unsafe-fixture-write']=reject(prepare.safe_path,workspace/'new-source','../../escape',False)
    return results


def verify_native_log(raw,build):
    chunks=re.split(r'(?m)^CASE\|([^\r\n]+)\r?\n',raw.decode('ascii'))
    if chunks[0] or tuple(chunks[1::2])!=NATIVE_CASES:raise ValueError('new native case inventory differs')
    native={};valid=None
    for index,name in enumerate(chunks[1::2]):
        text=chunks[2+index*2];base=(0x80000000,0x100000000,(1<<40)-0x10000000)[index] if index<3 else 0x80000000
        text=ram_frames(base)+text;args_decode=('a'*32,build['xnu_payload_sha256'],build['xnu_payload_size'],build[prepare.FLAG+'_geometry_sha256'])
        if index<3:
            decode(text,*args_decode)
            if index==0:valid=text
        else:reject(decode,text,*args_decode)
        native[name]=True
    return native,valid


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--artifact',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);parser.add_argument('--cc',default='clang')
    args=parser.parse_args();artifact=args.artifact.resolve();output=args.output.resolve();private=(prepare.ROOT/'note10/private').resolve()
    if args.output.exists() or args.output.is_symlink() or output==private or not output.is_relative_to(private):raise ValueError('fresh private observation output required')
    # Native proof may live under the artifact; copied preparer work never does.
    output.mkdir(parents=True);temporary=output/'tmp';temporary.mkdir();env=dict(os.environ,TMP=str(temporary),TEMP=str(temporary),TMPDIR=str(temporary))
    build=json.loads((artifact/'build-result.json').read_text(encoding='utf8'));raw=native_source(artifact/prepare.PREPARED);(output/'native.c').write_bytes(raw)
    executable=output/('native.exe' if os.name=='nt' else 'native')
    compiled=subprocess.run([args.cc,'-std=c11','-O2','-Wall','-Wextra','-Werror',str(output/'native.c'),'-o',str(executable)],capture_output=True,env=env,timeout=120)
    (output/'compile.log').write_bytes(compiled.stdout+compiled.stderr)
    if compiled.returncode:raise ValueError('new production planner/companion native compile failed')
    ran=subprocess.run([str(executable)],capture_output=True,env=env,timeout=30);(output/'native.log').write_bytes(ran.stdout+ran.stderr)
    if ran.returncode or ran.stderr:raise ValueError('new production planner companion native cases failed')
    native,valid=verify_native_log(ran.stdout,build)
    parsers=parser_cases(valid,build)
    with tempfile.TemporaryDirectory(prefix='xnu-observation-adapter-',dir=private) as temp:
        workspace=Path(temp).resolve()
        if workspace.is_relative_to(artifact) or artifact.is_relative_to(workspace):raise ValueError('adapter fixtures must be disjoint from artifact')
        preparers=preparer_cases(artifact,build,workspace)
    result={'passed':True,'native_cases':native,'parser_cases':parsers,'preparer_cases':preparers,
      'source_sha256':{name:prepare.sha((prepare.HERE/name).read_bytes()) for name in prepare.SOURCES},
      'compiled_files_sha256':{name:prepare.sha((output/name).read_bytes()) for name in ('native.c',executable.name,'compile.log','native.log')},
      'actual_production_planner_and_companion_executed':True,'physical_memory_or_hardware_accessed':False,
      'old_v54_v55_or_PM_suites_replayed':False,'materialized':False,'device_operations':[]}
    (output/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')


if __name__=='__main__':main()
