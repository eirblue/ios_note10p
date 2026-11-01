"""Private PC-only Linux FDT memory declarations; never a usable/owned RAM map."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import stat

import linux_cpu_adt as fdt

POLICY = 'linux-fdt-memory-declaration-inventory-v1'
PRIVATE_ROOT = fdt.PRIVATE_ROOT
MAX_MANIFEST = 8 * fdt.MAX_FDT
FLAGS = ('no-map', 'reusable', 'no-ship', 'hotpluggable', 'linux,cma-default', 'linux,dma-default')


def _hint(value):
    if value is None:
        return None
    return dict(bytes=len(value), raw_be_hex=value.hex())


def _qualifiers(properties):
    return dict(status=_hint(properties.get('status')),
                flags={name: _hint(properties[name]) for name in FLAGS if name in properties},
                effective_admission_known=False)


def _cells(properties, name):
    value = properties.get(name)
    if value not in (b'\0\0\0\1', b'\0\0\0\2'):
        raise ValueError('Explicit memory address/size cells 1 or 2 required')
    return int.from_bytes(value, 'big')


def _extent(address, size):
    if not 0 <= address < 1 << 64 or not 0 < size < 1 << 64 or address+size > 1 << 64:
        raise ValueError('Nonzero bounded u64 declaration extent required')
    return dict(start=address, size=size)


def _tuples(value, address_cells, size_cells):
    stride = 4 * (address_cells+size_cells)
    if value is None or not value or len(value) % stride:
        raise ValueError('Exact nonempty memory declaration tuple width required')
    return [_extent(int.from_bytes(value[offset:offset+4*address_cells], 'big'),
                    int.from_bytes(value[offset+4*address_cells:offset+stride], 'big'))
            for offset in range(0, len(value), stride)]


def _source(path, property_name):
    return dict(node_path='/'+'/'.join(path), property=property_name,
                provenance='historical-or-caller-pinned firmware declaration, not runtime ownership')


def inventory(raw, *, require_complete_placement=False):
    """One existing structural scan plus selected declaration semantics only."""
    if require_complete_placement:
        raise ValueError('Complete placement unsupported: unresolved declarations and live occupancy/ownership unknown')
    fields = fdt.memory_fields(raw)
    root = fields['root']
    ac, sc = _cells(root, '#address-cells'), _cells(root, '#size-cells')
    banks, usable, header, fixed, unresolved = [], [], [], [], []
    for node in fields['memory_nodes']:
        path, properties = node['path'], node['properties']
        qualifiers = _qualifiers(properties)
        for extent in _tuples(properties.get('reg'), ac, sc):
            banks.append(dict(extent, source=_source(path, 'reg'), qualifiers=qualifiers))
        if 'linux,usable-memory' in properties:
            for extent in _tuples(properties['linux,usable-memory'], ac, sc):
                usable.append(dict(extent, source=_source(path, 'linux,usable-memory'), qualifiers=qualifiers))
    if not banks:
        raise ValueError('Direct exact device_type memory declarations required')
    for index, (address, size) in enumerate(fields['header_reservations']):
        header.append(dict(_extent(address, size), source=dict(property='FDT header reserve map', entry=index)))
    reserved_root = fields['reserved_root']
    if reserved_root is not None:
        if (_cells(reserved_root, '#address-cells') != ac or _cells(reserved_root, '#size-cells') != sc or
                reserved_root.get('ranges') != b''):
            raise ValueError('Reserved root requires matching explicit cells and empty ranges')
    counts = dict(memory_nodes=len(fields['memory_nodes']), memory_banks=len(banks),
                  linux_usable_declarations=len(usable), header_reservations=len(header),
                  reserved_nodes=len(fields['reserved_nodes']), direct_fixed_nodes=0,
                  direct_fixed_ranges=0, nested_nodes=0, dynamic_nodes=0, container_nodes=0,
                  conditional_nodes=0, unresolved_records=0)
    for node in fields['reserved_nodes']:
        path, properties = node['path'], node['properties']
        qualifiers = _qualifiers(properties)
        reasons = []
        if len(path) != 2:
            # Never parse descendant reg using root cells or guess bus translation.
            reasons.append('unsupported-nested-address-space')
            counts['nested_nodes'] += 1
        elif 'reg' not in properties:
            if 'size' in properties:
                reasons.append('unresolved-dynamic-allocation')
                counts['dynamic_nodes'] += 1
            else:
                reasons.append('unsupported-container-without-reg-or-size')
                counts['container_nodes'] += 1
        else:
            extents = _tuples(properties['reg'], ac, sc)
            if 'no-ship' in properties:
                reasons.append('unresolved-config-conditional-no-ship')
            if properties.get('status', b'okay\0') not in (b'okay\0', b'ok\0'):
                reasons.append('unresolved-status-admission')
            if 'size' in properties:
                reasons.append('unresolved-reg-and-size-declaration')
            if reasons:
                counts['conditional_nodes'] += 1
            else:
                counts['direct_fixed_nodes'] += 1
                fixed.extend(dict(extent, source=_source(path, 'reg'), qualifiers=qualifiers) for extent in extents)
        if reasons:
            unresolved.append(dict(source=_source(path, 'reserved-memory declaration'), reasons=reasons,
                qualifiers=qualifiers,
                hints={name: _hint(properties[name]) for name in
                       ('reg', 'size', 'alignment', 'alloc-ranges', 'ranges', '#address-cells', '#size-cells')
                       if name in properties},
                physical_extent_interpreted=False))
    counts.update(direct_fixed_ranges=len(fixed), unresolved_records=len(unresolved))
    return dict(schema=1, policy=POLICY, root_cells=dict(address=ac, size=sc),
                input_shape_restriction='/cpus must exist; CPU identities are not interpreted',
                ram_declarations=banks, linux_usable_declarations=usable,
                header_reservations=header, direct_fixed_reservations=fixed,
                reserved_root_present=reserved_root is not None, unresolved=unresolved, counts=counts,
                private_output=True, placement_ready=False, memory_ownership=False,
                live_occupancy_known=False, handoff_ready=False, free_memory_computed=False,
                effective_linux_memory_map=False, xnu_executed=False,
                limitations=['Declarations only; no allocation or reservation success',
                             'Dynamic/nested/conditional records are not physical blocked extents',
                             'No bank union, subtraction, address selection or boot_args sizing',
                             'A historical FDT does not establish current live occupied ranges',
                             'No same-boot CPU/FDT join or complete Apple memory map'])


def build(input_path, input_sha256, output, *, require_complete_placement=False):
    source, destination = Path(input_path), Path(output).resolve()
    if destination == PRIVATE_ROOT or not destination.is_relative_to(PRIVATE_ROOT) or destination.exists():
        raise ValueError('Fresh output below repository note10/private required')
    if not source.resolve().is_relative_to(PRIVATE_ROOT):
        raise ValueError('Pinned input must remain private')
    if len(input_sha256) != 64 or any(c not in '0123456789abcdef' for c in input_sha256):
        raise ValueError('Explicit lowercase input SHA256 required')
    before = source.lstat()
    if not stat.S_ISREG(before.st_mode) or not 40 <= before.st_size <= fdt.MAX_FDT:
        raise ValueError('Private bounded ordinary input required')
    with source.open('rb') as stream:
        if fdt._file_identity(os.fstat(stream.fileno())) != fdt._file_identity(before):
            raise ValueError('Input identity changed before read')
        raw = stream.read(fdt.MAX_FDT+1)
        after = os.fstat(stream.fileno())
    if fdt._file_identity(before) != fdt._file_identity(after) or fdt._file_identity(source.lstat()) != fdt._file_identity(before):
        raise ValueError('Input changed during read')
    if hashlib.sha256(raw).hexdigest() != input_sha256:
        raise ValueError('Input SHA256 differs')
    manifest = inventory(raw, require_complete_placement=require_complete_placement)
    manifest.update(input_sha256=input_sha256, input_bytes=len(raw))
    payload = (json.dumps(manifest, indent=2, sort_keys=True)+'\n').encode('utf-8')
    if len(payload) > MAX_MANIFEST:
        raise ValueError('Memory declaration manifest budget')
    # All syntax/semantic rejection precedes fresh output creation.
    destination.mkdir(parents=False, exist_ok=False)
    temporary, target = destination/'.declarations.json.tmp', destination/'declarations.json'
    with temporary.open('xb') as stream:
        stream.write(payload); stream.flush(); os.fsync(stream.fileno())
    os.replace(temporary, target)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True)
    parser.add_argument('--input-sha256', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--require-complete-placement', action='store_true')
    args = parser.parse_args()
    manifest = build(args.input, args.input_sha256, args.output,
                     require_complete_placement=args.require_complete_placement)
    print(json.dumps(dict(policy=manifest['policy'], counts=manifest['counts'], private_output=True,
                          placement_ready=False, memory_ownership=False,
                          live_occupancy_known=False, handoff_ready=False)))


if __name__ == '__main__':
    main()
