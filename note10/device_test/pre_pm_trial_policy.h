/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef N10_PRE_PM_POLICY_H
#define N10_PRE_PM_POLICY_H
#include "runtime_relocation.h"
#define N10_PRE_PM_AFFECTED UINT64_C(0x22b0000)
#define N10_PRE_PM_PAGE UINT64_C(4096)
struct n10_pre_pm_layout { uint64_t backup, guard_after, pfns, capacity, total, pages; };
static int n10_pre_pm_add(uint64_t a, uint64_t b, uint64_t *out)
{ if (a > UINT64_MAX-b) return -1; *out=a+b; return 0; }
static int n10_pre_pm_span(uint64_t a,uint64_t n,uint64_t b,uint64_t m)
{ uint64_t x,y; return !n || !m || n10_pre_pm_add(a,n,&x) || n10_pre_pm_add(b,m,&y) || (a<y && b<x); }
/* Capacity is derived before allocation, including the metadata's own pages. */
static int n10_pre_pm_layout_make(uint64_t affected,uint64_t page,struct n10_pre_pm_layout *out)
{
 uint64_t prefix,pages,total,bytes,rounded; unsigned int i;
 struct n10_pre_pm_layout v={0};
 if (!out || !affected || page!=4096 || affected%page || affected>N10_PRE_PM_AFFECTED) return -1;
 if(n10_pre_pm_add(affected,2*page,&prefix)) return -1;
 pages=prefix/page;
 for(i=0;i<16;i++) {
  if(pages>UINT64_MAX/8) return -1;
  bytes=pages*8;
  if(n10_pre_pm_add(bytes,page-1,&rounded)) return -1;
  rounded=rounded/page*page;
  if(n10_pre_pm_add(prefix,rounded,&total)) return -1;
  if(total/page==pages) { v.backup=page;v.guard_after=page+affected;v.pfns=prefix;v.capacity=rounded/8;v.total=total;v.pages=pages;*out=v;return 0; }
  pages=total/page;
 }
 return -1;
}
static int n10_pre_pm_pfn(uint64_t pfn,uint64_t page,uint64_t base,uint64_t size)
{ if(page!=4096 || pfn>UINT64_MAX/page) return -1;return n10_pre_pm_span(pfn*page,page,base,size)?-1:0; }
static int n10_pre_pm_sorted(const uint64_t *p,uint64_t n)
{ uint64_t i;if(!p||!n) return -1;for(i=1;i<n;i++)if(p[i]<=p[i-1])return -1;return 0; }
static int n10_pre_pm_guard(const uint8_t *p,uint64_t n,uint8_t expected)
{ uint64_t i;if(!p||!n)return -1;for(i=0;i<n;i++)if(p[i]!=expected)return -1;return 0; }
#endif
