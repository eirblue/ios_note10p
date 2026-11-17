"""One recovery-only Linux Image; no PID1, carrier ABI or physical operation."""
import argparse
import hashlib
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
import v154_linux_build as house
import v130_archive as archive_helper

ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT / 'note10/device_test'
WORKFLOW = '.github/workflows/note10-v293-recovery-only.yml'
JOB = 'v293-recovery-only'
OUTPUT = ROOT / 'note10/private/v293-ci-recovery-only'
NEW_FILES = ('v293_recovery_prepare.py', 'v293_recovery_only.inc',
             'v293_recovery_fixture.c', 'test_v293_recovery.py')
CONTEXT_SCHEMA = 'note10-v293-recovery-only-public-input-v1'
DECLARATION = b'extern void n154_require_return_armed(void);'
ENTRY = b'\tn154_require_return_armed();\n\targv_init[1] = n10_builtin_init_argument();'
NEW_ENTRY = b'''\tn154_require_return_armed();
#ifdef CONFIG_DEFERRED_INITCALLS
\t/* Preserve stock deferred initialization before the permanent park. */
\tschedule_work(&deferred_initcall_work);
#endif
\tn293_recovery_only();
\targv_init[1] = n10_builtin_init_argument();'''
SETTINGS = dict(house.SETTINGS, LOCALVERSION='"-v293-recovery-only"',
                INITRAMFS_SOURCE='""', KEXEC='n', KEXEC_FILE='n', KEXEC_JUMP='n',
                DEFERRED_INITCALLS='y')
PROOF_FUNCTIONS = ('kernel_init', 'n154_return_init', 'n293_recovery_only', 'n10_return_worker')
LOGS = ('00-clang.log', '01-defconfig.log', '02-settings.log', '03-config.log',
        '04-Image.log', '05-linked-nm.log', '06-caller.log', '07-arm.log',
        '08-park.log', '09-worker.log', '10-return-relocations.log')
SUCCESS_MEMBERS = {'result.json', 'actual-effective.config', 'Image',
                   'source-evidence.json', 'commands.json', *LOGS, 'members.json'}


def require(value, message):
    if not value:
        raise ValueError(message)


def source_pins():
    pins = p.source_pins()
    for name in ('v154_linux_build.py', *NEW_FILES):
        relative = 'note10/device_test/' + name
        pins[relative] = p.sha(p.ordinary(ROOT / relative))
    pins[WORKFLOW] = p.sha(p.ordinary(ROOT / WORKFLOW))
    return pins


def public_context(head, passed):
    p.hexid(head, 40)
    require(set(passed) == {'passed', 'groups', 'variants', 'assertions', 'result_sha256'}
            and passed['passed'] is True
            and tuple(passed[k] for k in ('groups', 'variants', 'assertions')) == (2, 3, 12),
            'new seam and park fixture only')
    p.hexid(passed['result_sha256'])
    return dict(schema=CONTEXT_SCHEMA, source_head=head, source_sha256=source_pins(),
                new_fixture_PASS=passed, old_tests_replayed=False)


def main_overlay(raw):
    require(raw.count(DECLARATION) == raw.count(ENTRY) == 1 and b'n293_recovery_only' not in raw,
            'exact existing SYSTEM_RUNNING guard seam')
    return raw.replace(DECLARATION, DECLARATION + b'\nextern void __noreturn n293_recovery_only(void);', 1).replace(ENTRY, NEW_ENTRY, 1)


def install(source, identity, buffers):
    value = p.install(source, identity, buffers)
    main = source / 'init/main.c'
    main.write_bytes(main_overlay(p.ordinary(main)))
    target = source / 'drivers/misc/v154_linux_return.c'
    target.write_bytes(p.ordinary(target) + b'\n#include "v293_recovery_only.inc"\n')
    include = target.parent / 'v293_recovery_only.inc'
    require(not include.exists(), 'fresh recovery-only include')
    include.write_bytes(buffers['note10/device_test/v293_recovery_only.inc'])
    names = ('init/main.c', 'drivers/misc/v154_linux_return.c',
             'drivers/misc/v293_recovery_only.inc', 'drivers/misc/note10_auto_return.c',
             'drivers/misc/builtin_init_route.c', 'drivers/misc/v154_linux_id.h')
    value['recovery_only_source_sha256'] = {name: p.sha(p.ordinary(source / name)) for name in names}
    value.update(worker_modified=False, initramfs_source='', PID1_produced=False,
                 custom_reservation_bytes=0, restart_owners=1)
    return value


def symbol_table(text):
    table = {}
    for line in text.splitlines():
        row = line.split()
        if len(row) >= 3 and re.fullmatch('[0-9a-fA-F]+', row[2]):
            table.setdefault(row[0], []).append(dict(type=row[1], address=int(row[2], 16),
                                                    bytes=int(row[3], 16) if len(row) == 4 else 0))
    return table


def image_proof(raw, symbols, identity):
    require(64 <= len(raw) <= p.IMAGE_LIMIT and raw[56:60] == b'ARM\x64', 'bounded ARM64 Image')
    extent = struct.unpack_from('<Q', raw, 16)[0]
    table = symbol_table(symbols)
    require(all(len(table.get(name, [])) == 1 for name in (*PROOF_FUNCTIONS, '_text', '_end')),
            'same linked Image caller/park/arm/worker symbols')
    require(0 < extent == table['_end'][0]['address'] - table['_text'][0]['address'] <= p.IMAGE_LIMIT,
            'actual linked Image extent')
    require(all(0 < table[name][0]['bytes'] <= 65536 for name in PROOF_FUNCTIONS), 'bounded linked function extents')
    callbacks = [name for name in table if name.startswith('__initcall_') and 'n154_return_init' in name]
    require(len(callbacks) == 1, 'one linked late-init arm registration')
    require(raw.count(p.CYCLE_MARKER + b'\0') == 1, 'one existing host-patched cycle slot')
    for marker in (b'N293RET', b'N154ARM', b'N10RET1', b'N10BOOTLINK2', identity.encode()):
        require(marker in raw, 'linked recovery identity/markers')
    for marker in (b'N210PREP', b'N10XNU', b'N10PAYLOAD', b'N10OWNED', b'N10SHACTL1'):
        require(marker not in raw, 'no transfer/carrier payload')
    return dict(Image_bytes=len(raw), Image_sha256=p.sha(raw), linked_extent=extent,
                cycle_offset=raw.index(p.CYCLE_MARKER + b'\0'),
                linked_functions={name: table[name][0] for name in PROOF_FUNCTIONS},
                linked_arm_initcall=callbacks[0], PID1_entry_possible=False,
                initramfs_runtime_eligibility_required=False)


def run_build(output, context, head):
    require(sys.platform == 'linux' and context == public_context(head, context.get('new_fixture_PASS')),
            'exact source-bound new public context')
    expected = {'GITHUB_SHA': head, 'GITHUB_WORKFLOW_SHA': head, 'GITHUB_REPOSITORY': 'eirblue/ios_note10p',
                'GITHUB_JOB': JOB, 'GITHUB_RUN_ATTEMPT': '1'}
    require(all(os.environ.get(k) == v for k, v in expected.items())
            and os.environ.get('GITHUB_WORKFLOW_REF', '').startswith('eirblue/ios_note10p/' + WORKFLOW + '@'),
            'exact first CI dispatch')
    out = Path(output).resolve()
    require(out == OUTPUT, 'fixed private build output')
    work = out.with_name(out.name + '-work')
    archive = out.with_name(out.name + '-source.tar.gz')
    require(not any(path.exists() for path in (out, work, archive)), 'fresh one-use producer')
    out.mkdir(parents=True)
    identity = uuid.uuid4().hex
    result = dict(schema='note10-v293-recovery-only-build-v1', version='v293', passed=False,
                  source_head=head, source_sha256=context['source_sha256'], public_input=context,
                  build_evidence_id=identity, run_id=int(os.environ['GITHUB_RUN_ID']), run_attempt=1,
                  full_Image_build_attempts=0, old_tests_replayed=0, physical_ready=False,
                  XNU_execution=False, watchdog_armed=False, new_MMIO=False, BOOT_writes=0,
                  PID1_produced=False, custom_CPIO_produced=False, custom_reservation_bytes=0, stages={})
    def persist():
        p.save(out / 'result.json', result)
    def run(argv, label, timeout=600):
        result['stages'][label] = dict(argv=list(map(str, argv)), status='started')
        persist()
        with (out / (label + '.log')).open('xb') as log:
            done = house.run_command(argv, log, timeout)
        result['stages'][label].update(status='completed', returncode=done.returncode)
        persist()
        require(done.returncode == 0, 'producer stage failed: ' + label)
        if not (out / (label + '.log')).stat().st_size:
            (out / (label + '.log')).write_bytes(b'completed\n')
    persist()
    try:
        for name in ('clang-14', 'gcc', 'make', 'aarch64-linux-gnu-gcc', 'arm-linux-gnueabi-gcc',
                     'aarch64-linux-gnu-nm', 'aarch64-linux-gnu-objdump', 'aarch64-linux-gnu-readelf'):
            require(shutil.which(name) is not None, 'required tool absent: ' + name)
        run(['clang-14', '--version'], '00-clang')
        archive_helper.acquire(archive)
        with archive.open('rb') as stream:
            digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        require(archive.stat().st_size == p.ARCHIVE_BYTES and digest == p.ARCHIVE_SHA, 'pinned source archive')
        work.mkdir()
        source = archive_helper.extract(archive, work / 'source')
        objects = work / 'objects'
        objects.mkdir()
        require(p.sha(p.ordinary(source / 'arch/arm64/configs' / p.DEFCONFIG)) == p.DEFCONFIG_SHA, 'stock defconfig pin')
        buffers = {name: p.ordinary(ROOT / name) for name in context['source_sha256']}
        result['preparation'] = install(source, identity, buffers)
        persist()
        make = ['make', '-C', str(source), 'O=' + str(objects), 'ARCH=arm64', 'CC=clang-14',
                'CROSS_COMPILE=aarch64-linux-gnu-', 'CLANG_TRIPLE=aarch64-linux-gnu-',
                'CROSS_COMPILE_ARM32=arm-linux-gnueabi-', 'GCC_TOOLCHAIN_DIR=/usr/aarch64-linux-gnu/bin/',
                'HOSTCC=gcc', 'HOSTCFLAGS=-Wno-error=deprecated-declarations', 'KCFLAGS=-gdwarf-4']
        run([*make, p.DEFCONFIG], '01-defconfig')
        edits = []
        for key, value in SETTINGS.items():
            edits.extend(['--enable' if value == 'y' else '--disable', key] if value in ('y', 'n') else
                         ['--set-str', key, value[1:-1]] if value.startswith('"') else ['--set-val', key, value])
        run([source / 'scripts/config', '--file', objects / '.config', *edits], '02-settings')
        run([*make, 'olddefconfig'], '03-config')
        config = p.ordinary(objects / '.config')
        result['effective_profile'] = house.check_config(config, SETTINGS)
        (out / 'actual-effective.config').write_bytes(config)
        result['effective_config_sha256'] = p.sha(config)
        result['full_Image_build_attempts'] = 1
        persist()
        run([*make, 'V=1', '-j4', 'Image'], '04-Image', 5400)
        raw = p.ordinary(objects / 'arch/arm64/boot/Image', p.IMAGE_LIMIT)
        run(['aarch64-linux-gnu-nm', '--format=posix', '--print-size', '--defined-only', objects / 'vmlinux'], '05-linked-nm')
        symbols = p.ordinary(out / '05-linked-nm.log', 16777216).decode()
        result.update(image_proof(raw, symbols, identity))
        for name, label in zip(PROOF_FUNCTIONS, ('06-caller', '07-arm', '08-park', '09-worker')):
            run(['aarch64-linux-gnu-objdump', '-d', '--disassemble=' + name, objects / 'vmlinux'], label)
        require(b'<n293_recovery_only>' in p.ordinary(out / '06-caller.log'), 'linked caller enters permanent park')
        require(b'<kernel_restart>' in p.ordinary(out / '09-worker.log'), 'existing linked worker requests recovery')
        run(['aarch64-linux-gnu-readelf', '-rW', objects / 'drivers/misc/v154_linux_return.o'], '10-return-relocations')
        commands = {}
        for name in ('init/main.o', 'drivers/misc/v154_linux_return.o'):
            obj = p.ordinary(objects / name, 67108864)
            command = p.ordinary(objects / Path(name).with_name('.' + Path(name).name + '.cmd'))
            require(b'clang-14' in command and b'-DMODULE' not in command, 'same Image built-in compiler command')
            commands[name] = dict(object_sha256=p.sha(obj), object_bytes=len(obj), command=command.decode(), command_sha256=p.sha(command))
        p.save(out / 'commands.json', commands)
        names = result['preparation']['recovery_only_source_sha256']
        p.save(out / 'source-evidence.json', {name: dict(sha256=digest, text=p.ordinary(source / name).decode()) for name, digest in names.items()})
        require(source_pins() == context['source_sha256'], 'reviewed source changed during build')
        (out / 'Image').write_bytes(raw)
        result.update(passed=True, eligible_for_reviewed_BOOT_preparation=True,
                      physical_ready=False, native_make_target='Image', restart_owners=1)
        persist()
    except BaseException as error:
        result.update(error_type=type(error).__name__, error=str(error)[:1024])
        persist()
        raise
    return result


def seal(out, head):
    files = sorted(path for path in out.iterdir() if path.is_file())
    require(not (out / 'members.json').exists(), 'never seal twice')
    result = p.read(out / 'result.json')
    sizes = {path.name: path.stat().st_size for path in files}
    require(result['source_head'] == head and set(sizes) <= SUCCESS_MEMBERS - {'members.json'}
            and (result['passed'] is not True or set(sizes) == SUCCESS_MEMBERS - {'members.json'}), 'closed producer members')
    require(all(not path.is_symlink() and 0 < path.stat().st_size <= 67108864 for path in files)
            and sum(sizes.values()) <= 134217728, 'bounded private evidence')
    p.save(out / 'members.json', dict(schema='note10-v293-recovery-only-sealed-members-v1', source_head=head,
                                    member_bytes=sizes, member_sha256={path.name: p.sha(p.ordinary(path, 67108864)) for path in files},
                                    manifest_self_excluded=True))
    bundle = out.with_suffix('.zip')
    with zipfile.ZipFile(bundle, 'x', compression=zipfile.ZIP_DEFLATED) as packed:
        for path in [*files, out / 'members.json']:
            packed.write(path, path.name)
    subprocess.run(['node', str(HERE / 'sealed_affinity_artifact.cjs'), 'seal', str(bundle),
                    str(out.with_suffix('.n10sealed')), head], check=True, timeout=120)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--expected-source-head', required=True)
    parser.add_argument('--passed-new-test-context', required=True)
    args = parser.parse_args()
    context = json.loads(args.passed_new_test_context)
    house.recipient(os.environ.get('N10_RECIPIENT_PUBLIC_KEY_B64'))
    try:
        run_build(args.output, context, args.expected_source_head)
    finally:
        if args.output.resolve() == OUTPUT and (OUTPUT / 'result.json').exists():
            seal(OUTPUT, args.expected_source_head)


if __name__ == '__main__':
    main()
