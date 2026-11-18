/* Host-only302 actor: same WDT owner, then explicit one-way stop_machine commit. */
#include "v299_return_contract.h"
#include "v302_park_contract.h"
#ifndef N299_BUILD_ID
#error Exact producer identity required
#endif
static long call4(long number,long a,long b,long c,long d)
{
    register long x0 __asm__("x0")=a,x1 __asm__("x1")=b,x2 __asm__("x2")=c,x3 __asm__("x3")=d;
    register long x8 __asm__("x8")=number;
    __asm__ volatile("svc #0":"+r"(x0):"r"(x1),"r"(x2),"r"(x3),"r"(x8):"memory","cc");return x0;
}
static unsigned int length(const char *s){unsigned int n=0;while(s[n])++n;return n;}
static void say(const char *s){(void)call4(64,1,(long)s,length(s),0);}
static long read_file(const char *name,char *buf,unsigned int cap)
{
    long fd=call4(56,-100,(long)name,0xA0000,0),n;
    if(fd<0)return fd;
    n=call4(63,fd,(long)buf,cap-1,0);(void)call4(57,fd,0,0,0);
    if(n<0 || n>=(long)cap-1){return -1;}
    buf[n]=0;return n;
}
struct arm64_stat {
    unsigned long dev,ino;unsigned int mode,nlink,uid,gid;unsigned long rdev,pad;
    long size;int blksize,pad2;long blocks,atime,atime_nsec,mtime,mtime_nsec,ctime,ctime_nsec;
    unsigned int unused[2];
};
_Static_assert(sizeof(struct arm64_stat)==128,"AArch64 stat ABI");
struct watchdog_info { unsigned int options,firmware;char identity[32]; };
static int abort_watchdog(long fd)
{
    int disable=1;long result=call4(29,fd,0x80045704,(long)&disable,0);
    if(result<0)(void)call4(64,fd,(long)"V",1,0);
    (void)call4(57,fd,0,0,0);say("N299FAIL watchdog abort; cooperative fallback retained\n");return 2;
}
long n299_main(unsigned long *stack)
{
    char **argv=(char **)(stack+1),buf[512],command[100],boot[33],ack[128];long n,fd,parkfd;int timeout=10;long drain[2]={1,0};
    struct n299_status status;struct arm64_stat st;struct watchdog_info info;
    if(stack[0]!=3 || !n299_hex(argv[1],32) || length(argv[2])!=36)return 2;
    n=read_file("/proc/sys/kernel/random/boot_id",buf,sizeof(buf));
    if(n!=37 || buf[36]!='\n' || !n299_equal(buf,argv[2],36))return 2;
    n=read_file("/sys/kernel/n299_return/status",buf,sizeof(buf));
    if(n<0 || n299_parse_status(buf,(unsigned int)n,N299_BUILD_ID,argv[1],&status) ||
       !status.ready || status.prepared || !n299_budget(1,0,1,status.remaining,0))return 2;
    {unsigned int i;for(i=0;i<33;++i)boot[i]=status.boot[i];}
    if(n299_command(command,N299_BUILD_ID,argv[1],boot)!=99)return 2;
    parkfd=call4(56,-100,(long)"/sys/kernel/n299_return/park",0xA0001,0);
    if(parkfd<0)return 2;
    fd=call4(56,-100,(long)"/sys/kernel/n299_return/prepare",0xA0001,0);
    if(fd<0){return 2;}
    n=call4(64,fd,(long)command,99,0);(void)call4(57,fd,0,0,0);if(n!=99)return 2;
    n=read_file("/sys/kernel/n299_return/status",buf,sizeof(buf));
    if(n<0 || n299_parse_status(buf,(unsigned int)n,N299_BUILD_ID,argv[1],&status) ||
       status.prepared!=1 || status.remaining<40000 || !n299_equal(status.boot,boot,33))return 2;
    n=read_file("/proc/sys/kernel/random/boot_id",buf,sizeof(buf));
    if(n!=37 || !n299_equal(buf,argv[2],36))return 2;
    if(call4(79,-100,(long)"/dev/watchdog",(long)&st,256)<0 ||
       (st.mode&0170000)!=0020000 || st.rdev!=0xA82)return 2;
    fd=call4(56,-100,(long)"/dev/watchdog",0xA0001,0);if(fd<0)return 2;
    if(call4(29,fd,0x80285700,(long)&info,0)<0 ||
       !n299_equal(info.identity,"S3C2410 Watchdog",16) || info.identity[16] || !(info.options&0x100) || !(info.options&0x80))return abort_watchdog(fd);
    if(call4(29,fd,0xC0045706,(long)&timeout,0)<0 || timeout!=10)return abort_watchdog(fd);
    timeout=0;if(call4(29,fd,0x80045707,(long)&timeout,0)<0 || timeout!=10)return abort_watchdog(fd);
    n=read_file("/sys/kernel/n299_return/status",buf,sizeof(buf));
    if(n<0 || n299_parse_status(buf,(unsigned int)n,N299_BUILD_ID,argv[1],&status) ||
       status.prepared!=1 || status.remaining<30000 || !n299_equal(status.boot,boot,33))return abort_watchdog(fd);
    n=n302_ack_line(ack,status.remaining);
    if(n<0 || call4(64,1,(long)ack,n,0)!=n)return abort_watchdog(fd);
    if(call4(64,1,(long)"N302ENTER route=stop_machine cpu=0\n",sizeof("N302ENTER route=stop_machine cpu=0\n")-1,0)!=(long)sizeof("N302ENTER route=stop_machine cpu=0\n")-1)return abort_watchdog(fd);
    /* Bounded best-effort USB drain; host must actually receive both lines. */
    if(call4(101,(long)drain,0,0,0)<0)return abort_watchdog(fd);
    (void)call4(64,parkfd,(long)command,99,0);
    (void)call4(57,parkfd,0,0,0);
    /* Any return is a precommit refusal; successful quiesce never returns. */
    return abort_watchdog(fd);
}
__asm__(".global _start\n_start:\nmov x0, sp\nbl n299_main\nmov x8, #93\nsvc #0\n");
