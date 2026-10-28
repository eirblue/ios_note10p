/* SPDX-License-Identifier: GPL-2.0-only */
/* Executed by the restored worker only, after PM and CPU restoration. */
#include <linux/note10_pm_edge_dma.h>
#include <linux/note10_pm_edge_iommu.h>
#include <linux/note10_pm_edge_syscore.h>
#include <linux/note10_dma_pm.h>
#include <linux/note10_iommu_pm.h>
#define N10_EDGE_LOG_BUDGET 65536U
#define N10_EDGE_LINE_OVERHEAD 96U
static struct n10_edge_dma_sample n10_edge_dma_out[4];
static struct n10_edge_iommu_sample n10_edge_iommu_out[4];
static struct n10_edge_syscore_sample n10_edge_syscore_out[2];
static struct n10_dma_pm_sample n10_edge_old_dma[3];
static struct n10_iommu_pm_sample n10_edge_old_iommu[3];
static int n10_edge_emit(const char *tag, char *frame, int count,
                         unsigned int *budget, int emit)
{
    unsigned int bytes;
    if (count < 0 || count >= 512) return -E2BIG;
    bytes = count + strlen(tag) + N10_EDGE_LINE_OVERHEAD;
    if (*budget > N10_EDGE_LOG_BUDGET - bytes) return -E2BIG;
    *budget += bytes;
    if (emit) pr_info("%s %s checksum=%08x\n", tag, frame,
                      n10_frame_checksum(frame, count));
    return 0;
}
static int n10_edge_emit_inventory(int emit)
{
    unsigned int copy, phase, index, byte, budget = 0;
    char frame[512], encoded[129];
    static const char digits[] = "0123456789abcdef";
    int n, ret;
#define N10_EDGE_ROW(tag, ...) do { \
    n = snprintf(frame, sizeof(frame), __VA_ARGS__); \
    ret = n10_edge_emit(tag, frame, n, &budget, emit); \
    if (ret) return ret; \
} while (0)
    for (copy = 0; copy < 2; ++copy) {
        for (phase = 0; phase < 4; ++phase) {
            struct n10_edge_dma_sample *d = &n10_edge_dma_out[phase];
            struct n10_edge_iommu_sample *m = &n10_edge_iommu_out[phase];
            N10_EDGE_ROW("N10EDG1", "id=%s seq=%u phase=%u generation=%u total=%x dma=%x prepared=%x suspended=%x late=%x noirq=%x direct=%x syscore=%x covered=%x excdirect=%x excsyscore=%x uncovered=%x active=%x idle=%x other=%x names_xor=%x names_sum=%x",
                N10_RESERVE_BUILD_ID, copy * 4 + phase, phase, d->generation,
                d->total,d->dma,d->prepared,d->suspended,d->late,d->noirq,d->direct,d->syscore,
                d->covered,d->exception_direct,d->exception_syscore,d->uncovered,
                d->active,d->runtime_suspended,d->runtime_other,d->names_xor,d->names_sum);
            N10_EDGE_ROW("N10EIM1", "id=%s seq=%u phase=%u generation=%u total=%x active=%x suspended=%x runtime=%x manual_off=%x manual_on=%x boot_hold=%x secure=%x mapped=%x syscore=%x direct=%x prepared=%x pm_suspended=%x late=%x noirq=%x other=%x names_xor=%x names_sum=%x policy=%x details=%x",
                N10_RESERVE_BUILD_ID,copy * 4 + phase,phase,m->generation,m->total,
                m->active,m->suspended,m->runtime,m->manual_off,m->manual_on,m->boot_hold,
                m->secure_configured,m->mapped,m->syscore,m->direct,m->prepared,m->pm_suspended,
                m->late,m->noirq,m->runtime_other,m->names_xor,m->names_sum,m->policy_active,m->detail_count);
            for (index=0; index < (m->detail_count ? m->detail_count : 1); ++index) {
                struct n10_edge_iommu_detail empty = {0};
                struct n10_edge_iommu_detail *x = m->detail_count ? &m->details[index] : &empty;
                for (byte=0; byte<x->length; ++byte) {
                    encoded[2*byte]=digits[((unsigned char)x->name[byte])>>4];
                    encoded[2*byte+1]=digits[((unsigned char)x->name[byte])&15];
                }
                if (!x->length) { encoded[0]='-'; encoded[1]=0; }
                else encoded[2*x->length]=0;
                N10_EDGE_ROW("N10EID1", "id=%s seq=%u phase=%u generation=%u index=%u count=%u length=%u name=%s activations=%x runtime=%x manual=%x active=%x suspended=%x effective=%x syscore=%x direct=%x prepared=%x pm_suspended=%x late=%x noirq=%x hold=%x secure=%x mapped=%x",
                    N10_RESERVE_BUILD_ID,copy*32+phase*8+index,phase,m->generation,index,m->detail_count,x->length,encoded,
                    x->activations,x->runtime_count,x->manual,x->active,x->suspended,x->effective,x->syscore,x->direct,
                    x->prepared,x->pm_suspended,x->late,x->noirq,x->hold,x->secure,x->mapped);
            }
        }
        for (phase=0; phase<2; ++phase) {
            struct n10_edge_syscore_sample *s = &n10_edge_syscore_out[phase];
            for (index=0; index<s->count; ++index) {
                struct n10_edge_syscore_entry *e=&s->entries[index];
                unsigned int slength=strlen(e->names[0]),rlength=strlen(e->names[1]),dlength=strlen(e->names[2]);
                N10_EDGE_ROW("N10ESC1", "id=%s seq=%u phase=%u generation=%u index=%u count=%u mask=%x slength=%u sname=%s rlength=%u rname=%s dlength=%u dname=%s",
                    N10_RESERVE_BUILD_ID,copy*128+phase*64+index,phase*3,s->generation,index,s->count,e->mask,
                    slength,slength ? e->names[0] : "-",rlength,rlength ? e->names[1] : "-",dlength,dlength ? e->names[2] : "-");
            }
        }
        N10_EDGE_ROW("N10EOK1", "id=%s seq=%u generation=%u status=0", N10_RESERVE_BUILD_ID,copy,n10_edge_dma_out[0].generation);
    }
#undef N10_EDGE_ROW
    return 0;
}
static int n10_edge_compare_old(void)
{
    unsigned int edge, old;
    for (edge=0; edge<=3; edge+=3) {
        struct n10_edge_dma_sample *d=&n10_edge_dma_out[edge];
        struct n10_edge_iommu_sample *m=&n10_edge_iommu_out[edge];
        struct n10_dma_pm_sample *a;
        struct n10_iommu_pm_sample *b;
        old=edge ? 2 : 0; a=&n10_edge_old_dma[old]; b=&n10_edge_old_iommu[old];
        /* Separate sequential reads can see legitimate runtime transitions. */
        if (d->total!=a->total || d->dma!=a->dma || d->names_xor!=a->names_xor ||
            d->names_sum!=a->names_sum || m->total!=b->total || m->names_xor!=b->names_xor ||
            m->names_sum!=b->names_sum || m->syscore!=b->syscore) return -EIO;
    }
    return 0;
}
static int n10_report_pm_edge(unsigned int generation)
{
    unsigned int failures=0, budget=0, copy, phase;
    char frame[512];
    if (n10_edge_dma_read(n10_edge_dma_out,generation)) failures |= 1U;
    if (n10_edge_iommu_read(n10_edge_iommu_out,generation)) failures |= 2U;
    if (n10_edge_syscore_read(n10_edge_syscore_out,generation)) failures |= 4U;
    if (n10_dma_pm_read(n10_edge_old_dma,generation)) failures |= 8U;
    if (n10_iommu_pm_read(n10_edge_old_iommu,generation)) failures |= 16U;
    if (!failures && n10_edge_compare_old()) failures |= 32U;
    if (!failures && n10_edge_emit_inventory(0)) failures |= 64U;
    if (failures) {
        for (copy=0; copy<2; ++copy) {
            for (phase=0; phase<4; ++phase) {
                struct n10_edge_dma_sample *d=&n10_edge_dma_out[phase];
                struct n10_edge_iommu_sample *m=&n10_edge_iommu_out[phase];
                struct n10_edge_syscore_sample *s=phase==0 ? &n10_edge_syscore_out[0] :
                    phase==3 ? &n10_edge_syscore_out[1] : NULL;
                int n=snprintf(frame,sizeof(frame),
                    "id=%s seq=%u phase=%u generation=%u failures=%x dma_seen=%x dma_error=%x dma_generation=%u iommu_seen=%x iommu_error=%x iommu_generation=%u sys_seen=%x sys_error=%x sys_generation=%u sys_count=%x",
                    N10_RESERVE_BUILD_ID,copy*4+phase,phase,generation,failures,
                    d->seen,d->error,d->generation,m->seen,m->error,m->generation,
                    s ? s->seen : 0, s ? s->error : 0, s ? s->generation : 0, s ? s->count : 0);
                n10_edge_emit("N10EER1",frame,n,&budget,1);
            }
            {
                int n=snprintf(frame,sizeof(frame),"id=%s seq=%u generation=%u status=1",N10_RESERVE_BUILD_ID,copy,generation);
                n10_edge_emit("N10EOK1",frame,n,&budget,1);
            }
        }
        return -EIO;
    }
    return n10_edge_emit_inventory(1);
}
