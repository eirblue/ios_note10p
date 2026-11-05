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
