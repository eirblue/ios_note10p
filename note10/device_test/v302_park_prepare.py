"""Linux-owned all-online IRQ-off park; hardware countdown is the postcommit owner."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import uuid
import zipfile
import v301_timeout_prepare as retained
p=retained.p
house=retained.house
archive_helper=retained.archive_helper
symbol_table=retained.symbol_table
recipient=retained.recipient
require=retained.require
worker_recovery_proof=retained.worker_recovery_proof
check_config=retained.check_config
rootfs_facts=retained.rootfs_facts
ROOT=Path(__file__).resolve().parents[2]
HERE=ROOT/'note10/device_test'
WORKFLOW='.github/workflows/note10-v302-irqoff-park.yml'
JOB='v302-irqoff-park'
OUTPUT=ROOT/'note10/private/v302-ci-irqoff-park'
SETTINGS=dict(retained.SETTINGS,LOCALVERSION='"-v302-irqoff-park"')
CONTEXT_SCHEMA='note10-v302-irqoff-park-public-input-v1'
PROOF_FUNCTIONS=retained.PROOF_FUNCTIONS
PARK_LOGS={f'15-park-{i}.log' for i in range(12)}
CORE_MEMBERS=retained.CORE_MEMBERS|{'park-flow.json'}
HELPER_LOGS=retained.HELPER_LOGS
ALLOWED_MEMBERS=CORE_MEMBERS|HELPER_LOGS|PARK_LOGS|{'outlined-worker.json'}
NEW_FILES=('v302_park_prepare.py','v302_park_contract.h','v302_park.inc','v302_watchdog_park.c',
           'v302_park_fixture.c','test_v302_park.py')
FLOW_FUNCTIONS=('n302_park_write','n302_cpu0','n302_spin','stop_machine','stop_machine_cpuslocked','multi_cpu_stop')


def source_pins():
    pins=retained.source_pins();pins.pop(retained.WORKFLOW)
    for name in NEW_FILES:
        path='note10/device_test/'+name;pins[path]=p.sha(p.ordinary(ROOT/path))
    pins[WORKFLOW]=p.sha(p.ordinary(ROOT/WORKFLOW));return pins


def public_context(head,passed):
    p.hexid(head,40)
    require(set(passed)=={'passed','groups','variants','assertions','result_sha256'} and passed['passed'] is True
            and tuple(passed[k] for k in ('groups','variants','assertions'))==(2,20,20),'new park/ACK/spin/seam cases only')
    p.hexid(passed['result_sha256'])
    return dict(schema=CONTEXT_SCHEMA,source_head=head,source_sha256=source_pins(),new_fixture_PASS=passed,old_tests_replayed=False)


def append_park(raw):
    require(b'v302_park.inc' not in raw and raw.endswith(b'\n'),'fresh normal-lifetime park include')
    return raw+b'\n#if IS_ENABLED(CONFIG_NOTE10_BUILTIN_INIT_ROUTE) && IS_ENABLED(CONFIG_NOTE10_V154_LINUX_DIAGNOSTIC)\n#include "v302_park.inc"\n#endif\n'


def install(source,identity,buffers):
    result=retained.install(source,identity,buffers)
    target=source/'drivers/misc/v154_linux_return.c';target.write_bytes(append_park(p.ordinary(target)))
    leaf=target.parent/'v302_park.inc';require(not leaf.exists(),'new park include')
    leaf.write_bytes(buffers['note10/device_test/v302_park.inc'])
    header=source/'include/linux/n302_park_contract.h';require(not header.exists(),'new park contract')
    header.write_bytes(buffers['note10/device_test/v302_park_contract.h'])
    names=set(result['twrp_route_source_sha256'])|{'drivers/misc/v302_park.inc','include/linux/n302_park_contract.h',
         'kernel/stop_machine.c','include/linux/stop_machine.h','kernel/watchdog.c','kernel/workqueue.c',
         'include/linux/nmi.h','include/linux/sched.h','include/linux/watchdog.h','kernel/printk/printk.c',
         'lib/debug-snapshot.c','arch/arm64/include/asm/processor.h'}
    result['twrp_route_source_sha256']={name:p.sha(p.ordinary(source/name)) for name in sorted(names)}
    result.update(park_route='stop_machine-cpu0-irqoff-tightspin',park_MMU_changed=False,park_CPU_power_changed=False,
                  park_WDT_registers_changed=False,park_clock_changed=False,park_XNU=False,
                  postcommit_software_abort_available=False,physical_arming_authorized=False)
    return result


def image_proof(raw,symbols,identity):
    value=retained.image_proof(raw,symbols,identity);table=symbol_table(symbols);proof={}
    for name in FLOW_FUNCTIONS:
        entries=table.get(name,[])
        require(len(entries)==1 and entries[0]['type'] in ('T','t') and 0<entries[0]['bytes']<=8192,'actual linked park/stock rendezvous function')
        proof[name]=entries[0]
    value['park_functions']=proof;return value


def spin_proof(text,entry):
    rows=[]
    for match in re.finditer(r'^[ \t]*([0-9a-f]+):[ \t]+[0-9a-f]{8}[ \t]+(\S+)(?:[ \t]+([^\r\n]*))?$',text,re.M):
        address=int(match[1],16)
        if entry['address']<=address<entry['address']+entry['bytes']:rows.append((address,match[2],match[3] or ''))
    require(len(rows)==2 and rows[0][1]=='yield' and rows[1][1]=='b' and rows[1][0]==rows[0][0]+4,'compiled tightspin has only yield and branch')
    target=rows[1][2].split()[0];require(re.fullmatch('[0-9a-f]+',target) and int(target,16)==rows[0][0],'compiled spin backedge never exits')
    return dict(passed=True,address=entry['address'],bytes=entry['bytes'],instruction_count=2,no_return=True,no_WFI=True,no_MMIO=True)


def capture_park_flow(symbols,run,objects,out):
    table=symbol_table(symbols);entries=[];spin=None;total=0
    for logical in FLOW_FUNCTIONS:
        names=[logical]+([logical+'.cfi'] if logical+'.cfi' in table else [])
        for name in names:
            found=table.get(name,[]);require(len(found)==1,'unique exact compiled flow symbol')
            item=found[0];require(item['type'] in ('T','t') and 0<item['bytes']<=8192,'bounded flow symbol')
            label='15-park-'+str(len(entries))
            run(['aarch64-linux-gnu-objdump','-d','--disassemble-zeroes','--start-address='+hex(item['address']),
                 '--stop-address='+hex(item['address']+item['bytes']),objects/'vmlinux'],label)
            raw=p.ordinary(out/(label+'.log'),32768);total+=len(raw);require(total<=131072,'bounded total park flow evidence')
            entries.append(dict(item,logical=logical,log=label+'.log',sha256=p.sha(raw),log_bytes=len(raw)))
            if logical=='n302_spin' and (name.endswith('.cfi') or logical+'.cfi' not in table):spin=spin_proof(raw.decode(),item)
    require(spin is not None,'actual compiled spin proof')
    return dict(schema='note10-v302-bounded-park-flow-v1',passed=True,functions=entries,spin=spin,
                static_scope='linked entry/callback/stock rendezvous bodies and exact nonreturn spin; source-pinned RUN barrier',
                runtime_quiesce_proven=False,raw_reset_cause_proven=False,XNU=False)


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
    result = dict(schema='note10-v302-irqoff-park-build-v1', version='v302', passed=False,
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
        require(all(line in config.splitlines() for line in (b'CONFIG_SMP=y',b'CONFIG_HOTPLUG_CPU=y',b'CONFIG_DEBUG_SNAPSHOT=y',b'CONFIG_SEC_DEBUG_LAST_KMSG=y'))
                and b'CONFIG_HARDLOCKUP_DETECTOR_PERF=y' not in config.splitlines()
                and b'CONFIG_HAVE_NMI_WATCHDOG=y' not in config.splitlines(),'stock all-online and nonhardware NMI-touch/logging contract')
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
        require(match and match[1].endswith('-v302-irqoff-park'), 'exact diagnostic kernel release')
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
        result['park_flow_proof']=capture_park_flow(symbols,run,objects,out)
        p.save(out/'park-flow.json',result['park_flow_proof'])
        actor=out/'watchdog-trigger'
        run(['aarch64-linux-gnu-gcc','-std=c11','-O2','-Wall','-Wextra','-Werror','-static','-nostdlib',
             '-fno-builtin','-fno-tree-loop-distribute-patterns','-fno-stack-protector','-fno-pie','-no-pie',
             '-Wl,--build-id=none','-Wl,-e,_start','-I',HERE,'-DN299_BUILD_ID="'+identity+'"',
             HERE/'v302_watchdog_park.c','-o',actor],'13-trigger-build')
        run(['aarch64-linux-gnu-readelf','-hlW',actor],'14-trigger-elf')
        actor_raw=p.ordinary(actor,262144)
        require(actor_raw[:4]==b'\x7fELF' and actor_raw[4:6]==b'\x02\x01' and int.from_bytes(actor_raw[16:18],'little')==2 and int.from_bytes(actor_raw[18:20],'little')==183,'bounded staticAArch64 actor')
        headers=p.ordinary(out/'14-trigger-elf.log').decode()
        require('INTERP' not in headers,'actor has no runtime interpreter')
        result['watchdog_actor_produced']=True
        result['watchdog_actor']=dict(bytes=len(actor_raw),sha256=p.sha(actor_raw),build_id=identity,
                                     host_only=True,auto_start=False,timeout=10,precommit_return_aborts=True,postcommit_software_abort=False,ack_drain_seconds=1,keepalives=0)

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
        needed=(CORE_MEMBERS-{'members.json'})|{'outlined-worker.json'}|{entry['log'] for entry in result['worker_return_proof']['helpers']}|{entry['log'] for entry in result['park_flow_proof']['functions']}
        require(set(sizes)==needed,'all current success proof members')
    require(all(not path.is_symlink() and 0<path.stat().st_size<=67108864 for path in files)
            and sum(sizes.values())<=134217728,'bounded private evidence including retained Image')
    p.save(out/'members.json',dict(schema='note10-v302-irqoff-park-sealed-members-v1',source_head=head,
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
