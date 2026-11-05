/* NEW129 actual PID1 return-path fixture. Never links/runs old128 core tests. */
#include <stdio.h>
#include <stdlib.h>
#define N10_V129_HOST_FIXTURE 1
#include "v129_loader.c"

static int compare(const char *a,const char *b)
{while(*a && *a==*b){a++;b++;}return (unsigned char)*a-(unsigned char)*b;}
static const char *find(const char *text,const char *word)
{const char *a,*b;for(;*text;text++){a=text;b=word;while(*a && *b && *a==*b){a++;b++;}if(!*b)return text;}return 0;}
static int scenario,recoveries,loads,events,reads;
static char event_log[4096];
int n10_destination_valid(const struct n10_destination *d,const char *build)
{(void)d;(void)build;return scenario==7?-22:0;}
long n10_loader_proof(const struct n10_destination *d,const char *build,const void *data,unsigned long size,
                      const struct n10_loader_ops *operations,void *context)
{
    (void)d;(void)build;(void)data;(void)size;(void)operations;(void)context;
    ++loads;return -(long)(scenario+1);
}
n10_sysword n10_syscall6(n10_sysword nr,n10_sysword a,n10_sysword b,n10_sysword c,n10_sysword d,n10_sysword e,n10_sysword f)
{
    (void)c;(void)d;(void)e;(void)f;
    if(nr==__NR_openat)return compare((const char *)b,"/dev/kmsg")==0?10:(scenario==2?-2:11);
    if(nr==__NR_close)return 0;
    if(nr==__NR_write){
        if(a==10 && b && c>0 && events+c<(long)sizeof(event_log)){
            memcpy(event_log+events,(const void *)b,(unsigned long)c);events+=(int)c;event_log[events]=0;
        }
        return c;
    }
    if(nr==__NR_mount)return scenario==1?-1:0;
    if(nr==__NR_read){
        ++reads;
        if(reads==1){memset((void *)b,0,(unsigned long)c);return scenario==3?-5:scenario==4?127:c;}
        return scenario==5?-5:scenario==6?1:0;
    }
    if(nr==__NR_reboot){
        if(a!=LINUX_REBOOT_MAGIC1 || b!=LINUX_REBOOT_MAGIC2 || c!=LINUX_REBOOT_CMD_RESTART2 || compare((const char *)d,"recovery"))abort();
        ++recoveries;return -1;
    }
    abort();
}

#define REQUIRE(v) do {if(!(v)){fprintf(stderr,"NEW129 failure line %d\n",__LINE__);return 1;}}while(0)
int main(void)
{
    int cases=0,i;
    for(scenario=0;scenario<=12;scenario++){
        recoveries=loads=events=reads=0;event_log[0]=0;
        for(i=0;i<32;i++)n10_proof_cycle[i]=scenario==0?'!':'a';
        n10_test_cookie_offset=scenario==8?32:0;
        n10_legacy_init();
        REQUIRE(recoveries==1);REQUIRE(loads==(scenario>=9));
        REQUIRE(find(event_log,"event=normal-recovery-request\n")!=0);
        REQUIRE(find(event_log,"event=normal-recovery-returned-terminal-park\n")!=0);
        REQUIRE(find(event_log,"event=proof-load-once\n")==0 || loads==1);
        ++cases;
    }
    printf("{\"schema\":\"note10-v129-new-PID1-fixture-v1\",\"passed\":true,\"cases\":%d,\"hardware_operations\":0,\"old_core_runs\":0}\n",cases);
    return 0;
}
