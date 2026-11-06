"""One NEW PC-only batch using complete authentic selected IVA native bodies."""
from pathlib import Path
import argparse
import hashlib
import json
import re
import subprocess
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
from v142_iva_native import CTRL, MCU, NATIVE_SHA256, patch_native

FIXTURE_HEADER_SHA256 = {
    'drivers/vision/iva/iva_ctrl.h': '89fdd85645f1844a05551f225c9fbf1063762df0ea09f6d04d9cfbe546513f56',
    'drivers/vision/iva/iva_mcu.h': 'b4ae430f8f654a9eff3f677278bd716dac72820d5c8211524fa45a8b678952e5',
}
_TOKENS = re.compile(rb'/\*.*?\*/|//[^\n]*|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|[{}]', re.S)


def native_body(raw, name):
    pattern = rb'(?m)^(?:static[ \t]+)?int32_t[ \t]+' + name.encode() + rb'[ \t]*\('
    matches = list(re.finditer(pattern, raw))
    if len(matches) != 1:
        raise ValueError('one authentic native function required: ' + name)
    start = matches[0].start()
    opening = raw.find(b'\n{', matches[0].end())
    if opening < 0:
        raise ValueError('native function body missing')
    depth = 0
    for token in _TOKENS.finditer(raw, opening + 1):
        if token.group() == b'{':
            depth += 1
        elif token.group() == b'}':
            depth -= 1
            if depth == 0:
                return raw[start:token.end()]
    raise ValueError('unbalanced native function body')


PRELUDE = r'''
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#define __user
#define CONFIG_SOC_EXYNOS9820 1
#define MCU_SRAM_VIA_MEMCPY
#define IVA_ST_MCU_BOOT_DONE 1
#define IVA_CTRL_BOOT_FILE_LEN 256
#define IVA_MCU_FILE_PATH "/system/vendor/firmware/iva30_rt-makalu.bin"
#define EINVAL 22
#define EIO 5
#define EFAULT 14
#define EFBIG 27
#define O_RDONLY 0
#define STATX_MODE 1
#define STATX_SIZE 2
#define STATX_MTIME 4
#define AT_STATX_SYNC_AS_STAT 0
#define S_ISREG(mode) ((mode) == 1)
#define IS_ERR_OR_NULL(value) ((value) == NULL)
#define dev_dbg(dev, ...) ((void)(dev))
#define dev_warn(dev, ...) ((void)(dev))
#define dev_err(dev, ...) ((void)(dev))
#define dev_info(dev, ...) ((void)(dev))
#define loff_t n142_loff_t
typedef long long n142_loff_t;
struct n142_time { long sec, nsec; };
struct kstat { int mode; uint64_t size; struct n142_time mtime; };
struct n142_refcount { int value; };
struct kref { struct n142_refcount refcount; };
struct device { int unused; };
struct n142_path { int unused; };
struct file { struct n142_path f_path; };
struct mcu_binary {
    struct n142_time last_mtime;
    char file[IVA_CTRL_BOOT_FILE_LEN];
    uint32_t file_size;
    void *bin;
    uint32_t io_va;
};
struct iva_dev_data {
    struct device *dev;
    unsigned long state;
    uint32_t mcu_mem_size;
    struct mcu_binary *mcu_bin;
    struct kref glob_boot_ref, glob_init_ref;
    int mcu_split_sram;
};
struct iva_proc { struct iva_dev_data *iva_data; struct kref boot_ref; };
static struct device device;
static struct file firmware;
static struct mcu_binary binary;
static struct iva_dev_data owner;
static struct iva_proc process;
static unsigned char contents[128];
static char events[128];
static size_t event_count;
static int getattr_error, open_error;
static unsigned int failures, cases;
static void event(char value) {
    if (event_count + 1 < sizeof(events)) {
        events[event_count++] = value; events[event_count] = 0;
    }
}
static void check(int condition, const char *label) {
    if (!condition) { fprintf(stderr, "FAIL %s\n", label); failures++; }
}
static void reset_case(void) {
    memset(&owner, 0, sizeof(owner)); memset(&process, 0, sizeof(process));
    memset(&binary, 0, sizeof(binary)); memset(contents, 0, sizeof(contents));
    owner.dev = &device; owner.mcu_bin = &binary; owner.mcu_mem_size = sizeof(contents);
    owner.mcu_split_sram = 1; owner.glob_init_ref.refcount.value = 1;
    process.iva_data = &owner; binary.bin = contents;
    event_count = 0; events[0] = 0; getattr_error = open_error = 0; cases++;
}
static int iva_ctrl_is_iva_on(struct iva_dev_data *iva) {
    return iva->glob_init_ref.refcount.value != 0;
}
static int strncpy_from_user(char *target, const char *source, size_t count) {
    size_t i; event('C'); if (!source) return -EFAULT;
    for (i = 0; i < count; i++) { target[i] = source[i]; if (!source[i]) return (int)i; }
    return (int)count;
}
static int kref_get_unless_zero(struct kref *ref) {
    event(ref == &process.boot_ref ? 'p' : 'g');
    if (!ref->refcount.value) return 0;
    ref->refcount.value++; return 1;
}
static void kref_init(struct kref *ref) {
    event(ref == &process.boot_ref ? 'P' : 'G'); ref->refcount.value = 1;
}
static int kref_read(const struct kref *ref) { return ref->refcount.value; }
static void refcount_set(struct n142_refcount *ref, int value) { event('Z'); ref->value = value; }
static int test_bit(unsigned int bit, const unsigned long *state) { return (*state & (1UL << bit)) != 0; }
static void set_bit(unsigned int bit, unsigned long *state) { *state |= 1UL << bit; }
static void iva_ctrl_mcu_boot_prepare_system(struct iva_dev_data *iva) { (void)iva; event('Q'); }
static void iva_ctrl_mcu_boot_unprepare_system(struct iva_dev_data *iva) { (void)iva; event('U'); }
static struct file *filp_open(const char *path, int flags, int mode) {
    (void)path; (void)flags; (void)mode; event('O'); return open_error ? NULL : &firmware;
}
static int vfs_getattr(struct n142_path *path, struct kstat *st, int mask, int flags) {
    (void)path; (void)mask; (void)flags; event('A');
    st->mode = 1; st->size = 16; st->mtime.sec = 11; st->mtime.nsec = 0; return getattr_error;
}
static int timespec_equal(const struct n142_time *a, const struct n142_time *b) {
    return a->sec == b->sec && a->nsec == b->nsec;
}
static int iva_mcu_map_boot_mem(struct iva_dev_data *iva, struct mcu_binary *bin) {
    (void)iva; (void)bin; event('M'); return 0;
}
static void iva_mcu_prepare_mcu_reset(struct iva_dev_data *iva, uint32_t address) {
    (void)iva; (void)address; event('S');
}
static int kernel_read(struct file *file, void *buffer, size_t bytes, loff_t *position) {
    (void)file; (void)buffer; (void)position; event('R'); return (int)bytes;
}
static int iva_mcu_boot(struct iva_dev_data *iva, struct mcu_binary *bin, int32_t ready) {
    (void)iva; (void)bin; (void)ready; event('B'); return 0;
}
static int filp_close(struct file *file, void *unused) { (void)file; (void)unused; event('F'); return 0; }
'''

CASES = r'''
static void invalid_user(const char *argument, int error, int already_booted) {
    int result; reset_case();
    if (already_booted) { process.boot_ref.refcount.value = 2; owner.glob_boot_ref.refcount.value = 3; owner.state = 1UL << IVA_ST_MCU_BOOT_DONE; }
    result = iva_ctrl_mcu_boot_file(&process, argument, 0);
    check(result == error, "user argument errno");
    check(strcmp(events, "C") == 0, "invalid user: copy only, no refs/QoS/native action");
    check(process.boot_ref.refcount.value == (already_booted ? 2 : 0), "invalid user proc reference unchanged");
    check(owner.glob_boot_ref.refcount.value == (already_booted ? 3 : 0), "invalid user global reference unchanged");
    check(owner.state == (already_booted ? 1UL << IVA_ST_MCU_BOOT_DONE : 0), "invalid user native state unchanged");
}
static void invalid_native(const char *argument, int already_booted) {
    int result; reset_case(); owner.state = already_booted ? 1UL << IVA_ST_MCU_BOOT_DONE : 0;
    result = iva_mcu_boot_file(&owner, argument, 0);
    check(result == -EINVAL, "native invalid argument errno");
    check(event_count == 0, "native invalid: no file/boot action");
    check(owner.state == (already_booted ? 1UL << IVA_ST_MCU_BOOT_DONE : 0), "native invalid state unchanged");
}
int main(void) {
    int result; char overlong[IVA_CTRL_BOOT_FILE_LEN + 32];
    char unterminated[IVA_CTRL_BOOT_FILE_LEN - 1];
    char bounded_native[sizeof(IVA_MCU_FILE_PATH)];
    char valid_with_tail[sizeof(IVA_MCU_FILE_PATH) + 8];
    memset(overlong, 'x', sizeof(overlong)); memcpy(overlong, IVA_MCU_FILE_PATH, sizeof(IVA_MCU_FILE_PATH) - 1); overlong[sizeof(overlong)-1] = 0;
    memset(unterminated, 'x', sizeof(unterminated)); memcpy(unterminated, IVA_MCU_FILE_PATH, sizeof(IVA_MCU_FILE_PATH) - 1);
    memcpy(bounded_native, IVA_MCU_FILE_PATH, sizeof(bounded_native)); bounded_native[sizeof(bounded_native)-1] = 'x';
    memcpy(valid_with_tail, IVA_MCU_FILE_PATH, sizeof(IVA_MCU_FILE_PATH)); memset(valid_with_tail + sizeof(IVA_MCU_FILE_PATH), 'x', 8);
    invalid_user(NULL, -EFAULT, 0); invalid_user("", -EINVAL, 0);
    invalid_user("/wrong/firmware.bin", -EINVAL, 0); invalid_user(overlong, -EINVAL, 0);
    invalid_user(unterminated, -EINVAL, 0); invalid_user("/wrong/firmware.bin", -EINVAL, 1);
    invalid_native(NULL, 0); invalid_native("", 0); invalid_native("/wrong/firmware.bin", 0);
    invalid_native(overlong, 0); invalid_native(bounded_native, 0); invalid_native("/wrong/firmware.bin", 1);
    reset_case(); result = iva_ctrl_mcu_boot_file(&process, IVA_MCU_FILE_PATH, 0);
    check(result == 0 && strcmp(events, "CpPgQOAMSRBFG") == 0, "valid fresh native call order/count preserved");
    check(process.boot_ref.refcount.value == 1 && owner.glob_boot_ref.refcount.value == 1 && test_bit(IVA_ST_MCU_BOOT_DONE, &owner.state), "valid fresh native state preserved");
    reset_case(); result = iva_ctrl_mcu_boot_file(&process, valid_with_tail, 0);
    check(result == 0 && strcmp(events, "CpPgQOAMSRBFG") == 0, "valid C string accepts bytes after first NUL");
    reset_case(); process.boot_ref.refcount.value = 1;
    result = iva_ctrl_mcu_boot_file(&process, IVA_MCU_FILE_PATH, 0);
    check(result == 0 && process.boot_ref.refcount.value == 2 && strcmp(events, "Cp") == 0, "valid repeated proc request native behavior preserved");
    reset_case(); owner.glob_boot_ref.refcount.value = 1;
    result = iva_ctrl_mcu_boot_file(&process, IVA_MCU_FILE_PATH, 0);
    check(result == 0 && owner.glob_boot_ref.refcount.value == 2 && strcmp(events, "CpPg") == 0, "valid existing global native behavior preserved");
    reset_case(); owner.state = 1UL << IVA_ST_MCU_BOOT_DONE;
    result = iva_mcu_boot_file(&owner, IVA_MCU_FILE_PATH, 0);
    check(result == 0 && event_count == 0, "valid already-booted native path unchanged");
    reset_case(); binary.last_mtime.sec = 11; strcpy(binary.file, IVA_MCU_FILE_PATH);
    result = iva_mcu_boot_file(&owner, IVA_MCU_FILE_PATH, 0);
    check(result == 0 && strcmp(events, "OAMSRBF") == 0, "native memcpy branch preserves reload despite cached metadata");
    reset_case(); getattr_error = -EIO;
    result = iva_ctrl_mcu_boot_file(&process, IVA_MCU_FILE_PATH, 0);
    check(result == -EIO && strcmp(events, "CpPgQOAFUZ") == 0, "existing valid-path error and cleanup order preserved");
    reset_case(); owner.glob_init_ref.refcount.value = 0;
    result = iva_ctrl_mcu_boot_file(&process, "", 0);
    check(result == -EIO && event_count == 0, "existing uninitialized-device error precedence preserved");
    if (failures) return 1;
    printf("{\"passed\":true,\"cases\":%u}\n", cases); return 0;
}
'''


def ordinary(path):
    path = Path(path)
    if not path.is_absolute() or path.is_symlink() or not path.is_file():
        raise ValueError('absolute ordinary existing input required: ' + str(path))
    return path.resolve()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('output', 'cc', 'native-root'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    output = args.output
    native_root = args.native_root
    if (not output.is_absolute() or output.resolve() != output or output.exists() or
            output.is_symlink() or not output.is_relative_to(ROOT / 'note10/private') or
            not native_root.is_absolute() or native_root.resolve() != native_root or
            native_root.is_symlink() or not native_root.is_dir() or
            output.is_relative_to(native_root) or native_root.is_relative_to(output)):
        parser.error('fresh separate canonical private output and native input root required')
    compiler = ordinary(args.cc)
    for name, pin in FIXTURE_HEADER_SHA256.items():
        if hashlib.sha256(ordinary(native_root / name).read_bytes()).hexdigest() != pin:
            raise ValueError('exact native fixture dependency required: ' + name)
    source = {name: ordinary(native_root / name).read_bytes() for name in NATIVE_SHA256}
    changed = patch_native(source)
    # The native production functions themselves form the C fixture: no copied
    # implementation model and no retained renderer, test, build or device call.
    lower = native_body(changed[MCU], 'iva_mcu_boot_file')
    upper = native_body(changed[CTRL], 'iva_ctrl_mcu_boot_file')
    fixture = PRELUDE.encode() + b'\n' + lower + b'\n' + upper + b'\n' + CASES.encode()
    output.mkdir(parents=True)
    result = dict(schema='note10-v142-iva-firmware-argument-result-v1', passed=False,
                  scope='PC-only-native-invalid-firmware-argument', NEW_transform_invocations=1,
                  compiler_invocations=0, fixture_processes=0, old_tests_replayed=0,
                  retained_overlay_render_invocations=0, kernel_CI=0, device_operations=[],
                  physical_ready=False, owner_registry_success_emitted=False,
                  native_input_sha256=NATIVE_SHA256,
                  native_fixture_header_sha256=FIXTURE_HEADER_SHA256,
                  changed_native_sha256={name: hashlib.sha256(raw).hexdigest() for name, raw in changed.items()})
    def persist():
        (output / 'result.json').write_bytes((json.dumps(result, indent=2) + '\n').encode())
    persist()
    for name, raw in changed.items():
        target = output / 'native-output' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
    fixture_path = output / 'new-iva-firmware-argument.c'
    fixture_path.write_bytes(fixture)
    result['fixture_sha256'] = hashlib.sha256(fixture).hexdigest()
    executable = output / ('new-iva-firmware-argument.exe' if sys.platform == 'win32' else 'new-iva-firmware-argument')
    command = [str(compiler), '-std=gnu11', '-O2', '-Wall', '-Wextra', '-Werror',
               '-Wstrict-prototypes', '-Wno-unused-function', str(fixture_path), '-o', str(executable)]
    result['compiler_invocations'] = 1
    result['compiler_argv'] = command
    persist()
    with (output / 'compile.log').open('xb') as log:
        subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=60)
    result['fixture_processes'] = 1
    persist()
    with (output / 'fixture.log').open('xb') as log:
        done = subprocess.run([str(executable)], cwd=ROOT, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, timeout=30)
        log.write(done.stdout)
    done.check_returncode()
    fixture_result = json.loads(done.stdout)
    if fixture_result != {'passed': True, 'cases': 20}:
        raise ValueError('exact NEW native argument case receipt required')
    result.update(passed=True, fixture_result=fixture_result)
    persist()
    print(json.dumps({'passed': True, 'cases': fixture_result['cases'], 'physical_ready': False}))


if __name__ == '__main__':
    main()
