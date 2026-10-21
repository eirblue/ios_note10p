#include "qarma.h"
#include <inttypes.h>
#include <stdio.h>
int main(void)
{
    const struct n10_pac_key key = {0xec2802d4e0a488e9ULL, 0x84be85ce9804e94bULL};
    uint64_t actual = 0;
    if (!n10_qarma(0xfb623599da6e8127ULL, 0x477d469dec0b8762ULL, &key, 5, &actual))
        return 1;
    /* Paper appendix A.1, QARMA64_5 sigma2. sigma0 has a different vector. */
    printf("{\"actual\":\"%016" PRIx64 "\",\"expected\":\"c003b93999b33765\",\"sbox\":\"sigma2\",\"passed\":%s}\n",
           actual, actual == 0xc003b93999b33765ULL ? "true" : "false");
    return actual == 0xc003b93999b33765ULL ? 0 : 1;
}
