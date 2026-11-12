/* SPDX-License-Identifier: GPL-2.0-only */
#define _GNU_SOURCE
#include "native_prepare_core.h"
#include <errno.h>
#include <fcntl.h>
#include <linux/if_alg.h>
#include <stdio.h>
#include <string.h>
#include <sys/mount.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <unistd.h>
#ifndef N154_BUILD_ID
#error Source-bound fresh build identity required
#endif
static const char identity[] __attribute__((used))="N10MININIT2:N210PREP";
static int read_exact(const char *path,void *buffer,size_t bytes)
{
    int fd=open(path,O_RDONLY|O_CLOEXEC);size_t done=0;char extra;ssize_t got;
    if(fd<0)return -1;
    while(done<bytes){got=read(fd,(char *)buffer+done,bytes-done);if(got<=0){close(fd);return -1;}done+=(size_t)got;}
    got=read(fd,&extra,1);close(fd);return got==0?0:-1;
}
static int hash_descriptor(const void *data,n209_u8 *out)
{
    struct sockaddr_alg algorithm={.salg_family=AF_ALG,.salg_type="hash",.salg_name="sha256"};
    int fd=socket(AF_ALG,SOCK_SEQPACKET|SOCK_CLOEXEC,0),operation=-1,result=-1;
    if(fd<0)return -1;
    if(bind(fd,(struct sockaddr *)&algorithm,sizeof(algorithm)))goto end;
    operation=accept4(fd,NULL,NULL,SOCK_CLOEXEC);if(operation<0)goto end;
    if(send(operation,data,256,0)==256&&recv(operation,out,32,MSG_WAITALL)==32)result=0;
 end:if(operation>=0)close(operation);close(fd);return result;
}
static int attempt(int argc,char **argv)
{
    struct n210_request request;struct n210_receipt receipt;struct n210_context context={0};
    n209_u8 hash[32];int arm=-1,used=0,fd,result=-1;char build[33],boot[33],cycle[33];ssize_t written;
    if(argc!=2||sscanf(argv[1],"id=%32[0-9a-f] boot=%32[0-9a-f] cycle=%32[0-9a-f] route=builtin arm=%d%n",build,boot,cycle,&arm,&used)!=4||
       argv[1][used]||strlen(build)!=32||strlen(boot)!=32||strlen(cycle)!=32||strcmp(build,N154_BUILD_ID)||arm!=0)return -1;
    memcpy(context.build,build,32);memcpy(context.boot,boot,32);memcpy(context.cycle,cycle,32);
    if((mkdir("/sys",0555)&&errno!=EEXIST)||(mount("sysfs","/sys","sysfs",0,NULL)&&errno!=EBUSY)||
       (mount("devtmpfs","/dev","devtmpfs",0,NULL)&&errno!=EBUSY))return -1;
    if(read_exact("/sys/kernel/note10_native_prepare/destination",&request.destination,96)||
       read_exact("/n10/native-payload.bin",request.payload,256)||read_exact("/n10/binding.bin",&request.binding,128)||
       hash_descriptor(request.payload,hash)||n210_request_valid(&request,&request.destination,&context,hash))return -1;
    fd=open("/sys/kernel/note10_native_prepare/prepare",O_WRONLY|O_CLOEXEC);if(fd<0)return -1;
    written=write(fd,&request,480);close(fd);if(written!=480)return -1;
    if(read_exact("/sys/kernel/note10_native_prepare/result",&receipt,192)||n210_receipt_matches(&receipt,&context,&request))return -1;
    fd=open("/dev/kmsg",O_WRONLY|O_CLOEXEC);
    if(fd>=0){result=dprintf(fd,"<6>N210PID1 id=%s boot=%s cycle=%s metadata_prepared=1 reserved32M=1 native_source=0 mapping_verified=0 qualified_XNU_return=0\n",build,boot,cycle);close(fd);}
    return result>0?0:-1;
}
int main(int argc,char **argv)
{
    int result=attempt(argc,argv);
    if(result)dprintf(1,"N210PID1 stage=prepare-failed native_source=0 transfer=0\n");
    /* Existing kernel recovery workqueue is the sole restart owner. */
    for(;;)pause();
}
