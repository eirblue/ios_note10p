"""Registered Exynos IOMMU driver inventory; no hardware shutdown assertion."""
from decode_cpu_cache import frames

def decode(text, identity, completed):
    fields=('id','seq','phase','generation','seen','error','total','active','suspended','runtime',
        'manual_off','manual_on','boot_hold','secure_configured','mapped','syscore','prepared','pm_suspended','runtime_other','names_xor','names_sum','status')
    phases={}
    counts=('active','suspended','runtime','manual_off','manual_on','boot_hold','secure_configured','mapped','syscore','prepared','pm_suspended','runtime_other')
    for row in frames(text,'N10MMU1',fields,identity,24).values():
        phase=row['phase'];next_generation=(row['generation']+1)&0xffffffff
        if not next_generation:next_generation=1
        if (phase>=3 or row['seq']%3!=phase or not 0<row['generation']<=0xffffffff or
            next_generation!=completed or row['seen']!=1 or row['error'] or row['status'] or
            not 1<=row['total']<=64 or any(row[k]>row['total'] for k in counts) or
            row['active']+row['suspended']>row['total'] or row['manual_off']+row['manual_on']>row['total'] or
            row['names_xor']>0xffffffff or row['names_sum']>0xffffffff):
            raise ValueError('Invalid registered IOMMU driver inventory')
        snapshot={k:v for k,v in row.items() if k!='seq'}
        old=phases.setdefault(phase,dict(snapshot=snapshot,sequences=[]))
        if old['snapshot']!=snapshot:raise ValueError('Conflicting IOMMU samples')
        old['sequences'].append(row['seq'])
    if set(phases)!=set(range(3)) or any(len(v['sequences'])<2 for v in phases.values()):
        raise ValueError('Two intact IOMMU records per phase required')
    inventory=lambda s:tuple(s[k] for k in ('total','names_xor','names_sum'))
    if len({inventory(v['snapshot']) for v in phases.values()})!=1:
        raise ValueError('Registered IOMMU inventory changed')
    return dict(iommu_pm_driver_inventory_observed=True,phases=phases,registered_controllers_only=True,
        name_digest_is_not_collision_proof=True,no_mmio_access=True,
        hardware_iommu_shutdown_verified=False,global_dma_shutdown_verified=False,xnu_executed=False)
