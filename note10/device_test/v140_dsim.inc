/* SPDX-License-Identifier: GPL-2.0-only */
/* Exact DSI IOVMM proxy binding; no new SFR/PHY/clock/PM operation. */
#ifdef N140_DECON_NATIVE
bool n140_native_dsim_link(void *primary_object,void *output_object)
{
    struct decon_device *decon=primary_object;struct dsim_device *dsim=output_object;
    /* Caller owns BOTH core device locks, after parent final validation. */
    return decon && dsim && decon_drvdata[0]==decon && decon->id==0 &&
        decon->dt.out_type==DECON_OUT_DSI && decon->dt.dsi_mode==DSI_MODE_SINGLE &&
        decon->dt.out_idx[0]==0 && dsim->id==0 &&
        decon->out_sd[0]==&dsim->sd && decon->dsim_sd[0]==&dsim->sd &&
        v4l2_get_subdevdata(&dsim->sd)==dsim;
}
#endif

#ifdef N140_DSIM_CATALOG
#include <linux/of_address.h>
static struct n136_witness n140_dsim_witness;
static struct n136_detail n140_dsim_detail;
static bool n140_dsim_seen;
static int n140_dsim_result=-ENOENT;
static int n140_dsim_bad(const char *reason,unsigned int item,u32 state,int error,u32 aux)
{
    if(!n140_dsim_detail.reason){n140_dsim_detail.reason=reason;n140_dsim_detail.item=item;
        n140_dsim_detail.state=state;n140_dsim_detail.value=error;n140_dsim_detail.aux=aux;}
    return error;
}
static int n140_dsim_tuple(struct n138_slot *slot,struct n138_slot *parent)
{
    static const resource_size_t starts[]={0x190a0000,0x190b0000,0x190c0000};
    struct device_node *node,*peer,*domain;struct resource resource;
    unsigned int index;u32 cells,cal_id;int error;
    error=of_property_count_u32_elems(slot->dev->of_node,"iommus");
    if(error!=3)return n140_dsim_bad("dsim-proxy-tuple",0,error,-ENODEV,3);
    error=of_property_count_u32_elems(parent->dev->of_node,"iommus");
    if(error!=3)return n140_dsim_bad("dsim-proxy-peer-tuple",0,error,-ENODEV,3);
    for(index=0;index<3;index++){
        node=of_parse_phandle(slot->dev->of_node,"iommus",index);
        peer=of_parse_phandle(parent->dev->of_node,"iommus",index);
        domain=NULL;error=0;cells=0;cal_id=0;
        if(!node || node!=peer || !of_device_is_available(node) ||
           !of_device_is_compatible(node,"samsung,exynos-sysmmu") ||
           of_property_read_u32(node,"#iommu-cells",&cells) || cells ||
           of_address_to_resource(node,0,&resource))
            error=n140_dsim_bad("dsim-proxy-controller",index,cells,-ENODEV,0);
        else if(resource.start!=starts[index] || resource_size(&resource)!=0x9000)
            error=n140_dsim_bad("dsim-proxy-resource",index,(u32)resource.start,-ENODEV,(u32)resource_size(&resource));
        if(!error){
            domain=of_parse_phandle(node,"samsung,power-domain",0);
            if(!domain || !of_device_is_available(domain) ||
               !of_device_is_compatible(domain,"samsung,exynos-pd") ||
               of_property_read_u32(domain,"cal_id",&cal_id) || cal_id!=0xb1380003 ||
               of_address_to_resource(domain,0,&resource))
                error=n140_dsim_bad("dsim-proxy-domain",index,cal_id,-ENODEV,0);
            else if(resource.start!=0x15861e00 || resource_size(&resource)!=0x20)
                error=n140_dsim_bad("dsim-proxy-pmu-binding",index,(u32)resource.start,-ENODEV,(u32)resource_size(&resource));
        }
        of_node_put(domain);of_node_put(peer);of_node_put(node);
        if(error)return error;
    }
    return 0;
}
static int n140_dsim_guard(struct n138_slot *slot,struct n138_slot *parent,unsigned int *type)
{
    unsigned int index;
    if(n138_core_owner!=current || in_interrupt() || !n138_final_seen || n138_final_result ||
       !n138_seen || !n138_complete || n138_result || !n138_closed || n138_active || n138_history)
        return n140_dsim_bad("dsim-proxy-parent",0,n138_history,-EPERM,n138_active);
    for(index=0;index<N138_SLOTS;index++)if(n138_slots[index].lifetime &&
        (!n138_slots[index].device_locked || n138_slots[index].lifetime!=N138_BOUND ||
         !n138_slots[index].probe_completed || n138_slots[index].generation!=n138_slots[index].frozen_generation))
        return n140_dsim_bad("dsim-proxy-lifetime",index,n138_slots[index].lifetime,-ENODEV,n138_slots[index].generation);
    if(!n138_slots[0].object || n138_slots[0].lifetime!=N138_BOUND ||
       !n138_slots[0].device_locked || !slot->dev || !slot->object || slot->family!=N138_DSIM || slot->id ||
       slot->lifetime!=N138_BOUND || n138_find(N138_DSIM,1)->lifetime || !parent->dev ||
       !n136_witness_valid(&n138_witness,parent->dev,n138_witness.type,N138_DPU_DOMAINS))
        return n140_dsim_bad("dsim-proxy-owner",0,slot->lifetime,-ENODEV,0);
    if(n138_witness.type==N138_DPU_NATIVE_STOP_FROZEN){
        for(index=0;index<2;index++)if(!n138_find(N138_DECON,index?2:0)->stopped)
            return n140_dsim_bad("dsim-proxy-decon-ack",index,0,-EPERM,0);
        for(index=0;index<6;index++)if(!n138_find(N138_DPP,index)->stopped)
            return n140_dsim_bad("dsim-proxy-dpp-ack",index,0,-EPERM,0);
        *type=N140_DSIM_PROXY_NATIVE_FROZEN;
    }else if(n138_witness.type==N138_DPU_DOMAIN_OFF_FROZEN)*type=N140_DSIM_PROXY_OFF_FROZEN;
    else return n140_dsim_bad("dsim-proxy-witness",0,n138_witness.type,-EPERM,0);
    return 0;
}
int n140_dsim_final(void)
{
    struct n138_slot *slot=n138_find(N138_DSIM,0),*parent=n138_find(N138_DP,0);
    struct n138_slot *primary=n138_find(N138_DECON,0);
    struct device_node *node;unsigned long flags;unsigned int type=0,count=0;int error;
    spin_lock_irqsave(&n138_lock,flags);
    error=n140_dsim_guard(slot,parent,&type);
    if(!error && n140_dsim_seen){
        error=n140_dsim_result;
        if(!error && !n136_witness_valid(&n140_dsim_witness,slot->dev,type,N138_DPU_DOMAINS))error=-EPERM;
        spin_unlock_irqrestore(&n138_lock,flags);return error;
    }
    if(!error)n140_dsim_seen=true;
    spin_unlock_irqrestore(&n138_lock,flags);
    if(error)goto refused;
    /* Parent final holds all OWN core locks through IOMMU/transfer. No new
     * lock level, private access before those locks, or repeated self-trylock. */
    for_each_compatible_node(node,NULL,"samsung,exynos9-dsim"){
        if(!of_device_is_available(node))continue;
        count++;
        if(count!=1 || node!=slot->dev->of_node || of_alias_get_id(node,"dsim")!=0){
            of_node_put(node);error=n140_dsim_bad("dsim-proxy-node",count,0,-ENODEV,0);goto refused;
        }
    }
    if(count!=1){error=n140_dsim_bad("dsim-proxy-node",count,0,-ENODEV,0);goto refused;}
    if(!n140_native_dsim_link(primary->object,slot->object)){
        error=n140_dsim_bad("dsim-proxy-output",0,0,-ENODEV,0);goto refused;
    }
    error=n140_dsim_tuple(slot,parent);if(error)goto refused;
    spin_lock_irqsave(&n138_lock,flags);error=n140_dsim_guard(slot,parent,&type);
    spin_unlock_irqrestore(&n138_lock,flags);if(error)goto refused;
    error=n136_witness_commit(&n140_dsim_witness,slot->dev,type,N138_DPU_DOMAINS);
    if(!error)error=n130_dma_record(slot->dev,0);
    if(!error){n140_dsim_result=0;return 0;}
    (void)n140_dsim_bad("dsim-proxy-record",0,type,error,0);
refused:
    n140_dsim_result=error;
    if(slot->dev)(void)n130_dma_record(slot->dev,error);
    n131_gate_refused("dsim-proxy",error,slot->dev);
    pr_emerg("N10XNU140 id=%s display reason=%.40s item=%u state=%u value=%d aux=%u owner=%.64s\n",
        N10_KEXEC_BUILD_ID,n140_dsim_detail.reason?n140_dsim_detail.reason:"dsim-proxy-cache",
        n140_dsim_detail.item,n140_dsim_detail.state,n140_dsim_detail.value,n140_dsim_detail.aux,
        slot->dev?dev_name(slot->dev):"none");
    return error;
}
#endif
