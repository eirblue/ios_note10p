/* Exercise the exact kernel handler with synthetic config combinations. */
#include <assert.h>
#include <stdio.h>
#define __init
static int builtin_route, diagnostic, do_skip_initramfs;
#define CONFIG_NOTE10_BUILTIN_INIT_ROUTE builtin_route
#define CONFIG_NOTE10_V154_LINUX_DIAGNOSTIC diagnostic
#define IS_ENABLED(option) (option)
#include "v298_skip_initramfs.inc"
int main(void)
{
    int bits, valued;
    char bare[] = "", value[] = "1";
    for (bits = 0; bits < 4; ++bits) {
        builtin_route = bits & 1;
        diagnostic = (bits >> 1) & 1;
        for (valued = 0; valued < 2; ++valued) {
            do_skip_initramfs = 0;
            assert(skip_initramfs_param(valued ? value : bare) == !valued);
            assert(do_skip_initramfs == (!valued && bits != 3));
        }
    }
    puts("{\"passed\":true,\"groups\":1,\"variants\":8,\"assertions\":16}");
    return 0;
}
