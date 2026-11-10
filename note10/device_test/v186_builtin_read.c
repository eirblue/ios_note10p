/* SPDX-License-Identifier: GPL-2.0-only */
/* RAM-rootfs PID1 file adapter; no device file or native kernel handoff. */
#include <stdint.h>
#include "note10_iostorage_read_request.h"
#include "note10_iostorage_read_range.h"

#ifndef N186_BUILD_ID
#error N186_BUILD_ID must bind the reviewed Image
#endif
typedef intptr_t n186_word;
_Static_assert(sizeof(n186_word) == 8 && sizeof(uint64_t) == 8, "64-bit ABI required");
_Static_assert(sizeof(N186_BUILD_ID) == 33, "32 hex build identity required");
enum {
    N186_OPENAT = 56, N186_CLOSE = 57, N186_LSEEK = 62,
    N186_WRITE = 64, N186_PREAD64 = 67, N186_PPOLL = 73,
    N186_AT_FDCWD = -100, N186_SEEK_END = 2,
    N186_READ_FLAGS = 00004000 | 0100000 | 02000000,
    N186_KMSG_FLAGS = 00000001 | 00004000 | 0100000 | 02000000,
    N186_BYTES = 64, N186_ELF_MAX = 1048576, N186_FRAME_MAX = 512
};
#ifdef N186_HOST_FIXTURE
static n186_word n186_syscall(n186_word, n186_word, n186_word, n186_word, n186_word, n186_word);
#else
#if !defined(__aarch64__) || !defined(__linux__)
#error native PID1 requires Linux AArch64
#endif
static n186_word n186_syscall(n186_word number, n186_word a0, n186_word a1,
                             n186_word a2, n186_word a3, n186_word a4)
{
    register n186_word x0 __asm__("x0") = a0;
    register n186_word x1 __asm__("x1") = a1;
    register n186_word x2 __asm__("x2") = a2;
    register n186_word x3 __asm__("x3") = a3;
    register n186_word x4 __asm__("x4") = a4;
    register n186_word x8 __asm__("x8") = number;
    __asm__ volatile("svc 0" : "+r"(x0) : "r"(x1), "r"(x2), "r"(x3), "r"(x4), "r"(x8) : "memory");
    return x0;
}
#endif
static const char n186_elf_identity[] __attribute__((used)) = "N10MININIT2:N186READ1";

static const char *n186_tag(const char *value, const char *tag)
{
    if (!value)
        return 0;
    while (*tag)
        if (*value++ != *tag++)
            return 0;
    return value;
}

static const char *n186_id(const char *value, const char *expected)
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

struct n186_read {
    n186_word fd, open_rc, extent, pread_return, close_rc;
    unsigned reads, completions, preads;
    uint64_t actual;
    enum note10_iostorage_read_status status;
    bool admitted, returned, owner_live, returned_before_close;
    unsigned char bytes[N186_BYTES];
};

static bool n186_backing_read(void *context, uint64_t offset, uint64_t length, uint64_t *actual)
{
    struct n186_read *s = context;
    ++s->reads;
    if (s->reads != 1 || s->fd < 0 || s->returned || offset != 0 || length != N186_BYTES)
        return false;
    ++s->preads;
    s->pread_return = n186_syscall(N186_PREAD64, s->fd, (n186_word)s->bytes, N186_BYTES, 0, 0);
    *actual = s->pread_return < 0 ? 0 : (uint64_t)s->pread_return;
    return s->pread_return >= 0;
}

static void n186_complete(void *context, enum note10_iostorage_read_status status, uint64_t actual)
{
    struct n186_read *s = context;
    ++s->completions;
    s->status = status;
    s->actual = actual;
    s->owner_live = s->fd >= 0 && !s->returned && s->reads == 1 && s->preads == 1;
}

static char *n186_append(char *p, char *limit, const char *text)
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

static char *n186_number(char *p, char *limit, const char *key, n186_word value)
{
    char digits[21];
    unsigned count = 0;
    uint64_t magnitude = value < 0 ? (uint64_t)(-(value + 1)) + 1 : (uint64_t)value;
    p = n186_append(p, limit, key);
    if (value < 0)
        p = n186_append(p, limit, "-");
    do {
        digits[count++] = (char)('0' + magnitude % 10);
        magnitude /= 10;
    } while (magnitude);
    while (count) {
        char digit[2];
        digit[0] = digits[--count]; digit[1] = 0;
        p = n186_append(p, limit, digit);
    }
    return p;
}

static void n186_observe(n186_word argc, const char *argument)
{
    const char *next;
    struct n186_read s;
    char frame[N186_FRAME_MAX], *p, *limit = frame + sizeof(frame);
    n186_word kmsg;
    bool elf = false, arm64 = false, passed;

    if (argc != 2)
        return;
    next = n186_id(n186_tag(argument, "id="), N186_BUILD_ID);
    next = n186_id(n186_tag(next, " boot="), 0);
    next = n186_id(n186_tag(next, " cycle="), 0);
    next = n186_tag(next, " route=builtin arm=0");
    if (!next || *next)
        return;

    s.fd = -1; s.open_rc = -61; s.extent = -1; s.pread_return = -61; s.close_rc = -61;
    s.reads = 0; s.completions = 0; s.preads = 0; s.actual = 0;
    s.status = NOTE10_IOSTORAGE_READ_ERROR;
    s.admitted = false; s.returned = false; s.owner_live = false; s.returned_before_close = false;
    s.fd = n186_syscall(N186_OPENAT, N186_AT_FDCWD, (n186_word)"/init", N186_READ_FLAGS, 0, 0);
    s.open_rc = s.fd < 0 ? s.fd : 0;
    if (s.fd >= 0) {
        s.extent = n186_syscall(N186_LSEEK, s.fd, 0, N186_SEEK_END, 0, 0);
        if (s.extent >= N186_BYTES && s.extent <= N186_ELF_MAX) {
            s.admitted = note10_iostorage_read_request((uint64_t)s.extent, 1, 0, N186_BYTES,
                N186_BYTES, NOTE10_IOSTORAGE_READ_DIRECTION, n186_backing_read, n186_complete, &s);
            s.returned = true;
        }
        s.returned_before_close = s.returned;
        s.close_rc = n186_syscall(N186_CLOSE, s.fd, 0, 0, 0, 0);
        s.fd = -1;
    }
    if (s.pread_return == N186_BYTES && s.actual == N186_BYTES && s.status == NOTE10_IOSTORAGE_READ_OK) {
        elf = s.bytes[0] == 0x7f && s.bytes[1] == 'E' && s.bytes[2] == 'L' && s.bytes[3] == 'F' &&
            s.bytes[4] == 2 && s.bytes[5] == 1 && s.bytes[6] == 1 && s.bytes[16] == 2 && s.bytes[17] == 0;
        arm64 = elf && s.bytes[18] == 183 && s.bytes[19] == 0;
    }
    passed = s.open_rc == 0 && s.admitted && s.reads == 1 && s.completions == 1 && s.preads == 1 &&
        s.pread_return == N186_BYTES && s.status == NOTE10_IOSTORAGE_READ_OK && s.actual == N186_BYTES &&
        s.owner_live && s.returned_before_close && s.close_rc == 0 && elf && arm64;
    p = n186_append(frame, limit, "<6>N186READ1 ");
    p = n186_append(p, limit, argument);
    p = n186_append(p, limit, " entered=1");
    p = n186_number(p, limit, " open_rc=", s.open_rc);
    p = n186_number(p, limit, " extent=", s.extent);
    p = n186_number(p, limit, " admitted=", s.admitted);
    p = n186_number(p, limit, " read_callbacks=", s.reads);
    p = n186_number(p, limit, " completion_callbacks=", s.completions);
    p = n186_number(p, limit, " pread64_calls=", s.preads);
    p = n186_number(p, limit, " pread64_return=", s.pread_return);
    p = n186_number(p, limit, " completion_status=", s.status);
    p = n186_number(p, limit, " completed_bytes=", (n186_word)s.actual);
    p = n186_number(p, limit, " owner_live_at_completion=", s.owner_live);
    p = n186_number(p, limit, " returned_before_close=", s.returned_before_close);
    p = n186_number(p, limit, " close_rc=", s.close_rc);
    p = n186_number(p, limit, " header_elf64le=", elf);
    p = n186_number(p, limit, " header_aarch64=", arm64);
    p = n186_number(p, limit, " passed=", passed);
    p = n186_append(p, limit, "\n");
    if (!p)
        return;
    kmsg = n186_syscall(N186_OPENAT, N186_AT_FDCWD, (n186_word)"/dev/kmsg", N186_KMSG_FLAGS, 0, 0);
    if (kmsg >= 0) {
        n186_syscall(N186_WRITE, kmsg, (n186_word)frame, p - frame, 0, 0);
        n186_syscall(N186_CLOSE, kmsg, 0, 0, 0, 0);
    }
}

static void n186_wait(void)
{
    n186_syscall(N186_PPOLL, 0, 0, 0, 0, 0);
}

#ifndef N186_HOST_FIXTURE
__attribute__((used, noreturn)) static void n186_start(const n186_word *stack)
{
    n186_observe(stack[0], stack[0] == 2 ? (const char *)stack[2] : 0);
    for (;;)
        n186_wait();
}
__asm__(".text\n.global _start\n.type _start,%function\n_start:\n"
        "mov x0, sp\nb n186_start\n.size _start, .-_start\n");
#endif
