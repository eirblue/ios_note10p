"""Execute actual kernel wrapper with modeled reservation/mapping APIs on PC."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
from run_probe import ROOT
from decode_reservation import checksum
from decode_window_access import decode

HERE=Path(__file__).resolve().parent
ID='0123456789abcdef0123456789abcdef'
STUB=r'''
#include <stdio.h>
#include <stdlib.h>
#include <stdarg.h>
typedef unsigned long long u64;
typedef unsigned int u32;
typedef u64 phys_addr_t;
#define __init
#define PAGE_SHIFT 12
#define N10_WINDOW_SIZE (256ULL << 20)
#define N10_WINDOW_ALIGN (32ULL << 20)
#define N10_WINDOW_LIMIT (1ULL << 40)
#define N10_RESERVE_BUILD_ID "0123456789abcdef0123456789abcdef"
static phys_addr_t n10_window_base = 0xa00000000ULL;
static int n10_window_status = 1;
static int mode;
static u64 *buffer, writes, reads;
static void *phys_to_virt(phys_addr_t address) { (void)address; return buffer; }
static int virt_addr_valid(const void *p) {
    return !((mode == 8 && p == buffer) ||
             (mode == 9 && p == buffer + N10_WINDOW_SIZE / 8 - 1));
}
static phys_addr_t virt_to_phys(const void *p) {
    phys_addr_t address = n10_window_base + (const unsigned char *)p - (const unsigned char *)buffer;
    if ((mode == 10 && p == buffer) ||
        (mode == 11 && p == buffer + N10_WINDOW_SIZE / 8 - 1)) address += 8;
    return address;
}
static u64 load_word(u64 *p) {
    u64 value = *(volatile u64 *)p;
    ++reads;
    return mode == 12 && reads == 17 ? value ^ 1 : value;
}
static void store_word(u64 *p, u64 value) { ++writes; *(volatile u64 *)p = value; }
#define READ_ONCE(value) load_word(&(value))
#define WRITE_ONCE(value, number) store_word(&(value), (number))
#define smp_mb() __asm__ volatile("" ::: "memory")
#define cond_resched() ((void)0)
#define pr_info(...) printf(__VA_ARGS__)
static int scnprintf(char *out, unsigned long capacity, const char *format, ...) {
    va_list args; int result; va_start(args,format);
    result=vsnprintf(out,capacity,format,args); va_end(args);
    return result < (int)capacity ? result : (int)capacity-1;
}
'''
MAIN=r'''
int main(int argc, char **argv) {
    unsigned long pages=65536, reserved=65536, invalid=0;
    if (argc != 2) return 10;
    mode=atoi(argv[1]);buffer=calloc((size_t)(N10_WINDOW_SIZE / 8),sizeof(u64));
    if (!buffer) return 11;
    if (mode == 1) n10_window_status=0;
    if (mode == 2) --reserved;
    if (mode == 3) invalid=1;
    if (mode == 4) --pages;
    if (mode == 5) n10_window_base=0;
    if (mode == 6) n10_window_base+=8;
    if (mode == 7) n10_window_base=N10_WINDOW_LIMIT;
    note10_test_xnu_window_access(reserved,pages,invalid);
    printf("MODEL writes=%llu reads=%llu\n",writes,reads);
    free(buffer);return 0;
}
'''


def test(output):
    if not output.resolve().is_relative_to((ROOT/'note10/private').resolve()) or output.exists():
        raise ValueError('Fresh private output required')
    output.mkdir(parents=True)
    reserve=(HERE/'xnu_reserve.c').read_text()
    start=reserve.index('static u32 n10_frame_checksum(')
    end=reserve.index('static void __init note10_reserve_xnu_window',start)
    wrapper=(HERE/'xnu_window_access.c').read_text()
    modeled=re.sub(r'^#include <[^>]+>\n','',wrapper,flags=re.M)
    core=(HERE/'window_access_core.h').read_bytes()
    (output/'note10_window_access_core.h').write_bytes(core)
    source=output/'modeled-wrapper.c';source.write_text(STUB+reserve[start:end]+modeled+MAIN)
    compiler=(ROOT/'host-tools/windows-build/llvm-mingw/llvm-mingw-20261006-ucrt-x86_64/bin/clang.exe'
              if sys.platform=='win32' else shutil.which('cc'))
    if not compiler:raise RuntimeError('Native C compiler required')
    exe=output/('test.exe' if sys.platform=='win32' else 'test')
    result=subprocess.run([str(compiler),'-O2','-Wall','-Wextra','-Werror',str(source),'-o',str(exe)],
                          capture_output=True,timeout=60)
    (output/'compile.log').write_bytes(result.stdout+result.stderr)
    if result.returncode:raise RuntimeError('Kernel wrapper model compilation failed')
    baseline=''
    for seq in range(2):
        body=f'id={ID} seq={seq} base=a00000000 size=10000000 align=2000000 pages=65536 reserved=65536 invalid=0 shift=12'
        baseline+='N10RAM2 '+body+f' checksum={checksum(body.encode()):08x}\n'
    cases=[]
    for mode in range(13):
        raw=subprocess.check_output([str(exe.resolve()),str(mode)],timeout=60)
        text=raw.decode();(output/f'mode-{mode}.txt').write_text(text)
        match=re.search(r'MODEL writes=([0-9]+) reads=([0-9]+)',text)
        if not match:raise ValueError('Missing modeled I/O counters')
        writes,reads=map(int,match.groups())
        try:observation=decode(baseline+text,ID);accepted=True
        except ValueError:observation=None;accepted=False
        if accepted!=(mode==0):raise ValueError('Wrong kernel-wrapper disposition')
        if mode in range(1,12) and (writes or reads):raise ValueError('Failed guard accessed the buffer')
        if mode==0 and (writes!=100663296 or reads!=100663296 or observation['access_intact_frame_count']!=32):
            raise ValueError('Incomplete full-window wrapper execution')
        if mode==12 and (writes!=67108864 or reads!=67108864):raise ValueError('Mismatch path did not scrub')
        cases.append({'mode':mode,'accepted':accepted,'writes':writes,'reads':reads})
    report={'passed':True,'cases':cases,'wrapper_sha256':hashlib.sha256(wrapper.encode()).hexdigest(),
            'core_sha256':hashlib.sha256(core).hexdigest(),'hardware_verified':False,'device_operations':[],
            'scope':'Actual kernel wrapper/core/checksum C; modeled reservation/PFN/linear-map APIs on PC buffers'}
    (output/'result.json').write_text(json.dumps(report,indent=2));return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    print(json.dumps(test(p.parse_args().output)))
