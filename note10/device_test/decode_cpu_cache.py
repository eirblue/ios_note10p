"""Strict same-boot CPU offline/online, cache and per-CPU readback evidence."""
import re
from decode_reservation import checksum
from decode_xnu_stage import decode as decode_stage


def frames(text,tag,names,identity,maximum):
    pattern=tag+' ('+' '.join(name+'=([0-9a-f]+)' for name in names)+r') checksum=([0-9a-f]{8})(?=\r?\n|$)'
    records={}
    decimal={'seq','cpu','cpus','words','clean','status','devices','resume','blocked','oldlevel','newlevel',
             'resume_errors','timers','error'}
    for match in re.finditer(pattern,text):
        body,*values,digest=match.groups()
        row=dict(zip(names,values))
        if row['id']!=identity or checksum(body.encode('ascii'))!=int(digest,16):continue
        parsed={}
        for name,value in row.items():
            if name=='id':continue
            if name=='sha256' and len(value)!=64:raise ValueError('Invalid CPU/cache SHA256 width')
            if name in decimal and not value.isdigit():raise ValueError('Nondecimal CPU/cache value')
            number=int(value,10 if name in decimal else 16)
            if name!='sha256' and number>=1<<64:raise ValueError('CPU/cache integer overflow')
            parsed[name]=number
        if parsed['seq']>=maximum:raise ValueError('Unexpected CPU/cache sequence')
        key=(parsed.get('cpu'),parsed['seq'])
        if key in records:raise ValueError('Duplicate CPU/cache sequence / merged boots')
        records[key]=parsed
    return records


def decode(text,identity,payload_sha256,payload_size):
    stage=decode_stage(text,identity,payload_sha256,payload_size)
    summaries=frames(text,'N10QUI1',
        ('id','seq','before','stopped','restored','cpus','words','fnv','sha256','clean','status'),identity,32)
    if len(summaries)<2:raise ValueError('Two intact CPU/cache summary frames required')
    baseline=None
    for row in summaries.values():
        current={k:v for k,v in row.items() if k!='seq'}
        if baseline is not None and current!=baseline:raise ValueError('Conflicting CPU/cache summaries')
        baseline=current
        if (row['before'],row['stopped'],row['restored'],row['cpus'],row['words'],row['clean'],row['status'])!=(
                0xff,1,0xff,8,payload_size//8,1,0) or row['sha256']!=int(payload_sha256,16):
            raise ValueError('CPU offline/online or cache/readback batch did not pass')
    cpus=frames(text,'N10CPU2',
        ('id','seq','cpu','el','mpidr','sctlr','tcr','ttbr1','mair','cntkctl','cntfrq','words','fnv'),identity,8)
    observed={}
    for row in cpus.values():
        cpu=row['cpu']
        if cpu>=8:raise ValueError('Unexpected CPU in roundtrip evidence')
        if (row['el']!=4 or row['cntfrq']!=26000000 or row['sctlr']&0x1005!=0x1005 or
            row['words']!=payload_size//8 or row['fnv']!=baseline['fnv']):
            raise ValueError('CPU state or payload readback differs')
        current={k:v for k,v in row.items() if k!='seq'}
        previous=observed.setdefault(cpu,{'snapshot':current,'sequences':[]})
        if previous['snapshot']!=current:raise ValueError('Conflicting CPU register snapshots')
        previous['sequences'].append(row['seq'])
    if set(observed)!=set(range(8)) or any(len(v['sequences'])<2 for v in observed.values()):
        raise ValueError('Two intact snapshots from each of eight CPUs required')
    return {'previous_boot_cpu_cache_roundtrip_observed':True,
        'summary_intact_frame_count':len(summaries),'cpus':observed,
        'online_before':255,'online_stopped':1,'online_restored':255,
        'payload_sha256':payload_sha256,'payload_size':payload_size,
        'linux_cpu_offline_roundtrip_observed':True,'cached_payload_readback_observed':True,
        'dma_quiescence_verified':False,'cache_mmu_shutdown_verified':False,
        'gic_handoff_verified':False,'xnu_executed':False,'region':stage['region'],
        'scope':'Previous Linux CPU offline/online and cached coherency diagnostic; not XNU handoff'}
