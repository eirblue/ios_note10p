/* Called only after the all-online IRQ-off barrier and final log record. */
#include <linux/n303_mmuoff_contract.h>
int noinline n303_snapshot_claim(struct n303_slot *out)
{
    struct dbg_snapshot_item *log,*header;struct n303_owner state;
    if(dss_desc.log_kernel_num>=ARRAY_SIZE(dss_items) || dss_desc.header_num>=ARRAY_SIZE(dss_items))return -EINVAL;
    log=&dss_items[dss_desc.log_kernel_num];header=&dss_items[dss_desc.header_num];
    if(!dss_base.enabled || !log->entry.enabled || !header->entry.enabled ||
       header->entry.paddr!=dss_base.paddr || header->entry.vaddr!=dss_base.vaddr ||
       (unsigned long)log->head_ptr!=log->entry.vaddr || !header->entry.vaddr ||
       header->entry.size<DSS_OFFSET_LAST_LOGBUF+4)return -EINVAL;
    state.log_pa=log->entry.paddr;state.log_va=log->entry.vaddr;state.log_bytes=log->entry.size;
    state.cursor_va=(unsigned long)log->curr_ptr;state.header_pa=header->entry.paddr;
    state.header_va=header->entry.vaddr;state.header_bytes=header->entry.size;state.offset=DSS_OFFSET_LAST_LOGBUF;
    state.saved=__raw_readl((void __iomem *)(header->entry.vaddr+DSS_OFFSET_LAST_LOGBUF));state.enabled=1;
    return n303_claim_ok(&state,out)?0:-EINVAL;
}
/* v347: the dss layout for /chosen/note10-ufs dss-capture: cursor word PA, kernel-log ring PA and size (the descriptor
 * checks of n303_snapshot_claim; values only, no write). Called once from n310_adt in n304_prepare_args (IRQ-off,
 * before the claim); the deferred N347DSS line lets the host rebuild the hashed ADT. */
int n347_snapshot_layout(u64 *layout);
int noinline n347_snapshot_layout(u64 *layout)
{
    struct dbg_snapshot_item *log,*header;
    if(dss_desc.log_kernel_num>=ARRAY_SIZE(dss_items) || dss_desc.header_num>=ARRAY_SIZE(dss_items))return -EINVAL;
    log=&dss_items[dss_desc.log_kernel_num];header=&dss_items[dss_desc.header_num];
    if(!dss_base.enabled || !log->entry.enabled || !header->entry.enabled || header->entry.paddr!=dss_base.paddr ||
       header->entry.size<DSS_OFFSET_LAST_LOGBUF+4 || !log->entry.paddr || !log->entry.size)return -EINVAL;
    layout[0]=header->entry.paddr+DSS_OFFSET_LAST_LOGBUF;layout[1]=log->entry.paddr;layout[2]=log->entry.size;
    printk_deferred(KERN_EMERG "N347DSS cursor=%016llx log=%016llx size=%016llx\n",
                    (unsigned long long)layout[0],(unsigned long long)layout[1],(unsigned long long)layout[2]);
    return 0;
}
