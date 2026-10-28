/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef NOTE10_EHLD_LOCK_AUDIT_H
#define NOTE10_EHLD_LOCK_AUDIT_H
#include <linux/types.h>
struct notifier_block;
struct n10_precond_sample;
struct n10_ehld_lock_row {
	unsigned int index, chain_count, lock_available, running_valid, running;
};
int n10_ehld_lock_get(struct n10_ehld_lock_row *row,
		      struct notifier_block *n,
		      const struct n10_precond_sample *pre,
		      unsigned int index, unsigned int generation);
struct n10_ehld_lock_sample {
	unsigned int generation, seen, completed;
	int error;
	struct n10_ehld_lock_row row;
};
void n10_ehld_lock_begin(unsigned int generation);
int n10_ehld_lock_collect(struct notifier_block *n,
			  const struct n10_precond_sample *pre,
			  unsigned int index, unsigned int generation);
int n10_ehld_lock_complete(const struct n10_precond_sample *pre,
			   unsigned int generation);
void n10_ehld_lock_invalidate(void);
void n10_ehld_lock_finish(int error);
int n10_ehld_lock_copy(struct n10_ehld_lock_sample *out,
		       unsigned int completed);
int n10_ehld_lock_read(struct n10_ehld_lock_sample *out,
		      unsigned int completed);
#endif
