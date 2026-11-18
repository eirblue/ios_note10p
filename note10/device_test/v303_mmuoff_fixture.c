/* New source-owned cursor and post-MMU record ABI cases only. */
#include <assert.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#include "v303_mmuoff_contract.h"
static struct n303_owner valid(void)
{
    struct n303_owner s={0x200000,0x10000000,4096,0x10000100,0x300000,0x11000000,4096,0x200100,256,1};return s;
}
int main(void)
{
    struct n303_owner s=valid();struct n303_slot out;char text[N303_RECORD_BYTES+1];const char *id="11111111111111111111111111111111";
    assert(n303_claim_ok(&s,&out)&&out.record==0x200100&&out.cursor==0x300100&&out.next==0x200100+N303_RECORD_BYTES);
    s.enabled=0;assert(!n303_claim_ok(&s,&out));s=valid();
    s.cursor_va=s.log_va-1;assert(!n303_claim_ok(&s,&out));s=valid();
    s.cursor_va=s.log_va+s.log_bytes-8;s.saved=s.log_pa+s.log_bytes-8;assert(!n303_claim_ok(&s,&out));s=valid();
    s.log_pa=0xffffff00ULL;s.saved=s.log_pa+256;assert(!n303_claim_ok(&s,&out));s=valid();
    s.header_pa=s.log_pa;assert(!n303_claim_ok(&s,&out));s=valid();
    s.offset=257;assert(!n303_claim_ok(&s,&out));s=valid();
    s.saved++;assert(!n303_claim_ok(&s,&out));
    assert(snprintf(text,sizeof(text),N303_FORMAT,id,id,id,1ULL,2ULL,3ULL,4ULL)==N303_RECORD_BYTES&&text[N303_COMMIT_OFFSET]=='0'&&text[N303_EL_OFFSET]=='0'&&text[N303_SCTLR_OFFSET]=='0'&&text[N303_CHECKSUM_OFFSET]=='0'&&text[N303_RECORD_BYTES-1]=='\n');
    assert(offsetof(struct n303_parameters,text)==N303_PARAM_TEXT&&sizeof(((struct n303_parameters *)0)->text)==N303_RECORD_BYTES+1);
    puts("{\"passed\":true,\"groups\":1,\"variants\":10,\"assertions\":10}");return 0;
}
