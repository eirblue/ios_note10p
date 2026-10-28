"""Strict independent decoder for bounded PM edge software inventories."""
import re
from decode_reservation import checksum

DMA='id seq phase generation total dma prepared suspended late noirq direct syscore covered excdirect excsyscore uncovered active idle other names_xor names_sum'.split()
IOMMU='id seq phase generation total active suspended runtime manual_off manual_on boot_hold secure mapped syscore direct prepared pm_suspended late noirq other names_xor names_sum policy details'.split()
DETAIL='id seq phase generation index count length name activations runtime manual active suspended effective syscore direct prepared pm_suspended late noirq hold secure mapped'.split()
SYS='id seq phase generation index count mask slength sname rlength rname dlength dname'.split()
OK='id seq generation status'.split()
DECIMAL={'seq','phase','generation','index','count','kind','length','slength','rlength','dlength','status'}

def rows(text,tag,fields,identity,limit):
    pattern=re.escape(tag)+' ('+' '.join(k+(r'=([^\s=]+)' if k in ('sname','rname','dname') else '=([0-9a-f-]+)') for k in fields)+r') checksum=([0-9a-f]{8})(?=\r?\n|$)'
    result={}
    for match in re.finditer(pattern,text):
        body,*values,digest=match.groups();row=dict(zip(fields,values))
        if row['id']!=identity or checksum(body.encode('ascii'))!=int(digest,16):continue
        for key in fields:
            if key in ('id','name','sname','rname','dname'):continue
            value=row[key]
            if len(value)>10 or not re.fullmatch('[0-9]+' if key in DECIMAL else '[0-9a-f]+',value):raise ValueError('Invalid PM edge integer')
            row[key]=int(value,10 if key in DECIMAL else 16)
            if row[key]>0xffffffff:raise ValueError('PM edge integer overflow')
        seq=row['seq']
        if seq>=limit or seq in result:raise ValueError('Duplicate or invalid PM edge sequence')
        result[seq]=row
    return result

def canonical(row):return {k:v for k,v in row.items() if k not in ('id','seq')}
def next_generation(value):return ((value+1)&0xffffffff) or 1

def require_pair(records,seq0,seq1):
    if seq0 not in records or seq1 not in records:raise ValueError('Missing PM edge copies')
    a,b=records[seq0],records[seq1]
    if canonical(a)!=canonical(b):raise ValueError('Conflicting PM edge copies')
    return a

def decode_name(row):
    name=row['name'];length=row['length']
    if not length:
        if name!='-':raise ValueError('Invalid empty name sentinel')
        return ''
    if length>63 or len(name)!=2*length or not re.fullmatch('[0-9a-f]+',name):raise ValueError('Invalid PM edge name length')
    raw=bytes.fromhex(name)
    if any(c<33 or c>126 or c==61 for c in raw):raise ValueError('Invalid PM edge name bytes')
    return raw.decode('ascii')

def decode(text,identity,completed,old_dma,old_iommu):
    if not 0<completed<=0xffffffff:raise ValueError('Invalid completion generation')
    ok=rows(text,'N10EOK1',OK,identity,2)
    marker=require_pair(ok,0,1)
    begin=marker['generation']
    if len(ok)!=2 or marker['status'] or not begin or next_generation(begin)!=completed:raise ValueError('PM edge producer failed')
    if re.search(r'N10EER1 id='+re.escape(identity)+r' ',text):raise ValueError('PM edge failure record present')
    dma=rows(text,'N10EDG1',DMA,identity,8);iommu=rows(text,'N10EIM1',IOMMU,identity,8)
    details=rows(text,'N10EID1',DETAIL,identity,64);syscore=rows(text,'N10ESC1',SYS,identity,256)
    if len(dma)!=8 or len(iommu)!=8:raise ValueError('Incomplete PM edge aggregate rows')
    dph=[];mph=[];identities=[]
    for phase in range(4):
        d=require_pair(dma,phase,4+phase);m=require_pair(iommu,phase,4+phase)
        if d['phase']!=phase or m['phase']!=phase or d['generation']!=begin or m['generation']!=begin:raise ValueError('PM edge phase binding differs')
        if not 0<d['dma']<=d['total']<=4096 or any(d[k]>d['dma'] for k in ('prepared','suspended','late','noirq','direct','syscore','covered','excdirect','excsyscore','uncovered','active','idle','other')):raise ValueError('Invalid DMA coverage counts')
        if d['covered']+d['excdirect']+d['excsyscore']+d['uncovered']!=d['dma'] or d['active']+d['idle']+d['other']!=d['dma'] or d['noirq']>d['late'] or d['late']>d['suspended'] or d['excdirect']>d['direct'] or d['excsyscore']>d['syscore']:raise ValueError('Invalid DMA coverage equations')
        if d['covered'] != (d['late'] if phase==1 else d['noirq'] if phase==2 else 0):raise ValueError('DMA phase coverage differs')
        if phase in (0,3) and (d['prepared'] or d['suspended'] or d['late'] or d['noirq']):raise ValueError('DMA initial/restored flags not clear')
        mcounts=('active','suspended','runtime','manual_off','manual_on','boot_hold','secure','mapped','syscore','direct','prepared','pm_suspended','late','noirq','other','policy')
        if not 0<m['total']<=64 or any(m[k]>m['total'] for k in mcounts) or m['details']>min(8,m['total']):raise ValueError('Invalid IOMMU inventory counts')
        if m['active']+m['suspended']>m['total'] or m['manual_off']+m['manual_on']>m['total'] or m['noirq']>m['late'] or m['late']>m['pm_suspended'] or m['policy']>m['active'] or m['policy']>m['runtime']+m['manual_on']:raise ValueError('Invalid IOMMU equations')
        if phase in (0,3) and (m['prepared'] or m['pm_suspended'] or m['late'] or m['noirq']):raise ValueError('IOMMU initial/restored flags not clear')
        entries=[]
        for index in range(m['details'] or 1):
            x=require_pair(details,phase*8+index,32+phase*8+index)
            if x['phase']!=phase or x['generation']!=begin or x['index']!=index or x['count']!=m['details']:raise ValueError('IOMMU identity binding differs')
            name=decode_name(x);bits=('active','suspended','effective','syscore','direct','prepared','pm_suspended','late','noirq','hold','secure','mapped')
            if any(x[k] not in (0,1) for k in bits) or x['activations']>1024 or x['runtime']>1024 or x['manual']>2:raise ValueError('Invalid IOMMU identity state')
            if not m['details']:
                if index or name or any(x[k] for k in ('activations','runtime','manual')+bits):raise ValueError('Invalid IOMMU empty sentinel')
                continue
            if not name or x['active']!=int(not x['suspended'] and x['activations']>0) or x['effective']!=int(bool(x['active'] and ((x['runtime']>0 and x['manual']==0) or x['manual']==2))) or not (x['runtime'] or x['manual'] or x['hold'] or x['syscore'] or x['direct']):raise ValueError('Invalid IOMMU policy')
            if x['noirq']>x['late'] or x['late']>x['pm_suspended']:raise ValueError('Invalid IOMMU per-device PM flags')
            entries.append(dict(x,name=name))
        if len({x['name'] for x in entries})!=len(entries):raise ValueError('Duplicate IOMMU identity')
        checks={'runtime':sum(x['runtime']>0 and not x['manual'] for x in entries),'manual_off':sum(x['manual']==1 for x in entries),'manual_on':sum(x['manual']==2 for x in entries),'boot_hold':sum(x['hold'] for x in entries),'syscore':sum(x['syscore'] for x in entries),'direct':sum(x['direct'] for x in entries),'policy':sum(x['effective'] for x in entries)}
        if any(m[k]!=v for k,v in checks.items()):raise ValueError('IOMMU exception coverage incomplete')
        if any(sum(x[k] for x in entries)>m[k] for k in ('active','suspended','secure','mapped','prepared','pm_suspended','late','noirq')):raise ValueError('IOMMU details exceed aggregate')
        dph.append(d);mph.append(m);identities.append(entries)
    if len(details)!=2*sum(m['details'] or 1 for m in mph):raise ValueError('Extra IOMMU identities')
    if len({(d['total'],d['dma'],d['names_xor'],d['names_sum']) for d in dph})!=1 or len({(m['total'],m['names_xor'],m['names_sum']) for m in mph})!=1:raise ValueError('PM edge inventory changed')
    syssets=[frozenset(x['name'] for x in phase if x['syscore']) for phase in identities]
    if len(set(syssets))!=1:raise ValueError('IOMMU syscore identity changed')
    for edge,old in ((0,0),(3,2)):
        od=old_dma['phases'][old]['snapshot'];om=old_iommu['phases'][old]['snapshot']
        if any(dph[edge][k]!=od[k] for k in ('total','dma','names_xor','names_sum')) or any(mph[edge][k]!=om[k] for k in ('total','names_xor','names_sum','syscore')):raise ValueError('Prior inventory binding differs')
        old_entries=old_iommu['controller_details'][old]['controllers']
        if syssets[edge]!=frozenset(x['name'] for x in old_entries if x['syscore']):raise ValueError('Prior IOMMU syscore identities differ')
    ordered=[]
    for slot,phase in enumerate((0,3)):
        inventory=[];count=None
        for index in range(64):
            first=slot*64+index
            if first not in syscore:break
            x=require_pair(syscore,first,128+first)
            if x['phase']!=phase or x['generation']!=begin or x['index']!=index or not 0<x['count']<=64 or x['mask']>7:raise ValueError('Invalid syscore identity row')
            if count is None:count=x['count']
            if x['count']!=count:raise ValueError('Inconsistent syscore count')
            names=[]
            for kind,prefix in enumerate(('s','r','d')):
                length=x[prefix+'length'];name=x[prefix+'name']
                if length==0:
                    if name!='-':raise ValueError('Invalid syscore empty sentinel')
                    name=''
                elif length>63 or len(name)!=length or any(ord(c)<33 or ord(c)>126 or c=='=' for c in name):raise ValueError('Invalid syscore symbol')
                if bool(name)!=bool(x['mask']&(1<<kind)):raise ValueError('Syscore callback sentinel differs')
                names.append(name)
            inventory.append((x['mask'],tuple(names)))
        if not count or len(inventory)!=count:raise ValueError('Incomplete syscore inventory')
        ordered.append(inventory)
    if ordered[0]!=ordered[1] or len(syscore)!=4*len(ordered[0]):raise ValueError('Changed or extra syscore inventory')
    return {'dma_noirq_coverage':True,'iommu_noirq_inventory':True,'syscore_inventory':True,
            'dma_phases':[canonical(x) for x in dph], 'iommu_phases':[canonical(x) for x in mph],
            'iommu_identities':identities,'syscore_entries':ordered[0],
            'hardware_dma_shutdown_verified':False,'syscore_callbacks_executed':False}
