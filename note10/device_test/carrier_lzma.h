/* SPDX-License-Identifier: LGPL-2.1-or-later */
#ifndef N10_CARRIER_LZMA_H
#define N10_CARRIER_LZMA_H
#include <stddef.h>
#include <stdint.h>
#ifdef _WIN32
#define N10_LZMA_API __declspec(dllexport)
#else
#define N10_LZMA_API
#endif
#define N10_LZMA_WORKSPACE 15980u
#define N10_LZMA_MAX_BYTES (64u * 1024u * 1024u)
enum n10_lzma_status {
    N10_LZMA_OK = 0, N10_LZMA_ARGUMENT = -1, N10_LZMA_HEADER = -2,
    N10_LZMA_INPUT = -3, N10_LZMA_OUTPUT = -4, N10_LZMA_WORK = -5,
    N10_LZMA_CORRUPT = -6, N10_LZMA_EARLY_EOS = -7
};
struct n10_lzma_result {
    uint32_t version;
    int32_t status;
    uint64_t consumed, written;
};
N10_LZMA_API int n10_lzma_alone_decode(const uint8_t *input, size_t input_bytes,
    uint8_t *output, size_t output_capacity, void *workspace, size_t workspace_bytes,
    struct n10_lzma_result *result);
#endif
