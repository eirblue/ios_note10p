"""ABOX driver/event observations; never independent DSP/DMA shutdown proof."""
from decode_cpu_cache import frames

FIELDS=('enabled','restored','firmware','fw_version','audio','cpu_gear','runtime','usage','usage_negative','children','depth',
    'runtime_error','prepared','suspended','head','tail','queued','interfaces','rdma','wdma',
    'events','enables','disables','ipc_seen','ipc_called','pending','enable_error','ipc_error','worker_starts','worker_finishes','worker_stage','worker_inflight','pm_get_result','pm_get_negative','gate_seen','can_ipc','work_pending','puts','put_busy','gets','get_empty')
EXTRA_FIELDS=('fw_downloads','fw_result','fw_negative','notify_prepares','notify_stage','clearable_seen','clearable',
    'suspend_calls','suspend_result','suspend_negative','notify_bad','notify_done')
QOS_FIELDS=('qos_seen','qos_error','qos_registered','qos_active','qos_target','qos_applied','qos_absolute','qos_default',
    'qos_first_id','qos_first_value','qos_work_pending','qos_gets','qos_puts','qos_get_result','qos_get_negative','qos_put_result','qos_put_negative','qos_worker_starts','qos_worker_finishes','qos_worker_inflight')

def qos_frames(text,identity,completed):
    phases={}
    for row in frames(text,'N10ABQ1',('id','seq','phase','generation')+QOS_FIELDS+('status',),identity,12).values():
        phase=row['phase'];next_generation=(row['generation']+1)&0xffffffff
        if not next_generation:next_generation=1
        active=row['qos_active'];target=row['qos_target']
        if (phase>=3 or row['seq']%3!=phase or not 0<row['generation']<=0xffffffff or next_generation!=completed or row['status'] or
            any(row[k]>0xffffffff for k in QOS_FIELDS) or row['qos_seen']!=1 or row['qos_error'] or
            any(row[k] not in (0,1) for k in ('qos_work_pending','qos_get_negative','qos_put_negative','qos_worker_inflight')) or
            not 0<=active<=row['qos_registered']<=64 or
            (not active and (target or row['qos_first_id'] or row['qos_first_value'])) or
            (active and (not target or not row['qos_first_id'] or not 0<row['qos_first_value']<=target)) or
            row['qos_absolute']>target or row['qos_default']>target or
            (row['qos_absolute'] and row['qos_default'] and active<2) or
            (row['qos_first_id']==0xAB0CDEFA and row['qos_first_value']!=row['qos_default']) or
            (row['qos_first_id']==0xABC0ABC0 and row['qos_first_value']!=row['qos_absolute']) or
            (row['qos_get_negative'] and not row['qos_get_result']) or
            (row['qos_put_negative'] and not row['qos_put_result'])):
            raise ValueError('Invalid ABOX AUD QoS observation')
        snapshot={k:v for k,v in row.items() if k!='seq'}
        old=phases.setdefault(phase,dict(snapshot=snapshot,sequences=[]))
        if old['snapshot']!=snapshot:raise ValueError('Conflicting ABOX QoS observations')
        old['sequences'].append(row['seq'])
    if set(phases)!=set(range(3)) or any(len(v['sequences'])<2 for v in phases.values()):
        raise ValueError('Two intact ABOX QoS observations per phase required')
    return phases

def prepare_frames(text,identity,completed):
    phases={}
    for row in frames(text,'N10ABR1',('id','seq','phase','generation')+EXTRA_FIELDS+('status',),identity,12).values():
        phase=row['phase'];next_generation=(row['generation']+1)&0xffffffff
        if not next_generation:next_generation=1
        stage=row['notify_stage']
        if (phase>=3 or row['seq']%3!=phase or not 0<row['generation']<=0xffffffff or next_generation!=completed or row['status'] or
            any(row[k]>0xffffffff for k in EXTRA_FIELDS) or
            any(row[k] not in (0,1) for k in ('fw_negative','clearable_seen','clearable','suspend_negative')) or
            (row['fw_negative'] and not row['fw_result']) or (row['suspend_negative'] and not row['suspend_result']) or
            stage>6 or (stage==0 and any(row[k] for k in EXTRA_FIELDS[3:])) or
            (stage in (1,2) and any(row[k] for k in ('clearable_seen','clearable','suspend_result','suspend_negative'))) or
            (stage>=3 and not row['clearable_seen']) or (row['clearable'] and not row['clearable_seen']) or
            (stage in (4,5) and not row['clearable']) or (stage==5 and not row['suspend_negative']) or
            (stage==6 and row['suspend_negative']) or (not row['clearable'] and (row['suspend_result'] or row['suspend_negative']))):
            raise ValueError('Invalid ABOX firmware/prepare observation')
        snapshot={k:v for k,v in row.items() if k!='seq'}
        old=phases.setdefault(phase,dict(snapshot=snapshot,sequences=[]))
        if old['snapshot']!=snapshot:raise ValueError('Conflicting ABOX prepare observations')
        old['sequences'].append(row['seq'])
    if set(phases)!=set(range(3)) or any(len(v['sequences'])<2 for v in phases.values()):
        raise ValueError('Two intact ABOX prepare observations per phase required')
    return phases

def decode(text,identity,completed):
    fields=('id','seq','phase','generation','seen','error')+FIELDS+('status',)
    phases={}
    for row in frames(text,'N10ABX4',fields,identity,24).values():
        phase=row['phase'];next_generation=(row['generation']+1)&0xffffffff
        if not next_generation:next_generation=1
        if (phase>=3 or row['seq']%3!=phase or not 0<row['generation']<=0xffffffff or
            next_generation!=completed or row['seen']!=1 or row['error'] or row['status'] or
            any(row[k] not in (0,1) for k in ('enabled','restored','usage_negative','prepared','suspended','ipc_called','pending','worker_inflight','pm_get_negative','gate_seen','can_ipc','work_pending')) or
            row['worker_stage']>4 or (row['pm_get_negative'] and not row['pm_get_result']) or (row['can_ipc'] and not row['gate_seen']) or (row['worker_stage']==0 and any(row[k] for k in ('worker_starts','worker_finishes','worker_inflight','pm_get_result','pm_get_negative','gate_seen','can_ipc'))) or (row['worker_stage'] in (1,2) and (not row['worker_inflight'] or row['gate_seen'])) or (row['worker_stage']==1 and (row['pm_get_result'] or row['pm_get_negative'])) or (row['worker_stage']==3 and (not row['worker_inflight'] or not row['gate_seen'])) or (row['worker_stage']==4 and (row['worker_inflight'] or not row['gate_seen'])) or row['firmware']>3 or row['runtime']>3 or row['head']>=128 or row['tail']>=128 or
            row['queued']!=(row['tail']+128-row['head'])%128 or row['interfaces']>8 or row['rdma']>16 or row['wdma']>16 or
            row['children']>4096 or row['depth']>0xffff or any(row[k]>0xffffffff for k in FIELDS) or
            any(row[k]>4095 for k in ('runtime_error','enable_error','ipc_error')) or
            (row['ipc_called'] and not row['ipc_seen']) or (row['usage_negative'] and not row['usage']) or
            (row['ipc_error'] and not row['ipc_called']) or (row['enable_error'] and not row['enables']) or
            (not row['events'] and any(row[k] for k in ('enables','disables','ipc_seen','ipc_called','pending','enable_error','ipc_error','worker_starts','worker_finishes','worker_stage','worker_inflight','pm_get_result','pm_get_negative','gate_seen','can_ipc','puts','put_busy','gets','get_empty')))):
            raise ValueError('Invalid ABOX driver/event observation')
        snapshot={k:v for k,v in row.items() if k!='seq'}
        old=phases.setdefault(phase,dict(snapshot=snapshot,sequences=[]))
        if old['snapshot']!=snapshot:raise ValueError('Conflicting ABOX snapshots')
        old['sequences'].append(row['seq'])
    if set(phases)!=set(range(3)) or any(len(v['sequences'])<2 for v in phases.values()):
        raise ValueError('Two intact ABOX observations per phase required')
    prepares=prepare_frames(text,identity,completed)
    qos=qos_frames(text,identity,completed)
    for phase in phases:
        core=phases[phase]['snapshot'];extra=prepares[phase]['snapshot']
        if core['generation']!=extra['generation']:raise ValueError('ABOX core/prepare generation differs')
        if not core['events'] and any(extra[k] for k in EXTRA_FIELDS):raise ValueError('ABOX prepare history without events')
        core.update({k:extra[k] for k in EXTRA_FIELDS})
        view=qos[phase]['snapshot']
        if core['generation']!=view['generation']:raise ValueError('ABOX QoS generation differs')
        if not core['events'] and any(view[k] for k in QOS_FIELDS[11:]):raise ValueError('ABOX QoS history without events')
        core.update({k:view[k] for k in QOS_FIELDS})
    suspended=phases[1]['snapshot']
    idle=(not any(suspended[k] for k in ('enabled','restored','firmware','fw_version','audio','usage','usage_negative','children',
        'runtime_error','depth','queued','pending','enable_error','ipc_error','worker_inflight','work_pending','pm_get_negative','fw_negative','suspend_negative','notify_bad',
        'qos_target','qos_applied','qos_work_pending','qos_get_negative','qos_put_negative','qos_worker_inflight')) and suspended['runtime']==2)
    return dict(abox_pm_driver_observed=True,phases=phases,abox_driver_idle_state_observed=idle,
        prepare_observations=prepares,normal_pm_prepare_observed=bool(suspended['notify_stage']),
        firmware_download_deferred=bool(suspended['fw_negative'] and suspended['fw_result']==11),
        qos_observations=qos,aud_qos_driver_observed=True,qos_counts_are_not_reference_balance_proof=True,
        runtime_ownership_unbalanced=any(v['snapshot']['usage_negative'] for v in phases.values()),
        callback_history_is_current_boot_not_per_generation=True,cpu_gear_value_is_not_idle_proof=True,no_mmio_access=True,
        audio_dsp_shutdown_verified=False,global_dma_shutdown_verified=False,xnu_executed=False)
