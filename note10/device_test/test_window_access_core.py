"""Compile and execute actual RAM-pattern C on PC buffers, never a phone."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
from run_probe import ROOT

HERE=Path(__file__).resolve().parent
HARNESS=r'''
#include <stdio.h>
#include <stdlib.h>
typedef unsigned long long u64;
typedef unsigned int u32;
static unsigned int mode;
static u64 words, reads, writes, fences, reschedules;
static u64 *buffer;
static u64 load_word(u64 *pointer) {
    u64 value;
    if (mode == 4 && pointer == buffer + words - 1) pointer = buffer;
    value = *(volatile u64 *)pointer;
    ++reads;
    if ((mode == 1 && reads == 17) ||
        (mode == 2 && reads == 2 * words + 13)) value ^= 1;
    return value;
}
static void store_word(u64 *pointer, u64 value) {
    ++writes;
    if (mode == 3 && writes == 17) return;
    if (mode == 4 && pointer == buffer + words - 1) pointer = buffer;
    *(volatile u64 *)pointer = value;
}
#define READ_ONCE(value) load_word(&(value))
#define WRITE_ONCE(value, number) store_word(&(value), (number))
#define N10_ACCESS_FENCE() do { ++fences; __asm__ volatile("" ::: "memory"); } while (0)
#define N10_ACCESS_RESCHED() (++reschedules)
#include "window_access_core.h"
int main(int argc, char **argv) {
    struct n10_access_result result;
    u64 allocation, i, remaining = 0;
    if (argc != 3) return 10;
    mode = (unsigned int)strtoul(argv[1], NULL, 10);
    words = strtoull(argv[2], NULL, 10);
    allocation = mode >= 5 ? 1 : words;
    buffer = calloc((size_t)allocation, sizeof(u64));
    if (!buffer) return 11;
    n10_access_test(mode == 5 ? NULL : buffer, words, &result);
    for (i = 0; i < allocation; ++i) remaining += buffer[i] != 0;
    printf("%llu %llu %llu %llu %llu %u %u %llu %llu %llu %llu %llu\n",
           result.written, result.checked, result.zeroed, result.zero_checked,
           result.mismatches, result.rounds, result.status,
           remaining, reads, writes, fences, reschedules);
    free(buffer);
    return 0;
}
'''


def test(output):
    if not output.resolve().is_relative_to((ROOT/'note10/private').resolve()) or output.exists():
        raise ValueError('Fresh private PC test output required')
    output.mkdir(parents=True)
    compiler=(ROOT/'host-tools/windows-build/llvm-mingw/llvm-mingw-20261006-ucrt-x86_64/bin/clang.exe'
              if sys.platform=='win32' else shutil.which('cc'))
    if not compiler:raise RuntimeError('Native C compiler required')
    source=output/'harness.c';source.write_text(HARNESS)
    exe=output/('test.exe' if sys.platform=='win32' else 'test')
    command=[str(compiler),'-std=c11','-O2','-Wall','-Wextra','-Werror','-I',str(HERE),str(source),'-o',str(exe)]
    built=subprocess.run(command,capture_output=True,timeout=60)
    (output/'compile.log').write_bytes(built.stdout+built.stderr)
    if built.returncode:raise RuntimeError('Native test compilation failed; see private compile.log')
    cases=[(0,n) for n in (1,17,8192,131072,33554432)]
    cases += [(mode,8192) for mode in range(1,5)] + [(5,8192),(6,0),(7,33554433)]
    results=[]
    for mode,words in cases:
        raw=subprocess.check_output([str(exe.resolve()),str(mode),str(words)],timeout=60)
        values=list(map(int,raw.split()))
        if len(values)!=12:raise ValueError('Unexpected C result')
        written,checked,zeroed,zero_checked,bad,rounds,status,remaining,reads,writes,fences,reschedules=values
        if mode>=5:
            if values!=[0,0,0,0,0,0,1,0,0,0,0,0]:raise ValueError('Invalid input touched the test buffer')
        else:
            passes=1 if mode in (1,3,4) else 2
            expected=[passes*words,passes*words,words,words,0 if mode==0 else 1,passes,0 if mode==0 else 2]
            if values[:7]!=expected or remaining or reads!=(passes+1)*words or writes!=(passes+1)*words or fences!=passes+1:
                raise ValueError('Wrong C disposition/counters for mode '+str(mode))
            if reschedules!=2*(passes+1)*(words//65536):raise ValueError('Reschedule opportunities missing')
        results.append({'mode':mode,'words':words,'status':status,'checked':checked,
                        'zero_checked':zero_checked,'mismatches':bad,'remaining_nonzero_words':remaining})
    report={'passed':True,'cases':results,'core_sha256':hashlib.sha256((HERE/'window_access_core.h').read_bytes()).hexdigest(),
            'full_256mib_pc_buffer_tested':True,'hardware_verified':False,'device_operations':[],
            'scope':'Actual C patterns/readback/scrub; PC buffers and modeled read/write faults/barriers/reschedule'}
    (output/'result.json').write_text(json.dumps(report,indent=2))
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    print(json.dumps(test(parser.parse_args().output)))
