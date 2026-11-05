"""Fresh v131 terminal-proof delta over immutable v130 source rendering."""
from pathlib import Path
import v130_prepare as retained

HERE=Path(__file__).resolve().parent
OPTION=retained.OPTION
PINS=retained.PINS
once=retained.once
sha=retained.sha
OWN={
 'arch/arm64/mm/v131_dma_registry.inc':'v131_dma_registry.inc',
 'drivers/scsi/ufs/v130_ufs.inc':'v131_ufs.inc',
 'drivers/iommu/v130_iommu.inc':'v131_iommu.inc'}


def render(stock,identity,source128):
    output=retained.render(stock,identity,source128)
    # Fresh markers, retained wire/core ABI and same qualified late-WDT ordering.
    for name,raw in output.items():output[name]=raw.replace(b'N10XNU130',b'N10XNU131')
    kernel=output['arch/arm64/mm/v130_kernel.c']
    start=kernel.index(b'int n130_dma_record(')
    end=kernel.index(b'static ssize_t n130_read(',start)
    kernel=kernel[:start]+b'#include "v131_dma_registry.inc"\n'+kernel[end:]
    kernel=once(kernel,b'    if(!result)result=n130_ufs_prepare();',
        b'    if(result)n131_gate_refused("usb-terminal",result,NULL);\n    if(!result)result=n130_ufs_prepare();')
    kernel=once(kernel,b'    return n130_dmaengine_prepare();',b'    result=n130_dmaengine_prepare();\n    if(result)n131_gate_refused("dma-provider",result,NULL);\n    return result;')
    kernel=once(kernel,b'    if(result){WRITE_ONCE(n130_arm_state,4);return result;}',
        b'    if(result){n131_gate_refused("final",result,NULL);WRITE_ONCE(n130_arm_state,4);return result;}')
    output['arch/arm64/mm/v130_kernel.c']=kernel
    api=output['include/linux/v130_kernel_api.h']
    api=once(api,b'int n130_dma_ready(struct device *);',b'int n130_dma_ready(struct device *);\nint n131_dma_status(struct device *);\nvoid n131_gate_refused(const char *,int,struct device *);')
    output['include/linux/v130_kernel_api.h']=api
    ufs=output['drivers/scsi/ufs/ufshcd.c']
    ufs=once(ufs,b'    n130_dma_record(hba->dev, ret || hba->curr_dev_pwr_mode!=UFS_POWERDOWN_PWR_MODE || !ufshcd_is_link_off(hba) ? -EIO : 0);',
        b'    n130_dma_record(hba->dev, ret ? ret :\n        (hba->curr_dev_pwr_mode!=UFS_POWERDOWN_PWR_MODE || !ufshcd_is_link_off(hba) ? -EIO : 0));')
    output['drivers/scsi/ufs/ufshcd.c']=ufs
    pl330=output['drivers/dma/v130_pl330.inc']
    pl330=once(pl330,b'    spin_unlock_irqrestore(&controller->lock,flags);\n    return error;',
        b'    spin_unlock_irqrestore(&controller->lock,flags);\n    if(!error)error=n130_dma_record(device->dev,0);\n    return error;')
    output['drivers/dma/v130_pl330.inc']=pl330
    for target,name in OWN.items():output[target]=(HERE/name).read_bytes()
    return output


def install(source,identity,source128):
    source=Path(source).resolve();stock={name:(source/name).read_bytes() for name in PINS}
    output=render(stock,identity,source128)
    for name in output:
        path=source/name
        if not path.resolve().is_relative_to(source) or any(p.is_symlink() for p in (path,*path.parents)):raise ValueError('unsafe successor overlay path')
        if name not in PINS and path.exists():raise ValueError('new successor component already exists')
    for name,raw in output.items():
        path=source/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
    return {name:sha(raw) for name,raw in output.items()}
