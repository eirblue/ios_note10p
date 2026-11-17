/* SPDX-License-Identifier: GPL-2.0-only */
/* New park loop only; no kernel worker, hardware operation or reboot. */
#include <assert.h>
#include <setjmp.h>
#include <stdarg.h>
#include <stdio.h>
#include <string.h>
#define __noreturn __attribute__((noreturn))
#define KERN_INFO ""
#define HZ 100
#define READ_ONCE(value) (value)
#define atomic_read(value) (*(value))
#define N154_BUILD_ID "11111111111111111111111111111111"
static const char n10_boot_id[] = "22222222222222222222222222222222";
static const char n10_cycle[] = "33333333333333333333333333333333";
static int n154_arm_result, n10_return_requested;
enum { SYSTEM_RUNNING = 2 };
static int system_state = SYSTEM_RUNNING;
static unsigned int records, sleeps, requested_records;
static jmp_buf stop;

static int printk(const char *format, ...)
{
    char line[256], expected[32];
    va_list args;
    va_start(args, format);
    int count = vsnprintf(line, sizeof(line), format, args);
    va_end(args);
    assert(count > 0 && (unsigned int)count < sizeof(line));
    assert(strstr(line, "N293RET id=" N154_BUILD_ID));
    assert(strstr(line, "boot=22222222222222222222222222222222"));
    assert(strstr(line, "cycle=33333333333333333333333333333333"));
    snprintf(expected, sizeof(expected), "seq=%u ", records);
    assert(strstr(line, expected) && strstr(line, "arm=0"));
    assert(strstr(line, "running=1"));
    if (n10_return_requested) {
        assert(strstr(line, "requested=1"));
        ++requested_records;
    }
    ++records;
    return count;
}

static long schedule_timeout_uninterruptible(long delay)
{
    assert(delay == 10 * HZ);
    if (++sleeps == 9)
        n10_return_requested = 1; /* Existing owner's state; loop must not retry. */
    if (sleeps == 13)
        longjmp(stop, 1);
    return 0;
}

#include "v293_recovery_only.inc"

int main(void)
{
    for (int initial = 0; initial < 2; ++initial) {
        records = sleeps = requested_records = 0;
        n10_return_requested = initial;
        if (!setjmp(stop))
            n293_recovery_only();
        assert(records == 12 && sleeps == 13);
        assert(requested_records == (initial ? 12U : 3U));
    }
    puts("{\"passed\":true,\"groups\":1,\"variants\":2,\"assertions\":8}");
    return 0;
}
