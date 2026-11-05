/* SPDX-License-Identifier: GPL-2.0-only */
/* Same dmaengine.c TU. Admission is intentionally limited to never-used PL330. */
#include <linux/v130_kernel_api.h>
static int n130_dma_terminal;
int n130_dmaengine_prepare(void)
{
    struct dma_device *device;struct dma_chan *channel;int error=0;
    mutex_lock(&dma_list_mutex);
    /* Same order as ordinary requests: list mutex, then admission mutex. */
    mutex_lock(&n130_dma_admission_mutex);
    WRITE_ONCE(n130_dma_freeze,1);smp_mb();
    list_for_each_entry(device,&dma_device_list,global_node){
        list_for_each_entry(channel,&device->channels,device_node)
            if(channel->client_count){error=-EBUSY;break;}
        if(error)break;
        error=n130_pl330_preflight(device);if(error)break;
    }
    mutex_unlock(&n130_dma_admission_mutex);
    /* All pure provider/client/history rejects precede irreversible PM/IRQ work. */
    if(!error)list_for_each_entry(device,&dma_device_list,global_node){
        error=n130_pl330_quiet(device);if(error)break;
    }
    if(!error)WRITE_ONCE(n130_dma_terminal,1);
    mutex_unlock(&dma_list_mutex);return error;
}
int n130_dmaengine_final(void)
{return READ_ONCE(n130_dma_freeze) && READ_ONCE(n130_dma_terminal)?0:-EBUSY;}
