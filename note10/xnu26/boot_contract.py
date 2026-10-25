"""PC-side ARM64 boot arguments and explicit synthetic placement validation.

This module does not reserve physical RAM, convert Linux DT, perform a CPU
handoff, write partitions, or authorize using a plan on hardware.
"""
from dataclasses import dataclass
import struct

SIZE = 1152
OFFSETS = dict(Revision=0, Version=2, virtBase=8, physBase=16, memSize=24,
               topOfKernelData=32, Video=40, machineType=88, deviceTreeP=96,
               deviceTreeLength=104, CommandLine=108, bootFlags=1136,
               memSizeActual=1144)
LIMIT = 1 << 64
PAGE = 0x4000
BLOCK = 0x2000000


def uint(value, bits=64):
    if type(value) is not int or not 0 <= value < 1 << bits:
        raise ValueError('Expected unsigned integer of width ' + str(bits))
    return value


@dataclass(frozen=True)
class Region:
    start: int
    size: int

    def __post_init__(self):
        uint(self.start); uint(self.size)
        if not self.size or self.start + self.size > LIMIT:
            raise ValueError('Empty or overflowing memory region')

    @property
    def end(self):
        return self.start + self.size

    def contains(self, other):
        return self.start <= other.start and other.end <= self.end

    def overlaps(self, other):
        return self.start < other.end and other.start < self.end


def encode_boot_args(*, virtual_base, physical_base, memory_size, top_of_kernel,
                     device_tree_pointer=0, device_tree_length=0, command_line='',
                     memory_size_actual=None, boot_flags=0, machine_type=0,
                     video=(0, 0, 0, 0, 0, 0)):
    """Encode revision 2/version 2, with deterministic zero ABI padding.

    device_tree_pointer is the virtual address consumed by PE_init_platform;
    this routine only serializes it. Placement must be validated separately.
    Zero DT is permitted solely for entry-boundary tests, not a complete boot.
    """
    memory = Region(physical_base, memory_size)
    uint(virtual_base); uint(top_of_kernel)
    if any(value % PAGE for value in (physical_base, virtual_base, memory_size, top_of_kernel)):
        raise ValueError('Boot memory parameters must meet compiled 16K alignment')
    if (virtual_base - physical_base) % BLOCK:
        raise ValueError('Virtual/physical bases must have matching L2 block offsets')
    if virtual_base + memory_size > LIMIT or not memory.start < top_of_kernel <= memory.end:
        raise ValueError('Invalid virtual memory extent or topOfKernelData')
    uint(device_tree_pointer); uint(device_tree_length, 32)
    if bool(device_tree_pointer) != bool(device_tree_length):
        raise ValueError('DT pointer and length must both be present or absent')
    if device_tree_pointer + device_tree_length > LIMIT:
        raise ValueError('Device tree pointer extent overflow')
    actual = memory_size if memory_size_actual is None else uint(memory_size_actual)
    if actual < memory_size:
        raise ValueError('Actual memory is smaller than described memory')
    if not isinstance(command_line, str) or '\0' in command_line:
        raise ValueError('Command line must be text without embedded NUL')
    line = command_line.encode('utf-8')
    if len(line) >= 1024:
        raise ValueError('Command line exceeds 1023 bytes')
    if len(video) != 6:
        raise ValueError('Expected six Boot_Video fields')
    for field in video: uint(field)
    raw = bytearray(SIZE)
    struct.pack_into('<HH', raw, 0, 2, 2)
    struct.pack_into('<4Q', raw, 8, virtual_base, physical_base, memory_size, top_of_kernel)
    struct.pack_into('<6Q', raw, 40, *video)
    struct.pack_into('<I', raw, 88, uint(machine_type, 32))
    struct.pack_into('<QI', raw, 96, device_tree_pointer, device_tree_length)
    raw[108:108 + len(line)] = line
    struct.pack_into('<QQ', raw, 1136, uint(boot_flags), actual)
    return bytes(raw)


def validate_placement(*, ram, reserved, occupied, kernel, arguments,
                       device_tree=None, adapter=None, top_of_kernel):
    """Reject conflicts; never choose addresses or infer free RAM from iomem.

    The caller must supply occupied ranges for the running recovery/loader,
    including buffers, stacks and page tables. These cannot be learned from
    a firmware DT alone. Even a passing result remains PC-only evidence.
    """
    if not isinstance(reserved, (list, tuple)) or not isinstance(occupied, (list, tuple)):
        raise ValueError('Explicit reservation and live occupancy lists required')
    allocations = {'kernel': kernel, 'arguments': arguments}
    if device_tree is not None: allocations['device_tree'] = device_tree
    if adapter is not None: allocations['adapter'] = adapter
    if arguments.size < SIZE:
        raise ValueError('Boot arguments allocation is too small')
    if any(r.start % PAGE for r in allocations.values()) or kernel.size % PAGE:
        raise ValueError('Allocations must meet compiled 16K alignment')
    block = Region(kernel.start & ~(BLOCK - 1), BLOCK)
    # start.s adjusts memSize by the Mach-O header displacement, then uses
    # floor(remaining / L2 block size) entries. Do not assume all RAM is mapped.
    count = (ram.end - kernel.start) // BLOCK
    if count <= 0 or not Region(block.start, count * BLOCK).contains(kernel):
        raise ValueError('Kernel exceeds modeled initial bootstrap mapping')
    for name, region in allocations.items():
        if not ram.contains(region): raise ValueError(name + ' outside RAM')
        # Deliberately conservative producer policy: boot metadata stays in
        # the first mapped block; the kernel itself may span multiple blocks.
        if name != 'kernel' and not block.contains(region):
            raise ValueError(name + ' outside first bootstrap block')
        for blocked in (*reserved, *occupied):
            if region.overlaps(blocked): raise ValueError(name + ' conflicts with reserved/occupied RAM')
    items = list(allocations.items())
    for index, (name, region) in enumerate(items):
        if any(region.overlaps(other) for _, other in items[index + 1:]):
            raise ValueError(name + ' overlaps another allocation')
    uint(top_of_kernel)
    if top_of_kernel % PAGE or not max(r.end for r in allocations.values()) <= top_of_kernel <= ram.end:
        raise ValueError('topOfKernelData must cover all allocations and be aligned within RAM')
    return {'layout_checks_passed': True, 'hardware_verified': False,
            'deployment_ready': False, 'device_operations': [],
            'scope': 'Explicit synthetic ranges only; no physical RAM reservation or handoff'}
