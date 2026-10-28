"""Compose four-phase read-only PM inventories without changing suspend.c."""
import hashlib
from pathlib import Path
from prepare_pm_noirq import FINAL_SHA
from prepare_ufs_pm import instrument_dma
from prepare_dma_pm import HERE
from prepare_abox_pm import SYSTEM_PATCHED_SHA

PINS = {
 'drivers/base/power/main.c':'77535e2d086fcd23afaffac6d789605ef40a3398249dc9f6cb6593d6417192e1',
 'drivers/iommu/exynos-iommu.c':'67d9bfb7597ec7434fc07a7101e69c385ac4cb9e61ebd727f0bcd40d01f1bb0b',
 'drivers/iommu/exynos-iommu.h':'f5f2be8937e8990672296e55d33bdbcd12244d0ab6aa8b8eef96de6717fadc11',
 'drivers/base/syscore.c':'fcb46388e39a3ca03c37cf334124a9b7a4f6d1c19881147a59399b934856f8ab',
 'include/linux/syscore_ops.h':'fd27ef5c90fa8ca1b3dd7a77e4178b623be801f3254ba8eda6c94dec5ede7d8a',
 'include/linux/pm.h':'696f4052e4aa510c06266c0eaeaeb066b35ba42cd2ea5378fa1312f539508943',
 'include/linux/device.h':'978aae16ecc660db8572f664064f118d97a46774daefdbb27664079621f7e768',
 'kernel/kallsyms.c':'67359b399a6eb5c529e9da783336d3bf2befeb13cfd5f2617eeed5dacd693948',
 'include/linux/kallsyms.h':'0889f4595c8c387322072a977d74c30baca51b3ab79f4b52d88ca67d2e8f0c41',
 'kernel/extable.c':'63d4e1e9dbfe32285bbde0cc4b0eec4023ddddfbb01ebb8aee48bedf2e88e595',
 'include/linux/kernel.h':'5c8c7992db241ca1c2c8127752f82e8d56acb5a2b0f6c1532533c5af05639fc0',
}
SOURCES=('pm_edge_dma_contract.h','pm_edge_dma_backend.c','pm_edge_iommu_contract.h','pm_edge_iommu_backend.c',
         'pm_edge_syscore_contract.h','pm_edge_syscore_backend.c','pm_edge_probe.c','prepare_pm_edge.py',
         'test_pm_edge_dma_native.py','test_pm_edge_iommu_native.py','test_pm_edge_syscore_native.py',
         'test_pm_edge_integration_native.py','test_pm_edge_decoder.py','test_pm_edge_binding.py','decode_pm_edge.py','pm_edge_binding.py')

def replace(raw,old,new):
    if raw.count(old)!=1: raise ValueError('PM edge composition insertion differs')
    return raw.replace(old,new)

def prepare(source):
    source=Path(source)
    suffixes={'drivers/iommu/exynos-iommu.c':b'\n#ifdef CONFIG_NOTE10_IOMMU_PM_AUDIT\n#include "note10_iommu_pm.c"\n#endif\n'}
    for name,digest in PINS.items():
        raw=(source/name).read_bytes()
        if name=='drivers/base/power/main.c':
            if hashlib.sha256(raw).hexdigest()!=SYSTEM_PATCHED_SHA:raise ValueError('PM edge prepared ABOX core differs')
            continue
        if name in suffixes:
            suffix=suffixes[name]
            if not raw.endswith(suffix):raise ValueError('PM edge prerequisite differs: '+name)
            raw=raw[:-len(suffix)]
        if hashlib.sha256(raw).hexdigest()!=digest: raise ValueError('PM edge pinned source differs: '+name)
    suspend=source/'kernel/power/suspend.c'
    if hashlib.sha256(suspend.read_bytes()).hexdigest()!=FINAL_SHA: raise ValueError('PM edge guarded suspend differs')
    dma=source/'drivers/base/power/note10_dma_pm.c'
    if dma.read_bytes()!=instrument_dma((HERE/'dma_pm_backend.c').read_bytes()): raise ValueError('PM edge DMA prerequisite differs')
    dma_raw=dma.read_bytes()
    dma_raw=b'#ifdef CONFIG_NOTE10_PM_EDGE_INVENTORY\n#include <linux/note10_pm_edge_dma.h>\n#endif\n'+replace(dma_raw,b'\n}\n\nint n10_dma_pm_read(', b'''\n#ifdef CONFIG_NOTE10_PM_EDGE_INVENTORY
    if (phase == 0 || phase == 2) n10_edge_capture(phase == 0 ? 0 : 3, generation);
#endif
}\n\nint n10_dma_pm_read(''')
    noirq=source/'kernel/power/note10_pm_noirq.c'
    raw=noirq.read_bytes()
    if raw!=(HERE/'pm_noirq_backend.c').read_bytes(): raise ValueError('PM edge noirq prerequisite differs')
    raw=b'#ifdef CONFIG_NOTE10_PM_EDGE_INVENTORY\n#include <linux/note10_pm_edge_dma.h>\n#endif\n'+raw
    for flag,phase in (('late_ok',1),('noirq_ok',2)):
        old=('else if (!result) s->'+flag+' = 1; break;').encode()
        new=('else if (!result) { s->'+flag+' = 1;\n#ifdef CONFIG_NOTE10_PM_EDGE_INVENTORY\n'
             '                n10_edge_capture('+str(phase)+', s->generation);\n#endif\n            } break;').encode()
        raw=replace(raw,old,new)
    worker=source/'arch/arm64/mm/note10_pm_timer_roundtrip.c'; work=worker.read_bytes()
    anchor=b'static bool n10_timer_done;'
    work=replace(work,anchor,anchor+b'\n#ifdef CONFIG_NOTE10_PM_EDGE_INVENTORY\n#include "note10_pm_edge_probe.c"\n#endif')
    work=replace(work,b'    status = 0;\nreport:',b'#ifdef CONFIG_NOTE10_PM_EDGE_INVENTORY\n    if (n10_report_pm_edge(pm.qgeneration)) goto report;\n#endif\n    status = 0;\nreport:')
    pairs=(('drivers/base/power/note10_pm_edge_dma.c','pm_edge_dma_backend.c'),
           ('drivers/iommu/note10_pm_edge_iommu.c','pm_edge_iommu_backend.c'),
           ('drivers/base/note10_pm_edge_syscore.c','pm_edge_syscore_backend.c'),
           ('arch/arm64/mm/note10_pm_edge_probe.c','pm_edge_probe.c'))
    for target,name in pairs:
        if (source/target).exists():raise ValueError('PM edge already prepared: '+target)
        (source/target).write_bytes((HERE/name).read_bytes())
    for kind in ('dma','iommu','syscore'):
        (source/('include/linux/note10_pm_edge_'+kind+'.h')).write_bytes((HERE/('pm_edge_'+kind+'_contract.h')).read_bytes())
    for name,helper in (('drivers/base/power/main.c','note10_pm_edge_dma.c'),('drivers/iommu/exynos-iommu.c','note10_pm_edge_iommu.c'),('drivers/base/syscore.c','note10_pm_edge_syscore.c')):
        p=source/name;p.write_bytes(p.read_bytes()+('\n#ifdef CONFIG_NOTE10_PM_EDGE_INVENTORY\n#include "'+helper+'"\n#endif\n').encode())
    dma.write_bytes(dma_raw);noirq.write_bytes(raw);worker.write_bytes(work)
    config=source/'kernel/power/Kconfig'
    config.write_bytes(config.read_bytes()+b'\nconfig NOTE10_PM_EDGE_INVENTORY\n\tbool "Experimental read-only PM edge inventories"\n\tdepends on NOTE10_PM_POST_ARCH && NOTE10_PM_CPUS_TEST && NOTE10_DMA_PM_AUDIT && NOTE10_IOMMU_PM_AUDIT && KALLSYMS\n\tdefault n\n')
    if hashlib.sha256(suspend.read_bytes()).hexdigest()!=FINAL_SHA:raise ValueError('PM edge unexpectedly changed suspend.c')
    return {'pm_edge_inventory_diagnostic':True,'pm_edge_inventory_evidence_version':1,'pm_edge_source_pins':PINS,
        'pm_edge_sources_sha256':{name:hashlib.sha256((HERE/name).read_bytes()).hexdigest() for name in SOURCES},
        'pm_edge_prepared_sha256':{str(p.relative_to(source)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in
            (dma,noirq,worker,suspend,config,source/'drivers/base/power/main.c',source/'drivers/iommu/exynos-iommu.c',source/'drivers/base/syscore.c',
             *(source/target for target,_ in pairs),*(source/('include/linux/note10_pm_edge_'+kind+'.h') for kind in ('dma','iommu','syscore')))},
        'hardware_dma_shutdown_verified':False}
