/* SPDX-License-Identifier: GPL-2.0-only */
/* Same pinned core.c TU, using real probed controller and parent PM lifetime. */
#include <linux/platform_device.h>
#include <linux/v130_kernel_api.h>
#include <linux/v130_gate_core.h>
static struct dwc3 *n130_usb_controllers[4];
static unsigned int n130_usb_count;
static int n130_usb_readback(struct dwc3 *dwc)
{
    return dwc->dr_mode==USB_DR_MODE_PERIPHERAL &&
        n130_usb_halted(dwc3_readl(dwc->regs,DWC3_DCTL),dwc3_readl(dwc->regs,DWC3_DSTS),
            dwc3_readl(dwc->regs,DWC3_GCTL),dwc3_readl(dwc->regs,DWC3_GEVNTSIZ(0)),
            DWC3_DCTL_RUN_STOP,DWC3_DSTS_DEVCTRLHLT,DWC3_GCTL_PRTCAPDIR(DWC3_GCTL_PRTCAP_OTG),
            DWC3_GCTL_PRTCAPDIR(DWC3_GCTL_PRTCAP_DEVICE),DWC3_GEVNTSIZ_INTMASK,dwc->gadget_driver!=NULL)?0:-EBUSY;
}
static int n130_usb_stop_device(struct device *device,void *unused)
{
    struct dwc3 *dwc;struct device *parent;int error;(void)unused;
    if(device->driver!=&dwc3_driver.driver)return 0;
    dwc=dev_get_drvdata(device);parent=device->parent;
    if(!dwc || !parent || !parent->driver || strcmp(parent->driver->name,"exynos-dwc3") ||
       dwc->dr_mode!=USB_DR_MODE_PERIPHERAL || !dwc->ev_buf ||
       n130_usb_count>=ARRAY_SIZE(n130_usb_controllers))return -ENODEV;
    /* No remove/suspend shortcut. Both references remain held until reset/transfer. */
    error=pm_runtime_get_sync(parent);if(error<0){pm_runtime_put_noidle(parent);return error;}
    pm_runtime_forbid(parent);
    error=pm_runtime_get_sync(device);if(error<0){pm_runtime_put_noidle(device);return error;}
    pm_runtime_forbid(device);
    if(pm_runtime_suspended(parent) || pm_runtime_suspended(device))return -EIO;
    error=n130_usb_gadget_quiet(dwc);if(error)return error;
    dwc3_event_buffers_cleanup(dwc);
    if(n130_usb_readback(dwc) ||
       dwc3_readl(dwc->regs,DWC3_GEVNTSIZ(0))!=DWC3_GEVNTSIZ_INTMASK)return -EBUSY;
    n130_usb_controllers[n130_usb_count++]=dwc;
    error=n130_dma_record(device,0);if(!error)error=n130_dma_record(parent,0);
    return error;
}
int n130_usb_prepare(void)
{
    int error=bus_for_each_dev(&platform_bus_type,NULL,NULL,n130_usb_stop_device);
    return error?error:(n130_usb_count?0:-ENODEV);
}
int n130_usb_final(void)
{
    unsigned int i;if(!n130_usb_count)return -ENODEV;
    for(i=0;i<n130_usb_count;i++){
        struct dwc3 *dwc=n130_usb_controllers[i];
        if(n130_usb_readback(dwc) ||
           dwc3_readl(dwc->regs,DWC3_GEVNTSIZ(0))!=DWC3_GEVNTSIZ_INTMASK)return -EBUSY;
    }
    return 0;
}
