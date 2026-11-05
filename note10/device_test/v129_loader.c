/* SPDX-License-Identifier: GPL-2.0-only */
/* Fresh proof-mode PID1; shipping Image has a disabled execution slot. */
#include <stddef.h>
#ifdef N10_V129_HOST_FIXTURE
#include "v129_fixture_uapi.h"
#else
#include <asm/unistd.h>
#include <linux/kexec.h>
#include <linux/reboot.h>
#endif
#include "legacy_kexec_core.h"
#include "legacy_kexec_build.h" /* Generated from actual fresh park build. */
_Static_assert(KEXEC_ARCH_AARCH64==N10_KEXEC_ARCH,"source UAPI architecture flag");
_Static_assert(sizeof(struct kexec_segment)==sizeof(struct n10_kexec_segment),"source UAPI segment ABI");
_Static_assert(sizeof(((struct kexec_segment *)0)->bufsz)==8,"native Linux64 size_t required");
_Static_assert(offsetof(struct kexec_segment,mem)==offsetof(struct n10_kexec_segment,mem),"source UAPI field offset");
#ifdef N10_V129_HOST_FIXTURE
static volatile char n10_proof_cycle[33]="!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!";
#else
static const volatile char n10_proof_cycle[33]="!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!";
#endif
static n10_u8 park[N10_KEXEC_ALIGN];
typedef __INTPTR_TYPE__ n10_sysword;
extern n10_sysword n10_syscall6(n10_sysword,n10_sysword,n10_sysword,n10_sysword,n10_sysword,n10_sysword,n10_sysword);
static n10_sysword call(n10_sysword nr,n10_sysword a,n10_sysword b,n10_sysword c,n10_sysword d,n10_sysword e,n10_sysword f){return n10_syscall6(nr,a,b,c,d,e,f);}
static n10_sysword open_file(const char *name,int flags){return call(__NR_openat,-100,(n10_sysword)name,flags,0,0,0);}
static void close_file(n10_sysword fd){(void)call(__NR_close,fd,0,0,0,0,0);}
static long arm_write(const struct n10_destination *d)
{
    n10_sysword fd=open_file("/sys/kernel/note10_kexec/arm",1), result;
    if(fd<0)return fd;
    result=call(__NR_write,fd,(n10_sysword)d,sizeof(*d),0,0,0);close_file(fd);
    return result==(n10_sysword)sizeof(*d)?0:(result<0?result:-5);
}
static long arm(void *unused,const struct n10_destination *d){(void)unused;return arm_write(d);}
static void cancel(void *unused,const struct n10_destination *d)
{struct n10_destination copy=*d;(void)unused;copy.status=0;(void)arm_write(&copy);}
static long load(void *unused,n10_u64 entry,n10_u64 count,const struct n10_kexec_segment *segments,n10_u64 flags)
{(void)unused;return call(__NR_kexec_load,entry,count,(n10_sysword)segments,flags,0,0);}
static long reboot_proof(void *unused)
{(void)unused;return call(__NR_reboot,LINUX_REBOOT_MAGIC1,LINUX_REBOOT_MAGIC2,LINUX_REBOOT_CMD_KEXEC,0,0,0);}
static const struct n10_loader_ops ops={arm,load,reboot_proof,cancel};
static void log_text(const char *text,unsigned long size)
{n10_sysword fd=open_file("/dev/kmsg",1);if(fd>=0){(void)call(__NR_write,fd,(n10_sysword)text,size,0,0,0);close_file(fd);}}
static void event(const char *name)
{
    char line[192];unsigned long n=0,i;const char *prefix="<6>N10KEXEC129 id=";
    for(i=0;prefix[i];i++)line[n++]=prefix[i];
    for(i=0;i<32;i++)line[n++]=N10_KEXEC_BUILD_ID[i];
    prefix=" cycle=";for(i=0;prefix[i];i++)line[n++]=prefix[i];
    for(i=0;i<32;i++)line[n++]=n10_proof_cycle[i];
    prefix=" event=";for(i=0;prefix[i];i++)line[n++]=prefix[i];
    for(i=0;name[i] && i<64;i++)line[n++]=name[i];
    line[n++]='\n';log_text(line,n);
}
static void attempt(void)
{
    struct n10_destination d;
    unsigned long i;n10_sysword fd,count,extra;char tail;
    for(i=0;i<32;i++)if(!((n10_proof_cycle[i]>='0' && n10_proof_cycle[i]<='9') ||
                         (n10_proof_cycle[i]>='a' && n10_proof_cycle[i]<='f'))){
        event("execution-disabled");return;
    }
    event("begin");
    if(call(__NR_mount,(n10_sysword)"none",(n10_sysword)"/sys",(n10_sysword)"sysfs",0,0,0)){
        event("mount-failed");return;
    }
    fd=open_file("/sys/kernel/note10_kexec/destination",0);
    if(fd<0){event("destination-open-failed");return;}
    count=call(__NR_read,fd,(n10_sysword)&d,sizeof(d),0,0,0);
    extra=call(__NR_read,fd,(n10_sysword)&tail,1,0,0,0);close_file(fd);
    if(count!=(n10_sysword)sizeof(d) || extra!=0 || n10_destination_valid(&d,N10_KEXEC_BUILD_ID)){
        event("destination-invalid");return;
    }
    if(sizeof(n10_park_bytes)>sizeof(park) || N10_PARK_COOKIE_OFFSET+16>sizeof(n10_park_bytes)){
        event("park-invalid");return;
    }
    for(i=0;i<sizeof(n10_park_bytes);i++)park[i]=n10_park_bytes[i];
    for(i=0;i<16;i++)park[N10_PARK_COOKIE_OFFSET+i]=d.cookie[i];
    event("proof-load-once");
    (void)n10_loader_proof(&d,N10_KEXEC_BUILD_ID,park,sizeof(park),&ops,0);
    event("proof-returned-failure-no-retry");
}
void n10_legacy_init(void)
{
    attempt();
    event("normal-recovery-request");
    (void)call(__NR_reboot,LINUX_REBOOT_MAGIC1,LINUX_REBOOT_MAGIC2,
               LINUX_REBOOT_CMD_RESTART2,(n10_sysword)"recovery",0,0);
    event("normal-recovery-returned-terminal-park");
}
void *memcpy(void *to,const void *from,unsigned long n)
{volatile n10_u8 *d=to;const volatile n10_u8 *s=from;unsigned long i;for(i=0;i<n;i++)d[i]=s[i];return to;}
void *memset(void *to,int value,unsigned long n)
{volatile n10_u8 *d=to;unsigned long i;for(i=0;i<n;i++)d[i]=(n10_u8)value;return to;}
