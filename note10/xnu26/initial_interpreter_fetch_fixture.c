/* Controlled initial-interpreter caller for the unchanged fetch and page gate. */
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

static int task_token, map_token;
static struct n10_user_page_source source;
static enum n10_user_page_status gate_status;
static unsigned service_calls, backing_calls;
static size_t service_bytes;
static uint64_t backing_offset;

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
    service_bytes = length;
    gate_status = n10_read_user_page_instruction(&source, (uint64_t)address, destination, length);
    return gate_status == N10_USER_PAGE_OK ? 0 : EFAULT;
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
    unsigned char wire[24], page[N10_USER_PAGE_BYTES];
    if (fread(wire, 1, sizeof(wire), stdin) != sizeof(wire) ||
        fread(page, 1, sizeof(page), stdin) != sizeof(page))
        return 1;
    source = (struct n10_user_page_source){
        .expected_task = &task_token, .expected_map = &map_token,
        .current_task = &task_token, .current_map = &map_token,
        .page_address = little64(wire), .page_bytes = sizeof(page),
        .initprot = little32(wire + 16), .maxprot = little32(wire + 20),
        .read4 = read_backing, .context = page
    };
    arm_saved_state_t frame;
    memset(&frame, 0, sizeof(frame));
    frame.ash.flavor = ARM_SAVED_STATE64;
    frame.ash.count = ARM_SAVED_STATE64_COUNT;
    frame.ss_64.pc = little64(wire + 8);
    frame.ss_64.cpsr = PSR64_MODE_EL0;
    arm_saved_state_t before = frame;
    struct n10_user_instruction fetched = n10_fetch_user_instruction(&frame);
    if (fetched.status != N10_USER_FETCH_OK || fetched.copy_error != 0 || gate_status != N10_USER_PAGE_OK ||
        service_calls != 1 || service_bytes != 4 || backing_calls != 1 ||
        memcmp(&frame, &before, sizeof(frame)) != 0)
        return 1;
    printf("{\"fetch_status\":%u,\"copy_error\":%d,\"gate_status\":%u,\"service_calls\":%u,"
           "\"backing_calls\":%u,\"backing_bytes\":4,\"relative_offset\":%" PRIu64 ","
           "\"frame_unchanged\":true,\"word\":%" PRIu32 "}\n",
           (unsigned)fetched.status, fetched.copy_error, (unsigned)gate_status,
           service_calls, backing_calls, backing_offset, fetched.word);
    return 0;
}
