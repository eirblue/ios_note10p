"""Small recovery/KAT composition in a disposable pinned kernel extraction."""
import hashlib
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
OPTION = 'NOTE10_SHA256_KAT_RECOVERY'
TARGET = 'drivers/misc/note10_sha256_kat.o'
INHERITED = {
    'sha256_runtime_kat.c': '58470621def88390f16d2608989bafac76ff6d502bb211d400d2b488ed5df5ca',
    'auto_return.c': '9ec43d3d17f12fe90d2ab36e4712537b7f8275f6f27b6536bbef826f9692037d',
    'decode_sha256_runtime_kat.py': 'c83437aae48ee4f1d7400edf73933c8b0102291934648a30387100ef187f42b9',
}
KERNEL_PINS = {
    'init/main.c': '4493d28f7aacf7de510e7cdc1864fb359278f2f88233abcea6b77a39cb8e0b70',
    'kernel/reboot.c': 'ed27858a87e0b7fe098510f03054c034a333874017444de2052af3e691d5b3f8',
    'drivers/samsung/sec_reboot.c': '9c598d65fac6c7be4ba9bcf1d3f6d7d5ec218844c28b97653deabc707190d594',
    'drivers/soc/samsung/exynos-reboot.c': 'be332988d59a77ae616a86bd70ac52ecae6dff94715239b84450a22c02633cf8',
    'drivers/base/core.c': '9f7daf9fe78e859cb419726ea837ef7b7a7e73ec3292718f8904da177c266512',
    'drivers/base/dd.c': '4ddf89fa825760b38fe4535a7e9b473675a740495caf364c2d7fb378aecd7746',
    'kernel/umh.c': '0a066faaf89b44d26b50f2456f4d4fc8bd54e5a187853393739d2e5acc099fe8',
    'crypto/api.c': 'e8e20ddab40bbb3a8db20e9a0b48a753549f97f3a40733daaecc7514c38707a3',
}


def inherited():
    result = {}
    for name, expected in INHERITED.items():
        data = (HERE/name).read_bytes()
        if hashlib.sha256(data).hexdigest() != expected:
            raise ValueError('inherited source changed: '+name)
        result[name] = data
    return result


def render(identity):
    if not isinstance(identity, str) or not re.fullmatch('[0-9a-f]{32}', identity):
        raise ValueError('32 lowercase hex build evidence ID required')
    old = inherited()
    return {
        'drivers/misc/note10_sha256_kat.c': (HERE/'sha256_kat_recovery.c').read_bytes(),
        'drivers/misc/sha256_kat_recovery_work.c': (HERE/'sha256_kat_recovery_work.c').read_bytes(),
        'drivers/misc/sha256_runtime_kat.c': old['sha256_runtime_kat.c'],
        'drivers/misc/note10_auto_return.c': old['auto_return.c'],
        'drivers/misc/note10_sha256_kat_id.h': ('#define N10_SHA256_KAT_ID "'+identity+'"\n').encode(),
        'drivers/misc/note10_sha256_kat.Kconfig': b'''config NOTE10_SHA256_KAT_RECOVERY
\tbool "Note10 recovery-armed SHA256 known-answer observation"
\tdepends on ARM64 && CRYPTO=y && CRYPTO_HASH=y && CRYPTO_SHA256=y
\tdefault n
\thelp
\t  Arm the existing diagnostic recovery route, then defer SHA256(abc)
\t  to a separate worker after SYSTEM_RUNNING. Requires a patched cycle ID.
\t  No hard-lockup recovery or cancellation of synchronous crypto calls.
''',
        'drivers/misc/note10_sha256_kat.Makefile':
            b'obj-$(CONFIG_NOTE10_SHA256_KAT_RECOVERY) += note10_sha256_kat.o\n',
    }


def install(source, identity):
    source = Path(source)
    files = render(identity)
    for name, expected in KERNEL_PINS.items():
        if hashlib.sha256((source/name).read_bytes()).hexdigest() != expected:
            raise ValueError('pinned recovery/init API source changed: '+name)
    hooks = {'drivers/misc/Makefile': '\ninclude $(srctree)/drivers/misc/note10_sha256_kat.Makefile\n',
             'drivers/misc/Kconfig': '\nsource "drivers/misc/note10_sha256_kat.Kconfig"\n'}
    for name in (*files, *hooks):
        path = source/name
        if any(p.is_symlink() for p in (path, *path.parents)):
            raise ValueError('overlay path traverses a symlink')
        if name in files and path.exists():
            raise ValueError('recovery/KAT overlay already exists')
        if name in hooks and (not path.is_file() or 'note10_sha256_kat' in path.read_text()):
            raise ValueError('missing or modified stock hook')
    for name, data in files.items():
        (source/name).write_bytes(data)
    for name, text in hooks.items():
        with (source/name).open('a', encoding='ascii', newline='\n') as stream:
            stream.write(text)
    return {name: hashlib.sha256((source/name).read_bytes()).hexdigest() for name in (*files, *hooks)}
