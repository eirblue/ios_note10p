"""v311 XNU image load witness: a 256 MiB memblock window holds the v310 diagnostic arena at B and the XNU memory image (read from candidate /tmp before stop_machine) at B+0x1004000; boot_args describe both; the MMU-off stub checks the window geometry, the Mach-O header and the whole-image word-FNV before the N311PS2T record, then fixed WDT return. No XNU execution. Build and static proof only."""
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
import v302_park_prepare as retained
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
WORKFLOW='.github/workflows/note10-v311-xnu-load-r1.yml'
JOB='v311-xnu-load-r1'
OUTPUT=ROOT/'note10/private/v311-ci-xnu-load-r1'
SETTINGS=dict(retained.SETTINGS,LOCALVERSION='"-v311-xnu-load-r1"')
CONTEXT_SCHEMA='note10-v311-xnu-load-r1-public-input-v1'
# groups (ADT entry predicate, generators, v311 load predicate, record validator), variants (38 ADT arena images +
# 17 generator inputs [9 ADT, 6 n311_arguments, 2 n311_fnv_words] + 15 load arena/image cases + 9 records),
# CHECK assertions in v311_load_fixture.c.
FIXTURE_COUNTS=(4,79,86)
PROOF_FUNCTIONS=retained.PROOF_FUNCTIONS
PARK_LOGS={f'15-park-{i}.log' for i in range(18)}
CORE_MEMBERS=retained.CORE_MEMBERS|{'park-flow.json'}
HELPER_LOGS=retained.HELPER_LOGS
ALLOWED_MEMBERS=CORE_MEMBERS|HELPER_LOGS|PARK_LOGS|{'outlined-worker.json'}
NEW_FILES=('v311_prepare.py','v303_mmuoff_contract.h','v303_snapshot_claim.inc','v311_abi_contract.h',
           'runtime_relocation.h','runtime_relocation.c','v311_terminal_abi.c','v311_terminal_abi_stub.S',
           'v311_xnu_window.c','v311_host_record.h','v311_host_record_validate.h','v311_load_fixture.c')
FLOW_FUNCTIONS=('n302_park_write','n311_load_image','n302_cpu0','stop_machine','stop_machine_cpuslocked','multi_cpu_stop','n304_prepare_args','n304_enter','n303_snapshot_claim','__cpu_soft_restart','n304_post_abi')
INIT_RESIZE=b'\n\tmemblock_allow_resize();\n}\n'
INIT_DECLARATION=b'void __init arm64_memblock_init(void)'
PARK_STOP=b'    return stop_machine(n302_cpu0,NULL,cpumask_of(0));'



def repo_path(name):
    # runtime_relocation.h lives with the XNU 26 sources; everything else is under device_test.
    return 'note10/xnu26/'+name if name in ('runtime_relocation.h','runtime_relocation.c') else 'note10/device_test/'+name


def source_pins():
    pins=retained.source_pins();pins.pop(retained.WORKFLOW)
    for name in NEW_FILES:
        path=repo_path(name);pins[path]=p.sha(p.ordinary(ROOT/path))
    pins[WORKFLOW]=p.sha(p.ordinary(ROOT/WORKFLOW));return pins


def public_context(head,passed):
    p.hexid(head,40)
    require(set(passed)=={'passed','groups','variants','assertions','result_sha256'} and passed['passed'] is True
            and tuple(passed[k] for k in ('groups','variants','assertions'))==FIXTURE_COUNTS,'v311 host fixture cases only')
    p.hexid(passed['result_sha256'])
    return dict(schema=CONTEXT_SCHEMA,source_head=head,source_sha256=source_pins(),new_fixture_PASS=passed,old_tests_replayed=False)


def return_overlay(raw):
    require(raw.count(b'    n302_spin();')==1 and b'n303_enter' not in raw and b'n304_enter' not in raw,'single retained302 terminal tail')
    # v311: the image is loaded once in process context; any failure returns before stop_machine (no transfer).
    require(raw.count(PARK_STOP)==1 and b'n311_' not in raw,'single retained302 park_write stop_machine')
    raw=raw.replace(PARK_STOP,b'    { int error=n311_load_image(); if (error) return error; }\n'+PARK_STOP,1)
    return raw.replace(b'    n302_spin();',b'    { int error=n304_prepare_args(N154_BUILD_ID,n10_boot_id,(const char *)n10_cycle);\n      if (!error) error=n304_enter();\n      /* Only our request claim is undone; attempted/prepared remain spent. */\n      atomic_cmpxchg(&n10_return_requested,1,0);atomic_set(&n302_committed,0);return error; }',1)


def snapshot_overlay(raw):
    require(raw.endswith(b'\n') and b'n303_snapshot_claim.inc' not in raw,'fresh stock snapshot owner include')
    return raw+b'\n#if IS_ENABLED(CONFIG_NOTE10_BUILTIN_INIT_ROUTE) && IS_ENABLED(CONFIG_NOTE10_V154_LINUX_DIAGNOSTIC)\n#include "n303_snapshot_claim.inc"\n#endif\n'


def install(source,identity,buffers):
    result=retained.install(source,identity,buffers)
    target=source/'drivers/misc/v302_park.inc';target.write_bytes(return_overlay(p.ordinary(target)))
    # Prototype remains in normal kernel lifetime with the existing park TU.
    target.write_bytes(b'#include <linux/n303_mmuoff_contract.h>\nint n304_prepare_args(const char *build, const char *boot, const char *cycle);\nint n304_enter(void);\nint n311_load_image(void);\n'+p.ordinary(target))
    for leaf,source_name in [('include/linux/n303_mmuoff_contract.h','v303_mmuoff_contract.h'),
                             ('lib/n303_snapshot_claim.inc','v303_snapshot_claim.inc'),
                             ('arch/arm64/kernel/n304_abi_contract.h','v311_abi_contract.h'),
                             ('arch/arm64/kernel/runtime_relocation.h','runtime_relocation.h'),
                             ('arch/arm64/kernel/n10_runtime_relocation.c','runtime_relocation.c'),
                             ('arch/arm64/kernel/n304_terminal_abi.c','v311_terminal_abi.c'),
                             ('arch/arm64/kernel/n304_terminal_abi_stub.S','v311_terminal_abi_stub.S'),
                             ('arch/arm64/mm/n311_xnu_window.c','v311_xnu_window.c')]:
        path=source/leaf;require(not path.exists(),'fresh own v311 source');path.write_bytes(buffers[repo_path(source_name)])
    # v311: one memblock window reservation at the end of arm64_memblock_init (device-proven v4 call site).
    init=source/'arch/arm64/mm/init.c';raw=p.ordinary(init)
    require(raw.count(INIT_RESIZE)==1 and raw.count(INIT_DECLARATION)==1 and b'n311_' not in raw,'exact stock memblock anchors')
    raw=raw.replace(INIT_DECLARATION,b'#include "n311_xnu_window.c"\n\n'+INIT_DECLARATION,1)
    init.write_bytes(raw.replace(INIT_RESIZE,b'\n\tn311_reserve_window();\n'+INIT_RESIZE,1))
    snapshot=source/'lib/debug-snapshot.c';snapshot.write_bytes(snapshot_overlay(p.ordinary(snapshot)))
    makefile=source/'arch/arm64/kernel/Makefile'
    raw=p.ordinary(makefile);require(b'n304_terminal_abi' not in raw and b'n10_runtime_relocation' not in raw and b'n303_mmuoff' not in raw,'fresh private route link rule')
    makefile.write_bytes(raw+b'\nifeq ($(CONFIG_NOTE10_BUILTIN_INIT_ROUTE)$(CONFIG_NOTE10_V154_LINUX_DIAGNOSTIC),yy)\nobj-y += cpu-reset.o n10_runtime_relocation.o n304_terminal_abi.o n304_terminal_abi_stub.o\nendif\n')
    names=set(result['twrp_route_source_sha256'])|{'drivers/misc/v302_park.inc','include/linux/n303_mmuoff_contract.h',
          'lib/debug-snapshot.c','lib/n303_snapshot_claim.inc','drivers/samsung/debug/sec_debug_last_kmsg.c',
          'arch/arm64/kernel/Makefile','arch/arm64/kernel/n304_terminal_abi.c','arch/arm64/kernel/n304_terminal_abi_stub.S',
          'arch/arm64/kernel/n304_abi_contract.h','arch/arm64/kernel/runtime_relocation.h','arch/arm64/kernel/n10_runtime_relocation.c',
          'arch/arm64/kernel/cpu-reset.h','arch/arm64/kernel/cpu-reset.S','arch/arm64/kernel/vmlinux.lds.S',
          'arch/arm64/include/asm/mmu_context.h','arch/arm64/include/asm/assembler.h','arch/arm64/mm/cache.S',
          'arch/arm64/mm/init.c','arch/arm64/mm/n311_xnu_window.c'}
    result['twrp_route_source_sha256']={name:p.sha(p.ordinary(source/name)) for name in sorted(names)}
    result.update(mmuoff_route='stock-idmap-EL1-own-v311-window-xnu-image-header-hash-and-v310-adt-checked-stub',park_MMU_changed=True,KEXEC_enabled=False,XNU=False,new_reservation_bytes=268435456,
                  XNU_image_loaded_by_CI=False,XNU_image_runtime_path='/tmp/n10-v311-kernel.mem',
                  witness='N311PS2T ASCII record after window boot_args geometry, loaded XNU Mach-O header and whole-image word-FNV (r[2]=ticks<<32|hash), ADT walk, memory-map, chosen DRAM span (r[3]=dram-size), root /defaults node, MPIDR/CNTFRQ and CNTVCT checks; commit byte T written before cursor advance',
                  normal_RECOVERY_modified=False,pretransition_refusal_releases_only_owned_request=True,
                  posttransition_software_escape=False,physical_arming_authorized=False)
    return result




def image_proof(raw,symbols,identity):
    value=retained.retained.image_proof(raw,symbols,identity);table=symbol_table(symbols);proof={}
    for name in FLOW_FUNCTIONS:
        found=table.get(name,[]);require(len(found)==1 and found[0]['type'] in ('T','t') and 0<found[0]['bytes']<=8192,'actual linked transition/owner/stock barrier')
        proof[name]=found[0]
    start=table.get('__idmap_text_start',[]);end=table.get('__idmap_text_end',[])
    require(len(start)==len(end)==1 and 0<end[0]['address']-start[0]['address']<=4096,'fresh linked stock4KiB idmap bound')
    for name in ('__cpu_soft_restart','n304_post_abi'):
        require(start[0]['address']<=proof[name]['address'] and proof[name]['address']+proof[name]['bytes']<=end[0]['address'],'whole physical trampoline/stub in idmap')
    value.update(park_functions=proof,idmap=dict(start=start[0]['address'],end=end[0]['address'],bytes=end[0]['address']-start[0]['address']))
    return value


def stub_proof(text,entry):
    rows=[]
    for m in re.finditer(r'^[ \t]*([0-9a-f]+):[ \t]+[0-9a-f]{8}[ \t]+(\S+)(?:[ \t]+([^\r\n]*))?$',text,re.M):
        address=int(m[1],16)
        if entry['address']<=address<entry['address']+entry['bytes']:rows.append((address,m[2],m[3] or ''))
    # v311 raises the self-imposed stub bound from <=512 rows/<=2048 B to <=640/<=2560: the hard limit is the single
    # 4 KiB idmap page (whole idmap <=4096 in image_proof, unchanged and authoritative). The window geometry, Mach-O
    # header and whole-image hash checks add about 51 instructions (502 -> 553 rows, 2008 -> 2212 B with the v310
    # local method); dropping v310 checks to fit would remove regression coverage.
    require(8<=len(rows)<=640 and entry['bytes']<=2560,'bounded physical-only stub')
    require(all(row[1] not in ('bl','blr','ret','hvc','smc','svc','wfi','wfe','adr','adrp') and 'sp' not in re.split(r'[^a-z0-9_]',row[2]) for row in rows),'no call/stack/external address/power instruction')
    reads={row[2].split(',')[-1].strip().lower() for row in rows if row[1]=='mrs'}
    require(reads=={'currentel','daif','sctlr_el1','mpidr_el1','cntfrq_el0','cntvct_el0'},'exact EL/DAIF/SCTLR, MPIDR/CNTFRQ and CNTVCT reads')
    require(not any(row[1]=='msr' for row in rows),'no system-register write')
    for address,mnemonic,operands in rows:
        if mnemonic=='b' or mnemonic.startswith('b.'):
            target=operands.split()[0];require(re.fullmatch('[0-9a-f]+',target) and entry['address']<=int(target,16)<entry['address']+entry['bytes'],'every stub branch stays inside source-owned range')
    require(rows[-2][1]=='yield' and rows[-1][1]=='b' and int(rows[-1][2].split()[0],16)==rows[-2][0],'compiled terminal yield/backedge')
    return dict(passed=True,address=entry['address'],bytes=entry['bytes'],instruction_count=len(rows),no_return=True,no_external_calls=True,no_stack=True,runtime_MMUoff_proven=False)


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
            # n304_prepare_args inlines the 13-node, 43-property n310_adt; its log is bounded by the 8192-byte symbol
            # limit above (<=2048 instructions at ~57 log bytes each). Other flow logs keep 32768.
            raw=p.ordinary(out/(label+'.log'),131072 if logical=='n304_prepare_args' else 32768);total+=len(raw)
            require(total<=196608,'bounded total park flow evidence')
            entries.append(dict(item,logical=logical,log=label+'.log',sha256=p.sha(raw),log_bytes=len(raw)))
            if logical=='n304_post_abi':spin=stub_proof(raw.decode(),item)
    require(spin is not None,'actual compiled own MMU-off stub proof')
    return dict(schema='note10-v311-bounded-park-flow-v1',passed=True,functions=entries,spin=spin,
                static_scope='linked owner/transition/stock barrier/idmap stub; no runtime MMUoff claim',
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
    result = dict(schema='note10-v311-xnu-load-r1-build-v1', version='v311', passed=False,
                  source_head=head, source_sha256=context['source_sha256'], public_input=context,
                  build_evidence_id=identity, run_id=int(os.environ['GITHUB_RUN_ID']), run_attempt=1,
                  full_Image_build_attempts=0, old_tests_replayed=0, physical_ready=False,
                  XNU_execution=False, watchdog_armed=False, new_MMIO=False, BOOT_writes=0,
                  PID1_produced=False, custom_CPIO_produced=False, custom_reservation_bytes=268435456, XNU_image_loaded_by_CI=False, builtin_TWRP_patch_required=True, hardware_WDT_trigger=False, stages={})
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
                and b'CONFIG_HAVE_NMI_WATCHDOG=y' not in config.splitlines()
                and b'CONFIG_KEXEC=y' not in config.splitlines() and b'CONFIG_CFI_CLANG=y' not in config.splitlines(),'stock all-online and nonhardware NMI-touch/logging contract')
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
        require(match and match[1].endswith('-v311-xnu-load-r1'), 'exact diagnostic kernel release')
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
    p.save(out/'members.json',dict(schema='note10-v311-xnu-load-r1-sealed-members-v1',source_head=head,
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
