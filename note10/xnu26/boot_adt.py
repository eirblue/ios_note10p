"""Bounded, canonical raw Apple Device Tree codec for loader preparation.

No firmware identities, MMIO values, CPU topology or GIC ownership are inferred.
This is not a Linux FDT-to-platform conversion or an IM4P encoder.
Placeholder properties are deliberately unsupported by this producer.
"""
from dataclasses import dataclass, field
import struct

MAX_BYTES = 16 * 1024 * 1024
MAX_NODES = 4096
MAX_DEPTH = 32
MAX_PROPS = 1024


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
