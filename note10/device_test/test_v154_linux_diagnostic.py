"""One NEW host batch: actual probe fixture and modeled new integration boundaries only."""
import argparse
from contextlib import ExitStack
import json
from pathlib import Path
import struct
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import patch
import v154_linux_prepare as p
import v154_linux_build as build
import v154_linux_package as package
import v154_linux_cycle as cycle

CHECKS = []


def check(value, label):
    if not value:
        raise AssertionError(label)
    CHECKS.append(label)


def refuses(call, label):
    try:
        call()
    except (ValueError, FileExistsError, TimeoutError):
        check(True, label)
    else:
        raise AssertionError('missing refusal: '+label)


FIXTURE = r'''
#include <assert.h>
#include <errno.h>
#include <stdarg.h>
#include <setjmp.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
typedef long long n154_off_t;
#define off_t n154_off_t
#define N154_HOST_TEST 1
#define N154_BUILD_ID "11111111111111111111111111111111"
#define O_RDWR 2
#define O_WRONLY 1
#define O_CLOEXEC 0x80000
#define PROT_NONE 0
#define MAP_SHARED 1
#define MAP_FAILED ((void *)-1)
#define F_OK 0
#define _SC_PAGESIZE 30
#ifndef EOPNOTSUPP
#define EOPNOTSUPP 95
#endif
static int mode, opens, maps, unmaps, closes, waits, mounts, logs;
static char records[8192];
static long fake_sysconf(int name) { assert(name == _SC_PAGESIZE); return mode == 2 ? 3 : 4096; }
static int fake_open(const char *name, int flags, ...) {
 if (!strcmp(name,"/dev/kmsg")) { assert(flags == (O_WRONLY|O_CLOEXEC)); ++logs; return 9; }
 assert(!strcmp(name,"/dev/iva_ctl")); assert(flags == (O_RDWR|O_CLOEXEC)); ++opens;
 if (mode == 3) { errno=ENODEV; return -1; } return 7;
}
static void *fake_mmap(void *address, size_t size, int prot, int flags, int fd, off_t offset) {
 assert(address == NULL && size == 4096 && prot == PROT_NONE && flags == MAP_SHARED && fd == 7 && offset == 0x18200000);
 ++maps; if (mode == 4) return (void *)0x1234;
 errno = mode == 5 ? EINVAL : EOPNOTSUPP; return MAP_FAILED;
}
static int fake_munmap(void *address, size_t size) { assert(address == (void *)0x1234 && size == 4096); ++unmaps; return 0; }
static int fake_close(int fd) { if (fd == 9) return 0; assert(fd == 7); ++closes; if (mode == 6) {errno=EIO;return -1;} return 0; }
static int fake_mount(const char *a,const char *b,const char *c,unsigned long d,const void *e) {
 (void)a;(void)b;(void)c;(void)d;(void)e; ++mounts; if(mode == 7) {errno=EINVAL;return -1;} return 0;
}
static int fake_mkdir(const char *name, unsigned int mask) { (void)name;(void)mask;return 0; }
static int fake_access(const char *name, int flags) { assert(!strcmp(name,"/dev/iva_ctl") && flags == 0); return mode == 8 ? -1 : 0; }
static unsigned int fake_sleep(unsigned int seconds) { assert(seconds == 1); ++waits;return 0; }
static int fake_dprintf(int fd, const char *format, ...) {
 va_list args; int result; (void)fd; va_start(args,format);
 result=vsnprintf(records+strlen(records),sizeof(records)-strlen(records),format,args); va_end(args);return result;
}
#define sysconf fake_sysconf
#define open fake_open
#define mmap fake_mmap
#define munmap fake_munmap
#define close fake_close
#define mount fake_mount
#define mkdir fake_mkdir
#define access fake_access
#define sleep fake_sleep
#define dprintf fake_dprintf
#include "PROBE_PATH"
static jmp_buf recovery_wait;
static int n154_arm_result, n10_return_requested, recovery_requests, recovery_parks;
static int recovery_fail_records, recovery_request_records, recovery_return_records;
#define READ_ONCE(value) (value)
static int atomic_cmpxchg(int *owner, int old, int value) { int prior=*owner; if(prior == old) *owner=value; return prior; }
static void n10_return_record(unsigned int phase, unsigned int status) {
 if (phase == 3) {assert(status == 5);++recovery_fail_records;}
 else if (phase == 1) {assert(status == 0);++recovery_request_records;}
 else {assert(phase == 2 && status == 1);++recovery_return_records;}
}
static void kernel_restart(const char *reason) { assert(!strcmp(reason,"recovery")); ++recovery_requests; }
static void n10_builtin_init_failed(int error) { assert(error == n154_arm_result && error); ++recovery_parks; longjmp(recovery_wait,1); }
ARM_GATE_BODY
static void test_arm_failure_gate(void) {
 n154_arm_result=0;n10_return_requested=0;
 n154_require_return_armed();assert(!recovery_requests && !recovery_parks && !n10_return_requested);
 n154_arm_result=-12;
 if (!setjmp(recovery_wait)) {n154_require_return_armed();assert(0);}
 assert(recovery_requests == 1 && recovery_parks == 1 && n10_return_requested == 1);
 assert(!opens && !maps && !mounts);
 assert(recovery_fail_records == 1 && recovery_request_records == 1 && recovery_return_records == 1);
 /* The retained delayed worker uses this same cmpxchg and must be suppressed. */
 assert(atomic_cmpxchg(&n10_return_requested,0,1) == 1);
 if (!setjmp(recovery_wait)) {n154_require_return_armed();assert(0);}
 assert(recovery_requests == 1 && recovery_parks == 2 && recovery_request_records == 1);
 /* A worker which already owns the request also excludes the immediate path. */
 recovery_requests=recovery_parks=recovery_request_records=0;n10_return_requested=1;
 if (!setjmp(recovery_wait)) {n154_require_return_armed();assert(0);}
 assert(!recovery_requests && recovery_parks == 1 && !recovery_request_records);
}
static void reset(int value) {mode=value;opens=maps=unmaps=closes=waits=mounts=logs=0;records[0]=0;}
int main(void) {
 char identity[]="id=11111111111111111111111111111111 boot=22222222222222222222222222222222 cycle=33333333333333333333333333333333 route=builtin arm=0";
 char unarmed[]="id=11111111111111111111111111111111 boot=22222222222222222222222222222222 cycle=33333333333333333333333333333333 route=builtin arm=-12";
 char *argv[2]={(char *)"/init",identity}; int value;
 reset(0); assert(!n154_run(2,argv)); assert(opens == 1 && maps == 1 && unmaps == 0 && closes == 1 && logs == 1); assert(strstr(records,"stage=pass"));
 argv[1]=unarmed; reset(1); assert(n154_run(2,argv)); assert(opens == 0 && maps == 0 && mounts == 0 && logs == 0); assert(!strstr(records,"stage=pass")); argv[1]=identity;
 for(value=2;value<=8;++value) {
  reset(value); assert(n154_run(2,argv)); assert(!strstr(records,"stage=pass"));
  assert(opens <= 1 && maps <= 1 && closes <= 1 && unmaps == (value == 4));
  if(value == 4) { assert(opens == 1 && maps == 1 && closes == 1); assert(strstr(records,"unexpected-map")); }
  if(value == 7 || value == 8) assert(!opens && !maps);
 }
 reset(0); identity[3]='f'; assert(n154_run(2,argv)); assert(!opens && !maps && !mounts);
 test_arm_failure_gate();
 puts("actual-probe-model PASS: arm gate / once / errno / nonaccess cleanup / fail-stop"); return 0;
}
'''


def test_compose():
    keys = list(p.STAGE_OUTPUT)
    cache = {name: ('stock:'+name).encode() for name in p.FINAL_NATIVE}
    buffers = {'note10/device_test/'+leaf: leaf.encode() for leaf in ('v143_iva_timer.inc', 'v144_iva_buffer.h', 'v145_iva_sidecar.inc')}
    modules = {}; expected = {}; calls = []
    names = ('v142_iva_native', 'v143_iva_timer', 'v144_iva_buffer', 'v145_iva_sidecar', 'v146_iva_user_read',
             'v147_iva_deinit', 'v148_iva_init_pm', 'v149_iva_init_state', 'v150_iva_mbox_register',
             'v151_iva_mmap_deny', 'v152_iva_fault_drain', 'v153_iommu_fault_register')
    for version, name in zip(range(142, 154), names):
        output = {key: (str(version)+':'+key).encode() for key in p.STAGE_OUTPUT['v'+str(version)]}
        expected['v'+str(version)] = {key: p.sha(raw) for key, raw in output.items()}
        native_keys = tuple(output)
        def apply(value, *args, version=version, output=output):
            calls.append((version, value, args))
            check(isinstance(value, dict) == (version in (142, 143, 144, 152)), 'stage API '+str(version))
            return output
        modules[name] = SimpleNamespace(patch_native=apply, NATIVE_SHA256={key: '' for key in native_keys})
    final = dict(cache)
    for version in range(142, 154):
        for key in p.STAGE_OUTPUT['v'+str(version)]:
            final[key] = (str(version)+':'+key).encode()
    with patch.object(p, 'STAGE_OUTPUT', expected), patch.object(p, 'FINAL_NATIVE', {key: p.sha(raw) for key, raw in final.items()}):
        actual, stages = p.compose(dict(cache), buffers, modules)
        check(actual == final and len(stages) == 12, 'all12 stages including150 and final14')
        check(next(row[1] for row in calls if row[0] == 150) == cache['drivers/vision/iva/iva_mbox.c'], '150 mailbox input')
        check(next(row[1] for row in calls if row[0] == 153) == final['drivers/iommu/exynos-iommu.c'].replace(b'153:', b'152:'), '153 IOMMU input')
        wrong = dict(expected); wrong['v153'] = {}
        with patch.object(p, 'STAGE_OUTPUT', wrong):
            refuses(lambda: p.compose(dict(cache), buffers, modules), 'altered native stage output refused')


def test_installer(folder):
    source = folder/'stock-install'; source.mkdir()
    fake_native = {name: ('native:'+name).encode() for name in p.FINAL_NATIVE}
    files = {name: b'stock' for name in p.FINAL_NATIVE if not name.endswith(('.inc', 'v144_iva_buffer.h'))}
    files.update({name: b'restart' for name in p.RESTART_PINS})
    files.update({'init/main.c': b'original main', 'firmware/Makefile': b'$(call cmd,fwbin,$(patsubst %.gen.S,%,$@))\n',
                  'drivers/misc/Kconfig': b'menu "Misc"\nendmenu\n', 'drivers/misc/Makefile': b'obj-y += old.o\n'})
    for name, raw in files.items():
        target = source/name; target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(raw)
    buffers = {name: p.ordinary(p.ROOT/name) for name in p.RETAINED}
    buffers['note10/device_test/v154_linux_return.c'] = p.ordinary(p.HERE/'v154_linux_return.c')
    route = SimpleNamespace(API_PINS={}, guard_main=lambda raw: b'extern char *n10_builtin_init_argument(void);\n\targv_init[1] = n10_builtin_init_argument();\n'+raw)
    with patch.object(p, 'module', return_value=route), patch.object(p, 'RESTART_PINS', {name: p.sha(b'restart') for name in p.RESTART_PINS}), patch.object(p, 'compose', return_value=(fake_native, {'all': 'modeled'})):
        receipt = p.install(source, '1'*32, buffers)
    check(len(receipt['native_output_sha256']) == 14, 'installer exact native14')
    guarded = (source/'init/main.c').read_bytes()
    check(guarded.endswith(b'original main') and guarded.index(b'\tn154_require_return_armed();') < guarded.index(b'\targv_init[1]'), 'post-SYSTEM_RUNNING shared recovery owner before argv/probe')
    route_raw = (source/'drivers/misc/builtin_init_route.c').read_bytes()
    check(b'route=builtin arm=%d' in route_raw and b'READ_ONCE(n154_arm_result)' in route_raw, 'argv successful-arm binding')
    check((source/'drivers/misc/note10_auto_return.c').read_bytes() == buffers['note10/device_test/auto_return.c'], 'unchanged sole return helper')
    check(b'NOTE10_V154_LINUX_DIAGNOSTIC' in (source/'drivers/misc/Makefile').read_bytes(), 'new Kbuild source wired')
    refuses(lambda: p.route_bytes(b'changed input'), 'altered route seam refused')
    refuses(lambda: p.firmware_fix(b'changed input'), 'altered firmware seam refused')


def elf():
    raw = bytearray(512); raw[:6] = b'\x7fELF\x02\x01'
    struct.pack_into('<HH', raw, 16, 2, 183); struct.pack_into('<Q', raw, 24, 0x400000)
    struct.pack_into('<Q', raw, 32, 64); struct.pack_into('<HH', raw, 54, 56, 1)
    struct.pack_into('<IIQQQQQQ', raw, 64, 1, 5, 0, 0x400000, 0x400000, 512, 512, 4096)
    raw[200:211] = b'N10MININIT2!'
    return bytes(raw)


def context():
    return dict(schema=p.CONTEXT_SCHEMA, scope='stock-linux-iva-mmap-denial-no-XNU', source_sha256=p.source_pins(),
                kernel=dict(commit=p.COMMIT, archive_sha256=p.ARCHIVE_SHA, defconfig_sha256=p.DEFCONFIG_SHA),
                host_pass=dict(accepted=p.HOST_PASS, new=dict(schema='note10-v154-linux-host-once-v1', passed=True,
                      result_sha256='1'*64, compiler_count=1, fixture_count=1, old_tests_count=0)))


def config(settings):
    return ('\n'.join('# CONFIG_'+key+' is not set' if value == 'n' else 'CONFIG_'+key+'='+value
                      for key, value in dict(p.REQUIRED_CONFIG, **settings).items())+'\n').encode()


def test_build(folder):
    model = context(); check(build.validate_context(model) is model, 'single canonical final public context')
    stale = dict(model, source_sha256=dict(model['source_sha256'], **{p.WORKFLOW: 'f'*64}))
    refuses(lambda: build.validate_context(stale), 'stale workflow dispatch context refused')
    env = dict(GITHUB_SHA='a'*40, GITHUB_WORKFLOW_SHA='a'*40, GITHUB_RUN_ATTEMPT='1', GITHUB_JOB=p.JOB,
               GITHUB_REPOSITORY=p.REPOSITORY, GITHUB_WORKFLOW_REF=p.REPOSITORY+'/'+p.WORKFLOW+'@refs/heads/main', GITHUB_RUN_ID='1')
    build.ci_guard('a'*40, env)
    refuses(lambda: build.ci_guard('a'*40, dict(env, GITHUB_RUN_ATTEMPT='2')), 'CI rerun refused')
    refuses(lambda: build.check_config(config(dict(build.SETTINGS, KEXEC='y')), build.SETTINGS), 'effective kexec refused')
    out = folder/'build-model'; work = out.with_name(out.name+'-work'); source = work/'source'; objects = work/'objects'
    route = p.module('builtin_init_route', {key: p.ordinary(p.ROOT/key) for key in p.RETAINED})
    def extract(archive, dest):
        dest.mkdir()
        target = dest/'arch/arm64/configs'/p.DEFCONFIG; target.parent.mkdir(parents=True); target.write_bytes(b'defconfig')
        return dest
    archive_module = SimpleNamespace(acquire=lambda path: path.write_bytes(b'archive'), extract=extract)
    def install(src, identity, buffers):
        for name in p.FINAL_NATIVE:
            path = src/name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(b'native-model')
        return dict(native_output_sha256=p.FINAL_NATIVE, installed_sha256={}, overlay_output_sha256=p.STAGE_OUTPUT)
    calls = []
    def subprocess_model(argv, **kwargs):
        argv = list(map(str, argv)); calls.append(argv)
        if argv == ['clang-14', '--version']:
            kwargs['stdout'].write(b'Ubuntu clang version 14.0.0\n')
        elif argv[0] == 'aarch64-linux-gnu-gcc':
            (out/'minimal-init.elf').write_bytes(elf())
        elif p.DEFCONFIG in argv:
            (objects/'.config').write_bytes(config({}))
        elif 'olddefconfig' in argv:
            (objects/'.config').write_bytes(config(dict(build.SETTINGS, INITRAMFS_SOURCE='"'+str(out/'initramfs.cpio')+'"')))
        elif argv[-1] == 'Image':
            for target in build.PROOF_TARGETS:
                path = objects/target; path.parent.mkdir(parents=True, exist_ok=True)
                obj = bytearray(64); obj[:6] = b'\x7fELF\x02\x01'; struct.pack_into('<HH', obj, 16, 1, 183); path.write_bytes(obj)
                path.with_name('.'+path.name+'.cmd').write_bytes(('clang-14 '+target[:-2]+'.c '+ ' '.join(build.DEPENDENCIES.get(target, ()))+'\n').encode())
            auto = objects/'include/generated/autoconf.h'; auto.parent.mkdir(parents=True); auto.write_bytes(b'/* IMA undefined model */\n')
            cpio = (out/'initramfs.cpio').read_bytes()
            result = p.read(out/'result.json'); identity = result['build_evidence_id']
            raw = bytearray(4096)+cpio+p.CYCLE_MARKER+b'\0N154IVA N154ARM N10RET1 N10ROUTE2 N10BOOTLINK2 N10MININIT2 '+identity.encode()
            raw[56:60] = b'ARM\x64'; struct.pack_into('<Q', raw, 16, len(raw))
            image = objects/'arch/arm64/boot/Image'; image.parent.mkdir(parents=True); image.write_bytes(raw)
            (objects/'System.map').write_bytes(b'0000000000000000 T _text\n0000000000001000 R __initramfs_start\n')
        return SimpleNamespace(returncode=0)
    with ExitStack() as stack:
        for key, value in (('ARCHIVE_BYTES', 7), ('ARCHIVE_SHA', p.sha(b'archive')), ('DEFCONFIG_SHA', p.sha(b'defconfig'))):
            stack.enter_context(patch.object(p, key, value))
        stack.enter_context(patch.object(build, 'validate_context', return_value=model))
        stack.enter_context(patch.object(p, 'load_sources', return_value={}))
        stack.enter_context(patch.object(p, 'module', side_effect=lambda name, buffers: archive_module if name == 'v130_archive' else route))
        stack.enter_context(patch.object(p, 'install', side_effect=install))
        stack.enter_context(patch.object(build.sys, 'platform', 'linux'))
        stack.enter_context(patch.object(build.shutil, 'which', side_effect=lambda name: '/tools/'+name))
        stack.enter_context(patch.object(build.subprocess, 'run', side_effect=subprocess_model))
        result = build.run_build(out, model, 'a'*40)
        refuses(lambda: build.run_build(out, model, 'a'*40), 'spent Image output refused')
    return finish_build_model(out, result, calls)


def finish_build_model(out, result, calls):
    check(result['passed'] and result['full_Image_build_attempts'] == 1, 'actual new builder completes modeled full Image once')
    check(sum(row[-1] == 'Image' for row in calls) == 1 and not any(row[-1].endswith('.o') for row in calls), 'no standalone object builds')
    check(len(result['object_evidence']) == 9 and result['IMA_evidence']['production_fence_compiled'], 'same Image seven native units plus init/return proof')
    node_calls = []
    def node_model(argv, **kwargs):
        node_calls.append(argv)
        Path(argv[4]).write_bytes(b'modeled sealed transport')
        return SimpleNamespace(returncode=0)
    original_read = p.ordinary
    def no_Image_validation(path, *args):
        if Path(path).name == 'Image':
            raise AssertionError('seal must reuse producer Image digest')
        return original_read(path, *args)
    with patch.object(build.subprocess, 'run', side_effect=node_model), patch.object(p, 'ordinary', side_effect=no_Image_validation):
        build.seal(out, 'a'*40)
        refuses(lambda: build.seal(out, 'a'*40), 'preexisting manifest no second seal')
    manifest = p.read(out/'members.json')
    check('members.json' not in manifest['member_sha256'] and set(manifest['member_bytes']) == set(build.SUCCESS_MEMBERS)-{'members.json'}, 'manifest excludes its own hash and joins exact premanifest35')
    import zipfile
    with zipfile.ZipFile(out.with_suffix('.zip')) as archive:
        check(set(archive.namelist()) == set(build.SUCCESS_MEMBERS) | {'members.json'}, 'exact36 bounded sealed members no vmlinux/debug/full objects')
    check(len(node_calls) == 1 and node_calls[0][2] == 'seal', 'original Node SEAL interface only modeled no private key')
    return out, result


def boot_bytes(kernel, total=None):
    raw = bytearray(4096); raw[:8] = b'ANDROID!'
    struct.pack_into('<10I', raw, 8, len(kernel), 0x80080000, 0, 0x82000000, 0, 0, 0x80000100, 4096, 1, (20 << 4) | 1)
    raw[48:52] = b'd2x\0'; raw[64:76] = b'model=linux\0'
    struct.pack_into('<IQI', raw, 1632, 0, 0, 1648)
    raw.extend(kernel); raw.extend(bytes(-len(raw) % 4096))
    if total:
        raw.extend(b'SEANDROIDENFORCE'); raw.extend(bytes(total-len(raw)))
    return bytes(raw)


def test_package(folder, build_folder, result):
    backup_folder = folder/'backup-model'; backup_folder.mkdir()
    safe = boot_bytes(b'old-kernel', 32768); (backup_folder/'boot.img').write_bytes(safe)
    rows = [dict(partition=name, block_node='/dev/block/sda'+str(index+12), size=32768 if name == 'boot' else 4096,
                 file=name+'.img', sha256=p.sha(safe) if name == 'boot' else str(index+1)*64,
                 remote_hash_before_and_after_match=True) for index, name in enumerate(sorted(p.PARTITIONS))]
    backup = dict(complete=True, partition_writes=False, partitions=rows, bootloader='N976NTEST')
    current = dict(schema='note10-v141-private-xnu-package-v1', version='v141', cycle='4'*32, build_evidence_id='5'*32,
                   diagnostic_BOOT_sha256='a'*64, rollback_BOOT_sha256=p.sha(safe), partitions=rows, bootloader='N976NTEST')
    ledger = dict(schema='note10-v141-owned-XNU-ledger-v1', cycle='4'*32, build_evidence_id='5'*32,
                  recovery_returned=True, status='cycle-complete-XNU-proof-limits-retained', host_BOOT_write_attempts=1, host_reboot_attempts=1)
    paths = {}
    for name, row in (('backup_manifest', backup), ('current141_package', current), ('current141_ledger', ledger)):
        path = backup_folder/(name+'.json'); p.save(path, row); paths[name] = path
    paths['build_result'] = build_folder/'result.json'
    dtb = next(row for row in rows if row['partition'] == 'dtb')
    binding = dict(schema='note10-v154-private-iva-resource-binding-v1', resource_base=0x18200000, resource_size=0x200000,
                   DTB_sha256=dtb['sha256'], DTB_baseline_only_not_live_FDT_equality=True, node_path='/iva@0x18200000',
                   hardware_terminal_claimed=False, partition=dtb, baseline_package_sha256=p.sha(p.ordinary(paths['current141_package'])))
    paths['iva_resource_binding'] = backup_folder/'binding.json'; p.save(paths['iva_resource_binding'], binding)
    paths['mkbootimg'] = backup_folder/'mkbootimg.py'; paths['mkbootimg'].write_bytes(b'# model tool\n')
    twrp = backup_folder/'official-recovery.img'; twrp.write_bytes(boot_bytes(b'recovery-model', 32768))
    pins = {name: dict(path=str(path), sha256=p.sha(p.ordinary(path))) for name, path in paths.items()}
    pins['twrp'] = dict(path=str(twrp), sha256=p.sha(twrp.read_bytes()), header_sha256=p.sha(twrp.read_bytes()[:1660]), bytes=twrp.stat().st_size)
    spec = dict(schema=p.INPUTS_SCHEMA, inputs=pins); contract = folder/'package-inputs.json'; p.save(contract, spec)
    out = folder/'package-model'; calls = []
    def mkbootimg(argv, **kwargs):
        calls.append(argv)
        kernel = Path(argv[argv.index('--kernel')+1]).read_bytes()
        Path(argv[argv.index('--output')+1]).write_bytes(boot_bytes(kernel))
        return SimpleNamespace(returncode=0)
    with patch.object(package, 'MKBOOTIMG_SHA', pins['mkbootimg']['sha256']), patch.object(package, 'TWRP_SHA', pins['twrp']['sha256']), patch.object(package.subprocess, 'run', side_effect=mkbootimg):
        receipt = package.prepare(contract, p.sha(p.ordinary(contract)), out)
        refuses(lambda: package.prepare(contract, p.sha(p.ordinary(contract)), out), 'spent package refused')
    plan, admitted = package.validate_plan(receipt['plan'], receipt['plan_sha256'])
    check(len(calls) == 1 and plan['internal_kexec_limit'] == 0 and plan['ioctl_limit'] == 0, 'new package complete Linux-only graph')
    check(admitted['expected_current_BOOT_sha256'] == current['diagnostic_BOOT_sha256'] and admitted['automatic_restore'] is False, 'current141 and restore availability separated')
    check((out/'restore.zip').is_file(), 'fresh paired restore ZIP available')
    bad_backup = dict(backup, partitions=[dict(row, block_node=rows[0]['block_node']) for row in rows])
    refuses(lambda: package.partition_rows(bad_backup), 'duplicate partition nodes refused')
    refuses(lambda: package.current_and_restore(current, dict(ledger, recovery_returned=False), backup), 'unreturned current baseline refused')
    altered = dict(result, cycle_offset=result['cycle_offset']+1)
    refuses(lambda: package.patch_cycle((build_folder/'Image').read_bytes(), altered, '3'*32), 'wrong cycle offset refused')
    script = package.updater('diagnostic', admitted)
    check(script.count(b'dd if=') == 1 and b'reboot' not in script.replace(b'No automatic reboot or restore.', b''), 'updater BOOT-only once no reboot')
    return receipt, plan, admitted


def return_log(identity, token):
    boot = '2'*32; lines = []
    for phase in (0, 1):
        if phase == 1:
            lines.extend(['N154IVA id='+identity+' boot='+boot+' cycle='+token+' stage=armed errno=0',
                          'N154IVA id='+identity+' boot='+boot+' cycle='+token+' stage=pass errno=95'])
        for seq in (0, 1):
            body = 'id='+identity+' cycle='+token+' phase='+str(phase)+' seq='+str(seq)+' delay_ms=90000 status=0'
            checksum = 2166136261
            for byte in body.encode():
                checksum = ((checksum ^ byte)*16777619) & 0xffffffff
            lines.append('N10BOOTLINK2 boot='+boot+' N10RET1 '+body+' checksum='+format(checksum, '08x'))
    return ('\n'.join(lines)+'\n').encode()


def test_cycle(folder, receipt, plan, admitted):
    log = return_log(plan['build_evidence_id'], plan['cycle'])
    check(cycle.decode(log, plan['build_evidence_id'], plan['cycle'])['probe_pass'], 'same-boot arm probe recovery decoder')
    refuses(lambda: cycle.decode(log.replace(b'errno=95', b'errno=22'), plan['build_evidence_id'], plan['cycle']), 'wrong errno log refused')
    refuses(lambda: cycle.decode(log+log, plan['build_evidence_id'], plan['cycle']), 'duplicate cycle log refused')
    adbfile = folder/'adb-model.exe'; adbfile.write_bytes(b'not executable model')
    review = dict(schema=cycle.APPROVAL_SCHEMA, decision='approve', version='v154', plan_sha256=receipt['plan_sha256'],
                  cycle=plan['cycle'], build_evidence_id=plan['build_evidence_id'], source_sha256=plan['source_sha256'],
                  XNU_execution_allowed=False, automatic_restore=False, battery_minimum=10, host_BOOT_writes=1,
                  host_reboots=1, internal_kexecs=0, ioctl_limit=0, diagnostic_BOOT_sha256=admitted['diagnostic_BOOT_sha256'],
                  restore_zip_sha256=admitted['restore_zip_sha256'], adb_path=str(adbfile.resolve()), adb_sha256=p.sha(adbfile.read_bytes()),
                  serial='MODEL', reviewed_restore_evidence=[dict(path=str(folder/'package-inputs.json'), sha256=p.sha(p.ordinary(folder/'package-inputs.json')))])
    approval = folder/'physical-model-review.json'; p.save(approval, review)
    class FakeAdb:
        def __init__(self, fail=False):
            self.path = str(adbfile); self.serial = 'MODEL'; self.return_deadline = None
            self.boot = admitted['expected_current_BOOT_sha256']; self.boot_id = '11111111-1111-1111-1111-111111111111'
            self.calls = []; self.fail = fail
        def text(self, *args, **kwargs):
            self.calls.append(args)
            facts = {('shell', 'getprop', 'ro.twrp.version'): 'model', ('shell', 'id', '-u'): '0',
                     ('shell', 'uname', '-m'): 'aarch64', ('shell', 'getprop', 'ro.product.device'): 'd2x',
                     ('shell', 'getprop', 'ro.bootloader'): admitted['bootloader'],
                     ('shell', 'cat', '/sys/class/power_supply/battery/capacity'): '80',
                     ('shell', 'cat', '/proc/sys/kernel/random/boot_id'): self.boot_id,
                     ('shell', 'cat', '/proc/mounts'): 'rootfs / rootfs rw 0 0\n'}
            if args in facts:
                return facts[args]
            for row in admitted['partitions']:
                if args == ('shell', 'readlink', '-f', '/dev/block/by-name/'+row['partition']): return row['block_node']
                if args == ('shell', 'blockdev', '--getsize64', row['block_node']): return str(row['size'])
                if args == ('shell', 'sha256sum', row['block_node']): return self.boot if row['partition'] == 'boot' else row['sha256']
            if args[:2] == ('shell', 'sha256sum'): return admitted['diagnostic_zip_sha256']+' remote'
            raise AssertionError(args)
        def call(self, *args, **kwargs):
            self.calls.append(args)
            if args[:3] == ('shell', 'twrp', 'install'):
                if self.fail: raise RuntimeError('modeled install failure')
                self.boot = admitted['diagnostic_BOOT_sha256']
            if args == ('reboot',): self.boot_id = '22222222-2222-2222-2222-222222222222'
            if args[:2] == ('exec-out', 'cat'): return log
            return b''
    def consume(model, expected):
        path = folder/('journal-'+str(consume.calls)+'.json'); consume.calls += 1
        with path.open('xb') as stream: stream.write(b'{"spent":true}\n')
        return path
    consume.calls = 0
    with patch.object(cycle.subprocess, 'run', return_value=SimpleNamespace(stdout=b'List of devices attached\nMODEL device\nOTHER device\n')):
        refuses(lambda: cycle.transport(adbfile, 'MODEL'), 'multiple transports refused')
    bad_adb = FakeAdb()
    original_text = bad_adb.text
    bad_adb.text = lambda *args, **kwargs: '9' if args == ('shell', 'cat', '/sys/class/power_supply/battery/capacity') else original_text(*args, **kwargs)
    refuses(lambda: cycle.preflight(bad_adb, admitted, admitted['expected_current_BOOT_sha256']), 'battery below10 refused')
    bad_adb = FakeAdb(); bad_adb.boot = 'f'*64
    refuses(lambda: cycle.preflight(bad_adb, admitted, admitted['expected_current_BOOT_sha256']), 'five-partition unexpected BOOT refused')
    with patch.object(cycle, 'transport'), patch.object(cycle, 'consume', side_effect=consume):
        adb = FakeAdb(); out = folder/'cycle-model'
        actual = cycle.run(receipt['plan'], receipt['plan_sha256'], approval, p.sha(p.ordinary(approval)), out, adb, execute=True)
        check(actual['status'] == 'cycle-complete-linux-mmap-denied' and actual['host_BOOT_write_attempts'] == actual['host_reboot_attempts'] == 1, 'new runner completes BOOT1 reboot1 integrity and probe')
        check(sum(call[:3] == ('shell', 'twrp', 'install') for call in adb.calls) == 1 and sum(call == ('reboot',) for call in adb.calls) == 1, 'no resend or restore install')
        refuses(lambda: cycle.run(receipt['plan'], receipt['plan_sha256'], approval, p.sha(p.ordinary(approval)), out, adb, execute=True), 'spent physical output refused')
        failed = FakeAdb(True)
        try:
            cycle.run(receipt['plan'], receipt['plan_sha256'], approval, p.sha(p.ordinary(approval)), folder/'cycle-fail-model', failed, execute=True)
        except RuntimeError:
            pass
        else:
            raise AssertionError('install failure did not stop')
        ledger = p.read(folder/'cycle-fail-model/ledger.json')
        check(ledger['host_BOOT_write_attempts'] == 1 and ledger['host_reboot_attempts'] == 0 and ledger['status'] == 'failed-spent-no-retry', 'failed write spent before call no reboot/retry')
    ticks = [0, 0, 240]
    refuses(lambda: cycle.wait_return(FakeAdb(), admitted, '11111111-1111-1111-1111-111111111111', 240, clock=lambda: ticks.pop(0) if ticks else 240, sleep=lambda value: None), 'same recovery ID never promoted')
    bad = dict(review, XNU_execution_allowed=True); p.save(approval, bad)
    refuses(lambda: cycle.admit(receipt['plan'], receipt['plan_sha256'], approval, p.sha(p.ordinary(approval))), 'XNU approval fallthrough refused')
    # Exercise actual exclusive journal creation without touching the real global journal.
    with patch.object(p, 'ROOT', folder/'journal-model-root'):
        first = cycle.consume(plan, receipt['plan_sha256'])
        check(first.exists(), 'real once journal persisted')
        refuses(lambda: cycle.consume(plan, receipt['plan_sha256']), 'same build journal replay refused')


def check_source_guards():
    return_source = p.ordinary(p.HERE/'v154_linux_return.c')
    probe_source = p.ordinary(p.HERE/'v154_linux_probe.c')
    check(return_source.count(b'n10_arm_auto_return()') == 1 and b'WRITE_ONCE(n154_arm_result, result)' in return_source, 'one return arm immutable result')
    check(return_source.count(b'kernel_restart("recovery")') == 1 and b'atomic_cmpxchg(&n10_return_requested, 0, 1)' in return_source and b'reboot(' not in probe_source and b'ioctl(' not in probe_source, 'arm-failure normal recovery shares retained worker owner no independent reset/ioctl')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--cc', type=Path, required=True)
    args = parser.parse_args()
    out = p.private(args.output)
    if out.exists():
        raise ValueError('fresh once host output required')
    out.mkdir(parents=True)
    result = dict(schema='note10-v154-linux-host-once-v1', passed=False, compiler_count=0, fixture_count=0,
                  old_tests_count=0, actual_device_operations=0, actual_full_Image_builds=0,
                  source_sha256={name: p.sha(p.ordinary(p.ROOT/name)) for name in p.NEW_FILES})
    p.save(out/'result.json', result)
    try:
        fixture = out/'probe_fixture.c'; exe = out/('probe_fixture.exe' if sys.platform == 'win32' else 'probe_fixture')
        return_raw = p.ordinary(p.HERE/'v154_linux_return.c').decode()
        begin = '/* N154_ARM_FAILURE_GATE_BEGIN */'
        end = '/* N154_ARM_FAILURE_GATE_END */'
        if return_raw.count(begin) != 1 or return_raw.count(end) != 1:
            raise ValueError('unique actual shared recovery gate required')
        gate = return_raw.split(begin)[1].split(end)[0]
        fixture.write_bytes(FIXTURE.replace('PROBE_PATH', (p.HERE/'v154_linux_probe.c').as_posix()).replace('ARM_GATE_BODY', gate).encode())
        compiler = [str(args.cc.resolve()), '-std=c11', '-Wall', '-Wextra', '-Werror', str(fixture), '-o', str(exe)]
        result.update(compiler_count=1, compiler_argv=compiler); p.save(out/'result.json', result)
        compiled = subprocess.run(compiler, capture_output=True, timeout=120)
        (out/'compiler.stdout').write_bytes(compiled.stdout); (out/'compiler.stderr').write_bytes(compiled.stderr)
        if compiled.returncode: raise ValueError('new probe fixture compile failed')
        result.update(fixture_count=1, fixture_argv=[str(exe)]); p.save(out/'result.json', result)
        executed = subprocess.run([str(exe)], capture_output=True, timeout=30)
        (out/'fixture.stdout').write_bytes(executed.stdout); (out/'fixture.stderr').write_bytes(executed.stderr)
        check(executed.returncode == 0, 'actual probe C fake-syscall fixture')
        test_compose(); test_installer(out)
        build_folder, built = test_build(out)
        receipt, plan, admitted = test_package(out, build_folder, built)
        test_cycle(out, receipt, plan, admitted)
        check_source_guards()
        result.update(passed=True, checks=CHECKS, check_count=len(CHECKS), modeled_integration_only=True)
    except BaseException as error:
        result.update(error_type=type(error).__name__, error=str(error)[:1024]); p.save(out/'result.json', result); raise
    p.save(out/'result.json', result)
    print(json.dumps(dict(passed=True, checks=len(CHECKS), compiler_count=1, fixture_count=1, old_tests_count=0)))


if __name__ == '__main__':
    main()
