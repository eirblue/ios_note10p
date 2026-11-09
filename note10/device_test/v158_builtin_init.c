/* SPDX-License-Identifier: GPL-2.0-only */
/* Freestanding Linux PID1: one kmsg entry record, then wait for kernel return. */
#ifndef N158_BUILD_ID
#error N158_BUILD_ID must bind the reviewed Image identity
#endif

typedef __INTPTR_TYPE__ n158_word;
_Static_assert(sizeof(n158_word) == 8, "64-bit ABI required");
_Static_assert(sizeof(N158_BUILD_ID) == 33, "32 hex build identity required");

/* Pinned stock ARM64 UAPI: O_NOFOLLOW differs from asm-generic. */
enum {
    N158_OPENAT = 56, N158_CLOSE = 57, N158_WRITE = 64, N158_PPOLL = 73,
    N158_AT_FDCWD = -100,
    N158_KMSG_FLAGS = 00000001 | 00004000 | 0100000 | 02000000
};

#ifdef N158_HOST_FIXTURE
static n158_word n158_syscall(n158_word, n158_word, n158_word, n158_word, n158_word, n158_word);
#else
#if !defined(__aarch64__) || !defined(__linux__)
#error native PID1 requires Linux AArch64
#endif
static n158_word n158_syscall(n158_word number, n158_word a0, n158_word a1,
                              n158_word a2, n158_word a3, n158_word a4)
{
    register n158_word x0 __asm__("x0") = a0;
    register n158_word x1 __asm__("x1") = a1;
    register n158_word x2 __asm__("x2") = a2;
    register n158_word x3 __asm__("x3") = a3;
    register n158_word x4 __asm__("x4") = a4;
    register n158_word x8 __asm__("x8") = number;
    __asm__ volatile("svc 0" : "+r"(x0) : "r"(x1), "r"(x2), "r"(x3), "r"(x4), "r"(x8) : "memory");
    return x0;
}
#endif

static const char n158_elf_identity[] __attribute__((used)) = "N10MININIT2:N158PID1";

static const char *n158_tag(const char *value, const char *tag)
{
    if (!value)
        return 0;
    while (*tag) {
        if (*value++ != *tag++)
            return 0;
    }
    return value;
}

static const char *n158_id(const char *value, const char *expected)
{
    unsigned int i;
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

static char *n158_append(char *dest, const char *value)
{
    while (*value)
        *dest++ = *value++;
    return dest;
}

static void n158_observe(n158_word argc, const char *argument)
{
    static const char kmsg[] = "/dev/kmsg";
    static const char prefix[] = "<6>N158PID1 ";
    static const char tail[] = " route=builtin arm=0";
    static const char suffix[] = " entered=1\n";
    char frame[sizeof(prefix) + 3 + 32 + 6 + 32 + 7 + 32 + sizeof(tail) + sizeof(suffix)];
    const char *next;
    char *end;
    n158_word fd;

    if (argc != 2)
        return;
    next = n158_id(n158_tag(argument, "id="), N158_BUILD_ID);
    next = n158_id(n158_tag(next, " boot="), 0);
    next = n158_id(n158_tag(next, " cycle="), 0);
    next = n158_tag(next, tail);
    if (!next || *next)
        return;

    fd = n158_syscall(N158_OPENAT, N158_AT_FDCWD, (n158_word)kmsg, N158_KMSG_FLAGS, 0, 0);
    if (fd < 0)
        return;
    end = n158_append(frame, prefix);
    end = n158_append(end, argument);
    end = n158_append(end, suffix);
    n158_syscall(N158_WRITE, fd, (n158_word)frame, end - frame, 0, 0);
    n158_syscall(N158_CLOSE, fd, 0, 0, 0, 0);
}

static void n158_wait(void)
{
    n158_syscall(N158_PPOLL, 0, 0, 0, 0, 0);
}

#ifndef N158_HOST_FIXTURE
__attribute__((used, noreturn)) static void n158_start(const n158_word *stack)
{
    n158_observe(stack[0], stack[0] == 2 ? (const char *)stack[2] : 0);
    for (;;)
        n158_wait();
}

__asm__(".text\n.global _start\n.type _start,%function\n_start:\n"
        "mov x0, sp\nb n158_start\n.size _start, .-_start\n");
#endif
