/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef N299_RETURN_CONTRACT_H
#define N299_RETURN_CONTRACT_H
#ifdef __KERNEL__
#include <linux/types.h>
typedef u32 n299_u32;
#else
typedef unsigned int n299_u32;
#endif
struct n299_marker_ops { int (*read)(void *,int,n299_u32 *); int (*write)(void *,int,n299_u32); };
static inline int n299_stage_marker(const struct n299_marker_ops *ops,void *ctx,n299_u32 mask,n299_u32 normal,n299_u32 recovery)
{
    n299_u32 value,expected;
    if(!ops || !ops->read || !ops->write || !mask || (normal&~mask))return -22;
    if(ops->read(ctx,0,&value))return -5;
    expected=(value&~mask)|normal;
    if(ops->write(ctx,0,expected) || ops->read(ctx,0,&value) || value!=expected)return -5;
    if(ops->write(ctx,1,recovery) || ops->read(ctx,1,&value) || value!=recovery)return -5;
    return 0;
}
static inline int n299_budget(int armed,int requested,int eligible,unsigned long remaining,int spent)
{return armed && !requested && eligible && !spent && remaining>=45000 && remaining<=90000;}
static inline int n299_hex(const char *s,unsigned int n)
{unsigned int i;for(i=0;i<n;++i)if(!((s[i]>='0'&&s[i]<='9')||(s[i]>='a'&&s[i]<='f')))return 0;return !s[n];}
static inline int n299_equal(const char *a,const char *b,unsigned int n)
{unsigned int i;for(i=0;i<n;++i)if(a[i]!=b[i])return 0;return 1;}
static inline int n299_command(char *out,const char *id,const char *cycle,const char *boot)
{
    unsigned int i;
    if(!n299_hex(id,32)||!n299_hex(cycle,32)||!n299_hex(boot,32))return -1;
    for(i=0;i<32;++i){out[i]=id[i];out[i+33]=cycle[i];out[i+66]=boot[i];}
    out[32]=out[65]=' ';out[98]='\n';out[99]=0;return 99;
}
struct n299_status { char boot[33];unsigned int ready,prepared,remaining; };
static inline int n299_parse_status(const char *raw,unsigned int len,const char *id,const char *cycle,struct n299_status *out)
{
    unsigned int i,value=0;
    if(len<105 || len>109 || !n299_equal(raw,id,32)||!n299_equal(raw+33,cycle,32)
       || raw[32]!=' ' || raw[65]!=' ' || raw[98]!=' ' || raw[100]!=' ' || raw[102]!=' '
       || (raw[99]!='0'&&raw[99]!='1') || raw[101]<'0'||raw[101]>'2' || raw[len-1]!='\n')return -1;
    for(i=0;i<32;++i){out->boot[i]=raw[i+66];}
    out->boot[32]=0;
    if(!n299_hex(out->boot,32))return -1;
    for(i=103;i<len-1;++i){if(raw[i]<'0'||raw[i]>'9')return -1;value=value*10+(unsigned int)(raw[i]-'0');}
    if(value>90000)return -1;
    out->remaining=value;out->ready=(unsigned int)(raw[99]-'0');out->prepared=(unsigned int)(raw[101]-'0');return 0;
}
#endif
