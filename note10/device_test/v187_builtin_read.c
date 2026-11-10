/* SPDX-License-Identifier: GPL-2.0-only */
/* RAM-rootfs PID1 file adapter; no device file or native kernel handoff. */
#include <stdint.h>
#include "note10_iostorage_read_request.h"
#include "note10_iostorage_read_range.h"

#ifndef N187_BUILD_ID
#error N187_BUILD_ID must bind the reviewed Image
#endif
typedef intptr_t n187_word;
_Static_assert(sizeof(n187_word) == 8 && sizeof(uint64_t) == 8, "64-bit ABI required");
_Static_assert(sizeof(N187_BUILD_ID) == 33, "32 hex build identity required");
enum {
    N187_OPENAT = 56, N187_CLOSE = 57, N187_LSEEK = 62,
    N187_WRITE = 64, N187_PREAD64 = 67, N187_PPOLL = 73,
    N187_AT_FDCWD = -100, N187_SEEK_END = 2,
    N187_READ_FLAGS = 00004000 | 0100000 | 02000000,
    N187_KMSG_FLAGS = 00000001 | 00004000 | 0100000 | 02000000,
    N187_BLOCK = 8, N187_LBA = 2, N187_COUNT = 8, N187_OFFSET = 16, N187_BYTES = 64, N187_ELF_MAX = 1048576, N187_FRAME_MAX = 512
};
#ifdef N187_HOST_FIXTURE
static n187_word n187_syscall(n187_word, n187_word, n187_word, n187_word, n187_word, n187_word);
#else
#if !defined(__aarch64__) || !defined(__linux__)
#error native PID1 requires Linux AArch64
#endif
static n187_word n187_syscall(n187_word number, n187_word a0, n187_word a1,
                             n187_word a2, n187_word a3, n187_word a4)
{
    register n187_word x0 __asm__("x0") = a0;
    register n187_word x1 __asm__("x1") = a1;
    register n187_word x2 __asm__("x2") = a2;
    register n187_word x3 __asm__("x3") = a3;
    register n187_word x4 __asm__("x4") = a4;
    register n187_word x8 __asm__("x8") = number;
    __asm__ volatile("svc 0" : "+r"(x0) : "r"(x1), "r"(x2), "r"(x3), "r"(x4), "r"(x8) : "memory");
    return x0;
}
#endif
static const char n187_elf_identity[] __attribute__((used)) = "N10MININIT2:N187READ1";

static const char *n187_tag(const char *value, const char *tag)
{
    if (!value)
        return 0;
    while (*tag)
        if (*value++ != *tag++)
            return 0;
    return value;
}

static const char *n187_id(const char *value, const char *expected)
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

struct n187_read {
    n187_word fd, open_rc, extent, pread_return, close_rc;
    uint64_t offset, pread_offset;
    unsigned reads, completions, preads;
    uint64_t actual;
    enum note10_iostorage_read_status status;
    bool admitted, returned, owner_live, returned_before_close;
    unsigned char bytes[N187_BYTES];
};

static bool n187_backing_read(void *context, uint64_t offset, uint64_t length, uint64_t *actual)
{
    struct n187_read *s = context;
    ++s->reads;
    if (s->reads != 1 || s->fd < 0 || s->returned || offset != N187_OFFSET || length != N187_BYTES)
        return false;
    s->offset = offset;
    s->pread_offset = offset;
    ++s->preads;
    s->pread_return = n187_syscall(N187_PREAD64, s->fd, (n187_word)s->bytes, N187_BYTES, (n187_word)s->pread_offset, 0);
    *actual = s->pread_return < 0 ? 0 : (uint64_t)s->pread_return;
    return s->pread_return >= 0;
}

static void n187_complete(void *context, enum note10_iostorage_read_status status, uint64_t actual)
{
    struct n187_read *s = context;
    ++s->completions;
    s->status = status;
    s->actual = actual;
    s->owner_live = s->fd >= 0 && !s->returned && s->reads == 1 && s->preads == 1;
}

struct n187_denial { unsigned reads, completions; };

static bool n187_deny_read(void *context, uint64_t offset, uint64_t length, uint64_t *actual)
{
    struct n187_denial *s = context;
    (void)offset; (void)length;
    ++s->reads; *actual = 0;
    return false;
}

static void n187_deny_complete(void *context, enum note10_iostorage_read_status status, uint64_t actual)
{
    struct n187_denial *s = context;
    (void)status; (void)actual;
    ++s->completions;
}

static char *n187_append(char *p, char *limit, const char *text)
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

static char *n187_number(char *p, char *limit, const char *key, n187_word value)
{
    char digits[21];
    unsigned count = 0;
    uint64_t magnitude = value < 0 ? (uint64_t)(-(value + 1)) + 1 : (uint64_t)value;
    p = n187_append(p, limit, key);
    if (value < 0)
        p = n187_append(p, limit, "-");
    do {
        digits[count++] = (char)('0' + magnitude % 10);
        magnitude /= 10;
    } while (magnitude);
    while (count) {
        char digit[2];
        digit[0] = digits[--count]; digit[1] = 0;
        p = n187_append(p, limit, digit);
    }
    return p;
}

static void n187_observe(n187_word argc, const char *argument)
{
    const char *next;
    struct n187_read s;
    struct n187_denial denial = {0, 0};
    char frame[N187_FRAME_MAX], *p, *limit = frame + sizeof(frame);
    n187_word kmsg;
    unsigned et = 0, em = 0, ev = 0;
    bool positive, denial_attempted = false, denial_admitted = false, denied, passed;

    if (argc != 2)
        return;
    next = n187_id(n187_tag(argument, "id="), N187_BUILD_ID);
    next = n187_id(n187_tag(next, " boot="), 0);
    next = n187_id(n187_tag(next, " cycle="), 0);
    next = n187_tag(next, " route=builtin arm=0");
    if (!next || *next)
        return;

    s.fd = -1; s.open_rc = -61; s.extent = -1; s.pread_return = -61; s.close_rc = -61;
    s.reads = 0; s.completions = 0; s.preads = 0; s.actual = 0;
    s.offset = 0; s.pread_offset = 0;
    s.status = NOTE10_IOSTORAGE_READ_ERROR;
    s.admitted = false; s.returned = false; s.owner_live = false; s.returned_before_close = false;
    s.fd = n187_syscall(N187_OPENAT, N187_AT_FDCWD, (n187_word)"/init", N187_READ_FLAGS, 0, 0);
    s.open_rc = s.fd < 0 ? s.fd : 0;
    if (s.fd >= 0) {
        s.extent = n187_syscall(N187_LSEEK, s.fd, 0, N187_SEEK_END, 0, 0);
        if (s.extent >= N187_OFFSET + N187_BYTES && s.extent <= N187_ELF_MAX && s.extent % N187_BLOCK == 0) {
            s.admitted = note10_iostorage_read_request((uint64_t)s.extent, N187_BLOCK, N187_LBA, N187_COUNT,
                N187_BYTES, NOTE10_IOSTORAGE_READ_DIRECTION, n187_backing_read, n187_complete, &s);
            s.returned = true;
            denial_attempted = true;
            denial_admitted = note10_iostorage_read_request((uint64_t)s.extent, N187_BLOCK,
                (uint64_t)s.extent / N187_BLOCK, 1, N187_BLOCK, NOTE10_IOSTORAGE_READ_DIRECTION,
                n187_deny_read, n187_deny_complete, &denial);
        }
        s.returned_before_close = s.returned;
        s.close_rc = n187_syscall(N187_CLOSE, s.fd, 0, 0, 0, 0);
        s.fd = -1;
    }
    if (s.pread_return == N187_BYTES && s.actual == N187_BYTES && s.status == NOTE10_IOSTORAGE_READ_OK) {
        et = (unsigned)s.bytes[0] | (unsigned)s.bytes[1] << 8;
        em = (unsigned)s.bytes[2] | (unsigned)s.bytes[3] << 8;
        ev = (unsigned)s.bytes[4] | (unsigned)s.bytes[5] << 8 |
            (unsigned)s.bytes[6] << 16 | (unsigned)s.bytes[7] << 24;
    }
    positive = s.open_rc == 0 && s.admitted && s.reads == 1 && s.completions == 1 && s.preads == 1 &&
        s.offset == N187_OFFSET && s.pread_offset == N187_OFFSET && s.pread_return == N187_BYTES &&
        s.status == NOTE10_IOSTORAGE_READ_OK && s.actual == N187_BYTES && s.owner_live &&
        s.returned_before_close && s.close_rc == 0 && et == 2 && em == 183 && ev == 1;
    denied = denial_attempted && !denial_admitted && denial.reads == 0 && denial.completions == 0;
    passed = positive && denied;
    p = n187_append(frame, limit, "<6>N187READ1 ");
    p = n187_append(p, limit, argument);
    p = n187_append(p, limit, " entered=1");
    p = n187_number(p, limit, " op=", s.open_rc);
    p = n187_number(p, limit, " ext=", s.extent);
    p = n187_number(p, limit, " adm=", s.admitted);
    p = n187_number(p, limit, " rcb=", s.reads);
    p = n187_number(p, limit, " ccb=", s.completions);
    p = n187_number(p, limit, " pc=", s.preads);
    p = n187_number(p, limit, " pr=", s.pread_return);
    p = n187_number(p, limit, " st=", s.status);
    p = n187_number(p, limit, " n=", (n187_word)s.actual);
    p = n187_number(p, limit, " off=", (n187_word)s.offset);
    p = n187_number(p, limit, " po=", (n187_word)s.pread_offset);
    p = n187_number(p, limit, " live=", s.owner_live);
    p = n187_number(p, limit, " ret=", s.returned_before_close);
    p = n187_number(p, limit, " cl=", s.close_rc);
    p = n187_number(p, limit, " et=", et);
    p = n187_number(p, limit, " em=", em);
    p = n187_number(p, limit, " ev=", ev);
    p = n187_number(p, limit, " ok=", positive);
    p = n187_number(p, limit, " da=", denial_admitted);
    p = n187_number(p, limit, " dr=", denial.reads);
    p = n187_number(p, limit, " dc=", denial.completions);
    p = n187_number(p, limit, " dok=", denied);
    p = n187_number(p, limit, " passed=", passed);
    p = n187_append(p, limit, "\n");
    if (!p)
        return;
    kmsg = n187_syscall(N187_OPENAT, N187_AT_FDCWD, (n187_word)"/dev/kmsg", N187_KMSG_FLAGS, 0, 0);
    if (kmsg >= 0) {
        n187_syscall(N187_WRITE, kmsg, (n187_word)frame, p - frame, 0, 0);
        n187_syscall(N187_CLOSE, kmsg, 0, 0, 0, 0);
    }
}

static void n187_wait(void)
{
    n187_syscall(N187_PPOLL, 0, 0, 0, 0, 0);
}

#ifndef N187_HOST_FIXTURE
__attribute__((used, noreturn)) static void n187_start(const n187_word *stack)
{
    n187_observe(stack[0], stack[0] == 2 ? (const char *)stack[2] : 0);
    for (;;)
        n187_wait();
}
__asm__(".text\n.global _start\n.type _start,%function\n_start:\n"
        "mov x0, sp\nb n187_start\n.size _start, .-_start\n");
#endif
