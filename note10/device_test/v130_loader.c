/* SPDX-License-Identifier: GPL-2.0-only */
/* Static native Linux PID1. Private files arrive only through the local slot. */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <linux/if_alg.h>
#include <linux/kexec.h>
#include <linux/reboot.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#include <sys/mount.h>
#include <sys/socket.h>
#include <sys/syscall.h>
#include <time.h>
#include <unistd.h>
#include "v130_handoff_core.h"
#include "v130_build_id.h"
_Static_assert(sizeof(struct kexec_segment)==sizeof(struct n130_segment),"native kexec ABI");
_Static_assert(offsetof(struct kexec_segment,mem)==offsetof(struct n130_segment,mem),"native segment offset");
static const volatile char n130_cycle[33]="!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!";
static unsigned char parcel[N130_MEMORY];
static struct timespec started;

static void event(const char *stage)
{
    int fd=open("/dev/kmsg",O_WRONLY|O_CLOEXEC);char text[192];int n;
    n=snprintf(text,sizeof(text),"<6>N10XNU130 id=%s cycle=%.32s stage=%s\n",N130_BUILD_ID,(const char *)n130_cycle,stage);
    if(fd>=0){if(n>0 && n<(int)sizeof(text))(void)write(fd,text,(size_t)n);close(fd);}
}
static int deadline(void)
{
    struct timespec now;
    return clock_gettime(CLOCK_MONOTONIC,&now) || now.tv_sec-started.tv_sec>=60;
}
static int file(void *out,size_t bytes,const char *path,unsigned char *digest)
{
    struct sockaddr_alg algorithm={.salg_family=AF_ALG,.salg_type="hash",.salg_name="sha256"};
    int fd=-1,hash=-1,operation=-1,error=-1;size_t done=0;char tail;
    if(deadline())return -ETIMEDOUT;
    fd=open(path,O_RDONLY|O_CLOEXEC);if(fd<0)goto end;
    if(digest){
        hash=socket(AF_ALG,SOCK_SEQPACKET|SOCK_CLOEXEC,0);
        if(hash<0 || bind(hash,(const struct sockaddr *)&algorithm,sizeof(algorithm)))goto end;
        operation=accept4(hash,NULL,NULL,SOCK_CLOEXEC);if(operation<0)goto end;
    }
    while(done<bytes){
        size_t amount=bytes-done;if(amount>65536)amount=65536;
        ssize_t got=read(fd,(unsigned char *)out+done,amount);
        if(got<=0 || deadline())goto end;
        if(digest && send(operation,(unsigned char *)out+done,(size_t)got,done+(size_t)got<bytes?MSG_MORE:0)!=got)goto end;
        done+=(size_t)got;
    }
    if(read(fd,&tail,1)!=0)goto end;
    if(digest && recv(operation,digest,32,MSG_WAITALL)!=32)goto end;
    error=0;
end:
    if(operation>=0)close(operation);
    if(hash>=0)close(hash);
    if(fd>=0)close(fd);
    return error;
}
static long arm(void *unused,const struct n130_wire *w)
{
    int fd;ssize_t n;(void)unused;
    fd=open("/sys/kernel/note10_xnu/arm",O_WRONLY|O_CLOEXEC);if(fd<0)return -errno;
    n=write(fd,w,sizeof(*w));close(fd);return n==(ssize_t)sizeof(*w)?0:-EIO;
}
static void cancel(void *unused,const struct n130_wire *w)
{struct n130_wire copy=*w;copy.status=0;(void)arm(unused,&copy);}
static long load(void *unused,n130_u64 entry,const struct n130_segment *segment,n130_u64 flags)
{
    long result;(void)unused;if(deadline())return -ETIMEDOUT;
    event("kexec-load-once");result=syscall(SYS_kexec_load,entry,1,segment,flags);
    return result<0?-errno:result;
}
static long transfer(void *unused)
{
    long result;(void)unused;if(deadline())return -ETIMEDOUT;
    event("kexec-reboot-once");result=syscall(SYS_reboot,LINUX_REBOOT_MAGIC1,LINUX_REBOOT_MAGIC2,LINUX_REBOOT_CMD_KEXEC,0);
    return result<0?-errno:result;
}
static const struct n130_loader_ops ops={arm,load,transfer,cancel};
static int attempt(void)
{
    struct n130_wire w;struct n130_payload payload;struct n130_activation activation;
    struct n130_platform expected,actual;unsigned char hashed[32],activation_hash[32];
    unsigned long i;unsigned char *record;uint64_t pair[2];
    if(clock_gettime(CLOCK_MONOTONIC,&started))return -1;
    for(i=0;i<32;i++)if(!((n130_cycle[i]>='0' && n130_cycle[i]<='9') || (n130_cycle[i]>='a' && n130_cycle[i]<='f')))return -1;
    event("begin");
    if(mount("none","/sys","sysfs",0,NULL))return -1;
    if(file(&w,sizeof(w),"/sys/kernel/note10_xnu/destination",NULL) || n130_descriptor(&w,N130_BUILD_ID))return -1;
    if(file(&payload,sizeof(payload),"/n10/payload.contract",NULL) || n130_payload_valid(&payload))return -1;
    if(file(&activation,sizeof(activation),"/n10/activation.contract",activation_hash) ||
       memcmp(activation.magic,"N10ACTV1",8) || activation.schema!=1 || activation.bytes!=128 || activation.reserved ||
       n130_layout(&w,activation.adt_bytes))return -1;
    if(file(&expected,sizeof(expected),"/n10/platform.contract",hashed) || memcmp(hashed,activation.platform_sha256,32))return -1;
    if(file(&actual,sizeof(actual),"/sys/kernel/note10_xnu/platform",NULL) || memcmp(&actual,&expected,sizeof(actual)))return -1;
    if(memcmp(actual.magic,"N10PLAT1",8) || actual.schema!=1 || actual.bytes!=128 || actual.status!=1)return -1;
    if(file(parcel,N130_SPAN,"/n10/kernel.mem",hashed) || memcmp(hashed,payload.kernel_sha256,32))return -1;
    memcpy(w.kernel_sha256,hashed,32);memcpy(w.activation_sha256,activation_hash,32);
    if(file(parcel+w.adt_offset,(size_t)w.adt_length,"/n10/platform.adt",hashed) || memcmp(hashed,activation.adt_sha256,32))return -1;
    if(n130_adt_owned_dram(parcel+w.adt_offset,(unsigned long)w.adt_length,&w) ||
       n130_boot_args(parcel+w.args_offset,N130_PAGE,&w))return -1;
    if(file(parcel+w.adapter_offset,N130_PAGE,"/n10/adapter.raw",hashed) || memcmp(hashed,payload.adapter_sha256,32))return -1;
    record=parcel+w.adapter_offset+payload.adapter_record;
    if(memcmp(record,"N10XFER1",8) || memcmp(record+8,"\1\0\0\0\100\0\0\0",8))return -1;
    for(i=16;i<64;i++)if(record[i])return -1;
    pair[0]=w.base+w.args_offset;pair[1]=w.base+N130_ENTRY;memcpy(record+16,pair,sizeof(pair));
    if(n130_parcel(&w,N130_BUILD_ID) || deadline())return -1;
    event("full-owned-parcel-ready");
    (void)n130_load_once(&w,N130_BUILD_ID,parcel,&ops,NULL);
    return -1;
}
int main(void)
{
    (void)attempt();event("normal-recovery-request");
    (void)syscall(SYS_reboot,LINUX_REBOOT_MAGIC1,LINUX_REBOOT_MAGIC2,LINUX_REBOOT_CMD_RESTART2,"recovery");
    event("recovery-returned-terminal-no-retry");for(;;)pause();
}
