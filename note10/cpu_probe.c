/* User-mode Android CPU diagnostic. No device nodes, MMIO, or privileged writes.
 * Scratch-register PAC instructions are caught with SIGILL if unavailable.
 * MRS reads may be emulated/sanitized by the Android kernel.
 */
#define _GNU_SOURCE
#include <errno.h>
#include <inttypes.h>
#include <sched.h>
#include <setjmp.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/auxv.h>
#include <unistd.h>

#if !defined(__aarch64__)
#error This diagnostic is for AArch64 Android userspace only
#endif

static sigjmp_buf recovery;
static volatile sig_atomic_t probing;

static void illegal(int signal_number)
{
    if (probing)
        siglongjmp(recovery, 1);
    _exit(128 + signal_number);
}

enum operation { PACIA_SCRATCH, XPACI_SCRATCH, ISAR1, MMFR0 };

static int attempt(enum operation op, uint64_t *out)
{
    uint64_t value = 0;
    if (sigsetjmp(recovery, 1)) {
        probing = 0;
        return 0;
    }
    probing = 1;
    switch (op) {
    case PACIA_SCRATCH:
        /* pacia x0, x1 (non-hint encoding); result is never dereferenced. */
        __asm__ volatile("mov x0, xzr\nmov x1, xzr\n.inst 0xdac10020"
                         : : : "x0", "x1", "memory");
        break;
    case XPACI_SCRATCH:
        /* xpaci x0; scratch pointer is never used as a branch or load. */
        __asm__ volatile("mov x0, xzr\n.inst 0xdac143e0" : : : "x0", "memory");
        break;
    case ISAR1:
        __asm__ volatile("mrs %0, id_aa64isar1_el1" : "=r"(value) : : "memory");
        break;
    case MMFR0:
        __asm__ volatile("mrs %0, id_aa64mmfr0_el1" : "=r"(value) : : "memory");
        break;
    }
    probing = 0;
    *out = value;
    return 1;
}

int main(void)
{
    struct sigaction action = {0};
    action.sa_handler = illegal;
    sigemptyset(&action.sa_mask);
    if (sigaction(SIGILL, &action, NULL) != 0) {
        perror("sigaction");
        return 1;
    }
    cpu_set_t original;
    if (sched_getaffinity(0, sizeof(original), &original) != 0) {
        perror("sched_getaffinity");
        return 1;
    }
    uint64_t hwcap = getauxval(AT_HWCAP);
    printf("{\"hwcap\":\"0x%016" PRIx64 "\",\"hwcap_paca\":%s,\"hwcap_pacg\":%s,\"cores\":[",
           hwcap, (hwcap & (1ULL << 30)) ? "true" : "false",
           (hwcap & (1ULL << 31)) ? "true" : "false");
    int first = 1;
    for (int cpu = 0; cpu < CPU_SETSIZE; ++cpu) {
        if (!CPU_ISSET(cpu, &original))
            continue;
        cpu_set_t single;
        CPU_ZERO(&single);
        CPU_SET(cpu, &single);
        if (!first)
            putchar(',');
        first = 0;
        printf("{\"requested_cpu\":%d", cpu);
        if (sched_setaffinity(0, sizeof(single), &single) != 0) {
            printf(",\"affinity_errno\":%d}", errno);
            continue;
        }
        printf(",\"running_cpu\":%d", sched_getcpu());
        uint64_t unused = 0, isar1 = 0, mmfr0 = 0;
        int pacia = attempt(PACIA_SCRATCH, &unused);
        int xpaci = attempt(XPACI_SCRATCH, &unused);
        int isar_ok = attempt(ISAR1, &isar1);
        int mmfr_ok = attempt(MMFR0, &mmfr0);
        printf(",\"pacia\":\"%s\",\"xpaci\":\"%s\"",
               pacia ? "executed" : "SIGILL", xpaci ? "executed" : "SIGILL");
        if (isar_ok)
            printf(",\"isar1_kernel_view\":\"0x%016" PRIx64 "\"", isar1);
        else
            printf(",\"isar1_kernel_view\":null");
        if (mmfr_ok)
            printf(",\"mmfr0_kernel_view\":\"0x%016" PRIx64 "\"", mmfr0);
        else
            printf(",\"mmfr0_kernel_view\":null");
        putchar('}');
    }
    int restore_ok = sched_setaffinity(0, sizeof(original), &original) == 0;
    printf("],\"affinity_restored\":%s}\n", restore_ok ? "true" : "false");
    return restore_ok ? 0 : 1;
}
