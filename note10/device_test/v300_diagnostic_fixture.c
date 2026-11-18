/* New reason-bit mapping: all original conditions remain mandatory. */
#include <assert.h>
#include <stdio.h>
#include "v300_return_diagnostic.h"
static struct n300_wdt_fields good_driver(void)
{
    struct n300_wdt_fields s={0};s.present=s.variant=s.route_func=s.rate_clock=s.gate_clock=1;
    s.freq=26000000;s.timeout=15;return s;
}
int main(void)
{
    struct n300_wdt_fields s;struct n300_outer_fields o;unsigned int bit;
    s=good_driver();assert(!n300_wdt_reasons(&s));
    for(bit=0;bit<15;++bit){
        s=good_driver();
        switch(bit){
        case 0:s.present=0;break;case 1:s.soft_noboot=1;break;case 2:s.nowayout=1;break;
        case 3:s.cluster=1;break;case 4:s.variant=0;break;case 5:s.route_func=0;break;
        case 6:s.rate_clock=0;break;case 7:s.gate_clock=0;break;case 8:s.freq=0;break;
        case 9:s.multistage=1;break;case 10:s.device_id=1;break;case 11:s.timeout=14;break;
        case 12:s.max_heartbeat=1;break;case 13:s.active=1;break;case 14:s.hw_running=1;break;
        }
        assert(n300_wdt_reasons(&s)==(1U<<bit));
    }
    s=good_driver();s.timeout=14;s.device_id=1;assert(n300_wdt_reasons(&s)==((1U<<10)|(1U<<11)));
    o=(struct n300_outer_fields){.running=1,.cycle_ok=1,.pending=1,.armed=1,.remaining=60000};
    assert(!n300_outer_reasons(&o));
    for(bit=0;bit<8;++bit){
        o=(struct n300_outer_fields){.running=1,.cycle_ok=1,.pending=1,.armed=1,.remaining=60000};
        switch(bit){
        case 0:o.running=0;break;case 1:o.cycle_ok=0;break;case 2:o.arm_result=-1;break;
        case 3:o.pending=0;break;case 4:o.armed=0;break;case 5:o.requested=1;break;
        case 6:o.remaining=44999;break;case 7:o.spent=1;break;
        }
        assert(n300_outer_reasons(&o)==(1U<<bit));
    }
    o.spent=1;o.requested=1;assert(n300_outer_reasons(&o)==((1U<<5)|(1U<<7)));
    puts("{\"passed\":true,\"groups\":1,\"variants\":27,\"assertions\":27}");return 0;
}
