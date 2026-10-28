"""Focused native model: compiled actual getter and chain with stubbed kernel context."""
import argparse, hashlib, json, pathlib, subprocess, tempfile
HERE=pathlib.Path(__file__).resolve().parent

PRE=r'''#include <string.h>
#include <errno.h>
#include <assert.h>
#include <stdint.h>
typedef int64_t s64;
#define N10_PRECOND_CAP 32
#define N10_PRE_FPSIMD 3
struct notifier_block { int (*notifier_call)(void); };
struct n10_precond_row { int priority; unsigned int kind,valid; s64 value[8]; };
struct n10_precond_sample { unsigned int generation,seen,bad,completed,count; int error; struct n10_precond_row row[32]; };
struct n10_fps_row { unsigned int index,chain_count,kind,reference,mm,foreign,depth; };
struct n10_fps_sample { unsigned int generation,seen,completed; int error; struct n10_fps_row row; };
struct fpsimd_state { int x; };
struct task { void *mm; struct { struct fpsimd_state fpsimd_state; struct { int depth; } fpsimd_kernel_state; } thread; } task, *current=&task;
static struct fpsimd_state *fpsimd_last_state, other; static int reads,foreign,context_ok=1;
static int callback(void){return 0;} static struct notifier_block fpsimd_cpu_pm_notifier_block={callback};
#define fpsimd_cpu_pm_notifier callback
#define TIF_FOREIGN_FPSTATE 1
#define test_thread_flag(x) (foreign)
#define atomic_read(x) (*(x))
#define READ_ONCE(x) (x)
#define __this_cpu_read(x) (reads++,(x))
#define in_interrupt() 0
static int n10_pre_context(unsigned int g,int irq,unsigned int preempt){return context_ok && g==9 && irq==1 && preempt==1;}
'''
POST=r'''
int main(void) {
 struct n10_precond_sample pre={0}; struct n10_fps_sample out; struct task saved; struct fpsimd_state *saved_last; int i;
 pre.generation=9;pre.seen=1;pre.count=1;pre.row[0].kind=3;pre.row[0].valid=15;
 for(i=0;i<3;i++) {
  task.mm=&task;foreign=1;task.thread.fpsimd_kernel_state.depth=2;
  fpsimd_last_state=i==0?0:i==1?&task.thread.fpsimd_state:&other;
  pre.row[0].value[0]=1;pre.row[0].value[1]=1;pre.row[0].value[2]=2;pre.row[0].value[3]=(i==1);reads=0;saved=task;saved_last=fpsimd_last_state;
  n10_fps_begin(9);assert(!n10_fps_collect(&fpsimd_cpu_pm_notifier_block,0,3,9));assert(reads==1);assert(!memcmp(&task,&saved,sizeof(task)) && fpsimd_last_state==saved_last);
  assert(!n10_fps_complete(&pre,9));n10_fps_finish(0);assert(!n10_fps_copy(&out,10));assert(out.row.reference==(unsigned)i);
 }
 n10_fps_begin(9);assert(!n10_fps_collect(&fpsimd_cpu_pm_notifier_block,0,3,9));n10_fps_finish(0);assert(n10_fps_copy(&out,10));
 n10_fps_begin(9);assert(!n10_fps_collect(&fpsimd_cpu_pm_notifier_block,0,3,9));assert(n10_fps_collect(&fpsimd_cpu_pm_notifier_block,0,3,9));n10_fps_finish(0);assert(n10_fps_copy(&out,10));
 n10_fps_begin(9);assert(!n10_fps_collect(&fpsimd_cpu_pm_notifier_block,0,3,9));pre.row[0].valid=0;assert(n10_fps_complete(&pre,9));n10_fps_finish(0);assert(n10_fps_copy(&out,10));pre.row[0].valid=15;
 n10_fps_begin(9);task.thread.fpsimd_kernel_state.depth=-1;reads=0;assert(n10_fps_collect(&fpsimd_cpu_pm_notifier_block,0,3,9));assert(!reads);n10_fps_finish(0);assert(n10_fps_copy(&out,10));
 task.thread.fpsimd_kernel_state.depth=2;pre.row[0].value[3]=0;n10_fps_begin(9);assert(!n10_fps_collect(&fpsimd_cpu_pm_notifier_block,0,3,9));assert(!n10_fps_complete(&pre,9));n10_fps_finish(-EIO);n10_fps_finish(0);assert(n10_fps_copy(&out,10));
 task.thread.fpsimd_kernel_state.depth=2;pre.row[0].value[3]=0;n10_fps_begin(9);assert(!n10_fps_collect(&fpsimd_cpu_pm_notifier_block,0,3,9));assert(!n10_fps_complete(&pre,9));n10_fps_finish(0);assert(!n10_fps_copy(&out,10));n10_fps_finish(0);assert(n10_fps_copy(&out,10));
 context_ok=0;reads=0;n10_fps_begin(9);assert(n10_fps_collect(&fpsimd_cpu_pm_notifier_block,0,3,9));assert(!reads);context_ok=1;
 {struct notifier_block wrong={callback};reads=0;n10_fps_begin(9);assert(n10_fps_collect(&wrong,0,3,9));assert(!reads);}
 task.mm=0;foreign=0;task.thread.fpsimd_kernel_state.depth=0;pre.row[0].value[0]=pre.row[0].value[1]=pre.row[0].value[2]=0;pre.row[0].value[3]=0;n10_fps_begin(9);assert(!n10_fps_collect(&fpsimd_cpu_pm_notifier_block,0,3,9));assert(!n10_fps_complete(&pre,9));n10_fps_finish(0);assert(!n10_fps_copy(&out,10));
 return 0;
}
'''
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--cc',default='clang');parser.add_argument('--source-root',type=pathlib.Path);parser.add_argument('--output',type=pathlib.Path);args=parser.parse_args()
 paths={'fpsimd_reference_getter.c': (args.source_root/'arch/arm64/kernel/note10_fpsimd_reference_getter.c' if args.source_root else HERE/'fpsimd_reference_getter.c'), 'fpsimd_reference_chain.c': (args.source_root/'kernel/note10_fpsimd_reference_chain.c' if args.source_root else HERE/'fpsimd_reference_chain.c')}
 def source(name):return '\n'.join(line for line in paths[name].read_text().splitlines() if not line.startswith('#include'))
 code=PRE+source('fpsimd_reference_getter.c')+source('fpsimd_reference_chain.c')+POST
 cases=['null-reference','current-reference','other-reference','complete-missing','duplicate-collect','prior-mask-mismatch','negative-depth','error-finish-overwrite','duplicate-finish','wrong-context','wrong-notifier','zero-mm-foreign-depth']
 with tempfile.TemporaryDirectory() as d:
  p=pathlib.Path(d);(p/'model.c').write_text(code,encoding='utf8',newline='\n');cmd=[args.cc,'-std=c11','-O2','-Wall','-Werror',str(p/'model.c'),'-o',str(p/'model.exe')]
  compile_result=subprocess.run(cmd,capture_output=True)
  if compile_result.returncode:raise RuntimeError(compile_result.stderr.decode(errors='replace'))
  run_result=subprocess.run([str(p/'model.exe')],capture_output=True)
  if run_result.returncode:raise RuntimeError(run_result.stderr.decode(errors='replace'))
  if args.output:
   args.output.mkdir(parents=True,exist_ok=False)
   (args.output/'model.c').write_bytes(code.encode())
   (args.output/'compile.log').write_bytes(compile_result.stdout+compile_result.stderr)
   (args.output/'run.log').write_bytes(run_result.stdout+run_result.stderr)
   result={'passed':True,'hardware_verified':False,'cases':cases,'compiler_options':['-std=c11','-O2','-Wall','-Werror'],'source_sha256':{n:hashlib.sha256(p.read_bytes()).hexdigest() for n,p in paths.items()},'harness_sha256':hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest(),'generated_sha256':hashlib.sha256(code.encode()).hexdigest(),'log_sha256':{n:hashlib.sha256((args.output/n).read_bytes()).hexdigest() for n in ('compile.log','run.log')}}
   (args.output/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
 print('native getter and lifecycle: pass (12 focused scenarios)')
if __name__=='__main__':main()
