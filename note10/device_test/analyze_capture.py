"""Analyze recovery observations; never infer a safe XNU load address."""
import argparse
import gzip
import io
import json
from pathlib import Path, PurePosixPath
import re
import struct
import sys
import tarfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from inspect_firmware import fdt_nodes

LIMIT = 32 * 1024 * 1024


def read(path, limit=LIMIT):
    if not path.is_file():return b''
    if path.is_symlink() or path.stat().st_size > limit:raise ValueError('Unsafe capture file: ' + path.name)
    return path.read_bytes()


def tree_from_tar(raw):
    nodes = {'/': {}}; total = 0
    with tarfile.open(fileobj=io.BytesIO(raw)) as archive:
        for entry in archive:
            p = PurePosixPath(entry.name)
            if p.is_absolute() or '..' in p.parts or entry.issym() or entry.islnk():
                raise ValueError('Unsafe device-tree archive path/link')
            parts = tuple(s for s in p.parts if s != '.')
            if entry.isdir():nodes.setdefault('/' + '/'.join(parts), {});continue
            if not entry.isfile() or not parts:raise ValueError('Unsupported device-tree archive member')
            total += entry.size
            if entry.size > 4*1024*1024 or total > LIMIT:raise ValueError('Device-tree archive too large')
            node = '/' + '/'.join(parts[:-1]); key = parts[-1]
            props = nodes.setdefault(node, {})
            if key in props:raise ValueError('Duplicate device-tree property')
            props[key] = archive.extractfile(entry).read()
    return nodes


def cell_count(props, key, default):
    raw = props.get(key)
    if raw is None:return default
    if len(raw) != 4:raise ValueError('Invalid device-tree cell count')
    result = struct.unpack('>I', raw)[0]
    if result not in (1, 2):raise ValueError('Unsupported memory address/size cell count')
    return result


def ranges(raw, address_cells, size_cells):
    width = 4 * (address_cells + size_cells)
    if not raw or len(raw) % width:raise ValueError('Invalid memory reg tuple width')
    result = []
    for offset in range(0, len(raw), width):
        split = offset + address_cells * 4
        base = int.from_bytes(raw[offset:split], 'big')
        size = int.from_bytes(raw[split:offset+width], 'big')
        if not size or base + size > 1 << 64:raise ValueError('Invalid memory extent')
        result.append({'start': hex(base), 'size': hex(size), 'end_exclusive': hex(base+size)})
    return result


def mem_reservations(raw):
    if not raw:return []
    total, offset = struct.unpack_from('>I', raw, 4)[0], struct.unpack_from('>I', raw, 16)[0]
    result = []
    if offset % 8 or offset < 40:raise ValueError('Invalid FDT memory reservation offset')
    while offset + 16 <= total:
        base, size = struct.unpack_from('>QQ', raw, offset); offset += 16
        if base == size == 0:return result
        if not size or base + size > 1 << 64:raise ValueError('Invalid FDT memory reservation')
        result.append({'start': hex(base), 'size': hex(size), 'end_exclusive': hex(base+size)})
    raise ValueError('Unterminated FDT memory reservations')


def strings(raw):return raw.rstrip(b'\0').decode(errors='replace').split('\0')


def analyze(directory):
    if read(directory/'COMPLETE', 128).strip() != b'NOTE10_PROBE_COMPLETE':
        raise ValueError('Incomplete recovery capture')
    properties = dict(line.split('=', 1) for line in read(directory/'properties.txt', 65536).decode(errors='replace').splitlines() if '=' in line)
    blob = read(directory/'live.dtb', 16*1024*1024)
    nodes = {}; tree_source = None; reservations = []
    if blob:
        nodes = fdt_nodes(blob); reservations = mem_reservations(blob); tree_source = 'live.dtb'
    else:
        packed = read(directory/'live-tree.tar')
        if packed:nodes = tree_from_tar(packed); tree_source = 'live-tree.tar'
    memory = []; reserved = []; dynamic = []
    for path, props in nodes.items():
        if props.get('status', b'okay').rstrip(b'\0') in (b'disabled', b'fail'):continue
        is_memory = props.get('device_type', b'').rstrip(b'\0') == b'memory' or path.rsplit('/',1)[-1].startswith('memory@')
        is_reserved = path.startswith('/reserved-memory/') and path.count('/') == 2
        if not is_memory and not is_reserved:continue
        parent = path.rsplit('/', 1)[0] or '/'
        cells = nodes.get(parent, {})
        ac = cell_count(cells, '#address-cells', 2); sc = cell_count(cells, '#size-cells', 1)
        if 'reg' in props:
            entry = {'path': path, 'ranges': ranges(props['reg'], ac, sc)}
            if is_reserved:entry['no_map'] = 'no-map' in props
            (memory if is_memory else reserved).append(entry)
        elif is_reserved:dynamic.append(path)
    relevant = {}
    for path, props in nodes.items():
        comp = strings(props.get('compatible', b''))
        if path == '/psci' or any(any(s in c for s in ('gic','armv8-timer','psci','ramoops')) for c in comp):
            relevant[path] = {k: (strings(v) if k in ('compatible','method','status') else v.hex())
                              for k,v in props.items() if k in ('compatible','method','status','reg','interrupts','clock-frequency')}
    config = {}
    compressed = read(directory/'config.gz', 4*1024*1024)
    if compressed:
        with gzip.GzipFile(fileobj=io.BytesIO(compressed)) as stream:decoded = stream.read(8*1024*1024+1)
        if len(decoded) > 8*1024*1024:raise ValueError('Expanded kernel config exceeds limit')
        for line in decoded.decode(errors='replace').splitlines():
            assignment = re.fullmatch(r'(CONFIG_[A-Z0-9_]+)=(.*)', line)
            disabled = re.fullmatch(r'# (CONFIG_[A-Z0-9_]+) is not set', line)
            if not assignment and not disabled:continue
            key, value = assignment.groups() if assignment else (disabled.group(1), 'n')
            if key in config and config[key] != value:
                raise ValueError('Conflicting kernel config values: ' + key)
            config[key] = value
    iomem = read(directory/'iomem.txt', 4*1024*1024).decode(errors='replace')
    observed_iomem = [{'start':hex(int(a,16)), 'end_inclusive':hex(int(b,16)), 'name':label.strip()}
                      for a,b,label in re.findall(r'^\s*([0-9a-fA-F]+)-([0-9a-fA-F]+)\s*:\s*(.*)$', iomem, re.M)]
    nonzero = any(int(r['start'],16) or int(r['end_inclusive'],16) for r in observed_iomem)
    return {'schema': 1, 'phase': 'linux-recovery-observation', 'properties': properties,
            'live_tree_observed': bool(nodes), 'tree_source': tree_source,
            'memory_nodes': memory, 'reserved_memory_nodes': reserved,
            'dynamic_reserved_nodes_without_reg': dynamic, 'fdt_memreserve': reservations,
            'fdt_memreserve_observable': tree_source == 'live.dtb',
            'platform_nodes': relevant, 'iomem_addresses_visible': nonzero, 'iomem': observed_iomem,
            'kernel_config': {k:config.get(k,'not observed') for k in
                ('CONFIG_KEXEC','CONFIG_KEXEC_FILE','CONFIG_IKCONFIG_PROC','CONFIG_PSTORE','CONFIG_PSTORE_RAM',
                 'CONFIG_ARM64_4K_PAGES','CONFIG_ARM64_16K_PAGES','CONFIG_ARM64_64K_PAGES')},
            'boot_contract_verified': False, 'safe_xnu_load_address_selected': None,
            'privileged_entry_registers_measured': False, 'xnu_executed': False,
            'limitations': ['Recovery Linux view does not establish bootloader entry EL/MMU/cache state.',
                'Recovery kernel configuration does not prove all CPU page granule capabilities.',
                'Dynamic reservations and device ownership require additional validation.',
                'Kexec configuration, if present, does not implement or validate an XNU handoff.']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__);parser.add_argument('directory', type=Path)
    args = parser.parse_args(); print(json.dumps(analyze(args.directory), indent=2))
