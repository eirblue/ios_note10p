"""Fresh source-owned SCORE terminal provider over immutable v132 rendering."""
from pathlib import Path
import re
import v132_prepare as retained
HERE=Path(__file__).resolve().parent
OPTION=retained.OPTION
PINS=dict(retained.PINS)
PINS.update({'drivers/vision/score/score_device.c': '43de590af0c2e6145ef4f33c6663a70752e53b181a84f6139505108ebcabc032', 'drivers/vision/score/score_device.h': '26e4eedcde96414cc06601a6986a4188deb728f3260a9054a4e59552f95084fe', 'drivers/vision/score/score_core.c': '9a2bcdc60305c0b70330ff74fc051b48f03598c06449e2e24a75dd13c37a7100', 'drivers/vision/score/score_core.h': '068e0c14acf8bbac6a2bda3434631280391e01426cfef43c97da8b9d2ebb2acb', 'drivers/vision/score/score_context.c': '2607af7edf90c8becc9d8d58309620c80e3f70c78ad24309ed5eafe814688f58', 'drivers/vision/score/score_frame.c': '58de702e593f7abb76f3060e1a6eb4340f85d5ac272394bd64f6bd7a534490f2', 'drivers/vision/score/score_frame.h': 'dfc16c778feb1694d4f9ee76c4ccb58f9b5ebe8d87966c3df73ca1004cccb35b', 'drivers/vision/score/score_mmu.c': 'a073c53e50f895a93265542ee2f491a9d5d4459b6eccfb3a9703f2116bee2084', 'drivers/vision/score/score_mmu.h': 'd97cde5ceab0c1e309c21a494f0e378fbcf52305b8cfa3bf74442cc536f29e60', 'drivers/vision/score/Kconfig': '3c9f2e65218b0872974c26e75da606f59992253ee1036fe390ca4e2f6fa6eaa9', 'drivers/vision/score/Makefile': '60a6bac84a817c8b67fe0ae11d400e14ba89fc88f54fc12af866ac20f0dfd1d9', 'drivers/vision/score/hardware/v3/score_system.c': 'df1be68b0bbba4481fa63ea023a272beaf5df48788c5ea920832a12490ccf6b4', 'drivers/vision/score/hardware/v3/score_system.h': '3dcb8ac3826cb1027e998388ee287ebae8d85bc18c9694887ef25909b70c9aa7', 'drivers/vision/score/hardware/v3/score_interface.c': '257b1914d06c2507a2525777a518eef089afc5f5c674542119420d863ab64e32', 'drivers/vision/score/hardware/v3/score_interface.h': '6ad4f499c2906a6162da900350d40d2da9a4c3fa97ce7626da49eee417e51728', 'drivers/vision/score/hardware/v3/score_scq.c': 'fa6e7093cf0fb70c84549b343b07009e31cf8a5afb2ba4fdd227d5818b95f3f5', 'drivers/vision/score/hardware/v3/score_scq.h': '78035138e4ce22701aff1b18b0143e77c15cd1da4c9c1041d57881b50f9104fe', 'drivers/vision/score/hardware/v3/score_print.c': '1ee1fc13890fa0140be0f6f0015f7e67c1305e04d47738bf29e0f842dc4b42f7', 'drivers/vision/score/hardware/v3/score_print.h': 'a375e443fe49c96eda097751deb39e48a134906d447f77ad4ac0e20734b06441', 'drivers/vision/score/hardware/v3/score_regs.h': '2d73812c941187c5b46c7ccc1f328671bcefbf64b039bd559e9e999086baa73c', 'drivers/vision/score/hardware/v3/score_firmware.h': '2e64039044fec638fe7ed113f24895616d3f3d31c7e17c171fc6c5f672758b85', 'drivers/vision/score/hardware/v3/v3_1/score_clk.c': '092de86291d1be80716e53bd324329916038f7d4837e740242b39ed93c4c7dec', 'drivers/vision/score/hardware/v3/v3_1/score_clk.h': 'e1bcd23fa3b816995819ccff1a47cfec83eebee869d9e5c4cf02c1816fbd1271', 'drivers/vision/score/hardware/v3/v3_1/score_pm.c': '14abb14b12d115b4e4ac6e32ba246bf36745277fcae709c5dabfef705f7b4d7e', 'drivers/vision/score/hardware/v3/v3_1/score_pm.h': '34c1beb850da406e52883e5ee3e5acb942af2371fb5daf575b12cd0906f74d07'})
PINS['drivers/base/power/runtime.c']='45d1f8a26a69f390911cdccd8b82a3988ab4e453a404d1a93aa3d822e3a666e0'
PINS['include/linux/device.h']='978aae16ecc660db8572f664064f118d97a46774daefdbb27664079621f7e768'
PINS['drivers/base/dd.c']='4ddf89fa825760b38fe4535a7e9b473675a740495caf364c2d7fb378aecd7746'
PINS['drivers/vision/score/hardware/v3/score_sysfs.c']='c331030bb0bd3d1ee0450cfa4fadf02a38734645d88b4b8403ccfc5fc19b7257'
PINS['drivers/vision/score/hardware/v3/score_profiler.c']='d1bc7135cb5388365a245206e18f6432b706d4ac329015bc946d224ad00773b3'
once=retained.once
sha=retained.sha

def user_callbacks(raw,names,owner):
    """Keep registered names; native bodies run only with a live read claim."""
    text=raw.decode();pattern=re.compile(r'(?m)^static ssize_t ([a-zA-Z0-9_]+)\(([^)]*)\)\s*\{')
    found={m.group(1):m for m in pattern.finditer(text)}
    if not set(names)<=set(found):raise ValueError('actual SCORE registered callbacks differ')
    for name in sorted(names,key=lambda n:found[n].start(),reverse=True):
        match=found[name];start=match.start();at=match.end();depth=1
        token=re.compile(r'/\*.*?\*/|//[^\n]*|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|[{}]',re.S)
        for part in token.finditer(text,at):
            if part.group()=='{':depth+=1
            elif part.group()=='}':depth-=1
            if depth==0:at=part.end();break
        if depth:raise ValueError('actual SCORE callback closing boundary differs')
        signature=text[start:match.end()-1].rstrip();native=name+'_n133_native'
        body=text[start:at].replace(' '+name+'(',' '+native+'(',1)
        args=[re.search(r'([a-zA-Z0-9_]+)\s*$',p.strip()).group(1) for p in match.group(2).split(',')]
        wrapper=signature+'\n{\n#ifdef CONFIG_NOTE10_XNU_KEXEC_HANDOFF\n'
        wrapper+='    struct device *n133_owner='+owner+';\n    struct score_device *n133_device=n133_owner?dev_get_drvdata(n133_owner):NULL;\n    ssize_t n133_answer;\n'
        wrapper+='    if(!n133_device || !n133_score_user_enter(n133_device))return -ESHUTDOWN;\n'
        wrapper+='    n133_answer='+native+'('+','.join(args)+');\n    n133_score_user_exit(n133_device);return n133_answer;\n#else\n'
        wrapper+='    return '+native+'('+','.join(args)+');\n#endif\n}\n'
        text=text[:start]+body+'\n'+wrapper+text[at:]
    return text.encode()

def render(stock,identity,source128):
    for name,pin in PINS.items():
        if sha(stock[name])!=pin:raise ValueError('pinned SCORE source differs: '+name)
    output=retained.render(stock,identity,source128)
    for name,raw in output.items():output[name]=raw.replace(b'N10XNU132',b'N10XNU133')
    api=output['include/linux/v130_kernel_api.h']
    api=once(api,b'int n132_g2d_prepare(void);',b'int n132_g2d_prepare(void);\nint n133_score_prepare(void);')
    output['include/linux/v130_kernel_api.h']=api
    kernel=output['arch/arm64/mm/v130_kernel.c']
    kernel=once(kernel,b'    if(!result)result=n130_iommu_prepare();',b'    if(!result)result=n133_score_prepare();\n    if(!result)result=n130_iommu_prepare();')
    output['arch/arm64/mm/v130_kernel.c']=kernel
    kconfig=output['arch/arm64/Kconfig']
    kconfig=once(kconfig,b' depends on EXYNOS_GRAPHICS_G2D && COMMON_CLK && PM',b' depends on EXYNOS_GRAPHICS_G2D && COMMON_CLK && PM\n depends on EXYNOS_SCORE && EXYNOS_SCORE_V3 && !EXYNOS_SCORE_V2 && !EXYNOS_SCORE_FPGA')
    output['arch/arm64/Kconfig']=kconfig
    device=stock['drivers/vision/score/score_device.h']
    device=once(device,b'struct score_device {',b'''struct score_device {
#ifdef CONFIG_NOTE10_XNU_KEXEC_HANDOFF
    struct rw_semaphore n133_user_lock;
    bool n133_user_frozen;
    bool n133_terminal;
    bool n133_ever_opened;
    bool n133_shutdown_seen;
    int n133_shutdown_result;
#endif''')
    device=b'#ifdef CONFIG_NOTE10_XNU_KEXEC_HANDOFF\n#include <linux/rwsem.h>\n#endif\n'+device
    device=once(device,b'int score_device_check_start',b'''#ifdef CONFIG_NOTE10_XNU_KEXEC_HANDOFF
/* Read claim spans the entire native callback, including its nested locks. */
static inline bool n133_score_user_enter(struct score_device *device)
{
    if(!down_read_trylock(&device->n133_user_lock))return false;
    if(device->n133_user_frozen){up_read(&device->n133_user_lock);return false;}
    return true;
}
static inline void n133_score_user_exit(struct score_device *device)
{up_read(&device->n133_user_lock);}
/* Caller holds native core.device_lock; no history reset. */
static inline bool n133_score_open_locked(struct score_device *device)
{
    if(device->n133_terminal)return false;
    device->n133_ever_opened=true;return true;
}
#endif
int score_device_check_start''')
    output['drivers/vision/score/score_device.h']=device
    core=stock['drivers/vision/score/score_core.c']
    core=once(core,b'\tscore_device_get(device);',b'''#ifdef CONFIG_NOTE10_XNU_KEXEC_HANDOFF
    if(!n133_score_open_locked(device)){mutex_unlock(&core->device_lock);ret=-ESHUTDOWN;goto p_err;}
#endif
\tscore_device_get(device);''')
    output['drivers/vision/score/score_core.c']=core
    sysfs=stock['drivers/vision/score/hardware/v3/score_sysfs.c']
    sysfs=once(sysfs,b'\t\tscore_device_get(device);',b'''#ifdef CONFIG_NOTE10_XNU_KEXEC_HANDOFF
        if(!n133_score_open_locked(device))goto p_err;
#endif
\t\tscore_device_get(device);''')
    names=tuple(re.findall(rb'^static ssize_t ((?:show|store)_sysfs_system_[a-z0-9_]+)\(',sysfs,re.M))
    if len(names)!=28:raise ValueError('actual SCORE sysfs callback catalog differs')
    output['drivers/vision/score/hardware/v3/score_sysfs.c']=user_callbacks(sysfs,[n.decode() for n in names],'dev')
    profiler=stock['drivers/vision/score/hardware/v3/score_profiler.c']
    profiler=b'#ifdef CONFIG_NOTE10_XNU_KEXEC_HANDOFF\n#include "score_device.h"\n#endif\n'+profiler
    output['drivers/vision/score/hardware/v3/score_profiler.c']=user_callbacks(profiler,('score_profiler_mask_show','score_profiler_mask_store','score_profiler_read'),'profiler.system?profiler.system->dev:NULL')
    system_h=stock['drivers/vision/score/hardware/v3/score_system.h']
    system_h=once(system_h,b'struct score_system {',b'''#ifdef CONFIG_NOTE10_XNU_KEXEC_HANDOFF
struct n133_score_detail {const char *reason;unsigned int item;u32 state;int value;u32 aux;};
#endif
struct score_system {
#ifdef CONFIG_NOTE10_XNU_KEXEC_HANDOFF
    spinlock_t n133_boot_lock;
    bool n133_terminal;
    bool n133_ever_booted;
#endif''')
    system_h=once(system_h,b'int score_system_dcache_control(',b'''#ifdef CONFIG_NOTE10_XNU_KEXEC_HANDOFF
/* Dedicated boot lock is initialized before primary IRQ registration. */
static inline bool n133_score_boot_enter(struct score_system *system)
{
    unsigned long flags;bool admit;
    spin_lock_irqsave(&system->n133_boot_lock,flags);
    admit=!system->n133_terminal;
    if(admit)system->n133_ever_booted=true;
    spin_unlock_irqrestore(&system->n133_boot_lock,flags);return admit;
}
int n133_score_hardware_stop(struct score_system *system,struct n133_score_detail *detail);
#endif
int score_system_dcache_control(''')
    output['drivers/vision/score/hardware/v3/score_system.h']=system_h
    system=stock['drivers/vision/score/hardware/v3/score_system.c']
    system=once(system,b'\tret = score_system_sw_reset(system);\n\tif (ret)\n\t\tgoto p_err;',b'''#ifdef CONFIG_NOTE10_XNU_KEXEC_HANDOFF
    if(!n133_score_boot_enter(system))return -ESHUTDOWN;
#endif
\tret = score_system_sw_reset(system);
\tif (ret)
\t\tgoto p_err;''')
    system=once(system,b'\tsystem->dev = &pdev->dev;',b'''\tsystem->dev = &pdev->dev;
#ifdef CONFIG_NOTE10_XNU_KEXEC_HANDOFF
    spin_lock_init(&system->n133_boot_lock);
#endif''')
    system+=b'\n#ifdef CONFIG_NOTE10_XNU_KEXEC_HANDOFF\n#define N133_SCORE_HARDWARE_TU\n#include "v133_score.inc"\n#endif\n'
    output['drivers/vision/score/hardware/v3/score_system.c']=system
    driver=stock['drivers/vision/score/score_device.c']
    driver=b'#ifdef CONFIG_NOTE10_XNU_KEXEC_HANDOFF\n#include <linux/v130_kernel_api.h>\n#endif\n'+driver
    driver=once(driver,b'\tdevice->pdev = pdev;',b'''#ifdef CONFIG_NOTE10_XNU_KEXEC_HANDOFF
    init_rwsem(&device->n133_user_lock);
#endif
\tdevice->pdev = pdev;''')
    driver=once(driver,b'static void score_device_shutdown(struct platform_device *pdev)',b'''#ifdef CONFIG_NOTE10_XNU_KEXEC_HANDOFF
static void n133_score_shutdown(struct platform_device *pdev);
#endif
static void score_device_shutdown(struct platform_device *pdev)''')
    anchor=b'\tdevice = dev_get_drvdata(&pdev->dev);\n\tpm = &device->pm;'
    driver=once(driver,anchor,b'''#ifdef CONFIG_NOTE10_XNU_KEXEC_HANDOFF
    if(n132_handoff_active()){n133_score_shutdown(pdev);return;}
#endif
'''+anchor)
    driver+=b'\n#ifdef CONFIG_NOTE10_XNU_KEXEC_HANDOFF\n#include "v133_score.inc"\n#endif\n'
    output['drivers/vision/score/score_device.c']=driver
    raw=(HERE/'v133_score.inc').read_bytes()
    output['drivers/vision/score/v133_score.inc']=raw
    output['drivers/vision/score/hardware/v3/v133_score.inc']=raw
    return output

def install(source,identity,source128):
    source=Path(source).resolve();stock={name:(source/name).read_bytes() for name in PINS}
    output=render(stock,identity,source128)
    for name in output:
        path=source/name
        if not path.resolve().is_relative_to(source) or any(p.is_symlink() for p in (path,*path.parents)):raise ValueError('unsafe SCORE overlay path')
        if name not in PINS and path.exists():raise ValueError('new SCORE component already exists')
    for name,raw in output.items():
        path=source/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
    return {name:sha(raw) for name,raw in output.items()}
