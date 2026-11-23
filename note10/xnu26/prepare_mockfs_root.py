"""Exact, default-off MOCKFS memory-root overlay (0016..0020) on the closed series13 source tree."""
import hashlib
import json
from pathlib import Path

from build_native_bootstrap_selection import run

ROOT = Path(__file__).resolve().parents[2]
PATCHES = ROOT / 'note10/xnu26/patches'
KIND = 'v340-mockfs-root-pc'
# (patch file, single source file, patch sha256, series13 preimage sha256, postimage sha256)
OVERLAY = (
    ('0016-exynos9825-mockfs-filesys.patch', 'config/MASTER.arm64.exynos9825',
     'e0c081b5942dc1588c03544162ef9a1736f5ab6b04c79b1eaf73884130b88103',
     '7305ce563bc221d71d4825f431d7b531befe081619efe586a444bbfd05bb5213',
     '8ec73ab6d8a45728791b906140db6a25dc58fc9926fdf64e58ba4087912c3e2e'),
    ('0017-mockfs-fsnode-type.patch', 'bsd/miscfs/mockfs/mockfs_fsnode.c',
     '9fd1e4cbdad3cb311d63edc34e246386db3e7557083cae2893d607882bcab117',
     'd0a949994d3f498a555547041710b8d83705a969eb3f564bdb4770c6ead0204d',
     '68b7e1a3d53ccceab60d4ff204e5a066941c2f89ff4f9b0324f585e4c0f163b3'),
    ('0018-mockfs-virtual-memdev.patch', 'bsd/miscfs/mockfs/mockfs_vfsops.c',
     '93be10981ee1427c057941184105ef4fdcd46afb59fe068191e7489f1471b31f',
     '2b38d7c13e3e2f591bdf41c62d2dc7e59d3b7a594e28bfe0e2331dda972e370d',
     'a2f0fa2edac585f74228f60e3ca0c56bb4fad3326546ca326309168f88ba037e'),
    ('0019-exynos9825-root-media-without-iostorage.patch', 'iokit/Kernel/IOService.cpp',
     '7d42a7aaf2aa15c4fe3b58bf5f094db39f13b61ee5b9dea242aabd418733ac72',
     '8f08ead991b7daf25a0d67344e4ea2de1a9807c04f97723f76857a1869622e72',
     'ea7cd21b70bdf2cec22a4ed68a9df1329ae198615122a1c7a3f5575775ef5d67'),
    ('0020-exynos9825-init-lookup-checkpoint.patch', 'bsd/kern/kern_exec.c',
     '7a4216a249837e0a929056b313efc0ef06932e34af4e2b48c98b4d560e2fb9e7',
     'ecec070f1cb5139f3681d7a95167a4bfe8f034f6fd1cc58bda5d9b447d85e045',
     '1d77dccf097538758855d8bb799908f69c201ef68ffb3ecd2e3d5ab5c1a978df'),
)


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def proof():
    return dict(schema='note10-v340-mockfs-root-overlay-v1', kind=KIND, patches=[
        dict(patch=name, source=rel, patch_sha256=patch_sha, preimage_sha256=pre, postimage_sha256=post)
        for name, rel, patch_sha, pre, post in OVERLAY])


def check_patches():
    for name, rel, patch_sha, _, _ in OVERLAY:
        raw = (PATCHES / name).read_bytes()
        lines = raw.decode('utf-8').splitlines()
        require(sha(raw) == patch_sha and b'\r' not in raw and
                [s for s in lines if s.startswith(('--- ', '+++ '))] == ['--- a/' + rel, '+++ b/' + rel],
                'reviewed single-file overlay patch differs: ' + name)


def apply(source, output):
    """Apply 0016..0020 once after provision (series 0001..0013) and before configure."""
    check_patches()
    for name, rel, _, pre, _ in OVERLAY:
        require(sha((source / rel).read_bytes()) == pre, 'exact series13 preimage required: ' + rel)
    command = ['git', '-c', 'core.autocrlf=false', 'apply']
    for n, (name, _, _, _, _) in enumerate(OVERLAY):
        run([*command, '--check', PATCHES / name], source, output / ('mockfs-check-' + str(n + 16) + '.log'))
        run([*command, PATCHES / name], source, output / ('mockfs-patch-' + str(n + 16) + '.log'))
    for name, rel, _, _, post in OVERLAY:
        require(sha((source / rel).read_bytes()) == post, 'exact reviewed postimage required: ' + rel)
    observation = proof()
    with (output / 'mockfs-root-overlay.json').open('x') as stream:
        stream.write(json.dumps(observation, sort_keys=True, indent=2) + '\n')
    return observation
