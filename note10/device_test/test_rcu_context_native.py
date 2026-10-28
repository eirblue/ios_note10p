"""Focused source-derived RCU getter/lifecycle model; fake layouts only."""
import argparse,hashlib,json,pathlib,subprocess,tempfile
HERE=pathlib.Path(__file__).resolve().parent
PRE=r'''#include <string.h>
#include <errno.h>
#include <stdint.h>
#include <limits.h>
#include <stdbool.h>
#include <assert.h>
typedef uint32_t u32;typedef long long s64;typedef struct {int value;} atomic_t;
#define N10_PRECOND_CAP 32
#define RCU_DYNTICK_CTRL_CTR 2
struct rcu_dynticks {long long dynticks_nesting;int dynticks_nmi_nesting;atomic_t dynticks;};
union special {u32 s;};struct fake_task {int rcu_read_lock_nesting;union special rcu_read_unlock_special;} task,*current=&task;
static struct rcu_dynticks rcu_dynticks;static bool disable_rcu_irq_enter;static int reads,context=1,field_reads[6];
static void record(const void *p){const void *fields[]={&rcu_dynticks.dynticks.value,&rcu_dynticks.dynticks_nesting,&rcu_dynticks.dynticks_nmi_nesting,&task.rcu_read_lock_nesting,&task.rcu_read_unlock_special.s,&disable_rcu_irq_enter};int i;reads++;for(i=0;i<6;i++)if(p==fields[i]){field_reads[i]++;return;}assert(0);}
#define this_cpu_ptr(p) (p)
#define READ_ONCE(x) (record(&(x)),(x))
#define atomic_read(x) (record(&(x)->value),(x)->value)
#define __this_cpu_read(x) (record(&(x)),(x))
#define in_interrupt() 0
static int n10_pre_context(unsigned int g,int irq,int pc){return context && g==9 && irq==1 && pc==1;}
struct n10_precond_sample {unsigned int generation,seen,bad,completed,count;int error;};
struct n10_rcu_row {unsigned int chain_count,watching,nesting_class,positive_headroom_two,nmi_nonzero,task_nesting_nonzero,task_special_nonzero,irq_enter_disabled;};
struct n10_rcu_sample {unsigned int generation,seen,completed;int error;struct n10_rcu_row row;};
'''
POST=r'''
int main(void){struct n10_rcu_row row;struct n10_rcu_sample out;struct n10_precond_sample pre={9,1,0,0,6,0};struct rcu_dynticks before;struct fake_task saved;int k;long long values[]={LLONG_MIN,-1,0,1,LLONG_MAX-3,LLONG_MAX-2,LLONG_MAX-1,LLONG_MAX};int i;
 for(i=0;i<8;i++){rcu_dynticks.dynticks_nesting=values[i];rcu_dynticks.dynticks_nmi_nesting=INT_MIN;rcu_dynticks.dynticks.value=i&1?2:1;task.rcu_read_lock_nesting=INT_MIN;task.rcu_read_unlock_special.s=0x80000000U;disable_rcu_irq_enter=1;before=rcu_dynticks;saved=task;reads=0;memset(field_reads,0,sizeof(field_reads));memset(&row,0,sizeof(row));assert(!n10_rcu_get(&row,9));assert(reads==6);for(k=0;k<6;k++)assert(field_reads[k]==1);assert(!memcmp(&rcu_dynticks,&before,sizeof(before))&&!memcmp(&task,&saved,sizeof(saved))&&disable_rcu_irq_enter);assert(row.watching==(unsigned)(i&1));assert(row.nesting_class==(unsigned)(i<2?0:i==2?1:2));assert(row.positive_headroom_two==(unsigned)(i>=3&&i<=5));assert(row.nmi_nonzero&&row.task_nesting_nonzero&&row.task_special_nonzero&&row.irq_enter_disabled);}
 context=0;reads=0;assert(n10_rcu_get(&row,9));assert(!reads);context=1;
 rcu_dynticks.dynticks_nesting=1;rcu_dynticks.dynticks_nmi_nesting=0;task.rcu_read_lock_nesting=0;task.rcu_read_unlock_special.s=0;disable_rcu_irq_enter=0;
 n10_rcu_begin(9);assert(!n10_rcu_collect(&pre,9));n10_rcu_finish(0);assert(!n10_rcu_copy(&out,10));assert(out.row.chain_count==6&&!out.row.nmi_nonzero&&!out.row.task_nesting_nonzero&&!out.row.task_special_nonzero&&!out.row.irq_enter_disabled);n10_rcu_finish(0);assert(n10_rcu_copy(&out,10));
 n10_rcu_begin(9);assert(!n10_rcu_collect(&pre,9));assert(n10_rcu_collect(&pre,9));n10_rcu_finish(0);assert(n10_rcu_copy(&out,10));
 n10_rcu_begin(9);assert(!n10_rcu_collect(&pre,9));n10_rcu_finish(-EIO);n10_rcu_finish(0);assert(n10_rcu_copy(&out,10));
 n10_rcu_begin(9);n10_rcu_finish(0);assert(n10_rcu_copy(&out,10));
 pre.bad=1;n10_rcu_begin(9);reads=0;assert(n10_rcu_collect(&pre,9));assert(!reads);pre.bad=0;pre.completed=1;n10_rcu_begin(9);reads=0;assert(n10_rcu_collect(&pre,9));assert(!reads);
 return 0;}
'''
CASES=['llmin','negative','zero','positive','max-minus-three','max-minus-two','max-minus-one','max','mask-bit0-v-bit1','negative-int-high-special','zero-fields','six-reads-input-unchanged','wrong-context-no-read','valid-lifecycle','duplicate-finish','duplicate-collect','error-finish-overwrite','missing-collect','invalid-prior-bad-or-completed']
def main():
 p=argparse.ArgumentParser();p.add_argument('--cc',default='clang');p.add_argument('--source-root',type=pathlib.Path);p.add_argument('--output',type=pathlib.Path);a=p.parse_args()
 paths={'getter':a.source_root/'kernel/rcu/note10_rcu_context_getter.c' if a.source_root else HERE/'rcu_context_getter.c','chain':a.source_root/'kernel/note10_rcu_context_chain.c' if a.source_root else HERE/'rcu_context_chain.c'}
 def source(n):return '\n'.join(line for line in paths[n].read_text().splitlines() if not line.startswith('#include'))
 code=PRE+source('getter')+source('chain')+POST
 with tempfile.TemporaryDirectory() as t:
  tmp=pathlib.Path(t);(tmp/'model.c').write_text(code,encoding='utf8',newline='\n');exe=tmp/'model.exe';c=subprocess.run([a.cc,'-std=c11','-O2','-Wall','-Werror',str(tmp/'model.c'),'-o',str(exe)],capture_output=True)
  if c.returncode:raise RuntimeError(c.stderr.decode(errors='replace'))
  x=subprocess.run([str(exe)],capture_output=True)
  if x.returncode:raise RuntimeError(x.stderr.decode(errors='replace'))
  if a.output:
   a.output.mkdir(parents=True,exist_ok=False);(a.output/'model.c').write_bytes(code.encode());(a.output/'compile.log').write_bytes(c.stdout+c.stderr);(a.output/'run.log').write_bytes(x.stdout+x.stderr)
   h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();result={'passed':True,'hardware_verified':False,'cases':CASES,'source_sha256':{n:h(p) for n,p in paths.items()},'harness_sha256':h(pathlib.Path(__file__)),'generated_sha256':hashlib.sha256(code.encode()).hexdigest(),'log_sha256':{n:h(a.output/n) for n in ('compile.log','run.log')}};(a.output/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
 print('RCU context native model: passed',len(CASES),'cases')
if __name__=='__main__':main()
