"""Exercise the actual v41 chain collector lifecycle with synthetic gate stubs."""
import argparse,subprocess
from pathlib import Path
STUB=r"""
#include <stdint.h>
#include <string.h>
#include <errno.h>
typedef uint32_t u32;
struct notifier_block {int type;};
#define N10_STATE_CAP 32
struct n10_state_row {unsigned int index,kind,num,supported;u32 used,present,owned,observed,running,stopped,uptodate,abnormal,affinity0,unbound,other,oncpu0,active;};
struct n10_state_sample {unsigned int generation,seen,completed,count;int error;struct n10_state_row row[32];};
static int ctx=1,intr,getter_calls;
static int n10_pre_context(unsigned int g,int irq,unsigned int p){return ctx && g && irq==1 && p==1;}
static int in_interrupt(void){return intr;}
static int n10_state_pmu(struct notifier_block *n,struct n10_state_row *r,unsigned int g){(void)n;(void)r;(void)g;getter_calls++;return 1;}
"""
MAIN=r"""
int main(void) {
 struct notifier_block n={0};struct n10_state_sample sample;
 if(n10_state_collect(&n,0,5,1)!=-EIO||getter_calls)return 1;
 n10_state_begin(1);if(n10_state_collect(&n,0,5,1)||getter_calls!=1)return 2;
 n10_state_finish(0);if(n10_state_copy(&sample,2))return 3;
 if(n10_state_collect(&n,1,5,1)!=-EIO||getter_calls!=1)return 4;
 n10_state_invalidate();if(!n10_state_copy(&sample,2))return 5;
 n10_state_begin(2);ctx=0;if(n10_state_collect(&n,0,5,2)!=-EPERM||getter_calls!=1)return 6;
 ctx=1;intr=1;if(n10_state_collect(&n,0,5,2)!=-EPERM||getter_calls!=1)return 7;
 intr=0;if(n10_state_collect(&n,0,5,2)||getter_calls!=2)return 8;
 n10_state_finish(-EIO);if(!n10_state_copy(&sample,3))return 9;
 n10_state_begin(3);if(n10_state_collect(&n,0,5,3))return 10;n10_state_finish(0);if(n10_state_copy(&sample,4))return 11;
 return 0;
}
"""
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--out',required=True);ap.add_argument('--cc',required=True);a=ap.parse_args();out=Path(a.out);out.mkdir(parents=True,exist_ok=False)
 source=Path(__file__).with_name('pmu_state_chain.c').read_text();source='\n'.join(x for x in source.splitlines() if not x.startswith('#include'))
 c=out/'native.c';c.write_text(STUB+'\n'+source+'\n'+MAIN,encoding='utf8',newline='\n');exe=out/'native.exe'
 subprocess.run([a.cc,'-std=gnu11','-Wall','-Wextra','-Werror',str(c),'-o',str(exe)],check=True);subprocess.run([str(exe)],check=True)
 print('lifecycle refusal, invalidation and fresh recovery passed')
if __name__=='__main__':main()
