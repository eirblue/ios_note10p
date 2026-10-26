"""Require a complete same-boot CPU/cache, PM devices and timer roundtrip."""
from decode_cpu_cache import frames,decode as decode_cpu

def decode_stages(text,identity):
    rows=frames(text,'N10PMS1',('id','seq','attempt','stage','error'),identity,24)
    names={0:'PM ownership unavailable',1:'PM wrapper entered',10:'prepare notifier entered',11:'interruptible sync entered',
           12:'interruptible sync completed',13:'freezer entered',14:'freezer returned',
           20:'device suspend entered',21:'device suspend returned'}
    attempts={}
    for row in rows.values():
        attempt=row['attempt']
        if attempt not in (1,2,3) or row['seq']//8+1!=attempt or row['stage'] not in names:
            raise ValueError('Invalid PM failure-stage record')
        current={'stage':row['stage'],'stage_name':names[row['stage']],'error':row['error']}
        previous=attempts.setdefault(attempt,{'result':current,'frames':0})
        if previous['result']!=current:raise ValueError('Conflicting PM failure stages')
        previous['frames']+=1
    if not attempts or any(value['frames']<2 for value in attempts.values()):
        raise ValueError('Two intact PM stage records per attempt required')
    if set(attempts)!=set(range(1,max(attempts)+1)):raise ValueError('Missing PM attempt stage')
    return attempts


def decode_quiescence(text,identity,require_success=True):
    names=('id','seq','attempt','version','generation','epoch','phase','called','restored',
           'screen','display','usb','wake','r_usb','r_display','r_screen')
    rows=frames(text,'N10QSC1',names,identity,24)
    attempts={}
    for row in rows.values():
        attempt=row['attempt']
        if (attempt not in (1,2,3) or row['seq']//8+1!=attempt or row['version']!=1 or
                row['phase']>11 or any(row[k]>1 for k in ('called','restored')) or
                row['generation']>=1<<32 or row['epoch']>=1<<32):
            raise ValueError('Invalid PM quiesce record')
        current={k:v for k,v in row.items() if k not in ('seq','attempt')}
        entry=attempts.setdefault(attempt,{'result':current,'frames':0})
        if entry['result']!=current:raise ValueError('Conflicting PM quiesce records')
        entry['frames']+=1
    if (not attempts or any(v['frames']<2 for v in attempts.values()) or
            set(attempts)!=set(range(1,max(attempts)+1))):
        raise ValueError('Two intact quiesce records per contiguous attempt required')
    final=attempts[max(attempts)]['result']
    if require_success:
        for attempt in range(1,max(attempts)):
            old=attempts[attempt]['result']
            if old['restored']!=1 or any(old[k] for k in ('r_usb','r_display','r_screen')):
                raise ValueError('A retry followed an incomplete driver restoration')
    if require_success and (final['phase']!=10 or final['called']!=1 or final['restored']!=1 or
            not final['generation'] or any(final[k] for k in
            ('screen','display','usb','wake','r_usb','r_display','r_screen'))):
        raise ValueError('PM quiesce or restoration failed')
    return {'attempts':attempts,'normal_driver_quiesce_observed':require_success,
            'hardware_dma_shutdown_verified':False,'xnu_executed':False}


def _bind_quiesce_attempts(text,identity,quiesce):
    names=('id','seq','attempt','error','devices','resume','blocked','oldlevel','newlevel','resume_errors')
    attempts={}
    for row in frames(text,'N10TRY1',names,identity,24).values():
        number=row['attempt']
        if number not in (1,2,3) or row['seq']//8+1!=number:
            raise ValueError('Invalid PM attempt record')
        current={k:v for k,v in row.items() if k not in ('seq','attempt')}
        entry=attempts.setdefault(number,{'result':current,'frames':0})
        if entry['result']!=current:raise ValueError('Conflicting PM attempt records')
        entry['frames']+=1
    stages=decode_stages(text,identity)
    if (set(attempts)!=set(quiesce['attempts']) or set(stages)!=set(attempts) or
            any(v['frames']<2 for v in attempts.values())):
        raise ValueError('PM stage, attempt and quiesce histories differ')
    for number,entry in attempts.items():
        row=entry['result']
        stage=stages[number]['result']
        if number==max(attempts):
            expected=(0,1,1,0,0,0,0)
            if stage['stage']!=21 or stage['error']:
                raise ValueError('Successful quiesce is not bound to a completed PM device phase')
        else:
            expected=(16,0,0,0,0,0,0)
            if stage['stage']>=20 or stage['error']!=16:
                raise ValueError('PM retry did not follow a clean pre-device EBUSY')
        if tuple(row[k] for k in ('error','devices','resume','blocked','oldlevel','newlevel','resume_errors'))!=expected:
            raise ValueError('PM attempt disposition contradicts retry or success evidence')


def decode(text,identity,digest,size,require_quiesce=False):
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
    records=frames(text,'N10TMR1',('id','seq','cpu','before','cleared','restored','freq','status'),identity,32)
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
    quiesce=decode_quiescence(text,identity) if require_quiesce else None
    if quiesce:_bind_quiesce_attempts(text,identity,quiesce)
    return {'previous_boot_pm_timer_observed':True,'summary_intact_frame_count':len(summaries),
        'quiescence':quiesce,
        'cpus':cpus,'pm_devices_test_returned':True,'pm_test_level_restored':True,
        'lowlevel_suspend_entered':False,'lowlevel_entry_blocked':False,
        'dma_quiescence_verified':False,'gic_handoff_verified':False,'cache_mmu_shutdown_verified':False,
        'xnu_executed':False,'region':previous['region'],
        'scope':'Linux devices-only suspend/resume test and restored CNTKCTL event selector; not XNU handoff'}
