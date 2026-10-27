"""Require intact per-CPU PMR restoration evidence from one selected boot."""
from decode_cpu_cache import frames

def decode(text,identity):
    summaries=frames(text,'N10GIC2',('id','seq','before','after','cpus','error','status'),identity,32)
    if len(summaries)<2:raise ValueError('Two intact GIC summaries required')
    for row in summaries.values():
        if (row['before'],row['after'],row['cpus'],row['error'],row['status'])!=(255,255,8,0,0):
            raise ValueError('GIC CPU roundtrip summary failed')
    names=('id','seq','cpu','ctlr','pmr','masked','restored','bpr','ctlr_after','bpr_after','dist','typer','iidr','irq_before','irq_after','seen','status')
    cpus={}
    for row in frames(text,'N10GIC1',names,identity,32).values():
        cpu=row['cpu']
        if (any(v>0xffffffff for v in row.values()) or cpu>=8 or row['status'] or row['seen']!=1 or not row['ctlr']&1 or not row['dist']&3 or
            not 0<row['pmr']<=255 or row['masked'] or row['restored']!=row['pmr'] or
            row['ctlr_after']!=row['ctlr'] or row['bpr_after']!=row['bpr'] or
            row['irq_before'] not in (0,1) or row['irq_after']!=row['irq_before']):
            raise ValueError('GIC CPU priority mask or IRQ state restoration failed')
        snapshot={k:v for k,v in row.items() if k!='seq'}
        old=cpus.setdefault(cpu,{'snapshot':snapshot,'sequences':[]})
        if old['snapshot']!=snapshot:raise ValueError('Conflicting GIC CPU snapshots')
        old['sequences'].append(row['seq'])
    if set(cpus)!=set(range(8)) or any(len(v['sequences'])<2 for v in cpus.values()):
        raise ValueError('Two intact GIC snapshots per CPU required')
    return dict(gic_cpu_pmr_roundtrip_observed=True,cpus=cpus,summary_frames=len(summaries),
        distributor_modified=False,gic_handoff_verified=False,dma_shutdown_verified=False,
        cache_mmu_handoff_verified=False,xnu_executed=False)
