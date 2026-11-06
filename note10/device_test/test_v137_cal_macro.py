"""One NEW CAL kernel-current macro and137 producer/consumer boundary batch."""
import argparse,json,re,subprocess,sys
from pathlib import Path
sys.dont_write_bytecode=True
from v130_contract import ROOT,private,ordinary,digest,hexid,save
import v137_prepare as prepare
import v137_build as build
import v137_cycle as cycle
from v135_metadata import encode_public
HERE=Path(__file__).resolve().parent
CURRENT_HEADER_SHA='848c2a2e0a262d970e60e201fbcbea7cac82d374ef665da4c666283f27595f54'
PRIOR_FILE_SHA='a9ee17fc54043940cc0f4caba43fd201a07e39a0245a8bcb968711cca389bbd5'
PRIOR_RESULT_SHA='c92d782f5f03287a15dc545a2b69ce1d3812e6350a2a5b31f8a811626ff5a0a4'
C_PREFIX=r'''
#include <assert.h>
#include <errno.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <string.h>
typedef uint32_t u32;
struct device {int id;};
struct task_struct {int marker;};
static struct task_struct n137_task;
static struct task_struct *get_current(void){return &n137_task;}
#define READ_ONCE(x) (x)
#define WRITE_ONCE(x,v) ((x)=(v))
#define smp_store_release(p,v) (*(p)=(v))
#define smp_load_acquire(p) (*(p))
#define ARRAY_SIZE(a) (sizeof(a)/sizeof((a)[0]))
struct mutex {int held;};
#define DEFINE_MUTEX(n) struct mutex n={0}
static int mutex_trylock(struct mutex *p){if(p->held)return 0;p->held=1;return 1;}
static void mutex_unlock(struct mutex *p){assert(p->held);p->held=0;}
typedef struct {int held;} spinlock_t;
#define DEFINE_SPINLOCK(n) spinlock_t n={0}
#define spin_lock_irqsave(p,f) do{assert(!(p)->held);(f)=0;(p)->held=1;}while(0)
#define spin_unlock_irqrestore(p,f) do{assert((p)->held);(void)(f);(p)->held=0;}while(0)
#define N10_KEXEC_BUILD_ID "0123456789abcdef0123456789abcdef"
#define pr_emerg(...) ((void)0)
#define PMUCAL_READ 0
struct pmucal_seq {u32 access_type;uintptr_t base_pa;void *base_va;u32 offset,mask;};
struct pmucal_dbg_info {u32 emul_offset,emul_bit,emul_en,emul_enabled;};
struct pmucal_pd {u32 id;char *name;struct pmucal_seq *status;u32 num_status;struct pmucal_dbg_info *dbg;};
static u32 n137_pmu[0x3000/4];static unsigned int n137_reads;
static struct pmucal_pd pmucal_pd_list[7];static unsigned int pmucal_pd_list_size=7;
static struct pmucal_seq n137_status[7];static struct pmucal_dbg_info n137_debug[7];
static u32 readl(void *p){uintptr_t n137_at=(uintptr_t)p,n137_base=(uintptr_t)n137_pmu;assert(n137_at>=n137_base && n137_at+sizeof(u32)<=n137_base+sizeof(n137_pmu));n137_reads++;return *(u32 *)p;}
'''
C_MAIN=r'''
int main(void)
{
 unsigned int n137_index;struct n136_detail n137_detail={0};
 assert(current==&n137_task);
 for(n137_index=1;n137_index<=2;n137_index++){
  u32 n137_offset=n137_index==1?0x1d00:0x1d80;
  n137_status[n137_index]=(struct pmucal_seq){PMUCAL_READ,0x15860000,n137_pmu,n137_offset+4,1};
  n137_debug[n137_index].emul_offset=n137_offset+12;
  pmucal_pd_list[n137_index]=(struct pmucal_pd){n137_index,n137_index==1?"blkpwr_npu0":"blkpwr_npu1",&n137_status[n137_index],1,&n137_debug[n137_index]};
 }
 /* Every changed local-state assignment/comparison under kernel current. */
 assert(n136_cal_begin(N136_NPU_DOMAINS,&n137_detail)==0 && n137_reads==6 && n137_detail.state==0);
 n136_cal_end(N136_NPU_DOMAINS,false);
 n137_pmu[0x1d00/4]=n137_pmu[0x1d04/4]=n137_pmu[0x1d80/4]=n137_pmu[0x1d84/4]=1;
 assert(n136_cal_begin(N136_NPU_DOMAINS,&n137_detail)==1 && n137_detail.state==1);n136_cal_end(N136_NPU_DOMAINS,false);
 n137_pmu[0x1d80/4]=n137_pmu[0x1d84/4]=0;
 assert(n136_cal_begin(N136_NPU_DOMAINS,&n137_detail)==-EIO && !strcmp(n137_detail.reason,"domain-mixed") && n137_detail.state==1 && n137_detail.aux==0);
 n137_status[1].mask=15;
 assert(n136_cal_begin(N136_NPU_DOMAINS,&n137_detail)==-ENODEV);
 assert(current==&n137_task);return 0;
}
'''


def new_protocol_inputs():
    # Exercise only the NEW wrapper. Do not call immutable136's passed render.
    original=prepare.retained.render
    raw=(HERE/'v136_cal.inc').read_bytes()
    prepare.retained.render=lambda stock,identity,source128:{prepare.CAL_PATH:raw,'synthetic-marker':b'N10XNU136 id=synthetic'}
    try:output=prepare.render({},'a'*32,HERE)
    finally:prepare.retained.render=original
    cal=output[prepare.CAL_PATH]
    assert not re.search(rb'\bcurrent\b',cal) and len(re.findall(rb'\bn137_snapshot_state\b',cal))==7
    assert output['synthetic-marker']==b'N10XNU137 id=synthetic' and b'N10XNU137' in cal and b'N10XNU136' not in cal
    loader=build.pid1_source()
    assert set(re.findall(rb'N10XNU[0-9]+',loader))=={b'N10XNU137'}
    # Direct actual137 entry boundary, including the nested producer call.
    source=(HERE/'v137_build.py').read_text()
    assert source.count('        loader=pid1_source()')==1
    assert source.index('        loader=pid1_source()')<source.index("        (out/'v137_loader.c').write_bytes(loader)")<source.index("result['PID1_source_sha256']=digest(loader)")<source.index("'00-new-PID1'")
    workflow=(ROOT/build.WORKFLOW).read_text()
    assert '  v137-cal-kernel-macro:' in workflow and 'python -B note10/device_test/v137_build.py' in workflow
    identity,cycle_id='a'*32,'b'*32
    text=('N10XNU137 id='+identity+' cycle='+cycle_id+' stage=begin\nN10XNU137 id='+identity+' stage=npu-power-off errno=-16 owner=synthetic\n').encode()
    assert cycle.decode({'synthetic':text},identity,cycle_id)['gate_refusals']==[dict(stage='npu-power-off',errno=-16,owner='synthetic')]
    assert not cycle.decode({'synthetic':text.replace(b'N10XNU137',b'N10XNU135')},identity,cycle_id)['previous_boot_build_cycle_observed']
    barrier=('N10XNU135 id='+identity+' cycle='+cycle_id+' stage=begin JUNK\nN10XNU137 id='+identity+' final_qualified=1 EL1_preserved=1 actual_XNU_pending=1\n').encode()
    assert not cycle.decode({'synthetic':text+barrier},identity,cycle_id)['final_hook_qualified_observed']
    return cal


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('output','cc','retained-context','kernel-current-header'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--retained-context-sha256',required=True);a=p.parse_args();out=private(a.output)
    if out.exists():p.error('fresh137 new-only output required')
    previous_raw=ordinary(a.retained_context).read_bytes()
    if a.retained_context_sha256!=PRIOR_FILE_SHA or digest(previous_raw)!=hexid(a.retained_context_sha256):raise ValueError('exact accepted136 host/fixture PASS required')
    previous=json.loads(previous_raw);build.retained_continuation(previous,build.RETAINED_SOURCE_SHA256)
    if digest(json.dumps(previous,sort_keys=True,separators=(',',':')).encode())!=build.RETAINED_CONTEXT_SHA256 or previous['delta_NEW_PASS']['result_sha256']!=PRIOR_RESULT_SHA:raise ValueError('retained136 exact provenance differs')
    current_header=ordinary(a.kernel_current_header).read_bytes()
    if digest(current_header)!=CURRENT_HEADER_SHA:raise ValueError('exact pinned arm64 current header required')
    definitions=re.findall(rb'(?m)^#define[ \t]+current[ \t]+get_current\(\)[ \t]*$',current_header)
    if len(definitions)!=1:raise ValueError('exact native kernel current definition required')
    current_source=build.source_pins();out.mkdir(parents=True)
    result=dict(schema='note10-v137-cal-macro-result-v1',scope=build.SCOPE,passed=False,source_sha256={k:current_source[k] for k in build.NEW_FILES},retained136_result_sha256=PRIOR_RESULT_SHA,
        retained136_source_map_sha256='50d591e3bfeb1e6a9e2f67e70b3a7015b86e1014c6497fc0c4079d95ae2f47cd',compiler_invocations=0,fixture_processes=0,old_tests_replayed=0,retained_overlay_render_invocations=0,
        Image_reads=0,raw_kernel_reads=0,adapter_reads=0,compressions=0,device_operations=[])
    def persist(): (out/'result.json').write_text(json.dumps(result,indent=2)+'\n',newline='\n')
    try:
        cal=new_protocol_inputs();result['NEW_protocol_cases_passed']=True;result['NEW_wrapper_invocations']=1
        (out/'v137-cal.inc').write_bytes(cal);result['native_CAL_sha256']=digest(cal)
        generated=(C_PREFIX+'\n'+definitions[0].decode()+'\n#include "v137-cal.inc"\n'+C_MAIN).encode();source=out/'new-cal-macro.c';source.write_bytes(generated)
        result['generated_C_file']=source.name;result['generated_C_sha256']=digest(generated);persist()
        include=out/'include/linux';include.mkdir(parents=True)
        for name in ('mutex.h','spinlock.h','smp.h','device.h','printk.h','string.h','types.h','errno.h','note10_legacy_kexec_build.h'):(include/name).write_text('/* synthetic native dependency */\n',newline='\n')
        (include/'v136_terminal.h').write_bytes((HERE/'v136_terminal.h').read_bytes())
        macros=['-DCONFIG_'+key+'=1' for key,value in build.SETTINGS.items() if value=='y']
        executable=out/('new-cal-macro.exe' if sys.platform=='win32' else 'new-cal-macro')
        command=[str(ordinary(a.cc)),'-std=gnu11','-O2','-Wall','-Wextra','-Werror','-Wstrict-prototypes','-Wno-unused-function','-ferror-limit=0',*macros,'-I',str(out/'include'),str(source),'-o',str(executable)]
        result['compiler_invocations']=1;persist()
        with (out/'compile.log').open('xb') as log:subprocess.run(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=60)
        result['fixture_processes']=1;persist()
        with (out/'fixture.log').open('xb') as log:subprocess.run([str(executable)],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=15)
        result['passed']=True;result_raw=(json.dumps(result,indent=2)+'\n').encode()
        delta=dict(schema='note10-v137-cal-kernel-macro-pass-v1',scope=build.SCOPE,passed=True,result_sha256=digest(result_raw),source_sha256=result['source_sha256'])
        candidate=dict(schema='note10-v137-public-terminal-continuation-v1',scope=build.SCOPE,passed=True,retained_source_commit=build.RETAINED_COMMIT,retained_terminal_PASS=previous,delta_NEW_PASS=delta,source_sha256=current_source)
        build.continuation(candidate,current_source);encoded=encode_public(candidate)
        (out/'result.json').write_bytes(result_raw);save(out/'public-cal-macro-continuation.json',candidate);(out/'public-cal-macro-continuation.txt').write_text(encoded+'\n',encoding='ascii',newline='\n')
    except BaseException:
        import traceback
        result['error']=traceback.format_exc();persist();raise
    print(json.dumps(dict(passed=True,compiler_invocations=1,fixture_processes=1,old_tests_replayed=0)))


if __name__=='__main__':main()
