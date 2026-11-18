/* Only new299 guard, wire and reused-marker adapter boundary cases. */
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "v299_return_contract.h"
struct fake { unsigned int magic,panic;int reads,writes,read_error,mismatch; };
static int rd(void *p,int which,unsigned int *v)
{struct fake *f=p;++f->reads;if(f->read_error)return -1;*v=which?f->panic:f->magic;if(f->mismatch&&f->writes)*v^=1;return 0;}
static int wr(void *p,int which,unsigned int v)
{struct fake *f=p;++f->writes;if(which)f->panic=v;else f->magic=v;return 0;}
int main(void)
{
    const struct n299_marker_ops ops={rd,wr};struct fake f;
    const char *id="11111111111111111111111111111111",*cycle="22222222222222222222222222222222",*boot="33333333333333333333333333333333";
    char command[100],status[128];struct n299_status parsed;int n;
    assert(n299_budget(1,0,1,45000,0));
    assert(!n299_budget(0,0,1,60000,0));
    assert(!n299_budget(1,1,1,60000,0));
    assert(!n299_budget(1,0,0,60000,0));
    assert(!n299_budget(1,0,1,60000,1));
    assert(!n299_budget(1,0,1,44999,0));
    assert(!n299_budget(1,0,1,90001,0));
    assert(n299_command(command,id,cycle,boot)==99 && command[98]=='\n' && command[99]==0);
    assert(n299_command(command,"wrong",cycle,boot)<0);
    f=(struct fake){.magic=0xA5B61234};
    assert(!n299_stage_marker(&ops,&f,0xFF0000,0x4E0000,0x12345674) && f.magic==0xA54E1234 && f.panic==0x12345674 && f.writes==2);
    f=(struct fake){.magic=7,.mismatch=1};
    assert(n299_stage_marker(&ops,&f,0xFF0000,0x4E0000,0x12345674)==-5 && f.writes==1);
    f=(struct fake){.read_error=1};
    assert(n299_stage_marker(&ops,&f,0xFF0000,0x4E0000,0x12345674)==-5 && !f.writes);
    n=snprintf(status,sizeof(status),"%s %s %s 1 0 60000\n",id,cycle,boot);
    assert(!n299_parse_status(status,(unsigned int)n,id,cycle,&parsed) && parsed.remaining==60000 && parsed.ready==1 && !parsed.prepared);
    assert(n299_parse_status(status,(unsigned int)n-1,id,cycle,&parsed)<0);
    status[0]='4';assert(n299_parse_status(status,(unsigned int)n,id,cycle,&parsed)<0);
    puts("{\"passed\":true,\"groups\":1,\"variants\":15,\"assertions\":15}");
    return 0;
}
