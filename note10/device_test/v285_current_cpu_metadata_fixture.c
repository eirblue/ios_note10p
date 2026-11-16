/* SPDX-License-Identifier: GPL-2.0-only */
#define N285_HOST_FIXTURE
#include <stdio.h>
#include <string.h>
#include "v285_current_cpu_metadata.inc"
static _Alignas(4096) n209_u8 pool[49152],destination_bytes[32U<<20];
static unsigned int lock_depth,locks,unlocks,ended,writes,reads,fail_write,fail_read,corrupt_read,stale;
n285_node *n285_fixture_root;
void n285_fixture_lock(unsigned long *flags)
{ *flags=0;if(lock_depth||!ended)lock_depth=99;else lock_depth=1;locks++; }
void n285_fixture_unlock(unsigned long flags)
{ (void)flags;if(lock_depth!=1)lock_depth=99;else lock_depth=0;unlocks++; }
struct inputs {
    struct n210_request request;struct n210_destination destination;struct n210_context context;
    struct n210_receipt prepared;struct n217_state ingest;unsigned int prepare_spent;n209_u8 hash[32];
};
static struct inputs in;
static unsigned char ac[4]={0,0,0,2},sc[4]={0},reg0[8]={0,0,0,0,0,0,2,5},reg1[8]={0,0,0,0,0,0,0,17};
static n285_property r1={"reg",8,reg1,0},t1={"device_type",4,"cpu",&r1};
static n285_property r0={"reg",8,reg0,0},t0={"device_type",4,"cpu",&r0};
static n285_property size_cells={"#size-cells",4,sc,0},address_cells={"#address-cells",4,ac,&size_cells};
static n285_node cpu1={"cpu@11",&t1,0,0},cpu0={"cpu@205",&t0,0,&cpu1};
static n285_node cpus={"cpus",&address_cells,&cpu0,0},root={"",0,&cpus,0};
static struct n231_cpu_observation sample;
static struct n233_cpu_node_consistency node;
static struct n240_query_receipt query;
static int owner(void *opaque,const struct n210_destination *d)
{ return opaque!=&in||stale||lock_depth||!ended||memcmp(d,&in.destination,sizeof(*d))?-116:0; }
int n285_fixture_write(void *opaque,n209_u64 offset,const void *raw,unsigned int bytes)
{
    if(owner(opaque,&in.destination)||!bytes||bytes>4096||offset%4096+bytes>4096||offset+bytes>sizeof(destination_bytes))return -116;
    writes++;if(writes==fail_write)return -5;
    memcpy(destination_bytes+offset,raw,bytes);return 0;
}
int n285_fixture_read(void *opaque,n209_u64 offset,void *raw,unsigned int bytes)
{
    if(owner(opaque,&in.destination)||!bytes||bytes>4096||offset%4096+bytes>4096||offset+bytes>sizeof(destination_bytes))return -116;
    reads++;if(reads==fail_read)return -5;
    memcpy(raw,destination_bytes+offset,bytes);if(reads==corrupt_read)((n209_u8 *)raw)[0]^=1;return 0;
}
static int setup(void)
{
    struct n209_payload p={0};struct n217_result *r;
    memset(&in,0,sizeof(in));memcpy(p.magic,"N209PAY1",8);p.schema=1;p.bytes=256;
    p.virtual_base=0xffff000001004000ULL;p.kernel_span=3*N209_PAGE;p.entry_extent_bytes=16;
    p.pool_offset=2*N209_PAGE;p.pool_bytes=N209_PAGE;p.adapter_bytes=N209_PAGE;
    p.adapter_entry_offset=64;p.adapter_record_offset=256;
    memset((n209_u8 *)&p+96,1,160);memset(in.hash,2,32);
    memcpy(in.destination.magic,"N210DST1",8);in.destination.schema=1;in.destination.bytes=96;
    in.destination.region.base=N209_ADDRESS_MIN+N210_RESIDUE;in.destination.region.size=N209_DESTINATION_BYTES;
    in.destination.region.generation=1;in.destination.region.page_shift=12;in.destination.region.status=1;
    memset(in.destination.region.build,'1',32);memset(in.destination.region.cookie,1,16);
    in.request.destination=in.destination;memcpy(in.request.payload,&p,256);
    memcpy(in.request.binding.magic,"N210BND1",8);in.request.binding.schema=1;in.request.binding.bytes=128;
    memset(in.request.binding.build,'1',32);memset(in.request.binding.cycle,'3',32);
    memcpy(in.request.binding.descriptor_sha256,in.hash,32);
    memset(in.context.build,'1',32);memset(in.context.boot,'2',32);memset(in.context.cycle,'3',32);
    in.context.return_armed=in.context.page_reserved=in.context.pid1=in.context.cap_sys_boot=1;
    if(n210_prepare_once(&in.request,&in.destination,&in.context,in.hash,&in.prepare_spent,&in.prepared))return 0;
    in.ingest.spent=1;r=&in.ingest.result;memcpy(r->magic,"N217RCP1",8);
    r->schema=1;r->bytes=352;r->status=1;r->flags=7;r->generation=1;
    memcpy(r->build,in.context.build,32);memcpy(r->boot,in.context.boot,32);memcpy(r->cycle,in.context.cycle,32);
    memcpy(r->cookie,in.destination.region.cookie,16);
    r->source_bytes[0]=r->copied_bytes[0]=p.kernel_span;r->source_bytes[1]=r->copied_bytes[1]=p.adapter_bytes;
    memcpy(r->source_sha256[0],p.materialized_sha256,32);memcpy(r->destination_sha256[0],p.materialized_sha256,32);
    memcpy(r->source_sha256[1],p.adapter_sha256,32);memcpy(r->destination_sha256[1],p.adapter_sha256,32);
    r->source_data_bytes=p.kernel_span+p.adapter_bytes;r->staging_request_bytes=4096;
    r->files_held=2;r->destination_content_verified=1;
    memset(&sample,0,sizeof(sample));sample.status=1;sample.linux_cpu=5;sample.current_el=4;
    sample.mpidr_el1=0x80000205;sample.cntfrq_el0=19200000;
    memset(&node,0,sizeof(node));node.status=1;node.linux_cpu=5;node.logical_mpidr=node.firmware_reg=0x205;
    node.address_cells=2;node.reg_bytes=8;
    memset(&query,0,sizeof(query));query.schema=1;query.status=1;
    query.cpu_enter=query.cpu_sample=query.cpu_before_release=5;query.pc_after_capture=query.pc_after_query=1;
    n285_fixture_root=&root;reg0[7]=5;reg1[6]=0;reg1[7]=17;r0.length=r1.length=8;cpu1.sibling=0;
    locks=unlocks=lock_depth=ended=writes=reads=fail_write=fail_read=corrupt_read=stale=0;
    memset(pool,0,sizeof(pool));memset(pool+42312,0x6b,43704-42312);
    memset(pool+44896,0xc7,160);memset(destination_bytes,0xa5,sizeof(destination_bytes));
    return 1;
}
static int attempt(unsigned int *shared_spent)
{
    struct n285_workspace *w=(struct n285_workspace *)pool;struct n278_seal *seal=(struct n278_seal *)(pool+43704);int error;
    if(*shared_spent)return -114;
    *shared_spent=1;ended=1; /* Completed ingestion/codec_end are new-case inputs. */
    memset(pool,0,42312);
    error=n285_snapshot_of_locked(&w->snapshot,&sample,&node,&query);
    if(!error)error=n285_prepare_metadata(&in.request,&in.destination,&in.context,&in,w,sizeof(*w));
    if(!error){if(reads!=5||lock_depth)return -99;
        error=n278_seal_once(seal,&in.request,&in.destination,&in.context,in.hash,&in.prepared,in.prepare_spent,&in.ingest);}
    if(error&&seal->phase==N278_EMPTY)seal->phase=N278_REFUSED;
    memset(pool,0,42312);memset(pool+45056,0,4096);memset(pool+42528,0,112);return error;
}
static int success(void)
{
    unsigned int spent=0,i;struct n278_seal *seal=(struct n278_seal *)(pool+43704);
    struct n285_header *h;struct n209_layout layout;struct n209_payload p;
    if(!setup()||attempt(&spent)||seal->phase!=N278_VALUES_ONLY||locks!=1||unlocks!=1||lock_depth)return 0;
    if(n209_decode_payload(in.request.payload,256,&p)||n209_layout_bounds(&p,&in.destination.region,N209_ADT_MAX,&layout))return 0;
    h=(struct n285_header *)(destination_bytes+layout.args_offset+N285_HEADER_OFFSET);
    if(memcmp(h->magic,"N285STG1",8)||h->adt_bytes==0||h->flags!=3||h->base!=in.destination.region.base||
       memcmp(h->boot,in.context.boot,32)||memcmp(destination_bytes+layout.args_offset+1152,"N10XFER1",8))return 0;
    for(i=0;i<p.kernel_span;i++)if(destination_bytes[i]!=0xa5)return 0;
    for(i=0;i<p.adapter_bytes;i++)if(destination_bytes[layout.adapter_offset+i]!=0xa5)return 0;
    {unsigned int running=0,timebase=0;const n209_u8 *adt=destination_bytes+layout.adt_offset;
     for(i=0;i+40<=h->adt_bytes;i++){
         if(i+44<=h->adt_bytes&&!memcmp(adt+i,"state",6)&&!memcmp(adt+i+36,"running",8))running++;
         if(!memcmp(adt+i,"timebase-frequency",19)){
             static const n209_u8 expected[4]={0,0xf8,0x24,1};
             if(memcmp(adt+i+36,expected,4))return 0;timebase++;
         }
     }
     if(running!=1||timebase!=1)return 0;}
    return 1;
}
static int refusal(void)
{
    unsigned int kind,at,spent;struct n278_seal *seal=(struct n278_seal *)(pool+43704);
    for(kind=0;kind<3;kind++)for(at=1;at<=(kind==0?6U:5U);at++){
        if(!setup())return 0;spent=0;
        if(kind==0)fail_write=at;else if(kind==1)fail_read=at;else corrupt_read=at;
        if(!attempt(&spent)||seal->phase!=N278_REFUSED||lock_depth)return 0;
    }
    for(kind=0;kind<6;kind++){
        if(!setup())return 0;spent=0;
        if(kind==0)stale=1;if(kind==1){reg1[6]=2;reg1[7]=5;}if(kind==2)node.firmware_reg=0x999;
        if(kind==3)r0.length=4;if(kind==4)query.pc_after_release=1;if(kind==5)in.ingest.result.boot[0]='9';
        if(!attempt(&spent)||seal->phase!=N278_REFUSED||locks!=unlocks||lock_depth)return 0;
    }
    return 1;
}
static int lifetime(void)
{
    unsigned int i,spent=0;struct n278_seal saved;
    if(!setup()||attempt(&spent))return 0;
    saved=*(struct n278_seal *)(pool+43704);
    for(i=0;i<42312;i++)if(pool[i])return 0;
    for(i=42312;i<43704;i++)if(pool[i]!=(i>=42528&&i<42640?0:0x6b))return 0;
    for(i=44896;i<45056;i++)if(pool[i]!=0xc7)return 0;
    memset(&root,0,sizeof(root));
    if(attempt(&spent)!=-114||memcmp(&saved,pool+43704,sizeof(saved))||locks!=1||unlocks!=1)return 0;
    root.name="";root.child=&cpus;return 1;
}
int main(void)
{
    if(!success())return 1;puts("PASS metadata-commit");
    if(!refusal())return 2;puts("PASS metadata-refusal");
    if(!lifetime())return 3;puts("PASS metadata-lifetime");
    puts("{\"schema\":\"note10-v285-C-fixture-v1\",\"passed\":true,\"variants\":3,\"assertions\":3,\"device\":0}");
    return 0;
}
