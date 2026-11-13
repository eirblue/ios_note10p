/* SPDX-License-Identifier: GPL-2.0-only */
#include "v233_cpu_node_consistency.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
struct n233_fixture_node {unsigned int kind;};
static struct n233_fixture_node node={1},parent={2};
static struct {n209_u64 before;struct n233_cpu_node_consistency value;n209_u64 after;} output;
static struct n233_cpu_node_consistency saved[3];
static struct n231_cpu_observation sample;
static n209_u64 logical,reg_value;static unsigned char address[4],size_value[4],reg[8];
static unsigned int scenario,cells,refs,node_refs,parent_refs,node_get_count,node_put_count,calls,bad_read,bad_publication,bad_index,variants,assertions;
static int reg_length,address_length,size_length;
#define CHECK(x) do {assertions++;if(!(x)){fprintf(stderr,"node assertion %u at %d\n",assertions,__LINE__);exit(1);}}while(0)
static void event(void){calls++;if(output.value.status)bad_publication=1;}
static void be(unsigned char *p,n209_u64 value,unsigned int bytes)
{ unsigned int i;for(i=0;i<bytes;i++)p[bytes-i-1]=(unsigned char)(value>>(8*i)); }
n209_u64 n233_fixture_logical_map(unsigned int cpu)
{event();if(cpu!=sample.linux_cpu)bad_index=1;return logical;}
struct n233_fixture_node *n233_fixture_get_cpu_node(unsigned int cpu,unsigned int *thread)
{event();if(cpu!=sample.linux_cpu)bad_index=1;*thread=scenario==12?1:0;if(scenario==11)return NULL;refs++;node_refs++;node_get_count++;return &node;}
struct n233_fixture_node *n233_fixture_get_parent(struct n233_fixture_node *n)
{event();if(n!=&node)abort();if(scenario==13)return NULL;refs++;parent_refs++;node_get_count++;return &parent;}
const char *n233_fixture_full_name(struct n233_fixture_node *n)
{event();if(n!=&parent)abort();return scenario==14?"/other":"/cpus";}
const void *n233_fixture_property(struct n233_fixture_node *n,const char *key,int *length)
{
    event();
    if(!strcmp(key,"#address-cells")){if(n!=&parent)abort();*length=address_length;return scenario==15?NULL:address;}
    if(!strcmp(key,"#size-cells")){if(n!=&parent)abort();*length=size_length;return scenario==19?NULL:size_value;}
    if(!strcmp(key,"reg")){if(n!=&node)abort();*length=reg_length;return scenario==22?NULL:reg;}
    abort();
}
n209_u64 n233_fixture_read_number(const void *p,unsigned int count)
{
    const unsigned char *raw=p;n209_u64 value=0;unsigned int i;event();
    if((p==address&&(address_length!=4||count!=1))||(p==size_value&&(size_length!=4||count!=1))||
       (p==reg&&(reg_length!=(int)(4*cells)||count!=cells||count<1||count>2)))bad_read=1;
    if(count>2)abort();
    for(i=0;i<4*count;i++)value=(value<<8)|raw[i];
    return value;
}
void n233_fixture_put(struct n233_fixture_node *n)
{
    event();if(!refs)abort();
    if(n==&node){if(!node_refs)abort();node_refs--;}
    else if(n==&parent){if(!parent_refs)abort();parent_refs--;}
    else abort();
    refs--;node_put_count++;
}
static void run(unsigned int which)
{
    struct n233_cpu_node_consistency zero={0};int wanted=which<3;
    scenario=which;cells=which==0?1:2;logical=0x103;reg_value=logical;
    sample=(struct n231_cpu_observation){0x80000103,24000000,3,4,1,0};
    address_length=size_length=4;reg_length=(int)(4*cells);refs=node_refs=parent_refs=node_get_count=node_put_count=calls=bad_read=bad_publication=bad_index=0;
    switch(which){
    case 0:logical=reg_value=0;sample.mpidr_el1=0x80000000;sample.linux_cpu=0;break;
    case 2:logical=reg_value=0xffffff;sample.mpidr_el1=0x80ffffff;break;
    case 3:sample.linux_cpu=8;break;case 4:sample.status=0;break;case 5:sample.reserved=1;break;
    case 6:sample.current_el=8;break;case 7:sample.cntfrq_el0=0;break;case 8:sample.cntfrq_el0=0x100000000ULL;break;
    case 9:logical=~(n209_u64)0;break;case 10:sample.mpidr_el1=0x80000104;break;
    case 16:address_length=8;break;case 17:cells=0;break;case 18:cells=3;break;
    case 20:size_length=8;break;case 23:reg_length=3;break;case 24:reg_length=12;break;
    case 25:reg_value=0x104;break;case 26:logical=reg_value=0x100000103ULL;sample.mpidr_el1=0x180000103ULL;break;
    default:break;
    }
    be(address,cells,4);be(size_value,which==21?1:0,4);be(reg,reg_value,8);
    if(cells==1)be(reg,reg_value,4);
    memset(&output,0xa5,sizeof(output));variants++;
    CHECK((n233_capture_cpu_node_consistency(which==27?NULL:&sample,&output.value)==0)==wanted);
    CHECK(refs==0&&node_refs==0&&parent_refs==0&&node_get_count==node_put_count&&!bad_publication&&!bad_index);
    CHECK(wanted?(output.value.logical_mpidr==logical&&output.value.firmware_reg==reg_value&&output.value.linux_cpu==sample.linux_cpu&&output.value.address_cells==cells&&output.value.reg_bytes==4*cells&&output.value.status==1):!memcmp(&output.value,&zero,sizeof(zero)));
    CHECK(output.before==UINT64_C(0xa5a5a5a5a5a5a5a5)&&output.after==UINT64_C(0xa5a5a5a5a5a5a5a5));
    CHECK(!bad_read);
    if(wanted)saved[which]=output.value;
}
int main(void)
{
    unsigned int i;for(i=0;i<28;i++)run(i);
    calls=0;variants++;CHECK(n233_capture_cpu_node_consistency(&sample,NULL)!=0);CHECK(calls==0);
    printf("{\"groups\":1,\"variants\":%u,\"assertions\":%u,\"valid_records\":[",variants,assertions);
    for(i=0;i<3;i++)printf("%s{\"reg\":%llu,\"cells\":%u}",i?",":"",(unsigned long long)saved[i].firmware_reg,(unsigned int)saved[i].address_cells);
    printf("]}\n");return 0;
}
