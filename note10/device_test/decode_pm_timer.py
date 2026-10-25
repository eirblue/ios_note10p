"""Require a complete same-boot CPU/cache, PM devices and timer roundtrip."""
from decode_cpu_cache import frames,decode as decode_cpu


def decode(text,identity,digest,size):
    previous=decode_cpu(text,identity,digest,size)
    summaries=frames(text,'N10PMT1',('id','seq','before','after','devices','resume','blocked',
        'oldlevel','newlevel','resume_errors','timers','error','sha256','status'),identity,32)
    if len(summaries)<2:raise ValueError('Two intact PM/timer summaries required')
    baseline=None
    for row in summaries.values():
        current={k:v for k,v in row.items() if k!='seq'}
        if baseline is not None and current!=baseline:raise ValueError('Conflicting PM/timer summaries')
        baseline=current
        if tuple(row[k] for k in ('before','after','devices','resume','blocked','oldlevel','newlevel',
            'resume_errors','timers','error','sha256','status'))!=(255,255,1,1,0,0,0,0,8,0,int(digest,16),0):
            raise ValueError('PM devices or timer roundtrip failed')
    records=frames(text,'N10TMR1',('id','seq','cpu','before','cleared','restored','freq','status'),identity,8)
    cpus={}
    for row in records.values():
        if (row['cpu']>=8 or row['cleared']!=row['before']&~0xf0 or row['restored']!=row['before'] or
            row['freq']!=26000000 or row['status']!=0):raise ValueError('Timer clear/restore state differs')
        snapshot={k:v for k,v in row.items() if k!='seq'}
        entry=cpus.setdefault(row['cpu'],{'snapshot':snapshot,'sequences':[]})
        if entry['snapshot']!=snapshot:raise ValueError('Conflicting timer snapshots')
        entry['sequences'].append(row['seq'])
    if set(cpus)!=set(range(8)) or any(len(v['sequences'])<2 for v in cpus.values()):
        raise ValueError('Two timer snapshots from each CPU required')
    return {'previous_boot_pm_timer_observed':True,'summary_intact_frame_count':len(summaries),
        'cpus':cpus,'pm_devices_test_returned':True,'pm_test_level_restored':True,
        'lowlevel_suspend_entered':False,'lowlevel_entry_blocked':False,
        'dma_quiescence_verified':False,'gic_handoff_verified':False,'cache_mmu_shutdown_verified':False,
        'xnu_executed':False,'region':previous['region'],
        'scope':'Linux devices-only suspend/resume test and restored CNTKCTL event selector; not XNU handoff'}
