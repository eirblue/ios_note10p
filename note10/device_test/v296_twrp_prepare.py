"""Full built-in TWRP /init with the unchanged boot-armed cooperative return."""
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
import v295_recovery_prepare as retained
p=retained.p
house=retained.house
archive_helper=retained.archive_helper
symbol_table=retained.symbol_table
recipient=retained.recipient
require=retained.require
worker_recovery_proof=retained.worker_recovery_proof
ROOT=Path(__file__).resolve().parents[2]
HERE=ROOT/'note10/device_test'
WORKFLOW='.github/workflows/note10-v296-twrp-bringup.yml'
JOB='v296-twrp-bringup'
OUTPUT=ROOT/'note10/private/v296-ci-twrp-bringup'
SETTINGS=dict(retained.SETTINGS,LOCALVERSION='"-v296-twrp-bringup"',
              INITRAMFS_FORCE='y',BLK_DEV_INITRD='y',RD_LZMA='y')
CONTEXT_SCHEMA='note10-v296-twrp-bringup-public-input-v1'
IMAGE_LIMIT=67108864
SLOT_BYTES=10962166
SLOT_MARKER=b'N296_TWRP_INITRAMFS_SLOT_UNSET_'
INITRAMFS_ASM_SHA='ec2e6e427c11bfe4544db421f1c889917c14510975bd568d472e0793a59111a2'
PROOF_FUNCTIONS=('kernel_init','n154_return_init','n154_require_return_armed','n10_return_worker')
CORE_MEMBERS=(retained.CORE_MEMBERS-{'08-park.log'})|{'08-route.log'}
HELPER_LOGS=retained.HELPER_LOGS
ALLOWED_MEMBERS=CORE_MEMBERS|HELPER_LOGS|{'outlined-worker.json'}
ARGUMENT=b'\targv_init[1] = n10_builtin_init_argument();'
NORMAL_ARGUMENT=b'\t(void)n10_builtin_init_argument();\n\targv_init[1] = NULL;'


def source_pins():
    pins=retained.source_pins();pins.pop(retained.WORKFLOW)
    for name in ('v296_twrp_prepare.py','test_v296_twrp_route.py'):
        relative='note10/device_test/'+name;pins[relative]=p.sha(p.ordinary(ROOT/relative))
    pins[WORKFLOW]=p.sha(p.ordinary(ROOT/WORKFLOW));return pins


def public_context(head,passed):
    p.hexid(head,40)
    require(set(passed)=={'passed','groups','variants','assertions','result_sha256'} and passed['passed'] is True
            and tuple(passed[k] for k in ('groups','variants','assertions'))==(1,7,7),'new builtin route/config/slot cases only')
    p.hexid(passed['result_sha256'])
    return dict(schema=CONTEXT_SCHEMA,source_head=head,source_sha256=source_pins(),new_fixture_PASS=passed,old_tests_replayed=False)


def main_overlay(raw):
    require(raw.count(ARGUMENT)==1 and raw.count(b'n154_require_return_armed();')==1
            and b'n293_recovery_only' not in raw,'one pre-PID1 armed route seam without park')
    return raw.replace(ARGUMENT,NORMAL_ARGUMENT,1)


def install(source,identity,buffers):
    value=p.install(source,identity,buffers)
    main=source/'init/main.c';main.write_bytes(main_overlay(p.ordinary(main)))
    target=source/'usr/initramfs_data.S';raw=p.ordinary(target)
    require(p.sha(raw)==INITRAMFS_ASM_SHA,'pinned stock initramfs assembly')
    seam=b'.incbin __stringify(INITRAMFS_IMAGE)'
    require(raw.count(seam)==1,'one binary initramfs inclusion')
    replacement=('.ascii "'+SLOT_MARKER.decode()+'"\n.zero '+str(SLOT_BYTES-len(SLOT_MARKER))).encode()
    target.write_bytes(raw.replace(seam,replacement,1))
    names=('init/main.c','usr/initramfs_data.S','drivers/misc/Kconfig','drivers/misc/Makefile',
           'drivers/misc/v154_linux_return.c','drivers/misc/note10_auto_return.c',
           'drivers/misc/builtin_init_route.c','drivers/misc/v154_linux_id.h')
    value['twrp_route_source_sha256']={name:p.sha(p.ordinary(source/name)) for name in names}
    value.update(worker_modified=False,initramfs_source='',custom_reservation_bytes=0,restart_owners=1,
                 builtin_TWRP_slot=True,slot_bytes=SLOT_BYTES,PID1_entry_possible=True,permanent_park=False)
    return value


def check_config(raw,settings):
    values=house.config_values(raw)
    for key,value in dict(p.REQUIRED_CONFIG,**settings).items():
        require(values.get(key,'n')==value,'effective builtin-TWRP setting differs: '+key)
    require(not any(k.startswith('NOTE10_') and v!='n' and k not in settings for k,v in values.items()),'unselected NOTE10 profile')
    return values


def initramfs_slot_proof(raw,table):
    require(all(len(table.get(k,[]))==1 for k in ('_text','__initramfs_start','__initramfs_size')),'unique linked initramfs symbols')
    base=table['_text'][0]['address']
    offset=table['__initramfs_start'][0]['address']-base
    size_offset=table['__initramfs_size'][0]['address']-base
    require(0<=offset and offset+SLOT_BYTES<=len(raw) and 0<=size_offset<=len(raw)-8,'initramfs symbols within raw Image')
    require(struct.unpack_from('<Q',raw,size_offset)[0]==SLOT_BYTES,'exact linked initramfs byte count')
    require(raw.count(SLOT_MARKER)==1 and raw[offset:offset+len(SLOT_MARKER)]==SLOT_MARKER
            and not any(raw[offset+len(SLOT_MARKER):offset+SLOT_BYTES]),'unique untouched inert slot')
    return dict(offset=offset,bytes=SLOT_BYTES,size_symbol_offset=size_offset,
                placeholder_sha256=p.sha(raw[offset:offset+SLOT_BYTES]),unpatched_Image_eligible=False)


def image_proof(raw,symbols,identity):
    require(64<=len(raw)<=IMAGE_LIMIT and raw[56:60]==b'ARM\x64','bounded ARM64 Image')
    extent=struct.unpack_from('<Q',raw,16)[0];table=symbol_table(symbols)
    require(all(len(table.get(name,[]))==1 for name in (*PROOF_FUNCTIONS,'_text','_end')),'same linked caller/arm/worker')
    require(0<extent==table['_end'][0]['address']-table['_text'][0]['address']<=IMAGE_LIMIT,'linked Image extent')
    require(all(0<table[name][0]['bytes']<=65536 for name in PROOF_FUNCTIONS),'bounded linked function extents')
    callbacks=[name for name in table if name.startswith('__initcall_') and 'n154_return_init' in name]
    require(len(callbacks)==1,'one linked late-init arm registration')
    require(raw.count(p.CYCLE_MARKER+b'\0')==1,'one cycle slot')
    for marker in (b'N154ARM',b'N10RET1',b'N10ROUTE2',b'N10BOOTLINK2',identity.encode()):
        require(marker in raw,'linked return identity')
    require('n293_recovery_only' not in table and b'N293RET' not in raw,'permanent park absent')
    for marker in (b'N210PREP',b'N10XNU',b'N10PAYLOAD',b'N10OWNED',b'N10SHACTL1'):
        require(marker not in raw,'no carrier payload')
    return dict(Image_bytes=len(raw),Image_sha256=p.sha(raw),linked_extent=extent,initramfs_slot=initramfs_slot_proof(raw,table),
                cycle_offset=raw.index(p.CYCLE_MARKER+b'\0'),linked_functions={name:table[name][0] for name in PROOF_FUNCTIONS},
                linked_arm_initcall=callbacks[0],PID1_entry_possible=True,host_TWRP_slot_patch_required=True,unpatched_Image_eligible=False)


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
    result = dict(schema='note10-v296-twrp-bringup-build-v1', version='v296', passed=False,
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
        require(match and match[1].endswith('-v296-twrp-bringup'), 'exact diagnostic kernel release')
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
    p.save(out/'members.json',dict(schema='note10-v296-twrp-bringup-sealed-members-v1',source_head=head,
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
