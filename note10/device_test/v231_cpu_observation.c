/* SPDX-License-Identifier: GPL-2.0-only */
#include "v231_cpu_observation.h"
#ifdef __KERNEL__
#include <linux/smp.h>
#include <asm/sysreg.h>
#define N231_GET_CPU() get_cpu()
#define N231_PUT_CPU() put_cpu()
#define N231_MPIDR() read_sysreg(mpidr_el1)
#define N231_CNTFRQ() read_sysreg(cntfrq_el0)
#define N231_EL() read_sysreg(CurrentEL)
#elif defined(N231_HOST_FIXTURE)
#define N231_GET_CPU() n231_fixture_get_cpu()
#define N231_PUT_CPU() n231_fixture_put_cpu()
#define N231_MPIDR() n231_fixture_read(0)
#define N231_CNTFRQ() n231_fixture_read(1)
#define N231_EL() n231_fixture_read(2)
#else
#error "231 requires kernel primitives or the explicit host IO shim"
#endif

static void n231_clear_observation(struct n231_cpu_observation *out)
{
    volatile n209_u8 *raw=(volatile n209_u8 *)out;unsigned int i;
    for(i=0;i<sizeof(*out);i++)raw[i]=0;
}
__attribute__((__noinline__)) int n231_capture_cpu_observation(struct n231_cpu_observation *out)
{
    n209_u64 el;
    if(!out)return -22;
    n231_clear_observation(out);
    out->linux_cpu=N231_GET_CPU();
    out->mpidr_el1=N231_MPIDR();out->cntfrq_el0=N231_CNTFRQ();el=N231_EL();
    N231_PUT_CPU();
    /* Validation/publication happens only after put_cpu has fully returned. */
    if(out->linux_cpu>=8 || el!=4 || !out->cntfrq_el0 || out->cntfrq_el0>0xffffffffULL){
        n231_clear_observation(out);return -22;
    }
    out->current_el=(n209_u32)el;out->status=1;return 0;
}

#ifdef __KERNEL__
/* Included after the retained stream owner; this aliases its existing gap. */
_Static_assert(N231_POOL_OFFSET==N226_STATS_OFFSET+sizeof(struct n226_stack_stats),"after stats48");
_Static_assert(N231_POOL_OFFSET%8==0 && N231_POOL_OFFSET+sizeof(struct n231_cpu_observation)<=N226_STAGE_OFFSET,"before stage4096");
__asm__(".globl n231_observation_storage\n.set n231_observation_storage,n226_source_pool+43544\n"
        ".type n231_observation_storage,%object\n.size n231_observation_storage,32\n");
static __used __attribute__((__noinline__)) void n231_layout_witness(void)
{
    asm volatile(".globl n231_size_observation\n.equ n231_size_observation,%c0\n"
                 ".globl n231_align_observation\n.equ n231_align_observation,%c1\n"
                 ".globl n231_status_offset\n.equ n231_status_offset,%c2\n"
                 : : "i"(sizeof(struct n231_cpu_observation)),"i"(__alignof__(struct n231_cpu_observation)),
                     "i"(offsetof(struct n231_cpu_observation,status)));
}
static __always_inline void n231_emit(int error)
{
    const struct n231_cpu_observation *sample=(const struct n231_cpu_observation *)(n226_source_pool+N231_POOL_OFFSET);
    pr_info("N231CPU id=%.32s boot=%.32s cycle=%.32s result=%d phase=linux-pid1-pre-ingest cpu=%u el=%x mpidr=%llx cntfrq=%llx valid=%u FDT_bound=0 handoff_cpu_selected=0 post_shutdown=0 XNU=0\n",
        n210_result.build,n210_result.boot,n210_result.cycle,error,sample->linux_cpu,sample->current_el,
        (unsigned long long)sample->mpidr_el1,(unsigned long long)sample->cntfrq_el0,!error&&sample->status==1);
}
#endif
