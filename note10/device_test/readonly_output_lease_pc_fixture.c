/* SPDX-License-Identifier: GPL-2.0-only */
#include <stdio.h>
#include <string.h>
#include "readonly_output_lease_pc.h"
#define CHECK(x) do { if (!(x)) { fprintf(stderr,"synthetic check failed at line %d\n",__LINE__); return 1; } } while (0)
static unsigned char bytes[66];
static struct n10_lease_pc_assertion assertion(void)
{
    struct n10_lease_pc_assertion a={bytes+1,64,64,7,1,1,1,1};
    return a;
}
static int lifecycle(void)
{
    struct n10_lease_pc s={0}; struct n10_lease_pc_assertion a=assertion();
    struct n10_lease_pc_token t={0}; const unsigned char *p=NULL; size_t n=0;
    CHECK(!n10_lease_pc_offer(&s,&a)); CHECK(!n10_lease_pc_acquire(&s,&t));
    CHECK(!n10_lease_pc_view(&s,&t,&p,&n) && p==bytes+1 && n==64);
    CHECK(!n10_lease_pc_release(&s,&t)); CHECK(n10_lease_pc_acquire(&s,&t));
    CHECK(n10_lease_pc_view(&s,&t,&p,&n)); CHECK(!n10_lease_pc_retire(&s,&t));
    CHECK(n10_lease_pc_retire(&s,&t)); CHECK(n10_lease_pc_view(&s,&t,&p,&n));
    /* The protocol cannot revoke this earlier copied pointer or keep it alive. */
    CHECK(p==bytes+1 && n==64); CHECK(s.data==NULL && s.length==0);
    return 0;
}
static int exclusive_borrow(void)
{
    struct n10_lease_pc s={0},before; struct n10_lease_pc_assertion a=assertion();
    struct n10_lease_pc_token t={0},other={0};
    CHECK(!n10_lease_pc_offer(&s,&a)); before=s;
    CHECK(n10_lease_pc_offer(&s,&a)); CHECK(s.phase==before.phase && s.generation==before.generation);
    CHECK(!n10_lease_pc_acquire(&s,&t)); CHECK(n10_lease_pc_acquire(&s,&other));
    CHECK(n10_lease_pc_retire(&s,&t)); CHECK(s.phase==N10_LEASE_PC_BORROWED);
    CHECK(!n10_lease_pc_release(&s,&t)); CHECK(n10_lease_pc_release(&s,&t));
    CHECK(n10_lease_pc_acquire(&s,&other)); CHECK(!n10_lease_pc_retire(&s,&t));
    return 0;
}
static int invalid_assertions(void)
{
    unsigned int i;
    for (i=0;i<10;++i) {
        struct n10_lease_pc s={0}; struct n10_lease_pc_assertion a=assertion();
        switch(i) {
        case 0:a.data=NULL;break; case 1:a.capacity=0;break; case 2:a.written=63;break;
        case 3:a.owner=0;break; case 4:a.generation=0;break; case 5:a.synthetic_owner=0;break;
        case 6:a.live=0;break; case 7:a.verified=0;break; case 8:a.live=2;break;
        default:a.capacity=SIZE_MAX;a.written=SIZE_MAX;break;
        }
        CHECK(n10_lease_pc_offer(&s,&a)); CHECK(s.phase==N10_LEASE_PC_EMPTY && s.data==NULL && s.generation==0);
    }
    CHECK(n10_lease_pc_offer(NULL,NULL));
    return 0;
}
static int generation_and_token(void)
{
    struct n10_lease_pc s={0}; struct n10_lease_pc_assertion a=assertion();
    struct n10_lease_pc_token old={0},fresh={0},wrong={8,1};
    const unsigned char *p=NULL; size_t n=0;
    CHECK(!n10_lease_pc_offer(&s,&a)); CHECK(!n10_lease_pc_acquire(&s,&old));
    CHECK(n10_lease_pc_view(&s,&wrong,&p,&n)); CHECK(p==NULL && n==0);
    CHECK(n10_lease_pc_release(&s,&wrong)); CHECK(!n10_lease_pc_release(&s,&old));
    CHECK(!n10_lease_pc_retire(&s,&old)); CHECK(n10_lease_pc_offer(&s,&a));
    a.generation=2; CHECK(!n10_lease_pc_offer(&s,&a)); CHECK(!n10_lease_pc_acquire(&s,&fresh));
    CHECK(n10_lease_pc_release(&s,&old)); CHECK(n10_lease_pc_view(&s,&old,&p,&n));
    CHECK(!n10_lease_pc_view(&s,&fresh,&p,&n)); CHECK(!n10_lease_pc_release(&s,&fresh));
    CHECK(!n10_lease_pc_retire(&s,&fresh));
    return 0;
}
static int assertions_are_not_attestation(void)
{
    struct n10_lease_pc s={0}; struct n10_lease_pc_assertion a=assertion();
    struct n10_lease_pc_token t={7,1},copy; const unsigned char *p=NULL; size_t n=0;
    /* Any caller can construct these values: acceptance attests no real owner. */
    CHECK(!n10_lease_pc_offer(&s,&a)); CHECK(!n10_lease_pc_acquire(&s,&t)); copy=t;
    CHECK(!n10_lease_pc_view(&s,&copy,&p,&n)); CHECK(!n10_lease_pc_release(&s,&copy));
    CHECK(!n10_lease_pc_retire(&s,&copy));
    return 0;
}
int main(void)
{
    unsigned int i;
    memset(bytes,0xa5,sizeof(bytes));
    if (lifecycle() || exclusive_borrow() || invalid_assertions() || generation_and_token() || assertions_are_not_attestation()) return 1;
    for (i=0;i<sizeof(bytes);++i) if(bytes[i]!=0xa5) return 1;
    puts("{\"schema\":\"n10-output-lease-fixture-pc-v1\",\"cases\":5,\"single_threaded\":true,\"one_total_borrow_per_generation\":true,\"canaries_unchanged\":true,\"caller_assertions_forgeable\":true,\"copied_token_forgeable\":true,\"raw_pointer_not_revoked\":true,\"ownership_attested\":false,\"memory_liveness_attested\":false,\"real_decoder_calls\":0,\"allocator_calls\":0,\"cleanup_calls\":0,\"hardware_operations\":0}");
    return 0;
}
