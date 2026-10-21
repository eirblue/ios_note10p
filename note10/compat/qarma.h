/* SPDX-License-Identifier: LGPL-2.1-or-later */
#ifndef NOTE10_QARMA_H
#define NOTE10_QARMA_H
#include <stdint.h>
struct n10_pac_key { uint64_t lo, hi; };
/* Architected QARMA3/QARMA5 core only. No PAC address insertion, ABI selection,
 * process key management or claim of matching Apple's hardware algorithm.
 * Invalid arguments leave *out unchanged. Experimental, not side-channel hardened.
 */
int n10_qarma(uint64_t data, uint64_t modifier, const struct n10_pac_key *key,
              unsigned rounds, uint64_t *out);
#endif
