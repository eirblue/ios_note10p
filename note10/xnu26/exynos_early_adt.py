"""Synthetic PC early-consumer AppleDT for the XNU 12377.121.6 Exynos profile.

This is a necessary early shape, not a complete platform tree or live handoff.
Inputs provide no actual CPU, DRAM, ownership, rootfs or return qualification.
"""
import struct
from boot_adt import Node, encode, decode

PROFILE = 'xnu-12377.121.6/ac9718fb1af618d5ce8678d0dc6e8a58f252216f/EXYNOS9825/MAX_CPUS=1'
FIELDS = ('cpu_affinity', 'timebase_frequency', 'dram_base', 'dram_size')


def _values(cpu_affinity, timebase_frequency, dram_base, dram_size):
    values = dict(zip(FIELDS, (cpu_affinity, timebase_frequency, dram_base, dram_size)))
    if any(type(value) is not int for value in values.values()):
        raise ValueError('Explicit integer scalars required')
    # ml_readprop accepts 64 bits, but topology phys_id narrows to uint32_t.
    if not 0 <= cpu_affinity <= 0xffffffff:
        raise ValueError('CPU affinity would lose bits in target phys_id')
    if not 1000000 <= timebase_frequency <= 0x7fffffff:
        raise ValueError('Timebase outside the selected early-clock contract')
    if not 0 <= dram_base <= 0xffffffffffffffff or not 0 < dram_size <= 0xffffffffffffffff - dram_base:
        raise ValueError('Invalid or overflowing explicit DRAM span')
    return values


def encode_early_adt(*, cpu_affinity, timebase_frequency, dram_base, dram_size):
    _values(cpu_affinity, timebase_frequency, dram_base, dram_size)
    cpu = Node('cpu@' + format(cpu_affinity, 'x'), {
        'device_type': b'cpu\0', 'reg': struct.pack('<I', cpu_affinity),
        'state': b'running\0', 'timebase-frequency': struct.pack('<I', timebase_frequency)})
    chosen = Node('chosen', {'dram-base': struct.pack('<Q', dram_base),
                             'dram-size': struct.pack('<Q', dram_size)})
    return encode(Node('device-tree', children=[Node('cpus', children=[cpu]), chosen]))


def decode_early_adt(raw):
    if not isinstance(raw, bytes) or not 0 < len(raw) <= 16384:
        raise ValueError('Early component must fit one 16 KiB page')
    root = decode(raw)
    if root.name != 'device-tree' or root.properties or len(root.children) != 2:
        raise ValueError('Expected the fixed early component root')
    children = {node.name: node for node in root.children}
    if set(children) != {'cpus', 'chosen'}:
        raise ValueError('Mandatory cpus/chosen nodes missing')
    cpus, chosen = children['cpus'], children['chosen']
    if cpus.properties or len(cpus.children) != 1 or chosen.children:
        raise ValueError('Selected MAX_CPUS=1 profile required')
    cpu = cpus.children[0]
    if cpu.children or set(cpu.properties) != {'device_type', 'reg', 'state', 'timebase-frequency'} or set(chosen.properties) != {'dram-base', 'dram-size'}:
        raise ValueError('Unexpected or missing early properties')
    if cpu.properties['device_type'] != b'cpu\0' or cpu.properties['state'] != b'running\0':
        raise ValueError('Selected synthetic CPU markers required')
    properties = (cpu.properties['reg'], cpu.properties['timebase-frequency'],
                  chosen.properties['dram-base'], chosen.properties['dram-size'])
    if tuple(map(len, properties)) != (4, 4, 8, 8):
        raise ValueError('Expected LE32 CPU/timebase and LE64 DRAM scalars')
    affinity, frequency = (struct.unpack('<I', item)[0] for item in properties[:2])
    base, size = (struct.unpack('<Q', item)[0] for item in properties[2:])
    if cpu.name != 'cpu@' + format(affinity, 'x'):
        raise ValueError('CPU name/affinity disagreement')
    return _values(affinity, frequency, base, size)
