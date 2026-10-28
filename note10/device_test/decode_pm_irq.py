"""Decode CPU0 local IRQ/architecture and read-only GIC observations."""
from decode_cpu_cache import frames
ARCH=('id','seq','phase','generation','seen','el','mpidr','sctlr','tcr','ttbr1','mair')
TIMER=('id','seq','phase','generation','cpu','online','count','irq','preempt','daif','cntkctl','cntfrq')
GIC=('id','seq','phase','generation','seen','cpu','online','count','irq','preempt','ctlr','pmr','bpr','iidr','dist','typer')
SUMMARY=('id','seq','generation','seen','bad','attempted','restored','complete','pre_before','pre_after','saved','error','status')

def group(text,tag,names,identity,phases):
    rows=frames(text,tag,names,identity,6 if phases==3 else 2);result=[]
    for phase in range(phases):
        seqs=(phase,phase+3) if phases==3 else (0,1)
        selected=[r for r in rows.values() if r['seq'] in seqs]
        if len(selected)!=2 or {r['seq'] for r in selected}!=set(seqs):raise ValueError('Missing IRQ evidence copies')
        snapshots=[{k:v for k,v in r.items() if k!='seq'} for r in selected]
        if snapshots[0]!=snapshots[1]:raise ValueError('Conflicting IRQ evidence copies')
        if phases==3 and snapshots[0]['phase']!=phase:raise ValueError('IRQ phase differs')
        result.append(snapshots[0])
    if len(rows)!=(6 if phases==3 else 2):raise ValueError('Unexpected IRQ evidence rows')
    return result

def decode(text,identity,completed,cpu_cache,timers):
    if not 0<completed<=0xffffffff:raise ValueError('Invalid completed generation')
    summary=group(text,'N10IQR1',SUMMARY,identity,1)[0];begin=summary['generation']
    if not 0<begin<=0xffffffff or ((begin+1)&0xffffffff or 1)!=completed or any(summary[k]!=1 for k in ('seen','attempted','restored','complete')) or any(summary[k] for k in ('bad','pre_before','pre_after','error','status')):raise ValueError('IRQ transaction did not complete')
    arch=group(text,'N10IAR1',ARCH,identity,3);timer=group(text,'N10ITR1',TIMER,identity,3);gic=group(text,'N10IGR1',GIC,identity,3)
    for phase in range(3):
        a,t,g=arch[phase],timer[phase],gic[phase]
        if any(x['generation']!=begin for x in (a,t,g)) or a['seen']!=1 or g['seen']!=1:raise ValueError('IRQ generation or sample differs')
        for x in (t,g):
            if (x['cpu'],x['online'],x['count'],x['irq'],x['preempt'])!=(0,1,1,int(phase==1),1):raise ValueError('IRQ context differs')
        if a['el']!=4 or a['sctlr']&0x1005!=0x1005 or t['cntfrq']!=26000000:raise ValueError('IRQ CPU register state invalid')
        if any(g[k]>0xffffffff for k in ('ctlr','pmr','bpr','iidr','dist','typer')):raise ValueError('IRQ GIC value exceeds u32')
        if not (g['ctlr']&1) or not (g['dist']&3) or not 0<g['pmr']<=255:raise ValueError('IRQ GIC interface not enabled')
    initial=timer[0]['daif']
    if initial&0x80 or summary['saved']!=initial or timer[1]['daif']!=(initial|0x80) or timer[2]['daif']!=initial:raise ValueError('IRQ flags were not exactly restored')
    for phase in (1,2):
        if any(arch[phase][k]!=arch[0][k] for k in ('el','mpidr','sctlr','tcr','ttbr1','mair')) or any(timer[phase][k]!=timer[0][k] for k in ('cntkctl','cntfrq')) or any(gic[phase][k]!=gic[0][k] for k in ('ctlr','pmr','bpr','iidr','dist','typer')):raise ValueError('IRQ local registers changed')
    before=cpu_cache['cpus'][0]['snapshot'];post_timer=timers['cpus'][0]
    if any(arch[0][k]!=before[k] for k in ('mpidr','sctlr','tcr','mair')) or ((arch[0]['ttbr1']^before['ttbr1'])&0x0000ffffffffffff) or timer[0]['cntkctl']!=post_timer['after'] or timer[0]['cntfrq']!=post_timer['freq']:raise ValueError('IRQ baseline binding differs')
    return {'cpu0_irq_arch_timer':True,'cpu0_irq_gic_readback':True,'architecture':arch,'timer':timer,'gic':gic,
            'syscore_callbacks_executed':False,'hardware_dma_shutdown_verified':False,'xnu_executed':False}
