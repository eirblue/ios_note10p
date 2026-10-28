/* SPDX-License-Identifier: GPL-2.0-only */
#include <linux/note10_ehld_lock_audit.h>
#define N10_EHLD_LOCK_BUDGET 2048U
static struct n10_ehld_lock_sample n10_ehld_lock_report;
static int n10_ehld_lock_emit(const char *tag, const char *frame, int n,
			      unsigned int *budget, int emit)
{
	unsigned int bytes;
	if (n < 0 || n >= 384)
		return -E2BIG;
	bytes = n + strlen(tag) + 96;
	if (bytes > N10_EHLD_LOCK_BUDGET ||
	    *budget > N10_EHLD_LOCK_BUDGET - bytes)
		return -E2BIG;
	*budget += bytes;
	if (emit)
		pr_info("%s %s checksum=%08x\n", tag, frame,
			n10_frame_checksum(frame, n));
	return 0;
}
static int n10_ehld_lock_emit_all(int emit, int status, unsigned int generation)
{
	char frame[384];
	unsigned int copy, budget = 0;
	int n, ret;
#define EHLD_ROW(tag, ...) do { \
	n = snprintf(frame, sizeof(frame), __VA_ARGS__); \
	ret = n10_ehld_lock_emit(tag, frame, n, &budget, emit); \
	if (ret) return ret; \
} while (0)
	for (copy = 0; copy < 2; copy++) {
		if (!status) {
			struct n10_ehld_lock_row *r = &n10_ehld_lock_report.row;
			EHLD_ROW("N10ELM1", "id=%s copy=%u generation=%u index=%u chain_count=%u lock_available=%u running_valid=%u running=%u",
				 N10_RESERVE_BUILD_ID, copy, generation, r->index,
				 r->chain_count, r->lock_available, r->running_valid,
				 r->running);
		}
		EHLD_ROW("N10ELQ1", "id=%s copy=%u generation=%u status=%d row_count=%u complete=%u",
			 N10_RESERVE_BUILD_ID, copy, generation, status,
			 status ? 0 : 1, status ? 0 : n10_ehld_lock_report.completed);
	}
#undef EHLD_ROW
	return 0;
}
static int n10_report_ehld_lock(unsigned int completed, int outer_error)
{
	unsigned int generation = completed == 1 ? 0xffffffffU : completed - 1;
	int ret;
	memset(&n10_ehld_lock_report, 0, sizeof(n10_ehld_lock_report));
	ret = n10_ehld_lock_read(&n10_ehld_lock_report, completed);
	if (!ret && outer_error)
		ret = outer_error;
	if (!ret)
		ret = n10_ehld_lock_emit_all(0, 0, generation);
	if (ret) {
		(void)n10_ehld_lock_emit_all(1, ret, generation);
		return ret;
	}
	return n10_ehld_lock_emit_all(1, 0, generation);
}
