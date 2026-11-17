/* SPDX-License-Identifier: GPL-2.0-only */
#include <assert.h>
#include <errno.h>
#include <stdio.h>
#include <string.h>
#include "native_prepare_core.h"
#define N154_BUILD_ID "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
#define SYSTEM_RUNNING 1
#define READ_ONCE(x) (x)
#define atomic_read(p) (*(p))
#define delayed_work_pending(p) (*(p))
static char n10_boot_id[33]="bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb";
static volatile char n10_cycle[33]="cccccccccccccccccccccccccccccccc";
static int n154_arm_result,n10_return_started,n10_return_requested,system_state,n10_return_work;
#include "v292_return_admission.inc"
static void reset(void)
{ n154_arm_result=0;n10_return_started=1;n10_return_requested=0;system_state=SYSTEM_RUNNING;n10_return_work=1; }
static int check(int expected)
{
    struct n210_context out,desired={0};int error;
    memset(&out,0xa5,sizeof(out));memcpy(desired.build,N154_BUILD_ID,32);
    memcpy(desired.boot,n10_boot_id,32);memcpy(desired.cycle,(const void *)n10_cycle,32);desired.return_armed=(n209_u32)expected;
    error=n210_linux_context(&out);
    return error==(expected?0:-EAGAIN)&&!memcmp(&out,&desired,sizeof(out));
}
int main(void)
{
    int ok=1;
    reset();ok&=check(1);
    reset();n154_arm_result=-EAGAIN;ok&=check(0);
    reset();n10_return_started=0;ok&=check(0);
    reset();n10_return_requested=1;ok&=check(0);
    reset();system_state=0;ok&=check(0);
    reset();n10_return_work=0;ok&=check(0);
    assert(ok);
    puts("{\"passed\":true,\"groups\":1,\"variants\":1,\"assertions\":1,\"negative_cases\":5}");return 0;
}
