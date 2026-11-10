"""One mocked PID1/core/decoder fixture; no real backing read, device or old suites."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
PID1 = ROOT/'note10/device_test/v190_builtin_read.c'
CORE = ROOT/'note10/xnu26'
SOURCES = [PID1, CORE/'note10_iostorage_read_range.c', CORE/'note10_iostorage_read_range.h',
           CORE/'note10_iostorage_read_request.c', CORE/'note10_iostorage_read_request.h']
BUILD, BOOT, CYCLE = '4'*32, '5'*32, '6'*32
HARNESS = r'''
#include <assert.h>
#include <stdio.h>
#include <string.h>
#define N190_HOST_FIXTURE 1
#define N190_BUILD_ID "44444444444444444444444444444444"
#include "PID1_SOURCE"
static int reads, seeks, opens, closes, writes, polls, live;
static n190_word extent_value, expected_offset;
static char capture[1024];
static n190_word n190_syscall(n190_word number, n190_word a0, n190_word a1,
                             n190_word a2, n190_word a3, n190_word a4)
{
    assert(a4 == 0);
    if (number == N190_OPENAT) {
        assert(a0 == -100 && a3 == 0);
        if (strcmp((const char *)a1, "/init") == 0) {
            assert(++opens == 1 && a2 == (00004000 | 0100000 | 02000000));
            live = 1;
            return 10;
        }
        assert(strcmp((const char *)a1, "/dev/kmsg") == 0 && !live);
        assert(a2 == (00000001 | 00004000 | 0100000 | 02000000));
        return 11;
    }
    if (number == N190_LSEEK) {
        assert(a0 == 10 && live && a1 == 0 && a2 == 2 && a3 == 0 && ++seeks == 1);
        return extent_value;
    }
    if (number == N190_PREAD64) {
        assert(a0 == 10 && live && a2 == 16 && a3 == expected_offset && ++reads == 1);
        memcpy((void *)a1, "0123456789ABCDEF", 16);
        return 16;
    }
    if (number == N190_CLOSE) {
        assert(a1 == 0 && a2 == 0 && a3 == 0);
        if (a0 == 10) {
            assert(live && ++closes == 1);
            live = 0;
            return 0;
        }
        assert(a0 == 11 && !live);
        return 0;
    }
    if (number == N190_WRITE) {
        size_t length = (size_t)a2;
        assert(a0 == 11 && !live && a3 == 0 && ++writes == 1);
        assert(length > 0 && length <= 512);
        memcpy(capture, (const void *)a1, length);
        capture[length] = 0;
        return (n190_word)length;
    }
    assert(number == N190_PPOLL && a0 == 0 && a1 == 0 && a2 == 0 && a3 == 0);
    ++polls;
    return -4;
}
int main(void)
{
    static const char argument[] = "id=" N190_BUILD_ID
        " boot=55555555555555555555555555555555 cycle=66666666666666666666666666666666 route=builtin arm=0";
    static const struct { n190_word eof, provider, offset; unsigned next_lba; } cases[] = {
        {5416, 5408, 5392, 338}, {5408, 5408, 5392, 338},
        {5425, 5424, 5408, 339}, {5439, 5424, 5408, 339},
        {64, 64, 48, 4}, {63, 0, 0, 0}, {1048577, 0, 0, 0},
    };
    unsigned index;
    for (index = 0; index < sizeof(cases)/sizeof(cases[0]); ++index) {
        char needle[80];
        int valid = cases[index].provider != 0;
        reads = seeks = opens = closes = writes = polls = live = 0;
        capture[0] = 0;
        extent_value = cases[index].eof;
        expected_offset = cases[index].offset;
        n190_observe(2, argument);
        assert(opens == 1 && seeks == 1 && closes == 1 && !live && writes == 1 && reads == valid);
        snprintf(needle, sizeof(needle), " ext=%lld pe=%lld ", (long long)extent_value, (long long)cases[index].provider);
        assert(strstr(capture, needle));
        snprintf(needle, sizeof(needle), " dl=%u da=0 dr=0 dc=0 dok=%d ", cases[index].next_lba, valid);
        assert(strstr(capture, needle));
        assert(strstr(capture, valid ? " passed=1" : " passed=0"));
        printf("CASE%u:%s\n", index, capture);
        n190_wait();
        assert(polls == 1);
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


WINDOW = b'0123456789ABCDEF'


def fnv32(data):
    checksum = 2166136261
    for byte in data:
        checksum = ((checksum ^ byte)*16777619)&0xffffffff
    return checksum


def decoder_checks(decoder, partial_frame, aligned_frame):
    def returning(phase, sequence):
        body = f'id={BUILD} cycle={CYCLE} phase={phase} seq={sequence} delay_ms=90000 status=0'
        return f'N10BOOTLINK2 boot={BOOT} N10RET1 {body} checksum={fnv32(body.encode()):08x}\n'

    expected = dict(offset=5392, length=16, fnv1a32=fnv32(WINDOW))
    def decode(frame, actual=5416, witness=expected):
        bound = f'id={BUILD} boot={BOOT} cycle={CYCLE}'
        prefix = returning(0, 2)+returning(0, 3)+f'N154ARM {bound} result=0\nN10ROUTE2 {bound} route=builtin exec_attempt=1\n'
        prefix += f'N159ROOT1 {bound} seen=1 skip=0 declared=6144 init_members=1 init_open=0\n'
        prefix += f'N157PRE1 {bound} lookup=0 rootfs=1 regular=1 open=0 xbits=111 bytes={actual} read=64 elf64le=1 aarch64=1\n'
        raw = (prefix+frame+returning(1, 2)+returning(1, 3)).encode()
        return decoder.decode(raw, BUILD, CYCLE, actual, 6144, witness)

    for frame, actual, tail in ((partial_frame, 5416, 8), (aligned_frame, 5408, 0)):
        result = decode(frame, actual)
        require(result['last_complete_block_verified'] is True and result['next_lba_denial_verified'] is True and
                result['read_completion_verified'] is True and result['partial_tail_bytes'] == tail and
                result['partial_tail_present'] is bool(tail) and result['partial_tail_denial_verified'] is bool(tail),
                'last block and next LBA classification')
    cases = 2
    mutations = [('off=5392', 'off=5376'), ('po=5392', 'po=5376'), ('dl=338', 'dl=337'),
                 ('dr=0', 'dr=1'), ('dc=0', 'dc=1'), ('da=0', 'da=1'), ('ext=5416', 'ext=5408')]
    invalid = []
    for old, new in mutations:
        changed = partial_frame.replace(' '+old, ' '+new, 1)
        require(changed != partial_frame, 'expected whole frame token missing')
        invalid.append(changed)
    invalid += [partial_frame.replace('N190READ1', 'N189READ1', 1),
                partial_frame.replace(BOOT, '7'*32, 1), partial_frame+partial_frame]
    for frame in invalid:
        try:
            decode(frame)
        except ValueError:
            pass
        else:
            raise ValueError('wrong last block or next LBA frame accepted')
        cases += 1
    try:
        decode(partial_frame, witness=dict(expected, offset=5376))
    except ValueError:
        pass
    else:
        raise ValueError('non-final producer window accepted')
    mismatch = decode(partial_frame, witness=dict(expected, fnv1a32=expected['fnv1a32'] ^ 1))
    require(mismatch['read_completion_verified'] is False and mismatch['last_complete_block_verified'] is False,
            'different last block witness cannot pass')
    return cases+2


def final_block_checks(pipeline, builder):
    cases = 0
    for actual, provider, offset, next_lba, tail in ((5416, 5408, 5392, 338, 8), (5408, 5408, 5392, 338, 0),
                                                   (5425, 5424, 5408, 339, 1)):
        elf = bytearray(actual)
        elf[offset:provider] = WINDOW
        elf[provider:] = b'Z'*tail
        window = builder.v190_window(elf)
        require(window == dict(offset=offset, length=16, fnv1a32=fnv32(WINDOW)), 'producer last complete block only')
        proof = dict(byte_window=window, provider_geometry=dict(block_bytes=16, extent_bytes=provider, tail_bytes=tail),
                     request=dict(block_bytes=16, lba=next_lba-1, count=1, descriptor_length=16, direction=1),
                     denial=dict(lba=next_lba, count=1, descriptor_length=16, admitted=False, read_callbacks=0, completion_callbacks=0))
        require(pipeline.last_block_fields(proof, actual) == proof, 'exact producer and consumer last block agreement')
        cases += 1
    wrong = [dict(proof, byte_window=dict(window, offset=offset-16)),
             dict(proof, byte_window=dict(window, length=32)),
             dict(proof, denial=dict(proof['denial'], descriptor_length=15)),
             dict(proof, denial=dict(proof['denial'], lba=next_lba-1)),
             dict(proof, provider_geometry=dict(proof['provider_geometry'], tail_bytes=0))]
    for changed in wrong:
        try:
            pipeline.last_block_fields(changed, actual)
        except ValueError:
            pass
        else:
            raise ValueError('mismatched producer last block or next LBA proof accepted')
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
    require(args.pipeline == ROOT/'note10/private/device-test/v190-last-complete-block-read-native-ci-20261111/v190_pipeline.py' and
            args.pipeline.resolve() == args.pipeline and not args.pipeline.is_symlink() and
            0 < args.pipeline.stat().st_size <= 131072 and digest(args.pipeline) == args.pipeline_sha256 and
            0 < builder_path.stat().st_size <= 131072 and digest(builder_path) == args.builder_sha256, 'exact new consumer source pins')
    compiler = ROOT/'host-tools/windows-build/llvm-mingw/llvm-mingw-20261006-ucrt-x86_64/bin/x86_64-w64-mingw32-clang.exe'
    require(compiler.is_file(), 'existing_host_compiler_required')
    pins = {path.relative_to(ROOT).as_posix(): digest(path) for path in SOURCES}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.mkdir(mode=0o700)
    result = dict(schema='note10-v190-builtin-read-host-once-v1', passed=False, compiler_count=0,
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
        frames = [line.split(':', 1) for line in call.stdout.decode('utf-8').splitlines() if line.startswith('CASE')]
        require([row[0] for row in frames] == [f'CASE{index}' for index in range(7)], 'seven final-block fixture frames required')
        decoder = load_source('v190_reviewed_decoder', args.decoder)
        pipeline = load_source('v190_reviewed_pipeline', args.pipeline)
        builder = load_source('v190_reviewed_builder', builder_path)
        final_block_cases = final_block_checks(pipeline, builder)
        decoder_cases = decoder_checks(decoder, frames[0][1]+'\n', frames[1][1]+'\n')
        require({path.relative_to(ROOT).as_posix(): digest(path) for path in SOURCES} == pins and
                digest(args.decoder) == args.decoder_sha256 and digest(args.pipeline) == args.pipeline_sha256 and
                digest(builder_path) == args.builder_sha256, 'fixture_sources_changed')
        result.update(passed=True, groups=3, cases_by_group=[7, final_block_cases, decoder_cases], cases=7+final_block_cases+decoder_cases,
                      consumer_source_sha256={str(args.pipeline): args.pipeline_sha256, str(builder_path): args.builder_sha256})
    except BaseException as error:
        result.update(error_type=type(error).__name__, failure_code=str(error)[:200])
    finally:
        save(out/'RESULT.json', result)
    print(json.dumps(dict(passed=result['passed'], groups=result.get('groups', 0))))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
