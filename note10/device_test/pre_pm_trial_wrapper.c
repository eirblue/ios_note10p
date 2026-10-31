/* SPDX-License-Identifier: GPL-2.0-only */
/* Dormant compile/static prerequisite. No runtime/hardware safety claim. */
#include <asm/barrier.h>
#include <asm/memory.h>
#include <linux/vmalloc.h>
#include <linux/slab.h>
#include <linux/sort.h>
#include <linux/preempt.h>
#include <linux/interrupt.h>
#include <linux/jiffies.h>
#include <crypto/hash.h>
#include "pre_pm_trial_policy.h"
#include "runtime_relocation_trial.c"
#define N10_PRE_PM_CUTOFF_SECONDS 60
static const uint8_t n10_pre_pm_expected[32]={
 0x3b,0x3e,0x72,0x99,0x67,0x29,0x28,0xeb,0xe7,0x08,0x65,0x82,0x89,0x1d,0xdf,0x35,
 0x87,0x8e,0x1c,0xd5,0xed,0x60,0xbf,0xd9,0xce,0x71,0x0d,0x8a,0x86,0x4e,0x7b,0x36};
static const uint8_t n10_pre_pm_tree[56]={1,0,0,0,0,0,0,0,'n','a','m','e',
 [40]=12,[44]='d',[45]='e',[46]='v',[47]='i',[48]='c',[49]='e',[50]='-',[51]='t',[52]='r',[53]='e',[54]='e'};
static int n10_pre_pm_cmp(const void *a,const void *b)
{ uint64_t x=*(const uint64_t *)a,y=*(const uint64_t *)b;return (x>y)-(x<y); }
static int n10_pre_pm_hash(struct shash_desc *desc,const void *p,uint64_t n,const uint8_t *expected)
{ uint8_t hash[32];if(n>0xffffffffULL || crypto_shash_digest(desc,p,(unsigned int)n,hash))return -1;return memcmp(hash,expected,32)?-1:0; }
static noinline int n10_pre_pm_trial(unsigned long reserved,unsigned long count,unsigned long invalid,unsigned long epoch)
{
 struct n10_pre_pm_layout layout;
 struct n10_rt_request req={0}; struct n10_rt_trial_result result;
 struct crypto_shash *tfm=NULL;struct shash_desc *desc=NULL;
 uint8_t *block=NULL,*backup,*window;uint64_t *pfns;uint64_t i;int rc=-EINVAL,trial_rc,verification;
 /* Actual late-init task context; no SYSTEM_RUNNING assumption. */
 if(in_interrupt() || irqs_disabled() || preempt_count() ||
    time_after_eq(jiffies,epoch+N10_PRE_PM_CUTOFF_SECONDS*HZ))return -EINVAL;
 if(n10_window_status!=1 || invalid || reserved!=count || count!=(N10_WINDOW_SIZE>>PAGE_SHIFT) || PAGE_SIZE!=4096 ||
    !n10_window_base || (n10_window_base&(N10_WINDOW_ALIGN-1)) || n10_window_base>N10_WINDOW_LIMIT-N10_WINDOW_SIZE)return -EINVAL;
 window=phys_to_virt(n10_window_base);
 if(!virt_addr_valid(window) || !virt_addr_valid(window+N10_WINDOW_SIZE-1) ||
    virt_to_phys(window)!=n10_window_base || virt_to_phys(window+N10_WINDOW_SIZE-1)!=n10_window_base+N10_WINDOW_SIZE-1)return -EINVAL;
 for(i=0;i<count;i++) {
  unsigned long pfn=PHYS_PFN(n10_window_base)+i;
  if(!pfn_valid(pfn)||!PageReserved(pfn_to_page(pfn)))return -EINVAL;
 }
 if(n10_pre_pm_layout_make(N10_PRE_PM_AFFECTED,PAGE_SIZE,&layout))return -EINVAL;
 tfm=crypto_alloc_shash("sha256-generic",0,0);if(IS_ERR(tfm))return PTR_ERR(tfm);
 if(crypto_shash_digestsize(tfm)!=32 || crypto_shash_descsize(tfm)>PAGE_SIZE-sizeof(*desc))goto out;
 desc=kmalloc(sizeof(*desc)+crypto_shash_descsize(tfm),GFP_KERNEL);if(!desc){rc=-ENOMEM;goto out;}
 desc->tfm=tfm;desc->flags=0;
 block=vmalloc(layout.total);if(!block){rc=-ENOMEM;goto out;}
 backup=block+layout.backup;pfns=(uint64_t *)(block+layout.pfns);
 if(layout.pages>layout.capacity || n10_pre_pm_span((uintptr_t)block,layout.total,(uintptr_t)window,N10_WINDOW_SIZE))goto out;
 for(i=0;i<layout.pages;i++) {
  struct page *page=vmalloc_to_page(block+i*PAGE_SIZE);unsigned long pfn;
  if(!page)goto out;pfn=page_to_pfn(page);
  if(!pfn_valid(pfn)||pfn_to_page(pfn)!=page||n10_pre_pm_pfn(pfn,PAGE_SIZE,n10_window_base,N10_WINDOW_SIZE))goto out;
 }
 /* No allocation bytes are written until every mapping is disjoint. */
 for(i=0;i<layout.pages;i++) {
  struct page *page=vmalloc_to_page(block+i*PAGE_SIZE);unsigned long pfn;
  if(!page)goto out;pfn=page_to_pfn(page);
  if(!pfn_valid(pfn)||pfn_to_page(pfn)!=page||n10_pre_pm_pfn(pfn,PAGE_SIZE,n10_window_base,N10_WINDOW_SIZE))goto out;
  pfns[i]=pfn;
 }
 sort(pfns,layout.pages,sizeof(*pfns),n10_pre_pm_cmp,NULL);
 if(n10_pre_pm_sorted(pfns,layout.pages))goto out;
 memset(block,0xa5,PAGE_SIZE);memset(block+layout.guard_after,0x5a,PAGE_SIZE);
 if(n10_pre_pm_guard(block,PAGE_SIZE,0xa5)||n10_pre_pm_guard(block+layout.guard_after,PAGE_SIZE,0x5a)||
    n10_pre_pm_hash(desc,window,N10_PRE_PM_AFFECTED,n10_pre_pm_expected))goto out;
 memcpy(backup,window,N10_PRE_PM_AFFECTED);
 if(memcmp(backup,window,N10_PRE_PM_AFFECTED)||n10_pre_pm_hash(desc,backup,N10_PRE_PM_AFFECTED,n10_pre_pm_expected))goto out;
 /* Empty optional exclusion lists are not Linux ownership evidence. */
 req.physical_base=n10_window_base;req.window_size=N10_WINDOW_SIZE;req.image_virtual=N10_RTP_IMAGE_VA;
 req.image_size=N10_RTP_IMAGE_SIZE;req.entry_virtual=N10_RTP_ENTRY_VA;req.adt=n10_pre_pm_tree;
 req.adt_length=sizeof(n10_pre_pm_tree);req.synthetic_adt=N10_RT_SYNTHETIC_ADT;
 /* Admission only: this cannot bound duration or prevent a recovery-work race. */
 if(time_after_eq(jiffies,epoch+N10_PRE_PM_CUTOFF_SECONDS*HZ))goto out;
 trial_rc=n10_rt_trial(&req,sizeof(req),sizeof(n10_pre_pm_tree),0,0,0,window,N10_WINDOW_SIZE,backup,N10_PRE_PM_AFFECTED,&result,sizeof(result));
 /* Unconditional complete restore after the admitted call, including failure.
  * Backup corruption/DMA may defeat this attempt; physical gates stay false. */
 memcpy(window,backup,N10_PRE_PM_AFFECTED);
 mb();
 rc=-EIO;
 /* Deliberately sequenced: collect every post-restore check on all statuses. */
 verification=n10_pre_pm_hash(desc,backup,N10_PRE_PM_AFFECTED,n10_pre_pm_expected);
 verification|=n10_pre_pm_hash(desc,window,N10_PRE_PM_AFFECTED,n10_pre_pm_expected);
 verification|=memcmp(window,backup,N10_PRE_PM_AFFECTED)!=0;
 verification|=n10_pre_pm_guard(block,PAGE_SIZE,0xa5);
 verification|=n10_pre_pm_guard(block+layout.guard_after,PAGE_SIZE,0x5a);
 if(verification)goto out;
 if(!trial_rc && result.kernel_offset==N10_RTP_KERNEL_OFFSET && result.image_size==N10_RTP_IMAGE_SIZE &&
    result.affected_size==N10_PRE_PM_AFFECTED && result.transient_compared==N10_RTP_IMAGE_SIZE &&
    result.restored_compared==N10_PRE_PM_AFFECTED && result.backward==1 && !result.reserved)rc=0;
 out:
 if(block)vfree(block);kfree(desc);crypto_free_shash(tfm);return rc;
}
