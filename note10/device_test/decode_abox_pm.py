"""ABOX driver/event observations; never independent DSP/DMA shutdown proof."""
from decode_cpu_cache import frames

FIELDS=('enabled','restored','firmware','fw_version','audio','cpu_gear','runtime','usage','usage_negative','children','depth',
    'runtime_error','prepared','suspended','head','tail','queued','interfaces','rdma','wdma',
    'events','enables','disables','ipc_seen','ipc_called','pending','enable_error','ipc_error')

def decode(text,identity,completed):
    fields=('id','seq','phase','generation','seen','error')+FIELDS+('status',)
    phases={}
    for row in frames(text,'N10ABX1',fields,identity,24).values():
        phase=row['phase'];next_generation=(row['generation']+1)&0xffffffff
        if not next_generation:next_generation=1
        if (phase>=3 or row['seq']%3!=phase or not 0<row['generation']<=0xffffffff or
            next_generation!=completed or row['seen']!=1 or row['error'] or row['status'] or
            any(row[k] not in (0,1) for k in ('enabled','restored','usage_negative','prepared','suspended','ipc_called','pending')) or
            row['firmware']>3 or row['runtime']>3 or row['head']>=128 or row['tail']>=128 or
            row['queued']!=(row['tail']+128-row['head'])%128 or row['interfaces']>8 or row['rdma']>16 or row['wdma']>16 or
            row['children']>4096 or row['depth']>0xffff or any(row[k]>0xffffffff for k in FIELDS) or
            any(row[k]>4095 for k in ('runtime_error','enable_error','ipc_error')) or
            (row['ipc_called'] and not row['ipc_seen']) or (row['usage_negative'] and not row['usage']) or
            (row['ipc_error'] and not row['ipc_called']) or (row['enable_error'] and not row['enables']) or
            (not row['events'] and any(row[k] for k in ('enables','disables','ipc_seen','ipc_called','pending','enable_error','ipc_error')))):
            raise ValueError('Invalid ABOX driver/event observation')
        snapshot={k:v for k,v in row.items() if k!='seq'}
        old=phases.setdefault(phase,dict(snapshot=snapshot,sequences=[]))
        if old['snapshot']!=snapshot:raise ValueError('Conflicting ABOX snapshots')
        old['sequences'].append(row['seq'])
    if set(phases)!=set(range(3)) or any(len(v['sequences'])<2 for v in phases.values()):
        raise ValueError('Two intact ABOX observations per phase required')
    suspended=phases[1]['snapshot']
    idle=(not any(suspended[k] for k in ('enabled','restored','firmware','fw_version','audio','cpu_gear','usage','usage_negative','children',
        'runtime_error','depth','queued','pending','enable_error','ipc_error')) and suspended['runtime']==2)
    return dict(abox_pm_driver_observed=True,phases=phases,abox_driver_idle_state_observed=idle,
        runtime_ownership_unbalanced=any(v['snapshot']['usage_negative'] for v in phases.values()),
        callback_history_is_current_boot_not_per_generation=True,no_mmio_access=True,
        audio_dsp_shutdown_verified=False,global_dma_shutdown_verified=False,xnu_executed=False)
