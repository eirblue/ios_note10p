"""Bounded runtime rootfs materialization diagnosis; unchanged cooperative return."""
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
import v296_twrp_prepare as retained
p=retained.p
house=retained.house
archive_helper=retained.archive_helper
symbol_table=retained.symbol_table
recipient=retained.recipient
require=retained.require
worker_recovery_proof=retained.worker_recovery_proof
check_config=retained.check_config
ROOT=Path(__file__).resolve().parents[2]
HERE=ROOT/'note10/device_test'
WORKFLOW='.github/workflows/note10-v297-rootfs-boundary.yml'
JOB='v297-rootfs-boundary'
OUTPUT=ROOT/'note10/private/v297-ci-rootfs-boundary'
SETTINGS=dict(retained.SETTINGS,LOCALVERSION='"-v297-rootfs-boundary"')
CONTEXT_SCHEMA='note10-v297-rootfs-boundary-public-input-v1'
PROOF_FUNCTIONS=retained.PROOF_FUNCTIONS
CORE_MEMBERS=retained.CORE_MEMBERS|{'12-rootfs-final.log'}
HELPER_LOGS=retained.HELPER_LOGS
ALLOWED_MEMBERS=CORE_MEMBERS|HELPER_LOGS|{'outlined-worker.json'}
INITRAMFS_SHA='1a9af19668584dc664c28c640e02b6a03cc37a2fa5ecd1900d818bb67c775806'
NEW_FILES=('v297_rootfs_prepare.py','v297_rootfs_probe.inc','v297_rootfs_fixture.c','test_v297_rootfs.py')
UNPACK=b'\terr = unpack_to_rootfs(__initramfs_start, __initramfs_size);'
OPEN=b'\t\t\twfd = sys_open(collected, openflags, mode);'
MAIN_DECL=b'extern void n154_require_return_armed(void);'
MAIN_CALL=b'\tn154_require_return_armed();'


def source_pins():
    pins=retained.source_pins();pins.pop(retained.WORKFLOW)
    for name in NEW_FILES:
        path='note10/device_test/'+name;pins[path]=p.sha(p.ordinary(ROOT/path))
    pins[WORKFLOW]=p.sha(p.ordinary(ROOT/WORKFLOW));return pins


def public_context(head,passed):
    p.hexid(head,40)
    require(set(passed)=={'passed','groups','variants','assertions','result_sha256'} and passed['passed'] is True
            and tuple(passed[k] for k in ('groups','variants','assertions'))==(3,12,21),'new rootfs probe/seam/protocol cases only')
    p.hexid(passed['result_sha256'])
    return dict(schema=CONTEXT_SCHEMA,source_head=head,source_sha256=source_pins(),new_fixture_PASS=passed,old_tests_replayed=False)


def rootfs_overlay(raw):
    before=b'static int __init do_name(void)'
    populate=b'static int __init populate_rootfs(void)'
    require(all(raw.count(anchor)==1 for anchor in (before,populate,UNPACK,OPEN)) and b'n297_' not in raw,'unique stock rootfs seams')
    raw=raw.replace(before,b'static void __init n297_note_init_open(const char *name, int result);\n\n'+before,1)
    raw=raw.replace(OPEN,OPEN+b'\n\t\t\tn297_note_init_open(collected, wfd);',1)
    raw=raw.replace(populate,b'#include "v297_rootfs_probe.inc"\n\n'+populate,1)
    return raw.replace(UNPACK,b'\tn297_before_unpack();\n'+UNPACK+b'\n\tn297_after_unpack(err ? -EINVAL : 0);',1)


def main_overlay(raw):
    require(raw.count(MAIN_DECL)==raw.count(MAIN_CALL)==1 and b'n297_' not in raw,'unique armed late route')
    raw=raw.replace(MAIN_DECL,MAIN_DECL+b'\nextern void __init n297_rootfs_final_probe(void);',1)
    return raw.replace(MAIN_CALL,MAIN_CALL+b'\n\tn297_rootfs_final_probe();',1)


def install(source,identity,buffers):
    result=retained.install(source,identity,buffers)
    main=source/'init/main.c';main.write_bytes(main_overlay(p.ordinary(main)))
    target=source/'init/initramfs.c';raw=p.ordinary(target)
    require(p.sha(raw)==INITRAMFS_SHA,'pinned stock population implementation')
    target.write_bytes(rootfs_overlay(raw))
    include=source/'init/v297_rootfs_probe.inc';require(not include.exists(),'fresh rootfs probe include')
    include.write_bytes(buffers['note10/device_test/v297_rootfs_probe.inc'])
    names=set(result['twrp_route_source_sha256'])|{'init/initramfs.c','init/v297_rootfs_probe.inc'}
    result['twrp_route_source_sha256']={name:p.sha(p.ordinary(source/name)) for name in sorted(names)}
    result.update(rootfs_probe_readonly=True,full_slot_hash_max_runs=1,worker_modified=False,
                  independent_late_probe=True,second_unpack=False)
    return result


def image_proof(raw,symbols,identity):
    value=retained.image_proof(raw,symbols,identity);table=symbol_table(symbols)
    entries=table.get('n297_rootfs_final_probe',[])
    require(len(entries)==1 and entries[0]['type'] in ('T','t') and 0<entries[0]['bytes']<=16384
            and b'N297RFS' in raw,'actual linked independent late rootfs probe')
    value['rootfs_probe_function']=entries[0];return value


def rootfs_facts(text,identity,expected):
    pattern=r'N297RFS id='+identity+r' stage=(pre|post|late) (.+)\r?$'
    rows={}
    keys={'flags','declared','hash_declared','span','magic','fnv','hash_stage','skip','unpack','open_seen','open_rc','init_rc','mode','ino','size','console_rc','root_rc','root_magic','root_ino'}
    for match in re.finditer(pattern,text,re.M):
        stage,body=match.groups();tokens=body.split();parts=[token.split('=',1) for token in tokens]
        require(all(len(part)==2 for part in parts) and len(parts)==len(keys) and {part[0] for part in parts}==keys and stage not in rows,'unique bounded rootfs record')
        rows[stage]={key:int(value,16 if key in ('magic','fnv') else 10) for key,value in parts}
    require('late' in rows,'independent late record required')
    late=rows['late'];require(late['flags']&12==12 and not late['flags']&~15 and late['span']==10962166,'late flags and exact linked slot')
    require(bool(late['flags']&1)==('pre' in rows) and bool(late['flags']&2)==('post' in rows),'recorded callback/state agreement')
    matches=all(late[key]==expected[key] for key in ('span','magic','fnv')) and late['declared']==late['hash_declared']==10962166
    if late['skip']:frontier='SKIP_INITRAMFS'
    elif 'pre' not in rows:frontier='BUILTIN_UNPACK_HOOKS_NOT_OBSERVED'
    elif not matches:frontier='RUNTIME_BLOB_OR_SIZE_MISMATCH'
    elif late['unpack']:frontier='UNPACK_REPORTED_ERROR'
    elif late['open_seen'] and late['open_rc']<0:frontier='INIT_CREATE_FAILED'
    elif 'post' in rows and rows['post']['init_rc']==0 and late['init_rc']!=0:frontier='INIT_LOST_AFTER_POPULATION'
    elif late['init_rc']==0:frontier='INIT_PRESENT_AT_LATE_ROUTE'
    else:frontier='INIT_NOT_MATERIALIZED'
    return dict(records=rows,blob_matches_expected=matches,frontier=frontier,
                late_init_exists=late['init_rc']==0,userspace_success_proven=False)


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
    result = dict(schema='note10-v297-rootfs-boundary-build-v1', version='v297', passed=False,
                  source_head=head, source_sha256=context['source_sha256'], public_input=context,
                  build_evidence_id=identity, run_id=int(os.environ['GITHUB_RUN_ID']), run_attempt=1,
                  full_Image_build_attempts=0, old_tests_replayed=0, physical_ready=False,
                  XNU_execution=False, watchdog_armed=False, new_MMIO=False, BOOT_writes=0,
                  PID1_produced=False, custom_CPIO_produced=False, custom_reservation_bytes=0, builtin_TWRP_patch_required=True, hardware_WDT_trigger=False, stages={})
    def persist():
        p.save(out / 'result.json', result)
    def run(argv, label, timeout=600):
        result['stages'][label] = dict(argv=list(map(str, argv)), status='started')
        persist()
        with (out / (label + '.log')).open('xb') as log:
            done = house.run_command(argv, log, timeout)
        result['stages'][label].update(status='completed', returncode=done.returncode)
        persist()
        if not (out / (label + '.log')).stat().st_size:
            (out / (label + '.log')).write_bytes(b'no stdout; returncode recorded in result.json\n')
        require(done.returncode == 0, 'producer stage failed: ' + label)
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
        result['effective_profile'] = check_config(config, SETTINGS)
        (out / 'actual-effective.config').write_bytes(config)
        result['effective_config_sha256'] = p.sha(config)
        result['full_Image_build_attempts'] = 1
        persist()
        run([*make, 'V=1', '-j4', 'Image'], '04-Image', 5400)
        raw = p.ordinary(objects / 'arch/arm64/boot/Image', 67108864)
        # Preserve the compiled output before every subsequent proof/tool call.
        (out / 'Image').write_bytes(raw)
        result['compiled_Image_retained'] = dict(bytes=len(raw), sha256=p.sha(raw))
        release = p.ordinary(objects / 'include/generated/utsrelease.h').decode()
        match = re.fullmatch(r'#define UTS_RELEASE "([^"\r\n]+)"\n', release)
        require(match and match[1].endswith('-v297-rootfs-boundary'), 'exact diagnostic kernel release')
        result['kernel_release'] = match[1]
        persist()
        run(['aarch64-linux-gnu-nm', '--format=posix', '--print-size', '--defined-only', objects / 'vmlinux'], '05-linked-nm')
        symbols = p.ordinary(out / '05-linked-nm.log', 16777216).decode()
        result.update(image_proof(raw, symbols, identity))
        for name, label in zip(PROOF_FUNCTIONS, ('06-caller', '07-arm', '08-route', '09-worker')):
            run(['aarch64-linux-gnu-objdump', '-d', '--disassemble=' + name, objects / 'vmlinux'], label)
        def capture_helper(entry, index):
            label = '11-helper-' + str(index)
            run(['aarch64-linux-gnu-objdump', '-d', '--disassemble-zeroes',
                 '--start-address=' + hex(entry['address']),
                 '--stop-address=' + hex(entry['address'] + entry['bytes']), objects / 'vmlinux'], label)
            return p.ordinary(out / (label + '.log'), 32768).decode()
        proof = worker_recovery_proof(p.ordinary(out / '09-worker.log').decode(), symbols, capture_helper)
        p.save(out / 'outlined-worker.json', proof)
        result['worker_return_proof'] = proof
        run(['aarch64-linux-gnu-objdump', '-d', '--disassemble=n297_rootfs_final_probe', objects / 'vmlinux'], '12-rootfs-final')
        persist()
        run(['aarch64-linux-gnu-readelf', '-rW', objects / 'drivers/misc/v154_linux_return.o'], '10-return-relocations')
        commands = {}
        for name in ('init/main.o', 'drivers/misc/v154_linux_return.o'):
            obj = p.ordinary(objects / name, 67108864)
            command = p.ordinary(objects / Path(name).with_name('.' + Path(name).name + '.cmd'))
            require(b'clang-14' in command and b'-DMODULE' not in command, 'same Image built-in compiler command')
            commands[name] = dict(object_sha256=p.sha(obj), object_bytes=len(obj), command=command.decode(), command_sha256=p.sha(command))
        p.save(out / 'commands.json', commands)
        names = result['preparation']['twrp_route_source_sha256']
        p.save(out / 'source-evidence.json', {name: dict(sha256=digest, text=p.ordinary(source / name).decode()) for name, digest in names.items()})
        require(source_pins() == context['source_sha256'], 'reviewed source changed during build')
        result.update(passed=True, eligible_for_reviewed_BOOT_preparation=False, eligible_for_reviewed_TWRP_slot_patch=True,
                      physical_ready=False, native_make_target='Image', restart_owners=1)
        persist()
    except BaseException as error:
        result.update(error_type=type(error).__name__, error=str(error)[:1024])
        persist()
        raise
    return result

def seal(out,head):
    files=sorted(path for path in out.iterdir() if path.is_file())
    require(not(out/'members.json').exists(),'never seal twice')
    result=p.read(out/'result.json');sizes={path.name:path.stat().st_size for path in files}
    require(result['source_head']==head and set(sizes)<=ALLOWED_MEMBERS-{'members.json'},'closed current producer members')
    if result['passed'] is True:
        needed=(CORE_MEMBERS-{'members.json'})|{'outlined-worker.json'}|{entry['log'] for entry in result['worker_return_proof']['helpers']}
        require(set(sizes)==needed,'all current success proof members')
    require(all(not path.is_symlink() and 0<path.stat().st_size<=67108864 for path in files)
            and sum(sizes.values())<=134217728,'bounded private evidence including retained Image')
    p.save(out/'members.json',dict(schema='note10-v297-rootfs-boundary-sealed-members-v1',source_head=head,
                                 member_bytes=sizes,member_sha256={path.name:p.sha(p.ordinary(path,67108864)) for path in files},
                                 manifest_self_excluded=True))
    bundle=out.with_suffix('.zip')
    with zipfile.ZipFile(bundle,'x',compression=zipfile.ZIP_DEFLATED) as packed:
        for path in [*files,out/'members.json']:packed.write(path,path.name)
    subprocess.run(['node',str(HERE/'sealed_affinity_artifact.cjs'),'seal',str(bundle),str(out.with_suffix('.n10sealed')),head],check=True,timeout=120)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--expected-source-head', required=True)
    parser.add_argument('--passed-new-test-context', required=True)
    args = parser.parse_args()
    context = json.loads(args.passed_new_test_context)
    recipient(os.environ.get('N10_RECIPIENT_PUBLIC_KEY_B64'))
    try:
        run_build(args.output, context, args.expected_source_head)
    finally:
        if args.output.resolve() == OUTPUT and (OUTPUT / 'result.json').exists():
            seal(OUTPUT, args.expected_source_head)


if __name__=='__main__':main()
