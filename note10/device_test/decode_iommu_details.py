"""Selected registered-controller identities, kept in private captures."""
import re
from decode_reservation import checksum

def decode(text,identity,completed,aggregate):
    fields=('id','seq','phase','generation','index','count','length','name','activations','runtime_count',
        'manual','active','suspended','effective','syscore','prepared','pm_suspended','hold','secure','mapped','status')
    decimal={'seq','phase','generation','index','count','length','status'}
    bits=('active','suspended','effective','syscore','prepared','pm_suspended','hold','secure','mapped')
    values=('activations','runtime_count','manual')+bits
    pattern='N10MMD1 ('+' '.join(k+'=([0-9a-f]+)' for k in fields)+r') checksum=([0-9a-f]{8})(?=\r?\n|$)'
    records={};sequences=set()
    for match in re.finditer(pattern,text):
        body,*raw,digest=match.groups();row=dict(zip(fields,raw))
        if row['id']!=identity or checksum(body.encode())!=int(digest,16):continue
        parsed={}
        for key,value in row.items():
            if key in ('id','name'):continue
            if len(value)>16 or (key in decimal and not value.isdigit()):raise ValueError('Invalid IOMMU identity integer')
            parsed[key]=int(value,10 if key in decimal else 16)
        phase=parsed['phase'];index=parsed['index'];sequence=parsed['seq'];count=parsed['count']
        next_generation=(parsed['generation']+1)&0xffffffff
        if not next_generation:next_generation=1
        if (phase>=3 or sequence>=96 or (sequence//8)%3!=phase or sequence%8!=index or index>=8 or count>8 or
            not 0<parsed['generation']<=0xffffffff or next_generation!=completed or parsed['status'] or
            parsed['generation']!=aggregate[phase]['snapshot']['generation'] or
            count!=aggregate[phase]['snapshot']['exceptions'] or parsed['length']>63 or
            any(parsed[k] not in (0,1) for k in bits) or parsed['activations']>1024 or
            parsed['runtime_count']>1024 or parsed['manual']>2):raise ValueError('Invalid IOMMU identity record')
        if sequence in sequences:raise ValueError('Duplicate IOMMU identity sequence')
        sequences.add(sequence)
        if not count:
            if index or parsed['length'] or row['name']!='00' or any(parsed[k] for k in values):
                raise ValueError('Invalid empty IOMMU identity inventory')
            name=''
        else:
            if index>=count or not parsed['length'] or len(row['name'])!=parsed['length']*2:
                raise ValueError('IOMMU identity name length differs')
            name_bytes=bytes.fromhex(row['name'])
            if any(not 33<=byte<=126 for byte in name_bytes):raise ValueError('Nonprintable IOMMU device name')
            name=name_bytes.decode('ascii')
            active=int(not parsed['suspended'] and parsed['activations']>0)
            effective=int(bool(active and ((parsed['runtime_count']>0 and not parsed['manual']) or parsed['manual']==2)))
            if parsed['active']!=active or parsed['effective']!=effective or not (
                parsed['runtime_count'] or parsed['manual'] or parsed['hold'] or parsed['syscore']):
                raise ValueError('IOMMU identity driver policy predicate differs')
        snapshot={k:v for k,v in parsed.items() if k!='seq'};snapshot['name']=name
        old=records.setdefault((phase,index),dict(snapshot=snapshot,sequences=[]))
        if old['snapshot']!=snapshot:raise ValueError('Conflicting IOMMU controller identity')
        old['sequences'].append(sequence)
    result={};syscore_sets=[]
    def fnv(name):
        value=2166136261
        for byte in name.encode():value=((value^byte)*16777619)&0xffffffff
        return value
    for phase in range(3):
        snapshot=aggregate[phase]['snapshot'];count=snapshot['exceptions']
        expected={(phase,index) for index in range(count or 1)}
        if {key for key in records if key[0]==phase}!=expected or any(len(records[k]['sequences'])<2 for k in expected):
            raise ValueError('Two matching records for every selected IOMMU controller required')
        entries=[records[(phase,index)]['snapshot'] for index in range(count)]
        if len({entry['name'] for entry in entries})!=count:raise ValueError('Ambiguous IOMMU controller names')
        sums={'runtime':sum(e['runtime_count']>0 and not e['manual'] for e in entries),
            'manual_off':sum(e['manual']==1 for e in entries),'manual_on':sum(e['manual']==2 for e in entries),
            'boot_hold':sum(e['hold'] for e in entries),'syscore':sum(e['syscore'] for e in entries),
            'policy_active':sum(e['effective'] for e in entries)}
        if any(snapshot[k]!=value for k,value in sums.items()):raise ValueError('IOMMU selected identities do not cover aggregate policy/exception counts')
        for name,key in (('active','active'),('suspended','suspended'),('secure','secure_configured'),('mapped','mapped'),('prepared','prepared'),('pm_suspended','pm_suspended')):
            if sum(e[name] for e in entries)>snapshot[key]:raise ValueError('IOMMU selected identity flags exceed aggregate')
        if count==snapshot['total']:
            hashes=[fnv(e['name']) for e in entries];xor=0
            for value in hashes:xor^=value
            if xor!=snapshot['names_xor'] or sum(hashes)&0xffffffff!=snapshot['names_sum']:
                raise ValueError('Complete IOMMU identity inventory differs from aggregate digest')
        syscore_sets.append(frozenset(e['name'] for e in entries if e['syscore']))
        result[phase]=dict(controllers=entries,policy_active=snapshot['policy_active'],selected_count=count)
    if len(set(syscore_sets))!=1:raise ValueError('IOMMU syscore identities changed across PM phases')
    return result
