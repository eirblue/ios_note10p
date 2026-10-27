"""Opt-in read-only UFS driver observations after the PM-list lock is released."""
import hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parent
PINS={'drivers/scsi/ufs/ufs-exynos.c':'ca61a2fad0b2dfee078cae1eb093297a5aca9b0e8d1227de22d1842ae854e188',
      'drivers/scsi/ufs/ufshcd.c':'08e81a0bdabe781408ee2ffb17a3b5e89c5d4f24f7c9eecc04d3052603640b0b',
      'drivers/scsi/ufs/ufshcd.h':'d0a7a1e96aa5cc7dd22107cc2e6de52d6fd0987aab47f7d87d2dc7d680d8b190',
      'drivers/scsi/ufs/ufs.h':'8856830dec209a98f0d945c6d154227199ae9391e1406c7cd6e14c46a6ea677f'}
SOURCES=('ufs_pm_contract.h','ufs_hci_backend.c','ufs_pm_backend.c','ufs_pm_probe.c','prepare_ufs_pm.py','decode_ufs_pm.py','ufs_pm_binding.py')

def replace(raw,old,new):
    if raw.count(old)!=1:raise ValueError('Pinned UFS observer insertion point differs')
    return raw.replace(old,new)

def instrument_dma(raw):
    if raw!=(HERE/'dma_pm_backend.c').read_bytes():raise ValueError('Prepared DMA observer base differs')
    prefix=b'#ifdef CONFIG_NOTE10_UFS_PM_AUDIT\n#include <linux/note10_ufs_pm.h>\n#endif\n'
    prefix+=b'#ifdef CONFIG_NOTE10_IOMMU_PM_AUDIT\n#include <linux/note10_iommu_pm.h>\n#endif\n'
    prefix+=b'#ifdef CONFIG_NOTE10_ABOX_PM_AUDIT\n#include <linux/note10_abox_pm.h>\n#endif\n'
    prefix+=b'#ifdef CONFIG_NOTE10_ABOX_PMU_AUDIT\n#include <linux/note10_abox_pmu.h>\n#endif\n'
    return prefix+replace(raw,b'    mutex_unlock(&dpm_list_mtx);',
        b'    mutex_unlock(&dpm_list_mtx);\n#ifdef CONFIG_NOTE10_UFS_PM_AUDIT\n    n10_ufs_pm_capture(phase, generation);\n#endif\n#ifdef CONFIG_NOTE10_IOMMU_PM_AUDIT\n    n10_iommu_pm_capture(phase, generation);\n#endif\n#ifdef CONFIG_NOTE10_ABOX_PM_AUDIT\n    n10_abox_pm_capture(phase, generation);\n#endif\n#ifdef CONFIG_NOTE10_ABOX_PMU_AUDIT\n    n10_abox_pmu_capture(phase, generation);\n#endif')

HCI_PATCHED_SHA = 'a273a596ea2a4f899658d4eca86f7901e0555198680c1de851453fd2969874d5'

HCI_ANCHOR = b'\tret = ufshcd_vops_reset_ctrl(hba, UFS_DEVICE_RESET_LOW); // hw reset set low'
HCI_CALL = b'#ifdef CONFIG_NOTE10_UFS_PM_AUDIT\n\tn10_ufs_hci_before_clock_off(hba, pm_op);\n#endif\n'

def instrument_hci(raw):
    if hashlib.sha256(raw).hexdigest()!=PINS['drivers/scsi/ufs/ufshcd.c']:
        raise ValueError('Pinned UFS HCI callback differs')
    return replace(raw,HCI_ANCHOR,HCI_CALL+HCI_ANCHOR)

def prepare(source):
    source=Path(source)
    for name,pin in PINS.items():
        if hashlib.sha256((source/name).read_bytes()).hexdigest()!=pin:raise ValueError('Pinned UFS source differs: '+name)
    driver=source/'drivers/scsi/ufs/ufs-exynos.c'
    helper=driver.with_name('note10_ufs_pm.c')
    if helper.exists():raise ValueError('UFS observer already prepared')
    helper.write_bytes((HERE/'ufs_pm_backend.c').read_bytes())
    (source/'include/linux/note10_ufs_pm.h').write_bytes((HERE/'ufs_pm_contract.h').read_bytes())
    driver.write_bytes(driver.read_bytes()+b'\n#ifdef CONFIG_NOTE10_UFS_PM_AUDIT\n#include "note10_ufs_pm.c"\n#endif\n')
    hci=source/'drivers/scsi/ufs/ufshcd.c'
    hci.write_bytes(b'#ifdef CONFIG_NOTE10_UFS_PM_AUDIT\n#include <linux/note10_ufs_pm.h>\n#endif\n'+instrument_hci(hci.read_bytes())+b'\n#ifdef CONFIG_NOTE10_UFS_PM_AUDIT\n#include \"note10_ufs_hci.c\"\n#endif\n')
    if hashlib.sha256(hci.read_bytes()).hexdigest()!=HCI_PATCHED_SHA:raise ValueError('Prepared HCI callback binding differs')
    hci.with_name('note10_ufs_hci.c').write_bytes((HERE/'ufs_hci_backend.c').read_bytes())
    dma=source/'drivers/base/power/note10_dma_pm.c'
    dma.write_bytes(instrument_dma(dma.read_bytes()))
    worker=source/'arch/arm64/mm/note10_pm_timer_roundtrip.c'
    worker.with_name('note10_ufs_pm_probe.c').write_bytes((HERE/'ufs_pm_probe.c').read_bytes())
    worker.write_bytes(b'#ifdef CONFIG_NOTE10_UFS_PM_AUDIT\n#include "note10_ufs_pm_probe.c"\n#endif\n'+replace(worker.read_bytes(),
        b'    status = 0;\nreport:',b'#ifdef CONFIG_NOTE10_UFS_PM_AUDIT\n    n10_report_ufs_pm(pm.qgeneration);\n#endif\n    status = 0;\nreport:'))
    config=source/'kernel/power/Kconfig'
    config.write_bytes(config.read_bytes()+b'\nconfig NOTE10_UFS_PM_AUDIT\n\tbool "Experimental read-only Exynos UFS PM driver state observer"\n\tdepends on NOTE10_DMA_PM_AUDIT && SCSI_UFSHCD=y && SCSI_UFS_EXYNOS=y\n\tdefault n\n')
    return dict(ufs_pm_audit_diagnostic=True,ufs_pm_audit_evidence_version=2,ufs_hci_patched_sha256=HCI_PATCHED_SHA,ufs_pm_audit_source_pins=PINS,
        ufs_pm_audit_sources_sha256={n:hashlib.sha256((HERE/n).read_bytes()).hexdigest() for n in SOURCES},
        ufs_pm_generated_dma_sha256=hashlib.sha256(dma.read_bytes()).hexdigest(),
        ufs_pm_patched_driver_sha256=hashlib.sha256(driver.read_bytes()).hexdigest(),hardware_ufs_dma_idle_verified=False)
