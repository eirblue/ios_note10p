#include <stdint.h>
#include <stdio.h>
#include "note10_user_instruction_fetch.h"
#include <arm64/proc_reg.h>

static struct n10_user_instruction supplied;
static unsigned fetch_calls, user_calls, kernel_calls;
static uint32_t legacy_word;

struct n10_user_instruction n10_fetch_user_instruction(const arm_saved_state_t *state)
{
    (void)state;
    ++fetch_calls;
    return supplied;
}

static int copyin(user_addr_t address, void *destination, size_t length)
{
    (void)address;
    ++user_calls;
    if (length != 4) return -1;
    *(uint32_t *)destination = legacy_word;
    return 0;
}

static int copyin_kern(user_addr_t address, void *destination, size_t length)
{
    (void)address;
    ++kernel_calls;
    if (length != 4) return -1;
    *(uint32_t *)destination = legacy_word;
    return 0;
}

#include "user-exception-policy.h"

static int check(uint32_t mode, int enabled, enum n10_user_fetch_status status,
                 uint32_t supplied_word, uint32_t expected, unsigned fetch, unsigned user, unsigned kernel)
{
    arm_saved_state_t state = {0};
    if (mode & PSR64_MODE_RW_32) {
        state.ash.flavor = ARM_SAVED_STATE32;
        state.ash.count = ARM_SAVED_STATE32_COUNT;
        state.ss_32.cpsr = mode;
        state.ss_32.pc = 16;
    } else {
        state.ash.flavor = ARM_SAVED_STATE64;
        state.ash.count = ARM_SAVED_STATE64_COUNT;
        state.ss_64.cpsr = mode;
        state.ss_64.pc = 16;
    }
    supplied = (struct n10_user_instruction){status, supplied_word, -1};
    fetch_calls = user_calls = kernel_calls = 0;
    legacy_word = UINT32_C(0x11223344);
    uint32_t word = enabled ? n198_enabled(&state) : n198_disabled(&state);
    return word == expected && fetch_calls == fetch && user_calls == user && kernel_calls == kernel;
}

int main(void)
{
    unsigned cases = 0;
#define CHECK(...) do { if (!check(__VA_ARGS__)) return 1; ++cases; } while (0)
    CHECK(PSR64_MODE_EL0, 1, N10_USER_FETCH_OK, UINT32_C(0xaabbccdd), UINT32_C(0xaabbccdd), 1, 0, 0);
    CHECK(PSR64_MODE_EL0, 1, N10_USER_FETCH_OK, 0, 0, 1, 0, 0);
    CHECK(PSR64_MODE_EL0, 1, N10_USER_FETCH_BAD_STATE, UINT32_MAX, 0, 1, 0, 0);
    CHECK(PSR64_MODE_EL0, 1, N10_USER_FETCH_BAD_PC, UINT32_MAX, 0, 1, 0, 0);
    CHECK(PSR64_MODE_EL0, 1, N10_USER_FETCH_COPY_ERROR, UINT32_MAX, 0, 1, 0, 0);
    printf("N198 USER64 cases=%u\n", cases);
    CHECK(PSR64_MODE_RW_32, 1, N10_USER_FETCH_OK, UINT32_MAX, UINT32_C(0x11223344), 0, 1, 0);
    CHECK(PSR64_MODE_EL1, 1, N10_USER_FETCH_OK, UINT32_MAX, UINT32_C(0x11223344), 0, 0, 1);
    CHECK(PSR64_MODE_EL0, 0, N10_USER_FETCH_OK, UINT32_MAX, UINT32_C(0x11223344), 0, 1, 0);
    printf("N198 ROUTES cases=%u\n", cases - 5);
    return cases == 8 ? 0 : 1;
}
