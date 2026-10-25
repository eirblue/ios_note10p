"""Execute actual CPU/cache diagnostic C with modeled kernel APIs on PC RAM."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
from run_probe import ROOT
from decode_cpu_cache import decode
from decode_reservation import checksum

HERE=Path(__file__).resolve().parent
IDENTITY='0123456789abcdef0123456789abcdef'
STUB=r'''
#include <stdio.h>
#include <stdlib.h>
#include <stdbool.h>
#include <string.h>
#include <stdarg.h>
#include <stdint.h>
#ifdef _WIN32
#include <windows.h>
#include <bcrypt.h>
#else
#include <openssl/sha.h>
#endif
typedef unsigned char u8;
typedef unsigned long long u64;
#define PAGE_SIZE 4096
#define N10_WINDOW_SIZE (256ULL<<20)
#define N10_WINDOW_ALIGN (32ULL<<20)
#define N10_WINDOW_LIMIT (1ULL<<40)
#define N10_RESERVE_BUILD_ID "0123456789abcdef0123456789abcdef"
static u64 n10_window_base=0xa00000000ULL,online=255;
static int n10_window_status=1,mode,current_cpu,down_calls,up_calls,flush_calls,sha_calls;
static u8 *buffer;
static void *phys_to_virt(u64 p) {(void)p;return buffer;}
static bool virt_addr_valid(const void *p) {(void)p;return mode!=12;}
static u64 virt_to_phys(const void *p) {return n10_window_base+(const u8 *)p-buffer;}
#define for_each_online_cpu(cpu) for((cpu)=0;(cpu)<8;++(cpu)) if(online&(1ULL<<(cpu)))
static u64 read_word(const u64 *p) {
    u64 value=*(volatile const u64 *)p;
    if(mode==8&&current_cpu==3&&p==(u64 *)buffer+17)value^=1;
    return value;
}
#define READ_ONCE(value) read_word(&(value))
static unsigned int smp_processor_id(void) {return (unsigned int)current_cpu;}
static u64 reg_value(const char *reg) {
    if(!strcmp(reg,"CurrentEL"))return mode==9&&current_cpu==5?8:4;
    if(!strcmp(reg,"cntfrq_el0"))return mode==10&&current_cpu==4?19200000:26000000;
    if(!strcmp(reg,"sctlr_el1"))return mode==14&&current_cpu==2?0x1001:0x1005;
    return 0x100ULL+(unsigned int)current_cpu;
}
#define read_sysreg(reg) reg_value(#reg)
static int disable_nonboot_cpus(void) {
    ++down_calls;online=mode==4?15:(mode==5?3:1);return mode==4?-16:0;
}
static void enable_nonboot_cpus(void) {++up_calls;online=mode==7?1:255;}
static void __flush_dcache_area(void *p,size_t n) {
    (void)n;++flush_calls;if(mode==6)((u8 *)p)[0]^=1;
}
#define dsb(domain) __asm__ volatile("" ::: "memory")
static void cpus_read_lock(void) {if(mode==20)online=15;}
static void cpus_read_unlock(void) {}
static void on_each_cpu(void (*callback)(void *),void *p,int wait) {
    (void)wait;
    for(current_cpu=0;current_cpu<8;++current_cpu) {
        if(mode==11&&current_cpu==6)continue;
        callback(p);if(mode==13&&current_cpu==2)callback(p);
    }
    current_cpu=0;if(mode==15)buffer[0]^=1;
}
static int n10_sha256(const u8 *p,size_t n,u8 out[32]) {
    ++sha_calls;
    if((mode==16&&sha_calls==1)||(mode==17&&sha_calls==2)||(mode==18&&sha_calls==3))return -1;
#ifdef _WIN32
    BCRYPT_ALG_HANDLE provider;BCRYPT_HASH_HANDLE hash=NULL;NTSTATUS result;
    result=BCryptOpenAlgorithmProvider(&provider,BCRYPT_SHA256_ALGORITHM,NULL,0);
    if(result<0)return -1;
    result=BCryptCreateHash(provider,&hash,NULL,0,NULL,0,0);
    if(result>=0)result=BCryptHashData(hash,(PUCHAR)p,(ULONG)n,0);
    if(result>=0)result=BCryptFinishHash(hash,out,32,0);
    if(hash)BCryptDestroyHash(hash);
    BCryptCloseAlgorithmProvider(provider,0);return result<0?-1:0;
#else
    return SHA256(p,n,out)?0:-1;
#endif
}
static int scnprintf(char *p,size_t n,const char *fmt,...) {
    va_list args;va_start(args,fmt);int count=vsnprintf(p,n,fmt,args);va_end(args);
    return count<0?0:((size_t)count>=n?(int)n-1:count);
}
static unsigned int n10_frame_checksum(const char *p,int n) {
    unsigned int value=2166136261U;for(int i=0;i<n;++i)value=(value^(unsigned char)p[i])*16777619U;return value;
}
#define pr_info printf
'''
MAIN=r'''
int main(int argc,char **argv) {
    FILE *file;size_t length=N10_XNU_PAYLOAD_SIZE;
    if(argc!=3)return 61;
    mode=atoi(argv[1]);file=fopen(argv[2],"rb");
    if(!file)return 62;
    buffer=malloc(length);
    if(!buffer)return 63;
    if(fread(buffer,1,length,file)!=length)return 64;
    fclose(file);
    if(mode==1)n10_window_status=-1;
    if(mode==2)online=7;
    if(mode==3)buffer[0]^=1;
    if(mode==19)n10_window_base+=4096;
    n10_test_cpu_cache();
    printf("MODEL down=%d up=%d flush=%d sha=%d\n",down_calls,up_calls,flush_calls,sha_calls);
    free(buffer);return 0;
}
'''


def prefix(digest,length):
    output=''
    for seq in range(2):
        body=(f'id={IDENTITY} seq={seq} base=a00000000 size=10000000 align=2000000 '
              'pages=65536 reserved=65536 invalid=0 shift=12')
        output+='N10RAM2 '+body+f' checksum={checksum(body.encode()):08x}\n'
        body=(f'id={IDENTITY} seq={seq} base=a00000000 size=10000000 bytes={length} '
              f'sha256={digest} status=0')
        output+='N10XNU1 '+body+f' checksum={checksum(body.encode()):08x}\n'
    return output


def test(payload,output):
    if not output.resolve().is_relative_to((ROOT/'note10/private').resolve()) or output.exists():
        raise ValueError('Fresh private model output required')
    raw=payload.read_bytes()
    if not 0<len(raw)<=64*1024*1024 or len(raw)%16384:raise ValueError('Bounded aligned payload required')
    digest=hashlib.sha256(raw).hexdigest()
    output.mkdir(parents=True)
    actual=(HERE/'cpu_cache_roundtrip.c').read_bytes()
    macros='#define N10_XNU_PAYLOAD_SIZE '+str(len(raw))+'ULL\n'
    macros+='#define N10_XNU_PAYLOAD_SHA256_BYTES {'+','.join('0x'+digest[i:i+2] for i in range(0,64,2))+'}\n'
    code=re.sub(r'^#include[^\n]*\n','',actual.decode(),flags=re.M)
    source=output/'model.c';source.write_text(STUB+macros+code+MAIN)
    compiler=(ROOT/'host-tools/windows-build/llvm-mingw/llvm-mingw-20261006-ucrt-x86_64/bin/clang.exe'
              if sys.platform=='win32' else shutil.which('cc'))
    executable=output/('model.exe' if sys.platform=='win32' else 'model')
    result=subprocess.run([str(compiler),'-std=c11','-O2','-Wall','-Wextra','-Werror','-Wno-sign-compare',
        str(source),'-lbcrypt' if sys.platform=='win32' else '-lcrypto','-o',str(executable)],capture_output=True,timeout=60)
    (output/'compile.log').write_bytes(result.stdout+result.stderr)
    if result.returncode:raise RuntimeError('Actual CPU/cache C model compilation failed; see compile.log')
    statuses=[0,1,2,3,4,5,6,7,8,8,8,8,1,8,8,9,3,6,9,1,7]
    early={1,2,3,12,16,19};cases=[]
    base=prefix(digest,len(raw))
    for mode,status in enumerate(statuses):
        result=subprocess.run([str(executable.resolve()),str(mode),str(payload.resolve())],capture_output=True,timeout=60)
        (output/f'mode-{mode}.txt').write_bytes(result.stdout+result.stderr)
        if result.returncode:raise ValueError('CPU/cache model process failed')
        text=result.stdout.decode();rows=re.findall(r'N10QUI1 ([^\r\n]*) checksum=([0-9a-f]{8})',text)
        if len(rows)!=32 or any(checksum(body.encode())!=int(total,16) or
            not body.endswith('status='+str(status)) for body,total in rows):
            raise ValueError('CPU/cache model status/checksum differs')
        counts=re.search(r'MODEL down=(\d+) up=(\d+) flush=(\d+) sha=(\d+)',text)
        if not counts:raise ValueError('Missing modeled CPU API counts')
        down,up,flush,sha=map(int,counts.groups())
        if (down,up)!=((0,0) if mode in early else (1,1)):
            raise ValueError('CPU restoration did not match every freeze attempt')
        if mode in early|{4,5} and flush:raise ValueError('Failed prerequisite touched cache API')
        try:observation=decode(base+text,IDENTITY,digest,len(raw));accepted=True
        except ValueError:observation=None;accepted=False
        if accepted!=(mode==0):raise ValueError('Decoder disposition differs from actual C model')
        if mode==0 and (len(observation['cpus'])!=8 or flush!=1 or sha!=3):
            raise ValueError('Incomplete successful CPU/cache batch')
        cases.append({'mode':mode,'status':status,'freeze_calls':down,'restore_calls':up,
                      'cache_calls':flush,'sha_calls':sha,'accepted':accepted})
    report={'passed':True,'source_sha256':hashlib.sha256(actual).hexdigest(),
        'payload_sha256':digest,'payload_size':len(raw),'cases':cases,
        'hardware_verified':False,'device_operations':[],
        'scope':'Actual diagnostic C and full payload reads; modeled CPU/cache/register APIs and injected faults; real SHA256'}
    (output/'result.json').write_text(json.dumps(report,indent=2))
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--payload',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    result=test(**vars(parser.parse_args()))
    print(json.dumps({'passed':result['passed'],'cases':len(result['cases']),'source_sha256':result['source_sha256']}))
