/* Hosted fixture only: independent snapshots are never inputs to the core. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "runtime_relocation_trial.h"
static uint8_t *capture;
static uint64_t captured;
static int inject,observed;
void n10_fixture_observe(uint8_t *w,uint64_t o,uint64_t s,uint64_t a)
{
    (void)a;memcpy(capture,w+o,(size_t)s);captured=s;observed++;
    if(inject)w[o+s/2]^=0x80;
}
static void save(const char *dir,const char *name,const uint8_t *p,size_t n)
{
    char path[4096];FILE *f;
    if(snprintf(path,sizeof(path),"%s/%s",dir,name)>=(int)sizeof(path))exit(90);
    f=fopen(path,"wb");if(!f || fwrite(p,1,n,f)!=n || fclose(f))exit(91);
}
int main(int argc,char **argv)
{
    const size_t total=0x22b0000;uint8_t tree[56]={1,0,0,0};
    uint8_t command[1024]={'t','e','s','t'};
    struct n10_rt_range reserved={0x90000000,0x4000},occupied={0xa0000000,0x4000};
    struct n10_rt_request r;struct n10_rt_trial_result result,sentinel,*rp=&result;
    const struct n10_rt_request *request=&r;
    uint64_t ic=sizeof(r),ac=56,cc=4,rc=sizeof(reserved),oc=sizeof(occupied),wc=total,bc=total,outc=sizeof(result);
    uint8_t *w=malloc(total+32),*b=malloc(total+32),*before=malloc(total),*oldbackup=malloc(total),*bp=b,*wp=w;
    int id,status,expect=0;uint64_t size=19578880,offset=0x1004000,affected=total;
    FILE *f;
    if(argc!=4 || !w || !b || !before || !oldbackup)return 92;
    memset(w,0xc7,total+32);memset(b,0xc7,total+32);w+=16;b+=16;wp=w;bp=b;
    id=atoi(argv[1]);capture=malloc(19578880);if(!capture)return 93;
    memset(w,0x69,total);memset(b,0xa5,total);memset(&result,0x5a,sizeof(result));sentinel=result;
    f=fopen(argv[2],"rb");if(!f || fread(w,1,19578880,f)!=19578880 || fgetc(f)!=EOF || fclose(f))return 94;
    memcpy(tree+8,"name",4);tree[40]=12;memcpy(tree+44,"device-tree",12);
    memset(&r,0,sizeof(r));r.physical_base=0x80000000;r.window_size=N10_RT_WINDOW;
    r.image_virtual=UINT64_C(0xfffffff007004000);r.image_size=size;r.entry_virtual=UINT64_C(0xfffffff007340490);
    r.adt=tree;r.adt_length=56;r.synthetic_adt=1;r.command_line=command;r.command_length=4;
    r.reserved=&reserved;r.reserved_count=1;r.occupied=&occupied;r.occupied_count=1;
    if(id==1)inject=1;
    if(id>=2 && id<=5){size=0x4000;r.image_size=size;r.entry_virtual=r.image_virtual;
        if(id==3)r.image_virtual=UINT64_C(0xfffffff00600c000);
        if(id==4)r.image_virtual=UINT64_C(0xfffffff006010000);
        if(id==5)r.image_virtual=UINT64_C(0xfffffff007ffc000);
        r.entry_virtual=r.image_virtual;offset=r.image_virtual&0x1ffffff;affected=offset+size;
    }
    if(id>=6)expect=1;
    switch(id){
    case 6:ic=sizeof(r)-1;break;case 7:ac=55;break;case 8:cc=3;break;
    case 9:rc=sizeof(reserved)-1;break;case 10:oc=sizeof(occupied)-1;break;
    case 11:wc=total-1;break;case 12:bc=total-1;break;case 13:outc=sizeof(result)-1;break;
    case 14:wp=NULL;break;case 15:bp=NULL;break;case 16:rp=NULL;break;case 17:request=NULL;break;
    case 18:wp=(uint8_t *)(uintptr_t)(UINTPTR_MAX-15);wc=32;break;
    case 19:bp=(uint8_t *)(uintptr_t)(UINTPTR_MAX-15);bc=32;break;
    case 20:r.adt=(const uint8_t *)(uintptr_t)(UINTPTR_MAX-15);break;
    case 21:bp=w;break;case 22:rp=(struct n10_rt_trial_result *)w;break;
    case 23:request=(const struct n10_rt_request *)w;break;
    case 24:r.adt=w;break;case 25:r.command_line=b;break;
    case 26:r.reserved=(const struct n10_rt_range *)b;break;
    case 27:r.occupied=&reserved;break;case 28:r.command_line=tree;break;
    case 29:r.synthetic_adt=0;break;case 30:tree[4]=1;break;
    case 31:r.image_size=0;break;case 32:r.image_size--;break;
    case 33:r.physical_base++;break;case 34:r.window_size--;break;
    case 35:r.entry_virtual=r.image_virtual-4;break;
    case 36:reserved.start=0x81004000;break;
    case 37:r.reserved_count=17;break;
    case 38:r.image_virtual=UINT64_MAX-0x3fff;break;
    case 39:r.command_length=1024;cc=1024;break;
    case 40:command[0]=1;break;
    case 41:ac=UINT64_MAX;break;
    case 42:wc=UINT64_MAX;break;
    case 43:outc=UINT64_MAX;break;
    case 44:rc=UINT64_MAX;break;
    case 45:oc=UINT64_MAX;break;
    case 46:ic=UINT64_MAX;break;
    case 47:r.adt_length=0;break;
    default:break;
    }
    /* Validate independent oracle spans outside the core. malloc objects are
     * distinct; comparison below also rejects overlapping numeric spans. */
    {const void *objects[12]={w,b,before,oldbackup,capture,&r,tree,command,&reserved,&occupied,&result,&sentinel};
     size_t lengths[12]={total,total,total,total,19578880,sizeof(r),sizeof(tree),sizeof(command),sizeof(reserved),sizeof(occupied),sizeof(result),sizeof(sentinel)};unsigned j,k;
     for(j=0;j<12;j++)for(k=j+1;k<12;k++)if((uintptr_t)objects[j]<(uintptr_t)objects[k]+lengths[k] &&
       (uintptr_t)objects[k]<(uintptr_t)objects[j]+lengths[j])return 95;}
    memcpy(before,w,total);memcpy(oldbackup,b,total);
    status=n10_rt_trial(request,ic,ac,cc,rc,oc,wp,wc,bp,bc,rp,outc);
    {size_t guard;for(guard=0;guard<16;guard++)if(w[-16+(int)guard]!=0xc7 || w[total+guard]!=0xc7 || b[-16+(int)guard]!=0xc7 || b[total+guard]!=0xc7)return 16;}
    if(memcmp(w,before,total))return 10;
    if(expect){if(!status || observed || memcmp(b,oldbackup,total) || memcmp(&result,&sentinel,sizeof(result)))return 11;}
    else {
        if(observed!=1 || captured!=size || memcmp(capture,before,(size_t)size) || memcmp(b,before,(size_t)affected))return 12;
        if(memcmp(b+affected,oldbackup+affected,total-(size_t)affected))return 15;
        if(id==1){if(!status || memcmp(&result,&sentinel,sizeof(result)))return 13;}
        else if(status || result.kernel_offset!=offset || result.image_size!=size || result.affected_size!=affected ||
          result.transient_compared!=size || result.restored_compared!=affected || result.backward!=(uint32_t)(offset<size) || result.reserved)return 14;
    }
    if(id==0 || id==1){char name[64];
        snprintf(name,sizeof(name),"case%d-before.bin",id);save(argv[3],name,before,total);
        snprintf(name,sizeof(name),"case%d-after.bin",id);save(argv[3],name,w,total);
        snprintf(name,sizeof(name),"case%d-transient.bin",id);save(argv[3],name,capture,(size_t)size);
        snprintf(name,sizeof(name),"case%d-backup.bin",id);save(argv[3],name,b,total);
    }
    printf("CASE|%d|status=%d|observed=%d|bytes=%llu|restored=%llu\n",id,status,observed,
      (unsigned long long)captured,(unsigned long long)(expect?0:affected));
    free(w-16);free(b-16);free(before);free(oldbackup);free(capture);return 0;
}
