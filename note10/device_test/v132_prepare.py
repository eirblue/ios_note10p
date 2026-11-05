"""Fresh source-owned G2D terminal provider over immutable v131 rendering."""
from pathlib import Path
import v131_prepare as retained

HERE=Path(__file__).resolve().parent
OPTION=retained.OPTION
PINS=dict(retained.PINS)
PINS.update({'drivers/gpu/exynos/g2d/g2d_drv.c': 'a233ba176caa25cbd9f859e35d20458fd8c1b6ccd0fa5f18150a16edd188181a', 'drivers/gpu/exynos/g2d/g2d_task.c': '79f77d96076ed4978ff34cb0929f99f482015275d82150845efd7235796b28f2', 'drivers/gpu/exynos/g2d/g2d.h': '66c110122a28cf51dd31aa5fd38d6737d1190fd7ae247644b17d814dac2d7974', 'drivers/gpu/exynos/g2d/g2d_task.h': 'c52cd6d68d842015afdeaafd32a259832205e0c9ad9368aa86c0632058e709c2', 'drivers/gpu/exynos/g2d/g2d_regs.h': '86439fd1d341daf27c08b1d1c0fb2b2b8db3dc1950476c5f28efa59a2f336116', 'include/linux/clk-provider.h': 'a0d1a442aa21338d6b610dfa4f5e686c366a6ce5f5eeeb3c9c9616221f016868', 'drivers/clk/clk.c': '81981b69357c00070cebd23b559a28891d6dff391a1270f14fdd9ff048ef49fb', 'drivers/base/core.c': '9f7daf9fe78e859cb419726ea837ef7b7a7e73ec3292718f8904da177c266512'})
once=retained.once
sha=retained.sha


def function(raw,name):
    anchor=('struct g2d_task *'+name+'(').encode()
    start=raw.index(anchor);at=raw.index(b'{',start)+1;depth=1
    while depth and at<len(raw):depth+=(raw[at]==123)-(raw[at]==125);at+=1
    if depth:raise ValueError('actual G2D function boundary differs')
    return start,at


def render(stock,identity,source128):
    for name,pin in PINS.items():
        if sha(stock[name])!=pin:raise ValueError('pinned G2D/clock source differs: '+name)
    output=retained.render(stock,identity,source128)
    for name,raw in output.items():output[name]=raw.replace(b'N10XNU131',b'N10XNU132')
    api=output['include/linux/v130_kernel_api.h']
    api=once(api,b'int n130_ufs_prepare(void);',b'int n130_ufs_prepare(void);\nint n132_handoff_active(void);\nint n132_g2d_prepare(void);')
    output['include/linux/v130_kernel_api.h']=api
    kernel=output['arch/arm64/mm/v130_kernel.c']
    kernel=once(kernel,b'int n130_after_shutdown(void)',b'int n132_handoff_active(void)\n{return READ_ONCE(n130_arm_state)==2 && READ_ONCE(n130_return_owner)==N130_HARDWARE;}\nint n130_after_shutdown(void)')
    kernel=once(kernel,b'    if(!result)result=n130_iommu_prepare();',b'    if(!result)result=n132_g2d_prepare();\n    if(!result)result=n130_iommu_prepare();')
    output['arch/arm64/mm/v130_kernel.c']=kernel
    kconfig=output['arch/arm64/Kconfig']
    kconfig=once(kconfig,b' bool "Note10 bounded actual-XNU legacy-kexec handoff"',b' bool "Note10 bounded actual-XNU legacy-kexec handoff"\n depends on EXYNOS_GRAPHICS_G2D && COMMON_CLK && PM')
    output['arch/arm64/Kconfig']=kconfig
    header=stock['drivers/gpu/exynos/g2d/g2d.h']
    header=once(header,b'struct g2d_device {',b'''struct g2d_device {
#ifdef CONFIG_NOTE10_XNU_KEXEC_HANDOFF
    bool n132_terminal;
    bool n132_ever_allocated;
    bool n132_shutdown_seen;
    int n132_shutdown_result;
    unsigned int n132_irq;
#endif''')
    header=once(header,b'#define G2D_AUTHORITY_HIGHUSER 1',b'''#ifdef CONFIG_NOTE10_XNU_KEXEC_HANDOFF
/* Native lock_task must be held; allocation history is never cleared. */
static inline bool n132_g2d_allocate_locked(struct g2d_device *g2d)
{
    if(g2d->n132_terminal)return false;
    g2d->n132_ever_allocated=true;return true;
}
#endif
#define G2D_AUTHORITY_HIGHUSER 1''')
    output['drivers/gpu/exynos/g2d/g2d.h']=header
    driver=stock['drivers/gpu/exynos/g2d/g2d_drv.c']
    driver=b'#ifdef CONFIG_NOTE10_XNU_KEXEC_HANDOFF\n#include <linux/v130_kernel_api.h>\n#endif\n'+driver
    driver=once(driver,b'\tdma_set_mask(&pdev->dev, DMA_BIT_MASK(36));',b'''#ifdef CONFIG_NOTE10_XNU_KEXEC_HANDOFF
    g2d_dev->n132_irq=res->start;
#endif
\tdma_set_mask(&pdev->dev, DMA_BIT_MASK(36));''')
    driver=once(driver,b'static void g2d_shutdown(struct platform_device *pdev)',b'''#ifdef CONFIG_NOTE10_XNU_KEXEC_HANDOFF
static void n132_g2d_shutdown(struct platform_device *pdev);
#endif
static void g2d_shutdown(struct platform_device *pdev)''')
    driver=once(driver,b'''static void g2d_shutdown(struct platform_device *pdev)
{
\tstruct g2d_device *g2d_dev = platform_get_drvdata(pdev);''',b'''static void g2d_shutdown(struct platform_device *pdev)
{
\tstruct g2d_device *g2d_dev = platform_get_drvdata(pdev);
#ifdef CONFIG_NOTE10_XNU_KEXEC_HANDOFF
    if(n132_handoff_active()){n132_g2d_shutdown(pdev);return;}
#endif''')
    driver+=b'\n#ifdef CONFIG_NOTE10_XNU_KEXEC_HANDOFF\n#include "v132_g2d.inc"\n#endif\n'
    output['drivers/gpu/exynos/g2d/g2d_drv.c']=driver
    tasks=stock['drivers/gpu/exynos/g2d/g2d_task.c']
    start,end=function(tasks,'g2d_get_free_task');body=tasks[start:end]
    anchor=b'\tspin_lock_irqsave(&g2d_dev->lock_task, flags);'
    guard=b'''
#ifdef CONFIG_NOTE10_XNU_KEXEC_HANDOFF
    if(g2d_dev->n132_terminal){spin_unlock_irqrestore(&g2d_dev->lock_task,flags);return NULL;}
#endif'''
    if body.count(anchor)!=2:raise ValueError('actual locked G2D initial/retry admissions differ')
    body=body.replace(anchor,anchor+guard)
    body=once(body,b'\ttask = list_first_entry(taskfree, struct g2d_task, node);',b'''#ifdef CONFIG_NOTE10_XNU_KEXEC_HANDOFF
    if(!n132_g2d_allocate_locked(g2d_dev)){spin_unlock_irqrestore(&g2d_dev->lock_task,flags);return NULL;}
#endif
\ttask = list_first_entry(taskfree, struct g2d_task, node);''')
    tasks=tasks[:start]+body+tasks[end:]
    tasks=once(tasks,b'''\tg2d_stamp_task(NULL, G2D_STAMP_STATE_RESUME, 0);
\tclear_bit(G2D_DEVICE_STATE_SUSPEND, &g2d_dev->state);''',b'''#ifdef CONFIG_NOTE10_XNU_KEXEC_HANDOFF
    if(g2d_dev->n132_terminal){spin_unlock_irq(&g2d_dev->lock_task);return;}
#endif
\tg2d_stamp_task(NULL, G2D_STAMP_STATE_RESUME, 0);
\tclear_bit(G2D_DEVICE_STATE_SUSPEND, &g2d_dev->state);''')
    output['drivers/gpu/exynos/g2d/g2d_task.c']=tasks
    output['drivers/gpu/exynos/g2d/v132_g2d.inc']=(HERE/'v132_g2d.inc').read_bytes()
    return output


def install(source,identity,source128):
    source=Path(source).resolve();stock={name:(source/name).read_bytes() for name in PINS}
    output=render(stock,identity,source128)
    for name in output:
        path=source/name
        if not path.resolve().is_relative_to(source) or any(p.is_symlink() for p in (path,*path.parents)):raise ValueError('unsafe G2D overlay path')
        if name not in PINS and path.exists():raise ValueError('new G2D component already exists')
    for name,raw in output.items():
        path=source/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
    return {name:sha(raw) for name,raw in output.items()}
