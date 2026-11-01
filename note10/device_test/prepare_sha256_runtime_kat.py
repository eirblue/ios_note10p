"""Render a default-off SHA256 runtime KAT into a fresh, extracted kernel tree."""
import hashlib
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
OPTION = 'NOTE10_SHA256_RUNTIME_KAT'
TARGET = 'drivers/misc/note10_sha256_kat.o'


def render(identity):
    if not isinstance(identity, str) or not re.fullmatch('[0-9a-f]{32}', identity):
        raise ValueError('32 lowercase hex build evidence ID required')
    return {
        'drivers/misc/note10_sha256_kat.c': (HERE/'sha256_runtime_kat.c').read_bytes(),
        'drivers/misc/note10_sha256_kat_id.h': (
            '#define N10_SHA256_KAT_ID "'+identity+'"\n').encode('ascii'),
        'drivers/misc/note10_sha256_kat.Kconfig': b'''config NOTE10_SHA256_RUNTIME_KAT
\tbool "Note10 SHA256 runtime known-answer observation"
\tdepends on CRYPTO=y && CRYPTO_HASH=y && CRYPTO_SHA256=y
\tdefault n
\thelp
\t  Observe sha256-generic allocation and SHA256(abc) at late init.
\t  Default off. Synchronous crypto calls have no hard local deadline.
\t  Requires separately reviewed recovery/device integration before use.
''',
        'drivers/misc/note10_sha256_kat.Makefile':
            b'obj-$(CONFIG_NOTE10_SHA256_RUNTIME_KAT) += note10_sha256_kat.o\n',
    }


def install(source, identity):
    """Only call for a disposable extraction, never immutable source inputs."""
    source = Path(source)
    files = render(identity)
    hooks = {
        'drivers/misc/Makefile': '\ninclude $(srctree)/drivers/misc/note10_sha256_kat.Makefile\n',
        'drivers/misc/Kconfig': '\nsource "drivers/misc/note10_sha256_kat.Kconfig"\n',
    }
    for name in (*files, *hooks):
        path = source/name
        if any(p.is_symlink() for p in (path, *path.parents)):
            raise ValueError('overlay path traverses a symlink')
        if name in files and path.exists():
            raise ValueError('KAT overlay already exists')
        if name in hooks and (not path.is_file() or 'note10_sha256_kat' in path.read_text()):
            raise ValueError('missing or already modified stock hook')
    for name, data in files.items():
        (source/name).write_bytes(data)
    for name, text in hooks.items():
        with (source/name).open('a', encoding='ascii', newline='\n') as stream:
            stream.write(text)
    return {name: hashlib.sha256((source/name).read_bytes()).hexdigest()
            for name in (*files, *hooks)}
