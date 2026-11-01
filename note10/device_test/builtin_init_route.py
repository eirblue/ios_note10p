"""Narrow forced-root preparation; no historical preparation/evaluation main."""
import hashlib
from pathlib import Path
import struct

HERE = Path(__file__).resolve().parent
MAIN_SHA = '4493d28f7aacf7de510e7cdc1864fb359278f2f88233abcea6b77a39cb8e0b70'
API_PINS = {
    'kernel/printk/printk.c': '9c3295f8ffe6d7084fcf61d5c087cccd1f936b52d36f4ae43727e815c6b4965d',
    'drivers/char/mem.c': 'f0962ee399ec5e100bd5920b6dd3071c60a9ec475a31dd9c01f07e0051e23af2',
    'include/uapi/asm-generic/unistd.h': '5677bbcd5c765af12ec7d38a866e4224a240de42b67c0a0af9cbb596e53a0f53',
    'usr/Kconfig': 'aaeeaa4793eebaf6eb68c2a41339126c4204de48f6c529f0f1b98e616899b59f',
    'include/linux/sched.h': 'ed3501d62e5a8afc1d76480155285321474b6958ffbccd01cd06cd8d7ffab0a3',
    'include/linux/random.h': '6e7b068350a000bc6bab9dcdab9f5a5914c3319b73d0aa7fb8f0063adfde760c',
    'drivers/char/random.c': 'e03b57b0e113a158415740ce7d1db1767b2e0a858b62257f3e563b8ffd75c55e',
}
OPTION = 'NOTE10_BUILTIN_INIT_ROUTE'


def builtin_cmdline_policy(config):
    """Stock INITRAMFS_FORCE needs EXTEND/FORCE; choose bounded DT append.

    A nonempty CMDLINE makes the ARM64 choice visible. Keep FORCE disabled:
    pinned FDT appends bootloader arguments after this sole builtin argument.
    The independent main.c guard still overrides any later rdinit selection.
    """
    names = ('CMDLINE', 'CMDLINE_FORCE', 'CMDLINE_EXTEND', 'CMDLINE_FROM_BOOTLOADER')
    values = {}
    for line in config.splitlines():
        for name in names:
            key = 'CONFIG_'+name
            value = line[len(key)+1:] if line.startswith(key+'=') else 'n' if line == '# '+key+' is not set' else None
            if value is not None:
                if name in values:
                    raise ValueError('duplicate actual builtin-route setting: '+name)
                values[name] = value
    if (values.get('CMDLINE') != '"rdinit=/init"' or values.get('CMDLINE_EXTEND') != 'y' or
            any(values.get(name, 'n') != 'n' for name in ('CMDLINE_FORCE', 'CMDLINE_FROM_BOOTLOADER'))):
        raise ValueError('builtin route requires only rdinit=/init, EXTEND=y and no FORCE/alternate choice')
    return dict(builtin_cmdline='rdinit=/init', builtin_cmdline_empty=False,
                bootloader_arguments_overwritten=False, bootloader_arguments_appended=True,
                pinned_fdt_branch='builtin-prefix-then-DT-bootargs',
                append_bound='existing COMMAND_LINE_SIZE; no unbounded preservation claim')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def elf_manifest(data):
    if not 64 <= len(data) <= 1024*1024 or data[:6] != b'\x7fELF\x02\x01':
        raise ValueError('bounded static ELF64LE required')
    kind, machine = struct.unpack_from('<HH', data, 16)
    offset = struct.unpack_from('<Q', data, 32)[0]
    size, count = struct.unpack_from('<HH', data, 54)
    if kind != 2 or machine != 183 or size != 56 or not 1 <= count <= 16 or offset+size*count > len(data):
        raise ValueError('static AArch64 executable program headers required')
    loads = []
    for i in range(count):
        typ, flags, pos, va, pa, filesz, memsz, align = struct.unpack_from('<IIQQQQQQ', data, offset+i*size)
        if typ in (2, 3) or filesz > memsz or pos+filesz > len(data):
            raise ValueError('dynamic/interpreter or invalid segment prohibited')
        if typ == 1:
            if flags & 3 == 3:
                raise ValueError('writable executable segment prohibited')
            loads.append((va, va+memsz, flags))
    entry = struct.unpack_from('<Q', data, 24)[0]
    if not any(a <= entry < z and f & 1 for a, z, f in loads) or b'N10MININIT2' not in data:
        raise ValueError('entry/identity missing')
    return dict(sha256=sha(data), bytes=len(data), machine='AArch64', static=True,
                identity='N10MININIT2', entry=entry)


def cpio(data):
    elf_manifest(data)
    output = bytearray()
    def entry(name, mode, payload=b'', major=0, minor=0):
        encoded = name.encode('ascii')+b'\0'
        fields = (len(output)+1, mode, 0, 0, 2 if mode == 0o040755 else 1, 0,
                  len(payload), 0, 0, major, minor, len(encoded), 0)
        output.extend(b'070701'+''.join(f'{x:08x}' for x in fields).encode())
        output.extend(encoded); output.extend(bytes(-len(output) % 4))
        output.extend(payload); output.extend(bytes(-len(output) % 4))
    entry('dev', 0o040755)
    entry('dev/console', 0o020600, major=5, minor=1)
    entry('dev/kmsg', 0o020600, major=1, minor=11)
    entry('init', 0o100755, data)
    entry('TRAILER!!!', 0)
    output.extend(bytes(-len(output) % 512))
    return bytes(output)


def guard_main(data):
    if sha(data) != MAIN_SHA:
        raise ValueError('pinned init/main.c differs')
    text = data.decode('utf8')
    include = '#include <linux/init.h>'
    namespace = '''\tif (!ramdisk_execute_command)
\t\tramdisk_execute_command = "/init";

\tif (sys_access((const char __user *) ramdisk_execute_command, 0) != 0) {
\t\tramdisk_execute_command = NULL;
\t\tprepare_namespace();
\t}'''
    execute = '\tif (ramdisk_execute_command) {\n\t\tret = run_init_process(ramdisk_execute_command);'
    for anchor in (include, namespace, execute):
        if text.count(anchor) != 1:
            raise ValueError('unique pinned init guard anchor required')
    text = text.replace(include, include+'''
#ifdef CONFIG_NOTE10_BUILTIN_INIT_ROUTE
extern char *n10_builtin_init_argument(void);
extern void __noreturn n10_builtin_init_failed(int error);
#endif''', 1)
    text = text.replace(namespace, '''#ifdef CONFIG_NOTE10_BUILTIN_INIT_ROUTE
\t/* Forced builtin rootfs: never mount a block root, regardless of rdinit. */
\tramdisk_execute_command = "/init";
#else
'''+namespace+'''
#endif''', 1)
    text = text.replace(execute, '''#ifdef CONFIG_NOTE10_BUILTIN_INIT_ROUTE
\t/* SYSTEM_RUNNING was set above. Success returns to the ELF entry; only
\t * the userspace N10INIT2 write proves PID1 reached its own entry point. */
\targv_init[1] = n10_builtin_init_argument();
\targv_init[2] = NULL;
\tret = run_init_process("/init");
#ifdef CONFIG_DEFERRED_INITCALLS
\t/* Preserve stock deferred initialization, also while failed PID1 waits. */
\tschedule_work(&deferred_initcall_work);
#endif
\tif (!ret)
\t\treturn 0;
\tn10_builtin_init_failed(ret);
#endif
'''+execute, 1)
    return text.encode('utf8')


def install(source, identity):
    from prepare_sha256_kat_recovery import install as install_recovery
    source = Path(source)
    for name, digest in API_PINS.items():
        if sha((source/name).read_bytes()) != digest:
            raise ValueError('pinned boot identity API differs: '+name)
    main = guard_main((source/'init/main.c').read_bytes())
    files = install_recovery(source, identity)
    replacements = {
        'drivers/misc/note10_sha256_kat.c': (HERE/'sha256_builtin_init.c').read_bytes(),
        'drivers/misc/builtin_init_route.c': (HERE/'builtin_init_route.c').read_bytes(),
        'init/main.c': main,
    }
    kconfig = source/'drivers/misc/note10_sha256_kat.Kconfig'
    kconfig.write_bytes(kconfig.read_bytes()+b'''
config NOTE10_BUILTIN_INIT_ROUTE
\tbool "Note10 forced minimal Linux PID1 route"
\tdepends on NOTE10_SHA256_KAT_RECOVERY && INITRAMFS_FORCE
\tdefault n
\thelp
\t  Diagnostic only. Never mount block-root or try normal init. Failed
\t  PID1 execution waits after SYSTEM_RUNNING for the existing recovery.
''')
    for name, data in replacements.items():
        (source/name).write_bytes(data)
    return {name: sha((source/name).read_bytes()) for name in (*files, *replacements)}
