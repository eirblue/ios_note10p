"""Prepare one source-pinned user-fetch host fixture; never compile or execute it."""
import argparse
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
REFERENCE = ROOT/'research/ios26/xnu-reference/xnu-ac9718fb1af618d5ce8678d0dc6e8a58f252216f'
OUT = ROOT/'note10/private/device-test/v162-user-instruction-fetch-pc-20261110/root-check-once'
REFERENCE_PINS = {'osfmk/mach/arm/thread_status.h': '60434026c659eebe0137ad2dd6536637e7330cf355958f580afe95bc34a82e95', 'osfmk/arm64/proc_reg.h': 'fcbead4162ad09d0f51be9ce88e5f2d6d89e89e58934975ee1aa23e506485055', 'bsd/libkern/copyio.h': 'e4c53c7f0164f5cad7be1c958d76df66d5e9033e577c62cfa15863b2e181362e', 'bsd/arm/types.h': '4b6d31fc15d19635ae7179647145130a86d0dff5ee9157e632e9bd3828ba3b73', 'bsd/arm/_types.h': 'dea174bb0a2621285e0380e1044283d04d7911c0c0c7507ae370e154b5a2d963', 'bsd/sys/_types/_u_int64_t.h': 'd096eee54a5acc2c3cd5cf71256d69198ada8f8d82cdb0a717bc8ed65650ad93', 'osfmk/mach/arm/vm_types.h': 'b2deb6cfadc2972a42f698b1822393d240f96c1f91426f4f087e0cffc367225d', 'osfmk/mach/message.h': 'ce1b7c102909919c8a15e984ab4279c2a54f09301c3641b0a3151dd4d7242465', 'osfmk/mach/arm/boolean.h': '03ceda8c88250b93a3bebca92e03dd558e13fe68e83eff6bba5db32f95b48b6d'}
SOURCE_PINS = {'note10_user_instruction_fetch.c': '20becc0643449b8116a22efb377e9486c18830569e5294c87931930d004eb1b3', 'note10_user_instruction_fetch.h': '6a9817830b75296d59f087b2cf96e872c8f9d4018b51e5b16d6e3b3cfdc96238'}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def pinned(path, digest):
    require(path.resolve() == path and not path.is_symlink() and path.is_file() and
            0 < path.stat().st_size <= 2*1024*1024, 'bounded canonical source required')
    raw = path.read_bytes()
    require(hashlib.sha256(raw).hexdigest() == digest, 'exact source changed: '+path.name)
    return raw.decode('utf-8')


def block(text, start, end):
    require(text.count(start) == text.count(end) == 1, 'unique reference block required')
    first = text.index(start)
    last = text.index(end, first)+len(end)
    return text[first:last]+'\n'


def line(text, pattern):
    rows = re.findall(pattern, text, re.M)
    require(len(rows) == 1, 'unique reference declaration required: '+pattern)
    return rows[0].rstrip()+'\n'


def macro(text, name):
    rows = list(re.finditer(r'^#define\s+'+re.escape(name)+r'(?=\s|\()', text, re.M))
    require(len(rows) == 1, 'unique reference macro required: '+name)
    first = rows[0].start()
    last = text.index('\n', first)
    while text[first:last].rstrip().endswith('\\'):
        last = text.index('\n', last+1)
    return text[first:last]+'\n'


def accessor(text, name):
    rows = list(re.finditer(r'^'+re.escape(name)+r'\(', text, re.M))
    require(len(rows) == 1, 'unique reference accessor required: '+name)
    first = text.rfind('\nstatic inline ', 0, rows[0].start())+1
    require(first > 0, 'reference inline signature required')
    last = text.index('\n}', rows[0].end())+2
    return text[first:last]+'\n'


FIXTURE = r'''#include <stdio.h>
#include <string.h>
#include "note10_user_instruction_fetch.h"
#include <sys/types.h>
#include <arm64/proc_reg.h>
#include <libkern/copyio.h>

static unsigned calls, bad_call, cases;
static uint64_t expected_address;
static int error_code, partial_copy;

int copyin(const user_addr_t address, void *destination, size_t length)
{
    static const unsigned char bytes[4] = {0x11, 0x22, 0x33, 0x44};
    ++calls;
    if (address != expected_address || length != sizeof(bytes)) bad_call = 1;
    if (!error_code || partial_copy)
        memcpy(destination, bytes, partial_copy ? 2 : sizeof(bytes));
    return error_code;
}

static arm_saved_state_t user_state(uint64_t pc)
{
    arm_saved_state_t state;
    memset(&state, 0xa5, sizeof(state));
    state.ash.flavor = ARM_SAVED_STATE64;
    state.ash.count = ARM_SAVED_STATE64_COUNT;
    state.ss_64.pc = pc;
    state.ss_64.cpsr = 0xa0000000U;
    return state;
}

static int check(const arm_saved_state_t *state, enum n10_user_fetch_status status,
                 int error, int partial, unsigned fetches)
{
    unsigned char before[sizeof(arm_saved_state_t)];
    if (state) memcpy(before, state, sizeof(before));
    expected_address = state && is_saved_state64(state) ? state->ss_64.pc : 0;
    calls = bad_call = 0; error_code = error; partial_copy = partial;
    struct n10_user_instruction result = n10_fetch_user_instruction(state);
    ++cases;
    if (result.status != status || calls != fetches || bad_call ||
        result.word != (status == N10_USER_FETCH_OK ? 0x44332211U : 0) ||
        result.copy_error != (fetches ? error : 0) ||
        (state && memcmp(before, state, sizeof(before)) != 0)) return 0;
    return 1;
}

#define CHECK(value) do { if (!(value)) { fprintf(stderr, "case line %d failed\n", __LINE__); return 1; } } while (0)
int main(void)
{
    arm_saved_state_t state = user_state(0x1000);
    CHECK(check(NULL, N10_USER_FETCH_BAD_STATE, 0, 0, 0));
    state.ash.flavor = 0; CHECK(check(&state, N10_USER_FETCH_BAD_STATE, 0, 0, 0));
    state = user_state(0x1000); state.ash.flavor = ARM_SAVED_STATE32; state.ash.count = ARM_SAVED_STATE32_COUNT;
    CHECK(check(&state, N10_USER_FETCH_BAD_STATE, 0, 0, 0));
    state = user_state(0x1000); --state.ash.count; CHECK(check(&state, N10_USER_FETCH_BAD_STATE, 0, 0, 0));
    state = user_state(0x1000); ++state.ash.count; CHECK(check(&state, N10_USER_FETCH_BAD_STATE, 0, 0, 0));
    state = user_state(0x1000); state.ss_64.cpsr |= PSR64_MODE_EL1; CHECK(check(&state, N10_USER_FETCH_BAD_STATE, 0, 0, 0));
    state = user_state(0x1000); state.ss_64.cpsr |= PSR64_MODE_RW_32; CHECK(check(&state, N10_USER_FETCH_BAD_STATE, 0, 0, 0));
    state = user_state(0x1001); CHECK(check(&state, N10_USER_FETCH_BAD_PC, 0, 0, 0));
    state = user_state(UINT64_MAX); CHECK(check(&state, N10_USER_FETCH_BAD_PC, 0, 0, 0));
    state = user_state(0x1000); CHECK(check(&state, N10_USER_FETCH_OK, 0, 0, 1));
    CHECK(check(&state, N10_USER_FETCH_COPY_ERROR, 14, 0, 1));
    CHECK(check(&state, N10_USER_FETCH_COPY_ERROR, 14, 1, 1));
    CHECK(check(&state, N10_USER_FETCH_COPY_ERROR, -7, 1, 1));
    state = user_state(UINT64_MAX-3); CHECK(check(&state, N10_USER_FETCH_COPY_ERROR, 14, 1, 1));
    state = user_state(0x8123456789abcdf0ULL); CHECK(check(&state, N10_USER_FETCH_OK, 0, 0, 1));
    state = user_state(0); CHECK(check(&state, N10_USER_FETCH_COPY_ERROR, 14, 0, 1));
    printf("v162 user instruction fetch boundary: PASS (%u cases)\n", cases);
    return 0;
}
'''


def prepare(out):
    require(out == OUT and out.resolve() == out and not out.is_symlink() and out.is_dir() and not any(out.iterdir()),
            'empty canonical ROOT-reserved fixture output required')
    refs = {name: pinned(REFERENCE/name, digest) for name, digest in REFERENCE_PINS.items()}
    sources = {name: pinned(ROOT/'note10/xnu26'/name, digest) for name, digest in SOURCE_PINS.items()}
    thread = refs['osfmk/mach/arm/thread_status.h']
    types = refs['bsd/arm/types.h']
    # Keep source notices with extracted declarations. The controlled fixture is LP64, HAS_APPLE_PAC=0.
    notice = thread[:thread.index('#ifndef _ARM_THREAD_STATUS_H_')]
    scalar = ('#ifndef N10_FIXTURE_SYS_TYPES_H\n#define N10_FIXTURE_SYS_TYPES_H\n#include <stdint.h>\n#include <stddef.h>\n'+
              line(refs['bsd/sys/_types/_u_int64_t.h'], r'^typedef unsigned long long\s+u_int64_t;')+
              line(types, r'^typedef int64_t\s+register_t;')+
              line(types, r'^typedef u_int64_t\s+user_addr_t;')+'#endif\n')
    machine = notice+'#ifndef N10_FIXTURE_THREAD_STATUS_H\n#define N10_FIXTURE_THREAD_STATUS_H\n#include <sys/types.h>\n#define HAS_APPLE_PAC 0\n'
    machine += line(refs['osfmk/mach/arm/boolean.h'], r'^typedef int\s+boolean_t;')
    machine += line(refs['bsd/arm/_types.h'], r'^typedef unsigned int\s+__darwin_natural_t;')
    machine += line(refs['osfmk/mach/arm/vm_types.h'], r'^typedef __darwin_natural_t\s+natural_t;')
    machine += line(refs['osfmk/mach/message.h'], r'^typedef natural_t\s+mach_msg_type_number_t;')
    machine += macro(thread, 'ARM_SAVED_STATE32')+macro(thread, 'ARM_SAVED_STATE64')
    machine += block(thread, 'struct arm_state_hdr {', 'typedef struct arm_state_hdr arm_state_hdr_t;')
    machine += block(thread, 'struct arm_saved_state32 {', 'typedef struct arm_saved_state arm_saved_state_t;')
    machine += ''.join(accessor(thread, name) for name in ('is_saved_state32', 'is_saved_state64',
                       'const_saved_state32', 'const_saved_state64', 'get_saved_state_pc', 'get_saved_state_cpsr'))+'#endif\n'
    modes = notice+'#ifndef N10_FIXTURE_PROC_REG_H\n#define N10_FIXTURE_PROC_REG_H\n'
    modes += ''.join(macro(refs['osfmk/arm64/proc_reg.h'], name) for name in ('PSR64_MODE_RW_SHIFT',
                    'PSR64_MODE_RW_32', 'PSR64_MODE_EL_SHIFT', 'PSR64_MODE_EL_MASK', 'PSR64_MODE_EL0',
                    'PSR64_MODE_EL1', 'PSR64_IS_USER', 'PSR64_IS_USER64'))+'#endif\n'
    copy = refs['bsd/libkern/copyio.h']
    copy_header = copy[:copy.index('#ifndef _LIBKERN_COPYIO_H_')]
    copy_header += '#include <sys/types.h>\n#define __sized_by(n)\n#define OS_WARN_RESULT __attribute__((warn_unused_result))\n'
    copy_header += line(copy, r'^int\s+copyin\(.*OS_WARN_RESULT;')
    outputs = {'include/sys/types.h': notice+scalar, 'include/mach/machine/thread_status.h': machine,
               'include/arm64/proc_reg.h': modes, 'include/libkern/copyio.h': copy_header,
               **sources, 'fixture.c': FIXTURE}
    require(sum(len(text.encode()) for text in outputs.values()) <= 512*1024, 'fixture source total bound')
    for name, text in outputs.items():
        target = out/name
        require(target.resolve().is_relative_to(out) and not target.exists() and not target.is_symlink(), 'fresh contained fixture file required')
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('xb') as stream:
            stream.write(text.encode('utf-8'))
    row = dict(schema='note10-v162-user-fetch-fixture-prepare-v1', prepared=True, reference_sha256=REFERENCE_PINS,
               source_sha256=SOURCE_PINS, output_sha256={name: hashlib.sha256(text.encode()).hexdigest() for name, text in outputs.items()},
               compiler_count=0, fixture_count=0, old_tests_count=0,
               limits='Exact pinned public reference fragments and copyin declaration; test-only copyin service, LP64/non-PAC frame. No current map ownership, full XNU header/firmware ABI, copyin implementation or trap hook proof.')
    with (out/'PREPARE-RECEIPT.json').open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(row, stream, indent=2, sort_keys=True)
        stream.write('\n')
    print(json.dumps(dict(prepared=True, source_files=len(outputs), compiler_count=0, fixture_count=0)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixture-dir', type=Path, required=True)
    args = parser.parse_args()
    prepare(args.fixture_dir)
