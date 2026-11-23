"""v339 XNU ramdisk root: public change is the boot input contract (CommandLine "-v n10diag=305 rd=md0", 21 bytes; /chosen/memory-map nProps 4 with a RAMDisk property {H + 0x2000, 0x2000} right after DeviceTree, the zero tail of the handoff page; n310_adt size 2592 -> 2644; node count 14 unchanged) and the record tag (N339PS20/N339PS2T, new build names); the v316 stub/Linux C and the v321 validator are reused byte-identical; the XNU-side boot-path change is a private image patch CI never sees. Unchanged from v338: the record tag mechanism (N338PS20/N338PS2T). Unchanged from v337: the record tag mechanism (N337PS20/N337PS2T). Unchanged from v336: the record tag mechanism (N336PS20/N336PS2T). Unchanged from v335: the record tag mechanism (N335PS20/N335PS2T). Unchanged from v334: the record tag mechanism (N334PS20/N334PS2T). Unchanged from v333: the record tag mechanism (N333PS20/N333PS2T). Unchanged from v332: the record tag mechanism (N332PS20/N332PS2T). Unchanged from v331: the record tag mechanism (N331PS20/N331PS2T). Unchanged from v330: the record tag mechanism (N330PS20/N330PS2T). Unchanged from v329: the record tag mechanism (N329PS20/N329PS2T). Unchanged from v328: the record tag mechanism (N328PS20/N328PS2T). Unchanged from v327: the record tag mechanism (N327PS20/N327PS2T). Unchanged from v326: the record tag mechanism (N326PS20/N326PS2T). Unchanged from v325: the record tag mechanism (N325PS20/N325PS2T). Unchanged from v324: the record tag mechanism (N324PS20/N324PS2T). Unchanged from v323: the record tag mechanism (N323PS20/N323PS2T). Unchanged from v322: the record tag mechanism (N322PS20/N322PS2T). Unchanged from v321: the ADT node /chosen/note10-platform (second /chosen child after memory-map: compatible samsung,exynos9825-note10, version 1, gic-handoff 1, gic-reg {GICD 0x10101000/0x1000, GICC 0x10102000/0x1000}, timer-intid 30, timebase-frequency = the cpu0 frequency; n310_adt size 2240 -> 2592, record n= 14 nodes), a copy of the ADT validator (v321_runtime_relocation.c) that allows the gic-handoff property key (a node named gic-handoff stays rejected; runtime_relocation.c is untouched for earlier builds) and the record tag (N321PS20/N321PS2T, new build names); the v316 stub and Linux C are reused byte-identical; the XNU-side checkpoint/markers are a private image patch CI never sees. Unchanged from v320: the record tag mechanism (N320PS20/N320PS2T). Unchanged from v319: two contract constants (N311_VIRT_BASE 0xfffffe0006000000, N312_LINK_BASE 0xfffffe0007004000 for the privately slid XNU image) plus the record tag (N319PS20/N319PS2T, new build names); the v316 stub and Linux C are reused byte-identical (only the assembled virtBase movk immediates change); the image slide is a private host step CI never sees. Unchanged from v318: the record tag mechanism. Unchanged from v317: the ADT gains /chosen random-seed (256 bytes, public synthetic constant 1 + i % 255) after dram-size and the ADT storage/max grow to 4096 (contract only; the v316 terminal_abi.c and stub are reused byte-identical, the stub ADT max compare now assembles with 4096); the N317PS2T record is committed as in v316. Unchanged from v316: Linux copies the checked arena boot_args/ADT into the handoff page H = B + kernel offset + image_bytes (right after the image), boot_args topOfKernelData/deviceTreeP and the ADT memory-map describe H, the stub proves the H copy word by word and branches with 'isb; mov x0, x20; br x18' (x0 = H); the N316PS2T record is committed as in v313. Unchanged from v315: the v313 window/image load, LC_UNIXTHREAD entry parse, pre-branch gates; Linux requires the record + three 8-byte checkpoint crumb span (274 B) to fit before the dss log end and stay disjoint from the window and the cursor, the stub's Block B cleans that whole span, and boot_args memSize is N315_BOOT_MEMSIZE (kernel offset + 32 MiB, the XNU bootstrap builder limit; the stub checks memSize and the image end against it). The crumbs themselves are written by a private XNU-side image patch that CI never sees. Build and static proof only; XNU progress is never claimed by CI."""
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
WORKFLOW='.github/workflows/note10-v339-xnu-ramdisk-root-r1.yml'
JOB='v339-xnu-ramdisk-root-r1'
OUTPUT=ROOT/'note10/private/v339-ci-xnu-ramdisk-root-r1'
SETTINGS=dict(retained.SETTINGS,LOCALVERSION='"-v339-xnu-ramdisk-root-r1"')
CONTEXT_SCHEMA='note10-v339-xnu-ramdisk-root-r1-public-input-v1'
# v339 new cases only: groups, variants and CHECK assertions as declared by v339_tag_fixture.c (FIXTURE_GROUPS,
# FIXTURE_VARIANTS, EXPECTED_CHECKS): N339PS20 kernel/host format tags and record length, N339PS2T validator, and the
# v339 contract group (n310_adt with the memory-map RAMDisk accepted by the validator; CommandLine with rd=md0).
FIXTURE_COUNTS=(3,6,6)
PROOF_FUNCTIONS=retained.PROOF_FUNCTIONS
PARK_LOGS={f'15-park-{i}.log' for i in range(18)}
CORE_MEMBERS=retained.CORE_MEMBERS|{'park-flow.json'}
HELPER_LOGS=retained.HELPER_LOGS
ALLOWED_MEMBERS=CORE_MEMBERS|HELPER_LOGS|PARK_LOGS|{'outlined-worker.json'}
# v312_xnu_window.c, v316_terminal_abi.c and v316_terminal_abi_stub.S are reused byte-identical (installed against the v339 contract).
# v321_runtime_relocation.c is reused byte-identical (installed as n10_runtime_relocation.c and linked into the fixture).
NEW_FILES=('v339_prepare.py','v303_mmuoff_contract.h','v303_snapshot_claim.inc','v339_abi_contract.h',
           'runtime_relocation.h','v321_runtime_relocation.c','v316_terminal_abi.c','v316_terminal_abi_stub.S',
           'v312_xnu_window.c','v339_host_record.h','v339_host_record_validate.h','v339_tag_fixture.c')
# v315 grep-level C proof: the record span (274) is used by both record disjoint checks and by the log-tail refusal;
# no record disjoint check keeps the 250-byte length.
C_SPAN_USES=(b'n304_disjoint(slot.record, N315_RECORD_SPAN, args, N311_WINDOW_BYTES)',
             b'n304_disjoint(slot.record, N315_RECORD_SPAN, slot.cursor, sizeof(uint32_t))',
             b'slot.tail < N315_RECORD_SPAN')
# v316 contract C proof: n311_arguments sets topOfKernelData to the handoff page end and deviceTreeP to the KVA of the ADT
# copy at H + N306_ADT_OFFSET; memSize stays N315_BOOT_MEMSIZE and memSizeActual the window.
C_ARGS_USES=(b'        .memory_size = N315_BOOT_MEMSIZE,\n',
             b'        .top_of_kernel = base + N311_KERNEL_OFFSET + image_bytes + N316_HANDOFF_BYTES,\n',
             b'        .device_tree_pointer = N311_VIRT_BASE + N311_KERNEL_OFFSET + image_bytes + N306_ADT_OFFSET,\n',
             b'        .memory_size_actual = N311_WINDOW_BYTES,\n')
# v316 Linux C proof: the ADT memory-map values describe H, prepare copies the checked args/ADT into H, enter refuses on
# either copy hash and cleans the image plus the handoff page.
C_HANDOFF_USES=(b'    handoff = base + N311_KERNEL_OFFSET + meta->image_bytes;\n',
                b'    adt_bytes = n310_adt(arena->view.adt, compatible, length + 1, handoff, regs, N307_CPUS, (uint32_t)frequency,\n',
                b'    memset(copy, 0, N316_HANDOFF_BYTES);\n',
                b'    memcpy(copy, arena->view.args, N304_ARGS_BYTES);\n',
                b'    memcpy(copy + N306_ADT_OFFSET, arena->view.adt, adt_bytes);\n',
                b'    copy = phys_to_virt(args + N311_KERNEL_OFFSET + meta->image_bytes);\n',
                b'        n304_fnv(copy, N304_ARGS_BYTES) != meta->args_hash ||\n',
                b'        n304_fnv(copy + N306_ADT_OFFSET, meta->adt_bytes) != meta->adt_hash)\n',
                b'    __flush_dcache_area(phys_to_virt(args + N311_KERNEL_OFFSET), meta->image_bytes + N316_HANDOFF_BYTES);\n')
# v317 contract C proof: ADT storage/max 4096, /chosen nProps 4 and the random-seed property after dram-size (v321: /chosen
# nChildren 2; v339: size 2644 + and memory-map nProps 4).
C_SEED_USES=(b'#define N307_ADT_STORAGE 4096 ',b'#define N307_ADT_MAX_BYTES 4096 ',b'#define N317_SEED_BYTES 256 ',
             b'    size = 2644 + ((count + 3) & ~3U);',
             b'    at = n306_node(out, at, 4, 2);\n    at = n306_prop(out, at, "name", "chosen", 7);\n',
             b'    at = n306_prop(out, at, "dram-size", value, 8);\n    for (i = 0; i < N317_SEED_BYTES; ++i)',
             b'        out[at + 36 + i] = (uint8_t)(1 + i % 255);\n    at = n306_prop(out, at, "random-seed", out + at + 36, N317_SEED_BYTES);\n    at = n306_node(out, at, 4, 0);\n')
# v319 contract C proof: the slid XNU virtBase/link base defines (the old 0xfffffff0 values are gone).
C_VA_USES=(b'#define N311_VIRT_BASE 0xfffffe0006000000 ',b'#define N312_LINK_BASE 0xfffffe0007004000ULL ',
           b'_Static_assert((N311_VIRT_BASE >> 47) == 0x1ffff, ',
           b'_Static_assert(((N311_VIRT_BASE + N311_KERNEL_OFFSET + 0x2000000 - 1) >> 47) == 0x1ffff, ')
# v321 contract C proof: the /chosen/note10-platform node right after the memory-map (v339: after its RAMDisk property),
# its plain constants, the 32-byte value buffer and the largest-ADT assert (v339: 2644).
C_PLATFORM_USES=(b'#define N321_GICD_BASE 0x10101000\n',b'#define N321_GICC_BASE 0x10102000\n',b'#define N321_GIC_SIZE 0x1000\n',
                 b'#define N321_TIMER_INTID 30\n',b'#define N321_PLATFORM_VERSION 1\n',b'    uint8_t value[32];\n',
                 b'_Static_assert(2644 + N304_COMPAT_BYTES <= N307_ADT_STORAGE, ',
                 b'    at = n306_prop(out, at, "RAMDisk", value, 16);\n'
                 b'    /* v321: /chosen/note10-platform (second /chosen child): timebase-frequency is the cpu0 frequency. */\n'
                 b'    at = n306_node(out, at, 7, 0);\n'
                 b'    at = n306_prop(out, at, "name", "note10-platform", 16);\n'
                 b'    at = n306_prop(out, at, "compatible", "samsung,exynos9825-note10", 26);\n'
                 b'    n306_put32(value, N321_PLATFORM_VERSION);\n'
                 b'    at = n306_prop(out, at, "version", value, 4);\n'
                 b'    n306_put32(value, 1);\n'
                 b'    at = n306_prop(out, at, "gic-handoff", value, 4);\n'
                 b'    n306_put64(value, N321_GICD_BASE);\n'
                 b'    n306_put64(value + 8, N321_GIC_SIZE);\n'
                 b'    n306_put64(value + 16, N321_GICC_BASE);\n'
                 b'    n306_put64(value + 24, N321_GIC_SIZE);\n'
                 b'    at = n306_prop(out, at, "gic-reg", value, 32);\n'
                 b'    n306_put32(value, N321_TIMER_INTID);\n'
                 b'    at = n306_prop(out, at, "timer-intid", value, 4);\n'
                 b'    n306_put32(value, frequency);\n'
                 b'    at = n306_prop(out, at, "timebase-frequency", value, 4);\n'
                 b'    at = n306_node(out, at, 1, N307_CPUS);\n')
# v339 contract C proof: the 21-byte CommandLine with rd=md0, the two RAMDisk constants and their asserts, memory-map
# nProps 4 and the RAMDisk property {base + N339_RAMDISK_OFFSET, N339_RAMDISK_BYTES} right after DeviceTree.
C_RAMDISK_USES=(b'#define N305_COMMAND "-v n10diag=305 rd=md0" ',b'#define N305_COMMAND_BYTES 21\n',
                b'#define N339_RAMDISK_OFFSET 0x2000\n',b'#define N339_RAMDISK_BYTES 0x2000\n',
                b'_Static_assert(N306_ADT_OFFSET + N307_ADT_STORAGE <= N339_RAMDISK_OFFSET, ',
                b'_Static_assert(N339_RAMDISK_OFFSET + N339_RAMDISK_BYTES == N316_HANDOFF_BYTES, ',
                b'_Static_assert(N339_RAMDISK_OFFSET % 4096 == 0 && N339_RAMDISK_BYTES % 4096 == 0, ',
                b'    at = n306_node(out, at, 4, 0);\n    at = n306_prop(out, at, "name", "memory-map", 11);\n',
                b'    at = n306_prop(out, at, "DeviceTree", value, 16);\n'
                b'    n306_put64(value, base + N339_RAMDISK_OFFSET); /* v339: memory-map RAMDisk (handoff page tail) */\n'
                b'    n306_put64(value + 8, N339_RAMDISK_BYTES);\n'
                b'    at = n306_prop(out, at, "RAMDisk", value, 16);\n'
                b'    /* v321: /chosen/note10-platform (second /chosen child): timebase-frequency is the cpu0 frequency. */\n')
# v321 validator proof: the property-key gic_name term is removed, the node-name gic_name check stays.
V321_KEY_LINE=b'        if(!key_length || key_length==32)return 0;\n'
V321_NAME_LINE=b'            if(gic_name(c->raw+value_at,length-1))return 0;\n'
# GNU/LLVM spellings of the reused stub's 'cmp w25, #N307_ADT_MAX_BYTES' with 4096 (operand_key form).
ADT_MAX_KEYS=(('cmp','w25,#4096'),('cmp','w25,#1,lsl#12'))
RECORD_BYTES,RECORD_SPAN=250,274  # N304_RECORD_BYTES, N315_RECORD_SPAN
BOOT_MEMSIZE=0x3004000  # N315_BOOT_MEMSIZE
HANDOFF_BYTES,ADT_OFFSET,ARGS_BYTES=0x4000,2048,1152  # N316_HANDOFF_BYTES, N306_ADT_OFFSET, N304_ARGS_BYTES
STUB_ROWS=617  # v316 stub reused byte-identical (v315 599 + 18); v317 only changes the ADT max immediate (4096)
FLOW_FUNCTIONS=('n302_park_write','n312_load_image','n302_cpu0','stop_machine','stop_machine_cpuslocked','multi_cpu_stop','n304_prepare_args','n304_enter','n303_snapshot_claim','__cpu_soft_restart','n304_post_abi')
INIT_RESIZE=b'\n\tmemblock_allow_resize();\n}\n'
INIT_DECLARATION=b'void __init arm64_memblock_init(void)'
PARK_STOP=b'    return stop_machine(n302_cpu0,NULL,cpumask_of(0));'
LOAD_CALL=b'    { int error=n312_load_image(); if (error) return error; }\n'
LOAD_PROTOTYPE=b'int n312_load_image(void);\n'



def repo_path(name):
    # runtime_relocation.h lives with the XNU 26 sources; everything else is under device_test.
    return 'note10/xnu26/'+name if name in ('runtime_relocation.h','runtime_relocation.c','v321_runtime_relocation.c') else 'note10/device_test/'+name


def source_pins():
    pins=retained.source_pins();pins.pop(retained.WORKFLOW)
    for name in NEW_FILES:
        path=repo_path(name);pins[path]=p.sha(p.ordinary(ROOT/path))
    pins[WORKFLOW]=p.sha(p.ordinary(ROOT/WORKFLOW));return pins


def public_context(head,passed):
    p.hexid(head,40)
    require(set(passed)=={'passed','groups','variants','assertions','result_sha256'} and passed['passed'] is True
            and tuple(passed[k] for k in ('groups','variants','assertions'))==FIXTURE_COUNTS,'v339 host fixture cases only')
    p.hexid(passed['result_sha256'])
    return dict(schema=CONTEXT_SCHEMA,source_head=head,source_sha256=source_pins(),new_fixture_PASS=passed,old_tests_replayed=False)


def return_overlay(raw):
    require(raw.count(b'    n302_spin();')==1 and b'n303_enter' not in raw and b'n304_enter' not in raw,'single retained302 terminal tail')
    # v311/v312: the image is loaded (and its entry parsed) once in process context; any failure returns before
    # stop_machine (no transfer).
    require(raw.count(PARK_STOP)==1 and b'n311_' not in raw and b'n312_' not in raw,'single retained302 park_write stop_machine')
    raw=raw.replace(PARK_STOP,LOAD_CALL+PARK_STOP,1)
    return raw.replace(b'    n302_spin();',b'    { int error=n304_prepare_args(N154_BUILD_ID,n10_boot_id,(const char *)n10_cycle);\n      if (!error) error=n304_enter();\n      /* Only our request claim is undone; attempted/prepared remain spent. */\n      atomic_cmpxchg(&n10_return_requested,1,0);atomic_set(&n302_committed,0);return error; }',1)


def snapshot_overlay(raw):
    require(raw.endswith(b'\n') and b'n303_snapshot_claim.inc' not in raw,'fresh stock snapshot owner include')
    return raw+b'\n#if IS_ENABLED(CONFIG_NOTE10_BUILTIN_INIT_ROUTE) && IS_ENABLED(CONFIG_NOTE10_V154_LINUX_DIAGNOSTIC)\n#include "n303_snapshot_claim.inc"\n#endif\n'


def c_span_proof(raw,contract):
    require(all(raw.count(use)==1 for use in C_SPAN_USES) and b'n304_disjoint(slot.record, N304_RECORD_BYTES' not in raw,
            'v315 record span in both record disjoint checks and the log-tail refusal')
    require(all(contract.count(use)==1 for use in C_ARGS_USES) and b'.memory_size = N311_WINDOW_BYTES' not in contract
            and b'.device_tree_pointer = N311_VIRT_BASE + N306_ADT_OFFSET,' not in contract,
            'v316 n311_arguments H-layout topOfKernelData/deviceTreeP, memSize N315_BOOT_MEMSIZE and memSizeActual N311_WINDOW_BYTES')
    require(all(raw.count(use)==1 for use in C_HANDOFF_USES) and b'n310_adt(arena->view.adt, compatible, length + 1, base,' not in raw
            and raw.count(b'__flush_dcache_area(phys_to_virt(args + N311_KERNEL_OFFSET), ')==1,
            'v316 handoff n310_adt base, H copy, copy hash refusal and image + handoff flush')
    require(all(contract.count(use)==1 for use in C_SEED_USES) and b'1948 +' not in contract and b'2240 +' not in contract
            and b'2592 +' not in contract and b'n306_node(out, at, 3, 0)' not in contract
            and b'n306_node(out, at, 3, 1)' not in contract and b'n306_node(out, at, 4, 1)' not in contract,
            'v317 ADT storage/max 4096, /chosen nProps 4, random-seed after dram-size; v321 /chosen nChildren 2; v339 size '
            '2644 + and memory-map nProps 4')
    require(all(contract.count(use)==1 for use in C_PLATFORM_USES) and contract.count(b'uint8_t value[16];')==0,
            'v321 /chosen/note10-platform node after the memory-map RAMDisk, plain GIC constants, 32-byte value buffer and '
            '2644 assert')
    require(all(contract.count(use)==1 for use in C_RAMDISK_USES) and contract.count(b'"RAMDisk"')==1
            and b'#define N305_COMMAND "-v n10diag=305"' not in contract and b'N305_COMMAND_BYTES 14' not in contract,
            'v339 CommandLine rd=md0 (21 bytes), RAMDisk constants/asserts, memory-map nProps 4 and RAMDisk after DeviceTree')
    require(all(contract.count(use)==1 for use in C_VA_USES) and b'0xfffffff006000000' not in contract
            and b'0xfffffff007004000' not in contract,'v319 slid virtBase/link base defines and builder VA asserts')
    return dict(passed=True,va_uses=[use.decode().strip() for use in C_VA_USES],uses=[use.decode() for use in C_SPAN_USES],args_uses=[use.decode().strip() for use in C_ARGS_USES],
                handoff_uses=[use.decode().strip() for use in C_HANDOFF_USES],seed_uses=[use.decode().strip() for use in C_SEED_USES],
                platform_uses=[use.decode().strip() for use in C_PLATFORM_USES],
                ramdisk_uses=[use.decode().strip() for use in C_RAMDISK_USES])


def validator_proof(raw):
    require(raw.count(V321_KEY_LINE)==1 and raw.count(V321_NAME_LINE)==1 and raw.count(b'gic_name(')==2
            and b'gic_name(c->raw+key_at' not in raw,'v321 validator: gic-handoff key allowed, node-name check kept')
    return dict(passed=True,key_line=V321_KEY_LINE.decode().strip(),name_line=V321_NAME_LINE.decode().strip())


def install(source,identity,buffers):
    result=retained.install(source,identity,buffers)
    target=source/'drivers/misc/v302_park.inc';target.write_bytes(return_overlay(p.ordinary(target)))
    # Prototype remains in normal kernel lifetime with the existing park TU.
    target.write_bytes(b'#include <linux/n303_mmuoff_contract.h>\nint n304_prepare_args(const char *build, const char *boot, const char *cycle);\nint n304_enter(void);\n'+LOAD_PROTOTYPE+p.ordinary(target))
    raw=p.ordinary(target);require(raw.count(LOAD_PROTOTYPE)==1 and raw.count(LOAD_CALL)==1 and raw.count(b'n312_load_image')==2,'v312 load prototype and call each exactly once')
    for leaf,source_name in [('include/linux/n303_mmuoff_contract.h','v303_mmuoff_contract.h'),
                             ('lib/n303_snapshot_claim.inc','v303_snapshot_claim.inc'),
                             ('arch/arm64/kernel/n304_abi_contract.h','v339_abi_contract.h'),
                             ('arch/arm64/kernel/runtime_relocation.h','runtime_relocation.h'),
                             ('arch/arm64/kernel/n10_runtime_relocation.c','v321_runtime_relocation.c'),
                             ('arch/arm64/kernel/n304_terminal_abi.c','v316_terminal_abi.c'),
                             ('arch/arm64/kernel/n304_terminal_abi_stub.S','v316_terminal_abi_stub.S'),
                             ('arch/arm64/mm/n311_xnu_window.c','v312_xnu_window.c')]:
        path=source/leaf;require(not path.exists(),'fresh own v339 source');path.write_bytes(buffers[repo_path(source_name)])
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
    result.update(mmuoff_route='stock-idmap-EL1-own-v311-window-xnu-image-header-hash-v312-entry-target-v313-gated-xnu-branch-v315-checkpoint-span-boot-memsize-v316-handoff-page-v317-random-seed-v318-tag-v319-slid-vm-layout-v320-tag-v321-platform-node-v322-tag-v323-tag-v324-tag-v325-tag-v326-tag-v327-tag-v328-tag-v329-tag-v330-tag-v331-tag-v332-tag-v333-tag-v334-tag-v335-tag-v336-tag-v337-tag-v338-tag-v339-ramdisk-contract-and-v310-adt-checked-stub',park_MMU_changed=True,KEXEC_enabled=False,XNU=True,entry_branch_compiled=True,xnu_checkpoint_crumbs_supported=True,runtime_XNU_progress_proven=False,new_reservation_bytes=268435456,boot_args_memsize=BOOT_MEMSIZE,
                  handoff_bytes=HANDOFF_BYTES,random_seed_bytes=256,adt_storage_bytes=4096,adt_bytes_base=2644,
                  command_line='-v n10diag=305 rd=md0',ramdisk=dict(offset=0x2000,bytes=0x2000,property='RAMDisk'),
                  c_span_proof=c_span_proof(buffers[repo_path('v316_terminal_abi.c')],buffers[repo_path('v339_abi_contract.h')]),
                  validator_proof=validator_proof(buffers[repo_path('v321_runtime_relocation.c')]),adt_platform_node=True,
                  XNU_image_loaded_by_CI=False,XNU_image_runtime_path='/tmp/n10-v311-kernel.mem',
                  witness='N339PS2T ASCII record (v321 ADT with /chosen/note10-platform and the v339 memory-map RAMDisk {H + 0x2000, 0x2000}, 14 nodes; CommandLine rd=md0; XNU-side private patch only; v319 layout; virtBase 0xfffffe0006000000 (slid private XNU image)) after window boot_args geometry (v315: memSize = kernel offset + 32 MiB; v316: deviceTreeP/topOfKernelData/memory-map on the handoff page H; v317: ADT with 256-byte /chosen random-seed), loaded XNU Mach-O header and whole-image word-FNV (r[2]=ticks<<32|hash), Linux-parsed LC_UNIXTHREAD entry offset bounds and entry word load (r[3]=entry_offset<<32|word), v313 entry-B/TGran16/PA-limit gates and dc civac of the record+checkpoint crumb span (v315: 274 B) and cursor lines, ADT walk, memory-map, chosen DRAM span containment, root /defaults node, MPIDR/CNTFRQ and CNTVCT checks; commit byte T written before cursor advance, handoff copy compare, then the single br x18 to the XNU entry with x0=H (handoff copy of the checked args/ADT with 256-byte /chosen random-seed right after the image)',
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


# v313: the stub may read exactly these system registers (ID_AA64MMFR0_EL1 for the TGran16 gate, CTR_EL0 for the dc civac
# line size), never writes one, and contains exactly one branch-to-register: the XNU entry branch 'br x18' at the end of
# the commit tail below. x18 is written exactly once (Block A 'add x18, x7, x8' = B + kernel offset + entry_offset) and
# read only by that br; every other branch-to-register/call/return/exception-return/cache-or-TLB-maintenance form other
# than the two 'dc civac' (record and cursor lines) is refused.
# v314/v315: 'add x0, x3, #imm' occurs exactly twice: the record/cursor separation bound (250) and, immediately before the
# first 'dc civac, x9', the Block B clean bound (v315: 274 = record + three crumbs); the .Lcopy bound stays 'cmp x8, #250'.
# v315: x8 = N315_BOOT_MEMSIZE by exactly one 'mov x8, #0x3000000; movk x8, #0x4000' pair, followed (with no x8 write in
# between) by 'cmp x1, x8' (image end) and 'cmp x9, x8' (memSize); neither compare uses the window register x12.
# v316: x20 = H is written only at entry ('mov x20, x1') and by exactly one 'add x20, x19, x1', directly followed by the
# deviceTreeP compare against virtBase + (H - B) + 2048 and then 'add x1, x1, #0x4000' (handoff end) before 'cmp x1, x8';
# the memory-map BootArgs value is compared with 'ccmp x9, x20' and DeviceTree with 'add x11, x20, #2048; cmp x9, x11';
# the 14-row handoff compare loop (loads only) precedes the record work; the branch tail is 'isb; mov x0, x20; br x18'.
# v317: the reused stub's single ADT max compare 'cmp w25, #N307_ADT_MAX_BYTES' assembles with 4096 (GNU '#0x1, lsl #12').
STUB_READS={'currentel','daif','sctlr_el1','mpidr_el1','cntfrq_el0','cntvct_el0','id_aa64mmfr0_el1','ctr_el0'}
STUB_FORBIDDEN=('bl','blr','ret','hvc','smc','svc','wfi','wfe','adr','adrp','msr','eret','eretaa','eretab','braa','brab',
                'braaz','brabz','blraa','blrab','blraaz','blrabz','retaa','retab','ic','tlbi','at','sys','sysl')
XNU_TAIL=(('mov','w9,#84'),('strb','w9,[x3,#7]'),('dsb','sy'),('str','w5,[x4]'),('dsb','sy'),('isb',''),('mov','x0,x20'),('br','x18'))
X18_WRITER=('add','x18,x7,x8')


def operand_key(operands):
    # objdump operands without comment/whitespace; immediates normalized to decimal (GNU '#7' == LLVM '#0x7').
    text=re.sub(r'\s+','',operands.split('//')[0]).lower()
    return re.sub(r'#(0x[0-9a-f]+|[0-9]+)',lambda m:'#'+str(int(m[1],0)),text)


def stub_proof(text,entry,rows_expected=STUB_ROWS):
    rows=[]
    for m in re.finditer(r'^[ \t]*([0-9a-f]+):[ \t]+[0-9a-f]{8}[ \t]+(\S+)(?:[ \t]+([^\r\n]*))?$',text,re.M):
        address=int(m[1],16)
        if entry['address']<=address<entry['address']+entry['bytes']:rows.append((address,m[2],m[3] or ''))
    # Bound unchanged from v311 (<=640 rows/<=2560 B; the authoritative hard limit is the single 4 KiB idmap page,
    # checked in image_proof). v313 adds Block A 15 + Block B 13 + tail 3 = 31 instructions (566 -> 597 rows,
    # 2264 -> 2388 B with the v312 local method).
    require(8<=len(rows)<=640 and entry['bytes']<=2560,'bounded physical-only stub')
    require(len(rows)==rows_expected,'v316 stub row count (v315 599 + 18)')
    require(all(row[1] not in STUB_FORBIDDEN and 'sp' not in re.split(r'[^a-z0-9_]',row[2]) for row in rows),'no call/return/stack/external address/power/sysreg-write/maintenance instruction')
    reads={row[2].split(',')[-1].strip().lower() for row in rows if row[1]=='mrs'}
    require(reads==STUB_READS,'exact EL/DAIF/SCTLR, MPIDR/CNTFRQ, CNTVCT, MMFR0 and CTR reads')
    keys=[(row[1],operand_key(row[2])) for row in rows]
    cleans=[key for key in keys if key[0]=='dc']
    require(len(cleans)==2 and all(key[1].startswith('civac,') for key in cleans),'exactly two dc civac (record and cursor lines)')
    for address,mnemonic,operands in rows:
        if mnemonic=='b' or mnemonic.startswith('b.'):
            target=operands.split()[0];require(re.fullmatch('[0-9a-f]+',target) and entry['address']<=int(target,16)<entry['address']+entry['bytes'],'every stub branch stays inside source-owned range')
    require(rows[-2][1]=='yield' and rows[-1][1]=='b' and int(rows[-1][2].split()[0],16)==rows[-2][0],'compiled terminal yield/backedge')
    branches=[index for index,row in enumerate(rows) if row[1]=='br']
    require(len(branches)==1 and branches[0]==len(rows)-3 and tuple(keys[branches[0]-7:branches[0]+1])==XNU_TAIL,
            'single br x18 immediately after T commit, dsb sy, cursor store, dsb sy, isb, mov x0, x20')
    uses=[index for index,key in enumerate(keys) if {'x18','w18'}&set(re.split(r'[^a-z0-9]',key[1]))]
    require(len(uses)==2 and keys[uses[0]]==X18_WRITER and uses[1]==branches[0],'x18 written once by add x18, x7, x8 and read only by the br')
    bounds=[(index,int(key[1][len('x0,x3,#'):])) for index,key in enumerate(keys) if key[0]=='add' and key[1].startswith('x0,x3,#')]
    first_clean=keys.index(('dc','civac,x9')) if ('dc','civac,x9') in keys else -1
    require([value for _,value in bounds]==[RECORD_BYTES,RECORD_SPAN] and bounds[1][0]+1==first_clean,
            'v315 separation bound 250 then Block B clean bound 274 immediately before dc civac, x9')
    require(keys.count(('cmp','x8,#%d'%RECORD_BYTES))==1 and ('cmp','x8,#%d'%RECORD_SPAN) not in keys,'v315 record copy bound stays 250')
    pair=[index for index in range(len(keys)-1) if keys[index]==('mov','x8,#%d'%(BOOT_MEMSIZE&~0xffff))
          and keys[index+1]==('movk','x8,#%d'%(BOOT_MEMSIZE&0xffff))]
    require(len(pair)==1 and keys.count(('cmp','x1,x8'))==1 and keys.count(('cmp','x9,x8'))==1
            and ('cmp','x1,x12') not in keys and ('cmp','x9,x12') not in keys,'v315 N315_BOOT_MEMSIZE pair and both compares on x8')
    image_cmp,memsize_cmp=keys.index(('cmp','x1,x8')),keys.index(('cmp','x9,x8'))
    require(pair[0]+1<image_cmp<memsize_cmp and not any(re.match(r'[xw]8,',key[1]) for key in keys[pair[0]+2:memsize_cmp]),
            'v315 x8 live from the pair to the memSize compare')
    # GNU objdump prints the unsigned-condition aliases b.cc (lo) and b.cs (hs); LLVM prints b.lo/b.hs. Same encoding.
    names=[{'b.cc':'b.lo','b.cs':'b.hs'}.get(row[1],row[1]) for row in rows]
    target=lambda index:int(rows[index][2].split()[0],16)
    writes=[index for index,key in enumerate(keys) if key[0] not in ('cmp','ccmp','cmn','tst','str','strb','strh','stp','stur','sturb','sturh')
            and re.match(r'[xw]20,',key[1])]
    require([keys[index] for index in writes]==[('mov','x20,x1'),('add','x20,x19,x1')] and writes[0]<4,
            'v316 x20 written only at entry and by the single add x20, x19, x1')
    h=writes[1];ends=[index for index,key in enumerate(keys) if key in (('add','x1,x1,#%d'%HANDOFF_BYTES),('add','x1,x1,#%d,lsl#12'%(HANDOFF_BYTES>>12)))]
    require(keys[h+1:h+5]==[('add','x10,x11,x1'),('add','x10,x10,#%d'%ADT_OFFSET),('ldr','x9,[x19,#96]'),('cmp','x9,x10')]
            and names[h+5]=='b.ne' and ends==[h+6] and h+7==image_cmp and ('add','x10,x11,#%d'%ADT_OFFSET) not in keys,
            'v316 H, deviceTreeP = virtBase + (H - B) + 2048, handoff end before the image end compare')
    boot=[index for index,key in enumerate(keys) if key==('ccmp','x9,x20,#0,eq')]
    require(len(boot)==1 and keys[boot[0]-1]==('cmp','x10,#%d'%ARGS_BYTES) and ('ccmp','x9,x19,#0,eq') not in keys,
            'v316 memory-map BootArgs == H')
    tree=[index for index,key in enumerate(keys) if key==('add','x11,x20,#%d'%ADT_OFFSET)]
    require(len(tree)==1 and keys[tree[0]+1:tree[0]+3]==[('cmp','x9,x11'),('ccmp','x10,x25,#0,eq')] and ('cmp','x9,x6') not in keys,
            'v316 memory-map DeviceTree == H + 2048')
    require(sum(keys.count(key) for key in ADT_MAX_KEYS)==1 and ('cmp','w25,#2048') not in keys,'v317 ADT max compare 4096')
    loop=[index for index,key in enumerate(keys) if key==('ldr','w9,[x19,x7]')];a=loop[0] if len(loop)==1 else -1
    require(a>=2 and keys[a-2:a]==[('mov','x7,#0'),('mov','x8,#%d'%ARGS_BYTES)]
            and keys[a+1:a+3]==[('ldr','w10,[x20,x7]'),('cmp','w9,w10')] and names[a+3]=='b.ne'
            and keys[a+4:a+6]==[('add','x7,x7,#4'),('cmp','x7,x8')] and names[a+6]=='b.lo' and target(a+6)==rows[a][0]
            and keys[a+7]==('cmp','x7,#%d'%ADT_OFFSET) and names[a+8]=='b.hs' and target(a+8)==rows[a+12][0]
            and keys[a+9:a+11]==[('mov','x7,#%d'%ADT_OFFSET),('add','x8,x25,#%d'%ADT_OFFSET)]
            and names[a+11]=='b' and target(a+11)==rows[a][0] and tree[0]<a<bounds[0][0],
            'v316 handoff compare over args [0, 1152) and ADT [2048, 2048 + adt_bytes), loads only, before the record work')
    return dict(passed=True,address=entry['address'],bytes=entry['bytes'],instruction_count=len(rows),no_return=True,no_external_calls=True,no_stack=True,
                xnu_entry_branch=dict(count=1,register='x18',writer='add x18, x7, x8',writer_offset=rows[uses[0]][0]-entry['address'],
                                      branch_offset=rows[branches[0]][0]-entry['address'],tail=[' '.join(key).strip() for key in XNU_TAIL]),
                dc_civac_rows=2,clean_bound=RECORD_SPAN,separation_bound=RECORD_BYTES,copy_bound=RECORD_BYTES,
                boot_memsize=dict(value=BOOT_MEMSIZE,register='x8',image_end_compare='cmp x1, x8',memsize_compare='cmp x9, x8'),
                handoff=dict(bytes=HANDOFF_BYTES,register='x20',writer='add x20, x19, x1',bootargs='ccmp x9, x20',
                             devicetree='add x11, x20, #%d; cmp x9, x11'%ADT_OFFSET,compare_rows=14,branch_x0='mov x0, x20'),
                adt_max=4096,
                entry_branch_compiled=True,runtime_MMUoff_proven=False,runtime_XNU_progress_proven=False)


def stub_proof_selftest():
    """Synthetic GNU-objdump rows: the v316 rows are accepted; a second br, br x17, a missing isb, an extra x18 write, an msr,
    a third dc, dc ivac, a 250 or 266 Block B clean bound, a 274 separation bound, a 274 copy bound, the image end or memSize
    compared against the window register x12, a wrong movk immediate, an x8 write between the pair and the memSize compare,
    (v316) 'mov x0, x19' at the branch, 'ccmp x9, x19' in the BootArgs block, 'cmp x9, x6' in the DeviceTree block, a second
    x20 write, a missing handoff end add, a store in the handoff compare loop, (v317) an ADT max compare with 2048 and a row
    count other than the expected one are each refused."""
    base=[('mov','x20, x1'),('cmp','w25, #0x1, lsl #12'),('mrs','x9, currentel'),('mrs','x9, daif'),('mrs','x23, sctlr_el1'),('orr','x9, x20, x21'),
          ('mov','x8, #0x3000000             \t// #50331648'),('movk','x8, #0x4000'),
          ('add','x20, x19, x1'),('add','x10, x11, x1'),('add','x10, x10, #0x800'),('ldr','x9, [x19, #0x60]'),('cmp','x9, x10'),
          ('b.ne','PARK'),('add','x1, x1, #0x4, lsl #12'),('cmp','x1, x8'),('b.hi','PARK'),('cmp','x9, x8'),
          ('cmp','x10, #0x480'),('ccmp','x9, x20, #0x0, eq'),('b.ne','PARK'),
          ('add','x11, x20, #0x800'),('cmp','x9, x11'),('ccmp','x10, x25, #0x0, eq'),('b.ne','PARK'),
          ('mrs','x15, mpidr_el1'),('mrs','x9, cntfrq_el0'),
          ('mrs','x28, cntvct_el0'),('add','x18, x7, x8'),('mrs','x9, id_aa64mmfr0_el1'),('b.hi','PARK'),
          ('mov','x7, #0x0'),('mov','x8, #0x480'),('ldr','w9, [x19, x7]'),('ldr','w10, [x20, x7]'),('cmp','w9, w10'),('b.ne','PARK'),
          ('add','x7, x7, #0x4'),('cmp','x7, x8'),('b.cc','LOOP'),('cmp','x7, #0x800'),('b.cs','DONE'),('mov','x7, #0x800'),
          ('add','x8, x25, #0x800'),('b','LOOP'),
          ('add','x0, x3, #0xfa'),('mrs','x9, ctr_el0'),('add','x0, x3, #0x112'),
          ('dc','civac, x9'),('dc','civac, x4'),('dsb','sy'),('cmp','x8, #0xfa'),('mov','w9, #0x54                \t// #84'),('strb','w9, [x3, #7]'),
          ('dsb','sy'),('str','w5, [x4]'),('dsb','sy'),('isb',''),('mov','x0, x20'),('br','x18'),('yield',''),('b','PARK')]

    def render(items):
        start=0x1000;names=[row[0] for row in items]
        labels=dict(PARK=names.index('yield'),LOOP=items.index(('ldr','w9, [x19, x7]')) if ('ldr','w9, [x19, x7]') in items else 0,
                    DONE=items.index(('add','x0, x3, #0xfa')))
        def operand(text):
            for label,index in labels.items():
                text=text.replace(label,f'{start+4*index:x} <n304_post_abi+0x{4*index:x}>')
            return text
        lines=[f'    {start+4*index:x}:\t{0:08x} \t{mnemonic}'+(('\t'+operand(operands)) if operands else '')
               for index,(mnemonic,operands) in enumerate(items)]
        return '\n'.join(lines)+'\n',dict(address=start,bytes=4*len(items))

    def at(row):
        return base.index(row)

    def edited(index,row=None,insert=False):
        items=list(base)
        if insert:items.insert(index,row)
        elif row is None:del items[index]
        else:items[index]=row
        return items

    stub_proof(*render(base),rows_expected=len(base))
    rejects=[edited(at(('mrs','x9, id_aa64mmfr0_el1')),('br','x18'),True),edited(at(('br','x18')),('br','x17')),
             edited(at(('isb',''))),edited(at(('add','x0, x3, #0xfa')),('mov','x18, x0'),True),
             edited(at(('add','x0, x3, #0xfa')),('msr','daifset, #0xf'),True),edited(at(('dc','civac, x4')),('dc','civac, x5'),True),
             edited(at(('dc','civac, x4')),('dc','ivac, x4')),
             edited(at(('add','x0, x3, #0x112')),('add','x0, x3, #0xfa')),edited(at(('add','x0, x3, #0x112')),('add','x0, x3, #0x10a')),
             edited(at(('mrs','x9, ctr_el0')),('add','x0, x3, #0x112'),True),edited(at(('cmp','x8, #0xfa')),('cmp','x8, #0x112')),
             edited(at(('cmp','x1, x8')),('cmp','x1, x12')),edited(at(('cmp','x9, x8')),('cmp','x9, x12')),
             edited(at(('movk','x8, #0x4000')),('movk','x8, #0x8000')),edited(at(('b.hi','PARK')),('mov','x8, x0'),True),
             edited(at(('mov','x0, x20')),('mov','x0, x19')),edited(at(('ccmp','x9, x20, #0x0, eq')),('ccmp','x9, x19, #0x0, eq')),
             edited(at(('cmp','x9, x11')),('cmp','x9, x6')),edited(at(('mrs','x15, mpidr_el1')),('mov','x20, x0'),True),
             edited(at(('add','x1, x1, #0x4, lsl #12'))),edited(at(('cmp','w9, w10')),('str','w9, [x20, x7]')),
             edited(at(('cmp','w25, #0x1, lsl #12')),('cmp','w25, #0x800'))]
    for items in rejects:
        try:stub_proof(*render(items),rows_expected=len(items))
        except ValueError:continue
        raise AssertionError('v339 stub_proof admitted an invalid stub')
    try:stub_proof(*render(base))
    except ValueError:pass
    else:raise AssertionError('v339 stub_proof admitted a wrong row count')
    return dict(passed=True,accepted=1,refused=len(rejects)+1)


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
            # n304_prepare_args inlines the 13-node, 44-property (v317: + random-seed) n310_adt; its log is bounded by the 8192-byte symbol
            # limit above (<=2048 instructions at ~57 log bytes each). n304_post_abi (v313 stub, v312 log 31989 B + 31
            # instructions) gets 65536. Total 196608 unchanged: v312 total 121340 + ~2 KiB growth. Others keep 32768.
            raw=p.ordinary(out/(label+'.log'),131072 if logical=='n304_prepare_args' else 65536 if logical=='n304_post_abi' else 32768);total+=len(raw)
            require(total<=196608,'bounded total park flow evidence')
            entries.append(dict(item,logical=logical,log=label+'.log',sha256=p.sha(raw),log_bytes=len(raw)))
            if logical=='n304_post_abi':spin=stub_proof(raw.decode(),item)
    require(spin is not None,'actual compiled own MMU-off stub proof')
    return dict(schema='note10-v339-bounded-park-flow-v1',passed=True,functions=entries,spin=spin,
                static_scope='linked owner/transition/stock barrier/idmap stub; no runtime MMUoff claim',
                runtime_quiesce_proven=False,raw_reset_cause_proven=False,XNU=True,runtime_XNU_progress_proven=False)


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
    result = dict(schema='note10-v339-xnu-ramdisk-root-r1-build-v1', version='v339', passed=False,
                  source_head=head, source_sha256=context['source_sha256'], public_input=context,
                  build_evidence_id=identity, run_id=int(os.environ['GITHUB_RUN_ID']), run_attempt=1,
                  full_Image_build_attempts=0, old_tests_replayed=0, physical_ready=False,
                  XNU_execution=False, entry_branch_compiled=True, xnu_checkpoint_crumbs_supported=True, runtime_XNU_progress_proven=False, watchdog_armed=False, new_MMIO=False, BOOT_writes=0,
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
    result['stub_proof_selftest'] = stub_proof_selftest()
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
        require(match and match[1].endswith('-v339-xnu-ramdisk-root-r1'), 'exact diagnostic kernel release')
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
    p.save(out/'members.json',dict(schema='note10-v339-xnu-ramdisk-root-r1-sealed-members-v1',source_head=head,
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
