/* SPDX-License-Identifier: GPL-2.0-only */
/* Pinned Exynos9820 EVT1 native stop: reset completion, then all four DMA idle. */
#if !defined(CONFIG_NOTE10_XNU_KEXEC_HANDOFF) || CONFIG_NOTE10_XNU_KEXEC_HANDOFF != 1 || !defined(CONFIG_SOC_EXYNOS9820) || !defined(CONFIG_EXYNOS_SCORE_V3) || defined(CONFIG_EXYNOS_SCORE_V2) || defined(CONFIG_EXYNOS_SCORE_FPGA) || !defined(SCORE_EVT1) || defined(SCORE_EVT0)
#error "SCORE reset proof requires the actual non-FPGA Exynos9820 EVT1 v3 profile"
#endif
int n133_score_hardware_stop(struct score_system *system,struct n133_score_detail *detail)
{
    unsigned int index,channel;u32 value=0;unsigned long flags;int error=0;
    const unsigned int dma[]={DMA0_QUEUE_STATUS,DMA1_QUEUE_STATUS,DMA2_QUEUE_STATUS,DMA3_QUEUE_STATUS};
    if(system->sfr_size<BR_CACHE_STATUS+sizeof(u32)){detail->reason="mmio-extent";detail->state=system->sfr_size;return -ENODEV;}
    spin_lock_irqsave(&system->cache_slock,flags);
    /* Same one-write/zero-completion predicate and bounds as the pinned native
     * score_system_sw_reset, used directly by score_system_stop on EVT1.
     * Never boot/wakeup firmware or ask an unbooted target to handle a SWI. */
    writel(0x1,system->sfr+SW_RESET);
    for(index=0;index<CHECK_RETRY_COUNT;index++){
        value=readl(system->sfr+SW_RESET);
        if(!value)break;
        udelay(CHECK_RETRY_DELAY);
    }
    if(value){detail->reason="reset-ack";detail->item=0;detail->state=value;
        detail->value=CHECK_RETRY_COUNT;detail->aux=SW_RESET;error=-ETIMEDOUT;goto done;}
    for(channel=0;channel<ARRAY_SIZE(dma);channel++){
        for(index=0;index<CHECK_RETRY_COUNT;index++){
            value=readl(system->sfr+dma[channel]);
            if(!(value&(1U<<12)))break;
            udelay(CHECK_RETRY_DELAY);
        }
        if(value&(1U<<12)){detail->reason="dma-busy";detail->item=channel;detail->state=value;
            detail->value=CHECK_RETRY_COUNT;detail->aux=dma[channel];error=-ETIMEDOUT;goto done;}
    }
done:
    spin_unlock_irqrestore(&system->cache_slock,flags);return error;
}
