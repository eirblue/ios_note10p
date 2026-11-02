"""Generate the exact EXYNOS checked allocator patch against accepted mapper source."""
import argparse
import difflib
import hashlib
from pathlib import Path
REL = 'osfmk/arm64/arm_vm_init.c'
PREIMAGE_SHA256 = 'c7b4de83ac1b9770000b3d4bfebee6420f9b7b312cde726bf410dd476c92b1fd'
COMPONENT_REL = 'osfmk/arm64/note10/exynos_checked_ptpage.c'
COMPONENT_SHA256 = '427e7e47a52d50134d57f7f870e4542bd24fb1c17ee4b8d0fe1a59e44e7c72fe'
PATCH_NAME = '0013-exynos9825-checked-dynamic-ptpage.patch'
PATCH_SHA256 = '272c06bb3ee6510760e14736168c0034483af7b625a38e72c4310facad97a798'
REPLACEMENTS = [('vm_offset_t\nalloc_ptpage(boolean_t map_static)', '#if defined(ARM64_BOARD_CONFIG_EXYNOS9825)\n#include "note10/exynos_checked_ptpage.c"\n#endif\n\nvm_offset_t\nalloc_ptpage(boolean_t map_static)'), ('\t\tvaddr = phystokv(avail_start);\n\t\tavail_start += ARM_PGBYTES;\n\n\t\treturn vaddr;', '#if defined(ARM64_BOARD_CONFIG_EXYNOS9825)\n        return n10_exynos_dynamic_ptpage();\n#else\n\t\tvaddr = phystokv(avail_start);\n\t\tavail_start += ARM_PGBYTES;\n\n\t\treturn vaddr;\n#endif'), ('\tgPhysBase = args->physBase;\n', '\tgPhysBase = args->physBase;\n#if defined(ARM64_BOARD_CONFIG_EXYNOS9825)\n    n10_pt_require_boot_input(gPhysBase, args->memSize, memory_size);\n#endif\n')]
HERE = Path(__file__).resolve().parent

def patch_bytes(before):
    if hashlib.sha256(before).hexdigest() != PREIMAGE_SHA256:
        raise ValueError('exact accepted after-mapper source required')
    text = before.decode()
    for old, new in REPLACEMENTS:
        if text.count(old) != 1:
            raise ValueError('unique native allocator seam required')
        text = text.replace(old, new, 1)
    component = (HERE / 'exynos_checked_ptpage.c').read_bytes()
    if hashlib.sha256(component).hexdigest() != COMPONENT_SHA256:
        raise ValueError('tested allocator component differs')
    chunks = [''.join(difflib.unified_diff(before.decode().splitlines(True), text.splitlines(True),
        fromfile='a/' + REL, tofile='b/' + REL)),
        ''.join(difflib.unified_diff([], component.decode().splitlines(True),
        fromfile='/dev/null', tofile='b/' + COMPONENT_REL))]
    raw = ''.join(chunks).encode()
    if hashlib.sha256(raw).hexdigest() != PATCH_SHA256:
        raise ValueError('reviewed allocator literal patch differs')
    return raw

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    raw = patch_bytes((a.source / REL).read_bytes())
    with a.output.open('xb') as stream:
        stream.write(raw)
if __name__ == '__main__':
    main()
