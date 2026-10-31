#include <stdint.h>
void n10_fixture_observe(uint8_t *,uint64_t,uint64_t,uint64_t);
#define N10_TRIAL_OBSERVE(w,o,s,a) n10_fixture_observe(w,o,s,a)
