"""Strict CPU-mask restoration and a separate CPU-stop PMU domain lane."""
from decode_cpu_cache import frames
from decode_pm_noirq import group,DOMAIN
from pmu_domain_table import DOMAINS
SUMMARY=('id','seq','generation','seen','bad','attempted','disabled','enabled','before','stopped','restored','cpu','phase','original','negative','error','error_negative','status')
TIMERS=('id','seq','generation','cpu','pre_seen','seen','before','after','freq','status')

def decode_timers(text,identity,completed):
    groups={};copies={}
    for row in frames(text,'N10NCT1',TIMERS,identity,4).values():
        cpu=row['cpu']
        if (cpu>=8 or row['generation']!=completed or not 0<completed<=0xffffffff or row['status'] or
            row['pre_seen']!=1 or row['seen']!=1 or row['before']!=row['after'] or row['freq']!=26000000):
            raise ValueError('Post-noirq CPU timer register did not restore')
        current={k:v for k,v in row.items() if k!='seq'}
        if cpu in groups and groups[cpu]!=current:raise ValueError('Conflicting CPU timer readback copies')
        groups[cpu]=current;copies.setdefault(cpu,[]).append(row['seq'])
    if set(groups)!=set(range(8)) or any(len(copies[cpu])<2 for cpu in groups):raise ValueError('Eight CPU timer readbacks with two copies each required')
    return dict(pm_cpus_timer_restore_observed=True,cpus=groups,sequences=copies,register_writes=False,xnu_executed=False)

def decode(text,identity,completed):
    summary=group(text,'N10NPC1',SUMMARY,identity,completed)
    domains=group(text,'N10NPD1',DOMAIN,identity,completed)
    s=summary['snapshot'];d=domains['snapshot']
    if (any(s[k]!=1 for k in ('seen','attempted','disabled','enabled')) or
        any(s[k] for k in ('bad','cpu','original','negative','error','error_negative')) or
        (s['before'],s['stopped'],s['restored'],s['phase'])!=(255,1,255,6) or
        s['generation']!=d['generation'] or d['seen']!=1 or d['error'] or d['count']!=16 or
        any(d[k]>65535 for k in ('before','state','after'))):
        raise ValueError('CPU hotplug restore or CPU-stop PMU evidence failed')
    domains['domains']={name:dict(configuration_before=(d['before']>>i)&1,status=(d['state']>>i)&1,configuration_after=(d['after']>>i)&1) for i,(name,_,_) in enumerate(DOMAINS)}
    domains['configuration_changed_mask']=d['before']^d['after']
    return dict(pm_cpus_noirq_roundtrip_observed=True,cpu_stop_pmu_domains_observed=True,
        summary=summary,power_domains=domains,original_hotplug_apis_used=True,
        local_interrupts_disabled_by_extension=False,syscore_entered=False,
        global_dma_shutdown_verified=False,xnu_executed=False)
