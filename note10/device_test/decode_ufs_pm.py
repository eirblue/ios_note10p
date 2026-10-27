"""Strict driver-state observations; never global hardware DMA-idle proof."""
from decode_cpu_cache import frames

def decode(text,identity,completed):
    fields=('id','seq','phase','generation','seen','error','requests','tasks','lrb','powered','irq','system','busy','power','link','clock','gating','runtime','hci_seen','hci_error','hce','transfer_db','task_db','status')
    phases={}
    for row in frames(text,'N10UFS2',fields,identity,24).values():
        phase=row['phase'];next_generation=(row['generation']+1)&0xffffffff
        if not next_generation:next_generation=1
        if (phase>=3 or row['seq']%3!=phase or not row['generation'] or next_generation!=completed or
            row['generation']>0xffffffff or row['seen']!=1 or row['error'] or row['status'] or
            row['powered']!=1 or row['irq'] not in (0,1) or row['system'] not in (0,1) or
            row['gating'] not in (0,1) or row['busy'] or row['requests'] or row['tasks'] or row['lrb'] or
            row['runtime']>3 or row['clock'] not in (0,1,2,3,4,0x99) or row['link'] not in (0,1,2) or
            row['power'] not in (1,2,3)):
            raise ValueError('UFS driver snapshot busy, invalid or incomplete')
        if phase==1 and (not row['system'] or row['irq'] or row['clock'] or not row['gating'] or row['link']==1 or row['power']==1):
            raise ValueError('UFS driver suspend state not observed')
        # Pinned Exynos runtime hooks also call the system PM helpers.
        if phase==2 and row['system'] and not (row['runtime']==2 and not row['irq'] and
            not row['clock'] and row['gating'] and row['link']!=1 and row['power']!=1):
            raise ValueError('UFS post-resume state is neither restored nor runtime suspended')
        if phase==1 and (row['hci_seen']!=1 or row['hci_error'] or row['hce'] or row['transfer_db'] or row['task_db']):
            raise ValueError('UFS held-clock HCI controller-disabled/empty-doorbell snapshot missing or busy')
        if phase!=1 and any(row[k] for k in ('hci_seen','hci_error','hce','transfer_db','task_db')):
            raise ValueError('Unexpected UFS HCI phase')
        snapshot={k:v for k,v in row.items() if k!='seq'}
        old=phases.setdefault(phase,dict(snapshot=snapshot,sequences=[]))
        if old['snapshot']!=snapshot:raise ValueError('Conflicting UFS driver snapshots')
        old['sequences'].append(row['seq'])
    if set(phases)!=set(range(3)) or any(len(v['sequences'])<2 for v in phases.values()):
        raise ValueError('Two intact UFS records per phase required')
    return dict(ufs_pm_driver_state_observed=True,phases=phases,held_clock_hci_snapshot_observed=True,mmio_writes=False,
        hardware_ufs_dma_idle_verified=False,global_dma_shutdown_verified=False,xnu_executed=False)
