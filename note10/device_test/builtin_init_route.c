/* SPDX-License-Identifier: GPL-2.0-only
 * Included in the diagnostic TU after the unchanged recovery declarations.
 * All callbacks/arguments remain alive after free_initmem().
 */
static char n10_init_argument[256];

static int __init n10_builtin_identity_init(void)
{
    unsigned char bytes[16];
    unsigned int i;
    /* Pinned get_random_bytes(void *, int), nonblocking. This is a boot-local
     * discriminator, not authentication or a claim of seeded entropy. */
    get_random_bytes(bytes, sizeof(bytes));
    for (i = 0; i < sizeof(bytes); ++i)
        scnprintf(n10_boot_id + 2*i, 3, "%02x", bytes[i]);
    return 0;
}
core_initcall(n10_builtin_identity_init);

char *n10_builtin_init_argument(void)
{
    scnprintf(n10_init_argument, sizeof(n10_init_argument),
        "id=%s boot=%s cycle=%s route=builtin",
        N10_SHA256_KAT_ID, n10_boot_id,
        n10_cycle_valid() ? (const char *)n10_cycle : "00000000000000000000000000000000");
    printk(KERN_INFO "N10ROUTE2 id=%s boot=%s cycle=%s route=builtin exec_attempt=1\n",
        N10_SHA256_KAT_ID, n10_boot_id,
        n10_cycle_valid() ? (const char *)n10_cycle : "00000000000000000000000000000000");
    return n10_init_argument;
}

void __noreturn n10_builtin_init_failed(int error)
{
    printk(KERN_ERR "N10ROUTE2 id=%s boot=%s route=builtin exec_failed=%d\n",
           N10_SHA256_KAT_ID, n10_boot_id, error);
    /* Called only after SYSTEM_RUNNING. Never panic, prepare_namespace,
     * try a normal init, or request another reboot. Recovery owns its queue. */
    for (;;)
        schedule_timeout_uninterruptible(HZ);
}
