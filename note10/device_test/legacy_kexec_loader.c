/* SPDX-License-Identifier: GPL-2.0-only */
/* Fresh proof-mode PID1; shipping Image has a disabled execution slot. */
#include <asm/unistd.h>
#include <stddef.h>
#include <linux/kexec.h>
#include <linux/reboot.h>
#include "legacy_kexec_core.h"
#include "legacy_kexec_build.h" /* Generated from actual fresh park build. */
_Static_assert(KEXEC_ARCH_AARCH64==N10_KEXEC_ARCH,"source UAPI architecture flag");
_Static_assert(sizeof(struct kexec_segment)==sizeof(struct n10_kexec_segment),"source UAPI segment ABI");
_Static_assert(sizeof(((struct kexec_segment *)0)->bufsz)==8,"native Linux64 size_t required");
_Static_assert(offsetof(struct kexec_segment,mem)==offsetof(struct n10_kexec_segment,mem),"source UAPI field offset");
static volatile char n10_proof_cycle[33]="!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!";
static n10_u8 park[N10_KEXEC_ALIGN];
extern long n10_syscall6(long,long,long,long,long,long,long);
static long call(long nr,long a,long b,long c,long d,long e,long f){return n10_syscall6(nr,a,b,c,d,e,f);}
static long open_file(const char *name,int flags){return call(__NR_openat,-100,(long)name,flags,0,0,0);}
static void close_file(long fd){(void)call(__NR_close,fd,0,0,0,0,0);}
static long arm_write(const struct n10_destination *d)
{
    long fd=open_file("/sys/kernel/note10_kexec/arm",1), result;
    if(fd<0)return fd;
    result=call(__NR_write,fd,(long)d,sizeof(*d),0,0,0);close_file(fd);
    return result==(long)sizeof(*d)?0:(result<0?result:-5);
}
static long arm(void *unused,const struct n10_destination *d){(void)unused;return arm_write(d);}
static void cancel(void *unused,const struct n10_destination *d)
{struct n10_destination copy=*d;(void)unused;copy.status=0;(void)arm_write(&copy);}
static long load(void *unused,n10_u64 entry,n10_u64 count,const struct n10_kexec_segment *segments,n10_u64 flags)
{(void)unused;return call(__NR_kexec_load,entry,count,(long)segments,flags,0,0);}
static long reboot_proof(void *unused)
{(void)unused;return call(__NR_reboot,LINUX_REBOOT_MAGIC1,LINUX_REBOOT_MAGIC2,LINUX_REBOOT_CMD_KEXEC,0,0,0);}
static const struct n10_loader_ops ops={arm,load,reboot_proof,cancel};
static void log_text(const char *text,unsigned long size)
{long fd=open_file("/dev/kmsg",1);if(fd>=0){(void)call(__NR_write,fd,(long)text,size,0,0,0);close_file(fd);}}
#define LOG(text) log_text(text,sizeof(text)-1)
void n10_legacy_init(void)
{
    struct n10_destination d;
    unsigned long i;long fd,count,extra;char tail;
    for(i=0;i<32;i++)if(!((n10_proof_cycle[i]>='0' && n10_proof_cycle[i]<='9') ||
                         (n10_proof_cycle[i]>='a' && n10_proof_cycle[i]<='f'))){
        LOG("<6>N10KEXEC execution-disabled xnu=0\n");return;
    }
    if(call(__NR_mount,(long)"none",(long)"/sys",(long)"sysfs",0,0,0))return;
    fd=open_file("/sys/kernel/note10_kexec/destination",0);if(fd<0)return;
    count=call(__NR_read,fd,(long)&d,sizeof(d),0,0,0);
    extra=call(__NR_read,fd,(long)&tail,1,0,0,0);close_file(fd);
    if(count!=(long)sizeof(d) || extra!=0 || n10_destination_valid(&d,N10_KEXEC_BUILD_ID))return;
    if(sizeof(n10_park_bytes)>sizeof(park) || N10_PARK_COOKIE_OFFSET+16>sizeof(n10_park_bytes))return;
    for(i=0;i<sizeof(n10_park_bytes);i++)park[i]=n10_park_bytes[i];
    for(i=0;i<16;i++)park[N10_PARK_COOKIE_OFFSET+i]=d.cookie[i];
    LOG("<6>N10KEXEC proof-load-once xnu=0\n");
    (void)n10_loader_proof(&d,N10_KEXEC_BUILD_ID,park,sizeof(park),&ops,0);
    LOG("<3>N10KEXEC proof-returned failure no-retry\n");
}
void *memcpy(void *to,const void *from,unsigned long n)
{volatile n10_u8 *d=to;const volatile n10_u8 *s=from;unsigned long i;for(i=0;i<n;i++)d[i]=s[i];return to;}
void *memset(void *to,int value,unsigned long n)
{volatile n10_u8 *d=to;unsigned long i;for(i=0;i<n;i++)d[i]=(n10_u8)value;return to;}
