'One NEW exact-context closing/drain/accounting batch, old DPU suites0.'
import argparse,json,re,subprocess,sys
from pathlib import Path
sys.dont_write_bytecode=True
from v130_contract import ROOT,private,ordinary,digest,hexid,save
from v135_metadata import encode_public
import v141_prepare as prepare
import v141_build as build
import v141_package as package
import v141_cycle as cycle
HERE=Path(__file__).resolve().parent
TASK_SHA='33d12411861aa26e309327a75a6f08965e7e3ace721f01dc912078f674d3c54b'
PREEMPT_SHA='386da1a2be5458d2a6e172286987ce9fe6e8383d50377ad42a220c7026c228af'
PRIOR_FILE_SHA='abd869d3b41f3515586d354926a88f59b527317a31ece54ee4a88d67a7d549c4'
PRIOR_RESULT_SHA='c751606ec8a12e70e036d075b9d5ae588a3e013923827f64c8378be03e52eafd'
C_PREFIX=r'''
#include <assert.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <string.h>
#include <errno.h>
#undef ETIMEDOUT
#define ETIMEDOUT 110
#undef EALREADY
#define EALREADY 114
typedef uint64_t u64;
typedef int64_t s64;
#define ARRAY_SIZE(v) (sizeof(v)/sizeof((v)[0]))
#define N138_BUDGET_NS 250000000LL
#define N138_POLL_LIMIT 25000U
#define N10_KEXEC_BUILD_ID "0123456789abcdef0123456789abcdef"
struct task_struct {int id;unsigned int usage;};
static struct task_struct coordinator={1,1},worker={2,1},foreign={3,1},*fixture_task=&coordinator;
static struct task_struct *get_current(void){return fixture_task;}
#define current get_current()
static unsigned int fixture_preempt;
static unsigned int preempt_count(void){return fixture_preempt;}
#include <linux/preempt.h>
static bool fixture_irq_off;
static bool irqs_disabled(void){return fixture_irq_off;}
typedef struct {bool held;} spinlock_t;
static spinlock_t n138_lock;
#define spin_lock_irqsave(p,f) do{assert(!(p)->held);(p)->held=true;(f)=fixture_irq_off;fixture_irq_off=true;fixture_preempt+=PREEMPT_OFFSET;}while(0)
#define spin_unlock_irqrestore(p,f) do{assert((p)->held);fixture_preempt-=PREEMPT_OFFSET;fixture_irq_off=(bool)(f);(p)->held=false;}while(0)
static unsigned int task_gets,task_puts;
#define atomic_inc(p) do{assert(n138_lock.held);++*(p);task_gets++;}while(0)
static bool atomic_dec_and_test(unsigned int *value){assert(!n138_lock.held && *value>1);task_puts++;return --*value==0;}
void __put_task_struct(struct task_struct *task){(void)task;assert(false);}
#include <linux/native_task.h>
static s64 fixture_time;
static s64 ktime_get_ns(void){return fixture_time;}
static void udelay(unsigned int value){assert(!n138_lock.held);fixture_time+=(s64)value*1000;}
static void (*progress)(void);
static unsigned int reschedules,log_count;
static void cond_resched(void){assert(!n138_lock.held && !fixture_irq_off && fixture_preempt==0);reschedules++;if(progress)progress();}
static char logged_entry[65];static unsigned int logged_depth,logged_irq,logged_self;
static void fixture_log(const char *format,const char *build,const char *entry,unsigned int depth,unsigned int irq_state,unsigned int self)
{assert(!n138_lock.held && format && build && entry);log_count++;strncpy(logged_entry,entry,64);logged_entry[64]=0;logged_depth=depth;logged_irq=irq_state;logged_self=self;}
#define pr_emerg fixture_log
static struct {const char *reason;unsigned int state,aux;int value;} n138_detail;
/* N141_CONTEXT_DECLARATION */
static struct n138_context n138_contexts[64];
static unsigned int n138_active,n138_history,n138_polls;
static bool n138_closed,n138_seen,n138_aborting;
static s64 n138_deadline;
static bool n138_is_proof(void){return false;}
/* N141_CHANGED_ACCOUNTING */
#include "v141_admission.inc"
'''
C_MAIN=r'''
static void reset(void)
{
 fixture_task=&coordinator;fixture_preempt=0;fixture_irq_off=false;fixture_time=0;
 coordinator.usage=worker.usage=foreign.usage=1;task_gets=task_puts=0;
 n138_lock.held=false;memset(n138_contexts,0,sizeof(n138_contexts));memset(&n138_detail,0,sizeof(n138_detail));
 n138_active=n138_history=n138_polls=0;n138_closed=n138_seen=n138_aborting=false;n138_deadline=0;
 progress=NULL;reschedules=log_count=0;memset(logged_entry,0,sizeof(logged_entry));logged_depth=logged_irq=logged_self=0;
}
static void start_worker(unsigned int irq_state,const char *entry)
{fixture_task=&worker;fixture_preempt=irq_state;assert(n141_user_begin(entry));fixture_preempt=0;fixture_task=&coordinator;}
static void finish_process(void)
{
 struct task_struct *saved=current;
 fixture_task=&foreign;assert(!n141_user_begin("late_foreign"));
 fixture_task=&worker;fixture_preempt=PREEMPT_OFFSET;assert(n141_user_begin("normal_nested"));
 assert(task_gets==1 && worker.usage==2);n138_user_end();assert(worker.usage==2);n138_user_end();assert(worker.usage==1 && task_puts==1);fixture_preempt=0;fixture_task=saved;progress=NULL;
}
static void finish_irq(void)
{
 struct task_struct *saved=current;fixture_task=&worker;
 fixture_preempt=2*HARDIRQ_OFFSET;assert(!n141_user_begin("new_nested_irq"));
 fixture_preempt=SOFTIRQ_OFFSET;assert(!n141_user_begin("new_softirq"));
 fixture_preempt=NMI_OFFSET|HARDIRQ_OFFSET;assert(!n141_user_begin("new_nmi"));
 fixture_preempt=0;assert(!n141_user_begin("new_process_context"));
 fixture_preempt=HARDIRQ_OFFSET;assert(n141_user_begin("same_irq_nested"));n138_user_end();n138_user_end();
 fixture_preempt=0;fixture_task=saved;progress=NULL;
}
static void poison_then_finish(void){n138_history|=2;finish_process();}
static void finish_after_deadline(void){finish_process();fixture_time=N138_BUDGET_NS;}
static void coupling_expired(void){finish_process();fixture_time=N138_BUDGET_NS-1000;}
int main(void)
{
 s64 deadline;unsigned int credits,index;
 reset();start_worker(0,"process_writer");progress=finish_process;
 assert(n141_display_close()==0 && n138_seen && n138_closed && !n138_aborting && !n138_active && !n138_history);
 assert(task_gets==1 && task_puts==1 && worker.usage==1);
 assert(reschedules==1 && fixture_time==10000 && n138_polls==N138_POLL_LIMIT-1 && !log_count);
 deadline=n138_deadline;credits=n138_polls;assert(!n141_user_begin("after_success") && n141_deadline_check()==0);
 assert(n138_deadline==deadline && n138_polls==credits);fixture_time=deadline;assert(n141_deadline_check()==-ETIMEDOUT);assert(n141_display_close()==-EALREADY && n138_deadline==deadline);
 reset();start_worker(HARDIRQ_OFFSET,"irq_writer");progress=finish_irq;
 assert(n141_display_close()==0 && n138_active==0 && !n138_history && !n138_aborting && task_gets==1 && task_puts==1 && worker.usage==1);
 reset();assert(n141_user_begin("self_writer"));assert(n141_display_close()==-EBUSY && !reschedules && n138_active==1);
 assert(coordinator.usage==2 && task_gets==1 && task_puts==0);
 assert(n138_closed && !strcmp(n138_detail.reason,"admission-self") && logged_self==1 && logged_depth==1);
 n138_user_end();assert(coordinator.usage==1 && task_puts==1);assert(!n138_active && n138_closed);assert(!n141_user_begin("new_after_self_failure"));
 reset();start_worker(0,"poisoned_writer");n138_history=2;
 assert(n141_display_close()==-EBUSY && n138_history==2 && n138_active==1 && !reschedules);
 reset();start_worker(0,"racing_writer");progress=poison_then_finish;
 assert(n141_display_close()==-EBUSY && n138_history==2 && !n138_active && n138_closed && !log_count);
 reset();start_worker(0,"stuck_writer");assert(n141_display_close()==-ETIMEDOUT);
 assert(fixture_time==N138_BUDGET_NS && reschedules==N138_POLL_LIMIT && n138_polls==0 && n138_active==1 && n138_closed);
 assert(worker.usage==2 && task_gets==1 && task_puts==0);
 assert(log_count==1 && !strcmp(logged_entry,"stuck_writer") && logged_depth==1 && logged_irq==0 && logged_self==0);
 assert(n141_display_close()==-EALREADY && !n138_polls);finish_process();assert(worker.usage==1 && !n138_active && n138_closed);
 reset();start_worker(0,"deadline_writer");progress=finish_after_deadline;
 assert(n141_display_close()==-ETIMEDOUT && !n138_active && n138_closed && !log_count);
 reset();start_worker(0,"last_budget_writer");progress=coupling_expired;
 assert(n141_display_close()==-ETIMEDOUT && n138_deadline==N138_BUDGET_NS);
 reset();start_worker(0,"context_writer");fixture_irq_off=true;
 assert(n141_display_close()==-EBUSY && !reschedules && n138_active==1 && n138_closed);
 reset();n138_contexts[0].task=&worker;n138_contexts[0].depth=1;n138_contexts[0].entry="broken_count";n138_contexts[0].task_owned=true;worker.usage=2;
 assert(n141_display_close()==-EBUSY && n138_history==1 && n138_contexts[0].depth==1);
 reset();n138_contexts[0].task=&worker;n138_contexts[0].task_owned=true;worker.usage=2;assert(n141_display_close()==-EBUSY && n138_history==1 && worker.usage==2 && !task_puts);
 reset();assert(n141_display_close()==0);n138_polls=0;
 assert(n141_deadline_check()==-ETIMEDOUT && n138_closed && n138_deadline==N138_BUDGET_NS);
 reset();start_worker(0,"foreign_end");fixture_task=&foreign;n138_user_end();assert(n138_history==1 && n138_active==1 && worker.usage==2 && !task_puts);
 reset();fixture_task=&worker;n138_active=~0U;assert(!n141_user_begin("overflow") && task_gets==0 && worker.usage==1 && n138_history==1);
 reset();for(index=0;index<64;index++){n138_contexts[index].task=&worker;n138_contexts[index].depth=1;n138_contexts[index].irq_state=index*SOFTIRQ_OFFSET;n138_contexts[index].entry="full";n138_contexts[index].task_owned=true;}worker.usage=65;n138_active=64;
 assert(!n141_user_begin("capacity") && !task_gets && !task_puts && worker.usage==65 && n138_history==1);
 reset();n138_contexts[0].task=&worker;assert(!n141_user_begin("stale_empty") && !task_gets && n138_history==1 && n138_contexts[0].task==&worker);
 reset();start_worker(0,"invalid_ownership");n138_contexts[0].task_owned=false;fixture_task=&worker;n138_user_end();assert(n138_active==1 && n138_history==1 && !task_puts && worker.usage==2);
 reset();assert(n138_user_begin());assert(n138_contexts[0].entry && !strcmp(n138_contexts[0].entry,"compat"));n138_user_end();
 assert(!n138_contexts[0].depth && !n138_contexts[0].entry && !n138_contexts[0].task);
 reset();start_worker(HARDIRQ_OFFSET,"uncompleted_irq");assert(n141_display_close()==-ETIMEDOUT);
 assert(logged_irq==HARDIRQ_OFFSET && logged_depth==1 && !logged_self && n138_history==0);
 return 0;
}
'''


def preempt_fixture(raw):
    text=raw.decode();start=text.index('#define PREEMPT_BITS\t8\n');end=text.index('#define PREEMPT_DISABLED',start)
    definitions=re.findall(r'(?m)^#define irq_count\(\)[^\n]*\\\n[^\n]*',text)
    if len(definitions)!=1:raise ValueError('exact selected native irq_count macro required')
    return ('#ifndef N141_NATIVE_PREEMPT_FIXTURE\n#define N141_NATIVE_PREEMPT_FIXTURE\n'+text[start:end]+definitions[0]+'\n#endif\n').encode()


def task_fixture(raw):
    text=raw.decode()
    definitions=re.findall(r'(?m)^#define get_task_struct\(tsk\)[^\n]*',text)
    parsed,rows=prepare.lexical.definitions(raw);rows=[row for row in rows if row[4]=='put_task_struct']
    if len(definitions)!=1 or len(rows)!=1:raise ValueError('exact native task reference definitions required')
    return ('#ifndef N141_TASK_FIXTURE\n#define N141_TASK_FIXTURE\n'+definitions[0]+'\n'+parsed[rows[0][0]:rows[0][2]]+'\n#endif\n').encode()


def changed_source():
    # Only directly changed coordinator input; no old renderer or DPU fixture.
    raw=(HERE/'v138_display.c').read_bytes().replace(b'N10XNU138',b'N10XNU140')
    source=prepare.named_entries(prepare.admission_source(raw))
    return source.replace(b'N10XNU140',b'N10XNU141')


def cases(source):
    text=source.decode()
    assert 'bool n141_user_begin(const char *entry)' in text and 'bool interrupt;' not in text
    assert 'n138_contexts[i].irq_state==irq_state' in text and 'context->irq_state=irq_count()' in text
    _,rows=prepare.lexical.definitions(source);rows=[row for row in rows if row[4]=='n138_display_prepare']
    if len(rows)!=1:raise ValueError('exact new aggregate entry required')
    body=text[rows[0][0]:rows[0][2]]
    assert body.index('n141_display_close()')<body.index('ops[0]=n138_decon_native()')
    assert 'n138_deadline=' not in body and 'n138_polls=N138_POLL_LIMIT' not in body
    for action in ('error=ops[family]->quiet','error=pm_runtime_get_if_in_use','mode=n136_cal_begin'):
        at=body.index(action);assert 'n141_deadline_check();if(error)goto release;' in body[max(0,at-100):at]
    sample=b'int writer(void)\n{if(!n138_user_begin())return -1;n138_user_end();return 0;}\nconst char *literal="n138_user_begin()";\n'
    named=prepare.named_entries(sample);assert b'n141_user_begin(__func__)' in named and b'"n138_user_begin()"' in named
    assert len(package.CURRENT140_SOURCE_SHA256)==101 and package.CURRENT140_SOURCE_SHA256==build.RETAINED_SOURCE_SHA256
    assert set(re.findall(rb'N10XNU[0-9]+',build.pid1_source()))=={b'N10XNU141'}
    identity,cycle_id='a'*32,'b'*32;prefix='N10XNU141 id='+identity+' cycle='+cycle_id+' stage=begin\n'
    row='N10XNU141 id='+identity+' admission entry=sample_writer depth=2 irq=65536 self=0\n'
    decoded=cycle.decode({'new':(prefix+row+row.replace('sample_writer','another')).encode()},identity,cycle_id)
    assert decoded['display_admission_details']==[dict(entry='sample_writer',depth=2,irq_state=65536,self_owned=False)]
    bad=row.replace('sample_writer','a'*65);assert not cycle.decode({'new':(prefix+bad).encode()},identity,cycle_id)['display_admission_details']
    assert not decoded['physical_XNU_entry_observed'] and not decoded['full_XNU_boot_observed']


def fixture(source):
    text,rows=prepare.lexical.definitions(source)
    names=('n138_context_locked','n138_open_locked','n138_ticket_locked','n141_user_begin','n138_user_begin','n138_user_end')
    selected={name:[row for row in rows if row[4]==name] for name in names}
    if any(len(value)!=1 for value in selected.values()):raise ValueError('exact changed native accounting definition catalog required')
    declaration=re.findall(r'(?m)^struct n138_context[^\n]*\};',text)
    if len(declaration)!=1:raise ValueError('exact changed context declaration required')
    methods='\n'.join(text[selected[name][0][0]:selected[name][0][2]] for name in names)
    return (C_PREFIX.replace('/* N141_CONTEXT_DECLARATION */',declaration[0]).replace('/* N141_CHANGED_ACCOUNTING */',methods)+C_MAIN).encode()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('output','cc','retained-context','native-preempt-header','native-task-header'):parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--retained-context-sha256',required=True);args=parser.parse_args();out=private(args.output)
    if out.exists():parser.error('fresh new141 output required')
    prior_raw=ordinary(args.retained_context).read_bytes()
    if args.retained_context_sha256!=PRIOR_FILE_SHA or digest(prior_raw)!=hexid(args.retained_context_sha256):raise ValueError('exact retained140 synthetic PASS required')
    previous=json.loads(prior_raw);build.retained_continuation(previous,build.RETAINED_SOURCE_SHA256)
    if digest(json.dumps(previous,sort_keys=True,separators=(',',':')).encode())!=build.RETAINED_CONTEXT_SHA256 or previous['delta_NEW_PASS']['result_sha256']!=PRIOR_RESULT_SHA:raise ValueError('retained140 source101 binding differs')
    native=ordinary(args.native_preempt_header).read_bytes()
    if digest(native)!=PREEMPT_SHA:raise ValueError('exact native irq_count source required')
    task=ordinary(args.native_task_header).read_bytes()
    if digest(task)!=TASK_SHA:raise ValueError('exact native task reference source required')
    current_source=dict(build.RETAINED_SOURCE_SHA256,**{name:digest((ROOT/name).read_bytes()) for name in build.NEW_FILES});out.mkdir(parents=True)
    result=dict(schema='note10-v141-display-admission-result-v1',scope=build.SCOPE,passed=False,source_sha256={name:current_source[name] for name in build.NEW_FILES},retained140_result_sha256=PRIOR_RESULT_SHA,retained140_source_map_sha256='909d4f70134a3872185313243821cac72e084e093f01301921dbe2de12e8121e',native_preempt_header_sha256=PREEMPT_SHA,native_task_header_sha256=TASK_SHA,NEW_coordinator_transform_invocations=0,NEW_host_invocations=0,compiler_invocations=0,fixture_processes=0,retained_overlay_render_invocations=0,old_tests_replayed=0,Image_reads=0,raw_kernel_reads=0,adapter_reads=0,compressions=0,device_operations=[])
    def persist():(out/'result.json').write_bytes((json.dumps(result,indent=2)+'\n').encode())
    try:
        result['NEW_coordinator_transform_invocations']=1;persist();source=changed_source();(out/'new-admission-source.c').write_bytes(source);native_macros=preempt_fixture(native);native_tasks=task_fixture(task)
        checkpoint=(json.dumps(dict(schema='note10-v141-new-admission-checkpoint-v1',source_sha256=current_source,changed_source_sha256=digest(source),native_macro_sha256=digest(native_macros),native_task_sha256=digest(native_tasks)),indent=2)+'\n').encode();(out/'MANIFEST.json').write_bytes(checkpoint)
        result.update(checkpoint_file='MANIFEST.json',checkpoint_sha256=digest(checkpoint),changed_source_sha256=digest(source),NEW_transform_passed=True);persist()
        result['NEW_host_invocations']=1;persist();cases(source);result['NEW_host_cases_passed']=True;persist()
        generated=fixture(source);path=out/'new-display-admission.c';path.write_bytes(generated);result.update(generated_C_file=path.name,generated_C_sha256=digest(generated));persist()
        include=out/'include/linux';include.mkdir(parents=True);(include/'preempt.h').write_bytes(native_macros);(include/'native_task.h').write_bytes(native_tasks)
        for name in ('irqflags.h','sched.h','delay.h'):(include/name).write_bytes(b'/* synthetic selected dependency */\n')
        (out/'v141_admission.inc').write_bytes((HERE/'v141_admission.inc').read_bytes())
        macros=['-DCONFIG_'+key+'=1' for key,value in build.SETTINGS.items() if value=='y'];exe=out/('new-display-admission.exe' if sys.platform=='win32' else 'new-display-admission')
        command=[str(ordinary(args.cc)),'-std=gnu11','-O2','-Wall','-Wextra','-Werror','-Wstrict-prototypes','-Wno-unused-function','-ferror-limit=0',*macros,'-I',str(out/'include'),str(path),'-o',str(exe)]
        result['compiler_invocations']=1;persist()
        with (out/'compile.log').open('xb') as log:subprocess.run(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=60)
        result['fixture_processes']=1;persist()
        with (out/'fixture.log').open('xb') as log:subprocess.run([str(exe)],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=15)
        result['passed']=True;result_raw=(json.dumps(result,indent=2)+'\n').encode();delta=dict(schema='note10-v141-display-admission-pass-v1',scope=build.SCOPE,passed=True,result_sha256=digest(result_raw),source_sha256=result['source_sha256'])
        candidate=dict(schema='note10-v141-public-terminal-continuation-v1',scope=build.SCOPE,passed=True,retained_source_commit=build.RETAINED_COMMIT,retained_terminal_PASS=previous,delta_NEW_PASS=delta,source_sha256=current_source)
        build.continuation(candidate,current_source);encoded=encode_public(candidate);(out/'result.json').write_bytes(result_raw);save(out/'public-display-admission-continuation.json',candidate);(out/'public-display-admission-continuation.txt').write_bytes((encoded+'\n').encode('ascii'))
    except BaseException:
        import traceback
        result['error']=traceback.format_exc();persist();raise
    print(json.dumps(dict(passed=True,compiler_invocations=1,fixture_processes=1,old_tests_replayed=0)))


if __name__=='__main__':main()
