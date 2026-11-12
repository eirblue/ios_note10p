"""One new freestanding PID1 syscall fixture; all I/O is injected metadata."""
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[2]
HERE=ROOT/'note10/device_test'
HARNESS=r"""
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define N212_HOST_FIXTURE 1
#define N212_BUILD_ID "44444444444444444444444444444444"
#include "PID1_SOURCE"
static unsigned int assertions,calls,prepare_writes,log_writes;
static int protocol_error,mode,live[32];static size_t positions[32];
static struct n210_request expected_request;static struct n210_receipt expected_receipt;
static uint8_t expected_hash[32];
enum { OK,FILE_OPEN,FILE_SHORT,FILE_EXTRA,HASH_SOCKET,HASH_BIND,HASH_ACCEPT,HASH_SEND,HASH_RECV,PREPARE_SHORT,RECEIPT_BOOT };
#define EXPECT(x) do{if(!(x))protocol_error=1;}while(0)
#define CHECK(x) do{++assertions;if(!(x)){fprintf(stderr,"fixture line%d\n",__LINE__);exit(1);}}while(0)
static const char argument[]="id=44444444444444444444444444444444 boot=55555555555555555555555555555555 cycle=66666666666666666666666666666666 route=builtin arm=0";
static int no_live(void){unsigned int i;for(i=0;i<32;i++)if(live[i])return 0;return 1;}
static n212_word opened(int fd){EXPECT(!live[fd]);live[fd]=1;positions[fd]=0;return fd;}
static n212_word n212_syscall(n212_word number,n212_word a0,n212_word a1,n212_word a2,n212_word a3,n212_word a4,n212_word a5)
{
    ++calls;
    if(number==N212_MKDIRAT){EXPECT(a0==-100&&a2==0555&&!a3&&!a4&&!a5&&!strcmp((char *)a1,"/sys"));return -17;}
    if(number==N212_MOUNT){EXPECT(!a3&&!a4&&!a5&&((!strcmp((char *)a0,"sysfs")&&!strcmp((char *)a1,"/sys")&&!strcmp((char *)a2,"sysfs"))||
        (!strcmp((char *)a0,"devtmpfs")&&!strcmp((char *)a1,"/dev")&&!strcmp((char *)a2,"devtmpfs"))));return 0;}
    if(number==N212_OPENAT){
        const char *path=(const char *)a1;int fd=-1,write_only=0;
        EXPECT(a0==-100&&!a3&&!a4&&!a5);
        if(!strcmp(path,"/sys/kernel/note10_native_prepare/destination"))fd=10;
        else if(!strcmp(path,"/n10/native-payload.bin")){if(mode==FILE_OPEN)return -2;fd=11;}
        else if(!strcmp(path,"/n10/binding.bin"))fd=12;
        else if(!strcmp(path,"/sys/kernel/note10_native_prepare/prepare")){fd=15;write_only=1;}
        else if(!strcmp(path,"/sys/kernel/note10_native_prepare/result"))fd=16;
        else if(!strcmp(path,"/dev/kmsg")){fd=17;write_only=1;}
        EXPECT(fd>=0&&a2==(N212_CLOEXEC|write_only));if(fd<0)return -2;return opened(fd);
    }
    if(number==N212_READ){
        const uint8_t *data=NULL;size_t bytes=0,amount;int fd=(int)a0;
        EXPECT(fd>=0&&fd<32&&live[fd]&&a2>0&&a2<=480&&!a3&&!a4&&!a5);
        if(fd==10){data=(const uint8_t *)&expected_request.destination;bytes=96;}
        else if(fd==11){data=expected_request.payload;bytes=256+(mode==FILE_EXTRA);}
        else if(fd==12){data=(const uint8_t *)&expected_request.binding;bytes=128;}
        else if(fd==16){data=(const uint8_t *)&expected_receipt;bytes=192;}
        else {protocol_error=1;return -9;}
        if(fd==11&&mode==FILE_SHORT){if(positions[fd]>=255)return 0;bytes=255;}
        if(positions[fd]>=bytes)return 0;
        amount=bytes-positions[fd];if(amount>(size_t)a2)amount=(size_t)a2;
        if(fd==11&&positions[fd]==256){*(uint8_t *)a1=0xaa;amount=1;}
        else memcpy((void *)a1,data+positions[fd],amount);
        positions[fd]+=amount;return (n212_word)amount;
    }
    if(number==N212_SOCKET){EXPECT(a0==38&&a1==(5|N212_CLOEXEC)&&!a2&&!a3&&!a4&&!a5);return mode==HASH_SOCKET?-12:opened(13);}
    if(number==N212_BIND){const struct n212_sockaddr_alg *alg=(const void *)a1;
        EXPECT(a0==13&&live[13]&&a2==88&&!a3&&!a4&&!a5&&alg->family==38&&!strcmp((const char *)alg->type,"hash")&&
               !strcmp((const char *)alg->name,"sha256")&&!alg->feat&&!alg->mask);return mode==HASH_BIND?-22:0;}
    if(number==N212_ACCEPT4){EXPECT(a0==13&&live[13]&&!a1&&!a2&&a3==N212_CLOEXEC&&!a4&&!a5);return mode==HASH_ACCEPT?-23:opened(14);}
    if(number==N212_SENDTO){EXPECT(a0==14&&live[14]&&a2==256&&!a3&&!a4&&!a5&&!memcmp((const void *)a1,expected_request.payload,256));return mode==HASH_SEND?255:256;}
    if(number==N212_RECVFROM){size_t count=mode==HASH_RECV?31:32;
        EXPECT(a0==14&&live[14]&&a2==32&&a3==0x100&&!a4&&!a5);memcpy((void *)a1,expected_hash,count);return (n212_word)count;}
    if(number==N212_WRITE){
        EXPECT(!a3&&!a4&&!a5&&a0>=0&&a0<32&&live[a0]);
        if(a0==15){++prepare_writes;EXPECT(prepare_writes==1&&a2==480&&!memcmp((const void *)a1,&expected_request,480));return mode==PREPARE_SHORT?479:480;}
        if(a0==17){
            static const char frame[]="<6>N212PID1 id=44444444444444444444444444444444 boot=55555555555555555555555555555555 cycle=66666666666666666666666666666666 metadata_prepared=1 reserved32M=1 native_source=0 mapping_verified=0 qualified_XNU_return=0\n";
            ++log_writes;EXPECT(log_writes==1&&a2==(n212_word)sizeof(frame)-1&&!memcmp((const void *)a1,frame,sizeof(frame)-1));return a2;
        }
        protocol_error=1;return -9;
    }
    if(number==N212_CLOSE){EXPECT(a0>=0&&a0<32&&live[a0]&&!a1&&!a2&&!a3&&!a4&&!a5);if(a0>=0&&a0<32)live[a0]=0;return 0;}
    protocol_error=1;return -38;
}
static void reset(int selected)
{
    struct n209_payload payload={0};
    mode=selected;calls=prepare_writes=log_writes=0;protocol_error=0;memset(live,0,sizeof(live));memset(positions,0,sizeof(positions));
    memset(&expected_request,0,sizeof(expected_request));memset(&expected_receipt,0,sizeof(expected_receipt));memset(expected_hash,7,32);
    memcpy(payload.magic,"N209PAY1",8);payload.schema=1;payload.bytes=256;payload.virtual_base=0xffff000001004000ULL;
    payload.kernel_span=3*N209_PAGE;payload.entry_extent_bytes=16;payload.pool_offset=2*N209_PAGE;payload.pool_bytes=N209_PAGE;
    payload.adapter_bytes=N209_PAGE;payload.adapter_record_offset=256;memset((uint8_t *)&payload+96,1,160);
    memcpy(expected_request.payload,&payload,256);memcpy(expected_request.destination.magic,"N210DST1",8);
    expected_request.destination.schema=1;expected_request.destination.bytes=96;
    expected_request.destination.region.base=N209_ADDRESS_MIN+N210_RESIDUE;expected_request.destination.region.size=N209_DESTINATION_BYTES;
    expected_request.destination.region.generation=1;expected_request.destination.region.page_shift=12;expected_request.destination.region.status=1;
    memset(expected_request.destination.region.build,'4',32);memset(expected_request.destination.region.cookie,1,16);
    memcpy(expected_request.binding.magic,"N210BND1",8);expected_request.binding.schema=1;expected_request.binding.bytes=128;
    memset(expected_request.binding.build,'4',32);memset(expected_request.binding.cycle,'6',32);memcpy(expected_request.binding.descriptor_sha256,expected_hash,32);
    memcpy(expected_receipt.magic,"N210RCP1",8);expected_receipt.schema=1;expected_receipt.bytes=192;expected_receipt.status=1;
    expected_receipt.generation=1;expected_receipt.flags=3;memset(expected_receipt.build,'4',32);memset(expected_receipt.boot,'5',32);
    memset(expected_receipt.cycle,'6',32);memset(expected_receipt.cookie,1,16);memcpy(expected_receipt.descriptor_sha256,expected_hash,32);
    if(mode==RECEIPT_BOOT)expected_receipt.boot[0]='7';
}
static void attempt_case(int selected,n212_word argc,const char *args,int success,unsigned int writes,int no_calls)
{
    int result;reset(selected);result=n212_attempt(argc,args);
    CHECK(success?result==0:result!=0);
    CHECK(prepare_writes==writes&&log_writes==(unsigned int)success&&no_live()&&(!no_calls||calls==0));
    CHECK(!protocol_error);
}
int main(void)
{
    char wrong[sizeof(argument)],trailing[sizeof(argument)+2],tiny[6];int selected;
    attempt_case(OK,2,argument,1,1,0);
    attempt_case(OK,1,argument,0,0,1);
    memcpy(wrong,argument,sizeof(argument));wrong[3]='7';attempt_case(OK,2,wrong,0,0,1);
    attempt_case(OK,2,"id=44444444444444444444444444444444 boot=5",0,0,1);
    memcpy(trailing,argument,sizeof(argument)-1);memcpy(trailing+sizeof(argument)-1," x",3);attempt_case(OK,2,trailing,0,0,1);
    for(selected=FILE_OPEN;selected<=FILE_EXTRA;selected++)attempt_case(selected,2,argument,0,0,0);
    for(selected=HASH_SOCKET;selected<=HASH_RECV;selected++)attempt_case(selected,2,argument,0,0,0);
    attempt_case(PREPARE_SHORT,2,argument,0,1,0);attempt_case(RECEIPT_BOOT,2,argument,0,1,0);
    reset(OK);memset(tiny,'x',sizeof(tiny));CHECK(n212_append(tiny+1,tiny+5,"12345",5)==NULL);
    CHECK(tiny[0]=='x'&&tiny[1]=='x'&&tiny[5]=='x');CHECK(calls==0&&prepare_writes==0&&log_writes==0);
    printf("{\"groups\":5,\"variants\":16,\"assertions\":%u,\"real_IO\":0,\"old_tests\":0}\n",assertions);
    return 0;
}
"""


def compile_argv(out,compiler):
    return [str(compiler),'-std=c11','-O2','-fno-builtin','-Wall','-Wextra','-Werror','-I',str(HERE),
            str(out/'fixture.c'),str(HERE/'native_prepare_core.c'),str(HERE/'native_parcel_core.c'),'-o',str(out/'pid1-fixture.exe')]


def run(out,compiler,environment):
    source=HARNESS.replace('PID1_SOURCE',(HERE/'v212_native_prepare_pid1.c').as_posix())
    with (out/'fixture.c').open('x',encoding='utf8',newline='\n') as stream:stream.write(source)
    with (out/'COMPILE-STARTED.json').open('x',encoding='utf8') as stream:json.dump(dict(attempt=1,argv=compile_argv(out,compiler)),stream)
    with (out/'compile.log').open('xb') as log:
        completed=subprocess.run(compile_argv(out,compiler),cwd=ROOT,env=environment,stdout=log,stderr=subprocess.STDOUT,timeout=120)
    if completed.returncode or (out/'compile.log').stat().st_size>16777216:raise ValueError('new PID1 fixture compile failed or log cap')
    executable=out/'pid1-fixture.exe'
    if not 0<executable.stat().st_size<=1048576:raise ValueError('new host fixture executable cap')
    with (out/'FIXTURE-STARTED.json').open('x',encoding='utf8') as stream:json.dump(dict(attempt=1,argv=[str(executable)]),stream)
    with (out/'fixture.log').open('xb') as log:
        completed=subprocess.run([str(executable)],cwd=ROOT,env=environment,stdout=log,stderr=subprocess.STDOUT,timeout=30)
    if completed.returncode or not 0<(out/'fixture.log').stat().st_size<=1048576:raise ValueError('new PID1 fixture failed or log cap')
    return json.loads((out/'fixture.log').read_bytes())
