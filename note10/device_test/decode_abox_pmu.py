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
    return dict(abox_pmu_controls_observed=True,
        phases={p:{c:rows[p,c] for c in range(2)} for p in range(3)},
        pmu_read_api_used=True,pmu_writes_performed=False,control_bits_are_not_power_off_acknowledgments=True,
        audio_dsp_shutdown_verified=False,global_dma_shutdown_verified=False,xnu_executed=False)
