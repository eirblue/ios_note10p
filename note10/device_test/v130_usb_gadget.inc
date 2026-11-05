/* SPDX-License-Identifier: GPL-2.0-only */
/* Same gadget.c TU. This bounded profile never admits a bound gadget client. */
#include <linux/v130_kernel_api.h>
int n130_usb_gadget_quiet(struct dwc3 *dwc)
{
    unsigned long flags;int error=0;
    spin_lock_irqsave(&dwc->lock,flags);
    if(dwc->gadget_driver || dwc->pullups_connected ||
       (dwc3_readl(dwc->regs,DWC3_DCTL)&DWC3_DCTL_RUN_STOP) ||
       !(dwc3_readl(dwc->regs,DWC3_DSTS)&DWC3_DSTS_DEVCTRLHLT))error=-EBUSY;
    if(!error)dwc3_gadget_disable_irq(dwc);
    spin_unlock_irqrestore(&dwc->lock,flags);
    if(error)return error;
    /* Do not hold dwc->lock while the actual IRQ handler/thread drains. */
    synchronize_irq(dwc->irq_gadget);
    if(dwc->gadget_driver || (dwc3_readl(dwc->regs,DWC3_DCTL)&DWC3_DCTL_RUN_STOP) ||
       !(dwc3_readl(dwc->regs,DWC3_DSTS)&DWC3_DSTS_DEVCTRLHLT))return -EBUSY;
    return 0;
}
