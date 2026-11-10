"""Private v159 source transform and same-Image rootfs metadata proof."""
import hashlib
from pathlib import Path
import re
import struct

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
STOCK = ROOT / 'note10/private/device-test/v106-kernel-owned-span-pc-20261103/authenticated-producer/image-producer/stock-inputs/init/initramfs.c'
OBSERVER = ROOT / 'note10/device_test/v157_builtin_init_observation.inc'
HEADER = HERE / 'note10_rootfs_snapshot.h'
STOCK_SHA = '1a9af19668584dc664c28c640e02b6a03cc37a2fa5ecd1900d818bb67c775806'
OBSERVER_SHA = 'f9b97fa886ff303657b73b68276af4e31ee770fc0a6c8f1ff4392cbf4d675498'
HEADER_SHA = '9844788efebdcc5793bc0f50d9abc34ec0f396ac0e9431fb8f875aca604bfaf1'

STATE = b'''
#ifdef CONFIG_NOTE10_BUILTIN_INIT_ROUTE
#include <linux/bug.h>
#include <linux/compiler.h>
#include <linux/errno.h>
#include <linux/note10_rootfs_snapshot.h>

static struct n159_rootfs_snapshot n159_rootfs_state = {
    .init_open_result = -ENODATA,
};

void n159_rootfs_get_snapshot(struct n159_rootfs_snapshot *out)
{
    BUILD_BUG_ON(sizeof(*out) > 128);
    out->declared_size = READ_ONCE(n159_rootfs_state.declared_size);
    out->populate_seen = READ_ONCE(n159_rootfs_state.populate_seen);
    out->skip = READ_ONCE(n159_rootfs_state.skip);
    out->init_members = READ_ONCE(n159_rootfs_state.init_members);
    out->init_open_result = READ_ONCE(n159_rootfs_state.init_open_result);
}
#endif
'''
POPULATE = b'''
#ifdef CONFIG_NOTE10_BUILTIN_INIT_ROUTE
    if (n159_rootfs_state.populate_seen < 2)
        n159_rootfs_state.populate_seen++;
    n159_rootfs_state.skip = !!do_skip_initramfs;
    n159_rootfs_state.declared_size = __initramfs_size;
#endif
'''
MEMBER = b'''
#ifdef CONFIG_NOTE10_BUILTIN_INIT_ROUTE
    if (!strcmp(collected, "init") && n159_rootfs_state.init_members < 2)
        n159_rootfs_state.init_members++;
#endif
'''
OPEN = b'''
#ifdef CONFIG_NOTE10_BUILTIN_INIT_ROUTE
            if (!strcmp(collected, "init"))
                n159_rootfs_state.init_open_result = wfd < 0 ? wfd : 0;
#endif
'''
SNAPSHOT = b'''
    n159_rootfs_get_snapshot(&snapshot);
    printk(KERN_INFO "N159ROOT1 id=%s boot=%s cycle=%s seen=%u skip=%u declared=%lu init_members=%u init_open=%d\\n",
           N154_BUILD_ID, n10_boot_id,
           n10_cycle_valid() ? (const char *)n10_cycle : "00000000000000000000000000000000",
           snapshot.populate_seen, snapshot.skip, snapshot.declared_size,
           snapshot.init_members, snapshot.init_open_result);
'''


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def require(ok, message):
    if not ok:
        raise ValueError(message)


def once(raw, anchor, replacement):
    require(raw.count(anchor) == 1, 'unique pinned v159 insertion anchor required')
    return raw.replace(anchor, replacement, 1)


def prepare(stock, observer, header):
    require((digest(stock), digest(observer), digest(header)) == (STOCK_SHA, OBSERVER_SHA, HEADER_SHA),
            'exact reviewed rootfs/observer/header sources required')
    include = b'#include <linux/initramfs.h>\n'
    modified = once(stock, include, include + STATE)
    populate = b'static int __init populate_rootfs(void)\n{\n\tchar *err;\n'
    modified = once(modified, populate, populate + POPULATE)
    path = b'\tclean_path(collected, mode);\n\tif (S_ISREG(mode)) {'
    modified = once(modified, path, MEMBER + path)
    opened = b'\t\t\twfd = sys_open(collected, openflags, mode);\n'
    modified = once(modified, opened, opened + OPEN)
    observed = once(observer, b'#include <linux/namei.h>\n',
                    b'#include <linux/namei.h>\n#include <linux/note10_rootfs_snapshot.h>\n')
    declaration = b'    unsigned int execute_bits = 0;\n'
    observed = once(observed, declaration, declaration + b'    struct n159_rootfs_snapshot snapshot;\n' + SNAPSHOT)
    return {'init/initramfs.c': modified, 'drivers/misc/v157_builtin_init_observation.inc': observed,
            'include/linux/note10_rootfs_snapshot.h': header}


def linked_rootfs_proof(image, symbols, archive_size, linked_extent):
    require(type(image) is bytes and image[56:60] == b'ARM\x64' and
            type(archive_size) is int and 0 < archive_size <= len(image) and
            type(linked_extent) is int and linked_extent >= 64, 'same-Image bounded rootfs inputs required')
    names = {'_text', '__initramfs_size', 'populate_rootfs', '__initcall_populate_rootfsrootfs',
             '__initcall5_start', '__initcallrootfs_start', '__initcall6_start'}
    table = {}
    for line in symbols.splitlines():
        row = re.fullmatch(r'([0-9a-fA-F]{1,16})\s+\S\s+(\S+)', line)
        if row and row[2] in names:
            require(row[2] not in table, 'duplicate rootfs linkage symbol')
            table[row[2]] = int(row[1], 16)
    require(set(table) == names, 'exact non-LTO rootfs linkage symbols required')
    start = table['_text']
    limit = min(len(image), linked_extent)
    def word(address):
        offset = address - start
        require(0 <= offset <= limit - 8 and address % 8 == 0, 'linked rootfs word outside Image')
        return struct.unpack_from('<Q', image, offset)[0], offset
    size, size_offset = word(table['__initramfs_size'])
    slot = table['__initcall_populate_rootfsrootfs']
    target, slot_offset = word(slot)
    require(size == archive_size and table['__initcall5_start'] <= table['__initcallrootfs_start'] <= slot and
            slot + 8 <= table['__initcall6_start'] and target == table['populate_rootfs'] and
            0 <= target - start < limit, 'linked rootfs size/initcall binding differs')
    return dict(schema='note10-v159-linked-rootfs-materialization-proof-v1', declared_archive_bytes=size,
                size_word_offset=size_offset, rootfs_initcall_slot_offset=slot_offset,
                rootfs_initcall_target=target, rootfs_section_start=table['__initcallrootfs_start'],
                rootfs_section_end=table['__initcall6_start'], runtime_population_proved=False)


def self_check():
    stock, observer, header = STOCK.read_bytes(), OBSERVER.read_bytes(), HEADER.read_bytes()
    transformed = prepare(stock, observer, header)
    changed = transformed['init/initramfs.c']
    require(changed.replace(STATE, b'', 1).replace(POPULATE, b'', 1).replace(MEMBER, b'', 1).replace(OPEN, b'', 1) == stock,
            'rootfs transform changed original calls/order/error handling')
    original = transformed['drivers/misc/v157_builtin_init_observation.inc']
    original = original.replace(b'#include <linux/note10_rootfs_snapshot.h>\n', b'', 1)
    original = original.replace(b'    struct n159_rootfs_snapshot snapshot;\n', b'', 1).replace(SNAPSHOT, b'', 1)
    require(original == observer and transformed['include/linux/note10_rootfs_snapshot.h'] == header,
            'snapshot altered original pre-exec behavior')
    require('kern_path' not in STATE.decode() and '__initdata' not in STATE.decode() and
            changed.count(b'wfd = sys_open(collected, openflags, mode);') == 1 and
            changed.count(b'unpack_to_rootfs(__initramfs_start, __initramfs_size)') == stock.count(b'unpack_to_rootfs(__initramfs_start, __initramfs_size)'),
            'telemetry must remain permanent and never repeat syscalls/unpack')
    image = bytearray(4096)
    image[56:60] = b'ARM\x64'
    struct.pack_into('<Q', image, 0x100, 3584)
    struct.pack_into('<Q', image, 0x120, 0x1800)
    rows = {'_text': 0x1000, '__initramfs_size': 0x1100, 'populate_rootfs': 0x1800,
            '__initcall_populate_rootfsrootfs': 0x1120, '__initcall5_start': 0x1108,
            '__initcallrootfs_start': 0x1110, '__initcall6_start': 0x1130}
    symbols = '\n'.join(f'{value:016x} D {name}' for name, value in rows.items())
    require(linked_rootfs_proof(bytes(image), symbols, 3584, len(image))['declared_archive_bytes'] == 3584,
            'linked size/initcall positive fixture')
    for mutate in ('size', 'slot', 'duplicate', 'input'):
        malformed = bytearray(image)
        table = symbols
        if mutate == 'size':
            struct.pack_into('<Q', malformed, 0x100, 0)
        elif mutate == 'slot':
            struct.pack_into('<Q', malformed, 0x120, 0x1804)
        elif mutate == 'duplicate':
            table += '\n0000000000001800 T populate_rootfs'
        try:
            if mutate == 'input':
                prepare(stock + b'\n', observer, header)
            else:
                linked_rootfs_proof(bytes(malformed), table, 3584, len(image))
        except ValueError:
            continue
        raise AssertionError('malformed v159 input accepted')


if __name__ == '__main__':
    self_check()
