"""New default-off v130 source overlay; no frozen Python/Node execution."""
from pathlib import Path
import hashlib
import re
from v130_contract import ROOT
HERE=Path(__file__).resolve().parent
OPTION='NOTE10_XNU_KEXEC_HANDOFF'
PINS={'arch/arm64/mm/init.c': 'cc990de7d8222f56fd71519c8b5dbf87a50abd4131e9eeb49ba78c04e3b6e3f3', 'init/main.c': '4493d28f7aacf7de510e7cdc1864fb359278f2f88233abcea6b77a39cb8e0b70', 'init/initramfs.c': '1a9af19668584dc664c28c640e02b6a03cc37a2fa5ecd1900d818bb67c775806', 'arch/arm64/Kconfig': '127273290ce9e8d337b0f186b576dac0ff3792bcbebffeea2ae49b9c5e99afc6', 'arch/arm64/kernel/machine_kexec.c': '341ab6c94215cb93c2e1a4ee39f9058bb9bd114de17c8a979ef77144cf67e5e6', 'arch/arm64/kernel/cpu-reset.h': '6f8873558cb62ac5403af15f25493ecab5b73bf803b835e449712e7dcbde0666', 'kernel/kexec_core.c': '537a3edd4e140117084aa641879965345ab1bdb9eaaad5396ed30aa831703d0b', 'kernel/reboot.c': 'ed27858a87e0b7fe098510f03054c034a333874017444de2052af3e691d5b3f8', 'drivers/samsung/sec_reboot.c': '9c598d65fac6c7be4ba9bcf1d3f6d7d5ec218844c28b97653deabc707190d594', 'drivers/watchdog/s3c2410_wdt.c': 'cea425d01ca901671ee67b644a15a0ee19271c970972894a2be52540f7186166', 'drivers/irqchip/irq-gic.c': 'b236ffb45d4269a0f1117bb5434ea2dc795ca9ec383ec164077cbf43096780eb', 'include/linux/irqchip/arm-gic.h': '191b5bd2eda66923b503f8c56186eb9001358941341207b5d5dceaf0fad4fbc6', 'drivers/clocksource/arm_arch_timer.c': '4b3d7bd50f48677962b650e7eef74320d3ae7e94df9806094723aa1eaf4039e4', 'drivers/usb/dwc3/core.c': '7d12e2d8303388da50de6c6631943921562423b4ae35b88d2a1431b668a3a4e1', 'drivers/usb/dwc3/core.h': '03de7b0605949ef9478dcba9593ff68329a13b26a88c0f997d581653e1b6b5f5', 'drivers/usb/dwc3/gadget.c': '89b6259ec31dd09add7497bd5f33a239a202742f461e0f716e6334daddf69bfc', 'drivers/scsi/ufs/ufshcd.c': '08e81a0bdabe781408ee2ffb17a3b5e89c5d4f24f7c9eecc04d3052603640b0b', 'drivers/scsi/ufs/ufshcd.h': 'd0a7a1e96aa5cc7dd22107cc2e6de52d6fd0987aab47f7d87d2dc7d680d8b190', 'drivers/scsi/ufs/ufs-exynos.c': 'ca61a2fad0b2dfee078cae1eb093297a5aca9b0e8d1227de22d1842ae854e188', 'drivers/iommu/exynos-iommu.c': '67d9bfb7597ec7434fc07a7101e69c385ac4cb9e61ebd727f0bcd40d01f1bb0b', 'drivers/iommu/exynos-iommu.h': 'f5f2be8937e8990672296e55d33bdbcd12244d0ab6aa8b8eef96de6717fadc11', 'include/linux/memblock.h': '04c5a23d41fa1adea1a955f832eca9412bd99cd43bbc84f2188559fb220f87fc', 'usr/initramfs_data.S': 'ec2e6e427c11bfe4544db421f1c889917c14510975bd568d472e0793a59111a2', 'usr/Makefile': 'fd61b618f993c54dc1e9e0f82f7f9798708683b601e2ab06c3c0d3c3dd84a1b5', 'lib/decompress.c': '784e0135483455f1bd30fc1d3359ca3d4705b07da2cfac0abc9eeeef5e3efd35', 'lib/decompress_inflate.c': 'a51bc095295c82b16e42504a664d61fdf7c68d0f1b65e8c288297a0ea826e8e3', 'scripts/gen_initramfs_list.sh': 'ea238afcbde1d54b8ca0a220adf3aed4e6078d85810ffa47ac04400d7cb3a271'}
PINS.update({'drivers/dma/dmaengine.c': '6cfb91beb7420d1326d3047a527db818d9b139abe8816c28f16c7f9c73b45dbd', 'drivers/dma/pl330.c': '3ca7d5eaee1ee1c5432bf79349510f17d0a5b6885ad1997b9bb1780f2ce646de', 'include/linux/dmaengine.h': '0af046f49ce09565aa3d7ebf18e30a424ea09b9b24e4ac16d87e9d60dc48680e'})
PINS.update({'drivers/scsi/ufs/ufs.h': '8856830dec209a98f0d945c6d154227199ae9391e1406c7cd6e14c46a6ea677f'})
PINS.update({'include/linux/usb/composite.h': '7ea97c31e0fb39dbffaccd08cb5efdffab72236e53050ba69c7c70c89eface01'})
PINS.update({'drivers/usb/dwc3/otg.c': 'f8ca1ef72d8eaef9e9377b6ebb6b26bc12c8290d0b502a18bc8fc191017d12de', 'drivers/usb/dwc3/host.c': '1d5d4614bb331af3545b9186aef7ea4b58c4ad5461532dd039713300042a0496', 'drivers/usb/dwc3/Makefile': 'f72d7e4025ea49eea4dae458b7bc41bf46d1785741f21d86b07d5021c39f7f0d', 'drivers/usb/host/Kconfig': 'e2d03376aa4a8859707cc04bff30c6eb17fb35102bdcba89dc5b5ef0e69b7ef7', 'drivers/usb/host/Makefile': 'e085b9d2a378496f8cea5aacea0db2da51ea83d02a9340ffe0f16ef2f60e7f3c', 'drivers/usb/manager/usb_typec_manager_notifier.c': '713e831f49315179950bba260a191dabf5c97212e2e634cbb642fd40564a6ebb', 'drivers/usb/gadget/function/f_accessory.c': '1963361a7de60b4df5658a8cc80bae63ecb26d8ca54e54a6426ed684bc369f1b', 'drivers/usb/gadget/configfs.c': '249965cbe70c6b4ad4f8218f37be76acf8a880a86ab11fd372b2eeaa4494a430', 'drivers/usb/gadget/function/u_ether.c': '649097adf76442895e16744680acb00b7cfd0e943d63054a7825a7205595b6a9', 'sound/usb/Kconfig': '97919f3ee35da67353fdfd7afd721d142eddff4a7d9afbd0e9bae96eea4b4da3', 'sound/usb/Makefile': 'bfe725c27600e2c6d065354ea70e6cbf8a67295a4cd7306f70b134d5c834b21a', 'net/netfilter/Kconfig': 'b8e3af765501b89865f0dbb648161cf5f3b558e30428bde2c0821bd01c4766a9', 'net/netfilter/Makefile': '27676215cb69762d8a3a26622cc57fb213064f963129a2cd7f78958f6dd5fc7e', 'include/linux/usb/otg-fsm.h': '5f53a1dbdc6a14c288ed20079800dddaf5559aa43c383682109a8c4ccdf51007'})
COMMON={
 'include/linux/legacy_kexec_core.h':'legacy_kexec_core.h',
 'include/linux/legacy_kexec_return.h':'legacy_kexec_return.h',
 'arch/arm64/mm/n130_legacy_core.c':'legacy_kexec_core.c',
 'drivers/samsung/n130_marker.c':'legacy_kexec_marker.c',
 'drivers/watchdog/n130_watchdog.c':'legacy_kexec_watchdog.c'}
OWN={
 'include/linux/v130_handoff_core.h':'v130_handoff_core.h',
 'include/linux/v130_gate_core.h':'v130_gate_core.h',
 'include/linux/v130_kernel_api.h':'v130_kernel_api.h',
 'arch/arm64/mm/v130_handoff_core.c':'v130_handoff_core.c',
 'arch/arm64/mm/v130_kernel.c':'v130_kernel.c',
 'drivers/irqchip/v130_gic.inc':'v130_gic.inc',
 'drivers/clocksource/v130_timer.inc':'v130_timer.inc',
 'drivers/usb/dwc3/v130_usb.inc':'v130_usb.inc',
 'drivers/usb/dwc3/v130_usb_gadget.inc':'v130_usb_gadget.inc',
 'drivers/iommu/v130_iommu.inc':'v130_iommu.inc',
 'drivers/scsi/ufs/v130_ufs.inc':'v130_ufs.inc',
 'drivers/dma/v130_dmaengine.inc':'v130_dmaengine.inc',
 'drivers/dma/v130_pl330.inc':'v130_pl330.inc'}
KCONFIG=b'''
config NOTE10_XNU_KEXEC_HANDOFF
 bool "Note10 bounded actual-XNU legacy-kexec handoff"
 depends on ARM64 && ARM64_4K_PAGES && OF && SYSFS && KEXEC && SMP && HOTPLUG_CPU
 depends on SEC_REBOOT && EXYNOS_PMU && S3C2410_WATCHDOG && S3C2410_SHUTDOWN_REBOOT
 depends on ARM_GIC && ARM_ARCH_TIMER && USB_DWC3_GADGET && SCSI_UFSHCD && EXYNOS_IOMMU && PL330_DMA
 depends on !USB_XHCI_HCD && !SND_USB_AUDIO && !SND_EXYNOS_USB_AUDIO && !LINK_FORWARD && !USB_CONFIGFS
 default n
 help
   Source-bound owned32MiB placement, full-parcel/PID1 admission, EL1-preserving
   normal legacy kexec and actual driver terminal gates. Private content is
   inserted only locally into a bounded source-built initramfs slot.
   A generic Image is disabled. No hardware execution permission is implied.
'''
def sha(raw):return hashlib.sha256(raw).hexdigest()
def once(raw,old,new):
    if raw.count(old)!=1:raise ValueError('unique pinned v130 source boundary differs: '+old.decode()[:80])
    return raw.replace(old,new,1)


def render(stock,identity,source128):
    if re.fullmatch('[0-9a-f]{32}',identity or '') is None:raise ValueError('new CI source-bound build identity required')
    for name,pin in PINS.items():
        if sha(stock[name])!=pin:raise ValueError('stock source pin differs: '+name)
    output={}
    init=stock['arch/arm64/mm/init.c']
    init=once(init,b'void __init arm64_memblock_init(void)',b'''#ifdef CONFIG_NOTE10_XNU_KEXEC_HANDOFF
#include "n130_legacy_core.c"
#include "v130_handoff_core.c"
#include "v130_kernel.c"
#endif

void __init arm64_memblock_init(void)''')
    init=once(init,b'\tmemblock_allow_resize();',b'''#ifdef CONFIG_NOTE10_XNU_KEXEC_HANDOFF
    n10_early_kexec_destination();
#endif
\tmemblock_allow_resize();''');output['arch/arm64/mm/init.c']=init
    main=stock['init/main.c']
    main=once(main,b'#include <linux/init.h>',b'#include <linux/init.h>\n#include <linux/reboot.h>\n#include <linux/delay.h>')
    main=once(main,b'\tif (!ramdisk_execute_command)\n\t\tramdisk_execute_command = "/init";',b'''#ifdef CONFIG_NOTE10_XNU_KEXEC_HANDOFF
    ramdisk_execute_command = "/init";
#endif
\tif (!ramdisk_execute_command)
\t\tramdisk_execute_command = "/init";''')
    main=once(main,b'\tif (sys_access((const char __user *) ramdisk_execute_command, 0) != 0) {',b'''#ifdef CONFIG_NOTE10_XNU_KEXEC_HANDOFF
    if (sys_access((const char __user *) "/init", 0)) {
        kernel_restart("recovery");
        while (1) msleep(1000);
    }
#endif
\tif (sys_access((const char __user *) ramdisk_execute_command, 0) != 0) {''')
    main=once(main,b'\tif (ramdisk_execute_command) {\n\t\tret = run_init_process(ramdisk_execute_command);',b'''#ifdef CONFIG_NOTE10_XNU_KEXEC_HANDOFF
    ret = run_init_process("/init");
    if (!ret) return 0;
    kernel_restart("recovery");
    while (1) msleep(1000);
#endif
\tif (ramdisk_execute_command) {
\t\tret = run_init_process(ramdisk_execute_command);''');output['init/main.c']=main
    archive=stock['init/initramfs.c']
    archive=once(archive,b'''\tif (do_skip_initramfs) {
\t\tif (initrd_start)
\t\t\tfree_initrd();
\t\treturn default_rootfs();
\t}''',b'''\tif (do_skip_initramfs) {
\t\tif (initrd_start)
\t\t\tfree_initrd();
#ifndef CONFIG_NOTE10_XNU_KEXEC_HANDOFF
\t\treturn default_rootfs();
#else
        initrd_start = 0;
        initrd_end = 0;
#endif
\t}''');output['init/initramfs.c']=archive
    machine=stock['arch/arm64/kernel/machine_kexec.c']
    machine=once(machine,b'#include <linux/kexec.h>',b'''#include <linux/kexec.h>
#ifdef CONFIG_NOTE10_XNU_KEXEC_HANDOFF
#include <linux/legacy_kexec_return.h>
#include <linux/v130_kernel_api.h>
#include <asm/system_misc.h>
#endif''')
    machine=once(machine,b'int machine_kexec_prepare(struct kimage *kimage)\n{',b'''int machine_kexec_prepare(struct kimage *kimage)
{
#ifdef CONFIG_NOTE10_XNU_KEXEC_HANDOFF
    int n130_error = n10_kexec_check_image(kimage);
    if (n130_error) return n130_error;
#endif''')
    machine=once(machine,b'\t/* Disable all DAIF exceptions. */',b'''#ifdef CONFIG_NOTE10_XNU_KEXEC_HANDOFF
    if (n10_kexec_final_return(kimage)) {
        pr_emerg("N10XNU130 final gate refused; recovery is not XNU proof\\n");
        n130_terminal_recovery();
        BUG();
    }
#endif
\t/* Disable all DAIF exceptions. */''')
    machine=once(machine,b'\tcpu_soft_restart(kimage != kexec_crash_image,',b'''\tcpu_soft_restart(
#ifdef CONFIG_NOTE10_XNU_KEXEC_HANDOFF
        0, /* Source-bound preserve EL1: never HVC to EL2 for the EL1-only adapter. */
#else
        kimage != kexec_crash_image,
#endif''');output['arch/arm64/kernel/machine_kexec.c']=machine
    core=stock['kernel/kexec_core.c']
    core=b'#ifdef CONFIG_NOTE10_XNU_KEXEC_HANDOFF\n#include <linux/v130_kernel_api.h>\n#endif\n'+core
    core=once(core,b'\t\tkexec_in_progress = true;\n\t\tkernel_restart_prepare(NULL);',b'''#ifdef CONFIG_NOTE10_XNU_KEXEC_HANDOFF
        error = n130_before_shutdown(kexec_image);
        if (error) goto Unlock;
#endif
\t\tkexec_in_progress = true;
\t\tkernel_restart_prepare(NULL);''');output['kernel/kexec_core.c']=core
    core=once(core,b'\t\tkernel_restart_prepare(NULL);',b'''\t\tkernel_restart_prepare(NULL);
#ifdef CONFIG_NOTE10_XNU_KEXEC_HANDOFF
        error = n130_after_shutdown();
        if (error) {
            /* Device shutdown is destructive: no return to PID1 or retry. */
            n130_terminal_recovery();
            BUG();
        }
#endif''');output['kernel/kexec_core.c']=core
    reboot=stock['kernel/reboot.c']
    reboot=once(reboot,b'#include <linux/sec_debug.h>',b'''#include <linux/sec_debug.h>
#ifdef CONFIG_NOTE10_XNU_KEXEC_HANDOFF
#include <linux/legacy_kexec_return.h>
#include <linux/v130_kernel_api.h>
static int n130_kernel_restart(char *cmd);
#endif''')
    restart_start=reboot.index(b'void kernel_restart_prepare(char *cmd)\n{')
    restart_end=reboot.index(b'\n}\n',restart_start)+3
    restart_before=reboot[restart_start:restart_end]
    restart_after=once(restart_before,b'\tignore_fs_panic = 1;\n\tdevice_shutdown();',b'''\tignore_fs_panic = 1;
#ifdef CONFIG_NOTE10_XNU_KEXEC_HANDOFF
    if (!cmd && n130_before_device_shutdown()) {
        n130_terminal_recovery();
        BUG();
    }
#endif
\tdevice_shutdown();''')
    reboot=once(reboot,restart_before,restart_after)
    reboot=once(reboot,b'void kernel_restart(char *cmd)\n{',b'''#ifdef CONFIG_NOTE10_XNU_KEXEC_HANDOFF
static int n130_kernel_restart(char *cmd)
#else
void kernel_restart(char *cmd)
#endif
{
#ifdef CONFIG_NOTE10_XNU_KEXEC_HANDOFF
    if (cmd && !strcmp(cmd, "recovery")) {
        if (n130_recovery_claim()) return -EBUSY;
        if (n10_sec_stage_kexec_recovery()) return -EIO;
    }
#endif''')
    reboot=once(reboot,b'\tmachine_restart(cmd);\n}\nEXPORT_SYMBOL_GPL(kernel_restart);',b'''\tmachine_restart(cmd);
#ifdef CONFIG_NOTE10_XNU_KEXEC_HANDOFF
    return -EIO;
#endif
}
#ifdef CONFIG_NOTE10_XNU_KEXEC_HANDOFF
void kernel_restart(char *cmd) { (void)n130_kernel_restart(cmd); }
#endif
EXPORT_SYMBOL_GPL(kernel_restart);''')
    reboot=once(reboot,b'\t\tkernel_restart(buffer);',b'''#ifdef CONFIG_NOTE10_XNU_KEXEC_HANDOFF
        ret = n130_kernel_restart(buffer);
#else
\t\tkernel_restart(buffer);
#endif''');output['kernel/reboot.c']=reboot
    for name,include in [('drivers/samsung/sec_reboot.c','n130_marker.c'),('drivers/watchdog/s3c2410_wdt.c','n130_watchdog.c'),
                         ('drivers/irqchip/irq-gic.c','v130_gic.inc'),('drivers/clocksource/arm_arch_timer.c','v130_timer.inc'),
                         ('drivers/usb/dwc3/core.c','v130_usb.inc'),('drivers/usb/dwc3/gadget.c','v130_usb_gadget.inc'),
                         ('drivers/iommu/exynos-iommu.c','v130_iommu.inc'),('drivers/scsi/ufs/ufs-exynos.c','v130_ufs.inc'),('drivers/dma/dmaengine.c','v130_dmaengine.inc'),('drivers/dma/pl330.c','v130_pl330.inc')]:
        output[name]=stock[name]+b'\n#ifdef CONFIG_NOTE10_XNU_KEXEC_HANDOFF\n#include "'+include.encode()+b'"\n#endif\n'
    usb=output['drivers/usb/dwc3/core.c']
    usb=once(usb,b'\tdwc3_get_properties(dwc);',b'''\tdwc3_get_properties(dwc);
#ifdef CONFIG_NOTE10_XNU_KEXEC_HANDOFF
    dwc->dr_mode = USB_DR_MODE_PERIPHERAL;
#endif''')
    output['drivers/usb/dwc3/core.c']=usb
    gadget=output['drivers/usb/dwc3/gadget.c']
    gadget=once(gadget,b'''#ifdef CONFIG_USB_ANDROID_SAMSUNG_COMPOSITE
#include <linux/usb/composite.h>
#endif''',b'''#if defined(CONFIG_USB_ANDROID_SAMSUNG_COMPOSITE) || defined(CONFIG_NOTE10_XNU_KEXEC_HANDOFF)
#include <linux/usb/composite.h>
#endif''')
    output['drivers/usb/dwc3/gadget.c']=gadget
    # Record the actual primary GIC OF node only after its real probe succeeds.
    gic=output['drivers/irqchip/irq-gic.c']
    gic=b'#ifdef CONFIG_NOTE10_XNU_KEXEC_HANDOFF\nstatic struct device_node *n130_gic_node;\n#endif\n'+gic
    gic=once(gic,b'\tif (!gic_cnt) {\n\t\tgic_init_physaddr(node);',b'''\tif (!gic_cnt) {
#ifdef CONFIG_NOTE10_XNU_KEXEC_HANDOFF
        n130_gic_node = of_node_get(node);
#endif
\t\tgic_init_physaddr(node);''');output['drivers/irqchip/irq-gic.c']=gic
    ufs=stock['drivers/scsi/ufs/ufshcd.c']
    ufs=b'#ifdef CONFIG_NOTE10_XNU_KEXEC_HANDOFF\n#include <linux/v130_kernel_api.h>\n#endif\n'+ufs
    anchor=b'''\t/* allow force shutdown even in case of errors */'''
    ufs=once(ufs,anchor,b'''#ifdef CONFIG_NOTE10_XNU_KEXEC_HANDOFF
    n130_dma_record(hba->dev, ret || hba->curr_dev_pwr_mode!=UFS_POWERDOWN_PWR_MODE || !ufshcd_is_link_off(hba) ? -EIO : 0);
#endif
'''+anchor);output['drivers/scsi/ufs/ufshcd.c']=ufs
    engine=output['drivers/dma/dmaengine.c']
    engine=once(engine,b'static DEFINE_MUTEX(dma_list_mutex);',b'''static DEFINE_MUTEX(dma_list_mutex);
#ifdef CONFIG_NOTE10_XNU_KEXEC_HANDOFF
static int n130_dma_freeze;
static DEFINE_MUTEX(n130_dma_admission_mutex);
bool n130_dma_frozen(void) { return READ_ONCE(n130_dma_freeze); }
EXPORT_SYMBOL_GPL(n130_dma_frozen);
#endif''')
    engine=once(engine,b'static int dma_chan_get(struct dma_chan *chan)',b'''#ifdef CONFIG_NOTE10_XNU_KEXEC_HANDOFF
static int n130_dma_chan_get_inner(struct dma_chan *chan)
#else
static int dma_chan_get(struct dma_chan *chan)
#endif''')
    engine=once(engine,b'''/**
 * dma_chan_put - drop a reference to a dma channel's parent driver module''',b'''#ifdef CONFIG_NOTE10_XNU_KEXEC_HANDOFF
static int dma_chan_get(struct dma_chan *chan)
{
    int result;
    mutex_lock(&n130_dma_admission_mutex);
    result = n130_dma_chan_get_inner(chan);
    mutex_unlock(&n130_dma_admission_mutex);
    return result;
}
#endif
/**
 * dma_chan_put - drop a reference to a dma channel's parent driver module''')
    engine=once(engine,b'\t/* The channel is already in use, update client count */',b'''#ifdef CONFIG_NOTE10_XNU_KEXEC_HANDOFF
    if (n130_dma_frozen()) return -EBUSY;
#endif
\t/* The channel is already in use, update client count */''')
    engine=once(engine,b'\tmutex_lock(&dma_list_mutex);\n\t/* take references on public channels */',b'''\tmutex_lock(&dma_list_mutex);
#ifdef CONFIG_NOTE10_XNU_KEXEC_HANDOFF
    if (n130_dma_frozen()) { rc = -EBUSY; mutex_unlock(&dma_list_mutex); goto err_out; }
#endif
\t/* take references on public channels */''');output['drivers/dma/dmaengine.c']=engine
    header=stock['include/linux/dmaengine.h']
    header=once(header,b'static inline dma_cookie_t dmaengine_submit(struct dma_async_tx_descriptor *desc)',b'''#ifdef CONFIG_NOTE10_XNU_KEXEC_HANDOFF
bool n130_dma_frozen(void);
#endif
static inline dma_cookie_t dmaengine_submit(struct dma_async_tx_descriptor *desc)''')
    header=once(header,b'\treturn desc->tx_submit(desc);',b'''#ifdef CONFIG_NOTE10_XNU_KEXEC_HANDOFF
    if (n130_dma_frozen()) return -EBUSY;
#endif
\treturn desc->tx_submit(desc);''')
    header=once(header,b'\tchan->device->device_issue_pending(chan);',b'''#ifdef CONFIG_NOTE10_XNU_KEXEC_HANDOFF
    if (n130_dma_frozen()) return;
#endif
\tchan->device->device_issue_pending(chan);''');output['include/linux/dmaengine.h']=header
    pl330=output['drivers/dma/pl330.c']
    pl330=once(pl330,b'struct pl330_dmac {',b'''struct pl330_dmac {
#ifdef CONFIG_NOTE10_XNU_KEXEC_HANDOFF
    bool n130_ever_allocated;
#endif''')
    pl330=once(pl330,b'''\tspin_lock_irqsave(&pl330->lock, flags);

\tdma_cookie_init(chan);''',b'''#ifdef CONFIG_NOTE10_XNU_KEXEC_HANDOFF
    WRITE_ONCE(pl330->n130_ever_allocated, true);
#endif
\tspin_lock_irqsave(&pl330->lock, flags);

\tdma_cookie_init(chan);''');output['drivers/dma/pl330.c']=pl330
    # Fixed peripheral profile excludes real host-only consumers; no dummy providers.
    otg=stock['drivers/usb/dwc3/otg.c']
    otg=once(otg,b'static void dwc3_otg_set_host_mode(struct dwc3_otg *dotg)\n{\n\tstruct dwc3 *dwc = dotg->dwc;\n\tu32 reg;\n\n\tif (dotg->regs) {\n\t\treg = dwc3_readl(dotg->regs, DWC3_OCTL);\n\t\treg &= ~DWC3_OTG_OCTL_PERIMODE;\n\t\tdwc3_writel(dotg->regs, DWC3_OCTL, reg);\n\t} else {\n\t\tdwc3_set_mode(dwc, DWC3_GCTL_PRTCAP_HOST);\n\t}\n}',b'#ifndef CONFIG_NOTE10_XNU_KEXEC_HANDOFF\nstatic void dwc3_otg_set_host_mode(struct dwc3_otg *dotg)\n{\n\tstruct dwc3 *dwc = dotg->dwc;\n\tu32 reg;\n\n\tif (dotg->regs) {\n\t\treg = dwc3_readl(dotg->regs, DWC3_OCTL);\n\t\treg &= ~DWC3_OTG_OCTL_PERIMODE;\n\t\tdwc3_writel(dotg->regs, DWC3_OCTL, reg);\n\t} else {\n\t\tdwc3_set_mode(dwc, DWC3_GCTL_PRTCAP_HOST);\n\t}\n}\n#endif')
    otg=once(otg,b'static struct device_node *dwc3_otg_parse_dt(void)\n{\n\tstruct device_node *np = NULL;\n\n\tnp = of_find_compatible_node(NULL, NULL, "synopsys,dwc3");\n\tif (!np) {\n\t\tpr_err("%s: failed to get the dwc3 device node\\n",\n\t\t\t__func__);\n\t\tgoto err;\n\t}\n\treturn np;\nerr:\n\treturn NULL;\n}',b'#ifndef CONFIG_NOTE10_XNU_KEXEC_HANDOFF\nstatic struct device_node *dwc3_otg_parse_dt(void)\n{\n\tstruct device_node *np = NULL;\n\n\tnp = of_find_compatible_node(NULL, NULL, "synopsys,dwc3");\n\tif (!np) {\n\t\tpr_err("%s: failed to get the dwc3 device node\\n",\n\t\t\t__func__);\n\t\tgoto err;\n\t}\n\treturn np;\nerr:\n\treturn NULL;\n}\n#endif')
    otg=once(otg,b'static struct dwc3 *dwc3_otg_get_struct(void)\n{\n\tstruct device_node\t*np = NULL;\n\tstruct platform_device\t*pdev = NULL;\n\tstruct device\t\t*dev;\n\tstruct dwc3\t\t*dwc;\n\n\tnp = dwc3_otg_parse_dt();\n\tif (np) {\n\t\tpdev = of_find_device_by_node(np);\n\t\tdev = &pdev->dev;\n\t\tof_node_put(np);\n\t\tif (pdev) {\n\t\t\tpr_info("%s: get the %s platform_device\\n",\n\t\t\t\t__func__, pdev->name);\n\n\t\t\tdwc = dev->driver_data;\n\t\t\treturn dwc;\n\t\t}\n\t}\n\n\tpr_err("%s: failed to get the platform_device\\n", __func__);\n\treturn NULL;\n}',b'#ifndef CONFIG_NOTE10_XNU_KEXEC_HANDOFF\nstatic struct dwc3 *dwc3_otg_get_struct(void)\n{\n\tstruct device_node\t*np = NULL;\n\tstruct platform_device\t*pdev = NULL;\n\tstruct device\t\t*dev;\n\tstruct dwc3\t\t*dwc;\n\n\tnp = dwc3_otg_parse_dt();\n\tif (np) {\n\t\tpdev = of_find_device_by_node(np);\n\t\tdev = &pdev->dev;\n\t\tof_node_put(np);\n\t\tif (pdev) {\n\t\t\tpr_info("%s: get the %s platform_device\\n",\n\t\t\t\t__func__, pdev->name);\n\n\t\t\tdwc = dev->driver_data;\n\t\t\treturn dwc;\n\t\t}\n\t}\n\n\tpr_err("%s: failed to get the platform_device\\n", __func__);\n\treturn NULL;\n}\n#endif')
    otg=once(otg,b'void dwc3_otg_check_bus_act(struct dwc3 *dwc)\n{\n\tu32 reg;\n\tu32 xm_wtran, xm_rtran, xm_ch_status;\n\tint retries = 100;\n\n\treg = dwc3_readl(dwc->regs, DWC3_GDBGLSPMUX_HST);\n\treg |= BUS_ACTIVITY_CHECK;\n\tdwc3_writel(dwc->regs, DWC3_GDBGLSPMUX_HST, reg);\n\n\tdo {\n\t\treg = readl(phycon_base_addr + LINK_DEBUG_L);\n\t\txm_ch_status = reg & 0x3FF;\n\t\txm_rtran = (reg >> READ_TRANS_OFFSET) & 0x3FFFFF;\n\t\treg = readl(phycon_base_addr + LINK_DEBUG_H);\n\t\txm_wtran = reg & 0x3FFFFF;\n\n\t\tif (!xm_rtran && !xm_wtran)\n\t\t\tbreak;\n\t\tmdelay(1);\n\t} while (--retries);\n\n\tpr_info("%s %s: retries = %d\\n", __func__,\n\t\tretries ? "clear" : "timeout", retries);\n}',b'#ifndef CONFIG_NOTE10_XNU_KEXEC_HANDOFF\nvoid dwc3_otg_check_bus_act(struct dwc3 *dwc)\n{\n\tu32 reg;\n\tu32 xm_wtran, xm_rtran, xm_ch_status;\n\tint retries = 100;\n\n\treg = dwc3_readl(dwc->regs, DWC3_GDBGLSPMUX_HST);\n\treg |= BUS_ACTIVITY_CHECK;\n\tdwc3_writel(dwc->regs, DWC3_GDBGLSPMUX_HST, reg);\n\n\tdo {\n\t\treg = readl(phycon_base_addr + LINK_DEBUG_L);\n\t\txm_ch_status = reg & 0x3FF;\n\t\txm_rtran = (reg >> READ_TRANS_OFFSET) & 0x3FFFFF;\n\t\treg = readl(phycon_base_addr + LINK_DEBUG_H);\n\t\txm_wtran = reg & 0x3FFFFF;\n\n\t\tif (!xm_rtran && !xm_wtran)\n\t\t\tbreak;\n\t\tmdelay(1);\n\t} while (--retries);\n\n\tpr_info("%s %s: retries = %d\\n", __func__,\n\t\tretries ? "clear" : "timeout", retries);\n}\n#endif')
    otg=once(otg,b'static int dwc3_otg_start_host(struct otg_fsm *fsm, int on)\n{\n\tstruct usb_otg\t*otg = fsm->otg;\n\tstruct dwc3_otg\t*dotg = container_of(otg, struct dwc3_otg, otg);\n\tstruct dwc3\t*dwc = dotg->dwc;\n\tstruct device\t*dev = dotg->dwc->dev;\n\tint ret = 0;\n\tint ret1 = -1;\n\n\tif (!dotg->dwc->xhci) {\n\t\tdev_err(dev, "%s: does not have any xhci\\n", __func__);\n\t\treturn -EINVAL;\n\t}\n\n\tdev_info(dev, "Turn %s host\\n", on ? "on" : "off");\n\tif (on) {\n\t\totg_connection = 1;\n\t\tret = dwc3_otg_phy_enable(fsm, 0, on);\n\t\tif (ret) {\n\t\t\tdev_err(dwc->dev, "%s: failed to reinitialize core\\n",\n\t\t\t\t\t__func__);\n\t\t\tgoto err1;\n\t\t}\n\n\t\t/**\n\t\t * In case there is not a resistance to detect VBUS,\n\t\t * DP/DM controls by S/W are needed at this point.\n\t\t */\n\t\tif (dwc->is_not_vbus_pad) {\n\t\t\tphy_set(dwc->usb2_generic_phy,\n\t\t\t\t\tSET_DPDM_PULLDOWN, NULL);\n\t\t\tphy_set(dwc->usb3_generic_phy,\n\t\t\t\t\tSET_DPDM_PULLDOWN, NULL);\n\t\t}\n\n\t\tdwc3_otg_set_host_mode(dotg);\n\t\tret = platform_device_add(dwc->xhci);\n\t\tif (ret) {\n\t\t\tdev_err(dev, "%s: cannot add xhci\\n", __func__);\n\t\t\tgoto err2;\n\t\t}\n#if defined(CONFIG_USB_PORT_POWER_OPTIMIZATION)\n\t\tregister_usb_power_notify();\n#endif\n#if defined(CONFIG_CCIC_MAX77705)\n\t\tmax77705_set_host_turn_on_event(on);\n#endif\n\t} else {\n#if defined(CONFIG_CCIC_MAX77705)\n\t\tmax77705_set_host_turn_on_event(on);\n#endif\n#if defined(CONFIG_USB_PORT_POWER_OPTIMIZATION)\n\t\txhci_port_power_set(1, 3);\n\t\tunregister_usb_power_notify();\n#endif\n\n#ifdef CONFIG_SND_EXYNOS_USB_AUDIO\n\t\totg_connection = 0;\n#endif\n\t\tif (dotg->dwc3_suspended) {\n\t\t\tpr_info("%s: wait resume completion\\n", __func__);\n\t\t\tret1 = wait_for_completion_timeout(&dotg->resume_cmpl,\n\t\t\t\t\t\t\tmsecs_to_jiffies(5000));\n\t\t}\n\n#ifdef CONFIG_SND_EXYNOS_USB_AUDIO\n\t\tif (usb_audio->usb_audio_state !=\n\t\t    USB_AUDIO_DISCONNECT) {\n\t\t\tpr_info("%s: wait audio disconnect\\n", __func__);\n\t\t\tret1 = wait_for_completion_timeout(&usb_audio\n\t\t\t\t\t\t->discon_done,\n\t\t\t\t\t\tmsecs_to_jiffies(1000));\n\t\t}\n#endif\n\t\tplatform_device_del(dwc->xhci);\nerr2:\n\t\tret = dwc3_otg_phy_enable(fsm, 0, on);\n\t}\nerr1:\n\treturn ret;\n}',b'#ifndef CONFIG_NOTE10_XNU_KEXEC_HANDOFF\nstatic int dwc3_otg_start_host(struct otg_fsm *fsm, int on)\n{\n\tstruct usb_otg\t*otg = fsm->otg;\n\tstruct dwc3_otg\t*dotg = container_of(otg, struct dwc3_otg, otg);\n\tstruct dwc3\t*dwc = dotg->dwc;\n\tstruct device\t*dev = dotg->dwc->dev;\n\tint ret = 0;\n\tint ret1 = -1;\n\n\tif (!dotg->dwc->xhci) {\n\t\tdev_err(dev, "%s: does not have any xhci\\n", __func__);\n\t\treturn -EINVAL;\n\t}\n\n\tdev_info(dev, "Turn %s host\\n", on ? "on" : "off");\n\tif (on) {\n\t\totg_connection = 1;\n\t\tret = dwc3_otg_phy_enable(fsm, 0, on);\n\t\tif (ret) {\n\t\t\tdev_err(dwc->dev, "%s: failed to reinitialize core\\n",\n\t\t\t\t\t__func__);\n\t\t\tgoto err1;\n\t\t}\n\n\t\t/**\n\t\t * In case there is not a resistance to detect VBUS,\n\t\t * DP/DM controls by S/W are needed at this point.\n\t\t */\n\t\tif (dwc->is_not_vbus_pad) {\n\t\t\tphy_set(dwc->usb2_generic_phy,\n\t\t\t\t\tSET_DPDM_PULLDOWN, NULL);\n\t\t\tphy_set(dwc->usb3_generic_phy,\n\t\t\t\t\tSET_DPDM_PULLDOWN, NULL);\n\t\t}\n\n\t\tdwc3_otg_set_host_mode(dotg);\n\t\tret = platform_device_add(dwc->xhci);\n\t\tif (ret) {\n\t\t\tdev_err(dev, "%s: cannot add xhci\\n", __func__);\n\t\t\tgoto err2;\n\t\t}\n#if defined(CONFIG_USB_PORT_POWER_OPTIMIZATION)\n\t\tregister_usb_power_notify();\n#endif\n#if defined(CONFIG_CCIC_MAX77705)\n\t\tmax77705_set_host_turn_on_event(on);\n#endif\n\t} else {\n#if defined(CONFIG_CCIC_MAX77705)\n\t\tmax77705_set_host_turn_on_event(on);\n#endif\n#if defined(CONFIG_USB_PORT_POWER_OPTIMIZATION)\n\t\txhci_port_power_set(1, 3);\n\t\tunregister_usb_power_notify();\n#endif\n\n#ifdef CONFIG_SND_EXYNOS_USB_AUDIO\n\t\totg_connection = 0;\n#endif\n\t\tif (dotg->dwc3_suspended) {\n\t\t\tpr_info("%s: wait resume completion\\n", __func__);\n\t\t\tret1 = wait_for_completion_timeout(&dotg->resume_cmpl,\n\t\t\t\t\t\t\tmsecs_to_jiffies(5000));\n\t\t}\n\n#ifdef CONFIG_SND_EXYNOS_USB_AUDIO\n\t\tif (usb_audio->usb_audio_state !=\n\t\t    USB_AUDIO_DISCONNECT) {\n\t\t\tpr_info("%s: wait audio disconnect\\n", __func__);\n\t\t\tret1 = wait_for_completion_timeout(&usb_audio\n\t\t\t\t\t\t->discon_done,\n\t\t\t\t\t\tmsecs_to_jiffies(1000));\n\t\t}\n#endif\n\t\tplatform_device_del(dwc->xhci);\nerr2:\n\t\tret = dwc3_otg_phy_enable(fsm, 0, on);\n\t}\nerr1:\n\treturn ret;\n}\n#endif')
    otg=once(otg,b'int exynos_usbdrd_inform_dp_use(int use, int lane_cnt)\n{\n\tstruct dwc3\t*dwc;\n\tstruct dwc3_otg\t*dotg;\n\tint ret = 0;\n\n\tpr_info("[%s] dp use = %d, lane_cnt = %d\\n",\n\t\t\t__func__, use, lane_cnt);\n\n\tdwc = dwc3_otg_get_struct();\n\tif (!dwc) {\n\t\tpr_err("[%s] dwc3_otg_get_struct error\\n", __func__);\n\t\treturn -ENODEV;\n\t}\n\tdotg = dwc->dotg;\n\tdotg->dp_use_informed = use;\n\n\tif ((use == 1) && (lane_cnt == 4)) {\n\t\tret = xhci_portsc_set(0);\n\t\tudelay(1);\n\t}\n\n\treturn ret;\n}',b'int exynos_usbdrd_inform_dp_use(int use, int lane_cnt)\n{\n#ifdef CONFIG_NOTE10_XNU_KEXEC_HANDOFF\n    /* Host/DP lane handoff is unavailable in this fixed peripheral profile. */\n    (void)use; (void)lane_cnt; return -EOPNOTSUPP;\n#else\n\tstruct dwc3\t*dwc;\n\tstruct dwc3_otg\t*dotg;\n\tint ret = 0;\n\n\tpr_info("[%s] dp use = %d, lane_cnt = %d\\n",\n\t\t\t__func__, use, lane_cnt);\n\n\tdwc = dwc3_otg_get_struct();\n\tif (!dwc) {\n\t\tpr_err("[%s] dwc3_otg_get_struct error\\n", __func__);\n\t\treturn -ENODEV;\n\t}\n\tdotg = dwc->dotg;\n\tdotg->dp_use_informed = use;\n\n\tif ((use == 1) && (lane_cnt == 4)) {\n\t\tret = xhci_portsc_set(0);\n\t\tudelay(1);\n\t}\n\n\treturn ret;\n\n#endif\n}')
    otg=once(otg,b'\t\t\tdwc3_otg_check_bus_act(dwc);',b'#ifndef CONFIG_NOTE10_XNU_KEXEC_HANDOFF\n\t\t\tdwc3_otg_check_bus_act(dwc);\n#endif')
    otg=once(otg,b'\t.start_host\t= dwc3_otg_start_host,',b'#ifndef CONFIG_NOTE10_XNU_KEXEC_HANDOFF\n\t.start_host\t= dwc3_otg_start_host,\n#endif')
    output['drivers/usb/dwc3/otg.c']=otg
    manager=stock['drivers/usb/manager/usb_typec_manager_notifier.c']
    manager=once(manager,b'\tdwc3_link_check= dwc3_gadget_get_cmply_link_state_wrapper();',b'#ifndef CONFIG_NOTE10_XNU_KEXEC_HANDOFF\n\tdwc3_link_check= dwc3_gadget_get_cmply_link_state_wrapper();\n#else\n    /* No configfs composite client exists; retain the no-enumeration PHY-off route. */\n    dwc3_link_check = -ENODEV;\n#endif')
    output['drivers/usb/manager/usb_typec_manager_notifier.c']=manager
    gadget=output['drivers/usb/dwc3/gadget.c']
    gadget=once(gadget,b'extern bool acc_dev_status;',b'#ifndef CONFIG_NOTE10_XNU_KEXEC_HANDOFF\nextern bool acc_dev_status;\n#endif')
    gadget=once(gadget,b'\tacc_dev_status = 0;',b'#ifndef CONFIG_NOTE10_XNU_KEXEC_HANDOFF\n\tacc_dev_status = 0;\n#endif')
    gadget=once(gadget,b'\tktime_t current_time;',b'#ifndef CONFIG_NOTE10_XNU_KEXEC_HANDOFF\n\tktime_t current_time;\n#endif')
    gadget=once(gadget,b'\tif (acc_dev_status && (dwc->rst_err_noti == false)) {\n\t\tcurrent_time = ktime_to_ms(ktime_get_boottime());\n\n\t\tif ((dwc->rst_err_cnt == 0) && (dwc->gadget.state < USB_STATE_CONFIGURED)) {\n\t\t\tif ((current_time - dwc->rst_time_before) < 1000) {\n\t\t\t\tdwc->rst_err_cnt++;\n\t\t\t\tdwc->rst_time_first = dwc->rst_time_before;\n\t\t\t}\n\t\t} else {\n\t\t\tif ((current_time - dwc->rst_time_first) < 1000) {\n\t\t\t\tdwc->rst_err_cnt++;\n\t\t\t} else {\n\t\t\t\tdwc->rst_err_cnt = 0;\n\t\t\t}\n\t\t}\n\n\t\tif (dwc->rst_err_cnt > ERR_RESET_CNT) {\n\t\t\tdwc->event_state = NOTIFY;\n\t\t\tschedule_delayed_work(&dwc->usb_event_work, msecs_to_jiffies(0));\n\t\t\tdwc->rst_err_noti = true;\n\t\t}\n\n\t\tpr_info("%s rst_err_cnt: %d, time_current: %lld, time_before: %lld\\n",\n\t\t\t__func__, dwc->rst_err_cnt, current_time, dwc->rst_time_before);\n\n\t\tdwc->rst_time_before = current_time;\n\t}',b'#ifndef CONFIG_NOTE10_XNU_KEXEC_HANDOFF\n\tif (acc_dev_status && (dwc->rst_err_noti == false)) {\n\t\tcurrent_time = ktime_to_ms(ktime_get_boottime());\n\n\t\tif ((dwc->rst_err_cnt == 0) && (dwc->gadget.state < USB_STATE_CONFIGURED)) {\n\t\t\tif ((current_time - dwc->rst_time_before) < 1000) {\n\t\t\t\tdwc->rst_err_cnt++;\n\t\t\t\tdwc->rst_time_first = dwc->rst_time_before;\n\t\t\t}\n\t\t} else {\n\t\t\tif ((current_time - dwc->rst_time_first) < 1000) {\n\t\t\t\tdwc->rst_err_cnt++;\n\t\t\t} else {\n\t\t\t\tdwc->rst_err_cnt = 0;\n\t\t\t}\n\t\t}\n\n\t\tif (dwc->rst_err_cnt > ERR_RESET_CNT) {\n\t\t\tdwc->event_state = NOTIFY;\n\t\t\tschedule_delayed_work(&dwc->usb_event_work, msecs_to_jiffies(0));\n\t\t\tdwc->rst_err_noti = true;\n\t\t}\n\n\t\tpr_info("%s rst_err_cnt: %d, time_current: %lld, time_before: %lld\\n",\n\t\t\t__func__, dwc->rst_err_cnt, current_time, dwc->rst_time_before);\n\n\t\tdwc->rst_time_before = current_time;\n\t}\n#endif')
    output['drivers/usb/dwc3/gadget.c']=gadget
    output['arch/arm64/Kconfig']=stock['arch/arm64/Kconfig']+KCONFIG
    output['include/linux/note10_legacy_kexec_build.h']=('#define N10_KEXEC_BUILD_ID "'+identity+'"\n').encode()
    for target,name in COMMON.items():output[target]=(Path(source128)/'note10/device_test'/name).read_bytes()
    for target,name in OWN.items():output[target]=(HERE/name).read_bytes()
    return output


def install(source,identity,source128):
    source=Path(source).resolve();stock={name:(source/name).read_bytes() for name in PINS}
    output=render(stock,identity,source128)
    for name in output:
        path=source/name
        if not path.resolve().is_relative_to(source) or any(p.is_symlink() for p in (path,*path.parents)):raise ValueError('unsafe overlay path')
        if name not in PINS and path.exists():raise ValueError('new source component already exists')
    for name,raw in output.items():
        path=source/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
    return {name:sha(raw) for name,raw in output.items()}
