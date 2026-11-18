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
