/* Host-only actual file window through the unchanged production C request core. */
#include <errno.h>
#include <fcntl.h>
#include <inttypes.h>
#include <io.h>
#include <stdio.h>
#include <stdlib.h>

#include "note10_iostorage_read_range.h"
#include "note10_iostorage_read_request.h"

enum { WINDOW_BYTES = 4096 };

struct window {
    FILE *file;
    unsigned char data[WINDOW_BYTES];
    uint64_t expected_offset;
    uint64_t actual;
    unsigned reads;
    unsigned completions;
    unsigned fread_calls;
    unsigned output_bytes;
    enum note10_iostorage_read_status status;
    bool returned;
    bool owner_live_at_completion;
    bool returned_before_close;
    bool closed_before_output;
};

static int
report(const struct window *window, const char *phase, bool passed)
{
    fprintf(stderr, "{\"schema\":\"note10-v175-file-window-status-v1\",\"phase\":\"%s\","
            "\"passed\":%s,\"read_callbacks\":%u,\"completion_callbacks\":%u,"
            "\"image_fread_calls\":%u,\"byte_offset\":%" PRIu64 ",",
            phase, passed ? "true" : "false", window->reads, window->completions,
            window->fread_calls, window->expected_offset);
    if (window->completions == 1)
        fprintf(stderr, "\"actual_bytes\":%" PRIu64 ",\"completion_status\":%u,",
                window->actual, (unsigned)window->status);
    else
        fputs("\"actual_bytes\":null,\"completion_status\":null,", stderr);
    fprintf(stderr, "\"owner_live_at_completion\":%s,\"returned_before_close\":%s,"
            "\"file_closed_before_output\":%s,\"data_output_bytes\":%u}\n",
            window->owner_live_at_completion ? "true" : "false",
            window->returned_before_close ? "true" : "false",
            window->closed_before_output ? "true" : "false", window->output_bytes);
    return passed ? 0 : 1;
}

static bool
decimal(const char *text, uint64_t *out)
{
    if (*text < '0' || *text > '9')
        return false;
    char *end;
    errno = 0;
    unsigned long long value = strtoull(text, &end, 10);
    if (errno != 0 || *end != '\0')
        return false;
    *out = (uint64_t)value;
    return true;
}

static bool
read_window(void *context, uint64_t offset, uint64_t length, uint64_t *actual_bytes)
{
    struct window *window = context;
    ++window->reads;
    if (window->reads != 1 || window->file == NULL || window->returned ||
        length != sizeof(window->data) || offset != window->expected_offset || offset > INT64_MAX ||
        _fseeki64(window->file, (int64_t)offset, SEEK_SET) != 0)
        return false;
    ++window->fread_calls;
    *actual_bytes = fread(window->data, 1, sizeof(window->data), window->file);
    return !ferror(window->file);
}

static void
complete_window(void *context, enum note10_iostorage_read_status status, uint64_t actual_bytes)
{
    struct window *window = context;
    ++window->completions;
    window->status = status;
    window->actual = actual_bytes;
    window->owner_live_at_completion = window->file != NULL && !window->returned &&
        window->reads == 1 && window->fread_calls == 1;
}

int
main(int argc, char **argv)
{
    struct window window = {0};
    uint64_t extent = 0, lba = 0;
    if (argc != 4 || !decimal(argv[2], &extent) || !decimal(argv[3], &lba) ||
        extent == 0 || extent > INT64_MAX || extent % WINDOW_BYTES != 0 || lba >= extent / WINDOW_BYTES)
        return report(&window, "arguments", false);
    window.expected_offset = lba * WINDOW_BYTES;
    if (_isatty(_fileno(stdout)) || _setmode(_fileno(stdout), _O_BINARY) == -1 ||
        setvbuf(stdout, NULL, _IONBF, 0) != 0)
        return report(&window, "stdout_capture", false);
    window.file = fopen(argv[1], "rb");
    if (window.file == NULL)
        return report(&window, "open", false);
    if (setvbuf(window.file, NULL, _IONBF, 0) != 0 ||
        _fseeki64(window.file, 0, SEEK_END) != 0 || _ftelli64(window.file) != (int64_t)extent) {
        fclose(window.file);
        window.file = NULL;
        return report(&window, "extent", false);
    }
    bool admitted = note10_iostorage_read_request(extent, WINDOW_BYTES, lba, 1, WINDOW_BYTES,
        NOTE10_IOSTORAGE_READ_DIRECTION, read_window, complete_window, &window);
    window.returned = true;
    bool complete = admitted && window.reads == 1 && window.completions == 1 && window.fread_calls == 1 &&
        window.owner_live_at_completion && window.status == NOTE10_IOSTORAGE_READ_OK && window.actual == WINDOW_BYTES;
    window.returned_before_close = window.returned;
    bool closed = fclose(window.file) == 0;
    window.file = NULL;
    window.closed_before_output = closed && window.returned_before_close;
    if (!complete || !closed)
        return report(&window, complete ? "close" : "request", false);
    window.output_bytes = (unsigned)fwrite(window.data, 1, sizeof(window.data), stdout);
    if (window.output_bytes != WINDOW_BYTES || fflush(stdout) != 0)
        return report(&window, "output", false);
    return report(&window, "complete", true);
}
