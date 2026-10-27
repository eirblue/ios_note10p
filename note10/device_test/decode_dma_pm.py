"""Validate three framework snapshots; never infer hardware DMA shutdown."""
from decode_cpu_cache import frames

def decode(text,identity,generation):
    fields=('id','seq','phase','generation','seen','error','total','dma','suspended','direct','syscore','uncovered','prepared','active','idle','other','names_xor','names_sum','status')
    rows=frames(text,'N10DMA1',fields,identity,24)
    phases={}
    for row in rows.values():
        phase=row['phase']
        completed=(row['generation']+1)&0xffffffff
        if not completed:completed=1
        if (phase>=3 or row['seq']%3!=phase or completed!=generation or not row['generation'] or row['seen']!=1 or
            row['error'] or row['status'] or not 0<row['dma']<=row['total']<=4096 or
            row['suspended']+row['direct']+row['syscore']+row['uncovered']!=row['dma'] or
            row['active']+row['idle']+row['other']!=row['dma'] or row['prepared']>row['dma'] or
            any(v>0xffffffff for v in row.values())):raise ValueError('Invalid DMA PM framework snapshot')
        snapshot={k:v for k,v in row.items() if k!='seq'}
        previous=phases.setdefault(phase,dict(snapshot=snapshot,sequences=[]))
        if previous['snapshot']!=snapshot:raise ValueError('Conflicting DMA PM snapshots')
        previous['sequences'].append(row['seq'])
    if set(phases)!=set(range(3)) or any(len(r['sequences'])<2 for r in phases.values()):
        raise ValueError('Two intact DMA PM snapshots per phase required')
    snapshots=[phases[n]['snapshot'] for n in range(3)]
    identities={(s['total'],s['dma'],s['names_xor'],s['names_sum']) for s in snapshots}
    if len(identities)!=1:raise ValueError('DMA-capable device inventory changed across PM')
    if any(snapshots[n]['prepared'] or snapshots[n]['suspended'] for n in (0,2)):
        raise ValueError('DMA PM framework initial/restored flags not clear')
    return dict(dma_pm_framework_observed=True,phases=phases,
        dma_capable_devices=snapshots[1]['dma'],uncovered_at_suspend=snapshots[1]['uncovered'],
        framework_name_digest_is_not_collision_proof=True,
        hardware_dma_shutdown_verified=False,gic_handoff_verified=False,xnu_executed=False)
