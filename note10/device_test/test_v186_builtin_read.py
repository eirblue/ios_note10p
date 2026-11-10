"""One mocked PID1/core/decoder fixture; no real backing read, device or old suites."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
PID1 = ROOT/'note10/device_test/v186_builtin_read.c'
CORE = ROOT/'note10/xnu26'
SOURCES = [PID1, CORE/'note10_iostorage_read_range.c', CORE/'note10_iostorage_read_range.h',
           CORE/'note10_iostorage_read_request.c', CORE/'note10_iostorage_read_request.h']
BUILD, BOOT, CYCLE = '4'*32, '5'*32, '6'*32
HARNESS = r'''
#include <assert.h>
#include <stdio.h>
#include <string.h>
#define N186_HOST_FIXTURE 1
#define N186_BUILD_ID "44444444444444444444444444444444"
#include "PID1_SOURCE"
static int mode, calls, reads, seeks, opens, closes, writes, polls, live;
static char capture[1024];
static n186_word n186_syscall(n186_word number, n186_word a0, n186_word a1,
                             n186_word a2, n186_word a3, n186_word a4)
{
    ++calls;
    assert(a4 == 0);
    if (number == N186_OPENAT) {
        assert(a0 == -100 && a3 == 0);
        if (strcmp((const char *)a1, "/init") == 0) {
            assert(++opens == 1 && a2 == (00004000 | 0100000 | 02000000));
            if (mode == 6) return -13;
            live = 1; return 10;
        }
        assert(strcmp((const char *)a1, "/dev/kmsg") == 0 && !live);
        assert(a2 == (00000001 | 00004000 | 0100000 | 02000000));
        return mode == 10 ? -13 : 11;
    }
    if (number == N186_LSEEK) {
        assert(a0 == 10 && live && a1 == 0 && a2 == 2 && a3 == 0 && ++seeks == 1);
        return mode == 4 ? 63 : mode == 5 ? 1048577 : 4096;
    }
    if (number == N186_PREAD64) {
        unsigned char *data = (unsigned char *)a1;
        assert(a0 == 10 && live && a2 == 64 && a3 == 0 && ++reads == 1);
        if (mode == 2 || mode == 9) return mode == 2 ? -5 : -4;
        memset(data, 0, 64);
        memcpy(data, "\177ELF\2\1\1", 7);
        data[16] = 2; data[18] = 183;
        if (mode == 7) data[18] = 62;
        return mode == 1 ? 63 : mode == 8 ? 65 : 64;
    }
    if (number == N186_CLOSE) {
        assert(a1 == 0 && a2 == 0 && a3 == 0);
        if (a0 == 10) {
            assert(live && ++closes == 1); live = 0;
            return mode == 3 ? -5 : 0;
        }
        assert(a0 == 11 && !live); return 0;
    }
    if (number == N186_WRITE) {
        size_t length = (size_t)a2;
        assert(a0 == 11 && !live && a3 == 0 && ++writes == 1);
        assert(length > 0 && length <= 512);
        if (mode == 11) --length;
        memcpy(capture, (const void *)a1, length); capture[length] = 0;
        return (n186_word)length;
    }
    assert(number == N186_PPOLL && a0 == 0 && a1 == 0 && a2 == 0 && a3 == 0);
    ++polls; return -4;
}
static void reset(int selected)
{
    mode = selected;
    calls = reads = seeks = opens = closes = writes = polls = live = 0;
    capture[0] = 0;
}
int main(void)
{
    static const char argument[] = "id=" N186_BUILD_ID
        " boot=55555555555555555555555555555555 cycle=66666666666666666666666666666666 route=builtin arm=0";
    int index;
    for (index = 0; index < 12; ++index) {
        reset(index);
        n186_observe(2, argument);
        assert(opens == 1 && !live);
        assert(closes == (index == 6 ? 0 : 1));
        assert(reads == (index == 4 || index == 5 || index == 6 ? 0 : 1));
        assert(writes == (index == 10 ? 0 : 1));
        if (index != 10) {
            assert(strstr(capture, index == 0 || index == 11 ? " passed=1" : " passed=0"));
            printf("CASE%d:%s\n", index, capture);
        }
        n186_wait(); assert(polls == 1);
    }
    for (index = 0; index < 6; ++index) {
        char bad[sizeof(argument)];
        memcpy(bad, argument, sizeof(argument));
        if (index == 2) bad[3] = '7';
        if (index == 3) memset(bad + 41, '0', 32);
        if (index == 4) bad[81] = 'g';
        if (index == 5) bad[sizeof(argument)-2] = '1';
        reset(0);
        n186_observe(index == 0 ? 1 : 2, index == 1 ? NULL : bad);
        assert(calls == 0 && !live);
        n186_wait(); assert(polls == 1);
    }
    return 0;
}
'''


def require(ok, code):
    if not ok:
        raise ValueError(code)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, data):
    with path.open('x', encoding='utf-8') as stream:
        stream.write(json.dumps(data, sort_keys=True, indent=2)+'\n')


def decoder_checks(decoder, actual_frame):
    bound = f'id={BUILD} boot={BOOT} cycle={CYCLE}'
    def returning(phase, sequence):
        body = f'id={BUILD} cycle={CYCLE} phase={phase} seq={sequence} delay_ms=90000 status=0'
        checksum = 2166136261
        for byte in body.encode():
            checksum = ((checksum ^ byte)*16777619)&0xffffffff
        return f'N10BOOTLINK2 boot={BOOT} N10RET1 {body} checksum={checksum:08x}\n'
    prefix = returning(0, 2)+returning(0, 3)+f'N154ARM {bound} result=0\nN10ROUTE2 {bound} route=builtin exec_attempt=1\n'
    prefix += f'N159ROOT1 {bound} seen=1 skip=0 declared=5120 init_members=1 init_open=0\n'
    prefix += f'N157PRE1 {bound} lookup=0 rootfs=1 regular=1 open=0 xbits=111 bytes=4096 read=64 elf64le=1 aarch64=1\n'
    suffix = returning(1, 2)+returning(1, 3)
    def decode(frame, before=prefix, after=suffix):
        return decoder.decode((before+frame+after).encode(), BUILD, CYCLE, 4096, 5120)
    result = decode(actual_frame)
    require(result['read_completion_verified'] is True and result['entry_proven'] is True,
            'actual_mocked_C_frame_composition')
    cases = 1
    mutations = [('admitted=1', 'admitted=0'), ('completion_callbacks=1', 'completion_callbacks=0'),
                 ('pread64_return=64', 'pread64_return=63'), ('completion_status=0', 'completion_status=1'),
                 ('completed_bytes=64', 'completed_bytes=63'), ('header_aarch64=1', 'header_aarch64=0'),
                 ('close_rc=0', 'close_rc=-5'), ('extent=4096', 'extent=4097'),
                 ('returned_before_close=1', 'returned_before_close=0'), ('owner_live_at_completion=1', 'owner_live_at_completion=0')]
    for old, new in mutations:
        changed = actual_frame.replace(old, new, 1)
        try:
            decode(changed)
        except ValueError:
            pass
        else:
            raise ValueError('inconsistent_PASS_accepted')
        cases += 1
    for frame in (actual_frame+actual_frame, actual_frame.replace(BOOT, '7'*32), actual_frame[:-1]+'garbage\n',
                  actual_frame+actual_frame.replace(BOOT, '7'*32), actual_frame.replace('N186READ1', 'N158PID1')):
        try:
            decode(frame)
        except ValueError:
            pass
        else:
            raise ValueError('duplicate_wrong_or_truncated_record_accepted')
        cases += 1
    failure = actual_frame.replace('close_rc=0', 'close_rc=-5').replace('passed=1', 'passed=0')
    require(decode(failure)['read_completion_verified'] is False, 'failed_close_is_not_PASS')
    cases += 1
    try:
        decode(actual_frame, prefix, '')
    except ValueError:
        pass
    else:
        raise ValueError('missing_return_accepted')
    return cases+1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--decoder', type=Path, required=True)
    parser.add_argument('--decoder-sha256', required=True)
    args = parser.parse_args()
    out = args.output.absolute()
    require(out.resolve() == out and out.is_relative_to(ROOT/'note10/private') and not out.exists() and not out.is_symlink(),
            'fresh_private_fixture_output')
    require(args.decoder.resolve() == args.decoder and args.decoder.is_file() and not args.decoder.is_symlink() and
            0 < args.decoder.stat().st_size <= 131072 and digest(args.decoder) == args.decoder_sha256,
            'exact_bounded_decoder_source')
    compiler = ROOT/'host-tools/windows-build/llvm-mingw/llvm-mingw-20261006-ucrt-x86_64/bin/x86_64-w64-mingw32-clang.exe'
    require(compiler.is_file(), 'existing_host_compiler_required')
    pins = {path.relative_to(ROOT).as_posix(): digest(path) for path in SOURCES}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.mkdir(mode=0o700)
    result = dict(schema='note10-v186-builtin-read-host-once-v1', passed=False, compiler_count=0,
                  fixture_count=0, old_tests_count=0, source_sha256=pins, decoder_source_sha256=args.decoder_sha256,
                  actual_backing_read_syscalls=0, device_operations=0, CI=0)
    save(out/'STARTED.json', result)
    try:
        source = out/'fixture.c'
        source.write_text(HARNESS.replace('PID1_SOURCE', PID1.as_posix()), encoding='utf-8')
        binary = out/'fixture.exe'
        argv = [str(compiler), '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror', '-I', str(CORE),
                str(source), str(CORE/'note10_iostorage_read_range.c'), str(CORE/'note10_iostorage_read_request.c'), '-o', str(binary)]
        result['compiler_count'] = 1
        call = subprocess.run(argv, capture_output=True, timeout=60)
        (out/'compile.stdout').write_bytes(call.stdout); (out/'compile.stderr').write_bytes(call.stderr)
        result.update(compiler_argv=argv, compiler_returncode=call.returncode)
        require(call.returncode == 0, 'new_host_compile_failed')
        result['fixture_count'] = 1
        call = subprocess.run([str(binary)], capture_output=True, timeout=30)
        (out/'fixture.stdout').write_bytes(call.stdout); (out/'fixture.stderr').write_bytes(call.stderr)
        result['fixture_returncode'] = call.returncode
        require(call.returncode == 0, 'new_host_fixture_failed')
        frames = call.stdout.decode('utf-8').split('CASE0:', 1)
        require(len(frames) == 2, 'first_native_mock_frame_required')
        actual_frame = frames[1].split('\n', 1)[0]+'\n'
        spec = importlib.util.spec_from_file_location('v186_reviewed_decoder', args.decoder)
        decoder = importlib.util.module_from_spec(spec); spec.loader.exec_module(decoder)
        decoder_cases = decoder_checks(decoder, actual_frame)
        require({path.relative_to(ROOT).as_posix(): digest(path) for path in SOURCES} == pins and
                digest(args.decoder) == args.decoder_sha256, 'fixture_sources_changed')
        result.update(passed=True, groups=3, cases_by_group=[12, 6, decoder_cases], cases=18+decoder_cases)
    except BaseException as error:
        result.update(error_type=type(error).__name__, failure_code=str(error)[:200])
    finally:
        save(out/'RESULT.json', result)
    print(json.dumps(dict(passed=result['passed'], groups=result.get('groups', 0))))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
