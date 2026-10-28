"""Require complete guarded late/noirq and reverse-resume evidence, not sleep."""
from decode_cpu_cache import frames
from pmu_domain_table import DOMAINS

SUMMARY=('id','seq','generation','seen','bad','finished','stage','state','phase','late','late_ok','noirq','noirq_ok','point','blocked','ops','error','negative','original','original_negative','status')
RESTORE=('id','seq','generation','pre_early','post_early','pre_noirq','post_noirq','status')
DOMAIN=('id','seq','generation','seen','error','count','before','state','after','status')

def group(text,tag,fields,identity,completed):
    snapshot=None;sequences=[]
    for row in frames(text,tag,fields,identity,4).values():
        g=row['generation'];following=(g+1)&0xffffffff
        if not following:following=1
        if not 0<g<=0xffffffff or following!=completed or row['status'] or any(v>0xffffffff for v in row.values()):
            raise ValueError('Invalid noirq generation/status/bounds')
        current={k:v for k,v in row.items() if k!='seq'}
        if snapshot is not None and current!=snapshot:raise ValueError('Conflicting noirq copies')
        snapshot=current;sequences.append(row['seq'])
    if len(sequences)<2:raise ValueError('Two intact noirq copies per lane required')
    return dict(snapshot=snapshot,sequences=sequences)

def decode(text,identity,completed,cpu_roundtrip=False):
    summary=group(text,'N10PNQ1',SUMMARY,identity,completed)
    restore=group(text,'N10PNR1',RESTORE,identity,completed)
    domains=group(text,'N10PND1',DOMAIN,identity,completed)
    s=summary['snapshot'];r=restore['snapshot'];d=domains['snapshot']
    if (any(s[k]!=1 for k in ('seen','finished','late','late_ok','noirq','noirq_ok','point')) or
        any(s[k] for k in ('bad','blocked','ops','error','negative','original','original_negative')) or (s['stage'],s['state'],s['phase'])!=(7,3,6) or
        r['pre_early']!=r['post_early'] or r['pre_noirq']!=r['post_noirq'] or
        r['pre_early']>0x7fffffff or r['pre_noirq']>0x7fffffff or
        d['seen']!=1 or d['error'] or d['count']!=16 or any(d[k]>0xffff for k in ('before','state','after')) or
        len({s['generation'],r['generation'],d['generation']})!=1):
        raise ValueError('Guarded late/noirq roundtrip or restore did not pass')
    domains['domains']={name:dict(configuration_before=(d['before']>>i)&1,status=(d['state']>>i)&1,configuration_after=(d['after']>>i)&1) for i,(name,_,_) in enumerate(DOMAINS)}
    domains['configuration_changed_mask']=d['before']^d['after']
    domains['sampled_off']=[name for i,(name,_,_) in enumerate(DOMAINS) if not ((d['before']|d['state']|d['after'])&(1<<i))]
    return dict(pm_late_noirq_roundtrip_observed=True,noirq_pmu_domain_status_observed=True,
                summary=summary,restore=restore,power_domains=domains,
                source_guard_blocks_nonboot_cpu_disable=not cpu_roundtrip,source_guard_blocks_syscore=True,
                source_guard_blocks_irq_disable=True,cpu_roundtrip_separately_required=cpu_roundtrip,
                real_platform_sleep_entered=False,sequential_domain_reads_are_not_atomic=True,
                global_dma_shutdown_verified=False,xnu_executed=False)
