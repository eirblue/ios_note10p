/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef N301_INITIAL_TIMEOUT_H
#define N301_INITIAL_TIMEOUT_H
#define N301_INITIAL_TIMEOUT 30U
/* Exact observed pre-open state; SETTIMEOUT/GETTIMEOUT still require10s. */
static inline unsigned int n301_timeout_reason(unsigned int timeout)
{
    return timeout==N301_INITIAL_TIMEOUT?0U:(1U<<11);
}
#endif
