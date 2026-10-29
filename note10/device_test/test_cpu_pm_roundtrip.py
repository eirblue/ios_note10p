"""Focused native model for the exact v49 CPU_PM guard and paired-call path."""
import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

from prepare_cpu_pm_roundtrip import TARGETS, transform, validate_transform, function

HERE = Path(__file__).resolve().parent
CASES = [
    'success', 'enter-error-no-exit', 'exit-error-no-retry', 'missing-node',
    'unknown-node', 'duplicate-node', 'reordered-node', 'priority-mismatch',
    'busy-chain', 'wrong-cpu', 'wrong-mask', 'wrong-preempt', 'wrong-generation',
    'schedutil-started', 'ehld-not-running', 'ehld-ctrl-busy', 'gic-changed',
    'timer-changed', 'daif-changed', 'ehld-not-restored', 'nested-active', 'repeat-generation',
]
TRANSFORM_CASES = [
    'capture-call-omitted', 'guard-order-mutated', 'chain-lock-retained',
    'CPU_PM-exit-removed', 'capture-restore-removed', 'Kconfig-symbol-removed',
]
TERMINAL_CASES = ['caller-context-refusal','prior-chain-refusal','helper-admission-refusal',
                  'enter-failure','exit-failure','postcondition-failure','strict-success-no-terminal']
ERR_EALREADY = -103 if sys.platform == 'win32' else -114
TRANSCRIPTS = {
    'success': (0, 0, 1, 1, 1, 1, 2, 2),
    'enter-error-no-exit': (1, -5, 1, 0, 1, 1, 2, 2),
    'exit-error-no-retry': (2, -5, 1, 1, 1, 1, 2, 2),
    'missing-node': (3, -5, 0, 0, 1, 1, 0, 0),
    'unknown-node': (4, -5, 0, 0, 1, 1, 0, 0),
    'duplicate-node': (5, -5, 0, 0, 1, 1, 0, 0),
    'reordered-node': (6, -5, 0, 0, 1, 1, 0, 0),
    'priority-mismatch': (7, -5, 0, 0, 1, 1, 0, 0),
    'busy-chain': (8, -16, 0, 0, 1, 0, 0, 0),
    'wrong-cpu': (9, -1, 0, 0, 0, 0, 0, 0),
    'wrong-mask': (10, -1, 0, 0, 0, 0, 0, 0),
    'wrong-preempt': (11, -1, 0, 0, 0, 0, 0, 0),
    'wrong-generation': (12, -1, 0, 0, 0, 0, 0, 0),
    'schedutil-started': (13, -5, 0, 0, 1, 1, 0, 0),
    'ehld-not-running': (14, -5, 0, 0, 0, 0, 0, 0),
    'ehld-ctrl-busy': (15, -16, 0, 0, 1, 1, 1, 0),
    'gic-changed': (16, -5, 1, 1, 1, 1, 2, 2),
    'timer-changed': (17, -5, 1, 1, 1, 1, 2, 2),
    'daif-changed': (18, -5, 1, 1, 1, 1, 2, 2),
    'ehld-not-restored': (19, -5, 1, 1, 1, 1, 2, 2),
    'nested-active': (20, ERR_EALREADY, 0, 0, 0, 0, 0, 0),
    'repeat-generation': (21, ERR_EALREADY, 0, 0, 1, 0, 0, 0),
}

PREFIX = r'''#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include <stdio.h>
#include <stdlib.h>
#include <errno.h>
typedef uint64_t u64; typedef uint32_t u32; typedef int64_t s64;
#define ARRAY_SIZE(a) (sizeof(a)/sizeof((a)[0]))
#define __used __attribute__((used))
#define READ_ONCE(x) (x)
#define rcu_dereference_raw(x) (x)
#define N10_PRECOND_CAP 32
enum n10_precond_kind { N10_PRE_UNKNOWN, N10_PRE_GIC, N10_PRE_TIMER, N10_PRE_FPSIMD, N10_PRE_SUGOV, N10_PRE_PMU, N10_PRE_EHLD };
struct notifier_block { int (*notifier_call)(void); int priority; struct notifier_block *next; unsigned int kind; };
struct n10_precond_row { int priority; unsigned int kind, valid; s64 value[8]; };
struct n10_precond_sample { unsigned int generation,seen,bad,completed,count; int error; struct n10_precond_row row[N10_PRECOND_CAP]; };
struct n10_ehld_lock_row { unsigned int index,chain_count,lock_available,running_valid,running; };
struct n10_cpu_pm_roundtrip_sample { unsigned int generation,attempted,chain_lock_acquired,chain_lock_released,roster_count,roster_valid,pre_snapshot_valid,post_snapshot_valid,cpu_before,online_before,online_count_before,enter_calls,exit_calls,enter_succeeded,exit_succeeded,daif_stable,timer_stable,gic_stable,ehld_before,ehld_after,context_stable,passed,terminal_attempted,terminal_recorded,terminal_completed,caller_invoked,terminal_stage; int terminal_outer_error,terminal_helper_error,enter_error,exit_error,error; };
struct n10_precond_gic_row { u32 enable,active,config[2],priority[8]; unsigned int seen,restore_matches; };
struct n10_irq_gic_sample { unsigned int seen,cpu,online,count,irq,preempt; u32 cpu_ctlr,pmr,bpr,iidr,dist_ctlr,typer; };
struct { struct { int held; } lock; struct notifier_block *head; } cpu_pm_notifier_chain;
static struct notifier_block blocks[6], unknown_block;
static unsigned int active_gen=10, cpu_id, online_count=1, online_bits=1, irq_off=1, pc, mode, started, ehld_running=1;
static unsigned int daif_state=0x80, timer_state=0x4d, gic_epoch, enter_count, exit_count, try_count, unlock_count, ehld_try_count, ehld_unlock_count;
static unsigned long cpu_online_mask[1];
static struct n10_precond_sample prior_sample;
static int n10_pre_context(unsigned int g,int irq,unsigned int p) { return g==active_gen && irq==irq_off && p==pc && cpu_id==0 && online_count==1 && online_bits==1; }
static unsigned int raw_smp_processor_id(void) { return cpu_id; }
static unsigned int num_online_cpus(void) { return online_count; }
static unsigned long *cpumask_bits(unsigned long *p) { cpu_online_mask[0]=online_bits; return p; }
static unsigned int preempt_count(void) { return pc; }
static int irqs_disabled(void) { return irq_off; }
static int preemptible(void) { return pc==0 && !irq_off; }
static void preempt_disable(void) { pc++; }
static void preempt_enable(void) { if(pc)pc--; }
static int spin_trylock_irqsave(void *lock,unsigned long *flags) { (void)lock;try_count++;*flags=irq_off;if(mode==8)return 0;cpu_pm_notifier_chain.lock.held=1;irq_off=1;pc++;return 1; }
static void spin_unlock_irqrestore(void *lock,unsigned long flags) { (void)lock;unlock_count++;cpu_pm_notifier_chain.lock.held=0;if(pc)pc--;irq_off=(unsigned int)flags; }
#define spin_trylock_irqsave(l,f) spin_trylock_irqsave((void *)(l),&(f))
#define spin_unlock_irqrestore(l,f) spin_unlock_irqrestore((void *)(l),(f))
#define PSR_I_BIT 0x80ULL
#define daif 1
#define cntkctl_el1 2
#define read_sysreg(r) ((r)==daif ? daif_state : timer_state)
static int n10_pre_gic(struct notifier_block *n,struct n10_precond_row *r){(void)r;return n==&blocks[0];}
static int n10_pre_timer(struct notifier_block *n,struct n10_precond_row *r){(void)r;return n==&blocks[1];}
static int n10_pre_fpsimd(struct notifier_block *n,struct n10_precond_row *r){if(n!=&blocks[2])return 0;r->valid=15;return 1;}
static int n10_pre_sugov(struct notifier_block *n,struct n10_precond_row *r){if(n!=&blocks[3])return 0;r->valid=3;r->value[1]=started;return 1;}
static int n10_pre_pmu(struct notifier_block *n,struct n10_precond_row *r){if(n!=&blocks[4])return 0;r->valid=31;r->value[0]=1;return 1;}
static int n10_pre_ehld(struct notifier_block *n,struct n10_precond_row *r){if(n!=&blocks[5])return 0;r->valid=3;r->value[0]=ehld_running;r->value[1]=1;return 1;}
static int n10_ehld_lock_get(struct n10_ehld_lock_row *r,struct notifier_block *n,const struct n10_precond_sample *p,unsigned int index,unsigned int generation){ehld_try_count++;if(!r||n!=&blocks[5]||!p||p->completed||p->generation!=generation||index!=5||pc!=1||!irq_off)return -EPERM;r->index=index;if(mode==15)return 0;r->lock_available=1;r->running_valid=1;r->running=ehld_running;ehld_unlock_count++;return 0;}
static int n10_irq_gic_capture(unsigned int phase,struct n10_irq_gic_sample *out){if(!out||phase!=1||pc!=1||!irq_off)return -EIO;out->seen++;out->cpu=cpu_id;out->online=online_bits;out->count=online_count;out->irq=irq_off;out->preempt=pc;out->cpu_ctlr=1+gic_epoch;out->pmr=0xf0;out->bpr=0;out->iidr=0x123;out->dist_ctlr=3;out->typer=4;return 0;}
static int n10_pre_gic_regs(unsigned int phase,struct n10_precond_gic_row *r,u32 ctlr,u32 pmr){unsigned int i;(void)ctlr;(void)pmr;if(!r||phase!=1||pc!=1||!irq_off)return -EIO;r->seen++;r->enable=0x12+gic_epoch;r->active=0x34;r->config[0]=0x56;r->config[1]=0x78;for(i=0;i<8;i++)r->priority[i]=0x90+i;return 0;}
static int cpu_pm_enter(void){enter_count++;if(mode==1)return -EIO;ehld_running=0;if(mode==16)gic_epoch++;if(mode==17)timer_state++;if(mode==18)daif_state^=0x40;return 0;}
static int cpu_pm_exit(void){exit_count++;if(mode==19){ehld_running=0;}else ehld_running=1;if(mode==2)return -EIO;return 0;}
static void reset_case(unsigned int m){unsigned int i;mode=m;cpu_id=0;online_count=1;online_bits=1;cpu_online_mask[0]=1;irq_off=1;pc=0;started=0;ehld_running=1;daif_state=0x80;timer_state=0x4d;gic_epoch=0;enter_count=exit_count=try_count=unlock_count=ehld_try_count=ehld_unlock_count=0;cpu_pm_notifier_chain.lock.held=0;memset(&prior_sample,0,sizeof(prior_sample));memset(&unknown_block,0,sizeof(unknown_block));for(i=0;i<6;i++){blocks[i].kind=i+1;blocks[i].priority=0;blocks[i].next=i==5?NULL:&blocks[i+1];blocks[i].notifier_call=(int(*)(void))(uintptr_t)(i+1);}cpu_pm_notifier_chain.head=&blocks[0];prior_sample.generation=active_gen;prior_sample.seen=1;prior_sample.completed=0;prior_sample.count=6;for(i=0;i<6;i++){prior_sample.row[i].kind=i+1;prior_sample.row[i].priority=0;}prior_sample.row[2].valid=15;prior_sample.row[3].valid=3;prior_sample.row[3].value[1]=0;prior_sample.row[4].valid=31;prior_sample.row[4].value[0]=1;prior_sample.row[5].valid=3;prior_sample.row[5].value[0]=1;prior_sample.row[5].value[1]=1;if(m==3)blocks[4].next=NULL;if(m==4){blocks[2].next=&unknown_block;unknown_block.next=&blocks[3];}if(m==5)blocks[2].next=&blocks[2];if(m==6){blocks[1].next=&blocks[3];blocks[3].next=&blocks[2];blocks[2].next=&blocks[4];blocks[4].next=&blocks[5];blocks[5].next=NULL;}if(m==7)blocks[2].priority=1;if(m==9)cpu_id=1;if(m==10)online_bits=3;if(m==11)pc=2;if(m==12)active_gen++;if(m==13)started=1;if(m==14)prior_sample.row[5].value[0]=ehld_running=0;}
'''


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def extract_helper(raw):
    start = raw.find(b'static unsigned int n10_cpu_pm_roundtrip_active;')
    end = raw.find(b'\n#endif', start)
    if start < 0 or end < 0:
        raise ValueError('roundtrip helper block missing')
    block = raw[start:end]
    # Keep the actual production function bodies, excluding only the feature guard.
    if block.count(b'int n10_cpu_pm_roundtrip(') != 1 or block.count(b'static int n10_cpu_pm_roundtrip_context(') != 1:
        raise ValueError('roundtrip production functions are not unique')
    return block


def extract_terminal_functions(capture,probe):
    signatures=(
        (capture,b'int n10_pre_capture(unsigned int generation)'),
        (capture,b'int n10_pre_roundtrip_terminal_read(struct n10_cpu_pm_roundtrip_sample *out,'),
        (probe,b'static int n10_pre_emit_terminal(unsigned int completed, unsigned int generation)'),
        (probe,b'static int n10_report_pm_preconditions(unsigned int completed,int outer_error)'),
    )
    return [function(raw,signature)[2] for raw,signature in signatures]


TERMINAL_PREFIX=r'''#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include <stdio.h>
#include <stdlib.h>
#include <errno.h>
typedef uint64_t u64;
#define CONFIG_NOTE10_CPU_PM_ROUNDTRIP 1
#define N10_PRECOND_CAP 8
#define N10_RESERVE_BUILD_ID "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
#define PSR_I_BIT 0x80ULL
#define daif 1
struct n10_cpu_pm_roundtrip_sample { unsigned int generation,attempted,chain_lock_acquired,chain_lock_released,roster_count,roster_valid,pre_snapshot_valid,post_snapshot_valid,cpu_before,online_before,online_count_before,enter_calls,exit_calls,enter_succeeded,exit_succeeded,daif_stable,timer_stable,gic_stable,ehld_before,ehld_after,context_stable,passed,terminal_attempted,terminal_recorded,terminal_completed,caller_invoked,terminal_stage; int terminal_outer_error,terminal_helper_error,enter_error,exit_error,error; };
struct n10_precond_row { int priority; unsigned int kind,valid; long long value[8]; };
struct n10_precond_sample { unsigned int generation,seen,bad,completed,count; int error; struct n10_cpu_pm_roundtrip_sample roundtrip; struct n10_precond_row row[N10_PRECOND_CAP]; };
struct n10_precond_gic_sample { unsigned int completed; };
static struct n10_precond_sample n10_pre_last; static int n10_pre_bad;
static struct n10_cpu_pm_roundtrip_sample n10_pre_terminal_report;
static struct n10_precond_sample n10_pre_report;
static struct n10_precond_gic_sample n10_pre_gic_report;
static unsigned int current_generation=42,irq_off,pc,mode,daif_state,emitted;
static unsigned int emit_all_count; static int emit_all_status;
static char emitted_tag[2][16],emitted_frame[2][512];
static int irqs_disabled(void){return irq_off;}
static unsigned int preempt_count(void){return pc;}
static int preemptible(void){return pc==0&&!irq_off;}
static int n10_pre_context(unsigned int g,int irq,unsigned int preempt){return g==current_generation&&irq==irq_off&&preempt==pc;}
static int n10_pre_read(struct n10_precond_sample *s,unsigned int completed){(void)s;(void)completed;return 0;}
static int n10_pre_gic_read(struct n10_precond_gic_sample *s,unsigned int completed){(void)s;(void)completed;return 0;}
static int n10_pre_emit_all(int emit,int status,unsigned int generation){(void)emit;(void)generation;emit_all_count++;emit_all_status=status;return 0;}
static int mutex_lock(void *m){(void)m;return 0;} static void mutex_unlock(void *m){(void)m;}
static int pm_mutex;
#define local_irq_save(f) do{(f)=irq_off;irq_off=1;}while(0)
#define local_irq_restore(f) do{irq_off=(unsigned int)(f);}while(0)
#define read_sysreg(r) ((r)==daif?daif_state:0)
static int n10_pre_chain(struct n10_precond_sample *s,unsigned int g){(void)s;(void)g;return mode==1?-5:0;}
static int n10_cpu_pm_roundtrip(unsigned int g,const struct n10_precond_sample *prior,struct n10_cpu_pm_roundtrip_sample *out){unsigned int attempted=out->terminal_attempted,called=out->caller_invoked;int outer=out->terminal_outer_error;(void)prior;memset(out,0,sizeof(*out));out->generation=g;out->terminal_attempted=attempted;out->caller_invoked=called;out->terminal_outer_error=outer;out->attempted=1;if(mode==2){out->error=-16;return -16;}if(mode==3){out->enter_calls=1;out->enter_error=-5;out->error=-5;return -5;}if(mode==4){out->enter_calls=1;out->exit_calls=1;out->enter_succeeded=1;out->exit_error=-5;out->error=-5;return -5;}if(mode==5){out->enter_calls=1;out->exit_calls=1;out->enter_succeeded=out->exit_succeeded=1;out->error=-5;return -5;}out->enter_calls=out->exit_calls=out->enter_succeeded=out->exit_succeeded=1;out->passed=1;return 0;}
static int n10_pre_emit(const char *tag,const char *frame,int n,unsigned int *budget,int emit){unsigned int i;(void)budget;(void)emit;if(n<0||n>=512||emitted>=2)return -1;i=emitted++;strncpy(emitted_tag[i],tag,sizeof(emitted_tag[i])-1);memcpy(emitted_frame[i],frame,(size_t)n);emitted_frame[i][n]=0;return 0;}
'''


def run_terminal_lifecycle(source,output,cc):
    source,output=Path(source),Path(output)
    target=output/'terminal-lifecycle'
    target.mkdir(parents=True,exist_ok=False)
    cap=(source/'kernel/power/note10_pm_pre_capture.c').read_bytes()
    probe=(source/'arch/arm64/mm/note10_pm_pre_probe.c').read_bytes()
    capture_fn,reader_fn,emitter_fn,report_fn=extract_terminal_functions(cap,probe)
    main_c=r'''int main(int argc,char **argv){int m,ret,report_ret;unsigned int gen=42;struct n10_cpu_pm_roundtrip_sample out={0};unsigned int stages[]={0,1,2,3,4,5};int outer[]={-1,-5,0,0,0,0};int helper[]={0,0,-16,-5,-5,-5};unsigned int called[]={0,0,1,1,1,1},enters[]={0,0,0,1,1,1},exits[]={0,0,0,0,1,1};char expected[512];if(argc!=2)return 90;m=atoi(argv[1]);mode=(unsigned int)m;irq_off=pc=0;daif_state=(m==0?PSR_I_BIT:0);current_generation=gen;memset(&n10_pre_last,0,sizeof(n10_pre_last));n10_pre_bad=0;emitted=emit_all_count=0;emit_all_status=0;ret=n10_pre_capture(gen);report_ret=n10_report_pm_preconditions(gen+1,ret);if(m==6){if(ret||report_ret||n10_pre_last.roundtrip.terminal_recorded||n10_pre_roundtrip_terminal_read(&out,gen+1)==0||emitted||emit_all_count!=2||emit_all_status)return 1;printf("PASS|%d|%d|0|0|0|0|0\n",m,ret);return 0;}if(!ret||report_ret!=ret||n10_pre_last.roundtrip.terminal_recorded!=1||n10_pre_last.roundtrip.terminal_completed!=1)return 2;if(n10_pre_roundtrip_terminal_read(&out,gen+1))return 3;if(n10_pre_roundtrip_terminal_read(&out,gen+2)==0)return 4;if(emitted!=2||emit_all_count!=1||emit_all_status!=ret)return 5;if(strcmp(emitted_tag[0],"N10CPT1")||strcmp(emitted_tag[1],"N10CPT1"))return 6;if(strcmp(emitted_frame[0],emitted_frame[1])==0)return 7;if(out.generation!=gen||out.terminal_attempted!=1||out.terminal_recorded!=1||out.terminal_completed!=1)return 8;if(out.terminal_stage!=stages[m]||out.caller_invoked!=called[m]||out.terminal_outer_error!=outer[m]||out.terminal_helper_error!=helper[m]||out.enter_calls!=enters[m]||out.exit_calls!=exits[m])return 9;for(unsigned int copy=0;copy<2;copy++){snprintf(expected,sizeof(expected),"id=%s copy=%u generation=%u attempted=1 recorded=1 completed=1 caller_invoked=%u stage=%u outer_error=%d helper_error=%d enter_calls=%u exit_calls=%u enter_error=%d exit_error=%d","aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",copy,gen,called[m],stages[m],outer[m],helper[m],enters[m],exits[m],m==3?-5:0,m==4?-5:0);if(strcmp(emitted_frame[copy],expected))return 10;}printf("PASS|%d|%d|%u|%u|%u|%u|%d\n",m,ret,out.terminal_stage,out.caller_invoked,out.enter_calls,out.exit_calls,out.terminal_helper_error);return 0;}'''
    generated=target/'terminal.c'
    generated.write_text(TERMINAL_PREFIX+capture_fn.decode('ascii')+'\n'+reader_fn.decode('ascii')+'\n'+emitter_fn.decode('ascii')+'\n'+report_fn.decode('ascii')+'\n'+main_c+'\n',encoding='ascii',newline='\n')
    exe=target/('terminal.exe' if sys.platform=='win32' else 'terminal')
    comp=subprocess.run([cc,'-std=gnu11','-Wall','-Werror',str(generated),'-o',str(exe)],capture_output=True,timeout=120)
    (target/'compile.log').write_bytes(comp.stdout+comp.stderr)
    if comp.returncode:raise RuntimeError('terminal caller/reader/probe native compile failed')
    transcripts={};logs={}
    for mode,name in enumerate(TERMINAL_CASES):
        run=subprocess.run([str(exe),str(mode)],capture_output=True,timeout=20)
        raw=run.stdout+run.stderr;(target/(f'case-{mode:02d}.log')).write_bytes(raw)
        text=raw.decode('ascii',errors='replace').strip()
        if run.returncode or not text.startswith('PASS|'):raise RuntimeError('terminal native case failed: '+name)
        transcripts[name]=text;logs[name]=sha(raw)
    proof={'passed':True,'hardware_verified':False,'cases':TERMINAL_CASES,
           'source_capture_sha256':sha((source/'kernel/power/note10_pm_pre_capture.c').read_bytes()),
           'source_probe_sha256':sha((source/'arch/arm64/mm/note10_pm_pre_probe.c').read_bytes()),
           'extracted_capture_sha256':sha(capture_fn),'extracted_reader_sha256':sha(reader_fn),
           'extracted_emitter_sha256':sha(emitter_fn),'extracted_report_sha256':sha(report_fn),
           'harness_sha256':sha(Path(__file__).read_bytes()),
           'generated_sha256':sha(generated.read_bytes()),'compile_log_sha256':sha((target/'compile.log').read_bytes()),
           'case_log_sha256':logs,'case_transcripts':transcripts}
    (target/'result.json').write_text(json.dumps(proof,indent=2)+'\n',encoding='utf8',newline='\n')
    return proof


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--source-root', required=True)
    ap.add_argument('--baseline-source', required=True)
    ap.add_argument('--output', required=True)
    ap.add_argument('--cc', default='clang-14')
    ap.add_argument('--terminal-only',action='store_true')
    a = ap.parse_args()
    source, baseline, output = Path(a.source_root), Path(a.baseline_source), Path(a.output)
    output.mkdir(parents=True, exist_ok=False)
    if a.terminal_only:
        proof=run_terminal_lifecycle(source,output,a.cc)
        print(json.dumps({'passed':proof['passed'],'hardware_verified':False,
                          'cases':len(proof['cases']),'generated_sha256':proof['generated_sha256']}))
        return
    old = {name: (baseline / name).read_bytes() for name in TARGETS}
    new = {name: (source / name).read_bytes() for name in TARGETS}
    if not validate_transform(old, new):
        raise ValueError('exact production transform validation failed')
    body = extract_helper(new['kernel/cpu_pm.c'])
    mutation_checks = {}
    mutations = {
        'capture-call-omitted': ('kernel/power/note10_pm_pre_capture.c', b'n10_cpu_pm_roundtrip(generation,s,&s->roundtrip)', b'n10_cpu_pm_roundtrip_skipped(generation,s,&s->roundtrip)'),
        'guard-order-mutated': ('kernel/cpu_pm.c', b'matches != 1 || kind != index + 1', b'matches == 0 || kind != index + 1'),
        'chain-lock-retained': ('kernel/cpu_pm.c', b'spin_unlock_irqrestore(&cpu_pm_notifier_chain.lock, flags);', b'/* mutation: lock not released */'),
        'CPU_PM-exit-removed': ('kernel/cpu_pm.c', b'exit_error = cpu_pm_exit();', b'exit_error = 0;'),
        'capture-restore-removed': ('kernel/power/note10_pm_pre_capture.c', b'local_irq_restore(roundtrip_flags);', b'/* mutation: missing IRQ restore */'),
        'Kconfig-symbol-removed': ('kernel/power/Kconfig', b'config NOTE10_CPU_PM_ROUNDTRIP', b'config NOTE10_CPU_PM_ROUNDTRIP_MUTATED'),
    }
    for name, (path, anchor, changed) in mutations.items():
        mutated = dict(new)
        if mutated[path].count(anchor) != 1:
            raise ValueError('focused transform mutation anchor missing: ' + name)
        mutated[path] = mutated[path].replace(anchor, changed, 1)
        try:
            validate_transform(old, mutated)
        except ValueError:
            mutation_checks[name] = True
        else:
            raise RuntimeError('production transform accepted mutation: ' + name)
    if set(mutation_checks) != set(TRANSFORM_CASES):
        raise ValueError('focused transform mutation set differs')
    main_c = r'''\nint main(int argc,char **argv){unsigned int m,pc_before;struct n10_cpu_pm_roundtrip_sample out={0};int ret;if(argc!=2)return 90;m=(unsigned int)atoi(argv[1]);reset_case(m);if(preemptible())return 89;if(m==20){n10_cpu_pm_roundtrip_active=1;}if(m==21){mode=8;ret=n10_cpu_pm_roundtrip(active_gen,&prior_sample,&out);if(ret!=-EBUSY||enter_count||exit_count)return 9;mode=0;active_gen++;prior_sample.generation=active_gen;memset(&out,0,sizeof(out));ret=n10_cpu_pm_roundtrip(active_gen,&prior_sample,&out);if(ret!=-EALREADY||enter_count||exit_count)return 10;printf("PASS|%u|%d|%u|%u|%u|%u|%u|%u\n",m,ret,enter_count,exit_count,try_count,unlock_count,ehld_try_count,ehld_unlock_count);return 0;}if(m==20){n10_cpu_pm_roundtrip_active=1;ret=n10_cpu_pm_roundtrip(active_gen,&prior_sample,&out);if(ret!=-EALREADY||enter_count||exit_count)return 1;printf("PASS|%u|%d|%u|%u|%u|%u|%u|%u\n",m,ret,enter_count,exit_count,try_count,unlock_count,ehld_try_count,ehld_unlock_count);return 0;}pc_before=pc;ret=n10_cpu_pm_roundtrip(active_gen,&prior_sample,&out);if(m==1){if(ret!=-EIO||enter_count!=1||exit_count!=0||out.enter_calls!=1||out.exit_calls!=0)return 2;}else if(m==2){if(ret!=-EIO||enter_count!=1||exit_count!=1)return 3;}else if(m==0){if(ret||!out.passed||enter_count!=1||exit_count!=1||!out.daif_stable||!out.timer_stable||!out.gic_stable||!out.context_stable){fprintf(stderr,"DBG ret=%d pass=%u api=%u/%u daif=%u timer=%u gic=%u ctx=%u err=%d enter=%d exit=%d roster=%u valid=%u pre=%u post=%u ehld=%u/%u\n",ret,out.passed,enter_count,exit_count,out.daif_stable,out.timer_stable,out.gic_stable,out.context_stable,out.error,out.enter_error,out.exit_error,out.roster_count,out.roster_valid,out.pre_snapshot_valid,out.post_snapshot_valid,out.ehld_before,out.ehld_after);return 4;}}else if(m>=16&&m<=19){if(ret!=-EIO||enter_count!=1||exit_count!=1)return 8;}else if(ret==0||enter_count||exit_count)return 5;if(out.chain_lock_acquired!=out.chain_lock_released)return 6;if(cpu_pm_notifier_chain.lock.held||pc!=pc_before||!irq_off||n10_cpu_pm_roundtrip_active)return 7;printf("PASS|%u|%d|%u|%u|%u|%u|%u|%u\n",m,ret,enter_count,exit_count,try_count,unlock_count,ehld_try_count,ehld_unlock_count);return 0;}\n'''
    main_c = main_c[2:-2]
    c_path = output / 'roundtrip.c'
    c_path.write_text(PREFIX + body.decode('ascii') + '\n' + main_c, encoding='ascii', newline='\n')
    exe = output / ('roundtrip.exe' if sys.platform == 'win32' else 'roundtrip')
    compile_run = subprocess.run([a.cc, '-std=gnu11', '-Wall', '-Werror', str(c_path), '-o', str(exe)], capture_output=True, timeout=120)
    (output / 'compile.log').write_bytes(compile_run.stdout + compile_run.stderr)
    if compile_run.returncode:
        raise RuntimeError('native compile failed; see compile.log')
    logs = {}
    transcripts = {}
    for i, name in enumerate(CASES):
        p = subprocess.run([str(exe), str(i)], capture_output=True, timeout=20)
        raw = p.stdout + p.stderr
        (output / f'case-{i:02d}.log').write_bytes(raw)
        fields = raw.decode('ascii', errors='replace').strip().split('|')
        try:
            transcript = tuple(int(x) for x in fields[1:]) if fields[0] == 'PASS' else ()
        except (ValueError, IndexError):
            transcript = ()
        if p.returncode or transcript != TRANSCRIPTS[name]:
            raise RuntimeError('native case failed: ' + name)
        logs[name] = sha(raw)
        transcripts[name] = raw.decode('ascii').strip()
    terminal_lifecycle=run_terminal_lifecycle(source,output,a.cc)
    result = {
        'schema_version': 1,
        'passed': True,
        'hardware_verified': False,
        'cases': CASES,
        'transform_cases': TRANSFORM_CASES,
        'transform_mutations_rejected': mutation_checks,
        'harness_sha256': sha(Path(__file__).read_bytes()),
        'generated_sha256': sha(c_path.read_bytes()),
        'compile_log_sha256': sha((output / 'compile.log').read_bytes()),
        'case_log_sha256': logs,
        'case_transcripts': transcripts,
        'production_source_sha256': {name: sha((source / name).read_bytes()) for name in TARGETS},
        'baseline_source_sha256': {name: sha((baseline / name).read_bytes()) for name in TARGETS},
        'api_call_cases': {name: list(TRANSCRIPTS[name][2:4]) for name in CASES},
        'ehld_lock_cases': {name: list(TRANSCRIPTS[name][6:8]) for name in CASES},
        'terminal_lifecycle':terminal_lifecycle,
    }
    (output / 'result.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8', newline='\n')


if __name__ == '__main__':
    main()
