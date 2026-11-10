/* SPDX-License-Identifier: GPL-2.0-only */
/* RAM-rootfs PID1 file adapter; no device file or native kernel handoff. */
#include <stdint.h>
#include "note10_iostorage_read_request.h"
#include "note10_iostorage_read_range.h"

#ifndef N188_BUILD_ID
#error N188_BUILD_ID must bind the reviewed Image
#endif
typedef intptr_t n188_word;
_Static_assert(sizeof(n188_word) == 8 && sizeof(uint64_t) == 8, "64-bit ABI required");
_Static_assert(sizeof(N188_BUILD_ID) == 33, "32 hex build identity required");
enum {
    N188_OPENAT = 56, N188_CLOSE = 57, N188_LSEEK = 62,
    N188_WRITE = 64, N188_PREAD64 = 67, N188_PPOLL = 73,
    N188_AT_FDCWD = -100, N188_SEEK_END = 2,
    N188_READ_FLAGS = 00004000 | 0100000 | 02000000,
    N188_KMSG_FLAGS = 00000001 | 00004000 | 0100000 | 02000000,
    N188_BLOCK = 16, N188_LBA = 3, N188_COUNT = 2, N188_OFFSET = 48, N188_BYTES = 32, N188_ELF_MAX = 1048576, N188_FRAME_MAX = 512
};
#ifdef N188_HOST_FIXTURE
static n188_word n188_syscall(n188_word, n188_word, n188_word, n188_word, n188_word, n188_word);
#else
#if !defined(__aarch64__) || !defined(__linux__)
#error native PID1 requires Linux AArch64
#endif
static n188_word n188_syscall(n188_word number, n188_word a0, n188_word a1,
                             n188_word a2, n188_word a3, n188_word a4)
{
    register n188_word x0 __asm__("x0") = a0;
    register n188_word x1 __asm__("x1") = a1;
    register n188_word x2 __asm__("x2") = a2;
    register n188_word x3 __asm__("x3") = a3;
    register n188_word x4 __asm__("x4") = a4;
    register n188_word x8 __asm__("x8") = number;
    __asm__ volatile("svc 0" : "+r"(x0) : "r"(x1), "r"(x2), "r"(x3), "r"(x4), "r"(x8) : "memory");
    return x0;
}
#endif
static const char n188_elf_identity[] __attribute__((used)) = "N10MININIT2:N188READ1";

static const char *n188_tag(const char *value, const char *tag)
{
    if (!value)
        return 0;
    while (*tag)
        if (*value++ != *tag++)
            return 0;
    return value;
}

static const char *n188_id(const char *value, const char *expected)
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

struct n188_read {
    n188_word fd, open_rc, extent, pread_return, close_rc;
    uint64_t offset, pread_offset;
    unsigned reads, completions, preads;
    uint64_t actual;
    enum note10_iostorage_read_status status;
    bool admitted, returned, owner_live, returned_before_close;
    unsigned char bytes[N188_BYTES];
};

static bool n188_backing_read(void *context, uint64_t offset, uint64_t length, uint64_t *actual)
{
    struct n188_read *s = context;
    ++s->reads;
    if (s->reads != 1 || s->fd < 0 || s->returned || offset != N188_OFFSET || length != N188_BYTES)
        return false;
    s->offset = offset;
    s->pread_offset = offset;
    ++s->preads;
    s->pread_return = n188_syscall(N188_PREAD64, s->fd, (n188_word)s->bytes, N188_BYTES, (n188_word)s->pread_offset, 0);
    *actual = s->pread_return < 0 ? 0 : (uint64_t)s->pread_return;
    return s->pread_return >= 0;
}

static void n188_complete(void *context, enum note10_iostorage_read_status status, uint64_t actual)
{
    struct n188_read *s = context;
    ++s->completions;
    s->status = status;
    s->actual = actual;
    s->owner_live = s->fd >= 0 && !s->returned && s->reads == 1 && s->preads == 1;
}

struct n188_denial { unsigned reads, completions; };

static bool n188_deny_read(void *context, uint64_t offset, uint64_t length, uint64_t *actual)
{
    struct n188_denial *s = context;
    (void)offset; (void)length;
    ++s->reads; *actual = 0;
    return false;
}

static void n188_deny_complete(void *context, enum note10_iostorage_read_status status, uint64_t actual)
{
    struct n188_denial *s = context;
    (void)status; (void)actual;
    ++s->completions;
}

static char *n188_append(char *p, char *limit, const char *text)
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

static char *n188_number(char *p, char *limit, const char *key, n188_word value)
{
    char digits[21];
    unsigned count = 0;
    uint64_t magnitude = value < 0 ? (uint64_t)(-(value + 1)) + 1 : (uint64_t)value;
    p = n188_append(p, limit, key);
    if (value < 0)
        p = n188_append(p, limit, "-");
    do {
        digits[count++] = (char)('0' + magnitude % 10);
        magnitude /= 10;
    } while (magnitude);
    while (count) {
        char digit[2];
        digit[0] = digits[--count]; digit[1] = 0;
        p = n188_append(p, limit, digit);
    }
    return p;
}

static void n188_observe(n188_word argc, const char *argument)
{
    const char *next;
    struct n188_read s;
    struct n188_denial denial = {0, 0};
    char frame[N188_FRAME_MAX], *p, *limit = frame + sizeof(frame);
    n188_word kmsg;
    unsigned eh = 0, ps = 0, pn = 0, pt = 0, pf = 0, i;
    uint32_t fnv = 0;
    bool positive, denial_attempted = false, denial_admitted = false, denied, passed;

    if (argc != 2)
        return;
    next = n188_id(n188_tag(argument, "id="), N188_BUILD_ID);
    next = n188_id(n188_tag(next, " boot="), 0);
    next = n188_id(n188_tag(next, " cycle="), 0);
    next = n188_tag(next, " route=builtin arm=0");
    if (!next || *next)
        return;

    s.fd = -1; s.open_rc = -61; s.extent = -1; s.pread_return = -61; s.close_rc = -61;
    s.reads = 0; s.completions = 0; s.preads = 0; s.actual = 0;
    s.offset = 0; s.pread_offset = 0;
    s.status = NOTE10_IOSTORAGE_READ_ERROR;
    s.admitted = false; s.returned = false; s.owner_live = false; s.returned_before_close = false;
    s.fd = n188_syscall(N188_OPENAT, N188_AT_FDCWD, (n188_word)"/init", N188_READ_FLAGS, 0, 0);
    s.open_rc = s.fd < 0 ? s.fd : 0;
    if (s.fd >= 0) {
        s.extent = n188_syscall(N188_LSEEK, s.fd, 0, N188_SEEK_END, 0, 0);
        if (s.extent >= N188_OFFSET + N188_BYTES && s.extent <= N188_ELF_MAX && s.extent % N188_BLOCK == 0) {
            s.admitted = note10_iostorage_read_request((uint64_t)s.extent, N188_BLOCK, N188_LBA, N188_COUNT,
                N188_BYTES, NOTE10_IOSTORAGE_READ_DIRECTION, n188_backing_read, n188_complete, &s);
            s.returned = true;
            denial_attempted = true;
            denial_admitted = note10_iostorage_read_request((uint64_t)s.extent, N188_BLOCK,
                N188_LBA, N188_COUNT, N188_BYTES - 1, NOTE10_IOSTORAGE_READ_DIRECTION,
                n188_deny_read, n188_deny_complete, &denial);
        }
        s.returned_before_close = s.returned;
        s.close_rc = n188_syscall(N188_CLOSE, s.fd, 0, 0, 0, 0);
        s.fd = -1;
    }
    if (s.pread_return == N188_BYTES && s.actual == N188_BYTES && s.status == NOTE10_IOSTORAGE_READ_OK) {
        eh = (unsigned)s.bytes[4] | (unsigned)s.bytes[5] << 8;
        ps = (unsigned)s.bytes[6] | (unsigned)s.bytes[7] << 8;
        pn = (unsigned)s.bytes[8] | (unsigned)s.bytes[9] << 8;
        pt = (unsigned)s.bytes[16] | (unsigned)s.bytes[17] << 8 |
            (unsigned)s.bytes[18] << 16 | (unsigned)s.bytes[19] << 24;
        pf = (unsigned)s.bytes[20] | (unsigned)s.bytes[21] << 8 |
            (unsigned)s.bytes[22] << 16 | (unsigned)s.bytes[23] << 24;
        fnv = 2166136261U;
        for (i = 0; i < N188_BYTES; ++i)
            fnv = (fnv ^ s.bytes[i]) * 16777619U;
    }
    positive = s.open_rc == 0 && s.admitted && s.reads == 1 && s.completions == 1 && s.preads == 1 &&
        s.offset == N188_OFFSET && s.pread_offset == N188_OFFSET && s.pread_return == N188_BYTES &&
        s.status == NOTE10_IOSTORAGE_READ_OK && s.actual == N188_BYTES && s.owner_live &&
        s.returned_before_close && s.close_rc == 0 && eh == 64 && ps == 56 && pn >= 1 && pn <= 16;
    denied = denial_attempted && !denial_admitted && denial.reads == 0 && denial.completions == 0;
    passed = positive && denied;
    p = n188_append(frame, limit, "<6>N188READ1 ");
    p = n188_append(p, limit, argument);
    p = n188_append(p, limit, " entered=1");
    p = n188_number(p, limit, " op=", s.open_rc);
    p = n188_number(p, limit, " ext=", s.extent);
    p = n188_number(p, limit, " adm=", s.admitted);
    p = n188_number(p, limit, " rcb=", s.reads);
    p = n188_number(p, limit, " ccb=", s.completions);
    p = n188_number(p, limit, " pc=", s.preads);
    p = n188_number(p, limit, " pr=", s.pread_return);
    p = n188_number(p, limit, " st=", s.status);
    p = n188_number(p, limit, " n=", (n188_word)s.actual);
    p = n188_number(p, limit, " off=", (n188_word)s.offset);
    p = n188_number(p, limit, " po=", (n188_word)s.pread_offset);
    p = n188_number(p, limit, " live=", s.owner_live);
    p = n188_number(p, limit, " ret=", s.returned_before_close);
    p = n188_number(p, limit, " cl=", s.close_rc);
    p = n188_number(p, limit, " eh=", eh);
    p = n188_number(p, limit, " ps=", ps);
    p = n188_number(p, limit, " pn=", pn);
    p = n188_number(p, limit, " pt=", pt);
    p = n188_number(p, limit, " pf=", pf);
    p = n188_number(p, limit, " fnv=", fnv);
    p = n188_number(p, limit, " ok=", positive);
    p = n188_number(p, limit, " da=", denial_admitted);
    p = n188_number(p, limit, " dr=", denial.reads);
    p = n188_number(p, limit, " dc=", denial.completions);
    p = n188_number(p, limit, " dok=", denied);
    p = n188_number(p, limit, " passed=", passed);
    p = n188_append(p, limit, "\n");
    if (!p)
        return;
    kmsg = n188_syscall(N188_OPENAT, N188_AT_FDCWD, (n188_word)"/dev/kmsg", N188_KMSG_FLAGS, 0, 0);
    if (kmsg >= 0) {
        n188_syscall(N188_WRITE, kmsg, (n188_word)frame, p - frame, 0, 0);
        n188_syscall(N188_CLOSE, kmsg, 0, 0, 0, 0);
    }
}

static void n188_wait(void)
{
    n188_syscall(N188_PPOLL, 0, 0, 0, 0, 0);
}

#ifndef N188_HOST_FIXTURE
__attribute__((used, noreturn)) static void n188_start(const n188_word *stack)
{
    n188_observe(stack[0], stack[0] == 2 ? (const char *)stack[2] : 0);
    for (;;)
        n188_wait();
}
__asm__(".text\n.global _start\n.type _start,%function\n_start:\n"
        "mov x0, sp\nb n188_start\n.size _start, .-_start\n");
#endif
