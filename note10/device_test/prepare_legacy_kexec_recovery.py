"""Source-pinned, default-off real kexec proof backend. No hardware operation."""
import hashlib
from pathlib import Path
import re

HERE=Path(__file__).resolve().parent
PINS={
 "arch/arm64/mm/init.c": "cc990de7d8222f56fd71519c8b5dbf87a50abd4131e9eeb49ba78c04e3b6e3f3",
 "init/main.c": "4493d28f7aacf7de510e7cdc1864fb359278f2f88233abcea6b77a39cb8e0b70",
 "arch/arm64/kernel/machine_kexec.c": "341ab6c94215cb93c2e1a4ee39f9058bb9bd114de17c8a979ef77144cf67e5e6",
 "drivers/samsung/sec_reboot.c": "9c598d65fac6c7be4ba9bcf1d3f6d7d5ec218844c28b97653deabc707190d594",
 "drivers/watchdog/s3c2410_wdt.c": "cea425d01ca901671ee67b644a15a0ee19271c970972894a2be52540f7186166",
 "arch/arm64/Kconfig": "127273290ce9e8d337b0f186b576dac0ff3792bcbebffeea2ae49b9c5e99afc6"
}
OPTION='NOTE10_LEGACY_KEXEC_RECOVERY_PROOF'
COPIES={
 'include/linux/legacy_kexec_core.h':'legacy_kexec_core.h',
 'include/linux/legacy_kexec_return.h':'legacy_kexec_return.h',
 'arch/arm64/mm/legacy_kexec_core.c':'legacy_kexec_core.c',
 'arch/arm64/mm/note10_legacy_kexec_reservation.c':'legacy_kexec_reservation.c',
 'drivers/samsung/note10_legacy_kexec_marker.c':'legacy_kexec_marker.c',
 'drivers/watchdog/note10_legacy_kexec_watchdog.c':'legacy_kexec_watchdog.c',
}
KCONFIG=b'''
config NOTE10_LEGACY_KEXEC_RECOVERY_PROOF
 bool "Note10 bounded legacy-kexec watchdog recovery proof"
 depends on ARM64 && ARM64_4K_PAGES && OF && SYSFS && KEXEC
 depends on SEC_REBOOT && EXYNOS_PMU && S3C2410_WATCHDOG && S3C2410_SHUTDOWN_REBOOT
 default n
 help
   Reserve a fresh32MiB destination before allocator use. Expose one-shot
   same-boot admission to an opt-in proof PID1 and qualify recovery marker
   and real watchdog immediately before native kexec MMU-off handoff.
   The payload parks, never executes XNU. No device permission is implied.
'''


def sha(raw):return hashlib.sha256(raw).hexdigest()


def once(raw,anchor,replacement):
    if raw.count(anchor)!=1:raise ValueError('unique pinned source boundary differs: '+anchor.decode()[:80])
    return raw.replace(anchor,replacement,1)


def render(stock,identity):
    if re.fullmatch('[0-9a-f]{32}',identity or '') is None:raise ValueError('source-bound build identity required')
    for name,pin in PINS.items():
        if sha(stock[name])!=pin:raise ValueError('stock source pin differs: '+name)
    output={}
    init=stock['arch/arm64/mm/init.c']
    declaration=b'void __init arm64_memblock_init(void)'
    init=once(init,declaration,b'''#ifdef CONFIG_NOTE10_LEGACY_KEXEC_RECOVERY_PROOF
#include "legacy_kexec_core.c"
#include "note10_legacy_kexec_reservation.c"
#endif

'''+declaration)
    # After kernel/initrd/DT/crash/elfcore/CMA exclusions, before bootmem release.
    init=once(init,b'\tmemblock_allow_resize();',b'''#ifdef CONFIG_NOTE10_LEGACY_KEXEC_RECOVERY_PROOF
    n10_early_kexec_destination();
#endif
\tmemblock_allow_resize();''')
    output['arch/arm64/mm/init.c']=init
    main=stock['init/main.c']
    main=once(main,b'\tif (!ramdisk_execute_command)\n\t\tramdisk_execute_command = "/init";',b'''#ifdef CONFIG_NOTE10_LEGACY_KEXEC_RECOVERY_PROOF
    ramdisk_execute_command = "/init";
#endif
\tif (!ramdisk_execute_command)
\t\tramdisk_execute_command = "/init";''')
    main=once(main,b'\tif (sys_access((const char __user *) ramdisk_execute_command, 0) != 0) {',b'''#ifdef CONFIG_NOTE10_LEGACY_KEXEC_RECOVERY_PROOF
    if (sys_access((const char __user *) "/init", 0))
        panic("Note10 proof init missing; no block root fallback");
#endif
\tif (sys_access((const char __user *) ramdisk_execute_command, 0) != 0) {''')
    main=once(main,b'\tif (ramdisk_execute_command) {\n\t\tret = run_init_process(ramdisk_execute_command);',b'''#ifdef CONFIG_NOTE10_LEGACY_KEXEC_RECOVERY_PROOF
    ret = run_init_process("/init");
    if (!ret)
        return 0;
    panic("Note10 proof init failed: %d", ret);
#endif
\tif (ramdisk_execute_command) {
\t\tret = run_init_process(ramdisk_execute_command);''')
    output['init/main.c']=main
    machine=stock['arch/arm64/kernel/machine_kexec.c']
    machine=once(machine,b'#include <linux/kexec.h>',b'''#include <linux/kexec.h>
#ifdef CONFIG_NOTE10_LEGACY_KEXEC_RECOVERY_PROOF
#include <linux/legacy_kexec_return.h>
#include <asm/system_misc.h>
#endif''')
    machine=once(machine,b'int machine_kexec_prepare(struct kimage *kimage)\n{',b'''int machine_kexec_prepare(struct kimage *kimage)
{
#ifdef CONFIG_NOTE10_LEGACY_KEXEC_RECOVERY_PROOF
    int n10_error = n10_kexec_check_image(kimage);
    if (n10_error)
        return n10_error;
#endif''')
    machine=once(machine,b'\t/* Disable all DAIF exceptions. */',b'''#ifdef CONFIG_NOTE10_LEGACY_KEXEC_RECOVERY_PROOF
    if (n10_kexec_final_return(kimage)) {
        pr_emerg("N10KRET1 qualification failed; SW fallback is NOT proof\\n");
        machine_restart("recovery");
        BUG();
    }
#endif
\t/* Disable all DAIF exceptions. */''')
    output['arch/arm64/kernel/machine_kexec.c']=machine
    for target,include in (('drivers/samsung/sec_reboot.c','note10_legacy_kexec_marker.c'),
                           ('drivers/watchdog/s3c2410_wdt.c','note10_legacy_kexec_watchdog.c')):
        output[target]=stock[target]+b'\n#ifdef CONFIG_NOTE10_LEGACY_KEXEC_RECOVERY_PROOF\n#include "'+include.encode()+b'"\n#endif\n'
    output['arch/arm64/Kconfig']=stock['arch/arm64/Kconfig']+KCONFIG
    output['include/linux/note10_legacy_kexec_build.h']=('#define N10_KEXEC_BUILD_ID "'+identity+'"\n').encode()
    for target,original in COPIES.items():output[target]=(HERE/original).read_bytes()
    return output


def install(source,identity):
    source=Path(source).resolve()
    stock={name:(source/name).read_bytes() for name in PINS}
    output=render(stock,identity)
    for name in output:
        path=source/name
        if not path.resolve().is_relative_to(source) or any(p.is_symlink() for p in (path,*path.parents)):
            raise ValueError('unsafe source overlay path')
        if name not in PINS and path.exists():raise ValueError('new source already exists')
    for name,raw in output.items():
        path=source/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
    return {name:sha(raw) for name,raw in output.items()}
