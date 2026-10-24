"""Decode explicit diagnostic printk records; never infer unobserved CPUs."""
import argparse
import json
from pathlib import Path
import re


def decode(text):
    records = re.findall(r'N10CAP1 ([A-Z]+) ([^\r\n]*)', text)
    if not 2 <= len(records) <= 1000 or records[0][0]!='BEGIN' or records[-1][0]!='END':
        raise ValueError('Incomplete or excessive diagnostic records')
    def values(raw, keys, decimal):
        fields = raw.split()
        if len(fields)!=len(keys):raise ValueError('Wrong diagnostic field count')
        result={}
        for field in fields:
            match=re.fullmatch(r'([a-z0-9]+)=([0-9a-f]+)',field)
            if not match:raise ValueError('Malformed diagnostic field')
            key,value=match.groups()
            if key not in keys or key in result:raise ValueError('Unexpected/duplicate diagnostic field')
            if key in decimal and not value.isdecimal():raise ValueError('Invalid decimal field')
            number=int(value,10 if key in decimal else 16)
            if number >= 1<<64:raise ValueError('Diagnostic integer exceeds register width')
            result[key]=number
        if set(result)!=set(keys):raise ValueError('Missing diagnostic fields')
        return result
    begin=values(records[0][1],('online',),('online',))['online']
    end=values(records[-1][1],('online',),('online',))['online']
    if not 1<=begin<=8 or begin!=end:raise ValueError('Unexpected or changing CPU count')
    cpus={};caches={};restores={}
    for kind,raw in records[1:-1]:
        if kind=='CPU':
            item=values(raw,('cpu','el','mpidr','mmfr0','mmfr1','isar1','clidr','ctr','cntfrq'),('cpu',))
            cpu=item['cpu']
            if cpu>=8 or cpu in cpus or item['el'] not in (4,8):raise ValueError('Invalid/duplicate CPU record')
            if not 0<item['cntfrq']<=0xffffffff:raise ValueError('Invalid timer frequency')
            cpus[cpu]=item
        elif kind=='CACHE':
            item=values(raw,('cpu','selector','value'),('cpu','selector'))
            key=(item['cpu'],item['selector'])
            if key in caches or key[0]>=8 or key[1]>=14:raise ValueError('Invalid/duplicate cache record')
            caches[key]=item['value']
        elif kind=='RESTORE':
            item=values(raw,('cpu','before','after'),('cpu',));cpu=item['cpu']
            if cpu>=8 or cpu in restores or item['before']!=item['after']:raise ValueError('CSSELR restore failed')
            restores[cpu]=item
        else:raise ValueError('Unexpected or repeated session marker')
    if len(cpus)!=begin or set(restores)!=set(cpus) or any(c not in cpus for c,s in caches):
        raise ValueError('Missing/extra CPU diagnostics')
    result=[]
    for cpu,item in sorted(cpus.items()):
        expected=set()
        for level in range(7):
            kind=(item['clidr']>>(level*3))&7
            if kind>4:raise ValueError('Reserved CLIDR cache type')
            if kind in (2,3,4):expected.add(level<<1)
            if kind in (1,3):expected.add((level<<1)|1)
        if {s for c,s in caches if c==cpu}!=expected:raise ValueError('Incomplete cache selector coverage')
        granule=(item['mmfr0']>>20)&15
        result.append({'cpu':cpu,'registers':{k:hex(v) for k,v in item.items() if k!='cpu'},
                       'stage1_16k_supported':True if granule in (1,2) else False if granule==0 else None,
                       'caches':[{'selector':s,'ccsidr':hex(caches[cpu,s]),
                                  'maintenance_line_bytes':1<<((caches[cpu,s]&7)+4)} for s in sorted(expected)]})
    supports=[c['stage1_16k_supported'] for c in result]
    return {'observed_cpus':len(result),'all_target_cpus_observed':len(result)==8,
            'all_target_cpus_support_16k':all(supports) if len(result)==8 and None not in supports else None,
            'cpus':result,'scope':'Linux privileged register view; not bootloader entry state or full cache capacity',
            'xnu_executed':False,'boot_contract_verified':False,'deployment_ready':False}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('log',type=Path)
    path=parser.parse_args().log
    if path.stat().st_size>16*1024*1024:raise ValueError('Log exceeds decoder size cap')
    print(json.dumps(decode(path.read_text(encoding='utf-8',errors='replace')),indent=2))
