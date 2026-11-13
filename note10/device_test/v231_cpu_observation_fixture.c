/* SPDX-License-Identifier: GPL-2.0-only */
#include "v231_cpu_observation.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static struct {n209_u64 before;struct n231_cpu_observation sample;n209_u64 after;} output;
static n209_u64 registers[3];static unsigned int cpu,events[5],count,bad_publication;
static unsigned int assertions,variants;
#define CHECK(x) do {assertions++;if(!(x)){fprintf(stderr,"CPU observation assertion %u at %d\n",assertions,__LINE__);exit(1);}}while(0)
static void event(unsigned int code)
{ if(count>=5)abort();events[count++]=code;if(output.sample.status)bad_publication=1; }
unsigned int n231_fixture_get_cpu(void){event(0);return cpu;}
n209_u64 n231_fixture_read(unsigned int which)
{ if(which>=3)abort();event(which+1);return registers[which]; }
void n231_fixture_put_cpu(void)
{
    event(4);
    /* Model migration after preemption is enabled, never during the read pair. */
    cpu=7;registers[0]=0;registers[1]=0;registers[2]=8;
}
static void run(unsigned int index,n209_u64 mpidr,n209_u64 hz,n209_u64 el,int valid)
{
    const unsigned int wanted[5]={0,1,2,3,4};struct n231_cpu_observation zero={0};
    cpu=index;registers[0]=mpidr;registers[1]=hz;registers[2]=el;count=bad_publication=0;
    memset(&output,0xa5,sizeof(output));variants++;
    CHECK((n231_capture_cpu_observation(&output.sample)==0)==valid);
    CHECK(count==5&&!bad_publication&&!memcmp(events,wanted,sizeof(wanted)));
    CHECK(valid?(output.sample.mpidr_el1==mpidr&&output.sample.cntfrq_el0==hz&&output.sample.linux_cpu==index&&
                 output.sample.current_el==4&&output.sample.status==1&&output.sample.reserved==0):!memcmp(&output.sample,&zero,sizeof(zero)));
    CHECK(output.before==UINT64_C(0xa5a5a5a5a5a5a5a5)&&output.after==UINT64_C(0xa5a5a5a5a5a5a5a5));
}
int main(void)
{
    run(0,UINT64_C(0x80000000),24000000,4,1);
    run(3,UINT64_C(0x1234567887654321),UINT64_C(0xffffffff),4,1);
    run(0,1,0,4,0);run(0,1,UINT64_C(0x100000000),4,0);
    run(0,1,24000000,8,0);run(0,1,24000000,UINT64_C(0x100000004),0);run(8,1,24000000,4,0);
    count=0;variants++;CHECK(n231_capture_cpu_observation(NULL)!=0);CHECK(count==0);
    printf("{\"groups\":1,\"variants\":%u,\"assertions\":%u}\n",variants,assertions);return 0;
}
