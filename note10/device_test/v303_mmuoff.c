/* Linux-owned EL1 identity-map transition; no kexec image or XNU consumer. */
#include <linux/kernel.h>
#include <linux/errno.h>
#include <linux/n303_mmuoff_contract.h>
#include <asm/cacheflush.h>
#include <asm/memory.h>
#include <asm/mmu_context.h>
#include <asm/sysreg.h>
#include "cpu-reset.h"
extern char __idmap_text_start[],__idmap_text_end[];
extern void n303_post_mmu(void);
static struct n303_parameters n303_parameters __aligned(64);
int noinline n303_enter(const char *build,const char *boot,const char *cycle)
{
    struct n303_slot slot;unsigned long daif,start=(unsigned long)__idmap_text_start,end=(unsigned long)__idmap_text_end;
    phys_addr_t entry=__pa_symbol(n303_post_mmu),restart=__pa_symbol(__cpu_soft_restart);int count,error=-EINVAL;
    BUILD_BUG_ON(offsetof(struct n303_parameters,text)!=N303_PARAM_TEXT);
    if(read_sysreg(CurrentEL)!=4 || !(read_sysreg(sctlr_el1)&1) || end<=start || end-start>4096 ||
       entry<__pa_symbol(__idmap_text_start) || entry>=__pa_symbol(__idmap_text_end) ||
       restart<__pa_symbol(__idmap_text_start) || restart>=__pa_symbol(__idmap_text_end))return -EINVAL;
    daif=read_sysreg(daif);asm volatile("msr daifset, #0xf" ::: "memory");
    if(n303_snapshot_claim(&slot))goto refused;
    n303_parameters.record=slot.record;n303_parameters.cursor=slot.cursor;n303_parameters.next=slot.next;
    n303_parameters.bytes=N303_RECORD_BYTES;
    count=scnprintf(n303_parameters.text,sizeof(n303_parameters.text),N303_FORMAT,build,boot,cycle,
                    (unsigned long long)slot.record,(unsigned long long)slot.cursor,(unsigned long long)slot.next,(unsigned long long)slot.tail);
    if(count!=N303_RECORD_BYTES)goto refused;
    /* No printk after the cursor claim. Only bounded stock cache primitives. */
    __flush_dcache_area(&n303_parameters,sizeof(n303_parameters));
    __flush_dcache_area(__idmap_text_start,end-start);flush_icache_range(start,end);
    cpu_soft_restart(0,entry,__pa_symbol(&n303_parameters),0,0);
refused:
    write_sysreg(daif,daif);return error;
}
