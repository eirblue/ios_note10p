/* Only changed initial-timeout boundary and reason-bit composition. */
#include <assert.h>
#include <stdio.h>
#include "v301_initial_timeout.h"
int main(void)
{
    const unsigned int values[]={15,29,30,31};unsigned int i;
    for(i=0;i<4;++i)
        assert(n301_timeout_reason(values[i])==(values[i]==30?0U:(1U<<11)));
    assert(((1U<<10)|n301_timeout_reason(30))==(1U<<10));
    assert(((1U<<10)|n301_timeout_reason(15))==((1U<<10)|(1U<<11)));
    puts("{\"passed\":true,\"groups\":1,\"variants\":6,\"assertions\":6}");return 0;
}
