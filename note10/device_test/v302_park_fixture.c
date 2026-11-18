/* New post-ACK ownership and actual-online witness guards only. */
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "v302_park_contract.h"
static struct n300_wdt_fields good_wdt(void)
{
    struct n300_wdt_fields w={0};w.present=w.variant=w.route_func=w.rate_clock=w.gate_clock=w.active=1;
    w.freq=26000000;w.timeout=10;return w;
}
static struct n302_gate good_gate(void)
{
    struct n302_gate g={1,1,1,1,0,1,1,60000};return g;
}
int main(void)
{
    struct n300_wdt_fields w=good_wdt();struct n302_gate g=good_gate();char ack[128];
    assert(n302_gate_ready(&g,&w));
    w.active=0;assert(!n302_gate_ready(&g,&w));w=good_wdt();
    w.timeout=30;assert(!n302_gate_ready(&g,&w));w=good_wdt();
    g.prepared=0;assert(!n302_gate_ready(&g,&w));g=good_gate();
    g.requested=1;assert(!n302_gate_ready(&g,&w));g=good_gate();
    g.remaining=29999;assert(!n302_gate_ready(&g,&w));g=good_gate();
    g.cpu0_online=0;assert(!n302_gate_ready(&g,&w));g=good_gate();
    w.freq=1;assert(!n302_gate_ready(&g,&w));
    assert(n302_online_ok(1,1,0,1));
    assert(n302_online_ok(5,2,0,1));
    assert(!n302_online_ok(2,1,0,1));
    assert(!n302_online_ok(5,2,0,0));
    assert(!n302_online_ok(5,3,0,1));
    assert(n302_ack_line(ack,60000)>0 && !strcmp(ack,"N299ARM timeout=10 remaining_ms=60000 descriptor=held keepalives=0\n"));
    assert(n302_ack_line(ack,29999)<0);
    puts("{\"passed\":true,\"groups\":1,\"variants\":15,\"assertions\":15}");return 0;
}
