"""PC-only FDT CPU descriptions to an INCOMPLETE canonical ADT fragment.

No CPU execution state, memory ownership or Apple platform compatibility is
inferred. Real input, its digest and all derived files must remain private.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import struct

from boot_adt import Node, encode

MAX_FDT = 2 * 1024 * 1024
MAX_CPUS = 32
MAX_DEPTH = 32
MAX_NODES = 4096
MAX_PROPS = 128
# Each FDT_PROP consumes a token, value length and name offset (12 bytes),
# even for an empty value. The input-size cap therefore bounds total scanning
# and duplicate-name bookkeeping without restricting unrelated wide nodes.
MAX_PROPERTY_TOKENS = MAX_FDT // 12
MAX_FRAGMENT = 16 * 1024
REFERENCE = {
    'tag': 'xnu-12377.121.6',
    'commit': 'ac9718fb1af618d5ce8678d0dc6e8a58f252216f',
    'target_kernel': 'xnu-12377.122.8',
    'exact_match': False,
    'exact_target_abi_claim': False,
}
POLICY = 'linux-fdt-cpu-affinity-description-v1'
PRIVATE_ROOT = Path(__file__).resolve().parents[1] / 'private'


def _name(raw, allow_empty=False):
    if (not raw and not allow_empty) or len(raw) > 255:
        raise ValueError('FDT name length')
    if any(c < 33 or c > 126 or c == 47 for c in raw):
        raise ValueError('FDT name characters')
    return raw.decode('ascii')


def _cpu_nodes(raw):
    """Validate one bounded FDT, retaining only /cpus and direct children."""
    if not isinstance(raw, bytes) or not 40 <= len(raw) <= MAX_FDT:
        raise ValueError('FDT size/type')
    magic, total, so, sto, ro, version, compatible, _, strings_size, size = struct.unpack_from('>10I', raw)
    if magic != 0xd00dfeed or total != len(raw) or version != 17 or compatible not in (16, 17):
        raise ValueError('FDT v17 header')
    if so % 4 or ro % 8 or size % 4 or not size:
        raise ValueError('FDT block alignment/size')
    blocks = [(so, so + size), (sto, sto + strings_size)]
    if any(a < 40 or b > total or a > b for a, b in blocks):
        raise ValueError('FDT block extent')
    if max(blocks[0][0], blocks[1][0]) < min(blocks[0][1], blocks[1][1]):
        raise ValueError('FDT overlapping blocks')
    if ro < 40 or ro + 16 > total:
        raise ValueError('FDT reserve map extent')
    rp = ro
    while True:
        if rp + 16 > total or (rp - ro) // 16 >= MAX_NODES:
            raise ValueError('FDT reserve map bound/terminator')
        if any(max(ro, a) < min(rp + 16, b) for a, b in blocks):
            raise ValueError('FDT reserve map overlaps data')
        address, length = struct.unpack_from('>QQ', raw, rp)
        rp += 16
        if address == length == 0:
            break
    cursor, end = so, so + size
    stack = []
    roots = nodes = property_tokens = 0
    cpus = None
    children = []
    while cursor < end:
        if cursor + 4 > end:
            raise ValueError('FDT truncated token')
        token = struct.unpack_from('>I', raw, cursor)[0]
        cursor += 4
        if token == 1:
            stop = raw.find(b'\0', cursor, end)
            if stop < 0:
                raise ValueError('FDT unterminated node')
            name = _name(raw[cursor:stop], allow_empty=not stack)
            cursor = (stop + 4) & ~3
            if cursor > end or len(stack) > MAX_DEPTH:
                raise ValueError('FDT node depth/extent')
            if stack:
                parent = stack[-1]
                if not name or name in parent['children']:
                    raise ValueError('FDT duplicate/empty child')
                parent['children'].add(name)
                parent['has_child'] = True
                path = parent['path'] + (name,)
            else:
                roots += 1
                if roots != 1 or name:
                    raise ValueError('FDT single empty root required')
                path = ()
            nodes += 1
            if nodes > MAX_NODES:
                raise ValueError('FDT node count')
            entry = dict(path=path, children=set(), properties=set(), has_child=False, values={})
            stack.append(entry)
            if path == ('cpus',):
                cpus = entry['values']
            elif len(path) == 2 and path[0] == 'cpus':
                children.append(entry['values'])
        elif token == 2:
            if not stack:
                raise ValueError('FDT unbalanced end-node')
            stack.pop()
        elif token == 3:
            if not stack or stack[-1]['has_child'] or cursor + 8 > end:
                raise ValueError('FDT property placement/extent')
            property_tokens += 1
            if property_tokens > MAX_PROPERTY_TOKENS:
                raise ValueError('FDT total property token budget')
            length, nameoff = struct.unpack_from('>II', raw, cursor)
            cursor += 8
            if nameoff >= strings_size or cursor + length > end:
                raise ValueError('FDT property extent/name offset')
            stop = raw.find(b'\0', sto + nameoff, sto + strings_size)
            if stop < 0:
                raise ValueError('FDT unterminated property name')
            name = _name(raw[sto + nameoff:stop])
            entry = stack[-1]
            if name in entry['properties']:
                raise ValueError('FDT duplicate property name')
            retain = entry['path'] == ('cpus',) or (len(entry['path']) == 2 and entry['path'][0] == 'cpus')
            if retain and len(entry['properties']) >= MAX_PROPS:
                raise ValueError('FDT CPU property count')
            entry['properties'].add(name)
            if retain:
                entry['values'][name] = raw[cursor:cursor + length]
            cursor = (cursor + length + 3) & ~3
            if cursor > end:
                raise ValueError('FDT property padding extent')
        elif token == 4:
            pass
        elif token == 9:
            if stack or roots != 1 or cursor != end:
                raise ValueError('FDT end/root/trailing structure')
            if cpus is None:
                raise ValueError('FDT /cpus missing')
            return cpus, children
        else:
            raise ValueError('FDT unknown token')
    raise ValueError('FDT end token missing')


def translate(raw, *, require_full_handoff=False):
    """Return fragment bytes and nonidentifying policy metadata; no file writes."""
    if require_full_handoff:
        raise ValueError('Full handoff unsupported: missing CPU execution-state/platform provenance and exact target contract')
    cpus, children = _cpu_nodes(raw)
    address = cpus.get('#address-cells')
    if address not in (b'\0\0\0\1', b'\0\0\0\2') or cpus.get('#size-cells') != bytes(4):
        raise ValueError('Explicit CPU address-cells 1/2 and size-cells 0 required')
    width = int.from_bytes(address, 'big') * 4
    affinities = set()
    for child in children:
        if child.get('device_type') != b'cpu\0':
            continue
        reg = child.get('reg')
        if not isinstance(reg, bytes) or len(reg) != width:
            raise ValueError('CPU reg width differs from address-cells')
        affinity = int.from_bytes(reg, 'big')
        if affinity > 0xffffffff or affinity in affinities:
            raise ValueError('CPU affinity unrepresentable or duplicate')
        affinities.add(affinity)
        if len(affinities) > MAX_CPUS:
            raise ValueError('CPU count exceeds 32')
    if not affinities:
        raise ValueError('No explicit CPU descriptions')
    descriptions = [Node(f'cpu@{value:x}', {'device_type': b'cpu\0', 'reg': struct.pack('<I', value)})
                    for value in sorted(affinities)]
    fragment = encode(Node('device-tree', children=[Node('cpus', children=descriptions)]))
    if len(fragment) > MAX_FRAGMENT:
        raise ValueError('ADT fragment size')
    metadata = dict(policy=POLICY, cpu_count=len(descriptions), reference=dict(REFERENCE),
                    complete_boot_tree=False, handoff_ready=False, cpu_execution_state_known=False,
                    memory_ownership=False, xnu_executed=False,
                    missing=['CPU execution-state provenance', 'platform contract', 'exact target consumer contract'])
    return fragment, metadata


def _file_identity(st):
    return st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns, st.st_nlink


def build(input_path, input_sha256, output, *, require_full_handoff=False):
    """Build private metadata from one explicitly pinned saved input, once."""
    source, destination = Path(input_path), Path(output).resolve()
    if destination == PRIVATE_ROOT or not destination.is_relative_to(PRIVATE_ROOT):
        raise ValueError('Output must resolve below repository note10/private')
    if len(input_sha256) != 64 or any(c not in '0123456789abcdef' for c in input_sha256):
        raise ValueError('Explicit lowercase input SHA256 required')
    before = source.lstat()
    if not stat.S_ISREG(before.st_mode) or not 40 <= before.st_size <= MAX_FDT:
        raise ValueError('Input must be a bounded ordinary file')
    with source.open('rb') as stream:
        if _file_identity(os.fstat(stream.fileno())) != _file_identity(before):
            raise ValueError('Input identity changed before read')
        raw = stream.read(MAX_FDT + 1)
        after = os.fstat(stream.fileno())
    if _file_identity(before) != _file_identity(after) or _file_identity(source.lstat()) != _file_identity(before):
        raise ValueError('Input changed during read')
    if hashlib.sha256(raw).hexdigest() != input_sha256:
        raise ValueError('Input SHA256 differs')
    fragment, metadata = translate(raw, require_full_handoff=require_full_handoff)
    metadata.update(input_sha256=input_sha256, input_bytes=len(raw), fragment_bytes=len(fragment),
                    fragment_sha256=hashlib.sha256(fragment).hexdigest(), private_output=True)
    # All semantic rejection precedes output creation. Fresh directory only;
    # publish complete files by rename inside this exclusively created directory.
    destination.mkdir(parents=False, exist_ok=False)
    for name, payload in [('cpu-description.adt', fragment),
                          ('manifest.json', (json.dumps(metadata, indent=2) + '\n').encode('utf-8'))]:
        temporary = destination / ('.' + name + '.tmp')
        with temporary.open('xb') as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, destination / name)
    return metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True)
    parser.add_argument('--input-sha256', required=True)
    parser.add_argument('--output', required=True, help='Fresh PRIVATE directory with an existing parent')
    parser.add_argument('--require-full-handoff', action='store_true', help='Always rejects: incomplete contract')
    args = parser.parse_args()
    metadata = build(args.input, args.input_sha256, args.output, require_full_handoff=args.require_full_handoff)
    # Do not print live input digest, path, affinity values or fragment bytes.
    print(json.dumps({key: metadata[key] for key in ('policy', 'cpu_count', 'handoff_ready')}))


if __name__ == '__main__':
    main()
