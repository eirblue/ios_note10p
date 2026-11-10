"""One mocked PID1/core/decoder fixture; no real backing read, device or old suites."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import struct

ROOT = Path(__file__).resolve().parents[2]
PID1 = ROOT/'note10/device_test/v189_builtin_read.c'
CORE = ROOT/'note10/xnu26'
SOURCES = [PID1, CORE/'note10_iostorage_read_range.c', CORE/'note10_iostorage_read_range.h',
           CORE/'note10_iostorage_read_request.c', CORE/'note10_iostorage_read_request.h']
BUILD, BOOT, CYCLE = '4'*32, '5'*32, '6'*32
HARNESS = r'''
#include <assert.h>
#include <stdio.h>
#include <string.h>
#define N189_HOST_FIXTURE 1
#define N189_BUILD_ID "44444444444444444444444444444444"
#include "PID1_SOURCE"
static int mode, reads, seeks, opens, closes, writes, polls, live;
static n189_word extent_value;
static char capture[1024];
static n189_word n189_syscall(n189_word number, n189_word a0, n189_word a1,
                             n189_word a2, n189_word a3, n189_word a4)
{
    assert(a4 == 0);
    if (number == N189_OPENAT) {
        assert(a0 == -100 && a3 == 0);
        if (strcmp((const char *)a1, "/init") == 0) {
            assert(++opens == 1 && a2 == (00004000 | 0100000 | 02000000));
            if (mode == 6) return -13;
            live = 1; return 10;
        }
        assert(strcmp((const char *)a1, "/dev/kmsg") == 0 && !live);
        assert(a2 == (00000001 | 00004000 | 0100000 | 02000000));
        return 11;
    }
    if (number == N189_LSEEK) {
        assert(a0 == 10 && live && a1 == 0 && a2 == 2 && a3 == 0 && ++seeks == 1);
        return extent_value;
    }
    if (number == N189_PREAD64) {
        unsigned char *data = (unsigned char *)a1;
        assert(a0 == 10 && live && a2 == 32 && a3 == 48 && ++reads == 1);
        if (mode == 2 || mode == 9) return mode == 2 ? -5 : -4;
        memset(data, 0, 32);
        data[4] = 64; data[6] = 56; data[8] = 3; data[16] = 1; data[20] = 5; data[24] = 32;
        if (mode == 7) data[6] = 55;
        if (mode == 11) data[4] = 0;
        return mode == 1 ? 31 : mode == 8 ? 33 : 32;
    }
    if (number == N189_CLOSE) {
        assert(a1 == 0 && a2 == 0 && a3 == 0);
        if (a0 == 10) {
            assert(live && ++closes == 1); live = 0;
            return mode == 3 ? -5 : 0;
        }
        assert(a0 == 11 && !live); return 0;
    }
    if (number == N189_WRITE) {
        size_t length = (size_t)a2;
        assert(a0 == 11 && !live && a3 == 0 && ++writes == 1);
        assert(length > 0 && length <= 512);
        memcpy(capture, (const void *)a1, length); capture[length] = 0;
        return (n189_word)length;
    }
    assert(number == N189_PPOLL && a0 == 0 && a1 == 0 && a2 == 0 && a3 == 0);
    ++polls; return -4;
}
static void reset(int selected)
{
    mode = selected;
    reads = seeks = opens = closes = writes = polls = live = 0;
    capture[0] = 0;
}
int main(void)
{
    static const char argument[] = "id=" N189_BUILD_ID
        " boot=55555555555555555555555555555555 cycle=66666666666666666666666666666666 route=builtin arm=0";
    static const n189_word edges[] = {5352, 5360, 79, 1048577, 0};
    int index;
    for (index = 0; index < 37; ++index) {
        char needle[80];
        int valid;
        reset(0);
        extent_value = index < 5 ? edges[index] : index < 21 ? 5312 + index - 5 : 80 + index - 21;
        valid = extent_value >= 80 && extent_value <= 1048576;
        n189_observe(2, argument);
        assert(opens == 1 && closes == 1 && !live && writes == 1);
        assert(reads == valid);
        snprintf(needle, sizeof(needle), " ext=%lld pe=%lld ", (long long)extent_value,
                 (long long)(valid ? extent_value - extent_value % 16 : 0));
        assert(strstr(capture, needle));
        assert(strstr(capture, valid ? " passed=1" : " passed=0"));
        if (valid) assert(strstr(capture, " da=0 dr=0 dc=0 dok=1"));
        printf("CASE%d:%s\n", index, capture);
        n189_wait(); assert(polls == 1);
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
    def returning(phase, sequence):
        body = f'id={BUILD} cycle={CYCLE} phase={phase} seq={sequence} delay_ms=90000 status=0'
        checksum = 2166136261
        for byte in body.encode():
            checksum = ((checksum ^ byte)*16777619)&0xffffffff
        return f'N10BOOTLINK2 boot={BOOT} N10RET1 {body} checksum={checksum:08x}\n'
    window = bytearray(32)
    window[4] = 64; window[6] = 56; window[8] = 3; window[16] = 1; window[20] = 5; window[24] = 32
    checksum = 2166136261
    for byte in window:
        checksum = ((checksum ^ byte)*16777619)&0xffffffff
    expected = dict(offset=48, length=32, phoff=64, ehsize=64, phentsize=56, phnum=3, p_type=1, p_flags=5, fnv1a32=checksum)
    def decode(frame, actual=5352):
        bound = f'id={BUILD} boot={BOOT} cycle={CYCLE}'
        prefix = returning(0, 2)+returning(0, 3)+f'N154ARM {bound} result=0\nN10ROUTE2 {bound} route=builtin exec_attempt=1\n'
        prefix += f'N159ROOT1 {bound} seen=1 skip=0 declared=6144 init_members=1 init_open=0\n'
        prefix += f'N157PRE1 {bound} lookup=0 rootfs=1 regular=1 open=0 xbits=111 bytes={actual} read=64 elf64le=1 aarch64=1\n'
        raw = (prefix+frame+returning(1, 2)+returning(1, 3)).encode()
        return decoder.decode(raw, BUILD, CYCLE, actual, 6144, expected)
    first = decode(actual_frame)
    require(first['provider_extent_verified'] and first['read_completion_verified'], '5352_tail8_must_PASS')
    rounded_file = actual_frame.replace(' ext=5352', ' ext=5360', 1).replace(' pe=5344', ' pe=5360', 1)
    require(decode(rounded_file, 5360)['read_completion_verified'], 'genuine_actual5360_is_valid')
    cases = 2
    for frame, actual in ((actual_frame.replace(' pe=5344', ' pe=5360', 1), 5352),
                          (actual_frame.replace(' pe=5344', ' pe=5352', 1), 5352),
                          (actual_frame.replace(' pe=5344', ' pe=5328', 1), 5352),
                          (actual_frame.replace(' ext=5352', ' ext=5344', 1), 5352),
                          (actual_frame, 5344), (actual_frame, 5360),
                          (actual_frame.replace('N189READ1', 'N188READ1'), 5352)):
        try:
            decode(frame, actual)
        except ValueError:
            pass
        else:
            raise ValueError('wrong_actual_or_provider_projection_accepted')
        cases += 1
    return cases


def projection_checks(pipeline, builder):
    cases = 0
    for actual in (5352, 5360, *range(5312, 5328), *range(80, 96)):
        value = dict(block_bytes=16, extent_bytes=actual-actual%16, tail_bytes=actual%16)
        require(pipeline.provider_geometry(value, actual) == value, 'actual/provider_tail_projection')
        cases += 1
    for value, actual in ((dict(block_bytes=16, extent_bytes=5360, tail_bytes=8), 5352),
                          (dict(block_bytes=16, extent_bytes=5344, tail_bytes=0), 5352),
                          (dict(block_bytes=16, extent_bytes=5344, tail_bytes=True), 5352),
                          (dict(block_bytes=16, extent_bytes=64, tail_bytes=15), 79),
                          (dict(block_bytes=16, extent_bytes=1048576, tail_bytes=1), 1048577)):
        try:
            pipeline.provider_geometry(value, actual)
        except ValueError:
            pass
        else:
            raise ValueError('invalid_provider_claim_accepted')
        cases += 1
    for length in (5352, 5360):
        elf = bytearray(length)
        struct.pack_into('<Q', elf, 32, 64)
        struct.pack_into('<HHH', elf, 52, 64, 56, 3)
        struct.pack_into('<II', elf, 64, 1, 5)
        value = builder.v189_window(elf)
        require(value['offset'] == 48 and value['length'] == 32 and value['phoff'] == 64,
                'actual_producer_remainder_gate_removed')
        cases += 1
    return cases


def load_source(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    loaded = importlib.util.module_from_spec(spec)
    sys.modules[name] = loaded
    spec.loader.exec_module(loaded)
    return loaded


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--decoder', type=Path, required=True)
    parser.add_argument('--decoder-sha256', required=True)
    parser.add_argument('--pipeline', type=Path, required=True)
    parser.add_argument('--pipeline-sha256', required=True)
    parser.add_argument('--builder-sha256', required=True)
    args = parser.parse_args()
    out = args.output.absolute()
    require(out.resolve() == out and out.is_relative_to(ROOT/'note10/private') and not out.exists() and not out.is_symlink(),
            'fresh_private_fixture_output')
    require(args.decoder.resolve() == args.decoder and args.decoder.is_file() and not args.decoder.is_symlink() and
            0 < args.decoder.stat().st_size <= 131072 and digest(args.decoder) == args.decoder_sha256,
            'exact_bounded_decoder_source')
    builder_path = ROOT/'note10/device_test/v154_linux_build.py'
    require(args.pipeline == ROOT/'note10/private/device-test/v189-complete-block-read-native-ci-20261111/v189_pipeline.py' and
            args.pipeline.resolve() == args.pipeline and not args.pipeline.is_symlink() and
            0 < args.pipeline.stat().st_size <= 131072 and digest(args.pipeline) == args.pipeline_sha256 and
            0 < builder_path.stat().st_size <= 131072 and digest(builder_path) == args.builder_sha256, 'exact new consumer source pins')
    compiler = ROOT/'host-tools/windows-build/llvm-mingw/llvm-mingw-20261006-ucrt-x86_64/bin/x86_64-w64-mingw32-clang.exe'
    require(compiler.is_file(), 'existing_host_compiler_required')
    pins = {path.relative_to(ROOT).as_posix(): digest(path) for path in SOURCES}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.mkdir(mode=0o700)
    result = dict(schema='note10-v189-builtin-read-host-once-v1', passed=False, compiler_count=0,
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
        decoder = load_source('v189_reviewed_decoder', args.decoder)
        pipeline = load_source('v189_reviewed_pipeline', args.pipeline)
        builder = load_source('v189_reviewed_builder', builder_path)
        projection_cases = projection_checks(pipeline, builder)
        decoder_cases = decoder_checks(decoder, actual_frame)
        require({path.relative_to(ROOT).as_posix(): digest(path) for path in SOURCES} == pins and
                digest(args.decoder) == args.decoder_sha256 and digest(args.pipeline) == args.pipeline_sha256 and
                digest(builder_path) == args.builder_sha256, 'fixture_sources_changed')
        result.update(passed=True, groups=3, cases_by_group=[37, projection_cases, decoder_cases], cases=37+projection_cases+decoder_cases,
                      consumer_source_sha256={str(args.pipeline): args.pipeline_sha256, str(builder_path): args.builder_sha256})
    except BaseException as error:
        result.update(error_type=type(error).__name__, failure_code=str(error)[:200])
    finally:
        save(out/'RESULT.json', result)
    print(json.dumps(dict(passed=result['passed'], groups=result.get('groups', 0))))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
