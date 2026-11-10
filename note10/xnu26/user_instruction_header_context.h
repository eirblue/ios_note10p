#ifndef NOTE10_USER_INSTRUCTION_HEADER_CONTEXT_H
#define NOTE10_USER_INSTRUCTION_HEADER_CONTEXT_H

/* This BSD-aware translation unit must take string.h's sys/types.h branch. */
#ifdef MACH_KERNEL_PRIVATE
#error User fetch must not select standalone Mach libsa types
#endif
#if !defined(KERNEL) || !defined(KERNEL_PRIVATE) || !defined(XNU_KERNEL_PRIVATE) || !defined(MACH_KERNEL)
#error User fetch still requires the real private kernel declarations
#endif

#include <sys/types.h>
#include <string.h>

#ifdef _MACH_TYPES_H_
#error Standalone libsa/types.h was selected instead of BSD sys/types.h
#endif
_Static_assert(__builtin_types_compatible_p(dev_t, __darwin_dev_t), "BSD dev_t identity required");
_Static_assert(__builtin_types_compatible_p(daddr_t, int32_t), "BSD daddr_t identity required");

#endif
