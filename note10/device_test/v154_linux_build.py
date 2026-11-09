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

def validate_context(context):
    if (type(context) is not dict or set(context) != {'schema', 'scope', 'source_sha256', 'host_pass', 'kernel'} or
        context['schema'] != p.CONTEXT_SCHEMA or context['scope'] != 'stock-linux-iva-mmap-denial-no-XNU' or
        context['source_sha256'] != p.source_pins() or
        context['kernel'] != dict(commit=p.COMMIT, archive_sha256=p.ARCHIVE_SHA, defconfig_sha256=p.DEFCONFIG_SHA)):
        raise ValueError('exact final public context/source/kernel required')
    passes = context['host_pass']
    if (type(passes) is not dict or set(passes) != {'accepted', 'new', 'retained_v154_host_result_sha256'} or
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


def public_context(encoded):
    codec = p.module('v135_metadata', {'note10/device_test/v135_metadata.py': p.ordinary(p.ROOT/'note10/device_test/v135_metadata.py')})
    return validate_context(codec.decode_public(encoded))


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


def check_image(raw, archive, identity, symbols):
    if not 64 <= len(raw) <= p.IMAGE_LIMIT or raw[56:60] != b'ARM\x64':
        raise ValueError('bounded ARM64 Image header required')
    linked_extent = struct.unpack_from('<Q', raw, 16)[0]
    if (not 0 < linked_extent <= p.IMAGE_LIMIT or
        raw.count(p.CYCLE_MARKER+b'\0') != 1 or raw.count(archive) != 1):
        raise ValueError('bounded ARM64 Image/cycle/CPIO proof differs')
    if any(marker not in raw for marker in (b'N154IVA', b'N154ARM', b'N10RET1', b'N10ROUTE2', b'N10BOOTLINK2', b'N10MININIT2', identity.encode())):
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


def run_build(output, context, head, jobs=4):
    validate_context(context)
    if sys.platform != 'linux' or type(jobs) is not int or jobs != 4:
        raise ValueError('Linux jobs4 only')
    out = p.private(output)
    work = out.with_name(out.name+'-work')
    archive = out.with_name(out.name+'-source.tar.gz')
    if any(path.exists() for path in (out, work, archive)):
        raise ValueError('fresh output/work/archive required; never retry')
    buffers = p.load_sources(context['source_sha256'])
    out.mkdir(parents=True)
    result = dict(schema=p.BUILD_SCHEMA, version='v154', build_revision='v155', passed=False, source_head=head,
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
        for name in p.FINAL_NATIVE:
            dest = out/'native-source'/name; dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(p.ordinary(source/name))
        identity = result['build_evidence_id']
        run(['aarch64-linux-gnu-gcc', '-std=c11', '-O2', '-static', '-fno-stack-protector',
             '-Wall', '-Wextra', '-Werror', '-DN154_BUILD_ID="'+identity+'"',
             p.ROOT/'note10/device_test/v154_linux_probe.c', '-o', out/'minimal-init.elf'], '01-probe-compile')
        route = p.module('builtin_init_route', buffers)
        init = p.ordinary(out/'minimal-init.elf', 1024*1024)
        result['minimal_init'] = route.elf_manifest(init)
        cpio = route.cpio(init); (out/'initramfs.cpio').write_bytes(cpio)
        make = ['make', '-C', str(source), 'O='+str(objects), 'ARCH=arm64', 'CC=clang-14',
                'CROSS_COMPILE=aarch64-linux-gnu-', 'CLANG_TRIPLE=aarch64-linux-gnu-',
                'CROSS_COMPILE_ARM32=arm-linux-gnueabi-', 'GCC_TOOLCHAIN_DIR=/usr/aarch64-linux-gnu/bin/',
                'HOSTCC=gcc', 'HOSTCFLAGS=-Wno-error=deprecated-declarations', 'KCFLAGS=-gdwarf-4']
        run([*make, p.DEFCONFIG], '02-stock-defconfig')
        check_config(p.ordinary(objects/'.config'), {})
        settings = dict(SETTINGS, INITRAMFS_SOURCE='"'+str(out/'initramfs.cpio')+'"')
        edits = []
        for key, value in settings.items():
            edits.extend(['--enable' if value == 'y' else '--disable', key] if value in ('y', 'n') else
                         ['--set-str', key, value[1:-1]] if value.startswith('"') else ['--set-val', key, value])
        run([source/'scripts/config', '--file', objects/'.config', *edits], '03-diagnostic-settings')
        run([*make, 'olddefconfig'], '04-effective-defconfig')
        config = p.ordinary(objects/'.config'); (out/'actual-effective.config').write_bytes(config)
        result['effective_profile'] = check_config(config, settings)
        result['cmdline_policy'] = route.builtin_cmdline_policy(config.decode())
        result['effective_config_sha256'] = p.sha(config)
        result['full_Image_build_attempts'] = 1; persist()
        run([*make, 'V=1', '-j4', 'Image'], '05-one-Image', 5400)
        autoconf = p.ordinary(objects/'include/generated/autoconf.h')
        if re.search(rb'^\s*#\s*define\s+CONFIG_EXYNOS_IMA(?:_MODULE)?\b', autoconf, re.M):
            raise ValueError('IMA stock/generated undefined proof failed')
        (out/'generated-autoconf.h').write_bytes(autoconf)
        evidence = {}
        for target in PROOF_TARGETS:
            obj = p.ordinary(objects/target, MAX_MEMBER)
            cmdname = str(Path(target).with_name('.'+Path(target).name+'.cmd'))
            cmd = p.ordinary(objects/cmdname)
            if (obj[:6] != b'\x7fELF\x02\x01' or int.from_bytes(obj[16:18], 'little') != 1 or
                int.from_bytes(obj[18:20], 'little') != 183 or b'clang-14' not in cmd or
                target[:-2].encode()+b'.c' not in cmd or any(name.encode() not in cmd for name in DEPENDENCIES.get(target, ())) or re.search(rb'(?:^|\s)-DMODULE(?:\s|=|$)', cmd)):
                raise ValueError('actual same-Image builtin ARM64 source/.cmd proof failed: '+target)
            saved = out/'commands'/cmdname; saved.parent.mkdir(parents=True, exist_ok=True); saved.write_bytes(cmd)
            evidence[target] = dict(object_sha256=p.sha(obj), object_bytes=len(obj), command_sha256=p.sha(cmd),
                                    command_path=saved.relative_to(out).as_posix(), builtin_ARM64=True,
                                    helper_dependencies={name: True for name in DEPENDENCIES.get(target, ())},
                                    source_dependency={target[:-2]+'.c': True})
        result['object_evidence'] = evidence
        result['IMA_evidence'] = dict(generated_macros_undefined=True, production_fence_compiled=True,
                                      all_native_units_from_same_Image=True, autoconf_sha256=p.sha(autoconf))
        raw = p.ordinary(objects/'arch/arm64/boot/Image', p.IMAGE_LIMIT)
        symbols = p.ordinary(objects/'System.map', 16*1024*1024).decode()
        result.update(check_image(raw, cpio, identity, symbols))
        result['dhd_link_evidence'] = check_dhd_symbol(symbols)
        (out/'Image').write_bytes(raw)
        if p.source_pins() != context['source_sha256']:
            raise ValueError('source changed during producer execution')
        result.update(passed=True, native_output_sha256=p.FINAL_NATIVE,
                      native_make_target='Image', native_link_validation_status='linked-in-this-Image')
        persist()
    except BaseException as error:
        result.update(error_type=type(error).__name__, error=str(error)[:1024]); persist(); raise
    return result


def seal(output, head):
    out = p.private(output)
    result = p.read(out/'result.json')
    if result['source_head'] != head:
        raise ValueError('sealing source association differs')
    if (out/'members.json').exists() or (out/'members.json').is_symlink():
        raise ValueError('preexisting manifest; never seal twice')
    files = sorted(path for path in out.rglob('*') if path.is_file())
    if any(path.is_symlink() or not path.resolve().is_relative_to(out) for path in files):
        raise ValueError('unsafe evidence member')
    sizes = {path.relative_to(out).as_posix(): path.stat().st_size for path in files}
    before_manifest = set(SUCCESS_MEMBERS)-{'members.json'}
    if not set(sizes) <= before_manifest or (result['passed'] is True and set(sizes) != before_manifest):
        raise ValueError('exact producer member allowlist differs')
    if any(not 0 < size <= MAX_MEMBER for size in sizes.values()) or sum(sizes.values()) > MAX_TOTAL or len(files) > 64:
        raise ValueError('bounded exact Image evidence archive required')
    manifest = dict(schema='note10-v154-sealed-members-v1', source_head=head,
                    member_sha256={path.relative_to(out).as_posix(): (result['Image_sha256'] if path.name == 'Image' else p.sha(p.ordinary(path, MAX_MEMBER))) for path in files},
                    member_bytes=sizes, max_member=MAX_MEMBER, max_total=MAX_TOTAL,
                    success_member_allowlist=list(SUCCESS_MEMBERS), manifest_self_excluded=True)
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
    parser.add_argument('--jobs', type=int, default=4)
    args = parser.parse_args()
    ci_guard(args.expected_source_head, os.environ)
    # Trusted codec/helper pins are checked before either module or Node execution.
    for name, pin in p.TRUSTED.items():
        if p.sha(p.ordinary(p.ROOT/name)) != pin:
            raise ValueError('original trusted source changed')
    context = public_context(args.passed_new_test_context)
    recipient(os.environ.get('N10_RECIPIENT_PUBLIC_KEY_B64', ''))
    p.load_sources(context['source_sha256'])
    subprocess.run(['node', str(p.ROOT/'note10/device_test/sealed_affinity_artifact.cjs'), 'recipient'], check=True, timeout=30)
    output = p.private(args.output)
    if any(path.exists() for path in (output, output.with_name(output.name+'-work'), output.with_name(output.name+'-source.tar.gz'))):
        raise ValueError('spent producer invocation; no sealing/replay')
    try:
        run_build(output, context, args.expected_source_head, args.jobs)
    finally:
        if (output/'result.json').is_file():
            seal(output, args.expected_source_head)


if __name__ == '__main__':
    main()
