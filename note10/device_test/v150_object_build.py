"""One genuine AArch64 native IVA mailbox-object build; no kernel/Image execution."""
from pathlib import Path
import argparse
import base64
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import types

sys.dont_write_bytecode = True
BASE = Path(__file__).resolve().parents[2]
ROOT = BASE
HERE = Path(__file__).resolve().parent
PRIVATE = ROOT / 'note10/private'
WORKFLOW = '.github/workflows/note10-v150-native-iva-object.yml'
JOB = 'v150-native-iva-object'
REPOSITORY = 'eirblue/ios_note10p'
SCHEMA = 'note10-v150-native-iva-object-result-v1'
SCOPE = 'native-IVA150-mailbox-object-only'
COMMIT = '55f042627bb7030c93550faafa117674d32b21d1'
ARCHIVE_SHA = '46d6a563af04e0c2ed9c96c2a1af8cab2344b458c9554b09098e6a9e7219ae4c'
ARCHIVE_BYTES = 212648376
DEFCONFIG = 'exynos9820-d2x_defconfig'
DEFCONFIG_SHA = '0245e51f4e8efa406b329ddc66fa58e0b93f0c84520cf2dd68055e116eacb82b'
RECIPIENT = 'af9c0ca55448a00faae76c484d05b451443faf46ac94202d75030e170647459d'
PUBLIC_PEM_SHA = '26aa34c6674e8bad6d5e3c1cf9967f33b8b24339fdd2cfd64a92a0ea344e7f51'
TRUSTED = {
    'note10/device_test/v130_archive.py': 'bc49ffef72f73769de77a55432253f57f14d20433933ac56570f0ebfc3a1bce4',
    'note10/device_test/v135_metadata.py': 'd631d04e6f7a4cf1f48e6aeae53be8ef7a48599f4badf08091391fde96e218a9',
    'note10/device_test/sealed_affinity_artifact.cjs': '08c17edb82357d5719fbccd2427fca1970c09f6b3ee7aef91d6034f7d12f70ec',
}
HOST_SOURCE = {'note10/device_test/v150_iva_mbox_register.py': 'b10a752ff612ec64cbc79e5257cde1a7595cba092af7a1ed821bd33e7723e7c2', 'note10/device_test/test_v150_iva_mbox_register.py': 'bbbb548b9e3febe4660c5689ee5692a86b8f1e09b7f8711659d0597ce2ffd9d5'}
HOST_PASS = {'v150': {'result_schema': 'v150-native-mailbox-register-unlock-once-v1', 'result_sha256': '6d38bb486c430495cc2b7532f645dd044debfb73ba2ba196bc1a04d4f51752a4', 'passed': True, 'actual_counters': {'primary_transform_count': 1, 'negative_transform_count': 1, 'compiler_count': 1, 'fixture_count': 1, 'old_tests_count': 0}, 'native_output_sha256': {'drivers/vision/iva/iva_mbox.c': '7167cdb91a1e5729b2d4aaef87950a17f7b7a0c91792da7eb0df6dcc8a29e331'}}}
STAGE_OUTPUT = {'v150': {'drivers/vision/iva/iva_mbox.c': '7167cdb91a1e5729b2d4aaef87950a17f7b7a0c91792da7eb0df6dcc8a29e331'}}
FINAL_NATIVE = {'drivers/vision/iva/iva_mbox.c': '7167cdb91a1e5729b2d4aaef87950a17f7b7a0c91792da7eb0df6dcc8a29e331'}
TARGETS = ('drivers/vision/iva/iva_mbox.o',)
PREDECESSOR_PASS = {'schema': 'note10-v149-authenticated-producer-PASS-for-v150-v1', 'passed': True, 'source_head': '562ad1737f0c907f63394b2040915cb212790eef', 'run_id': 42475187853, 'run_attempt': 1, 'job_id': 128714830013, 'artifact_id': 13615226574, 'producer_result_schema': 'note10-v149-native-iva-object-result-v1', 'producer_result_sha256': '88e627e08e2595d1151155bc1fad648e776733aa2f682f90e105778cbd8cdb82', 'authenticated_summary_sha256': '093dbf89ae9c58f4027b8ed929957eca3922759287072bd086266f41343adb92', 'receive_terminal_sha256': '9aea95f8d790ea1707d8dd6efc55c6ea1b2cf2dae509e118798b25f90f43b3ed', 'object_sha256': {'drivers/vision/iva/iva_ctrl.o': '2e9512fc407a8dfe57800fd85944fde31af9f2118c2e5e027335ece03050d346'}, 'physical_ready': False, 'owner_success_emitted': False}
REQUIRED_CONFIG = {
    'ARM64': 'y', '64BIT': 'y', 'SMP': 'y', 'SOC_EXYNOS9820': 'y', 'SOC_EXYNOS9820_EVT0': 'n',
    'EXYNOS_IVA': 'y', 'IVA_VER': '30', 'IVA_FPGA': 'n', 'ION_EXYNOS': 'y',
    'EXYNOS_IOVMM': 'y', 'EXYNOS_IMA': 'n', 'PM': 'y', 'PM_SLEEP': 'y', 'LTO': 'n', 'LTO_CLANG': 'n', 'LTO_NONE': 'y',
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def hexid(value, length=64):
    if type(value) is not str or re.fullmatch('[0-9a-f]{' + str(length) + '}', value) is None:
        raise ValueError('exact hexadecimal identity required')
    return value


def ordinary(path, bound):
    if path.is_symlink() or not path.is_file() or not 0 < path.stat().st_size <= bound:
        raise ValueError('ordinary bounded input required: ' + str(path))
    return path.read_bytes()


def module_from_bytes(name, path, raw):
    module = types.ModuleType(name)
    module.__file__ = str(path)
    sys.modules[name] = module
    exec(compile(raw, str(path), 'exec'), module.__dict__)
    return module


def exact_value(actual, expected):
    if type(actual) is not type(expected):
        return False
    if type(expected) is dict:
        return set(actual) == set(expected) and all(exact_value(actual[k], v) for k, v in expected.items())
    return actual == expected


def validated_context(encoded):
    codec_path = ROOT / 'note10/device_test/v135_metadata.py'
    codec_raw = ordinary(codec_path, 2 * 1024 * 1024)
    if sha(codec_raw) != TRUSTED[codec_path.relative_to(ROOT).as_posix()]:
        raise ValueError('original public metadata codec differs')
    codec = module_from_bytes('v150_reviewed_public_codec', codec_path, codec_raw)
    context = codec.decode_public(encoded)
    keys = {'schema', 'scope', 'passed', 'host_pass', 'host_source_sha256', 'orchestration_sha256', 'kernel', 'predecessor149'}
    if (type(context) is not dict or set(context) != keys or
            context['schema'] != 'note10-v150-native-object-public-input-v1' or
            context['scope'] != SCOPE or context['passed'] is not True or
            not exact_value(context['host_pass'], HOST_PASS) or
            not exact_value(context['host_source_sha256'], HOST_SOURCE)):
        raise ValueError('exact actual150 host PASS/public2 source context required')
    kernel = dict(commit=COMMIT, archive_sha256=ARCHIVE_SHA, defconfig_sha256=DEFCONFIG_SHA)
    if not exact_value(context['kernel'], kernel):
        raise ValueError('exact native public kernel/stock profile binding required')
    orchestration = context['orchestration_sha256']
    if (type(orchestration) is not dict or
            set(orchestration) != set(TRUSTED) | {'note10/device_test/v150_object_build.py', WORKFLOW} or
            any(orchestration.get(name) != pin for name, pin in TRUSTED.items())):
        raise ValueError('separate exact original3 plus new148 orchestration2 pins required')
    pins = dict(HOST_SOURCE, **orchestration)
    buffers = {'note10/device_test/v135_metadata.py': codec_raw}
    for name, pin in pins.items():
        hexid(pin)
        raw = buffers.get(name)
        if raw is None:
            raw = ordinary(ROOT / name, 2 * 1024 * 1024)
            if sha(raw) != pin:
                raise ValueError('reviewed source bytes differ: ' + name)
        buffers[name] = raw
    predecessor149(context['predecessor149'])
    return context, pins, buffers


def predecessor149(row):
    if not exact_value(row, PREDECESSOR_PASS):
        raise ValueError('exact actual authenticated149 predecessor PASS required')


def recipient():
    encoded = os.environ.get('N10_RECIPIENT_PUBLIC_KEY_B64', '')
    if len(encoded) > 8192:
        raise ValueError('bounded original PUBLIC recipient required')
    pem = base64.b64decode(encoded, validate=True)
    if (sha(pem) != PUBLIC_PEM_SHA or b'PRIVATE KEY' in pem or
            not pem.startswith(b'-----BEGIN PUBLIC KEY-----\n') or not pem.endswith(b'-----END PUBLIC KEY-----\n')):
        raise ValueError('original PUBLIC PEM required')
    der = base64.b64decode(b''.join(pem.splitlines()[1:-1]), validate=True)
    if sha(der) != RECIPIENT:
        raise ValueError('original public recipient SPKI required')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--jobs', type=int, default=4)
    parser.add_argument('--expected-source-head', required=True)
    parser.add_argument('--passed-new-test-context', required=True)
    args = parser.parse_args()
    head = hexid(args.expected_source_head, 40)
    out = args.output if args.output.is_absolute() else ROOT / args.output
    out = out.absolute()
    work = out.with_name(out.name + '-workspace')
    archive = out.with_name(out.name + '-kernel-input.tar.gz')
    if (not sys.platform.startswith('linux') or args.jobs != 4 or out.resolve() != out or
            not out.is_relative_to(PRIVATE) or out == PRIVATE or
            any(path.exists() or path.is_symlink() for path in (out, work, archive))):
        parser.error('one fresh canonical Linux-only private object build required')
    context_keys = ('GITHUB_SHA', 'GITHUB_WORKFLOW_SHA', 'GITHUB_RUN_ID', 'GITHUB_RUN_ATTEMPT',
                    'GITHUB_REPOSITORY', 'GITHUB_JOB', 'GITHUB_WORKFLOW_REF')
    ci = {key: os.environ.get(key, '') for key in context_keys}
    if (ci['GITHUB_SHA'] != head or ci['GITHUB_WORKFLOW_SHA'] != head or
            re.fullmatch('[1-9][0-9]*', ci['GITHUB_RUN_ID']) is None or ci['GITHUB_RUN_ATTEMPT'] != '1' or
            ci['GITHUB_REPOSITORY'] != REPOSITORY or ci['GITHUB_JOB'] != JOB or
            ci['GITHUB_WORKFLOW_REF'] != REPOSITORY + '/' + WORKFLOW + '@refs/heads/main'):
        parser.error('actual reviewed source/head/job/attempt1 workflow identity required')
    public, source_pins, buffers = validated_context(args.passed_new_test_context)
    recipient()
    modules = {}
    for name in ('v130_archive', 'v150_iva_mbox_register'):
        path = HERE / (name + '.py')
        modules[name] = module_from_bytes('v150_reviewed_' + name, path, buffers[path.relative_to(ROOT).as_posix()])
    archive_module = modules['v130_archive']
    if (archive_module.COMMIT, archive_module.ARCHIVE_SHA, archive_module.DEFCONFIG) != (COMMIT, ARCHIVE_SHA, DEFCONFIG):
        raise ValueError('original source acquisition helper constants differ')
    identity = sha(json.dumps(dict(source=source_pins, ci=ci), sort_keys=True, separators=(',', ':')).encode())[:32]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.mkdir(mode=0o700)
    result = dict(schema=SCHEMA, version='v150', scope=SCOPE, passed=False, ci_context=ci,
                  producer_argv=[sys.executable, *sys.argv], producer_cwd=str(ROOT),
                  source_sha256=source_pins, build_evidence_id=identity, public_input=public,
                  predecessor149=public['predecessor149'],
                  kernel_commit=COMMIT, kernel_archive_sha256=ARCHIVE_SHA,
                  recipient_sha256=RECIPIENT, targets=list(TARGETS), stages={}, object_evidence={},
                  native_object_compile_status='pending', native_link_validation_status='not-requested',
                  old_tests_replayed=0, host_tests_replayed=0, retained_render_invocations=0,
                  Image_builds=0, hardware_package_emitted=False, physical_ready=False,
                  device_operations=[], owner_success_emitted=False, XNU_execution_allowed=False,
                  prior_overlays_applied=0, controller_objects_requested=0, IRQ_SMP_RCU_execution_claim=False)
    commands = []
    def save(path, row):
        path.write_bytes((json.dumps(row, indent=2, sort_keys=True) + '\n').encode())
    def persist():
        save(out / 'result.json', result)
    def run(command, label, timeout, allow_failure=False):
        row = dict(argv=[str(item) for item in command], completed=False, label=label)
        commands.append(row)
        save(out / 'commands.json', commands)
        with (out / (label + '.log')).open('xb') as stream:
            done = subprocess.run(row['argv'], cwd=ROOT, env=dict(os.environ, PLATFORM_VERSION='11', ANDROID_MAJOR_VERSION='r'),
                                  stdout=stream, stderr=subprocess.STDOUT, timeout=timeout)
        row.update(completed=True, returncode=done.returncode)
        save(out / 'commands.json', commands)
        if done.returncode and not allow_failure:
            raise ValueError('native build command failed: ' + label)
        return done.returncode
    persist()
    try:
        tools = {}
        for name in ('clang-14', 'gcc', 'make', 'aarch64-linux-gnu-gcc', 'arm-linux-gnueabi-gcc'):
            found = shutil.which(name)
            if not found:
                raise ValueError('required native build tool unavailable: ' + name)
            path = Path(found).resolve()
            tools[name] = dict(path=str(path), sha256=sha(ordinary(path, 512 * 1024 * 1024)),
                               version_argv=[str(path), '--version'], status='version-probe-started')
            save(out / 'toolchain.json', tools)
            version = subprocess.run([str(path), '--version'], capture_output=True, text=True, timeout=30)
            tools[name].update(version=version.stdout[:4096], stderr=version.stderr[:4096],
                               returncode=version.returncode, status='version-probe-completed')
            save(out / 'toolchain.json', tools)
            if version.returncode or (name == 'clang-14' and re.search(r'\bversion 14\.', version.stdout) is None):
                raise ValueError('required actual tool version unavailable: ' + name)
        save(out / 'toolchain.json', tools)
        result['stages']['source_acquire'] = dict(attempts=1, status='started')
        persist()
        archive_module.acquire(archive)
        if archive.stat().st_size != ARCHIVE_BYTES or sha(ordinary(archive, ARCHIVE_BYTES)) != ARCHIVE_SHA:
            raise ValueError('exact fresh public kernel archive differs')
        result['stages']['source_acquire']['status'] = 'completed'
        work.mkdir(mode=0o700)
        result['stages']['source_extract'] = dict(attempts=1, status='started')
        persist()
        source = archive_module.extract(archive, work / 'source')
        objects = work / 'objects'
        objects.mkdir(mode=0o700)
        stock_profile = ordinary(source / 'arch/arm64/configs' / DEFCONFIG, 2 * 1024 * 1024)
        if sha(stock_profile) != DEFCONFIG_SHA:
            raise ValueError('exact stock d2x source profile differs')
        result['stages']['source_extract']['status'] = 'completed'
        result['stages']['overlay150'] = dict(attempts=1, status='started')
        persist()
        native_input = ordinary(source / 'drivers/vision/iva/iva_mbox.c', 2 * 1024 * 1024)
        output = modules['v150_iva_mbox_register'].patch_native(native_input)
        hashes = {name: sha(raw) for name, raw in output.items()}
        if hashes != STAGE_OUTPUT['v150']:
            raise ValueError('intrinsic mailbox overlay differs from actual150 host output pin')
        result['overlay_output_sha256'] = {'v150': hashes}
        result['stages']['overlay150']['status'] = 'completed'
        for name, raw in output.items():
            path = source / name
            if not path.resolve().is_relative_to(source) or path.is_symlink():
                raise ValueError('unsafe native mailbox overlay output path')
            path.write_bytes(raw)
            snapshot = out / 'native-source' / name
            snapshot.parent.mkdir(parents=True, exist_ok=True)
            snapshot.write_bytes(raw)
        result['native_output_sha256'] = dict(FINAL_NATIVE)
        make = [tools['make']['path'], '-C', str(source), 'O=' + str(objects), 'ARCH=arm64', 'CC=clang-14',
                'CROSS_COMPILE=aarch64-linux-gnu-', 'CLANG_TRIPLE=aarch64-linux-gnu-',
                'CROSS_COMPILE_ARM32=arm-linux-gnueabi-', 'GCC_TOOLCHAIN_DIR=/usr/aarch64-linux-gnu/bin/',
                'HOSTCC=gcc', 'HOSTCFLAGS=-Wno-error=deprecated-declarations', 'KCFLAGS=-gdwarf-4']
        result['stages']['defconfig'] = dict(attempts=1, status='started')
        persist()
        run([*make, DEFCONFIG], '01-stock-defconfig', 600)
        config_raw = ordinary(objects / '.config', 2 * 1024 * 1024)
        configuration = {}
        for line in config_raw.decode('utf-8').splitlines():
            if line.startswith('CONFIG_') and '=' in line:
                name, value = line[7:].split('=', 1)
                if name in configuration:
                    raise ValueError('duplicate generated config key')
                configuration[name] = value
            elif line.startswith('# CONFIG_') and line.endswith(' is not set'):
                name = line[9:-11]
                if name in configuration:
                    raise ValueError('duplicate generated config key')
                configuration[name] = 'n'
        effective = {name: configuration.get(name, 'n') for name in REQUIRED_CONFIG if name != 'EXYNOS_IMA'}
        required_without_ima = {name: value for name, value in REQUIRED_CONFIG.items() if name != 'EXYNOS_IMA'}
        if effective != required_without_ima or configuration.get('EXYNOS_IMA') not in (None, 'n'):
            raise ValueError('actual stock native IVA branch differs; no forced profile change')
        ima_state = 'explicit-not-set' if configuration.get('EXYNOS_IMA') == 'n' else 'absent-in-generated-config'
        (out / 'actual-effective.config').write_bytes(config_raw)
        result.update(effective_config_sha256=sha(config_raw), effective_profile=effective,
                      effective_profile_evidence=dict(EXYNOS_IMA=dict(config_state=ima_state, resolved=False)),
                      effective_optional_profile={name: configuration.get(name, 'n') for name in ('MODULES', 'LTO_NONE', 'FTRACE_MCOUNT_RECORD')})
        result['stages']['defconfig']['status'] = 'completed'
        result['stages']['native_object_make'] = dict(attempts=1, status='started')
        persist()
        native_status = run([*make, '-k', 'V=1', '-j' + str(args.jobs), *TARGETS],
                            '02-native-one-object', 1800, allow_failure=True)
        result['native_object_make_exit_code'] = native_status
        persist()
        dependencies = {'iva_mbox.o': ('iva_ctrl_ioctl.h', 'iva_mbox.h', 'regs/iva_base_addr.h', 'regs/iva_mbox_reg.h', 'linux/interrupt.h')}
        for target in TARGETS:
            path = objects / target
            if native_status and (not path.is_file() or not path.stat().st_size):
                continue
            raw = ordinary(path, 64 * 1024 * 1024)
            target_elf = (len(raw) >= 20 and raw[:6] == b'\x7fELF\x02\x01' and
                          int.from_bytes(raw[16:18], 'little') == 1 and int.from_bytes(raw[18:20], 'little') == 183)
            saved = out / 'objects' / target
            saved.parent.mkdir(parents=True, exist_ok=True)
            saved.write_bytes(raw)
            row = dict(bytes=len(raw), sha256=sha(raw), artifact_path=str(saved.relative_to(out)),
                       AArch64_ELF64_little_relocatable=target_elf, diagnostic_only=True,
                       command_path=None, command_sha256=None, header_dependencies={})
            result['object_evidence'][target] = row
            persist()
            cmd_path = path.with_name('.' + path.name + '.cmd')
            cmd_raw = ordinary(cmd_path, 2 * 1024 * 1024) if not native_status or (cmd_path.is_file() and cmd_path.stat().st_size) else b''
            if cmd_raw:
                saved.with_name(cmd_path.name).write_bytes(cmd_raw)
                row.update(command_path=str(saved.with_name(cmd_path.name).relative_to(out)), command_sha256=sha(cmd_raw))
            row['header_dependencies'] = {name: name.encode() in cmd_raw for name in dependencies[path.name]}
            persist()
            if not native_status and (not target_elf or b'clang-14' not in cmd_raw or
                    re.search(rb'(?:^|\s)-DMODULE(?:\s|=|$)', cmd_raw) is not None or
                    not all(row['header_dependencies'].values())):
                raise ValueError('actual builtin ELF64 AArch64 clang/mailbox header evidence required')
            row['diagnostic_only'] = bool(native_status)
        autoconf_path = objects / 'include/generated/autoconf.h'
        if autoconf_path.is_file():
            autoconf = ordinary(autoconf_path, 2 * 1024 * 1024)
            (out / 'generated-autoconf.h').write_bytes(autoconf)
            result['generated_autoconf_sha256'] = sha(autoconf)
            ima_defined = re.search(rb'^\s*#\s*define\s+CONFIG_EXYNOS_IMA(?:_MODULE)?\b', autoconf, re.M) is not None
            result['effective_profile_evidence']['EXYNOS_IMA'].update(
                generated_macros_undefined=not ima_defined, mailbox_object_compiled=not native_status,
                resolved=not ima_defined and not native_status)
            if ima_defined:
                raise ValueError('generated IMA enabled; reviewed mailbox profile differs, no override/retry')
        else:
            raise ValueError('actual generated autoconf proof absent')
        if native_status:
            raise ValueError('native object make failed; partial new objects preserved diagnostically')
        if set(result['object_evidence']) != set(TARGETS):
            raise ValueError('exact one mailbox target evidence required')
        result['effective_profile']['EXYNOS_IMA'] = 'n'
        if result['effective_profile'] != REQUIRED_CONFIG:
            raise ValueError('actual effective profile proof incomplete')
        result['stages']['native_object_make']['status'] = 'completed'
        result.update(passed=True, native_object_compile_status='compiled-by-this-CI')
        persist()
        print(json.dumps(dict(passed=True, native_objects=1, physical_ready=False)))
    except Exception as error:
        for evidence in result['object_evidence'].values():
            evidence['diagnostic_only'] = True
        result.update(status='failed-spent-no-retry', error=str(error)[:512])
        persist()
        raise


if __name__ == '__main__':
    main()
