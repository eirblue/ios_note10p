"""Opt-in registered Exynos IOMMU driver snapshots after the PM list unlock."""
import hashlib
from pathlib import Path
import re
HERE=Path(__file__).resolve().parent
PINS={'drivers/iommu/exynos-iommu.c': '67d9bfb7597ec7434fc07a7101e69c385ac4cb9e61ebd727f0bcd40d01f1bb0b', 'drivers/iommu/exynos-iommu.h': 'f5f2be8937e8990672296e55d33bdbcd12244d0ab6aa8b8eef96de6717fadc11'}
HELPERS_SHA='38746aae63cd7b5b0c3e57b6f1c0b6be86c2cd59f12b49d2fde4405c3cce8e3c'
SOURCES=('iommu_pm_contract.h','iommu_pm_backend.c','iommu_pm_probe.c','prepare_iommu_pm.py','decode_iommu_pm.py','iommu_pm_binding.py')

def inline_helpers(raw):
    if hashlib.sha256(raw).hexdigest()!=PINS['drivers/iommu/exynos-iommu.h']:raise ValueError('Pinned IOMMU helper header differs')
    text=raw.decode()
    helpers='\n'.join(re.search(r'static inline bool '+name+r'\([^}]+}',text).group() for name in ('is_sysmmu_runtime_active','is_sysmmu_active'))+'\n'
    if hashlib.sha256(helpers.encode()).hexdigest()!=HELPERS_SHA:raise ValueError('Pinned IOMMU helper extraction differs')
    return helpers

def prepare(source):
    source=Path(source)
    for name,digest in PINS.items():
        if hashlib.sha256((source/name).read_bytes()).hexdigest()!=digest:raise ValueError('Pinned IOMMU source differs')
    inline_helpers((source/'drivers/iommu/exynos-iommu.h').read_bytes())
    driver=source/'drivers/iommu/exynos-iommu.c'
    helper=driver.with_name('note10_iommu_pm.c')
    if helper.exists():raise ValueError('IOMMU observer already prepared')
    helper.write_bytes((HERE/'iommu_pm_backend.c').read_bytes())
    (source/'include/linux/note10_iommu_pm.h').write_bytes((HERE/'iommu_pm_contract.h').read_bytes())
    driver.write_bytes(driver.read_bytes()+b'\n#ifdef CONFIG_NOTE10_IOMMU_PM_AUDIT\n#include "note10_iommu_pm.c"\n#endif\n')
    worker=source/'arch/arm64/mm/note10_pm_timer_roundtrip.c'
    worker.with_name('note10_iommu_pm_probe.c').write_bytes((HERE/'iommu_pm_probe.c').read_bytes())
    raw=worker.read_bytes();old=b'    status = 0;\nreport:'
    if raw.count(old)!=1:raise ValueError('IOMMU reporting insertion differs')
    worker.write_bytes(b'#ifdef CONFIG_NOTE10_IOMMU_PM_AUDIT\n#include "note10_iommu_pm_probe.c"\n#endif\n'+raw.replace(old,b'#ifdef CONFIG_NOTE10_IOMMU_PM_AUDIT\n    n10_report_iommu_pm(pm.qgeneration);\n#endif\n'+old))
    config=source/'kernel/power/Kconfig'
    config.write_bytes(config.read_bytes()+b'\nconfig NOTE10_IOMMU_PM_AUDIT\n\tbool "Experimental registered Exynos IOMMU driver inventory"\n\tdepends on NOTE10_UFS_PM_AUDIT && EXYNOS_IOMMU=y\n\tdefault n\n')
    return dict(iommu_pm_audit_diagnostic=True,iommu_pm_audit_evidence_version=1,iommu_pm_source_pins=PINS,
        iommu_pm_sources_sha256={n:hashlib.sha256((HERE/n).read_bytes()).hexdigest() for n in SOURCES},hardware_iommu_shutdown_verified=False)
