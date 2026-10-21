#!/usr/bin/env python3
"""Inspect stock boot images and DT tables; write only local analysis outputs."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'host-tools/python-packages'))


def need(condition, message):
    if not condition:
        raise ValueError(message)


def cstring(data):
    return data.split(b'\0', 1)[0].decode('utf-8', errors='replace')


def fdt_nodes(data):
    need(len(data) >= 40, 'Truncated FDT header')
    magic, total, off, strings, _, version, _, _, strings_size, struct_size = struct.unpack_from('>10I', data)
    need(magic == 0xd00dfeed and 17 <= version, 'Unsupported FDT header')
    need(total <= len(data) and off + struct_size <= total and strings + strings_size <= total, 'FDT bounds')
    end = off + struct_size
    names = data[strings:strings + strings_size]
    stack, nodes = [], {}
    while off + 4 <= end:
        token = struct.unpack_from('>I', data, off)[0]
        off += 4
        if token == 1:
            stop = data.find(b'\0', off, end)
            need(stop >= 0, 'Unterminated FDT node')
            name = data[off:stop].decode('utf-8')
            stack.append(name)
            path = '/' + '/'.join(stack[1:])
            need(path not in nodes, 'Duplicate FDT path')
            nodes[path] = {}
            off = (stop + 4) & ~3
        elif token == 2:
            need(bool(stack), 'Unbalanced FDT nodes')
            stack.pop()
        elif token == 3:
            need(off + 8 <= end and bool(stack), 'Truncated FDT property')
            length, nameoff = struct.unpack_from('>2I', data, off)
            off += 8
            stop = names.find(b'\0', nameoff)
            need(nameoff < len(names) and stop >= 0 and off + length <= end, 'FDT property bounds')
            key = names[nameoff:stop].decode('utf-8')
            nodes['/' + '/'.join(stack[1:])][key] = data[off:off + length]
            off = (off + length + 3) & ~3
        elif token == 4:
            continue
        elif token == 9:
            need(not stack, 'Unclosed FDT node')
            return nodes
        else:
            raise ValueError(f'Unknown FDT token {token}')
    raise ValueError('Missing FDT END')


def value(data):
    if not data:
        return True
    # A zero integer is not an empty string. Preserve numeric cells by default.
    if 32 <= data[0] <= 126 and data.endswith(b'\0') and b'\0\0' not in data and all(b == 0 or 32 <= b <= 126 for b in data):
        return data.rstrip(b'\0').decode('ascii').split('\0')
    if len(data) % 4 == 0:
        return [f'0x{x:08x}' for x in struct.unpack(f'>{len(data)//4}I', data)]
    return {'hex': data.hex()}


def boot_header(raw):
    need(len(raw) >= 1660 and raw[:8] == b'ANDROID!', 'Missing legacy Android boot header')
    fields = ('kernel_size', 'kernel_addr', 'ramdisk_size', 'ramdisk_addr',
              'second_size', 'second_addr', 'tags_addr', 'page_size', 'header_version', 'os_version_encoded')
    h = dict(zip(fields, struct.unpack_from('<10I', raw, 8)))
    need(h['header_version'] in (0, 1, 2), 'Unsupported boot version')
    page = h['page_size']
    need(page >= 2048 and page & (page - 1) == 0, 'Invalid boot page size')
    align = lambda n: (n + page - 1) // page * page
    h['name'] = cstring(raw[48:64])
    h['cmdline'] = cstring(raw[64:576]) + cstring(raw[608:1632])
    encoded = h['os_version_encoded']
    h['os_version'] = '.'.join(str((encoded >> shift) & 127) for shift in (25, 18, 11))
    h['security_patch_month'] = f'{2000 + ((encoded >> 4) & 127):04d}-{encoded & 15:02d}'
    h['kernel_file_offset'] = page
    h['ramdisk_file_offset'] = page + align(h['kernel_size'])
    h['second_file_offset'] = h['ramdisk_file_offset'] + align(h['ramdisk_size'])
    for part in ('kernel', 'ramdisk', 'second'):
        need(h[f'{part}_file_offset'] + h[f'{part}_size'] <= len(raw), f'{part} exceeds image')
    if h['header_version'] >= 1:
        h['recovery_dtbo_size'], h['recovery_dtbo_offset'], h['header_size'] = struct.unpack_from('<IQI', raw, 1632)
        need(h['header_size'] <= page, 'Header exceeds page')
        need(h['recovery_dtbo_offset'] + h['recovery_dtbo_size'] <= len(raw), 'Recovery DTBO exceeds image')
    if h['header_version'] == 2:
        h['dtb_size'], h['dtb_addr'] = struct.unpack_from('<IQ', raw, 1648)
    kernel = raw[page:page + h['kernel_size']]
    h['kernel_sha256'] = hashlib.sha256(kernel).hexdigest()
    h['kernel_first_64_bytes'] = kernel[:64].hex()
    h['kernel_arm64_image_magic'] = kernel[56:60] == b'ARM\x64'
    if h['kernel_arm64_image_magic']:
        h['arm64_text_offset'], h['arm64_image_size'], h['arm64_flags'] = struct.unpack_from('<3Q', kernel, 8)
    h['declared_load_addresses_hex'] = {k: hex(v) for k, v in h.items() if k.endswith('_addr')}
    return h


def dt_table(raw, output, stem):
    need(len(raw) >= 32, 'Short DT table')
    vals = struct.unpack_from('>8I', raw)
    keys = ('magic', 'total_size', 'header_size', 'entry_size', 'entry_count', 'entries_offset', 'page_size', 'version')
    h = dict(zip(keys, vals))
    need(h['magic'] == 0xd7b7ab1e and h['version'] == 0, 'Unsupported DT table')
    need(32 <= h['header_size'] <= h['total_size'] <= len(raw) and h['entry_size'] >= 32, 'DT table bounds')
    need(h['entries_offset'] >= h['header_size'] and h['entries_offset'] + h['entry_count'] * h['entry_size'] <= h['total_size'], 'DT entry bounds')
    entries = []
    for i in range(h['entry_count']):
        size, offset, ident, rev, *custom = struct.unpack_from('>8I', raw, h['entries_offset'] + i * h['entry_size'])
        need(offset >= h['entries_offset'] + h['entry_count'] * h['entry_size'] and offset + size <= h['total_size'], 'DT blob bounds')
        blob = raw[offset:offset + size]
        nodes = fdt_nodes(blob)
        decoded = {path: {key: value(v) for key, v in props.items()} for path, props in nodes.items()}
        file = f'{stem}-{i:02d}'
        (output / f'{file}.dtb').write_bytes(blob)
        (output / f'{file}.json').write_text(json.dumps(decoded, indent=2), encoding='utf-8')
        interesting = {}
        for path, props in decoded.items():
            # Keep the full tree separately; this selection is a navigation aid.
            terms = ('memory', 'reserved', 'timer', 'gic', 'interrupt-controller', 'ufs', 'watchdog', 'framebuffer', 'display', 'decon', 'dsim', 'touch', 'cpu@', 'psci', 'chosen')
            if path == '/' or any(term in path.lower() for term in terms):
                interesting[path] = props
        entries.append({'index': i, 'size': size, 'offset': offset, 'id': ident, 'rev': rev, 'custom': custom,
                        'sha256': hashlib.sha256(blob).hexdigest(), 'root': decoded.get('/'), 'node_count': len(nodes),
                        'selected_nodes': interesting})
    h['entries'] = entries
    return h


def main():
    import lz4.frame
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('input', type=Path, help='Directory containing extracted AP *.img.lz4 files')
    p.add_argument('--out', type=Path, default=ROOT / 'note10/private/firmware')
    args = p.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    report = {'input_directory': args.input.name, 'observations_only': True, 'images': {}}
    for stem in ('boot', 'recovery', 'dt', 'dtbo', 'vbmeta'):
        file = args.input / f'{stem}.img.lz4'
        need(file.stat().st_size <= 128 * 1024 * 1024, 'Compressed image too large')
        with lz4.frame.open(file, 'rb') as stream:
            raw = stream.read(128 * 1024 * 1024 + 1)
        need(len(raw) <= 128 * 1024 * 1024, 'Decompressed image too large')
        info = {'source': file.name, 'compressed_size': file.stat().st_size,
                'compressed_sha256': hashlib.sha256(file.read_bytes()).hexdigest(),
                'size': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
        if stem in ('boot', 'recovery'):
            info['header'] = boot_header(raw)
        elif stem in ('dt', 'dtbo'):
            info['table'] = dt_table(raw, args.out, stem)
        else:
            need(raw[:4] == b'AVB0', 'Missing AVB0 magic')
            info['avb_header_magic'] = 'AVB0'
        report['images'][stem] = info
        print(f'{stem}: {len(raw):,} bytes decoded')
    target = args.out / 'report.json'
    target.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(f'Observations saved: {target}')


if __name__ == '__main__':
    main()
