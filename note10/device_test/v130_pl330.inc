/* SPDX-License-Identifier: GPL-2.0-only */
/* Same PL330 TU. No allocated-idle inference; no active client termination claim. */
#include <linux/v130_kernel_api.h>
int n130_pl330_preflight(struct dma_device *device)
{
    struct pl330_dmac *controller;struct dma_chan *channel;unsigned long flags;int error=0;
    if(device->device_alloc_chan_resources!=pl330_alloc_chan_resources)return -EOPNOTSUPP;
    controller=container_of(device,struct pl330_dmac,ddma);
    spin_lock_irqsave(&controller->lock,flags);
    if(controller->n130_ever_allocated)error=-EBUSY;
    list_for_each_entry(channel,&device->channels,device_node){
        struct dma_pl330_chan *pch=to_pchan(channel);
        if(channel->client_count || pch->thread || pch->active || !list_empty(&pch->submitted_list) ||
           !list_empty(&pch->work_list) || !list_empty(&pch->completed_list))error=-EBUSY;
    }
    spin_unlock_irqrestore(&controller->lock,flags);return error;
}
int n130_pl330_quiet(struct dma_device *device)
{
    struct pl330_dmac *controller;struct dma_chan *channel;struct amba_device *amba;
    unsigned long flags;unsigned int i;int error;
    error=n130_pl330_preflight(device);if(error)return error;
    controller=container_of(device,struct pl330_dmac,ddma);
    amba=container_of(device->dev,struct amba_device,dev);
    error=pm_runtime_get_sync(device->dev);if(error<0){pm_runtime_put_noidle(device->dev);return error;}
    pm_runtime_forbid(device->dev);
    if(pm_runtime_suspended(device->dev))return -EIO;
    /* IRQ/manager tasklet drain is before device shutdown and CPU/DAIF stop. */
    for(i=0;i<AMBA_NR_IRQS && amba->irq[i];i++)disable_irq(amba->irq[i]);
    for(i=0;i<AMBA_NR_IRQS && amba->irq[i];i++)synchronize_irq(amba->irq[i]);
    tasklet_kill(&controller->tasks);
    spin_lock_irqsave(&controller->lock,flags);error=0;
    if(controller->n130_ever_allocated || !controller->manager || !list_empty(&controller->req_done) ||
       _state(controller->manager)!=PL330_STATE_STOPPED)error=-EBUSY;
    for(i=0;!error && i<controller->pcfg.num_chan;i++)
        if(_state(&controller->channels[i])!=PL330_STATE_STOPPED || controller->channels[i].req_running!=-1)error=-EBUSY;
    list_for_each_entry(channel,&device->channels,device_node){
        struct dma_pl330_chan *pch=to_pchan(channel);
        if(channel->client_count || pch->thread || pch->active || !list_empty(&pch->submitted_list) ||
           !list_empty(&pch->work_list) || !list_empty(&pch->completed_list))error=-EBUSY;
    }
    spin_unlock_irqrestore(&controller->lock,flags);
    return error;
}
