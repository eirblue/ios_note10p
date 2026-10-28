"""Bind post-PM per-CPU architecture and payload observations to baseline."""
from decode_cpu_cache import frames

ARCH = ('id','seq','generation','cpu','pre_seen','seen','el','mpidr','sctlr','tcr','ttbr1','mair','status')
PAYLOAD = ('id','seq','generation','cpu','pre_seen','seen','words','fnv','status')
MASK = (1 << 48) - 1


def lane(text, tag, fields, identity, generation):
    result = {}
    for row in frames(text, tag, fields, identity, 4).values():
        cpu = row['cpu']
        if cpu >= 8 or not 0 < generation <= 0xffffffff or row['generation'] != generation:
            raise ValueError('Post-PM CPU or generation invalid')
        if row['pre_seen'] != 1 or row['seen'] != 1 or row['status']:
            raise ValueError('Post-PM CPU sample failed')
        snapshot = {k:v for k,v in row.items() if k != 'seq'}
        current = result.setdefault(cpu, {'snapshot':snapshot, 'sequences':[]})
        if current['snapshot'] != snapshot:
            raise ValueError('Conflicting post-PM CPU copies')
        current['sequences'].append(row['seq'])
    if set(result) != set(range(8)) or any(len(v['sequences']) < 2 for v in result.values()):
        raise ValueError('Two post-PM samples for each of eight CPUs required')
    return result


def decode(text, identity, generation, baseline, payload_size):
    if type(payload_size) is not int or payload_size <= 0 or payload_size % 8:
        raise ValueError('Invalid payload size')
    cpus = baseline.get('cpus', {})
    arch = lane(text, 'N10PAR1', ARCH, identity, generation)
    payload = lane(text, 'N10PCL1', PAYLOAD, identity, generation)
    for cpu in range(8):
        original = cpus.get(cpu, cpus.get(str(cpu)))
        if not isinstance(original, dict) or not isinstance(original.get('snapshot'), dict):
            raise ValueError('Missing baseline CPU sample')
        b = original['snapshot']; a = arch[cpu]['snapshot']; p = payload[cpu]['snapshot']
        if (a['el'] != 4 or a['sctlr'] & 0x1005 != 0x1005 or
            any(a[k] != b[k] for k in ('el','mpidr','sctlr','tcr','mair')) or
            (a['ttbr1'] & MASK) != (b['ttbr1'] & MASK)):
            raise ValueError('Post-PM architectural state differs')
        if p['words'] != payload_size // 8 or p['words'] != b['words'] or p['fnv'] != b['fnv']:
            raise ValueError('Post-PM CPU payload read differs')
    return dict(pm_cpus_arch_restore_observed=True, pm_cpus_payload_readback_observed=True,
                arch=arch, payload=payload, ttbr1_asid_bits_excluded=True,
                register_writes=False, xnu_executed=False, global_dma_shutdown_verified=False)
