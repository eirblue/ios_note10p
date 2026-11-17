"""Retain the built Linux Image and verify bounded compiler-outlined recovery calls."""
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
import v294_recovery_prepare as retained
p=retained.retained.p
house=retained.retained.house
archive_helper=retained.retained.archive_helper
install=retained.retained.install
image_proof=retained.retained.image_proof
symbol_table=retained.retained.symbol_table
recipient=retained.recipient
require=retained.require
ROOT=Path(__file__).resolve().parents[2]
HERE=ROOT/'note10/device_test'
WORKFLOW='.github/workflows/note10-v295-recovery-only.yml'
JOB='v295-recovery-only'
OUTPUT=ROOT/'note10/private/v295-ci-recovery-only'
SETTINGS=dict(retained.SETTINGS,LOCALVERSION='"-v295-recovery-only"')
CONTEXT_SCHEMA='note10-v295-recovery-only-public-input-v1'
PROOF_FUNCTIONS=retained.retained.PROOF_FUNCTIONS
CORE_MEMBERS=retained.retained.SUCCESS_MEMBERS
HELPER_LOGS={f'11-helper-{i}.log' for i in range(4)}
ALLOWED_MEMBERS=CORE_MEMBERS|HELPER_LOGS|{'outlined-worker.json'}


def source_pins():
    pins=retained.source_pins();pins.pop(retained.WORKFLOW)
    for name in ('v295_recovery_prepare.py','test_v295_outlined_worker.py'):
        relative='note10/device_test/'+name;pins[relative]=p.sha(p.ordinary(ROOT/relative))
    pins[WORKFLOW]=p.sha(p.ordinary(ROOT/WORKFLOW));return pins


def public_context(head,passed):
    p.hexid(head,40)
    require(set(passed)=={'passed','groups','variants','assertions','result_sha256'} and passed['passed'] is True
            and tuple(passed[k] for k in ('groups','variants','assertions'))==(1,6,6),'new compiler-proof cases only')
    p.hexid(passed['result_sha256'])
    return dict(schema=CONTEXT_SCHEMA,source_head=head,source_sha256=source_pins(),new_fixture_PASS=passed,old_tests_replayed=False)


def instruction_rows(text,entry):
    start=entry['address'];end=start+entry['bytes'];rows=[]
    require(entry['bytes']>0 and entry['bytes']%4==0,'aligned compiler function extent')
    for match in re.finditer(r'^\s*([0-9a-fA-F]+):\s+([0-9a-fA-F]{8})\s+([^\r\n]+)$',text,re.M):
        address=int(match.group(1),16)
        require(start<=address<end and address%4==0,'disassembly stays in exact linked extent')
        rows.append(dict(address=address,word=int(match.group(2),16),printed=match.group(3)))
    require([r['address'] for r in rows]==list(range(start,end,4)),'every bounded instruction captured once')
    return rows


def direct_target(word,address):
    if word&0x7c000000==0x14000000:
        immediate=word&0x03ffffff
        signed=immediate-(1<<26) if immediate&(1<<25) else immediate
        return address+4*signed
    if word&0xff000010==0x54000000 or word&0x7e000000==0x34000000:
        immediate=(word>>5)&0x7ffff
        signed=immediate-(1<<19) if immediate&(1<<18) else immediate
        return address+4*signed
    if word&0x7e000000==0x36000000:
        immediate=(word>>5)&0x3fff
        signed=immediate-(1<<14) if immediate&(1<<13) else immediate
        return address+4*signed
    return None


def worker_recovery_proof(worker_text,nm_text,capture_helper):
    table=symbol_table(nm_text)
    def named(name):
        entries=table.get(name,[])
        require(len(entries)==1 and entries[0]['type'] in ('T','t'),'one linked executable '+name)
        return dict(name=name,**entries[0])
    worker=named('n10_return_worker');restart=named('kernel_restart')
    by_address={}
    for name,entries in table.items():
        for entry in entries:
            if entry['type'] in ('T','t'):
                by_address.setdefault(entry['address'],[]).append(dict(name=name,**entry))
    def resolve(address):
        entries=by_address.get(address,[])
        require(len(entries)==1,'unique executable entry at numeric target address')
        return entries[0]
    worker_rows=instruction_rows(worker_text,worker);helpers={}
    for row in worker_rows:
        target=direct_target(row['word'],row['address'])
        if target is None or worker['address']<=target<worker['address']+worker['bytes']:continue
        entry=resolve(target)
        if entry['name'].startswith('OUTLINED_FUNCTION_'):
            require(entry['bytes']>0 and entry['bytes']%4==0,'bounded outlined function extent')
            helpers[target]=entry
        elif 'OUTLINED_FUNCTION_' in row['printed']:
            raise ValueError('outlined target is not its exact numeric entry')
    require(len(helpers)<=4 and sum(e['bytes'] for e in helpers.values())<=256,'four helpers and256-byte cap')
    # Acquire all directly referenced helpers before inspecting any of their bodies.
    captured=[(entry,capture_helper(entry,index)) for index,entry in enumerate(helpers.values())]
    helper_rows=[(entry,instruction_rows(text,entry)) for entry,text in captured]
    witnesses=[]
    for entry,rows in [(worker,worker_rows),*helper_rows]:
        for row in rows:
            require(row['word']&0xfffffc1f not in (0xd61f0000,0xd63f0000),'no unclosed indirect compiler call')
            target=direct_target(row['word'],row['address'])
            if target is None or entry['address']<=target<entry['address']+entry['bytes']:continue
            callee=resolve(target)
            if entry['address']!=worker['address']:
                require(not callee['name'].startswith('OUTLINED_FUNCTION_'),'outlined depth exceeds one')
            if target==restart['address']:
                witnesses.append(dict(caller=entry['name'],caller_address=entry['address'],site=row['address'],kernel_restart_address=target))
    require(witnesses,'bounded worker recovery call witness absent')
    return dict(schema='note10-v295-worker-outline-proof-v1',passed=True,worker=worker,kernel_restart=restart,
                helpers=[dict(entry,log=f'11-helper-{index}.log',disassembly_sha256=p.sha(text.encode()))
                         for index,(entry,text) in enumerate(captured)],helper_bytes=sum(e['bytes'] for e in helpers.values()),
                depth=1,witnesses=witnesses,runtime_execution_proven=False)


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
    result = dict(schema='note10-v295-recovery-only-build-v1', version='v295', passed=False,
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
        result['effective_profile'] = house.check_config(config, SETTINGS)
        (out / 'actual-effective.config').write_bytes(config)
        result['effective_config_sha256'] = p.sha(config)
        result['full_Image_build_attempts'] = 1
        persist()
        run([*make, 'V=1', '-j4', 'Image'], '04-Image', 5400)
        raw = p.ordinary(objects / 'arch/arm64/boot/Image', 67108864)
        # Preserve the compiled output before every subsequent proof/tool call.
        (out / 'Image').write_bytes(raw)
        result['compiled_Image_retained'] = dict(bytes=len(raw), sha256=p.sha(raw))
        persist()
        run(['aarch64-linux-gnu-nm', '--format=posix', '--print-size', '--defined-only', objects / 'vmlinux'], '05-linked-nm')
        symbols = p.ordinary(out / '05-linked-nm.log', 16777216).decode()
        result.update(image_proof(raw, symbols, identity))
        for name, label in zip(PROOF_FUNCTIONS, ('06-caller', '07-arm', '08-park', '09-worker')):
            run(['aarch64-linux-gnu-objdump', '-d', '--disassemble=' + name, objects / 'vmlinux'], label)
        require(b'<n293_recovery_only>' in p.ordinary(out / '06-caller.log'), 'linked caller enters permanent park')
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
        names = result['preparation']['recovery_only_source_sha256']
        p.save(out / 'source-evidence.json', {name: dict(sha256=digest, text=p.ordinary(source / name).decode()) for name, digest in names.items()})
        require(source_pins() == context['source_sha256'], 'reviewed source changed during build')
        result.update(passed=True, eligible_for_reviewed_BOOT_preparation=True,
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
    p.save(out/'members.json',dict(schema='note10-v295-recovery-only-sealed-members-v1',source_head=head,
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
