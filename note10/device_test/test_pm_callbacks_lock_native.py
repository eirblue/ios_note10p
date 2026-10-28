"""Exercise pinned public spin trylock wrappers with synthetic primitives."""
import argparse,hashlib,json,subprocess,sys
from pathlib import Path
from test_fsys_pm_native import function
from prepare_pm_callbacks import PINS
STUB=r'''
#include <stdio.h>
#include <stdlib.h>
typedef struct {int dep_map;int held;} raw_spinlock_t;
typedef struct {raw_spinlock_t rlock;} spinlock_t;
#define __always_inline inline
#define __lockfunc
#define _RET_IP_ 0
#define __cond_lock(lock,expr) (expr)
#define typecheck(t,x) ((void)sizeof(t))
#define spin_acquire(...) ((void)0)
#define spin_release(...) ((void)0)
#define dbg_snapshot_spinlock(...) ((void)0)
static unsigned long machine_flags;static int preempt,allow;
#define local_irq_save(f) do{(f)=machine_flags;machine_flags|=0x80;}while(0)
#define local_irq_restore(f) do{machine_flags=(f);}while(0)
static void preempt_disable(void){preempt++;}static void preempt_enable(void){preempt--;}
static int do_raw_spin_trylock(raw_spinlock_t *l){if(!allow)return 0;l->held=1;return 1;}
static void do_raw_spin_unlock(raw_spinlock_t *l){if(!l->held)abort();l->held=0;}
static raw_spinlock_t *spinlock_check(spinlock_t *s){return &s->rlock;}
'''
MAIN=r'''
int main(int argc,char **argv){int family=atoi(argv[1]),success=atoi(argv[2]),initial=atoi(argv[3]);unsigned long saved=0,before=initial?0x1d5:0x155;spinlock_t lock={0};machine_flags=before;allow=success;
 if(family){if(spin_trylock_irqsave(&lock,saved)){if(!success||preempt!=1||machine_flags!=(before|0x80))abort();spin_unlock_irqrestore(&lock,saved);}else if(success)abort();}
 else {if(raw_spin_trylock_irqsave(&lock.rlock,saved)){if(!success||preempt!=1||machine_flags!=(before|0x80))abort();raw_spin_unlock_irqrestore(&lock.rlock,saved);}else if(success)abort();}
 if(machine_flags!=before||saved!=before||preempt||lock.rlock.held)abort();return 0;}
'''
def macro(text,name):
 lines=text.splitlines(keepends=True);hits=[i for i,x in enumerate(lines) if x.startswith('#define '+name+'(')];
 if len(hits)!=1:raise ValueError('macro missing: '+name)
 i=hits[0];res=lines[i];
 while lines[i].rstrip().endswith('\\'):i+=1;res+=lines[i]
 return res+'\n'
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--source-root',required=True);ap.add_argument('--output',required=True);a=ap.parse_args();root=Path(a.source_root);o=Path(a.output);o.mkdir(parents=True,exist_ok=True);names=('include/linux/spinlock.h','include/linux/spinlock_api_smp.h','kernel/locking/spinlock.c');raw={n:(root/n).read_bytes() for n in names}
 for n,b in raw.items():
  if hashlib.sha256(b).hexdigest()!=PINS[n]:raise ValueError('lock source pin differs '+n)
 h=raw[names[0]].decode();api=raw[names[1]].decode();c=raw[names[2]].decode()
 code=STUB+function(api,'static inline int __raw_spin_trylock(')+function(api,'static inline void __raw_spin_unlock_irqrestore(')+function(c,'int __lockfunc _raw_spin_trylock(')+function(c,'void __lockfunc _raw_spin_unlock_irqrestore(')+macro(h,'raw_spin_trylock')+macro(h,'raw_spin_unlock_irqrestore')+macro(h,'raw_spin_trylock_irqsave')+macro(h,'spin_trylock_irqsave')+function(h,'static __always_inline void spin_unlock_irqrestore(')+MAIN
 src=o/'lock.c';src.write_text(code,encoding='utf-8');cc=Path('host-tools/windows-build/llvm-mingw/llvm-mingw-20261006-ucrt-x86_64/bin/clang.exe') if sys.platform=='win32' else 'cc';exe=o/('lock.exe' if sys.platform=='win32' else 'lock');p=subprocess.run([str(cc),'-std=gnu11','-O2',str(src),'-o',str(exe)],capture_output=True,timeout=60);(o/'compile.log').write_bytes(p.stdout+p.stderr)
 if p.returncode:raise RuntimeError(p.stderr.decode(errors='replace'))
 rows=[]
 for f in (0,1):
  for success in (0,1):
   for initial in (0,1):
    p=subprocess.run([str(exe),str(f),str(success),str(initial)],capture_output=True,timeout=20);rows.append({'family':f,'success':success,'initial_irq_disabled':initial,'passed':p.returncode==0});
    if p.returncode:raise RuntimeError('Lock wrapper failure')
 (o/'result.json').write_text(json.dumps({'passed':True,'cases':len(rows),'outcomes':rows,'actual_public_macros_and_wrappers':True,'architecture_atomicity_verified':False,'hardware_verified':False,'source_sha256':{n:hashlib.sha256(b).hexdigest() for n,b in raw.items()},'harness_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'generated_c_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'compile_log_sha256':hashlib.sha256((o/'compile.log').read_bytes()).hexdigest()},indent=2)+'\n',encoding='utf-8');print('actual public lock wrapper cases:',len(rows))
if __name__=='__main__':main()
