"""Exact, default-off v342 iOS 16 root overlay (0021..0026 + 0021-stage-hfs.sh; v344 adds 0027 n10_wdt early pet/kick and
0028 n10_ufs stop ladder) after the MOCKFS overlay (0016..0020)."""
import hashlib
import json
from pathlib import Path

from build_native_bootstrap_selection import run

ROOT = Path(__file__).resolve().parents[2]
PATCHES = ROOT / 'note10/xnu26/patches'
KIND = 'v342-ios16-root-pc'
STAGE_HFS = ('0021-stage-hfs.sh', '8ff66a932ad2a706aae5ad3a162149f6550230020b0d2bab868d276d06621c71')
# (patch file, patch sha256, exact '+++ b/' file list)
OVERLAY = (
    ('0021-exynos9825-builtin-hfs.patch', 'b10fcd64013ec6832d5d30398634ef23c03b9f2c85f3a1424072097cdad76b02',
     ('bsd/conf/files', 'bsd/kern/bsd_init.c', 'bsd/n10_hfs/n10_hfs_compat.h',
      'bsd/n10_hfs/n10_hfs_iokit.c', 'config/MASTER', 'config/MASTER.arm64.exynos9825')),
    ('0022-exynos9825-unsealed-root-continue.patch', '2fe6eef33baa5d3adefcd31791d8cd8dfcfb93f084fa4fd9b90dc9e0aa43c073',
     ('bsd/kern/bsd_init.c',)),
    ('0023-exynos9825-n10-ufs-readonly-root.patch', '5a34e747975837a1567feb1706fec1116ebde7470cc470a7bb84e47aa9736790',
     ('bsd/conf/files', 'bsd/dev/n10_ufs.c', 'bsd/miscfs/mockfs/mockfs_vfsops.c', 'iokit/bsddev/IOKitBSDInit.cpp')),
    ('0024-exynos9825-n10-wdt-bounded-keepalive.patch', '45831ef4910e3ac8c5db6f72b67195752661c471f8070e47fd02b1ac4f580764',
     ('osfmk/arm64/note10/n10_wdt.c', 'osfmk/conf/files.arm64')),
    ('0025-exynos9825-genuine-static-trust-caches.patch', 'f1f8a7541da573fef65a78bd6628386fa9fa905b9569ca851e51c0708db03617',
     ('bsd/conf/files', 'bsd/kern/kern_trustcache.c', 'bsd/kern/n10_trustcache.c', 'bsd/kern/ubc_subr.c',
      'bsd/vm/vm_unix.c')),
    ('0026-exynos9825-legacy-mach-msg-trap.patch', '55ef082d9feef907c97cf7309c87c0d9eab8c6789f7c957a3413a408b3ddb0c6',
     ('osfmk/ipc/ipc_policy.c', 'osfmk/ipc/ipc_policy.h')),
    ('0027-exynos9825-n10-wdt-early-pet-kick.patch', '167b49c422f9ab952c82ae9080a2584b5957b78b77bee06d9cb4c00b857f5b1f',
     ('osfmk/arm64/note10/n10_wdt.c',)),
    ('0028-exynos9825-n10-ufs-stop-ladder.patch', '9e085ec6c8e6623e0f235323be47648bd3a1f506ce34be8b183b0d664ec35bec',
     ('bsd/dev/n10_ufs.c',)),
)
STAGED_DIRS = ('bsd/n10_hfs/core', 'bsd/n10_hfs/hfs_encodings')


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def check_patches():
    require(sha((PATCHES / STAGE_HFS[0]).read_bytes()) == STAGE_HFS[1], 'reviewed HFS stage script differs')
    for name, patch_sha, files in OVERLAY:
        raw = (PATCHES / name).read_bytes()
        plus = [s[6:] for s in raw.decode('utf-8').splitlines() if s.startswith('+++ b/')]
        require(sha(raw) == patch_sha and b'\r' not in raw and sorted(plus) == sorted(files),
                'reviewed v342 overlay patch differs: ' + name)


def apply(source, output):
    """Stage hfs-627.100.6, then apply 0021..0028 once after the MOCKFS overlay and before configure."""
    check_patches()
    require(all(not (source / d).exists() for d in STAGED_DIRS), 'fresh source without staged HFS required')
    run(['bash', PATCHES / STAGE_HFS[0]], source, output / 'ios16-stage-hfs.log')
    require(all((source / d).is_dir() for d in STAGED_DIRS) and (source / 'bsd/n10_hfs/TargetConditionals.h').is_file(),
            'staged HFS sources missing')
    command = ['git', '-c', 'core.autocrlf=false', 'apply']
    for n, (name, _, _) in enumerate(OVERLAY):
        run([*command, '--check', PATCHES / name], source, output / ('ios16-check-' + str(n + 21) + '.log'))
        run([*command, PATCHES / name], source, output / ('ios16-patch-' + str(n + 21) + '.log'))
    files = sorted({rel for _, _, rels in OVERLAY for rel in rels})
    observation = dict(schema='note10-v342-ios16-root-overlay-v1', kind=KIND,
                       stage_hfs=dict(script=STAGE_HFS[0], sha256=STAGE_HFS[1]),
                       patches=[dict(patch=name, patch_sha256=patch_sha) for name, patch_sha, _ in OVERLAY],
                       postimage_sha256={rel: sha((source / rel).read_bytes()) for rel in files})
    with (output / 'ios16-root-overlay.json').open('x') as stream:
        stream.write(json.dumps(observation, sort_keys=True, indent=2) + '\n')
    return observation
