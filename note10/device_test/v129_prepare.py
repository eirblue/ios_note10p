"""Successor producer: immutable128 backend plus opt-in129 builtin/PID1 policy."""
from pathlib import Path
from v129_inputs import module,digest

HERE=Path(__file__).resolve().parent
INITRAMFS_PIN='1a9af19668584dc664c28c640e02b6a03cc37a2fa5ecd1900d818bb67c775806'
FDT_PIN='e655d0f3902e4559932a8c262177a74623468caeda04b338c2de81d992593b34'
REBOOT_PIN='ed27858a87e0b7fe098510f03054c034a333874017444de2052af3e691d5b3f8'
OPTION='NOTE10_LEGACY_KEXEC_RECOVERY_PROOF'


def setup(inputs):
    frozen=module(inputs,'prepare_legacy_kexec_recovery.py')
    return frozen,{**frozen.PINS,'init/initramfs.c':INITRAMFS_PIN,'drivers/of/fdt.c':FDT_PIN,'kernel/reboot.c':REBOOT_PIN}


def render(stock,identity,inputs):
    frozen,pins=setup(inputs)
    for name,pin in pins.items():
        if digest(stock[name])!=pin:raise ValueError('pinned129 input differs: '+name)
    output=frozen.render(stock,identity)
    old=b'''\tif (do_skip_initramfs) {
\t\tif (initrd_start)
\t\t\tfree_initrd();
\t\treturn default_rootfs();
\t}'''
    new=b'''\tif (do_skip_initramfs) {
\t\tif (initrd_start)
\t\t\tfree_initrd();
#ifndef CONFIG_NOTE10_LEGACY_KEXEC_RECOVERY_PROOF
\t\treturn default_rootfs();
#else
        /* Proof mode retains builtin PID1, even with Samsung bare skip. */
        initrd_start = 0;
        initrd_end = 0;
        pr_info("N10INIT129 skip external initrd; retain builtin proof init\\n");
#endif
\t}'''
    output['init/initramfs.c']=frozen.once(stock['init/initramfs.c'],old,new)
    main=output['init/main.c']
    main=frozen.once(main,b'        panic("Note10 proof init missing; no block root fallback");',
        b'''    {
        kernel_restart("recovery");
        pr_emerg("N10REC129 missing init recovery returned; terminal no retry\\n");
        while (1)
            msleep(1000);
    }''')
    main=frozen.once(main,b'    panic("Note10 proof init failed: %d", ret);',
        b'''    kernel_restart("recovery");
    pr_emerg("N10REC129 init exec failed %d recovery returned; terminal no retry\\n", ret);
    while (1)
        msleep(1000);''')
    if b'#include <linux/reboot.h>' not in main:
        main=frozen.once(main,b'#include <linux/init.h>',b'#include <linux/init.h>\n#include <linux/reboot.h>')
    if b'#include <linux/delay.h>' not in main:
        main=frozen.once(main,b'#include <linux/init.h>',b'#include <linux/init.h>\n#include <linux/delay.h>')
    output['init/main.c']=main
    reboot=stock['kernel/reboot.c']
    reboot=frozen.once(reboot,b'#include <linux/sec_debug.h>',b'''#include <linux/sec_debug.h>
#ifdef CONFIG_NOTE10_LEGACY_KEXEC_RECOVERY_PROOF
#include <linux/legacy_kexec_return.h>
static int n10_proof_kernel_restart(char *cmd);
#endif''')
    reboot=frozen.once(reboot,b'void kernel_restart(char *cmd)\n{',b'''#ifdef CONFIG_NOTE10_LEGACY_KEXEC_RECOVERY_PROOF
static int n10_proof_kernel_restart(char *cmd)
#else
void kernel_restart(char *cmd)
#endif
{
#ifdef CONFIG_NOTE10_LEGACY_KEXEC_RECOVERY_PROOF
    /* Before notifier/device shutdown can start WDT, also for early PID1 errors. */
    if (cmd && !strcmp(cmd, "recovery") && n10_sec_stage_kexec_recovery()) {
        pr_emerg("N10REC129 early recovery marker failed; no shutdown/no retry\\n");
        return -EIO;
    }
#endif''')
    reboot=frozen.once(reboot,b'\tmachine_restart(cmd);\n}\nEXPORT_SYMBOL_GPL(kernel_restart);',b'''\tmachine_restart(cmd);
#ifdef CONFIG_NOTE10_LEGACY_KEXEC_RECOVERY_PROOF
    return -EIO; /* Any returned restart is failure, never a successful reset. */
#endif
}
#ifdef CONFIG_NOTE10_LEGACY_KEXEC_RECOVERY_PROOF
void kernel_restart(char *cmd)
{
    (void)n10_proof_kernel_restart(cmd);
}
#endif
EXPORT_SYMBOL_GPL(kernel_restart);''')
    reboot=frozen.once(reboot,b'\t\tkernel_restart(buffer);',b'''#ifdef CONFIG_NOTE10_LEGACY_KEXEC_RECOVERY_PROOF
        ret = n10_proof_kernel_restart(buffer);
#else
\t\tkernel_restart(buffer);
#endif''')
    output['kernel/reboot.c']=reboot
    return output


def install(source,identity,inputs):
    source=Path(source).resolve();_,pins=setup(inputs)
    stock={name:(source/name).read_bytes() for name in pins}
    output=render(stock,identity,inputs)
    for name in output:
        path=source/name
        if not path.resolve().is_relative_to(source) or any(p.is_symlink() for p in (path,*path.parents)):
            raise ValueError('unsafe successor overlay path')
        if name not in pins and path.exists():raise ValueError('successor overlay exists')
    for name,raw in output.items():
        path=source/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
    return {name:digest(raw) for name,raw in output.items()}
