/* Same-CPU, IRQ-disabled paired CPU-PM only; one normally banked GIC. */
static void n10_gic_priority_clear(struct gic_chip_data *gic)
{
    struct n10_gic_priority *p;
    if (!gic->n10_priority)
        return;
    p = raw_cpu_ptr(gic->n10_priority);
    p->valid = false;
    p->pending = false;
}

static bool n10_gic_priority_begin(struct gic_chip_data *gic)
{
    struct n10_gic_priority *p;
    bool duplicate;
    if (!gic->n10_priority)
        return false;
    p = raw_cpu_ptr(gic->n10_priority);
    duplicate = p->pending;
    p->valid = false;
    p->pending = true;
    return !duplicate && irqs_disabled();
}

static void n10_gic_priority_save(struct gic_chip_data *gic, void __iomem *base)
{
    struct n10_gic_priority *p = raw_cpu_ptr(gic->n10_priority);
    int i;
    for (i = 0; i < 8; i++)
        p->words[i] = readl_relaxed(base + GIC_DIST_PRI + i * 4);
    p->valid = true;
}

static struct n10_gic_priority *n10_gic_priority_take(struct gic_chip_data *gic)
{
    struct n10_gic_priority *p;
    bool valid;
    if (!gic->n10_priority)
        return NULL;
    p = raw_cpu_ptr(gic->n10_priority);
    valid = p->valid && p->pending && irqs_disabled();
    p->valid = false;
    p->pending = false;
    if (!valid)
        pr_warn_once("N10GIPR1: missing GIC priority snapshot\n");
    return valid ? p : NULL;
}
