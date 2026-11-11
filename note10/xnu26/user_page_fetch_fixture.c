/* Controlled PC copyin service for the unchanged instruction-fetch consumer. */
#include <errno.h>
#include <inttypes.h>
#include <stdio.h>
#include <string.h>
#include <sys/types.h>
#include <arm64/proc_reg.h>
#include <libkern/copyio.h>
#include "note10_user_instruction_fetch.h"
#include "note10_user_page_read.h"
#if defined(_WIN32)
#include <fcntl.h>
#include <io.h>
#endif

struct backing {
    const unsigned char *bytes;
    size_t size;
    unsigned calls;
    uint64_t last_offset;
    int error;
    int partial;
};

static int task_token, map_token, other_task, other_map;
static const struct n10_user_page_source *active_source;
static enum n10_user_page_status last_gate;
static unsigned service_calls, synthetic_cases;
static size_t service_bytes;

static int backing_read(void *context, uint64_t offset, unsigned char bytes[4])
{
    struct backing *backing = context;
    ++backing->calls;
    backing->last_offset = offset;
    if (backing->size < 4 || offset > backing->size - 4)
        return EFAULT;
    if (backing->error) {
        if (backing->partial)
            memcpy(bytes, backing->bytes + offset, 2);
        return backing->error;
    }
    memcpy(bytes, backing->bytes + offset, 4);
    return 0;
}

int copyin(const user_addr_t address, void *destination, size_t length)
{
    ++service_calls;
    service_bytes = length;
    last_gate = n10_read_user_page_instruction(active_source, (uint64_t)address, destination, length);
    return last_gate == N10_USER_PAGE_OK ? 0 : EFAULT;
}

static struct n10_user_page_source source_for(struct backing *backing)
{
    struct n10_user_page_source source = {
        .expected_task = &task_token, .expected_map = &map_token,
        .current_task = &task_token, .current_map = &map_token,
        .page_address = UINT64_C(0x4000), .page_bytes = N10_USER_PAGE_BYTES,
        .maxprot = 5, .initprot = 5, .read4 = backing_read, .context = backing
    };
    return source;
}

static arm_saved_state_t user_frame(uint64_t address)
{
    arm_saved_state_t frame;
    memset(&frame, 0, sizeof(frame));
    frame.ash.flavor = ARM_SAVED_STATE64;
    frame.ash.count = ARM_SAVED_STATE64_COUNT;
    frame.ss_64.pc = address;
    frame.ss_64.cpsr = PSR64_MODE_EL0;
    return frame;
}

static void reset(struct backing *backing)
{
    service_calls = 0;
    service_bytes = 0;
    last_gate = N10_USER_PAGE_BAD_REQUEST;
    backing->calls = 0;
    backing->last_offset = UINT64_MAX;
}

static int check_fetch(const struct n10_user_page_source *source, struct backing *backing,
                       uint64_t address, enum n10_user_page_status expected,
                       unsigned reads, uint32_t word)
{
    arm_saved_state_t frame = user_frame(address);
    arm_saved_state_t before = frame;
    reset(backing);
    active_source = source;
    struct n10_user_instruction fetched = n10_fetch_user_instruction(&frame);
    ++synthetic_cases;
    return last_gate == expected && service_calls == 1 && service_bytes == 4 &&
           backing->calls == reads && memcmp(&frame, &before, sizeof(frame)) == 0 &&
           fetched.status == (expected == N10_USER_PAGE_OK ? N10_USER_FETCH_OK : N10_USER_FETCH_COPY_ERROR) &&
           fetched.copy_error == (expected == N10_USER_PAGE_OK ? 0 : EFAULT) && fetched.word == word;
}

static int check_gate(const struct n10_user_page_source *source, struct backing *backing,
                      uint64_t address, size_t length, int missing_destination,
                      enum n10_user_page_status expected)
{
    unsigned char output[4] = {0xa5, 0xa5, 0xa5, 0xa5};
    const unsigned char unchanged[4] = {0xa5, 0xa5, 0xa5, 0xa5};
    reset(backing);
    enum n10_user_page_status status = n10_read_user_page_instruction(source, address,
        missing_destination ? NULL : output, length);
    ++synthetic_cases;
    return status == expected &&
           backing->calls == (expected == N10_USER_PAGE_READ_FAILED ? 1u : 0u) && service_calls == 0 &&
           memcmp(output, unchanged, sizeof(output)) == 0;
}

#define CHECK(value) do { if (!(value)) { fprintf(stderr, "new case at line %d failed\n", __LINE__); return 0; } } while (0)

static int owner_cases(struct backing *backing)
{
    struct n10_user_page_source source = source_for(backing);
    uint64_t address = source.page_address + 8;
    CHECK(check_fetch(NULL, backing, address, N10_USER_PAGE_BAD_OWNER, 0, 0));
    source.expected_task = NULL;
    CHECK(check_fetch(&source, backing, address, N10_USER_PAGE_BAD_OWNER, 0, 0));
    source = source_for(backing);
    source.expected_map = NULL;
    CHECK(check_fetch(&source, backing, address, N10_USER_PAGE_BAD_OWNER, 0, 0));
    source = source_for(backing);
    source.current_task = NULL;
    CHECK(check_fetch(&source, backing, address, N10_USER_PAGE_BAD_OWNER, 0, 0));
    source = source_for(backing);
    source.current_map = NULL;
    CHECK(check_fetch(&source, backing, address, N10_USER_PAGE_BAD_OWNER, 0, 0));
    source = source_for(backing);
    source.current_task = &other_task;
    CHECK(check_fetch(&source, backing, address, N10_USER_PAGE_BAD_OWNER, 0, 0));
    source = source_for(backing);
    source.current_map = &other_map;
    CHECK(check_fetch(&source, backing, address, N10_USER_PAGE_BAD_OWNER, 0, 0));
    return 1;
}

static int request_cases(struct backing *backing)
{
    struct n10_user_page_source source = source_for(backing);
    uint64_t address = source.page_address + 8;
    source.read4 = NULL;
    CHECK(check_gate(&source, backing, address, 4, 0, N10_USER_PAGE_BAD_REQUEST));
    source = source_for(backing);
    CHECK(check_gate(&source, backing, address, 4, 1, N10_USER_PAGE_BAD_REQUEST));
    CHECK(check_gate(&source, backing, address, 2, 0, N10_USER_PAGE_BAD_REQUEST));
    CHECK(check_gate(&source, backing, source.page_address + 1, 4, 0, N10_USER_PAGE_BAD_REQUEST));
    source.page_bytes = 0;
    CHECK(check_gate(&source, backing, address, 4, 0, N10_USER_PAGE_BAD_REQUEST));
    source = source_for(backing);
    source.page_bytes /= 2;
    CHECK(check_gate(&source, backing, address, 4, 0, N10_USER_PAGE_BAD_REQUEST));
    source = source_for(backing);
    source.page_address += 4;
    CHECK(check_gate(&source, backing, address, 4, 0, N10_USER_PAGE_BAD_REQUEST));
    source = source_for(backing);
    source.page_address = UINT64_MAX - N10_USER_PAGE_BYTES + 1;
    CHECK(check_gate(&source, backing, source.page_address, 4, 0, N10_USER_PAGE_BAD_REQUEST));
    source = source_for(backing);
    CHECK(check_gate(&source, backing, source.page_address - 4, 4, 0, N10_USER_PAGE_BAD_REQUEST));
    CHECK(check_gate(&source, backing, source.page_address + N10_USER_PAGE_BYTES, 4, 0, N10_USER_PAGE_BAD_REQUEST));
    source.initprot = 4;
    CHECK(check_gate(&source, backing, address, 4, 0, N10_USER_PAGE_BAD_RIGHTS));
    source.initprot = 1;
    CHECK(check_gate(&source, backing, address, 4, 0, N10_USER_PAGE_BAD_RIGHTS));
    source = source_for(backing);
    source.maxprot = 1;
    CHECK(check_gate(&source, backing, address, 4, 0, N10_USER_PAGE_BAD_RIGHTS));
    source = source_for(backing);
    source.maxprot = 13;
    CHECK(check_gate(&source, backing, address, 4, 0, N10_USER_PAGE_BAD_RIGHTS));
    return 1;
}

static int callback_cases(struct backing *backing)
{
    struct n10_user_page_source source = source_for(backing);
    CHECK(check_fetch(&source, backing, source.page_address + 8, N10_USER_PAGE_OK, 1, UINT32_C(0x44332211)));
    CHECK(check_fetch(&source, backing, source.page_address, N10_USER_PAGE_OK, 1, UINT32_C(0x11111111)));
    CHECK(check_fetch(&source, backing, source.page_address + N10_USER_PAGE_BYTES - 4,
                      N10_USER_PAGE_OK, 1, UINT32_C(0x88776655)));
    backing->error = EFAULT;
    CHECK(check_fetch(&source, backing, source.page_address + 8, N10_USER_PAGE_READ_FAILED, 1, 0));
    backing->partial = 1;
    CHECK(check_fetch(&source, backing, source.page_address + 8, N10_USER_PAGE_READ_FAILED, 1, 0));
    CHECK(check_gate(&source, backing, source.page_address + 8, 4, 0, N10_USER_PAGE_READ_FAILED));
    return 1;
}

static uint64_t little64(const unsigned char *bytes)
{
    uint64_t value = 0;
    for (unsigned index = 0; index < 8; ++index)
        value |= (uint64_t)bytes[index] << (8 * index);
    return value;
}

static uint32_t little32(const unsigned char *bytes)
{
    uint32_t value = 0;
    for (unsigned index = 0; index < 4; ++index)
        value |= (uint32_t)bytes[index] << (8 * index);
    return value;
}

int main(void)
{
#if defined(_WIN32)
    if (_setmode(_fileno(stdin), _O_BINARY) == -1)
        return 1;
#endif
    unsigned char synthetic[N10_USER_PAGE_BYTES];
    memset(synthetic, 0x11, sizeof(synthetic));
    const unsigned char middle[4] = {0x11, 0x22, 0x33, 0x44};
    const unsigned char last[4] = {0x55, 0x66, 0x77, 0x88};
    memcpy(synthetic + 8, middle, 4);
    memcpy(synthetic + sizeof(synthetic) - 4, last, 4);
    struct backing test = {.bytes = synthetic, .size = sizeof(synthetic)};
    if (!owner_cases(&test) || !request_cases(&test) || !callback_cases(&test) || synthetic_cases != 27)
        return 1;

    unsigned char wire[24], page[N10_USER_PAGE_BYTES];
    if (fread(wire, 1, sizeof(wire), stdin) != sizeof(wire) ||
        fread(page, 1, sizeof(page), stdin) != sizeof(page))
        return 1;
    struct backing actual = {.bytes = page, .size = sizeof(page)};
    struct n10_user_page_source source = source_for(&actual);
    source.page_address = little64(wire);
    source.initprot = little32(wire + 16);
    source.maxprot = little32(wire + 20);
    arm_saved_state_t frame = user_frame(little64(wire + 8));
    arm_saved_state_t before = frame;
    reset(&actual);
    active_source = &source;
    struct n10_user_instruction fetched = n10_fetch_user_instruction(&frame);
    if (fetched.status != N10_USER_FETCH_OK || fetched.copy_error != 0 || last_gate != N10_USER_PAGE_OK ||
        service_calls != 1 || service_bytes != 4 || actual.calls != 1 ||
        memcmp(&frame, &before, sizeof(frame)) != 0)
        return 1;
    printf("{\"synthetic_groups\":3,\"synthetic_cases\":%u,\"owner_denial_cases\":7,"
           "\"owner_denial_service_calls_per_case\":1,\"owner_denial_backing_calls_per_case\":0,"
           "\"fetch_status\":%u,\"copy_error\":%d,\"gate_status\":%u,\"service_calls\":%u,"
           "\"backing_calls\":%u,\"backing_bytes\":4,\"relative_offset\":%" PRIu64 ","
           "\"frame_unchanged\":true,\"word\":%" PRIu32 "}\n",
           synthetic_cases, (unsigned)fetched.status, fetched.copy_error, (unsigned)last_gate,
           service_calls, actual.calls, actual.last_offset, fetched.word);
    return 0;
}
