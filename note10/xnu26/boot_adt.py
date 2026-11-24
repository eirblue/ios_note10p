"""Bounded, canonical raw Apple Device Tree codec for loader preparation.

No firmware identities, MMIO values, CPU topology or GIC ownership are inferred.
This is not a Linux FDT-to-platform conversion or an IM4P encoder.
Placeholder properties are deliberately unsupported by this producer.
"""
from dataclasses import dataclass, field, replace
import struct

MAX_BYTES = 16 * 1024 * 1024
MAX_NODES = 4096
MAX_DEPTH = 32
MAX_PROPS = 1024
RAMDISK_MAX_BYTES = 0xfffff000


@dataclass
class Node:
    name: str
    properties: dict = field(default_factory=dict)
    children: list = field(default_factory=list)


def text(value, limit):
    if not isinstance(value, str) or not value or '\0' in value or '/' in value:
        raise ValueError('Invalid ADT name')
    raw = value.encode('ascii')
    if len(raw) > limit: raise ValueError('ADT name exceeds format limit')
    return raw


def encode(root):
    output = bytearray(); seen = set()
    def visit(node, depth):
        if depth > MAX_DEPTH or len(seen) >= MAX_NODES or id(node) in seen:
            raise ValueError('ADT cycle, shared node or tree limit')
        seen.add(id(node))
        name = text(node.name, 63) + b'\0'
        if 'name' in node.properties or len(node.properties) + 1 > MAX_PROPS:
            raise ValueError('Duplicate name property or property limit')
        names = [child.name for child in node.children]
        if len(names) != len(set(names)): raise ValueError('Duplicate ADT child name')
        output.extend(struct.pack('<II', len(node.properties) + 1, len(node.children)))
        for key, value in [('name', name), *node.properties.items()]:
            key_raw = text(key, 31)
            if not isinstance(value, bytes) or len(value) > MAX_BYTES:
                raise ValueError('Invalid ADT property bytes')
            if len(output) + 36 + ((len(value) + 3) & ~3) > MAX_BYTES:
                raise ValueError('ADT byte limit exceeded')
            output.extend(key_raw.ljust(32, b'\0') + struct.pack('<I', len(value)))
            output.extend(value + bytes(-len(value) & 3))
        for child in node.children: visit(child, depth + 1)
    visit(root, 0)
    return bytes(output)


def decode(raw):
    if not isinstance(raw, bytes) or len(raw) > MAX_BYTES:
        raise ValueError('Invalid ADT input size/type')
    cursor = 0; nodes = 0
    def take(size):
        nonlocal cursor
        if cursor + size > len(raw): raise ValueError('Truncated ADT')
        result = raw[cursor:cursor + size]; cursor += size
        return result
    def visit(depth):
        nonlocal nodes
        nodes += 1
        if depth > MAX_DEPTH or nodes > MAX_NODES: raise ValueError('ADT tree limit')
        props, children = struct.unpack('<II', take(8))
        if not 1 <= props <= MAX_PROPS or children > MAX_NODES:
            raise ValueError('ADT count limit')
        values = {}
        for _ in range(props):
            key_raw = take(32); key, separator, tail = key_raw.partition(b'\0')
            if not separator or any(tail): raise ValueError('Noncanonical ADT property name')
            key = key.decode('ascii'); text(key, 31)
            if key in values: raise ValueError('Duplicate ADT property')
            size = struct.unpack('<I', take(4))[0]
            if size > MAX_BYTES: raise ValueError('Unsupported property flag or extent')
            values[key] = take(size)
            if any(take(-size & 3)): raise ValueError('Nonzero ADT padding')
        name = values.pop('name', b'')
        if not name.endswith(b'\0') or b'\0' in name[:-1]: raise ValueError('Missing or invalid node name')
        name = name[:-1].decode('ascii'); text(name, 63)
        result = Node(name, values, [visit(depth + 1) for _ in range(children)])
        names = [child.name for child in result.children]
        if len(names) != len(set(names)): raise ValueError('Duplicate ADT child')
        return result
    result = visit(0)
    if cursor != len(raw): raise ValueError('Trailing ADT bytes')
    return result


def encode_ramdisk_adt(root, *, mapped_ram, backing, physical_base, size):
    """Encode a synthetic RAMDisk declaration using caller-supplied ranges.

    The backing region follows the selected 16 KiB placement contract. The
    property stores byte values aligned to the consumer's 4 KiB units.
    """
    from boot_contract import PAGE, Region

    if not isinstance(root, Node) or not all(isinstance(r, Region) for r in (mapped_ram, backing)):
        raise ValueError('ADT root and explicit mapped RAM/backing regions required')
    disk = Region(physical_base, size)
    unit = 1 << 12
    # memdev reconstructs bytes with the unwidened uint32_t mdSize << 12.
    if not disk.start or disk.start % unit or disk.size % unit or disk.size > RAMDISK_MAX_BYTES:
        raise ValueError('RAMDisk must fit the aligned 32-bit consumer byte extent')
    if backing.start % PAGE or backing.size % PAGE:
        raise ValueError('RAMDisk backing must meet the selected 16 KiB alignment')
    if not mapped_ram.contains(backing) or not backing.contains(disk):
        raise ValueError('RAMDisk must fit its backing inside mapped RAM')

    chosen_nodes = [child for child in root.children if child.name == 'chosen']
    if len(chosen_nodes) != 1:
        raise ValueError('Expected one existing /chosen node')
    chosen = chosen_nodes[0]
    maps = [child for child in chosen.children if child.name == 'memory-map']
    if len(maps) > 1 or (maps and 'RAMDisk' in maps[0].properties):
        raise ValueError('Duplicate memory-map or RAMDisk declaration')

    value = struct.pack('<QQ', disk.start, disk.size)
    if maps:
        current = maps[0]
        memory_map = replace(current, properties=dict(current.properties, RAMDisk=value))
        children = [memory_map if child is current else child for child in chosen.children]
    else:
        children = [*chosen.children, Node('memory-map', {'RAMDisk': value})]
    updated = replace(chosen, children=children)
    return encode(replace(root, children=[updated if child is chosen else child for child in root.children]))


# v342 kernel handoff (0023 n10_ufs, 0024 n10_wdt, 0025 static trust caches). The UFS values are the reviewed
# constants n10_ufs.c compares against (pinned Samsung exynos9820 DT/driver); the caller still supplies them so a
# mismatch fails here, on the host, before any image is produced.
V342_UFS = dict(hci_base=0x13d60000, hci_size=0x200, nexus_off=0x1140, prdt_entry_size=128, prdt_length_bias=16)
V342_WDT_SIZE_RANGE = (0xc, 0x4000)


def encode_v342_handoff_adt(root, *, mapped_ram, ufs, partition_lba, wdt_reg, armed_wtdat, trust_cache):
    """Add /chosen/note10-ufs, /chosen/note10-wdt and the /chosen/memory-map TrustCache range."""
    from boot_contract import Region

    if not isinstance(root, Node) or not all(isinstance(r, Region) for r in (mapped_ram, trust_cache)):
        raise ValueError('ADT root and explicit mapped RAM/trust cache regions required')
    if ufs != V342_UFS:
        raise ValueError('UFS handoff must equal the reviewed n10_ufs constants')
    first, last = partition_lba
    if not (0 < first <= last <= 0xffffffff):
        raise ValueError('userdata 4 KiB LBA range required')
    wdt_base, wdt_size = wdt_reg
    if not wdt_base or wdt_base & 0xfff or not V342_WDT_SIZE_RANGE[0] <= wdt_size <= V342_WDT_SIZE_RANGE[1]:
        raise ValueError('page-aligned WDT base and one-page register size required')
    if not 0 < armed_wtdat <= 0xffff:
        raise ValueError('16-bit armed WTDAT required')
    if not trust_cache.start or trust_cache.size < 16 or not mapped_ram.contains(trust_cache):
        raise ValueError('TrustCache segment must be inside mapped RAM')

    chosen_nodes = [child for child in root.children if child.name == 'chosen']
    if len(chosen_nodes) != 1:
        raise ValueError('Expected one existing /chosen node')
    chosen = chosen_nodes[0]
    if any(child.name in ('note10-ufs', 'note10-wdt') for child in chosen.children):
        raise ValueError('Duplicate v342 handoff node')
    maps = [child for child in chosen.children if child.name == 'memory-map']
    if len(maps) != 1 or 'TrustCache' in maps[0].properties:
        raise ValueError('Expected one memory-map without TrustCache')
    ufs_node = Node('note10-ufs', {
        'hci-reg': struct.pack('<QQ', ufs['hci_base'], ufs['hci_size']),
        'nexus-reg': struct.pack('<Q', ufs['hci_base'] + ufs['nexus_off']),
        'prdt-entry-size': struct.pack('<I', ufs['prdt_entry_size']),
        'prdt-length-bias': struct.pack('<I', ufs['prdt_length_bias']),
        'partition-lba': struct.pack('<QQ', first, last)})
    wdt_node = Node('note10-wdt', {'reg': struct.pack('<QQ', wdt_base, wdt_size),
                                   'armed-wtdat': struct.pack('<I', armed_wtdat)})
    memory_map = replace(maps[0], properties=dict(maps[0].properties,
                         TrustCache=struct.pack('<QQ', trust_cache.start, trust_cache.size)))
    children = [memory_map if child is maps[0] else child for child in chosen.children] + [ufs_node, wdt_node]
    updated = replace(chosen, children=children)
    return encode(replace(root, children=[updated if child is chosen else child for child in root.children]))
