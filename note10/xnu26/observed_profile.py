"""Bind Linux CPU observations to limited XNU build/entry constraints.

No RAM selection/reservation, SMP enablement, MMIO, handoff or device access.
Input provenance is a file hash, not hardware attestation.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'note10/device_test'))
from decode_linux_caps import decode

RELEASE='4.14.113-note10-handoff-pc'
PA_BITS={0:32,1:36,2:40,3:42,4:44,5:48,6:52}


def derive(text):
    banners=re.findall(r'Linux version ([^\s\x00]+)',text)
    if banners!=[RELEASE]:raise ValueError('Exactly one expected diagnostic kernel banner required')
    caps=decode(text)
    if not caps['all_target_cpus_observed'] or not caps['all_target_cpus_support_16k']:
        raise ValueError('All eight target CPUs must report 16K support')
    cpus=caps['cpus']
    if any(c['registers']['el']!='0x4' for c in cpus):raise ValueError('Expected Linux EL1 register view')
    if any(c['compiled_40bit_ips_supported'] is not True for c in cpus):
        raise ValueError('Compiled 40bit IPS unsupported or unknown on a CPU')
    if len({int(c['registers']['mpidr'],16) for c in cpus})!=8:
        raise ValueError('Duplicate raw MPIDR observations')
    affinities={}
    for c in cpus:
        affinity=int(c['registers']['mpidr'],16)&0xff00ffffff
        affinities.setdefault(affinity,[]).append(c['cpu'])
    frequencies={int(c['registers']['cntfrq'],16) for c in cpus}
    if len(frequencies)!=1:raise ValueError('Inconsistent CPU timer frequency')
    def uniform(field):
        values={c[field] for c in cpus}
        if len(values)!=1:raise ValueError('Heterogeneous CTR minima need an explicit policy')
        return values.pop()
    i_line=uniform('ctr_instruction_minimum_line_bytes')
    d_line=uniform('ctr_data_minimum_line_bytes')
    lines=[v['maintenance_line_bytes'] for c in cpus for v in c['caches']]
    if not lines:raise ValueError('No cache observations')
    for c in cpus:
        cache={v['selector']:v['maintenance_line_bytes'] for v in c['caches']}
        # Initial profile requires an observed L1 data/unified and I cache.
        if 0 not in cache or 1 not in cache:raise ValueError('Separate L1 cache observations required')
        if cache[0]<d_line or cache[1]<i_line:raise ValueError('CCSIDR line smaller than CTR minimum')
    def exponent(value):
        if type(value) is not int or value<16 or value>2048 or value&(value-1):
            raise ValueError('Invalid observed cache line')
        return value.bit_length()-1
    defines={'N10_BOARD_SCHEMA':1,'N10_ICACHE_LINE_LOG2':exponent(i_line),
             'N10_DCACHE_LINE_LOG2':exponent(d_line),
             'N10_MAX_CACHE_LINE_LOG2':exponent(max([i_line,d_line,*lines])),
             'N10_KERNEL_PAGE_SHIFT':14}
    return {'kernel_release':RELEASE,'observed_cpu_count':8,'defines':defines,
            'minimum_pa_bits':min(c['physical_address_bits'] for c in cpus),
            'timer_frequency_hz':frequencies.pop(),
            'per_cpu':[{'cpu':c['cpu'],'registers':c['registers'],
                        'physical_address_bits':c['physical_address_bits'],'caches':c['caches']} for c in cpus],
            'compiled_cpu_limit':1,'smp_handoff_verified':False,
            'affinity_alias_groups':[ids for ids in affinities.values() if len(ids)>1],
            'cpu_topology_mapping_verified':False,
            'register_view':'Linux EL1; not bootloader or post-shutdown state',
            'xnu_hardware_execution_verified':False,'deployment_ready':False}


def check_tcr(profile,tcr):
    if type(tcr) is not int or not 0<=tcr<1<<64:raise ValueError('Invalid TCR integer')
    if ((tcr>>14)&3)!=2 or ((tcr>>30)&3)!=1:raise ValueError('Both bootstrap granules must be 16K')
    bits=PA_BITS.get((tcr>>32)&7)
    if bits is None or bits>48 or tcr&(1<<59):
        raise ValueError('Unsupported bootstrap address format')
    if bits>profile['minimum_pa_bits']:raise ValueError('TCR IPS exceeds observed CPU capacity')
    return {'tcr_el1':hex(tcr),'translation_granule_bytes':16384,'tcr_pa_bits':bits,
            'all_observed_cpus_cover_tcr_ips':True,'scope':'Capacity comparison only; MMU remains unexecuted'}


def header(profile):
    return ('/* Derived Linux observations; not an SMP or handoff contract. */\n'+
            ''.join('#define '+k+' '+str(v)+'\n' for k,v in profile['defines'].items())).encode()


def load(path):
    record=json.loads(path.read_text(encoding='utf-8'))
    source=Path(record['raw_log_path']);raw=source.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=record['raw_log_sha256']:raise ValueError('Observed log hash changed')
    profile=derive(raw.decode(errors='replace'))
    if profile!=record['profile']:raise ValueError('Stored profile differs from raw observations')
    if (path.parent/'observed-board.h').read_bytes()!=header(profile):raise ValueError('Observed header differs')
    return profile


def create(log,output):
    if not output.resolve().is_relative_to((ROOT/'note10/private').resolve()):raise ValueError('Private output required')
    if output.exists():raise ValueError('Refusing to overwrite an observation bundle')
    if not 0<log.stat().st_size<=16*1024*1024:raise ValueError('Invalid log size')
    raw=log.read_bytes();profile=derive(raw.decode(errors='replace'))
    record={'raw_log_path':str(log.resolve()),'raw_log_sha256':hashlib.sha256(raw).hexdigest(),
            'profile':profile,'provenance':'Local captured log and hash; not cryptographic device attestation',
            'device_operations':[]}
    output.mkdir(parents=True,exist_ok=False)
    (output/'observed-profile.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
    (output/'observed-board.h').write_bytes(header(profile))
    return profile


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--log',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();p=create(args.log,args.output)
    print(json.dumps({'defines':p['defines'],'observed_cpus':8,'minimum_pa_bits':p['minimum_pa_bits'],
                      'xnu_executed':False,'deployment_ready':False}))
