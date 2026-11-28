"""Exact, default-off v342 iOS 16 root overlay (0021..0026 + 0021-stage-hfs.sh; v344 adds 0027 n10_wdt early pet/kick and
0028 n10_ufs stop ladder; v346 adds 0029 n10_ufs task tag 0 and site-10 clock-stop/IS detail; v347 adds 0030 n10_dsslog
synchronous-exception capture into the Linux dss log ring and 0031 console/kprintf text copy into it) after the MOCKFS
overlay (0016..0020)."""
import hashlib
import json
from pathlib import Path

from build_native_bootstrap_selection import run

ROOT = Path(__file__).resolve().parents[2]
PATCHES = ROOT / 'note10/xnu26/patches'
FILE_OVERLAY = ROOT / 'note10/xnu26/overlay'
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
    ('0029-exynos9825-n10-ufs-tag-clkstop-detail.patch', 'c26a2528af697e87d6c0728e5b510bbb02f610f66ccae5532d1715f36d09efca',
     ('bsd/dev/n10_ufs.c',)),
    ('0030-exynos9825-n10-dss-sync-capture.patch', '1a2a8b314737b82d1d2b6092991dd7599c9de523f3513c7d8575a0e778b0edbd',
     ('osfmk/arm64/note10/n10_dsslog.c', 'osfmk/conf/files.arm64')),
    ('0031-exynos9825-n10-dss-console-log.patch', '6547a28df4561b487b6c4646e0b88891200d70839a16883a2ec5be07b0398c3d',
     ('osfmk/console/serial_console.c', 'pexpert/arm/pe_kprintf.c')),
    ('0032-exynos9825-amfi-absent-der-entitlements.patch', '0197c10f61f27fb03d16b9c3198c24e1fe657e5631f5a6208d69dde8e1daa787',
     ('bsd/kern/kern_cs.c', 'iokit/bsddev/IOKitBSDInit.cpp')),
    ('0033-exynos9825-n10-ephemeral-storage.patch', 'c21abc250152fbb13320bd55aee52c2ef44a5cb2b49f8ef79f96e3312331890f',
     ('bsd/kern/kern_mib.c',)),
    ('0034-exynos9825-n10-ufs-ram-write-overlay.patch', '9584e547d4c68e395925957d50a4f32ecb4b5a70adfb78b965913b145afe10dd',
     ('bsd/dev/n10_ufs.c', 'bsd/vfs/vfs_subr.c', 'bsd/vfs/vfs_syscalls.c')),
    ('0035-exynos9825-n10-ufs-ram-overlay-zero-blocks.patch', '2f2b1ce1259f3a064b471a6634ab81e78cdfd168048d015c529f007cd59bcd13',
     ('bsd/dev/n10_ufs.c',)),
    ('0036-exynos9825-n10-ufs-userdata-write.patch', '2f7c2926198151903a4eb83d74a308a0752d89153606378ac1608ffffbbf83e0',
     ('bsd/dev/n10_ufs.c',)),
    ('0037-exynos9825-n10-dataprotect-class0-panic-note.patch',
     '76c84c46dbf531e411eb23f81847ca96f0e861ba3e7345044785cdd7faabca10',
     ('bsd/vfs/vfs_attrlist.c', 'osfmk/kern/debug.c')),
    ('0038-exynos9825-n10-ufs-readonly-root-data-volume.patch',
     '8e23342676a356d4bca0daa9caf91fcc9cb3e37c0572fded455e875d0ad40d78',
     ('bsd/dev/n10_ufs.c', 'bsd/vfs/vfs_subr.c', 'bsd/vfs/vfs_syscalls.c')),
    ('0039-exynos9825-n10-legacy-mach-ports-lookup.patch',
     'adec78e1c54762e64a1d3e6edfcb4958747b0a1fb2bbcb78001c3fce6638eba9',
     ('osfmk/kern/ipc_tt.c', 'osfmk/mach/task.defs')),
    ('0040-exynos9825-n10-write-random-early-reseed.patch',
     '593f60378400994dbfc6f67b8d29a87e4e596d65f1c553f08ad12747f16dcdad',
     ('osfmk/prng/prng_random.c',)),
    ('0041-exynos9825-n10-preemption-disable-threshold.patch',
     '9662b2cd737c061f8d93a53520b9dfb70e195dbc011114c2ce755672eaf2f330',
     ('osfmk/arm/preemption_disable.c',)),
    ('0042-exynos9825-n10-dss-process-trace.patch',
     '9541dc2fc7055bd3d9510e1b8422266746e5ec98b2cd60217b1233a81899b740',
     ('bsd/kern/kern_exec.c', 'bsd/kern/kern_exit.c', 'bsd/kern/kern_shutdown.c',
      'osfmk/arm64/note10/n10_dsslog.c', 'osfmk/arm64/note10/n10_wdt.c')),
    ('0043-exynos9825-n10-kernel-fast-fault-forward.patch',
     'dd496ab539bc9263a8f00b517e26d1bacfe3f4d9e445a0d940f5d75f1c09acf5',
     ('osfmk/arm64/note10/n10_dsslog.c', 'osfmk/arm64/note10/n10_wdt.c')),
    ('0044-exynos9825-n10-xpcproxy-call-trace.patch',
     'ead7cf0ce09403fa0b68bdc3f7888c4c578589b44b5a18bdec57e4ae2b67952e',
     ('bsd/dev/arm/systemcalls.c', 'osfmk/arm64/bsd_arm64.c', 'osfmk/arm64/note10/n10_wdt.c')),
    ('0045-exynos9825-n10-bootstrap-map-48mib.patch',
     '6211394464971976cde97924a3bf7770f3a1e6f4b3cfd0d33a5593f412ec4687',
     ('osfmk/arm64/start.s',)),
    ('0046-exynos9825-n10-xpcproxy-wait-macpolicy-trace.patch',
     '3e198ff59cd9277bfd2e207ba20d241f3700fad0291e2d6382bc1bc3ec3b5a1c',
     ('bsd/dev/arm/systemcalls.c', 'osfmk/arm64/bsd_arm64.c', 'osfmk/arm64/note10/n10_wdt.c', 'security/mac_base.c')),
    ('0047-exynos9825-n10-multistage-wdt-reload-thread-wait-trace.patch',
     'f3b41f4d98631d326c545031787e009fa565640a2ed0599e059894dab80f0ded',
     ('bsd/dev/arm/systemcalls.c', 'osfmk/arm64/bsd_arm64.c', 'osfmk/arm64/note10/n10_wdt.c')),
    ('0048-exynos9825-n10-wdt-250ms-tick-trace.patch',
     '054def6ebbb5fe6fdf7e3197fdf042d5f4c4fe87e866377b25a35335618c33d1',
     ('osfmk/arm64/note10/n10_wdt.c',)),
    ('0049-exynos9825-n10-ram-512mib-high-window.patch',
     '1a8224f586135b0458de4b597b4a56fbe4b14119b52356917cfc8c67a33efac0',
     ('bsd/dev/n10_ufs.c', 'osfmk/arm64/arm_vm_init.c', 'osfmk/arm64/note10/n10_dsslog.c', 'osfmk/arm64/start.s')),
    ('0050-exynos9825-n10-ufs-stop-dss-line.patch',
     '4f6f5e9b919f324327dace9991f6d8e3c8c2892853ed560c9d2d8fbcd83a777c',
     ('bsd/dev/n10_ufs.c',)),
    ('0051-exynos9825-n10-psynch-ipc-bincompat-watchdogd.patch',
     '12908b2e246a7a65b4cafcba67e6cc84c0f9c7c1ff02aca4b7491a4f4b7f48bd',
     ('bsd/conf/files', 'bsd/kern/hvg_sysctl.c', 'bsd/kern/kern_exit.c', 'bsd/pthread/n10_psynch.c',
      'bsd/pthread/pthread_shims.c', 'iokit/Kernel/IOPlatformExpert.cpp', 'osfmk/ipc/ipc_policy.c')),
    ('0052-exynos9825-n10-text-tail-pad.patch',
     '1513be2868671c82177191a34a69f4f73900fafa5a5097dddefe8c8aae0fc099',
     ('osfmk/arm64/note10/n10_dsslog.c',)),
    ('0053-exynos9825-n10-silent-stop-capture-crumbs.patch',
     '022cc1c5ad5605c40402459286f5fc56ec9814f62605ad31869d8e78a28506b5',
     ('bsd/dev/arm/systemcalls.c', 'osfmk/arm64/bsd_arm64.c', 'osfmk/arm64/locore.s',
      'osfmk/arm64/note10/n10_dsslog.c', 'osfmk/arm64/sleh.c')),
    ('0054-exynos9825-n10-ufs-fua-panic-backtrace.patch',
     'da83122175cd24d475997d93e6e3a2cbf289ed5d7ab72eded71d07e483a4ae4e',
     ('bsd/dev/n10_ufs.c', 'osfmk/kern/debug.c')),
    ('0055-exynos9825-n10-abort-reason-iokit-miss-no-crash-reporter.patch',
     '23b008a29aea28555e3193927c6310c3a11cab968b1d7bf2375292f5bed81a69',
     ('bsd/kern/kern_exit.c', 'iokit/Kernel/IOUserClient.cpp')),
    ('0056-exynos9825-n10-csops-signature-psynch-rwlock.patch',
     '5eedf503e0473325b0e53c7f6b3bed036db6e53b3e7ed94fb425a1f510bd6fff',
     ('bsd/kern/kern_proc.c', 'bsd/pthread/n10_psynch.c', 'bsd/pthread/pthread_shims.c')),
    ('0057-exynos9825-n10-iomfb-display-sandbox-check-trace.patch',
     'c761b69a7be63af679f4b15a34f2396c69d36caf3ecce23bbe4de70c6313d2bb',
     ('bsd/dev/arm/systemcalls.c', 'bsd/kern/kern_proc.c', 'iokit/Kernel/NoteFramebuffer.cpp',
      'iokit/bsddev/IOKitBSDInit.cpp', 'iokit/conf/files', 'security/mac_base.c')),
    ('0058-exynos9825-n10-csops-status-valid-hid-stub-iomfb-counts.patch',
     '1eb11ec92335b520d1ecf77adb6760796158879289b2d6deefbf5c6934cd7f8b',
     ('bsd/dev/arm/systemcalls.c', 'bsd/kern/kern_proc.c', 'iokit/Kernel/NoteFramebuffer.cpp',
      'osfmk/arm64/note10/n10_dsslog.c')),
    ('0059-exynos9825-n10-fault-image-trace-open-fail-iokit-cap.patch',
     '7df625dd96cc91d3ce4fe3b3771d579f4bec0be92aa4b7a02b472d9d52c3260a',
     ('bsd/kern/kern_exit.c', 'iokit/Kernel/IOUserClient.cpp')),
    ('0060-exynos9825-n10-fault-sc-offset-registry-path-miss.patch',
     '3895c57cd2bfa164d8e1ad2e1ac77c8fd7c0ca94bbcb80c25bb839d3f58d25c3',
     ('bsd/kern/kern_exit.c', 'iokit/Kernel/IOUserClient.cpp')),
    ('0061-exynos9825-n10-dt-product-options-fstab-path-dedupe.patch',
     'b3dd0a3c6a55b520590d52a0bcce80aaa144155249f495d47a9c0264c049de86',
     ('iokit/Kernel/IOUserClient.cpp', 'iokit/Kernel/NoteFramebuffer.cpp')),
    ('0062-exynos9825-n10-iosurface-root-user-client.patch',
     '14bec41c4fe24066df407a81423e403bdd955ddb053c50f300699a8d0b990ae5',
     ('iokit/Kernel/NoteFramebuffer.cpp',)),
    ('0063-exynos9825-n10-chosen-display-scale-surface-trace.patch',
     '37f19a4bce849c2eac7e6b629d01cf1a2369af262546d04fb4ad1af3199dbf9a',
     ('iokit/Kernel/NoteFramebuffer.cpp',)),
    ('0064-exynos9825-n10-decon-scanout-probe-frame-copy.patch',
     '17d2deac1dacbd56316261c9747c926654cd002c6536b6c38044badb952d4873',
     ('iokit/Kernel/NoteFramebuffer.cpp',)),
    ('0065-exynos9825-n10-pmu-calibrated-display-power-probe.patch',
     '2dab192e90d348410af954ad723969bfc3be4421727d7fafa874d875a1d43da9',
     ('iokit/Kernel/NoteFramebuffer.cpp',)),
    ('0066-exynos9825-n10-pagewise-sysmmu-scanout.patch',
     'fcf20fbd9b7613bb9ba908a6da6e5a5b568168a589e79992ccb71bf44cce19f9',
     ('iokit/Kernel/NoteFramebuffer.cpp',)),
    ('0067-exynos9825-n10-scanout-byte-order-dominance.patch',
     'cce5604bd0525ad6a111af86dcf80c59b05eae45d5b666c1ea62c7c6ee399315',
     ('iokit/Kernel/NoteFramebuffer.cpp',)),
    ('0068-exynos9825-n10-timer-armed-scanout-test-bars.patch',
     '29f0b023436f7835306262aba339279437b41edd954aad9e1d2e747d0d0ee763',
     ('iokit/Kernel/NoteFramebuffer.cpp',)),
    ('0069-exynos9825-n10-continuous-ios-frames.patch',
     '613eda8cb2790f60bef2afc6ae16577fbb84057061a7d54bd3356e668a4e795c',
     ('iokit/Kernel/NoteFramebuffer.cpp',)),
    ('0070-exynos9825-n10-sec-ts-touch-hid.patch',
     'd3df9994b0a3d67303b9c3c86ecf807e4104a3e196080abce2e4b4267f56f772',
     ('iokit/Kernel/IOUserClient.cpp', 'iokit/Kernel/NoteFramebuffer.cpp')),
    ('0071-exynos9825-n10-touch-i2c-recover-hid-display.patch',
     '6f71d8faf932a3b42208776a2f19927f3bbfd954834e701fe7ec572a70eeb435',
     ('iokit/Kernel/NoteFramebuffer.cpp',)),
    ('0072-exynos9825-n10-touch-mode-swap-surface-trace.patch',
     'ac378704c707a6fab88df48ab7a6bb87f1b7a2eac4729ec8ef8b78689df792a7',
     ('bsd/dev/arm/systemcalls.c', 'iokit/Kernel/NoteFramebuffer.cpp', 'osfmk/arm64/bsd_arm64.c')),
    ('0073-exynos9825-n10-window300-springboard-peer.patch',
     'e7cd94e448a88de06fb072940676cb87f1aef936a6f3e2c1b42db53d875d64f9',
     ('bsd/dev/arm/systemcalls.c', 'iokit/Kernel/NoteFramebuffer.cpp', 'osfmk/arm64/bsd_arm64.c',
      'osfmk/arm64/note10/n10_dsslog.c', 'osfmk/arm64/note10/n10_wdt.c', 'osfmk/console/serial_console.c')),
    ('0074-exynos9825-n10-sbwait-bbd-iokit-trace.patch',
     '1cb95051cb4d4f0ba45213ee538661a59ef6050aa4a2c8feb0db367ab42735cd',
     ('bsd/dev/arm/systemcalls.c', 'iokit/Kernel/IOUserClient.cpp', 'iokit/Kernel/NoteFramebuffer.cpp',
      'osfmk/arm64/note10/n10_dsslog.c')),
    ('0075-exynos9825-n10-xpcpeer-lsd-blackframe.patch',
     'd50e3e89f89d2b08c908cde4414b57062f53058de2d9283d8ffdc342c30278d6',
     ('bsd/dev/arm/systemcalls.c', 'iokit/Kernel/IOUserClient.cpp', 'iokit/Kernel/NoteFramebuffer.cpp',
      'osfmk/arm64/note10/n10_dsslog.c')),
    ('0076-exynos9825-n10-tcc-sandbox-builtin-peerwhere.patch',
     'fbd562a34045c4bd9bca36fec2ca37591100b540d829a9956097e3aae0b49ec7',
     ('bsd/dev/arm/systemcalls.c', 'osfmk/arm64/bsd_arm64.c', 'security/mac_base.c')),
    ('0077-exynos9825-n10-lsd-prio-floor-policy-done.patch',
     '3a6842dfd6b31496bcc590ef9ca6cd56a45078aff2dc606def4bca3e19f8ec5f',
     ('bsd/dev/arm/systemcalls.c', 'osfmk/arm64/note10/n10_wdt.c', 'osfmk/kern/thread_policy.c',
      'security/mac_base.c')),
    ('0078-exynos9825-n10-smp-cluster0-psci.patch',
     'cc2822fd2c007d48c8d4a1b4049a6f2e93d23c1d2b6a1c06910b4f248b8fc272',
     ('bsd/dev/arm/systemcalls.c', 'bsd/kern/bsd_init.c', 'osfmk/arm/cpu_common.c', 'osfmk/arm64/cpu.c',
      'osfmk/arm64/note10/n10_dsslog.c', 'osfmk/arm64/note10/n10_smp.c', 'osfmk/arm64/note10/n10_wdt.c',
      'osfmk/arm64/start.s', 'osfmk/conf/files.arm64', 'pexpert/arm/pe_note10_bootstrap.c',
      'pexpert/arm/pe_note10_irq.c', 'pexpert/pexpert/arm64/EXYNOS9825.h')),
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
    """Stage hfs-627.100.6, then apply 0021..0031 once after the MOCKFS overlay and before configure."""
    check_patches()
    require(all(not (source / d).exists() for d in STAGED_DIRS), 'fresh source without staged HFS required')
    run(['bash', PATCHES / STAGE_HFS[0]], source, output / 'ios16-stage-hfs.log')
    require(all((source / d).is_dir() for d in STAGED_DIRS) and (source / 'bsd/n10_hfs/TargetConditionals.h').is_file(),
            'staged HFS sources missing')
    command = ['git', '-c', 'core.autocrlf=false', 'apply']
    for n, (name, _, _) in enumerate(OVERLAY):
        run([*command, '--check', PATCHES / name], source, output / ('ios16-check-' + str(n + 21) + '.log'))
        run([*command, PATCHES / name], source, output / ('ios16-patch-' + str(n + 21) + '.log'))
    # Whole-file source overlay (note10/xnu26/overlay mirrors the XNU tree), copied after the patches.
    copied = [p.relative_to(FILE_OVERLAY).as_posix() for p in sorted(FILE_OVERLAY.rglob('*')) if p.is_file()]
    for rel in copied:
        (source / rel).parent.mkdir(parents=True, exist_ok=True)
        (source / rel).write_bytes((FILE_OVERLAY / rel).read_bytes())
    files = sorted({rel for _, _, rels in OVERLAY for rel in rels} | set(copied))
    observation = dict(schema='note10-v342-ios16-root-overlay-v1', kind=KIND,
                       stage_hfs=dict(script=STAGE_HFS[0], sha256=STAGE_HFS[1]),
                       patches=[dict(patch=name, patch_sha256=patch_sha) for name, patch_sha, _ in OVERLAY],
                       postimage_sha256={rel: sha((source / rel).read_bytes()) for rel in files})
    with (output / 'ios16-root-overlay.json').open('x') as stream:
        stream.write(json.dumps(observation, sort_keys=True, indent=2) + '\n')
    return observation
