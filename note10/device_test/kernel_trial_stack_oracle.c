/* Read-only constants evaluated by actual configured kernel headers. */
#include <asm/thread_info.h>
#include <asm/irq.h>
__attribute__((__used__,__section__(".n10_stack")))
const uint64_t n10_kernel_stack_oracle[]={THREAD_SIZE,
#ifdef IRQ_STACK_SIZE
    IRQ_STACK_SIZE
#else
    0 /* Unsupported IRQ-size oracle; no IRQ stack-safety assertion. */
#endif
};
