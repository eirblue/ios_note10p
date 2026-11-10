"""One fresh full Linux Image; carry accepted host evidence without replay."""
import argparse
import base64
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
import uuid
import zipfile
import v154_linux_prepare as p

SETTINGS = {'BLK_DEV_INITRD': 'y', 'INITRAMFS_FORCE': 'y', 'RD_GZIP': 'y',
            'DEVTMPFS': 'y', 'DEVTMPFS_MOUNT': 'y', 'PROC_FS': 'y', 'SYSFS': 'y',
            'PRINTK': 'y', 'BINFMT_ELF': 'y', 'EXYNOS_REBOOT': 'y', 'SEC_REBOOT': 'y',
            'LOG_BUF_SHIFT': '21', 'STACK_VALIDATION': 'n', 'FTRACE_MCOUNT_RECORD': 'n',
            'LOCALVERSION_AUTO': 'n', 'LOCALVERSION': '"-v154-linux-iva-mmap"', 'NOTE10_V154_LINUX_DIAGNOSTIC': 'y',
            'NOTE10_BUILTIN_INIT_ROUTE': 'y', 'CMDLINE': '"rdinit=/init"',
            'CMDLINE_EXTEND': 'y', 'CMDLINE_FORCE': 'n', 'CMDLINE_FROM_BOOTLOADER': 'n',
            'KEXEC': 'n', 'KEXEC_JUMP': 'n', 'INITRAMFS_COMPRESSION_NONE': 'y',
            'INITRAMFS_COMPRESSION_GZIP': 'n', 'INITRAMFS_COMPRESSION_BZIP2': 'n',
            'INITRAMFS_COMPRESSION_LZMA': 'n', 'INITRAMFS_COMPRESSION_XZ': 'n',
            'INITRAMFS_COMPRESSION_LZO': 'n', 'INITRAMFS_COMPRESSION_LZ4': 'n'}
TARGETS = tuple(name[:-2]+'.o' for name in p.FINAL_NATIVE if name.endswith('.c'))
PROOF_TARGETS = (*TARGETS, 'drivers/misc/v154_linux_return.o', 'init/main.o')
DEPENDENCIES = {
    'drivers/vision/iva/iva_ctrl.o': ('v145_iva_sidecar.inc', 'v144_iva_buffer.h', 'iva_mem.h', 'iva_ctrl.h', 'linux/kref.h', 'linux/exynos_iovmm.h'),
    'drivers/iommu/exynos-iommu.o': ('exynos-iommu.h', 'linux/exynos_iovmm.h', 'linux/iommu.h', 'linux/rcupdate.h'),
    'drivers/iommu/exynos-iovmm.o': ('exynos-iommu.h', 'linux/exynos_iovmm.h', 'linux/iommu.h'),
    'drivers/misc/v154_linux_return.o': ('v154_linux_id.h', 'note10_auto_return.c', 'builtin_init_route.c')} 
MAX_MEMBER = 64*1024*1024
MAX_TOTAL = 128*1024*1024
BUILD_LOGS = ('00-clang-version.log', '01-probe-compile.log', '02-stock-defconfig.log',
              '03-diagnostic-settings.log', '04-effective-defconfig.log', '05-one-Image.log')
SUCCESS_MEMBERS = tuple(sorted(('members.json', 'result.json', 'Image', 'minimal-init.elf', 'initramfs.cpio',
                               'actual-effective.config', 'generated-autoconf.h', *BUILD_LOGS,
                               *('native-source/'+name for name in p.FINAL_NATIVE),
                               *('commands/'+Path(name).with_name('.'+Path(name).name+'.cmd').as_posix() for name in PROOF_TARGETS))))


MAKE_ENVIRONMENT = {'PLATFORM_VERSION': '11', 'ANDROID_MAJOR_VERSION': 'r'}
DHD_SYMBOL = 'dhd_smmu_fault_handler'
V154_HOST_RESULT_SHA = '28c7d96f68d1a49f6ccdd3dc0219747b46455ddf9b173992bc23cd77bf96a439'
V155_HOST_SCHEMA = 'note10-v155-linux-make-environment-host-once-v1'
V157_CONTEXT_SCHEMA = 'note10-v157-linux-builtin-preexec-public-input-v1'
V157_BUILD_SCHEMA = 'note10-v157-linux-builtin-preexec-build-v1'
V157_OUTPUT = 'note10/private/v157-ci-linux-builtin-preexec'
V157_OBSERVER = 'v157_builtin_init_observation.inc'
V157_NATIVE = ('init/main.c', 'drivers/misc/v154_linux_return.c', 'drivers/misc/'+V157_OBSERVER)
V157_SOURCE = {
    'note10/device_test/v157_splice_observation.py': '212d3bb320767b54d686948c6d0974ffb1d389ed4a3a9f212ce12d7280bd3f34',
    'note10/device_test/'+V157_OBSERVER: 'f9b97fa886ff303657b73b68276af4e31ee770fc0a6c8f1ff4392cbf4d675498',
}
V157_STOCK = {
    'include/linux/cred.h': '3892bf98b97ae4a937b13859cca740fbdd8fef86febeaf603e1265ad0f7993ad',
    'include/linux/dcache.h': '4074fdbd7713fe68b8f68e61150019f3adb5542552c29cc48a741ba3a2d55e06',
    'include/linux/err.h': 'eaea697160bdfe002ba6b7b7b46a20a44a7afd6b2dd6faf587fa1122848d5eb6',
    'include/linux/fcntl.h': 'c683f32678ab06ad389c2a6c48307eb9d7dfbd3b3b04ec79721e2984cde0d461',
    'include/linux/fs.h': '28f33eb4c958db5d8983458c2ed76a78383a51f8fc6a023f66f68d062f6ea34f',
    'include/linux/namei.h': '12d3d48d427bdcd07d484231a19bf78b3060bb120ebac507fc4e44e6b11c84bf',
    'include/linux/path.h': '478f1703984df9260834133726d1cbe32adf17faf776b202c990d9eb94cd1ca8',
    'include/linux/stat.h': '959af62ca017e2d65c3d7e606beeaef5f14b7432207e2f8f34e3687770fef1dc',
    'include/uapi/asm-generic/fcntl.h': 'fc4998b97bb644acb07c55a4dade3bdcb89f6f82d6c24c305d68858b3dce88e1',
    'include/uapi/linux/stat.h': '2e5c5b2179e313d91995c3c5e8bd1303dc2cec3915424cd0ce2b8b1f31bec819',
    'fs/namei.c': 'ab04c33e3e6af5e235151e41600cb04885072f638d1781d9925cb714a89804e4',
    'fs/open.c': '49845ac0e8c34fe9d34441081484a10ad1f8f85595023cc7cfb770bd6d5baff7',
    'init/do_mounts.c': '61282d08f8d6f10915230371712d9b32b27345550b6028da28ceb6f18f8ddb84',
}
V157_SPLICE_PASS = dict(schema='note10-v157-splice-host-once-v1', passed=True, fixture_count=1, old_tests_count=0,
                        result_sha256='8ca879bb56e4eb0c1b757fbd02809d36d1eb7f174b951a9f19bc5562128f24d6',
                        review_sha256='b0ab83fa16c1bca03b15881ad99b8cf09590af38b300fe297b7995beed143522')
V157_RETAINED_ENV_SHA = '476648d2692da950a0ea6afce3cb216a67b6a386a96baddf95e82e1092401439'
V158_CONTEXT_SCHEMA = 'note10-v158-linux-builtin-entry-public-input-v1'
V158_BUILD_SCHEMA = 'note10-v158-linux-builtin-entry-build-v1'
V158_OUTPUT = 'note10/private/v158-ci-linux-builtin-entry'
V158_PID1 = 'note10/device_test/v158_builtin_init.c'
V158_PID1_SHA = 'd231c5fdf2d99b07054f3613f0376236bb99864afa8a6b64e5ea6f71122d7ebe'
V158_PID1_ID = b'N10MININIT2:N158PID1'
V158_ENTRY_PASS = dict(schema='note10-v158-entry-only-pid1-host-once-v1', passed=True, compiler_count=1, fixture_count=1,
                       old_tests_count=0, result_sha256='96022f17fa5e32b237107f131690d800bac811b00acb9ab0b3765c53a5e0e98d',
                       review_sha256='6f507f686f966cf5a8d63ebb19b52a81a4cba05ad10aa21159e7d60399550a1a')
V158_STOCK = {
    'arch/arm64/include/uapi/asm/fcntl.h': '6d43602d5db08d4f4acda256ba09009c43b9d93b9283ad9dd75ce7c9dd2b6864',
    'arch/arm64/include/uapi/asm/unistd.h': '252cf55cbdece5ef96f6e834bc9f48d043008038971b9ae4bd9d6bfd4dfb9fc1',
    'include/uapi/linux/fcntl.h': '23dec401241e680af2106be32573aa568aaf6dd76dee2a4593705d9319648355',
    'fs/select.c': '546b19b69238e5336403f253190a609b65922f98d99a341066352373ff5d4e74',
}
V159_CONTEXT_SCHEMA = 'note10-v159-linux-rootfs-materialization-public-input-v1'
V159_BUILD_SCHEMA = 'note10-v159-linux-rootfs-materialization-build-v1'
V159_OUTPUT = 'note10/private/v159-ci-linux-rootfs-materialization'
V159_SOURCE = {
    'note10/device_test/v159_rootfs_materialization.py': '2495fbdbf799b5686a603e1ae33116433f7ae6c885f41d250a14963d71173644',
    'note10/device_test/note10_rootfs_snapshot.h': '9844788efebdcc5793bc0f50d9abc34ec0f396ac0e9431fb8f875aca604bfaf1',
}
V159_NATIVE = ('init/initramfs.c', 'include/linux/note10_rootfs_snapshot.h')
V159_ROOTFS_PASS = dict(schema='note10-v159-rootfs-materialization-host-once-v1', passed=True, compiler_count=0,
                        fixture_count=1, old_tests_count=0,
                        result_sha256='69469db57e58b082ce092d4195fb9ed44c8c0370aa1b8a934c78c3e35321387f',
                        review_sha256='28f64654d500eca1b1aecfdeb3022fded74bb2200505d1faf1ffeda8d3241fba')
V160_CONTEXT_SCHEMA = 'note10-v160-linux-rootfs-relocation-public-input-v1'
V160_BUILD_SCHEMA = 'note10-v160-linux-rootfs-relocation-build-v1'
V160_OUTPUT = 'note10/private/v160-ci-linux-rootfs-relocation'
V160_SCOPE = 'stock-linux-rootfs-relocation-proof-and-materialization-observation-no-XNU'
V160_SOURCE = {'note10/device_test/v160_rootfs_relocation.py':
               'dcd37fdf338eeb904aac1576b52ad381c97fbec7d6ab8eb683f35818826c24fe'}
V160_STOCK = {
    'arch/arm64/Makefile': '621178b0a638d591aeec814215dcd7c8ab1bf69137d7255beb6ffb05ce315d5d',
    'arch/arm64/kernel/head.S': '015d1af89b5821df0b0c8abef91209fca6178b123cac6d5d89ff5accff605908',
    'arch/arm64/kernel/vmlinux.lds.S': '7d1e35dbdd36858f29794c16efcc197ba7950e8cf265277288c66d155062baec',
    'arch/arm64/kernel/image.h': 'f09a9bc7abd5c49191567c05c281ec5637d67af627ed9e217bb8cb25dff80054',
    'arch/arm64/include/asm/elf.h': '0c1e6515d233640afe9c86782c41cb40ddae83f7e7b411f5e98505ad3c6b2e4e',
    'arch/arm64/boot/Makefile': '5393fe51861fb4cb12e56049cec668246218e5351c4af205a16bdaccf8f8e9a5',
}
V160_RELOCATION_PASS = dict(schema='note10-v160-rootfs-relocation-host-once-v1', passed=True, compiler_count=0,
                            fixture_count=1, old_tests_count=0,
                            result_sha256='22b52b376c89ae7605ab9296d44bace6b2f4a4c397e15b846fa338074504b89e', review_sha256='5b7f9aac2bd9252a08dc896bd81a565c00490fd829a83677e4c76c87da922272')
V161_CONTEXT_SCHEMA = 'note10-v161-linux-diagnostic-initramfs-public-input-v1'
V161_BUILD_SCHEMA = 'note10-v161-linux-diagnostic-initramfs-build-v1'
V161_OUTPUT = 'note10/private/v161-ci-linux-diagnostic-initramfs'
V161_SCOPE = 'stock-linux-diagnostic-initramfs-force-and-entry-observation-no-XNU'
V161_SOURCE = {'note10/device_test/v161_initramfs_force.py':
               'b9f6254bfb47c5cf4c453b0d92d1789d87c586746e38e9b0aef074b2673846d5'}
V161_ROOTFS_SHA = '3f4a3808b35ce015274479ab6dcb1c6be76e00b43f50ed478b2696e364a51667'
V161_CONFIG = ('NOTE10_V154_LINUX_DIAGNOSTIC', 'NOTE10_BUILTIN_INIT_ROUTE', 'INITRAMFS_FORCE')
V161_PARSER_PASS = dict(schema='note10-v161-diagnostic-initramfs-parser-host-once-v1', passed=True,
                        prepare_count=1, compiler_count=1, fixture_count=1, old_tests_count=0,
                        result_sha256='ddd3b2570f4e7956888f627c2710a03dbc59482866272cddf7fbabfc71cb18c6', review_sha256='e1bd2864f67d10eca8e47c3247a3e0df4d88b046bffcc33fee847b7a62427007')


def observer_sources(revision):
    expected = dict(V157_SOURCE)
    if revision in ('v158', 'v159', 'v160', 'v161'):
        expected[V158_PID1] = V158_PID1_SHA
    if revision in ('v159', 'v160', 'v161'):
        expected.update(V159_SOURCE)
    if revision in ('v160', 'v161'):
        expected.update(V160_SOURCE)
    if revision == 'v161':
        expected.update(V161_SOURCE)
    buffers = {name: p.ordinary(p.ROOT/name) for name in expected}
    if {name: p.sha(raw) for name, raw in buffers.items()} != expected:
        raise ValueError('reviewed observer/PID1 source bytes differ')
    return buffers


def source_pins(revision):
    pins = p.source_pins()
    if revision != 'v155':
        pins.update({name: p.sha(raw) for name, raw in observer_sources(revision).items()})
    return pins


def load_sources(pins, revision):
    if revision == 'v155':
        return p.load_sources(pins)
    buffers = observer_sources(revision)
    if any(pins.get(name) != p.sha(raw) for name, raw in buffers.items()):
        raise ValueError('observer/PID1 context source pins differ')
    return dict(p.load_sources({name: pin for name, pin in pins.items() if name not in buffers}), **buffers)

def validate_context(context, revision='v155'):
    if revision not in ('v155', 'v157', 'v158', 'v159', 'v160', 'v161'):
        raise ValueError('unsupported Linux diagnostic build revision')
    observer = revision != 'v155'
    schemas = {'v155': p.CONTEXT_SCHEMA, 'v157': V157_CONTEXT_SCHEMA, 'v158': V158_CONTEXT_SCHEMA,
               'v159': V159_CONTEXT_SCHEMA, 'v160': V160_CONTEXT_SCHEMA, 'v161': V161_CONTEXT_SCHEMA}
    scopes = {'v155': 'stock-linux-iva-mmap-denial-no-XNU', 'v157': 'stock-linux-builtin-preexec-observation-no-XNU',
              'v158': 'stock-linux-builtin-entry-only-no-userspace-IVA-probe-or-XNU',
              'v159': 'stock-linux-rootfs-materialization-observation-no-XNU', 'v160': V160_SCOPE,
              'v161': V161_SCOPE}
    fields = {'schema', 'scope', 'source_sha256', 'host_pass', 'kernel'}
    if observer:
        fields.add('build_revision')
    if (type(context) is not dict or set(context) != fields or
        context['schema'] != schemas[revision] or context['scope'] != scopes[revision] or
        (observer and context['build_revision'] != revision) or context['source_sha256'] != source_pins(revision) or
        context['kernel'] != dict(commit=p.COMMIT, archive_sha256=p.ARCHIVE_SHA, defconfig_sha256=p.DEFCONFIG_SHA)):
        raise ValueError('exact final public context/source/kernel required')
    passes = context['host_pass']
    pass_fields = {'accepted', 'new', 'retained_v154_host_result_sha256'}
    if observer:
        pass_fields.add('v157_splice')
    if revision in ('v158', 'v159', 'v160', 'v161'):
        pass_fields.add('v158_entry')
    if revision in ('v159', 'v160', 'v161'):
        pass_fields.add('v159_rootfs')
    if revision in ('v160', 'v161'):
        pass_fields.add('v160_relocation')
    if revision == 'v161':
        pass_fields.add('v161_parser')
    if (type(passes) is not dict or set(passes) != pass_fields or
        not p.same(passes['accepted'], p.HOST_PASS) or passes['retained_v154_host_result_sha256'] != V154_HOST_RESULT_SHA):
        raise ValueError('exact accepted host and carried v154 PASS required')
    environment = passes['new']
    if (type(environment) is not dict or
        set(environment) != {'schema', 'passed', 'result_sha256', 'compiler_count', 'fixture_count', 'old_tests_count'} or
        environment['schema'] != V155_HOST_SCHEMA or environment['passed'] is not True or
        any(type(environment[key]) is not int or environment[key] != 0
            for key in ('compiler_count', 'fixture_count', 'old_tests_count'))):
        raise ValueError('one new v155 environment host PASS required')
    p.hexid(environment['result_sha256'])
    if observer and (environment['result_sha256'] != V157_RETAINED_ENV_SHA or
                    not p.same(passes['v157_splice'], V157_SPLICE_PASS)):
        raise ValueError('exact retained v155 environment and v157 splice PASS required')
    if revision in ('v158', 'v159', 'v160', 'v161') and not p.same(passes['v158_entry'], V158_ENTRY_PASS):
        raise ValueError('exact reviewed v158 entry-only PID1 host PASS required')
    if revision in ('v159', 'v160', 'v161') and not p.same(passes['v159_rootfs'], V159_ROOTFS_PASS):
        raise ValueError('exact reviewed v159 rootfs metadata host PASS required')
    if revision in ('v160', 'v161') and not p.same(passes['v160_relocation'], V160_RELOCATION_PASS):
        raise ValueError('exact reviewed v160 relocation host PASS required')
    if revision == 'v161' and not p.same(passes['v161_parser'], V161_PARSER_PASS):
        raise ValueError('exact reviewed v161 diagnostic parser host PASS required')
    return context


def ci_guard(head, env):
    p.hexid(head, 40)
    if (env.get('GITHUB_SHA') != head or env.get('GITHUB_WORKFLOW_SHA') != head or
        env.get('GITHUB_RUN_ATTEMPT') != '1' or env.get('GITHUB_JOB') != p.JOB or
        env.get('GITHUB_REPOSITORY') != p.REPOSITORY or
        env.get('GITHUB_WORKFLOW_REF') != p.REPOSITORY+'/'+p.WORKFLOW+'@refs/heads/main'):
        raise ValueError('exact reviewed HEAD/workflow/attempt1/job required')
    if re.fullmatch('[1-9][0-9]*', env.get('GITHUB_RUN_ID', '')) is None:
        raise ValueError('actual CI run required')


def public_context(encoded, revision='v155'):
    codec = p.module('v135_metadata', {'note10/device_test/v135_metadata.py': p.ordinary(p.ROOT/'note10/device_test/v135_metadata.py')})
    return validate_context(codec.decode_public(encoded), revision)


def recipient(encoded):
    if type(encoded) is not str or len(encoded) > 8192:
        raise ValueError('bounded public recipient required')
    raw = base64.b64decode(encoded, validate=True)
    if (p.sha(raw) != p.PUBLIC_PEM_SHA or b'PRIVATE KEY' in raw or
        not raw.startswith(b'-----BEGIN PUBLIC KEY-----\n') or not raw.endswith(b'-----END PUBLIC KEY-----\n')):
        raise ValueError('original public PEM required')
    if p.sha(base64.b64decode(b''.join(raw.splitlines()[1:-1]), validate=True)) != p.RECIPIENT:
        raise ValueError('original public SPKI required')


def config_values(raw):
    values = {}
    for line in raw.decode().splitlines():
        if line.startswith('CONFIG_') and '=' in line:
            key, value = line[7:].split('=', 1)
        elif line.startswith('# CONFIG_') and line.endswith(' is not set'):
            key, value = line[9:-11], 'n'
        else:
            continue
        if key in values:
            raise ValueError('duplicate generated configuration')
        values[key] = value
    return values


def check_config(raw, settings):
    values = config_values(raw)
    for key, value in dict(p.REQUIRED_CONFIG, **settings).items():
        if values.get(key, 'n') != value:
            raise ValueError('effective stock/diagnostic setting differs: '+key)
    if any(key.startswith('NOTE10_') and value != 'n' and key not in SETTINGS for key, value in values.items()):
        raise ValueError('legacy NOTE10 diagnostic/transfer profile prohibited')
    return values


def check_image(raw, archive, identity, symbols, pid1_marker=b'N154IVA'):
    if not 64 <= len(raw) <= p.IMAGE_LIMIT or raw[56:60] != b'ARM\x64':
        raise ValueError('bounded ARM64 Image header required')
    linked_extent = struct.unpack_from('<Q', raw, 16)[0]
    if (not 0 < linked_extent <= p.IMAGE_LIMIT or
        raw.count(p.CYCLE_MARKER+b'\0') != 1 or raw.count(archive) != 1):
        raise ValueError('bounded ARM64 Image/cycle/CPIO proof differs')
    if any(marker not in raw for marker in (pid1_marker, b'N154ARM', b'N10RET1', b'N10ROUTE2', b'N10BOOTLINK2', b'N10MININIT2', identity.encode())):
        raise ValueError('builtin diagnostic/return markers missing')
    if any(marker in raw for marker in (b'N10XNU141', b'N10OWNED', b'N10PAYLOAD', b'N10SHASTREAM1', b'N10SHACTL1')):
        raise ValueError('legacy transfer/diagnostic payload found')
    table = {}
    for line in symbols.splitlines():
        match = re.fullmatch(r'([0-9a-fA-F]+)\s+\S\s+(\S+)', line)
        if match is None:
            continue
        address, name = match.groups()
        if name in ('_text', '__initramfs_start'):
            if name in table:
                raise ValueError('duplicate Image layout symbol')
            table[name] = int(address, 16)
    if set(table) != {'_text', '__initramfs_start'}:
        raise ValueError('actual linked initramfs symbols required')
    offset = table['__initramfs_start']-table['_text']
    end = offset+len(archive)
    if offset < 0 or end > min(linked_extent, len(raw)) or raw[offset:end] != archive:
        raise ValueError('actual linked CPIO placement differs')
    return dict(Image_bytes=len(raw), Image_sha256=p.sha(raw), linked_extent=linked_extent,
                cycle_offset=raw.index(p.CYCLE_MARKER+b'\0'), initramfs_offset=offset,
                initramfs_bytes=len(archive), initramfs_sha256=p.sha(archive), linked_symbols=table)


def check_dhd_symbol(symbols):
    rows = []
    for line in symbols.splitlines():
        fields = line.split()
        if fields and fields[-1] == DHD_SYMBOL:
            rows.append(fields)
    if len(rows) != 1 or len(rows[0]) != 3:
        raise ValueError('exactly one defined DHD fault handler required')
    address, kind, name = rows[0]
    if kind not in ('T', 't') or not re.fullmatch(r'[0-9a-fA-F]{1,16}', address) or int(address, 16) == 0:
        raise ValueError('DHD fault handler must be a defined text symbol')
    return dict(name=name, address=int(address, 16), kind=kind)


def run_command(argv, log, timeout):
    env = dict(os.environ, **MAKE_ENVIRONMENT)
    return subprocess.run(list(map(str, argv)), cwd=p.ROOT, stdout=log, stderr=subprocess.STDOUT,
                          timeout=timeout, env=env)


def install_v157(source, buffers, preparation):
    for name, pin in V157_STOCK.items():
        if p.sha(p.ordinary(source/name)) != pin:
            raise ValueError('v157 pinned stock observation API differs: '+name)
    main, return_tu, observer = (source/name for name in V157_NATIVE)
    if observer.exists() or observer.is_symlink():
        raise ValueError('fresh v157 observer include required')
    splice = p.module('v157_splice_observation', buffers)
    main_bytes, return_bytes = splice.prepare(p.ordinary(main), p.ordinary(return_tu))
    observer_bytes = buffers['note10/device_test/'+V157_OBSERVER]
    for path, raw in zip((main, return_tu, observer), (main_bytes, return_bytes, observer_bytes)):
        path.write_bytes(raw)
        preparation['installed_sha256'][path.relative_to(source).as_posix()] = p.sha(raw)


def install_v159(source, buffers, preparation):
    helper = p.module('v159_rootfs_materialization', buffers)
    if (source/V159_NATIVE[1]).exists() or (source/V159_NATIVE[1]).is_symlink():
        raise ValueError('fresh v159 rootfs snapshot header required')
    outputs = helper.prepare(p.ordinary(source/'init/initramfs.c'),
                             p.ordinary(source/'drivers/misc'/V157_OBSERVER),
                             buffers['note10/device_test/note10_rootfs_snapshot.h'])
    if set(outputs) != {*V159_NATIVE, 'drivers/misc/'+V157_OBSERVER}:
        raise ValueError('exact v159 rootfs transformation outputs required')
    for name, raw in outputs.items():
        target = source/name
        if target.resolve() != target or not target.is_relative_to(source):
            raise ValueError('unsafe rootfs transformation output')
        target.write_bytes(raw)
        preparation['installed_sha256'][name] = p.sha(raw)
    return helper


def install_v161(source, buffers, preparation):
    helper = p.module('v161_initramfs_force', buffers)
    target = source/'init/initramfs.c'
    modified = helper.prepare(p.ordinary(target))
    if p.sha(modified) != V161_ROOTFS_SHA:
        raise ValueError('exact reviewed v161 parser output differs')
    target.write_bytes(modified)
    preparation['installed_sha256']['init/initramfs.c'] = V161_ROOTFS_SHA


def v157_link_proof(raw, symbols):
    name = 'n157_builtin_init_observe'
    rows = [line.split() for line in symbols.splitlines() if line.split()[-1:] == [name]]
    if (len(rows) != 1 or len(rows[0]) != 3 or rows[0][1] not in ('T', 't') or
        not re.fullmatch('[0-9a-fA-F]{1,16}', rows[0][0]) or int(rows[0][0], 16) == 0 or
        raw.count(b'N157PRE1 id=') != 1):
        raise ValueError('one same-Image v157 observer and marker required')
    return dict(marker='N157PRE1', symbol=name, linked_address=int(rows[0][0], 16),
                original_exec_retained=True, device_ready=False)


def v158_pid1_proof(elf, archive, init):
    if V158_PID1_ID not in elf or any(marker in elf for marker in (b'N154IVA', b'/dev/iva_ctl')):
        raise ValueError('entry-only v158 ELF identity required')
    phoff, = struct.unpack_from('<Q', elf, 32)
    phsize, count = struct.unpack_from('<HH', elf, 54)
    entry = init['entry']
    offsets = []
    for i in range(count):
        kind, flags, pos, va, _, file_size, _, _ = struct.unpack_from('<IIQQQQQQ', elf, phoff+i*phsize)
        if kind == 1 and flags & 1 and va <= entry < va+file_size:
            offsets.append(pos+entry-va)
    if entry % 4 or len(offsets) != 1:
        raise ValueError('unique file-backed v158 AArch64 entry required')
    pos = 0
    for name in (b'dev', b'dev/console', b'dev/kmsg'):
        raw = archive[pos:pos+110]
        if re.fullmatch(rb'070701[0-9a-fA-F]{104}', raw) is None:
            raise ValueError('v158 packaged kmsg newc header required')
        fields = [int(raw[i:i+8], 16) for i in range(6, 110, 8)]
        name_end = pos+110+fields[11]
        if fields[6] or archive[pos+110:name_end] != name+b'\0':
            raise ValueError('v158 packaged kmsg path differs')
        pos = (name_end+3)&~3
    if (fields[1], fields[2], fields[3], fields[9], fields[10]) != (0o020600, 0, 0, 1, 11):
        raise ValueError('v158 packaged kmsg must be root-owned character device 1:11')
    return dict(schema='note10-v158-entry-only-pid1-evidence-v1', source_sha256=V158_PID1_SHA,
                elf_sha256=init['sha256'], file_backed_entry_offset=offsets[0],
                packaged_kmsg=dict(major=1, minor=11, mode='020600'), marker='N158PID1',
                source_declared_syscalls=[56, 57, 64, 73], device_ready=False)


def producer_output(output, revision):
    out = p.private(output)
    fixed = {'v157': p.ROOT/V157_OUTPUT, 'v158': p.ROOT/V158_OUTPUT,
             'v159': p.ROOT/V159_OUTPUT, 'v160': p.ROOT/V160_OUTPUT, 'v161': p.ROOT/V161_OUTPUT}
    if (revision in fixed and out != fixed[revision]) or (revision == 'v155' and out in fixed.values()):
        raise ValueError('exact revision-specific producer output required')
    return out


def spent_output(out, revision):
    paths = (out, out.with_name(out.name+'-work'), out.with_name(out.name+'-source.tar.gz'))
    if revision != 'v155':
        paths += (out.with_suffix('.zip'), out.with_suffix('.n10sealed'))
    return any(path.exists() or path.is_symlink() for path in paths)


def run_build(output, context, head, jobs=4, revision='v155'):
    validate_context(context, revision)
    if sys.platform != 'linux' or type(jobs) is not int or jobs != 4:
        raise ValueError('Linux jobs4 only')
    out = producer_output(output, revision)
    observer = revision != 'v155'
    entry_only = revision in ('v158', 'v159', 'v160', 'v161')
    rootfs_observation = revision in ('v159', 'v160', 'v161')
    work = out.with_name(out.name+'-work')
    archive = out.with_name(out.name+'-source.tar.gz')
    if spent_output(out, revision):
        raise ValueError('fresh output/work/archive required; never retry')
    buffers = load_sources(context['source_sha256'], revision)
    out.mkdir(parents=True)
    schema = {'v155': p.BUILD_SCHEMA, 'v157': V157_BUILD_SCHEMA, 'v158': V158_BUILD_SCHEMA,
              'v159': V159_BUILD_SCHEMA, 'v160': V160_BUILD_SCHEMA, 'v161': V161_BUILD_SCHEMA}[revision]
    result = dict(schema=schema, version=revision if observer else 'v154', build_revision=revision, passed=False, source_head=head,
                  make_environment=dict(MAKE_ENVIRONMENT),
                  source_sha256=context['source_sha256'], public_input=context,
                  build_evidence_id=uuid.uuid4().hex, stages={}, XNU_execution_allowed=False,
                  physical_ready=False, internal_kexec_limit=0, full_Image_build_attempts=0,
                  separate_native_object_builds=0, old_tests_count=0,
                  ci_context=dict(run_id=os.environ.get('GITHUB_RUN_ID'), run_attempt=os.environ.get('GITHUB_RUN_ATTEMPT'),
                                  job=os.environ.get('GITHUB_JOB'), repository=os.environ.get('GITHUB_REPOSITORY'),
                                  workflow_sha=os.environ.get('GITHUB_WORKFLOW_SHA')))
    def persist():
        p.save(out/'result.json', result)
    def run(argv, label, timeout=600):
        result['stages'][label] = dict(argv=list(map(str, argv)), status='started')
        persist()
        with (out/(label+'.log')).open('xb') as log:
            call = run_command(argv, log, timeout)
        result['stages'][label].update(returncode=call.returncode, status='completed')
        persist()
        if (out/(label+'.log')).stat().st_size == 0:
            (out/(label+'.log')).write_bytes(('completed rc='+str(call.returncode)+'\n').encode())
        p.ordinary(out/(label+'.log'), MAX_MEMBER)
        if call.returncode:
            raise ValueError('single build stage failed: '+label)
    persist()
    try:
        for tool in ('clang-14', 'gcc', 'make', 'aarch64-linux-gnu-gcc', 'arm-linux-gnueabi-gcc'):
            if shutil.which(tool) is None:
                raise ValueError('required tool unavailable: '+tool)
        run(['clang-14', '--version'], '00-clang-version')
        if re.search(rb'\bversion 14\.', p.ordinary(out/'00-clang-version.log')) is None:
            raise ValueError('actual clang14 toolchain required')
        archive_module = p.module('v130_archive', buffers)
        result['stages']['source-acquire'] = dict(attempts=1, status='started'); persist()
        archive_module.acquire(archive)
        if len(p.ordinary(archive, p.ARCHIVE_BYTES)) != p.ARCHIVE_BYTES or p.sha(archive.read_bytes()) != p.ARCHIVE_SHA:
            raise ValueError('stock archive pin differs')
        work.mkdir()
        source = archive_module.extract(archive, work/'source')
        objects = work/'objects'; objects.mkdir()
        if p.sha(p.ordinary(source/'arch/arm64/configs'/p.DEFCONFIG)) != p.DEFCONFIG_SHA:
            raise ValueError('stock defconfig differs')
        result['stages']['source-acquire']['status'] = 'completed'
        result['preparation'] = p.install(source, result['build_evidence_id'], buffers); persist()
        if observer:
            install_v157(source, buffers, result['preparation']); persist()
        if rootfs_observation:
            rootfs_helper = install_v159(source, buffers, result['preparation']); persist()
        if revision == 'v161':
            install_v161(source, buffers, result['preparation']); persist()
        if revision in ('v160', 'v161'):
            for name, pin in V160_STOCK.items():
                if p.sha(p.ordinary(source/name)) != pin:
                    raise ValueError('v160 pinned stock relocation semantics differ: '+name)
            relocation_helper = p.module('v160_rootfs_relocation', buffers)
        for name in (*p.FINAL_NATIVE, *(V157_NATIVE if observer else ()), *(V159_NATIVE if rootfs_observation else ())):
            dest = out/'native-source'/name; dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(p.ordinary(source/name))
        identity = result['build_evidence_id']
        if entry_only:
            for name, pin in V158_STOCK.items():
                if p.sha(p.ordinary(source/name)) != pin:
                    raise ValueError('v158 pinned stock PID1 ABI differs: '+name)
            pid1 = work/Path(V158_PID1).name
            pid1.write_bytes(buffers[V158_PID1])
            run(['aarch64-linux-gnu-gcc', '-std=c11', '-Os', '-ffreestanding', '-fno-stack-protector',
                 '-fno-pie', '-no-pie', '-nostdlib', '-static', '-Wl,-e,_start', '-Wall', '-Wextra', '-Werror',
                 '-DN158_BUILD_ID="'+identity+'"', pid1, '-o', out/'minimal-init.elf'], '01-pid1-compile')
        else:
            run(['aarch64-linux-gnu-gcc', '-std=c11', '-O2', '-static', '-fno-stack-protector',
                 '-Wall', '-Wextra', '-Werror', '-DN154_BUILD_ID="'+identity+'"',
                 p.ROOT/'note10/device_test/v154_linux_probe.c', '-o', out/'minimal-init.elf'], '01-probe-compile')
        route = p.module('builtin_init_route', buffers)
        init = p.ordinary(out/'minimal-init.elf', 1024*1024)
        result['minimal_init'] = route.elf_manifest(init)
        cpio = route.cpio(init); (out/'initramfs.cpio').write_bytes(cpio)
        if entry_only:
            result['entry_only_pid1'] = v158_pid1_proof(init, cpio, result['minimal_init'])
        make = ['make', '-C', str(source), 'O='+str(objects), 'ARCH=arm64', 'CC=clang-14',
                'CROSS_COMPILE=aarch64-linux-gnu-', 'CLANG_TRIPLE=aarch64-linux-gnu-',
                'CROSS_COMPILE_ARM32=arm-linux-gnueabi-', 'GCC_TOOLCHAIN_DIR=/usr/aarch64-linux-gnu/bin/',
                'HOSTCC=gcc', 'HOSTCFLAGS=-Wno-error=deprecated-declarations', 'KCFLAGS=-gdwarf-4']
        run([*make, p.DEFCONFIG], '02-stock-defconfig')
        check_config(p.ordinary(objects/'.config'), {})
        settings = dict(SETTINGS, INITRAMFS_SOURCE='"'+str(out/'initramfs.cpio')+'"')
        if revision == 'v161':
            settings['LOCALVERSION'] = '"-v161-linux-diagnostic-initramfs"'
        elif revision == 'v160':
            settings['LOCALVERSION'] = '"-v160-linux-rootfs-relocation"'
        elif rootfs_observation:
            settings['LOCALVERSION'] = '"-v159-linux-rootfs-materialization"'
        elif entry_only:
            settings['LOCALVERSION'] = '"-v158-linux-builtin-entry"'
        elif observer:
            settings['LOCALVERSION'] = '"-v157-linux-builtin-preexec"'
        edits = []
        for key, value in settings.items():
            edits.extend(['--enable' if value == 'y' else '--disable', key] if value in ('y', 'n') else
                         ['--set-str', key, value[1:-1]] if value.startswith('"') else ['--set-val', key, value])
        run([source/'scripts/config', '--file', objects/'.config', *edits], '03-diagnostic-settings')
        run([*make, 'olddefconfig'], '04-effective-defconfig')
        config = p.ordinary(objects/'.config'); (out/'actual-effective.config').write_bytes(config)
        result['effective_profile'] = check_config(config, settings)
        if revision in ('v160', 'v161') and result['effective_profile'].get('RELOCATABLE') != 'y':
            raise ValueError('v160 boot RELATIVE relocation handling must be enabled')
        if revision == 'v161' and any(result['effective_profile'].get(name) != 'y' for name in V161_CONFIG):
            raise ValueError('v161 diagnostic parser configuration must be enabled')
        result['cmdline_policy'] = route.builtin_cmdline_policy(config.decode())
        result['effective_config_sha256'] = p.sha(config)
        result['full_Image_build_attempts'] = 1; persist()
        run([*make, 'V=1', '-j4', 'Image'], '05-one-Image', 5400)
        autoconf = p.ordinary(objects/'include/generated/autoconf.h')
        if re.search(rb'^\s*#\s*define\s+CONFIG_EXYNOS_IMA(?:_MODULE)?\b', autoconf, re.M):
            raise ValueError('IMA stock/generated undefined proof failed')
        if revision == 'v161' and any(len(re.findall(rb'^#define CONFIG_'+name.encode()+rb' 1$', autoconf, re.M)) != 1
                                       for name in V161_CONFIG):
            raise ValueError('v161 actual generated diagnostic configuration differs')
        (out/'generated-autoconf.h').write_bytes(autoconf)
        evidence = {}
        proof_targets = (*PROOF_TARGETS, *(('init/initramfs.o',) if rootfs_observation else ()))
        for target in proof_targets:
            obj = p.ordinary(objects/target, MAX_MEMBER)
            cmdname = str(Path(target).with_name('.'+Path(target).name+'.cmd'))
            cmd = p.ordinary(objects/cmdname)
            dependencies = DEPENDENCIES.get(target, ())
            if observer and target == 'drivers/misc/v154_linux_return.o':
                dependencies += (V157_OBSERVER,)
            if rootfs_observation and target in ('init/initramfs.o', 'drivers/misc/v154_linux_return.o'):
                dependencies += ('linux/note10_rootfs_snapshot.h',)
            if revision == 'v161' and target == 'init/initramfs.o':
                dependencies += ('linux/kconfig.h',)
            if (obj[:6] != b'\x7fELF\x02\x01' or int.from_bytes(obj[16:18], 'little') != 1 or
                int.from_bytes(obj[18:20], 'little') != 183 or b'clang-14' not in cmd or
                target[:-2].encode()+b'.c' not in cmd or any(name.encode() not in cmd for name in dependencies) or re.search(rb'(?:^|\s)-DMODULE(?:\s|=|$)', cmd)):
                raise ValueError('actual same-Image builtin ARM64 source/.cmd proof failed: '+target)
            if (observer and target in ('init/main.o', 'drivers/misc/v154_linux_return.o') and
                b'n157_builtin_init_observe\0' not in obj):
                raise ValueError('v157 observer symbol absent from same-Image native object: '+target)
            if (rootfs_observation and target in ('init/initramfs.o', 'drivers/misc/v154_linux_return.o') and
                b'n159_rootfs_get_snapshot\0' not in obj):
                raise ValueError('v159 snapshot symbol absent from same-Image native object: '+target)
            saved = out/'commands'/cmdname; saved.parent.mkdir(parents=True, exist_ok=True); saved.write_bytes(cmd)
            evidence[target] = dict(object_sha256=p.sha(obj), object_bytes=len(obj), command_sha256=p.sha(cmd),
                                    command_path=saved.relative_to(out).as_posix(), builtin_ARM64=True,
                                    helper_dependencies={name: True for name in dependencies},
                                    source_dependency={target[:-2]+'.c': True})
        result['object_evidence'] = evidence
        if revision == 'v161':
            row = evidence['init/initramfs.o']
            result['initramfs_skip_policy'] = dict(schema='note10-v161-diagnostic-initramfs-policy-evidence-v1',
                source_sha256=result['preparation']['installed_sha256']['init/initramfs.c'],
                helper_sha256=V161_SOURCE['note10/device_test/v161_initramfs_force.py'],
                config_required={name: 'y' for name in V161_CONFIG}, generated_defines={name: True for name in V161_CONFIG},
                effective_config_sha256=result['effective_config_sha256'], generated_autoconf_sha256=p.sha(autoconf),
                object_target='init/initramfs.o', object_sha256=row['object_sha256'],
                command_path=row['command_path'], command_sha256=row['command_sha256'],
                normal_config_preserved=True, runtime_behavior_proved=False)
            persist()
        result['IMA_evidence'] = dict(generated_macros_undefined=True, production_fence_compiled=True,
                                      all_native_units_from_same_Image=True, autoconf_sha256=p.sha(autoconf))
        raw = p.ordinary(objects/'arch/arm64/boot/Image', p.IMAGE_LIMIT)
        symbols = p.ordinary(objects/'System.map', 16*1024*1024).decode()
        result.update(check_image(raw, cpio, identity, symbols, V158_PID1_ID if entry_only else b'N154IVA'))
        if rootfs_observation:
            if revision in ('v160', 'v161'):
                relocation_helper.producer_rootfs_proof(result, raw, symbols, persist)
            else:
                result['rootfs_materialization'] = rootfs_helper.linked_rootfs_proof(raw, symbols, len(cpio), result['linked_extent'])
            if raw.count(b'N159ROOT1 id=') != 1:
                raise ValueError('one same-Image rootfs snapshot frame required')
        if entry_only and b'N154IVA' in raw:
            raise ValueError('legacy IVA probe marker in v158 Image')
        result['dhd_link_evidence'] = check_dhd_symbol(symbols)
        native_output = p.FINAL_NATIVE
        if observer:
            result['preexec_observation'] = v157_link_proof(raw, symbols)
            native_output = dict(native_output, **{name: result['preparation']['installed_sha256'][name]
                                                   for name in V157_NATIVE})
        if rootfs_observation:
            native_output.update({name: result['preparation']['installed_sha256'][name] for name in V159_NATIVE})
        (out/'Image').write_bytes(raw)
        if source_pins(revision) != context['source_sha256']:
            raise ValueError('source changed during producer execution')
        result.update(passed=True, native_output_sha256=native_output,
                      native_make_target='Image', native_link_validation_status='linked-in-this-Image')
        persist()
    except BaseException as error:
        result.update(error_type=type(error).__name__, error=str(error)[:1024]); persist(); raise
    return result


def seal(output, head, revision='v155'):
    out = producer_output(output, revision)
    result = p.read(out/'result.json')
    if result['source_head'] != head:
        raise ValueError('sealing source association differs')
    observer = revision != 'v155'
    schemas = {'v157': V157_BUILD_SCHEMA, 'v158': V158_BUILD_SCHEMA,
               'v159': V159_BUILD_SCHEMA, 'v160': V160_BUILD_SCHEMA, 'v161': V161_BUILD_SCHEMA}
    if ((observer and (result.get('build_revision') != revision or result.get('schema') != schemas[revision])) or
        (not observer and result.get('build_revision') in schemas)):
        raise ValueError('sealing build revision association differs')
    if (out/'members.json').exists() or (out/'members.json').is_symlink():
        raise ValueError('preexisting manifest; never seal twice')
    files = sorted(path for path in out.rglob('*') if path.is_file())
    if any(path.is_symlink() or not path.resolve().is_relative_to(out) for path in files):
        raise ValueError('unsafe evidence member')
    sizes = {path.relative_to(out).as_posix(): path.stat().st_size for path in files}
    members = set(SUCCESS_MEMBERS)
    if observer:
        members.update('native-source/'+name for name in V157_NATIVE)
    if revision in ('v158', 'v159', 'v160', 'v161'):
        members.remove('01-probe-compile.log')
        members.add('01-pid1-compile.log')
    if revision in ('v159', 'v160', 'v161'):
        members.update('native-source/'+name for name in V159_NATIVE)
        members.add('commands/init/.initramfs.o.cmd')
    success_members = sorted(members)
    before_manifest = set(success_members)-{'members.json'}
    if not set(sizes) <= before_manifest or (result['passed'] is True and set(sizes) != before_manifest):
        raise ValueError('exact producer member allowlist differs')
    if any(not 0 < size <= MAX_MEMBER for size in sizes.values()) or sum(sizes.values()) > MAX_TOTAL or len(files) > 64:
        raise ValueError('bounded exact Image evidence archive required')
    manifest = dict(schema=f'note10-{revision if observer else "v154"}-sealed-members-v1', source_head=head,
                    member_sha256={path.relative_to(out).as_posix(): (result['Image_sha256'] if path.name == 'Image' else p.sha(p.ordinary(path, MAX_MEMBER))) for path in files},
                    member_bytes=sizes, max_member=MAX_MEMBER, max_total=MAX_TOTAL,
                    success_member_allowlist=list(success_members), manifest_self_excluded=True)
    manifest_raw = (json.dumps(manifest, indent=2, sort_keys=True)+'\n').encode()
    if len(files)+1 > 64 or len(manifest_raw) > MAX_MEMBER or sum(sizes.values())+len(manifest_raw) > MAX_TOTAL:
        raise ValueError('manifest-inclusive evidence budget exceeded')
    (out/'members.json').write_bytes(manifest_raw)
    bundle = out.with_suffix('.zip')
    with zipfile.ZipFile(bundle, 'x', compression=zipfile.ZIP_DEFLATED) as archive:
        for path in [*files, out/'members.json']:
            archive.write(path, path.relative_to(out).as_posix())
    subprocess.run(['node', str(p.ROOT/'note10/device_test/sealed_affinity_artifact.cjs'),
                    'seal', str(bundle), str(out.with_suffix('.n10sealed')), head], check=True, timeout=120)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--expected-source-head', required=True)
    parser.add_argument('--passed-new-test-context', required=True)
    parser.add_argument('--build-revision', choices=('v155', 'v157', 'v158', 'v159', 'v160', 'v161'), default='v155')
    parser.add_argument('--jobs', type=int, default=4)
    args = parser.parse_args()
    ci_guard(args.expected_source_head, os.environ)
    # Trusted codec/helper pins are checked before either module or Node execution.
    for name, pin in p.TRUSTED.items():
        if p.sha(p.ordinary(p.ROOT/name)) != pin:
            raise ValueError('original trusted source changed')
    context = public_context(args.passed_new_test_context, args.build_revision)
    recipient(os.environ.get('N10_RECIPIENT_PUBLIC_KEY_B64', ''))
    load_sources(context['source_sha256'], args.build_revision)
    subprocess.run(['node', str(p.ROOT/'note10/device_test/sealed_affinity_artifact.cjs'), 'recipient'], check=True, timeout=30)
    output = producer_output(args.output, args.build_revision)
    if spent_output(output, args.build_revision):
        raise ValueError('spent producer invocation; no sealing/replay')
    try:
        run_build(output, context, args.expected_source_head, args.jobs, args.build_revision)
    finally:
        if (output/'result.json').is_file():
            seal(output, args.expected_source_head, args.build_revision)


if __name__ == '__main__':
    main()
