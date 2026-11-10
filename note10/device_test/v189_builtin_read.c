/* SPDX-License-Identifier: GPL-2.0-only */
/* RAM-rootfs PID1 file adapter; no device file or native kernel handoff. */
#include <stdint.h>
#include "note10_iostorage_read_request.h"
#include "note10_iostorage_read_range.h"

#ifndef N189_BUILD_ID
#error N189_BUILD_ID must bind the reviewed Image
#endif
typedef intptr_t n189_word;
_Static_assert(sizeof(n189_word) == 8 && sizeof(uint64_t) == 8, "64-bit ABI required");
_Static_assert(sizeof(N189_BUILD_ID) == 33, "32 hex build identity required");
enum {
    N189_OPENAT = 56, N189_CLOSE = 57, N189_LSEEK = 62,
    N189_WRITE = 64, N189_PREAD64 = 67, N189_PPOLL = 73,
    N189_AT_FDCWD = -100, N189_SEEK_END = 2,
    N189_READ_FLAGS = 00004000 | 0100000 | 02000000,
    N189_KMSG_FLAGS = 00000001 | 00004000 | 0100000 | 02000000,
    N189_BLOCK = 16, N189_LBA = 3, N189_COUNT = 2, N189_OFFSET = 48, N189_BYTES = 32, N189_ELF_MAX = 1048576, N189_FRAME_MAX = 512
};
#ifdef N189_HOST_FIXTURE
static n189_word n189_syscall(n189_word, n189_word, n189_word, n189_word, n189_word, n189_word);
#else
#if !defined(__aarch64__) || !defined(__linux__)
#error native PID1 requires Linux AArch64
#endif
static n189_word n189_syscall(n189_word number, n189_word a0, n189_word a1,
                             n189_word a2, n189_word a3, n189_word a4)
{
    register n189_word x0 __asm__("x0") = a0;
    register n189_word x1 __asm__("x1") = a1;
    register n189_word x2 __asm__("x2") = a2;
    register n189_word x3 __asm__("x3") = a3;
    register n189_word x4 __asm__("x4") = a4;
    register n189_word x8 __asm__("x8") = number;
    __asm__ volatile("svc 0" : "+r"(x0) : "r"(x1), "r"(x2), "r"(x3), "r"(x4), "r"(x8) : "memory");
    return x0;
}
#endif
static const char n189_elf_identity[] __attribute__((used)) = "N10MININIT2:N189READ1";

static const char *n189_tag(const char *value, const char *tag)
{
    if (!value)
        return 0;
    while (*tag)
        if (*value++ != *tag++)
            return 0;
    return value;
}

static const char *n189_id(const char *value, const char *expected)
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

struct n189_read {
    n189_word fd, open_rc, extent, provider, pread_return, close_rc;
    uint64_t offset, pread_offset;
    unsigned reads, completions, preads;
    uint64_t actual;
    enum note10_iostorage_read_status status;
    bool admitted, returned, owner_live, returned_before_close;
    unsigned char bytes[N189_BYTES];
};

static bool n189_backing_read(void *context, uint64_t offset, uint64_t length, uint64_t *actual)
{
    struct n189_read *s = context;
    ++s->reads;
    if (s->reads != 1 || s->fd < 0 || s->returned || offset != N189_OFFSET || length != N189_BYTES)
        return false;
    s->offset = offset;
    s->pread_offset = offset;
    ++s->preads;
    s->pread_return = n189_syscall(N189_PREAD64, s->fd, (n189_word)s->bytes, N189_BYTES, (n189_word)s->pread_offset, 0);
    *actual = s->pread_return < 0 ? 0 : (uint64_t)s->pread_return;
    return s->pread_return >= 0;
}

static void n189_complete(void *context, enum note10_iostorage_read_status status, uint64_t actual)
{
    struct n189_read *s = context;
    ++s->completions;
    s->status = status;
    s->actual = actual;
    s->owner_live = s->fd >= 0 && !s->returned && s->reads == 1 && s->preads == 1;
}

struct n189_denial { unsigned reads, completions; };

static bool n189_deny_read(void *context, uint64_t offset, uint64_t length, uint64_t *actual)
{
    struct n189_denial *s = context;
    (void)offset; (void)length;
    ++s->reads; *actual = 0;
    return false;
}

static void n189_deny_complete(void *context, enum note10_iostorage_read_status status, uint64_t actual)
{
    struct n189_denial *s = context;
    (void)status; (void)actual;
    ++s->completions;
}

static char *n189_append(char *p, char *limit, const char *text)
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

static char *n189_number(char *p, char *limit, const char *key, n189_word value)
{
    char digits[21];
    unsigned count = 0;
    uint64_t magnitude = value < 0 ? (uint64_t)(-(value + 1)) + 1 : (uint64_t)value;
    p = n189_append(p, limit, key);
    if (value < 0)
        p = n189_append(p, limit, "-");
    do {
        digits[count++] = (char)('0' + magnitude % 10);
        magnitude /= 10;
    } while (magnitude);
    while (count) {
        char digit[2];
        digit[0] = digits[--count]; digit[1] = 0;
        p = n189_append(p, limit, digit);
    }
    return p;
}

static void n189_observe(n189_word argc, const char *argument)
{
    const char *next;
    struct n189_read s;
    struct n189_denial denial = {0, 0};
    char frame[N189_FRAME_MAX], *p, *limit = frame + sizeof(frame);
    n189_word kmsg;
    unsigned eh = 0, ps = 0, pn = 0, pt = 0, pf = 0, i;
    uint32_t fnv = 0;
    bool positive, denial_attempted = false, denial_admitted = false, denied, passed;

    if (argc != 2)
        return;
    next = n189_id(n189_tag(argument, "id="), N189_BUILD_ID);
    next = n189_id(n189_tag(next, " boot="), 0);
    next = n189_id(n189_tag(next, " cycle="), 0);
    next = n189_tag(next, " route=builtin arm=0");
    if (!next || *next)
        return;

    s.fd = -1; s.open_rc = -61; s.extent = -1; s.provider = 0; s.pread_return = -61; s.close_rc = -61;
    s.reads = 0; s.completions = 0; s.preads = 0; s.actual = 0;
    s.offset = 0; s.pread_offset = 0;
    s.status = NOTE10_IOSTORAGE_READ_ERROR;
    s.admitted = false; s.returned = false; s.owner_live = false; s.returned_before_close = false;
    s.fd = n189_syscall(N189_OPENAT, N189_AT_FDCWD, (n189_word)"/init", N189_READ_FLAGS, 0, 0);
    s.open_rc = s.fd < 0 ? s.fd : 0;
    if (s.fd >= 0) {
        s.extent = n189_syscall(N189_LSEEK, s.fd, 0, N189_SEEK_END, 0, 0);
        if (s.extent >= N189_OFFSET + N189_BYTES && s.extent <= N189_ELF_MAX) {
            s.provider = s.extent - s.extent % N189_BLOCK;
            s.admitted = note10_iostorage_read_request((uint64_t)s.provider, N189_BLOCK, N189_LBA, N189_COUNT,
                N189_BYTES, NOTE10_IOSTORAGE_READ_DIRECTION, n189_backing_read, n189_complete, &s);
            s.returned = true;
            denial_attempted = true;
            denial_admitted = note10_iostorage_read_request((uint64_t)s.provider, N189_BLOCK,
                N189_LBA, N189_COUNT, N189_BYTES - 1, NOTE10_IOSTORAGE_READ_DIRECTION,
                n189_deny_read, n189_deny_complete, &denial);
        }
        s.returned_before_close = s.returned;
        s.close_rc = n189_syscall(N189_CLOSE, s.fd, 0, 0, 0, 0);
        s.fd = -1;
    }
    if (s.pread_return == N189_BYTES && s.actual == N189_BYTES && s.status == NOTE10_IOSTORAGE_READ_OK) {
        eh = (unsigned)s.bytes[4] | (unsigned)s.bytes[5] << 8;
        ps = (unsigned)s.bytes[6] | (unsigned)s.bytes[7] << 8;
        pn = (unsigned)s.bytes[8] | (unsigned)s.bytes[9] << 8;
        pt = (unsigned)s.bytes[16] | (unsigned)s.bytes[17] << 8 |
            (unsigned)s.bytes[18] << 16 | (unsigned)s.bytes[19] << 24;
        pf = (unsigned)s.bytes[20] | (unsigned)s.bytes[21] << 8 |
            (unsigned)s.bytes[22] << 16 | (unsigned)s.bytes[23] << 24;
        fnv = 2166136261U;
        for (i = 0; i < N189_BYTES; ++i)
            fnv = (fnv ^ s.bytes[i]) * 16777619U;
    }
    positive = s.open_rc == 0 && s.admitted && s.reads == 1 && s.completions == 1 && s.preads == 1 &&
        s.provider >= N189_OFFSET + N189_BYTES && s.provider <= s.extent &&
        s.provider % N189_BLOCK == 0 && s.offset == N189_OFFSET && s.pread_offset == N189_OFFSET && s.pread_return == N189_BYTES &&
        s.status == NOTE10_IOSTORAGE_READ_OK && s.actual == N189_BYTES && s.owner_live &&
        s.returned_before_close && s.close_rc == 0 && eh == 64 && ps == 56 && pn >= 1 && pn <= 16;
    denied = denial_attempted && !denial_admitted && denial.reads == 0 && denial.completions == 0;
    passed = positive && denied;
    p = n189_append(frame, limit, "<6>N189READ1 ");
    p = n189_append(p, limit, argument);
    p = n189_append(p, limit, " entered=1");
    p = n189_number(p, limit, " op=", s.open_rc);
    p = n189_number(p, limit, " ext=", s.extent);
    p = n189_number(p, limit, " pe=", s.provider);
    p = n189_number(p, limit, " adm=", s.admitted);
    p = n189_number(p, limit, " rcb=", s.reads);
    p = n189_number(p, limit, " ccb=", s.completions);
    p = n189_number(p, limit, " pc=", s.preads);
    p = n189_number(p, limit, " pr=", s.pread_return);
    p = n189_number(p, limit, " st=", s.status);
    p = n189_number(p, limit, " n=", (n189_word)s.actual);
    p = n189_number(p, limit, " off=", (n189_word)s.offset);
    p = n189_number(p, limit, " po=", (n189_word)s.pread_offset);
    p = n189_number(p, limit, " live=", s.owner_live);
    p = n189_number(p, limit, " ret=", s.returned_before_close);
    p = n189_number(p, limit, " cl=", s.close_rc);
    p = n189_number(p, limit, " eh=", eh);
    p = n189_number(p, limit, " ps=", ps);
    p = n189_number(p, limit, " pn=", pn);
    p = n189_number(p, limit, " pt=", pt);
    p = n189_number(p, limit, " pf=", pf);
    p = n189_number(p, limit, " fnv=", fnv);
    p = n189_number(p, limit, " ok=", positive);
    p = n189_number(p, limit, " da=", denial_admitted);
    p = n189_number(p, limit, " dr=", denial.reads);
    p = n189_number(p, limit, " dc=", denial.completions);
    p = n189_number(p, limit, " dok=", denied);
    p = n189_number(p, limit, " passed=", passed);
    p = n189_append(p, limit, "\n");
    if (!p)
        return;
    kmsg = n189_syscall(N189_OPENAT, N189_AT_FDCWD, (n189_word)"/dev/kmsg", N189_KMSG_FLAGS, 0, 0);
    if (kmsg >= 0) {
        n189_syscall(N189_WRITE, kmsg, (n189_word)frame, p - frame, 0, 0);
        n189_syscall(N189_CLOSE, kmsg, 0, 0, 0, 0);
    }
}

static void n189_wait(void)
{
    n189_syscall(N189_PPOLL, 0, 0, 0, 0, 0);
}

#ifndef N189_HOST_FIXTURE
__attribute__((used, noreturn)) static void n189_start(const n189_word *stack)
{
    n189_observe(stack[0], stack[0] == 2 ? (const char *)stack[2] : 0);
    for (;;)
        n189_wait();
}
__asm__(".text\n.global _start\n.type _start,%function\n_start:\n"
        "mov x0, sp\nb n189_start\n.size _start, .-_start\n");
#endif
