/* SPDX-License-Identifier: GPL-2.0-only */
#include <stdio.h>
#include <string.h>
#include "v240_guarded_query.h"
static int context_ok,pc,capture_error,node_error,room_fail,capture_bad,node_bad,cpu_bad,counter_bad;
static unsigned int get_count,put_count,capture_count,node_count,room_count,held_cpu;
static char events[32];static unsigned int event_count;
static void event(char value){if(event_count<sizeof(events)-1)events[event_count++]=value;}
int n240_fixture_context(void){return context_ok;}
n209_u32 n240_fixture_pc(void){return (n209_u32)pc;}
unsigned int n240_fixture_get(void){get_count++;pc++;event('G');return held_cpu;}
void n240_fixture_put(void){put_count++;pc--;event('P');}
unsigned int n240_fixture_cpu(void){return held_cpu+(cpu_bad?1U:0U);}
int n240_fixture_room(n209_u64 *out){room_count++;event('R');*out=15000;return room_count!=(unsigned int)room_fail;}
int n240_fixture_capture(struct n231_cpu_observation *out)
{
    capture_count++;event('C');
    if(pc!=1)return -99;
    /* Model only the unchanged provider's documented balanced nested primitive. */
    pc++;out->linux_cpu=held_cpu;out->status=1;out->current_el=4;out->cntfrq_el0=24000000;pc--;
    if(capture_bad==1)out->status=0;
    if(capture_bad==2)out->linux_cpu++;
    if(counter_bad==1)pc++;
    return capture_error;
}
int n240_fixture_node(const struct n231_cpu_observation *sample,struct n233_cpu_node_consistency *out)
{
    node_count++;event('N');if(pc!=1)return -99;
    out->status=1;out->linux_cpu=sample->linux_cpu;out->logical_mpidr=out->firmware_reg=0x103;out->address_cells=1;out->reg_bytes=4;
    if(node_bad==1)out->status=0;
    if(node_bad==2)out->linux_cpu++;
    if(counter_bad==2)pc++;
    return node_error;
}
static int zero(const void *ptr,unsigned int bytes)
{const unsigned char *raw=ptr;unsigned int i;for(i=0;i<bytes;i++)if(raw[i])return 0;return 1;}
#define CHECK(x) do{assertions++;if(!(x)){fprintf(stderr,"case%u line%u\n",variants,(unsigned int)__LINE__);return 1;}}while(0)
int main(void)
{
    struct {n209_u64 before;struct n231_cpu_observation sample;struct n233_cpu_node_consistency node;struct n240_query_receipt receipt;n209_u64 after;} block;
    unsigned int variant,variants=0,assertions=0;int error;
    for(variant=0;variant<18;variant++){
        variants++;memset(&block,0xa5,sizeof(block));block.before=block.after=0x1122334455667788ULL;
        context_ok=1;pc=0;capture_error=node_error=room_fail=capture_bad=node_bad=cpu_bad=counter_bad=0;
        get_count=put_count=capture_count=node_count=room_count=event_count=0;held_cpu=3;memset(events,0,sizeof(events));
        switch(variant){
        case 1:context_ok=0;break;case 2:pc=1;break;case 3:room_fail=1;break;
        case 4:capture_error=-22;break;case 5:capture_bad=1;break;case 6:capture_bad=2;break;
        case 7:node_error=-22;break;case 8:node_bad=1;break;case 9:node_bad=2;break;
        case 10:cpu_bad=1;break;case 11:counter_bad=1;break;case 12:counter_bad=2;break;
        case 13:room_fail=2;break;case 14:held_cpu=8;break;case 15:capture_error=1;break;
        case 16:node_error=1;break;case 17:held_cpu=0;break;default:break;}
        error=n240_observe_current_cpu(&block.sample,&block.node,&block.receipt);
        CHECK(block.before==0x1122334455667788ULL&&block.after==0x1122334455667788ULL);
        CHECK(block.receipt.schema==1&&block.receipt.error_code==(error<0?(n209_u32)-error:0U));
        CHECK(get_count==put_count&&get_count<=1);
        if(variant==0||variant==17){
            CHECK(error==0&&block.receipt.status==1&&block.sample.status==1&&block.node.status==1);
            CHECK(!strcmp(events,"RGCNPR")&&pc==0);
            CHECK(block.receipt.cpu_enter==held_cpu&&block.receipt.cpu_sample==held_cpu&&block.receipt.cpu_before_release==held_cpu);
            CHECK(block.receipt.pc_before==0&&block.receipt.pc_after_capture==1&&block.receipt.pc_after_query==1&&block.receipt.pc_after_release==0);
            CHECK(block.receipt.pre_headroom==15000&&block.receipt.post_headroom==15000);
            n240_invalidate_observations(&block.sample,&block.node,&block.receipt,-75);
            CHECK(zero(&block.sample,sizeof(block.sample))&&zero(&block.node,sizeof(block.node))&&block.receipt.status==0&&block.receipt.error_code==75);
        }else{
            CHECK(error<0&&block.receipt.status==0&&zero(&block.sample,sizeof(block.sample))&&zero(&block.node,sizeof(block.node)));
            CHECK((variant<=3)?get_count==0:get_count==1);
            CHECK((variant==11||variant==12)?pc==1:(variant==2?pc==1:pc==0));
            CHECK(node_count<=capture_count&&node_count<=1&&capture_count<=1);
            if(variant==4||variant==5||variant==6||variant==11||variant==14||variant==15)CHECK(node_count==0);
        }
    }
    variants++;memset(&block,0xa5,sizeof(block));CHECK(n240_observe_current_cpu(0,&block.node,&block.receipt)==-22);CHECK(zero(&block.node,sizeof(block.node))&&block.receipt.status==0);
    printf("{\"variants\":%u,\"assertions\":%u}\n",variants,assertions);return 0;
}
