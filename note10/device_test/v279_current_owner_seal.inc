/* SPDX-License-Identifier: GPL-2.0-only */
#include "v278_current_owner_seal.h"
#define N279_SEAL_OFFSET 43704U
#define N279_SEAL ((struct n278_seal *)(n226_source_pool+N279_SEAL_OFFSET))
_Static_assert(N279_SEAL_OFFSET==N269_POOL_OFFSET+sizeof(struct n269_binding),"after watchdog40");
_Static_assert(N226_POOL_BYTES==49152 && N226_STAGE_OFFSET==45056,"existing pool only");
_Static_assert(sizeof(struct n278_seal)==1192 && __alignof__(struct n278_seal)==8,"actual seal ABI");
_Static_assert(N279_SEAL_OFFSET%__alignof__(struct n278_seal)==0 &&
    N279_SEAL_OFFSET+sizeof(struct n278_seal)<=N226_STAGE_OFFSET,"seal inside existing gap");
#ifdef __KERNEL__
__asm__(".globl n279_seal_storage\n.set n279_seal_storage,n226_source_pool+43704\n"
        ".type n279_seal_storage,%object\n.size n279_seal_storage,1192\n");
/* Same computed-ABS witness pattern as230; never called at runtime. */
static __used __attribute__((__noinline__)) void n279_layout_witness(void)
{
    asm volatile(".globl n279_size_seal\n.equ n279_size_seal,%c0\n"
                 ".globl n279_align_seal\n.equ n279_align_seal,%c1\n"
                 ".globl n279_offset_values\n.equ n279_offset_values,%c2\n"
                 ".globl n279_owner_hash_offset\n.equ n279_owner_hash_offset,%c3\n"
                 ".globl n279_owner_hash_bytes\n.equ n279_owner_hash_bytes,%c4\n"
                 : : "i"(sizeof(struct n278_seal)),"i"(__alignof__(struct n278_seal)),
                     "i"(offsetof(struct n278_seal,values)),
                     "i"(N226_CONTROL_OFFSET+offsetof(struct n226_control,owner.hash)),
                     "i"(sizeof(((struct n226_control *)0)->owner.hash)));
}
#endif
