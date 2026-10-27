"""Bounded PMU control/standby reads; control bits are not power-off acknowledgments."""
from decode_cpu_cache import frames

FIELDS=('id','seq','phase','generation','index','count','seen','error','power','enable','standby','status')

def decode(text,identity,completed):
    rows={}
    for row in frames(text,'N10APM1',FIELDS,identity,24).values():
        phase=row['phase'];core=row['index'];generation=row['generation'];next_generation=(generation+1)&0xffffffff
        if not next_generation:next_generation=1
        if (phase>=3 or core>=2 or row['seq']//2%3!=phase or row['seq']%2!=core or
            not 0<generation<=0xffffffff or next_generation!=completed or row['count']!=2 or
            row['seen']!=1 or row['error'] or row['status'] or row['power']>1 or row['enable']>1 or
            row['standby'] & ~(0x11 if core==0 else 1)):
            raise ValueError('Invalid ABOX PMU control observation')
        key=(phase,core);snapshot={k:v for k,v in row.items() if k!='seq'}
        old=rows.setdefault(key,dict(snapshot=snapshot,sequences=[]))
        if old['snapshot']!=snapshot:raise ValueError('Conflicting ABOX PMU observations')
        old['sequences'].append(row['seq'])
    if set(rows)!={(p,c) for p in range(3) for c in range(2)} or any(len(r['sequences'])<2 for r in rows.values()):
        raise ValueError('Two intact PMU observations per core and phase required')
    fsys=decode_fsys(text,identity,completed)
    domains=decode_domains(text,identity,completed)
    return dict(fsys0a_policy_observed=True,fsys0a_policy=fsys,pmu_domain_status_observed=True,power_domains=domains,abox_pmu_controls_observed=True,
        phases={p:{c:rows[p,c] for c in range(2)} for p in range(3)},
        pmu_read_api_used=True,pmu_writes_performed=False,control_bits_are_not_power_off_acknowledgments=True,
        audio_dsp_shutdown_verified=False,global_dma_shutdown_verified=False,xnu_executed=False)


DOMAIN_FIELDS=('id','seq','phase','generation','count','seen','error','before','state','after','status')

def decode_domains(text,identity,completed):
    from pmu_domain_table import DOMAINS
    rows={}
    for row in frames(text,'N10PDS1',DOMAIN_FIELDS,identity,12).values():
        phase=row['phase'];generation=row['generation'];following=(generation+1)&0xffffffff
        if not following:following=1
        if (phase>=3 or row['seq']%3!=phase or not 0<generation<=0xffffffff or following!=completed or
            row['count']!=16 or row['seen']!=1 or row['error'] or row['status'] or
            any(row[k]>0xffff for k in ('before','state','after'))):raise ValueError('Invalid PMU domain status observation')
        snap={k:v for k,v in row.items() if k!='seq'};old=rows.setdefault(phase,dict(snapshot=snap,sequences=[]))
        if old['snapshot']!=snap:raise ValueError('Conflicting PMU domain status observations')
        old['sequences'].append(row['seq'])
    if set(rows)!={0,1,2} or any(len(r['sequences'])<2 for r in rows.values()):raise ValueError('Two intact domain status copies per phase required')
    for r in rows.values():
        s=r['snapshot'];r['domains']={name:dict(configuration_before=(s['before']>>i)&1,status=(s['state']>>i)&1,configuration_after=(s['after']>>i)&1) for i,(name,_,_) in enumerate(DOMAINS)}
        r['configuration_changed_mask']=s['before']^s['after']
        r['sampled_off']=[name for i,(name,_,_) in enumerate(DOMAINS) if not ((s['before']|s['state']|s['after'])&(1<<i))]
    return dict(phases=rows,domain_count=16,fields_are_sequential_not_atomic=True,power_request_performed=False,global_dma_shutdown_verified=False)


FSYS_FIELDS=('id','seq','phase','generation','reg','bad','ent','exit','gate','allow','deny','skip','ctrl','errors','done','result','negative','was_skip','status')

def decode_fsys(text,identity,completed):
    rows={}
    for row in frames(text,'N10FSP1',FSYS_FIELDS,identity,12).values():
        p=row['phase'];g=row['generation'];following=(g+1)&0xffffffff
        if not following:following=1
        if (p>=3 or row['seq']%3!=p or not 0<g<=0xffffffff or following!=completed or row['reg']!=1 or row['bad'] or row['status'] or
            any(v>0xffffffff for v in row.values()) or row['gate']!=row['allow']+row['deny'] or row['gate']>row['ent'] or
            row['exit']>row['ent'] or row['skip']>row['deny'] or row['ctrl']>2*row['allow'] or
            row['errors']>row['ctrl'] or row['done']>row['ctrl'] or row['negative']>1 or row['was_skip']>1 or
            row['result']>(0x80000000 if row['negative'] else 0x7fffffff)):
            raise ValueError('Invalid FSYS0A original-policy trace')
        snap={k:v for k,v in row.items() if k!='seq'};old=rows.setdefault(p,dict(snapshot=snap,sequences=[]))
        if old['snapshot']!=snap:raise ValueError('Conflicting FSYS0A policy trace')
        old['sequences'].append(row['seq'])
    if set(rows)!={0,1,2} or any(len(r['sequences'])<2 for r in rows.values()):raise ValueError('Two intact FSYS policy traces per phase required')
    counts=('ent','exit','gate','allow','deny','skip','ctrl','errors','done')
    for p,r in rows.items():
        s=r['snapshot'];r['callback_inflight']=s['ent']-s['exit']
        r['predicate_ever_denied']=bool(s['deny']);r['original_control_ever_called']=bool(s['ctrl'])
        if p and any(s[k]<rows[p-1]['snapshot'][k] for k in counts):raise ValueError('FSYS policy counters moved backwards')
    return dict(phases=rows,extra_power_requests=False,extra_predicate_calls=False,global_dma_shutdown_verified=False)
