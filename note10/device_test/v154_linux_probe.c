/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef _GNU_SOURCE
#define _GNU_SOURCE
#endif
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#ifndef N154_HOST_TEST
#include <fcntl.h>
#include <sys/mman.h>
#include <sys/mount.h>
#include <sys/stat.h>
#include <unistd.h>
#endif
#ifndef N154_BUILD_ID
#error N154_BUILD_ID must bind the reviewed Image identity
#endif

static const char n154_elf_identity[] __attribute__((used)) = "N10MININIT2:N154IVA";
static char n154_id[33], n154_boot[33], n154_cycle[33];

static int n154_identity(int argc, char **argv)
{
    int count = 0, arm = -1;
    if (argc != 2 || sscanf(argv[1],
        "id=%32[0-9a-f] boot=%32[0-9a-f] cycle=%32[0-9a-f] route=builtin arm=%d%n",
        n154_id, n154_boot, n154_cycle, &arm, &count) != 4 ||
        argv[1][count] || strlen(n154_id) != 32 || strlen(n154_boot) != 32 ||
        strlen(n154_cycle) != 32 || strcmp(n154_id, N154_BUILD_ID) ||
        !strcmp(n154_boot, "00000000000000000000000000000000") ||
        !strcmp(n154_cycle, "00000000000000000000000000000000") || arm != 0)
        return -1;
    return 0;
}

static void n154_record(int log, const char *stage, int error)
{
    dprintf(log, "<6>N154IVA id=%s boot=%s cycle=%s stage=%s errno=%d\n",
            n154_id, n154_boot, n154_cycle, stage, error);
}

static int n154_probe(int log)
{
    long page = sysconf(_SC_PAGESIZE);
    int fd, error, cleanup, good;
    void *mapping;
    if (page <= 0 || page > 0x200000 || (page & (page - 1)) ||
        (0x18200000UL % (unsigned long)page)) {
        n154_record(log, "page-fail", EINVAL);
        return 1;
    }
    fd = open("/dev/iva_ctl", O_RDWR | O_CLOEXEC);
    if (fd < 0) {
        n154_record(log, "open-fail", errno);
        return 1;
    }
    errno = 0;
    mapping = mmap(NULL, (size_t)page, PROT_NONE, MAP_SHARED, fd, (off_t)0x18200000);
    error = errno;
    good = mapping == MAP_FAILED && error == EOPNOTSUPP;
    if (mapping != MAP_FAILED) {
        cleanup = munmap(mapping, (size_t)page);
        n154_record(log, "unexpected-map", cleanup ? errno : 0);
    }
    cleanup = close(fd);
    if (cleanup) {
        n154_record(log, "close-fail", errno);
        good = 0;
    }
    n154_record(log, good ? "pass" : "fail", error);
    return good ? 0 : 1;
}

static int n154_run(int argc, char **argv)
{
    int log, wait;
    if (n154_identity(argc, argv)) {
        dprintf(1, "N154IVA stage=unarmed-or-identity-fail\n");
        return 1;
    }
    if ((mkdir("/proc", 0555) && errno != EEXIST) ||
        (mkdir("/sys", 0555) && errno != EEXIST) ||
        (mount("proc", "/proc", "proc", 0, NULL) && errno != EBUSY) ||
        (mount("sysfs", "/sys", "sysfs", 0, NULL) && errno != EBUSY) ||
        (mount("devtmpfs", "/dev", "devtmpfs", 0, NULL) && errno != EBUSY)) {
        dprintf(1, "N154IVA stage=mount-fail\n");
        return 1;
    }
    log = open("/dev/kmsg", O_WRONLY | O_CLOEXEC);
    if (log < 0)
        return 1;
    n154_record(log, "armed", 0);
    for (wait = 0; wait < 20 && access("/dev/iva_ctl", F_OK); ++wait)
        sleep(1);
    if (access("/dev/iva_ctl", F_OK)) {
        n154_record(log, "node-timeout", ENODEV);
        close(log);
        return 1;
    }
    wait = n154_probe(log);
    close(log);
    return wait;
}

#ifndef N154_HOST_TEST
int main(int argc, char **argv)
{
    (void)n154_run(argc, argv);
    /* Sole recovery owner is the kernel workqueue, including probe failure. */
    for (;;)
        pause();
}
#endif
