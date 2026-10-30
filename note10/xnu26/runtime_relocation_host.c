/* Host-only I/O and focused cases; never linked into the production library. */
#include "runtime_relocation.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <inttypes.h>
#include <errno.h>

static int check(int condition,const char *name)
{
    if(!condition){fprintf(stderr,"FAIL|%s\n",name);return 0;}
    printf("PASS|%s\n",name);return 1;
}
static void default_request(struct n10_rt_request *request,uint8_t adt[56])
{
    memset(request,0,sizeof(*request));memset(adt,0,56);
    adt[0]=1;memcpy(adt+8,"name",4);adt[40]=12;memcpy(adt+44,"device-tree",11);
    request->physical_base=UINT64_C(0x100000000);request->window_size=N10_RT_WINDOW;
    request->image_virtual=UINT64_C(0xfffffff007004000);request->image_size=UINT64_C(0x12ac000);
    request->entry_virtual=UINT64_C(0xfffffff007340490);request->adt=adt;request->adt_length=56;
    request->synthetic_adt=N10_RT_SYNTHETIC_ADT;
    request->command_line=(const uint8_t *)"debug=0x14e";request->command_length=11;
}
static int atomic_rejection(struct n10_rt_request *request)
{
    struct n10_rt_plan plan;uint8_t args[1152],record[64],expected_plan[sizeof(plan)];
    uint8_t expected_args[1152],expected_record[64];int result;
    memset(&plan,0xa5,sizeof(plan));memset(args,0xa5,sizeof(args));memset(record,0xa5,sizeof(record));
    memcpy(expected_plan,&plan,sizeof(plan));memcpy(expected_args,args,sizeof(args));memcpy(expected_record,record,sizeof(record));
    result=n10_rt_build(request,&plan,args,sizeof(args),record,sizeof(record));
    return result!=0 && !memcmp(&plan,expected_plan,sizeof(plan)) && !memcmp(args,expected_args,sizeof(args)) && !memcmp(record,expected_record,sizeof(record));
}
static int selftest(void)
{
    struct n10_rt_request in;struct n10_rt_plan plan;struct n10_rt_range blocked;
    uint8_t adt[60],line[1024],args[1184],record[96];unsigned int i;int ok=1;
    static const uint64_t bases[]={N10_RT_MIN_BASE,UINT64_C(0xc0000000),UINT64_C(0x100000000),N10_RT_LIMIT-N10_RT_WINDOW};
    static const char *const labels[]={"base-minimum","base-synthetic32","base-synthetic64","base-upper-bound"};
    for(i=0;i<4;i++) {
        default_request(&in,adt);in.physical_base=bases[i];
        memset(args,0xa5,sizeof(args));memset(record,0xa5,sizeof(record));
        ok&=check(n10_rt_build(&in,&plan,args+16,1152,record+16,64)==0 &&
            plan.virtual_ram_base==UINT64_C(0xfffffff006000000) && plan.kernel_physical==bases[i]+0x1004000 &&
            plan.entry_physical==bases[i]+0x1340490 && plan.kernel_end==bases[i]+0x22b0000 &&
            plan.arguments_physical==bases[i] && plan.device_tree_physical==bases[i]+0x4000 &&
            plan.adapter_physical==bases[i]+0x8000 && plan.mapping_blocks==7 && plan.kernel_blocks==2,labels[i]);
        for(unsigned int j=0;j<16;j++)if(args[j]!=0xa5 || args[1168+j]!=0xa5 || record[j]!=0xa5 || record[80+j]!=0xa5)ok=0;
    }
    ok&=check(ok,"success-output-canaries");
#define REJECT(name,mutation) do {default_request(&in,adt);mutation;ok&=check(atomic_rejection(&in),name);} while(0)
    REJECT("base-zero",in.physical_base=0);
    REJECT("base-below-minimum-aligned",in.physical_base=N10_RT_MIN_BASE-N10_RT_BLOCK);
    REJECT("base-unaligned",in.physical_base++);
    REJECT("window-wrong",in.window_size-=N10_RT_PAGE);
    REJECT("physical-limit",in.physical_base=N10_RT_LIMIT-N10_RT_WINDOW+N10_RT_BLOCK);
    REJECT("physical-overflow",in.physical_base=UINT64_MAX&~(N10_RT_BLOCK-1));
    REJECT("image-empty",in.image_size=0);
    REJECT("image-unaligned",in.image_size++);
    REJECT("image-va-unaligned",in.image_virtual++);
    REJECT("image-va-overflow",in.image_virtual=UINT64_MAX&~(N10_RT_PAGE-1));
    REJECT("virtual-window-overflow",in.image_virtual=UINT64_C(0xfffffffff0004000);in.entry_virtual=in.image_virtual;in.image_size=N10_RT_PAGE);
    REJECT("entry-before",in.entry_virtual=in.image_virtual-4);
    REJECT("entry-at-end",in.entry_virtual=in.image_virtual+in.image_size);
    REJECT("entry-unaligned",in.entry_virtual++);
    REJECT("metadata-overlap",in.image_virtual=UINT64_C(0xfffffff006004000);in.entry_virtual=in.image_virtual);
    REJECT("initial-mapping-insufficient",in.image_size=UINT64_C(0xe000000));
    REJECT("reserved-arguments",blocked.start=in.physical_base;blocked.size=1;in.reserved=&blocked;in.reserved_count=1);
    REJECT("reserved-tree",blocked.start=in.physical_base+N10_RT_PAGE;blocked.size=1;in.reserved=&blocked;in.reserved_count=1);
    REJECT("occupied-adapter",blocked.start=in.physical_base+2*N10_RT_PAGE;blocked.size=1;in.occupied=&blocked;in.occupied_count=1);
    REJECT("occupied-kernel",blocked.start=in.physical_base+0x1004000;blocked.size=N10_RT_PAGE;in.occupied=&blocked;in.occupied_count=1);
    REJECT("blocked-overflow",blocked.start=UINT64_MAX;blocked.size=2;in.occupied=&blocked;in.occupied_count=1);
    REJECT("blocked-empty",blocked.start=0;blocked.size=0;in.reserved=&blocked;in.reserved_count=1);
    REJECT("too-many-ranges",in.reserved_count=17;in.reserved=&blocked);
    REJECT("missing-ranges",in.occupied_count=1);
    REJECT("adt-not-synthetic",in.synthetic_adt=0);
    REJECT("adt-empty",in.adt_length=0);
    REJECT("adt-too-large",in.adt_length=0x4001);
    REJECT("adt-truncated",in.adt_length=55);
    REJECT("adt-trailing",in.adt_length=60);
    REJECT("adt-gic-handoff",memset(adt+8,0,32);memcpy(adt+8,"gic-handoff",11));
    REJECT("adt-name-padding",adt[39]=1);
    REJECT("adt-no-name",memcpy(adt+8,"else",4));
    REJECT("adt-count-limit",adt[0]=33);
    REJECT("command-too-long",in.command_line=line;in.command_length=1024);
    REJECT("command-nul",in.command_line=(const uint8_t *)"a\0b";in.command_length=3);
    REJECT("command-nonascii",line[0]=0x80;in.command_line=line;in.command_length=1);
#undef REJECT
    default_request(&in,adt);memset(args,0xa5,sizeof(args));memset(record,0xa5,sizeof(record));memset(&plan,0xa5,sizeof(plan));
    ok&=check(n10_rt_build(&in,&plan,args,1151,record,64)!=0 && args[0]==0xa5 && record[0]==0xa5 && ((uint8_t *)&plan)[0]==0xa5,"args-capacity-atomic");
    ok&=check(n10_rt_build(&in,&plan,args,1152,record,63)!=0 && args[0]==0xa5 && record[0]==0xa5,"record-capacity-atomic");
    ok&=check(n10_rt_build(&in,&plan,args,1152,args+32,64)!=0 && args[0]==0xa5,"output-overlap-atomic");
    ok&=check(n10_rt_build(&in,(struct n10_rt_plan *)&in,args,1152,record,64)!=0 && args[0]==0xa5,"input-output-overlap");
    ok&=check(n10_rt_build(&in,NULL,args,1152,record,64)!=0,"null-output");
    ok&=check(n10_rt_serialize_record(1,4,record,64)!=0 && record[0]==0xa5,"descriptor-alignment-atomic");
    memset(line,'a',1023);default_request(&in,adt);in.command_line=line;in.command_length=1023;
    ok&=check(n10_rt_build(&in,&plan,args,1152,record,64)==0 && args[1131]==0,"command-maximum");
    return ok?0:1;
}
static int write_file(const char *directory,const char *name,const void *data,size_t size)
{
    char path[4096];FILE *file;int count=snprintf(path,sizeof(path),"%s/%s",directory,name);
    if(count<0 || (size_t)count>=sizeof(path))return 0;
    file=fopen(path,"wb");if(!file)return 0;
    if(fwrite(data,1,size,file)!=size){fclose(file);return 0;}return fclose(file)==0;
}
static int number(const char *text,uint64_t *out)
{
    char *end;unsigned long long value;
    if(text[0]<'0' || text[0]>'9')return 0;errno=0;value=strtoull(text,&end,0);
    if(errno || *end)return 0;*out=(uint64_t)value;return 1;
}
static int emit(int argc,char **argv)
{
    struct n10_rt_request in;struct n10_rt_plan p;struct n10_rt_boot_fields oracle;
    uint8_t adt[16385],args[1152],record[64],serialized[1152];char json[4096];FILE *file;size_t length;int count;
    if(argc!=8)return 2;memset(&in,0,sizeof(in));
    if(!number(argv[2],&in.physical_base)||!number(argv[3],&in.image_virtual)||!number(argv[4],&in.image_size)||!number(argv[5],&in.entry_virtual))return 2;
    file=fopen(argv[6],"rb");if(!file)return 2;length=fread(adt,1,sizeof(adt),file);if(ferror(file)||fclose(file))return 2;
    in.adt=adt;in.adt_length=(uint32_t)length;in.synthetic_adt=N10_RT_SYNTHETIC_ADT;in.window_size=N10_RT_WINDOW;
    in.command_line=(const uint8_t *)"debug=0x14e";in.command_length=11;
    if(n10_rt_build(&in,&p,args,sizeof(args),record,sizeof(record)))return 3;
    count=snprintf(json,sizeof(json),"{\"virtual_ram_base\":\"0x%" PRIx64 "\",\"physical_base\":%" PRIu64 ",\"window_size\":%" PRIu64 ",\"kernel_physical\":%" PRIu64 ",\"entry_physical\":%" PRIu64 ",\"kernel_end\":%" PRIu64 ",\"arguments_physical\":%" PRIu64 ",\"device_tree_physical\":%" PRIu64 ",\"device_tree_virtual\":\"0x%" PRIx64 "\",\"adapter_physical\":%" PRIu64 ",\"mapping_blocks\":%" PRIu64 ",\"kernel_blocks\":%" PRIu64 ",\"adt_length\":%" PRIu64 "}\n",p.virtual_ram_base,p.physical_base,p.window_size,p.kernel_physical,p.entry_physical,p.kernel_end,p.arguments_physical,p.device_tree_physical,p.device_tree_virtual,p.adapter_physical,p.mapping_blocks,p.kernel_blocks,p.adt_length);
    if(count<0 || (size_t)count>=sizeof(json))return 4;
    memset(&oracle,0,sizeof(oracle));oracle.virtual_base=UINT64_C(0xfffffff000000000);oracle.physical_base=UINT64_C(0x80000000);
    oracle.memory_size=UINT64_C(0x40000000);oracle.top_of_kernel=UINT64_C(0x88004000);
    for(unsigned int i=0;i<6;i++)oracle.video[i]=i+1;
    oracle.machine_type=7;oracle.device_tree_pointer=UINT64_C(0xfffffff006008000);oracle.device_tree_length=0x1234;
    oracle.command_line=(const uint8_t *)"debug=0x14e";oracle.command_length=11;oracle.memory_size_actual=UINT64_C(0x40000000);
    if(n10_rt_serialize_boot_args(&oracle,serialized,sizeof(serialized)))return 5;
    return write_file(argv[7],"boot-args.bin",args,sizeof(args)) && write_file(argv[7],"transfer-record.bin",record,sizeof(record)) &&
           write_file(argv[7],"plan.json",json,(size_t)count) && write_file(argv[7],"oracle-serialized.bin",serialized,sizeof(serialized))?0:6;
}
int main(int argc,char **argv)
{
    if(argc==2 && !strcmp(argv[1],"--selftest"))return selftest();
    if(argc>1 && !strcmp(argv[1],"--emit"))return emit(argc,argv);
    return 2;
}
