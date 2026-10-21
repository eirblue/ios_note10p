/* Host-tool portability only. Not a kernel or target ABI compatibility header. */
#ifndef NOTE10_WINDOWS_CONFIG_COMPAT_H
#define NOTE10_WINDOWS_CONFIG_COMPAT_H
#include <limits.h>
#include <string.h>
_Static_assert(CHAR_BIT == 8, "XNU config host requires 8-bit bytes");
typedef unsigned char u_char;
#define index strchr
#define rindex strrchr
#endif
