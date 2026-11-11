/* Controlled producer-to-fetch integration with an explicitly modeled bias. */
#include <errno.h>
#include <inttypes.h>
#include <stdio.h>
#include <string.h>
#include <arm64/proc_reg.h>
#include <libkern/copyio.h>
#include "note10_model_user_entry_frame.h"
#include "note10_user_page_read.h"
#if defined(_WIN32)
#include <fcntl.h>
#include <io.h>
#endif

static int task_token, map_token;
static struct n10_user_page_source source;
static enum n10_user_page_status gate_status;
static unsigned fetch_calls, service_calls, backing_calls, cases;
static size_t service_bytes;
static uint64_t service_address, backing_offset;
static int frame_unchanged;

static void reset(void)
{
    fetch_calls = service_calls = backing_calls = 0;
    service_bytes = 0;
    service_address = backing_offset = UINT64_MAX;
    frame_unchanged = 0;
}

static int read_backing(void *context, uint64_t offset, unsigned char bytes[4])
{
    const unsigned char *page = context;
    ++backing_calls;
    backing_offset = offset;
    if (offset > N10_USER_PAGE_BYTES - 4)
        return EFAULT;
    memcpy(bytes, page + offset, 4);
    return 0;
}

int copyin(const user_addr_t address, void *destination, size_t length)
{
    ++service_calls;
    service_address = (uint64_t)address;
    service_bytes = length;
    gate_status = n10_read_user_page_instruction(&source, (uint64_t)address, destination, length);
    return gate_status == N10_USER_PAGE_OK ? 0 : EFAULT;
}

static enum n10_model_entry_status
produce_then_fetch(const struct n10_model_user_entry_request *request,
                   struct n10_model_user_entry_frame *prepared,
                   struct n10_user_instruction *fetched)
{
    enum n10_model_entry_status status = n10_make_model_user_entry_frame(request, prepared);
    if (status != N10_MODEL_ENTRY_OK)
        return status;
    source.page_address = prepared->page_address;
    arm_saved_state_t before;
    memcpy(&before, &prepared->state, sizeof(before));
    ++fetch_calls;
    *fetched = n10_fetch_user_instruction(&prepared->state);
    frame_unchanged = memcmp(&before, &prepared->state, sizeof(before)) == 0;
    return status;
}

static struct n10_model_user_entry_request valid_request(void)
{
    struct n10_model_user_entry_request request = {
        .raw_page_address = 0, .raw_entry_pc = 8,
        .page_bytes = N10_USER_PAGE_BYTES, .model_load_bias = 2 * N10_USER_PAGE_BYTES
    };
    return request;
}

static int reject_case(const struct n10_model_user_entry_request *request, int null_output,
                       enum n10_model_entry_status expected)
{
    struct n10_model_user_entry_frame output, before;
    struct n10_user_instruction fetched;
    memset(&output, 0xa5, sizeof(output));
    memcpy(&before, &output, sizeof(before));
    memset(&fetched, 0xa5, sizeof(fetched));
    reset();
    enum n10_model_entry_status status = produce_then_fetch(request, null_output ? NULL : &output, &fetched);
    ++cases;
    return status == expected && memcmp(&output, &before, sizeof(output)) == 0 &&
           fetch_calls == 0 && service_calls == 0 && backing_calls == 0;
}

static int success_case(struct n10_model_user_entry_request request)
{
    struct n10_model_user_entry_frame output, expected;
    memset(&output, 0xa5, sizeof(output));
    memset(&expected, 0, sizeof(expected));
    expected.page_address = request.raw_page_address + request.model_load_bias;
    expected.state.ash.flavor = ARM_SAVED_STATE64;
    expected.state.ash.count = ARM_SAVED_STATE64_COUNT;
    expected.state.ss_64.pc = request.raw_entry_pc + request.model_load_bias;
    expected.state.ss_64.cpsr = PSR64_MODE_EL0;
    reset();
    enum n10_model_entry_status status = n10_make_model_user_entry_frame(&request, &output);
    ++cases;
    return status == N10_MODEL_ENTRY_OK && memcmp(&output, &expected, sizeof(output)) == 0 &&
           is_saved_state64(&output.state) && (uint64_t)get_saved_state_pc(&output.state) == expected.state.ss_64.pc &&
           fetch_calls == 0 && service_calls == 0 && backing_calls == 0;
}

#define CHECK(value) do { if (!(value)) { fprintf(stderr, "new producer case at line %d failed\n", __LINE__); return 0; } } while (0)

static int input_cases(void)
{
    struct n10_model_user_entry_request request = valid_request();
    CHECK(reject_case(NULL, 0, N10_MODEL_ENTRY_INVALID));
    CHECK(reject_case(&request, 1, N10_MODEL_ENTRY_INVALID));
    request.page_bytes = 0;
    CHECK(reject_case(&request, 0, N10_MODEL_ENTRY_INVALID));
    request = valid_request();
    request.page_bytes /= 2;
    CHECK(reject_case(&request, 0, N10_MODEL_ENTRY_INVALID));
    request = valid_request();
    request.raw_page_address = 4;
    CHECK(reject_case(&request, 0, N10_MODEL_ENTRY_INVALID));
    request = valid_request();
    request.model_load_bias = 4;
    CHECK(reject_case(&request, 0, N10_MODEL_ENTRY_INVALID));
    request = valid_request();
    request.raw_entry_pc = 1;
    CHECK(reject_case(&request, 0, N10_MODEL_ENTRY_RANGE));
    request = valid_request();
    request.raw_page_address = N10_USER_PAGE_BYTES;
    request.raw_entry_pc = N10_USER_PAGE_BYTES - 4;
    CHECK(reject_case(&request, 0, N10_MODEL_ENTRY_RANGE));
    request = valid_request();
    request.raw_entry_pc = N10_USER_PAGE_BYTES;
    CHECK(reject_case(&request, 0, N10_MODEL_ENTRY_RANGE));
    return 1;
}

static int overflow_cases(void)
{
    struct n10_model_user_entry_request request = valid_request();
    request.raw_page_address = UINT64_MAX - N10_USER_PAGE_BYTES + 1;
    request.raw_entry_pc = request.raw_page_address;
    CHECK(reject_case(&request, 0, N10_MODEL_ENTRY_OVERFLOW));
    request = valid_request();
    request.raw_page_address = N10_USER_PAGE_BYTES;
    request.raw_entry_pc = N10_USER_PAGE_BYTES + 8;
    request.model_load_bias = UINT64_MAX - N10_USER_PAGE_BYTES + 1;
    CHECK(reject_case(&request, 0, N10_MODEL_ENTRY_OVERFLOW));
    request = valid_request();
    request.model_load_bias = UINT64_MAX - N10_USER_PAGE_BYTES + 1;
    CHECK(reject_case(&request, 0, N10_MODEL_ENTRY_OVERFLOW));
    return 1;
}

static int success_cases(void)
{
    struct n10_model_user_entry_request request = valid_request();
    request.model_load_bias = 0;
    CHECK(success_case(request));
    request = valid_request();
    request.raw_page_address = N10_USER_PAGE_BYTES;
    request.raw_entry_pc = N10_USER_PAGE_BYTES + 8;
    CHECK(success_case(request));
    request = valid_request();
    request.raw_entry_pc = 0;
    CHECK(success_case(request));
    request = valid_request();
    request.raw_entry_pc = N10_USER_PAGE_BYTES - 4;
    CHECK(success_case(request));
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
    if (!input_cases() || !overflow_cases() || !success_cases() || cases != 16)
        return 1;
    unsigned char wire[32], page[N10_USER_PAGE_BYTES];
    if (fread(wire, 1, sizeof(wire), stdin) != sizeof(wire) ||
        fread(page, 1, sizeof(page), stdin) != sizeof(page))
        return 1;
    struct n10_model_user_entry_request request = {
        .raw_page_address = little64(wire), .raw_entry_pc = little64(wire + 8),
        .model_load_bias = little64(wire + 16), .page_bytes = sizeof(page)
    };
    source = (struct n10_user_page_source){
        .expected_task = &task_token, .expected_map = &map_token,
        .current_task = &task_token, .current_map = &map_token,
        .page_bytes = sizeof(page), .initprot = little32(wire + 24), .maxprot = little32(wire + 28),
        .read4 = read_backing, .context = page
    };
    struct n10_model_user_entry_frame prepared;
    struct n10_user_instruction fetched;
    reset();
    enum n10_model_entry_status status = produce_then_fetch(&request, &prepared, &fetched);
    if (status != N10_MODEL_ENTRY_OK || fetched.status != N10_USER_FETCH_OK || fetched.copy_error != 0 ||
        gate_status != N10_USER_PAGE_OK || fetch_calls != 1 || service_calls != 1 || backing_calls != 1 ||
        service_bytes != 4 || !frame_unchanged || service_address != (uint64_t)get_saved_state_pc(&prepared.state))
        return 1;
    printf("{\"synthetic_groups\":3,\"synthetic_cases\":%u,\"reject_cases\":12,"
           "\"reject_output_unchanged\":true,\"reject_fetch_calls\":0,\"reject_service_calls\":0,\"reject_backing_calls\":0,"
           "\"producer_status\":%u,\"produced_page_address\":%" PRIu64 ",\"produced_pc\":%" PRIu64 ","
           "\"service_address\":%" PRIu64 ",\"fetch_status\":%u,\"copy_error\":%d,\"gate_status\":%u,"
           "\"fetch_calls\":%u,\"service_calls\":%u,\"backing_calls\":%u,\"backing_bytes\":4,"
           "\"relative_offset\":%" PRIu64 ",\"frame_unchanged\":true,\"word\":%" PRIu32 "}\n",
           cases, (unsigned)status, prepared.page_address, (uint64_t)get_saved_state_pc(&prepared.state),
           service_address, (unsigned)fetched.status, fetched.copy_error, (unsigned)gate_status,
           fetch_calls, service_calls, backing_calls, backing_offset, fetched.word);
    return 0;
}
