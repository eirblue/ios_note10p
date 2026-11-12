/* SPDX-License-Identifier: GPL-2.0-only */
/* Freestanding descriptor preparation only; kernel recovery remains the owner. */
#include <stddef.h>
#include <stdint.h>
#include "native_prepare_core.h"
#ifndef N212_BUILD_ID
#error Exact compiled build identity required
#endif
_Static_assert(sizeof(N212_BUILD_ID)==33,"build32");
typedef intptr_t n212_word;
_Static_assert(sizeof(n212_word)==8,"native64 syscall ABI");
enum { N212_MKDIRAT=34,N212_MOUNT=40,N212_OPENAT=56,N212_CLOSE=57,N212_READ=63,N212_WRITE=64,
       N212_PPOLL=73,N212_SOCKET=198,N212_BIND=200,N212_SENDTO=206,N212_RECVFROM=207,N212_ACCEPT4=242,
       N212_AT_FDCWD=-100,N212_CLOEXEC=02000000,N212_FRAME_BYTES=512 };
struct n212_sockaddr_alg { uint16_t family;uint8_t type[14];uint32_t feat,mask;uint8_t name[64]; };
_Static_assert(sizeof(struct n212_sockaddr_alg)==88,"AF_ALG address88");
_Static_assert(offsetof(struct n212_sockaddr_alg,name)==24,"AF_ALG name24");
#ifdef N212_HOST_FIXTURE
static n212_word n212_syscall(n212_word,n212_word,n212_word,n212_word,n212_word,n212_word,n212_word);
#else
#if !defined(__aarch64__) || !defined(__linux__)
#error Native PID1 requires Linux AArch64
#endif
static n212_word n212_syscall(n212_word number,n212_word a0,n212_word a1,n212_word a2,n212_word a3,n212_word a4,n212_word a5)
{
    register n212_word x0 __asm__("x0")=a0;register n212_word x1 __asm__("x1")=a1;
    register n212_word x2 __asm__("x2")=a2;register n212_word x3 __asm__("x3")=a3;
    register n212_word x4 __asm__("x4")=a4;register n212_word x5 __asm__("x5")=a5;
    register n212_word x8 __asm__("x8")=number;
    __asm__ volatile("svc 0":"+r"(x0):"r"(x1),"r"(x2),"r"(x3),"r"(x4),"r"(x5),"r"(x8):"memory","cc");
    return x0;
}
#endif
static const char n212_identity[] __attribute__((used))="N10MININIT2:N212PREP";
static void n212_copy(void *out,const void *in,size_t count)
{ uint8_t *to=out;const uint8_t *from=in;size_t i;for(i=0;i<count;i++)to[i]=from[i]; }
static void n212_zero(void *out,size_t count)
{ uint8_t *to=out;size_t i;for(i=0;i<count;i++)to[i]=0; }
#ifndef N212_HOST_FIXTURE
void *memcpy(void *out,const void *in,size_t count){n212_copy(out,in,count);return out;}
void *memset(void *out,int value,size_t count)
{ uint8_t *to=out;size_t i;for(i=0;i<count;i++)to[i]=(uint8_t)value;return out; }
#endif
static const char *n212_tag(const char *value,const char *tag)
{ if(!value)return 0;while(*tag)if(*value++!=*tag++)return 0;return value; }
static const char *n212_id(const char *value,const char *expected,uint8_t *out)
{
    unsigned int i,nonzero=0;if(!value)return 0;
    for(i=0;i<32;i++){
        char c=value[i];
        if(!c||!((c>='0'&&c<='9')||(c>='a'&&c<='f'))||(expected&&c!=expected[i]))return 0;
        nonzero|=c!='0';out[i]=(uint8_t)c;
    }
    return nonzero?value+32:0;
}
static int n212_parse(n212_word argc,const char *argument,struct n210_context *context)
{
    const char *next;if(argc!=2)return -1;
    next=n212_id(n212_tag(argument,"id="),N212_BUILD_ID,context->build);
    next=n212_id(n212_tag(next," boot="),0,context->boot);
    next=n212_id(n212_tag(next," cycle="),0,context->cycle);
    next=n212_tag(next," route=builtin arm=0");return next&&!*next?0:-1;
}
static int n212_close(n212_word fd)
{ return n212_syscall(N212_CLOSE,fd,0,0,0,0,0)==0?0:-1; }
static int n212_read_exact(const char *path,void *out,size_t bytes)
{
    n212_word fd=n212_syscall(N212_OPENAT,N212_AT_FDCWD,(n212_word)path,N212_CLOEXEC,0,0,0),got;
    size_t done=0;uint8_t tail;int error=0;if(fd<0)return -1;
    while(done<bytes){
        got=n212_syscall(N212_READ,fd,(n212_word)((uint8_t *)out+done),(n212_word)(bytes-done),0,0,0);
        if(got<=0||(uint64_t)got>bytes-done){error=-1;break;}done+=(size_t)got;
    }
    if(!error&&n212_syscall(N212_READ,fd,(n212_word)&tail,1,0,0,0)!=0)error=-1;
    if(n212_close(fd))error=-1;
    return error;
}
static int n212_hash(const uint8_t *data,uint8_t *out)
{
    struct n212_sockaddr_alg address;n212_word fd,operation=-1;int error=-1;
    n212_zero(&address,sizeof(address));address.family=38;n212_copy(address.type,"hash",5);n212_copy(address.name,"sha256",7);
    fd=n212_syscall(N212_SOCKET,38,5|N212_CLOEXEC,0,0,0,0);if(fd<0)return -1;
    if(n212_syscall(N212_BIND,fd,(n212_word)&address,sizeof(address),0,0,0)!=0)goto end;
    operation=n212_syscall(N212_ACCEPT4,fd,0,0,N212_CLOEXEC,0,0);if(operation<0)goto end;
    if(n212_syscall(N212_SENDTO,operation,(n212_word)data,256,0,0,0)!=256)goto end;
    if(n212_syscall(N212_RECVFROM,operation,(n212_word)out,32,0x100,0,0)!=32)goto end;
    error=0;
 end:
    if(operation>=0&&n212_close(operation))error=-1;
    if(n212_close(fd))error=-1;
    return error;
}
static char *n212_append(char *at,char *limit,const void *text,size_t bytes)
{
    if(!at||at>limit||bytes>(size_t)(limit-at))return 0;
    n212_copy(at,text,bytes);return at+bytes;
}
static int n212_emit(const struct n210_context *context)
{
    static const char begin[]="<6>N212PID1 id=",boot[]=" boot=",cycle[]=" cycle=";
    static const char end[]=" metadata_prepared=1 reserved32M=1 native_source=0 mapping_verified=0 qualified_XNU_return=0\n";
    char frame[N212_FRAME_BYTES],*at=frame,*limit=frame+sizeof(frame);n212_word fd,written;int error=0;
    at=n212_append(at,limit,begin,sizeof(begin)-1);at=n212_append(at,limit,context->build,32);
    at=n212_append(at,limit,boot,sizeof(boot)-1);at=n212_append(at,limit,context->boot,32);
    at=n212_append(at,limit,cycle,sizeof(cycle)-1);at=n212_append(at,limit,context->cycle,32);
    at=n212_append(at,limit,end,sizeof(end)-1);if(!at)return -1;
    fd=n212_syscall(N212_OPENAT,N212_AT_FDCWD,(n212_word)"/dev/kmsg",1|N212_CLOEXEC,0,0,0);if(fd<0)return -1;
    written=n212_syscall(N212_WRITE,fd,(n212_word)frame,at-frame,0,0,0);if(written!=at-frame)error=-1;
    if(n212_close(fd))error=-1;
    return error;
}
static int n212_attempt(n212_word argc,const char *argument)
{
    struct n210_context context;struct n210_request request;struct n210_receipt receipt;
    uint8_t hash[32];n212_word result,fd,written;int error=0;
    n212_zero(&context,sizeof(context));if(n212_parse(argc,argument,&context))return -1;
    result=n212_syscall(N212_MKDIRAT,N212_AT_FDCWD,(n212_word)"/sys",0555,0,0,0);if(result!=0&&result!=-17)return -1;
    result=n212_syscall(N212_MOUNT,(n212_word)"sysfs",(n212_word)"/sys",(n212_word)"sysfs",0,0,0);if(result!=0&&result!=-16)return -1;
    result=n212_syscall(N212_MOUNT,(n212_word)"devtmpfs",(n212_word)"/dev",(n212_word)"devtmpfs",0,0,0);if(result!=0&&result!=-16)return -1;
    if(n212_read_exact("/sys/kernel/note10_native_prepare/destination",&request.destination,96)||
       n212_read_exact("/n10/native-payload.bin",request.payload,256)||n212_read_exact("/n10/binding.bin",&request.binding,128)||
       n212_hash(request.payload,hash)||n210_request_valid(&request,&request.destination,&context,hash))return -1;
    fd=n212_syscall(N212_OPENAT,N212_AT_FDCWD,(n212_word)"/sys/kernel/note10_native_prepare/prepare",1|N212_CLOEXEC,0,0,0);if(fd<0)return -1;
    written=n212_syscall(N212_WRITE,fd,(n212_word)&request,480,0,0,0);if(written!=480)error=-1;
    if(n212_close(fd))error=-1;
    if(error)return -1;
    if(n212_read_exact("/sys/kernel/note10_native_prepare/result",&receipt,192)||n210_receipt_matches(&receipt,&context,&request))return -1;
    return n212_emit(&context);
}
#ifndef N212_HOST_FIXTURE
__attribute__((used,noreturn)) static void n212_start(const n212_word *stack)
{
    (void)n212_attempt(stack[0],stack[0]==2?(const char *)stack[2]:0);
    for(;;)(void)n212_syscall(N212_PPOLL,0,0,0,0,0,0);
}
__asm__(".text\n.global _start\n.type _start,%function\n_start:\nmov x0, sp\nb n212_start\n.size _start, .-_start\n");
#endif
