/* SPDX-License-Identifier: GPL-2.0-only */
/* RAM-rootfs PID1 file adapter; no device file or native kernel handoff. */
#include <stdint.h>
#include "note10_iostorage_read_request.h"
#include "note10_iostorage_read_range.h"

#ifndef N190_BUILD_ID
#error N190_BUILD_ID must bind the reviewed Image
#endif
typedef intptr_t n190_word;
_Static_assert(sizeof(n190_word) == 8 && sizeof(uint64_t) == 8, "64-bit ABI required");
_Static_assert(sizeof(N190_BUILD_ID) == 33, "32 hex build identity required");
enum {
    N190_OPENAT = 56, N190_CLOSE = 57, N190_LSEEK = 62,
    N190_WRITE = 64, N190_PREAD64 = 67, N190_PPOLL = 73,
    N190_AT_FDCWD = -100, N190_SEEK_END = 2,
    N190_READ_FLAGS = 00004000 | 0100000 | 02000000,
    N190_KMSG_FLAGS = 00000001 | 00004000 | 0100000 | 02000000,
    N190_BLOCK = 16, N190_BYTES = N190_BLOCK, N190_ELF_MIN = 64, N190_ELF_MAX = 1048576, N190_FRAME_MAX = 512
};
#ifdef N190_HOST_FIXTURE
static n190_word n190_syscall(n190_word, n190_word, n190_word, n190_word, n190_word, n190_word);
#else
#if !defined(__aarch64__) || !defined(__linux__)
#error native PID1 requires Linux AArch64
#endif
static n190_word n190_syscall(n190_word number, n190_word a0, n190_word a1,
                             n190_word a2, n190_word a3, n190_word a4)
{
    register n190_word x0 __asm__("x0") = a0;
    register n190_word x1 __asm__("x1") = a1;
    register n190_word x2 __asm__("x2") = a2;
    register n190_word x3 __asm__("x3") = a3;
    register n190_word x4 __asm__("x4") = a4;
    register n190_word x8 __asm__("x8") = number;
    __asm__ volatile("svc 0" : "+r"(x0) : "r"(x1), "r"(x2), "r"(x3), "r"(x4), "r"(x8) : "memory");
    return x0;
}
#endif
static const char n190_elf_identity[] __attribute__((used)) = "N10MININIT2:N190READ1";

static const char *n190_tag(const char *value, const char *tag)
{
    if (!value)
        return 0;
    while (*tag)
        if (*value++ != *tag++)
            return 0;
    return value;
}

static const char *n190_id(const char *value, const char *expected)
{
    unsigned i;
    int nonzero = 0;
    if (!value)
        return 0;
    for (i = 0; i < 32; ++i) {
        char c = value[i];
        if (!c || !((c >= '0' && c <= '9') || (c >= 'a' && c <= 'f')) ||
            (expected && c != expected[i]))
            return 0;
        nonzero |= c != '0';
    }
    return nonzero ? value + 32 : 0;
}

struct n190_read {
    n190_word fd, open_rc, extent, provider, pread_return, close_rc;
    uint64_t offset, pread_offset;
    unsigned reads, completions, preads;
    uint64_t actual;
    enum note10_iostorage_read_status status;
    bool admitted, returned, owner_live, returned_before_close;
    unsigned char bytes[N190_BYTES];
};

static bool n190_backing_read(void *context, uint64_t offset, uint64_t length, uint64_t *actual)
{
    struct n190_read *s = context;
    ++s->reads;
    if (s->reads != 1 || s->fd < 0 || s->returned || s->provider < N190_BYTES ||
        offset != (uint64_t)s->provider - N190_BYTES || length != N190_BYTES)
        return false;
    s->offset = offset;
    s->pread_offset = offset;
    ++s->preads;
    s->pread_return = n190_syscall(N190_PREAD64, s->fd, (n190_word)s->bytes, N190_BYTES, (n190_word)s->pread_offset, 0);
    *actual = s->pread_return < 0 ? 0 : (uint64_t)s->pread_return;
    return s->pread_return >= 0;
}

static void n190_complete(void *context, enum note10_iostorage_read_status status, uint64_t actual)
{
    struct n190_read *s = context;
    ++s->completions;
    s->status = status;
    s->actual = actual;
    s->owner_live = s->fd >= 0 && !s->returned && s->reads == 1 && s->preads == 1;
}

struct n190_denial { unsigned reads, completions; };

static bool n190_deny_read(void *context, uint64_t offset, uint64_t length, uint64_t *actual)
{
    struct n190_denial *s = context;
    (void)offset; (void)length;
    ++s->reads; *actual = 0;
    return false;
}

static void n190_deny_complete(void *context, enum note10_iostorage_read_status status, uint64_t actual)
{
    struct n190_denial *s = context;
    (void)status; (void)actual;
    ++s->completions;
}

static char *n190_append(char *p, char *limit, const char *text)
{
    if (!p)
        return 0;
    while (*text) {
        if (p == limit)
            return 0;
        *p++ = *text++;
    }
    return p;
}

static char *n190_number(char *p, char *limit, const char *key, n190_word value)
{
    char digits[21];
    unsigned count = 0;
    uint64_t magnitude = value < 0 ? (uint64_t)(-(value + 1)) + 1 : (uint64_t)value;
    p = n190_append(p, limit, key);
    if (value < 0)
        p = n190_append(p, limit, "-");
    do {
        digits[count++] = (char)('0' + magnitude % 10);
        magnitude /= 10;
    } while (magnitude);
    while (count) {
        char digit[2];
        digit[0] = digits[--count]; digit[1] = 0;
        p = n190_append(p, limit, digit);
    }
    return p;
}

static void n190_observe(n190_word argc, const char *argument)
{
    const char *next;
    struct n190_read s;
    struct n190_denial denial = {0, 0};
    char frame[N190_FRAME_MAX], *p, *limit = frame + sizeof(frame);
    n190_word kmsg;
    uint64_t denial_lba = 0;
    unsigned i;
    uint32_t fnv = 0;
    bool positive, denial_attempted = false, denial_admitted = false, denied, passed;

    if (argc != 2)
        return;
    next = n190_id(n190_tag(argument, "id="), N190_BUILD_ID);
    next = n190_id(n190_tag(next, " boot="), 0);
    next = n190_id(n190_tag(next, " cycle="), 0);
    next = n190_tag(next, " route=builtin arm=0");
    if (!next || *next)
        return;

    s.fd = -1; s.open_rc = -61; s.extent = -1; s.provider = 0; s.pread_return = -61; s.close_rc = -61;
    s.reads = 0; s.completions = 0; s.preads = 0; s.actual = 0;
    s.offset = 0; s.pread_offset = 0;
    s.status = NOTE10_IOSTORAGE_READ_ERROR;
    s.admitted = false; s.returned = false; s.owner_live = false; s.returned_before_close = false;
    s.fd = n190_syscall(N190_OPENAT, N190_AT_FDCWD, (n190_word)"/init", N190_READ_FLAGS, 0, 0);
    s.open_rc = s.fd < 0 ? s.fd : 0;
    if (s.fd >= 0) {
        s.extent = n190_syscall(N190_LSEEK, s.fd, 0, N190_SEEK_END, 0, 0);
        if (s.extent >= N190_ELF_MIN && s.extent <= N190_ELF_MAX) {
            uint64_t complete_blocks = (uint64_t)s.extent / N190_BLOCK;
            s.provider = (n190_word)(complete_blocks * N190_BLOCK);
            s.admitted = note10_iostorage_read_request((uint64_t)s.provider, N190_BLOCK, complete_blocks - 1, 1,
                N190_BYTES, NOTE10_IOSTORAGE_READ_DIRECTION, n190_backing_read, n190_complete, &s);
            s.returned = true;
            denial_attempted = true;
            denial_lba = complete_blocks;
            denial_admitted = note10_iostorage_read_request((uint64_t)s.provider, N190_BLOCK,
                denial_lba, 1, N190_BYTES, NOTE10_IOSTORAGE_READ_DIRECTION,
                n190_deny_read, n190_deny_complete, &denial);
        }
        s.returned_before_close = s.returned;
        s.close_rc = n190_syscall(N190_CLOSE, s.fd, 0, 0, 0, 0);
        s.fd = -1;
    }
    if (s.pread_return == N190_BYTES && s.actual == N190_BYTES && s.status == NOTE10_IOSTORAGE_READ_OK) {
        fnv = 2166136261U;
        for (i = 0; i < N190_BYTES; ++i)
            fnv = (fnv ^ s.bytes[i]) * 16777619U;
    }
    positive = s.open_rc == 0 && s.admitted && s.reads == 1 && s.completions == 1 && s.preads == 1 &&
        s.provider >= N190_BYTES && s.provider <= s.extent &&
        s.provider % N190_BLOCK == 0 && s.offset == (uint64_t)s.provider - N190_BYTES &&
        s.pread_offset == s.offset && s.pread_return == N190_BYTES &&
        s.status == NOTE10_IOSTORAGE_READ_OK && s.actual == N190_BYTES && s.owner_live &&
        s.returned_before_close && s.close_rc == 0;
    denied = denial_attempted && !denial_admitted && denial.reads == 0 && denial.completions == 0;
    passed = positive && denied;
    p = n190_append(frame, limit, "<6>N190READ1 ");
    p = n190_append(p, limit, argument);
    p = n190_append(p, limit, " entered=1");
    p = n190_number(p, limit, " op=", s.open_rc);
    p = n190_number(p, limit, " ext=", s.extent);
    p = n190_number(p, limit, " pe=", s.provider);
    p = n190_number(p, limit, " adm=", s.admitted);
    p = n190_number(p, limit, " rcb=", s.reads);
    p = n190_number(p, limit, " ccb=", s.completions);
    p = n190_number(p, limit, " pc=", s.preads);
    p = n190_number(p, limit, " pr=", s.pread_return);
    p = n190_number(p, limit, " st=", s.status);
    p = n190_number(p, limit, " n=", (n190_word)s.actual);
    p = n190_number(p, limit, " off=", (n190_word)s.offset);
    p = n190_number(p, limit, " po=", (n190_word)s.pread_offset);
    p = n190_number(p, limit, " live=", s.owner_live);
    p = n190_number(p, limit, " ret=", s.returned_before_close);
    p = n190_number(p, limit, " cl=", s.close_rc);
    p = n190_number(p, limit, " fnv=", fnv);
    p = n190_number(p, limit, " ok=", positive);
    p = n190_number(p, limit, " dl=", (n190_word)denial_lba);
    p = n190_number(p, limit, " da=", denial_admitted);
    p = n190_number(p, limit, " dr=", denial.reads);
    p = n190_number(p, limit, " dc=", denial.completions);
    p = n190_number(p, limit, " dok=", denied);
    p = n190_number(p, limit, " passed=", passed);
    p = n190_append(p, limit, "\n");
    if (!p)
        return;
    kmsg = n190_syscall(N190_OPENAT, N190_AT_FDCWD, (n190_word)"/dev/kmsg", N190_KMSG_FLAGS, 0, 0);
    if (kmsg >= 0) {
        n190_syscall(N190_WRITE, kmsg, (n190_word)frame, p - frame, 0, 0);
        n190_syscall(N190_CLOSE, kmsg, 0, 0, 0, 0);
    }
}

static void n190_wait(void)
{
    n190_syscall(N190_PPOLL, 0, 0, 0, 0, 0);
}

#ifndef N190_HOST_FIXTURE
__attribute__((used, noreturn)) static void n190_start(const n190_word *stack)
{
    n190_observe(stack[0], stack[0] == 2 ? (const char *)stack[2] : 0);
    for (;;)
        n190_wait();
}
__asm__(".text\n.global _start\n.type _start,%function\n_start:\n"
        "mov x0, sp\nb n190_start\n.size _start, .-_start\n");
#endif
