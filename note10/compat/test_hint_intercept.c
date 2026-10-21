/* Android-only interception experiment. No Apple code is modified or run. */
#define _GNU_SOURCE
#include "hint_sites.h"
#include <sched.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <sys/mman.h>
#include <ucontext.h>
#include <unistd.h>

static const uint32_t hints[] = {
    0xd503233fU, /* PACIASP */
    0xd50320ffU, /* XPACLRI */
    0xd503233fU, /* PACIASP */
    0xd50323bfU  /* AUTIASP */
};
#define TEST_BRK N10_HINT_BRK
static struct n10_hint_site registered_sites[4];
static struct n10_hint_table registered_table;
static uintptr_t patched_base;
static volatile sig_atomic_t traps, changed, completed;
static uint64_t original_lr;
static const struct n10_fixup_pac_context context = {
    {{48, 0, 5}, {48, 0, 5}}, {{1, 2}, {3, 4}, {5, 6}, {7, 8}}, 15, NULL, NULL
};

static void intercept(int signal_number, siginfo_t *info, void *opaque)
{
    ucontext_t *uc = opaque;
    uintptr_t pc = uc->uc_mcontext.pc;
    /* Only owned RX pages and precisely registered instruction sites qualify.
     * Never treat an arbitrary BRK or an untrusted user PC as a PAC operation.
     */
    if (signal_number != SIGTRAP || !info || info->si_code != TRAP_BRKPT ||
        pc < patched_base + 4 || pc >= patched_base + 20 || (pc & 3)) _exit(120);
    unsigned site = (unsigned)((pc - patched_base - 4) / 4);
    if (site != (unsigned)traps % 4 || *(const uint32_t *)pc != TEST_BRK) _exit(121);
    struct n10_user_state state;
    for (unsigned i = 0; i < 31; ++i) state.x[i] = uc->uc_mcontext.regs[i];
    state.sp = uc->uc_mcontext.sp;
    state.pc = pc;
    if (site == 0) original_lr = state.x[30];
    if (n10_hint_dispatch(&registered_table, *(const uint32_t *)pc, &state, &context) != N10_HINT_OK) _exit(122);
    if (state.pc != pc + 4 || state.sp != uc->uc_mcontext.sp) _exit(123);
    for (unsigned i = 0; i < 30; ++i)
        if (state.x[i] != uc->uc_mcontext.regs[i]) _exit(124);
    if ((site == 0 || site == 2) && state.x[30] != original_lr) ++changed;
    if ((site == 1 || site == 3) && state.x[30] != original_lr) _exit(125);
    /* Only LR and PC are changed; PSTATE and all other signal-frame state stay. */
    uc->uc_mcontext.regs[30] = state.x[30];
    uc->uc_mcontext.pc = state.pc;
    ++traps;
    if (site == 3) ++completed;
}

typedef uint64_t (*probe_fn)(void);
static void *make_probe(int patch, size_t page_size)
{
    uint32_t words[] = {
        0xaa1e03e9U, /* mov x9, x30: preserve real return address */
        hints[0], hints[1], hints[2], hints[3],
        0xca0903c0U, /* eor x0, x30, x9: must return zero */
        0xaa0903feU, /* mov x30, x9 */
        0xd65f03c0U  /* ret */
    };
    if (patch) for (unsigned i = 1; i <= 4; ++i) words[i] = TEST_BRK;
    void *page = mmap(NULL, page_size, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    if (page == MAP_FAILED) return NULL;
    memcpy(page, words, sizeof(words));
    __builtin___clear_cache(page, (char *)page + sizeof(words));
    if (mprotect(page, page_size, PROT_READ | PROT_EXEC)) {
        munmap(page, page_size); return NULL;
    }
    return page;
}

int main(void)
{
    size_t page_size = (size_t)sysconf(_SC_PAGESIZE);
    void *native = make_probe(0, page_size), *patched = make_probe(1, page_size);
    if (!native || !patched) { perror("probe mapping"); return 1; }
    patched_base = (uintptr_t)patched;
    for (unsigned i = 0; i < 4; ++i) {
        registered_sites[i].address = 4 + 4*i;
        registered_sites[i].original_word = hints[i];
    }
    registered_table = (struct n10_hint_table){registered_sites,4,patched_base};
    if (!n10_hint_table_validate(&registered_table)) return 1;
    struct sigaction action = {0}, previous;
    action.sa_sigaction = intercept;
    action.sa_flags = SA_SIGINFO;
    sigemptyset(&action.sa_mask);
    if (sigaction(SIGTRAP, &action, &previous)) { perror("sigaction"); return 1; }
    cpu_set_t saved, one;
    if (sched_getaffinity(0, sizeof(saved), &saved)) { perror("affinity"); return 1; }
    unsigned cores = 0, native_calls = 0, patched_calls = 0;
    int failed = 0;
    for (unsigned cpu = 0; cpu < CPU_SETSIZE; ++cpu) if (CPU_ISSET(cpu, &saved)) {
        CPU_ZERO(&one); CPU_SET(cpu, &one);
        if (sched_setaffinity(0, sizeof(one), &one)) { failed = 1; break; }
        ++cores;
        for (unsigned i = 0; i < 64; ++i) {
            sig_atomic_t before = traps;
            if (((probe_fn)native)() != 0 || traps != before) { failed = 1; break; }
            ++native_calls;
            if (((probe_fn)patched)() != 0 || traps != before + 4) { failed = 1; break; }
            ++patched_calls;
        }
        if (failed) break;
    }
    if (sched_setaffinity(0, sizeof(saved), &saved)) failed = 1;
    if (sigaction(SIGTRAP, &previous, NULL)) failed = 1;
    if (munmap(native, page_size) || munmap(patched, page_size)) failed = 1;
    if (!cores || !changed || completed != (sig_atomic_t)patched_calls) failed = 1;
    printf("{\"cores\":%u,\"native_hint_calls\":%u,\"patched_calls\":%u,"
           "\"handled_brk_traps\":%d,\"signed_lr_changes\":%d,\"passed\":%s}\n",
           cores, native_calls, patched_calls, traps, changed, failed ? "false" : "true");
    return failed;
}
