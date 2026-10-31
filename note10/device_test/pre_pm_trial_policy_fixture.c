/* New pure data boundary fixtures only: no kernel or OS mocks. */
#include <stdio.h>
#include "pre_pm_trial_policy.h"
#define CASE(name,expr) do { if(!(expr)){fprintf(stderr,"FAIL %s\n",name);return 1;}printf("CASE|%s\n",name); } while(0)
int main(void) {
 struct n10_pre_pm_layout v,old;uint64_t p[3]={1,2,3};uint8_t g[8]={1,1,1,1,1,1,1,1};
 CASE("layout-full",!n10_pre_pm_layout_make(N10_PRE_PM_AFFECTED,4096,&v)&&v.backup==4096&&v.guard_after==36376576&&v.pfns==36380672&&v.total==36454400&&v.pages==8900&&v.capacity==9216&&v.pages==v.total/4096&&v.pages<=v.capacity&&v.pfns==v.guard_after+4096);
 old=v;CASE("layout-overflow",n10_pre_pm_layout_make(UINT64_MAX,4096,&v)&&v.total==old.total);
 CASE("page-size",n10_pre_pm_layout_make(4096,16384,&v));
 CASE("unaligned-size",n10_pre_pm_layout_make(4097,4096,&v));
 CASE("zero-size",n10_pre_pm_layout_make(0,4096,&v));
 CASE("span-overflow",n10_pre_pm_span(UINT64_MAX-1,4,0,8));
 CASE("span-alias",n10_pre_pm_span(100,8,107,8));
 CASE("span-adjacent",!n10_pre_pm_span(100,8,108,8));
 CASE("pfn-outside",!n10_pre_pm_pfn(1,4096,8192,4096));
 CASE("pfn-overlap",n10_pre_pm_pfn(2,4096,8192,4096));
 CASE("pfn-overflow",n10_pre_pm_pfn(UINT64_MAX,4096,8192,4096));
 CASE("pfn-unique",!n10_pre_pm_sorted(p,3));p[2]=2;
 CASE("pfn-duplicate",n10_pre_pm_sorted(p,3));p[2]=0;
 CASE("pfn-unsorted",n10_pre_pm_sorted(p,3));
 CASE("guard-full",!n10_pre_pm_guard(g,8,1));g[7]=0;
 CASE("guard-last-byte",n10_pre_pm_guard(g,8,1));return 0;
}
