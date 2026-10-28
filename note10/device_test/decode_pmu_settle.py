"""Decode three separate timed PMU samples without requiring a power state."""
from decode_cpu_cache import frames
from pmu_domain_table import DOMAINS
FIELDS=('id','seq','generation','completed','index','target_ms','elapsed_ms','error','before','state','after','status')
TARGETS=(1000,5000,15000)

def decode(text,identity,completed):
    groups={};copies={}
    for row in frames(text,'N10PST1',FIELDS,identity,12).values():
        i=row['index'];g=row['generation'];following=(g+1)&0xffffffff
        if not following:following=1
        if (i not in range(3) or not 0<g<=0xffffffff or following!=completed or row['completed']!=completed or
            row['seq']//4!=i or row['target_ms']!=TARGETS[i] or not TARGETS[i]<=row['elapsed_ms']<=30000 or
            row['error'] or row['status'] or any(row[k]>0xffff for k in ('before','state','after'))):
            raise ValueError('Invalid timed post-resume PMU sample')
        current={k:v for k,v in row.items() if k!='seq'}
        if i in groups and groups[i]!=current:raise ValueError('Conflicting settled PMU copies')
        groups[i]=current;copies.setdefault(i,[]).append(row['seq'])
    if set(groups)!=set(range(3)) or any(len(copies[i])<2 for i in groups):raise ValueError('Three timed snapshots with two intact copies each required')
    if len({r['generation'] for r in groups.values()})!=1 or any(groups[i]['elapsed_ms']>=groups[i+1]['elapsed_ms'] for i in (0,1)):
        raise ValueError('Settled PMU generation/time order differs')
    for i,row in groups.items():
        row['configuration_changed_mask']=row['before']^row['after']
        row['domains']={name:dict(configuration_before=(row['before']>>j)&1,status=(row['state']>>j)&1,configuration_after=(row['after']>>j)&1) for j,(name,_,_) in enumerate(DOMAINS)}
    return dict(pmu_settled_post_resume_observed=True,samples=groups,sequences=copies,
                power_state_not_an_acceptance_condition=True,sequential_not_atomic=True,
                extra_power_requests=False,global_dma_shutdown_verified=False,xnu_executed=False)
