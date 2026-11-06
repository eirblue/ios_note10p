/* Selected builtin Exynos ION import boundary; no DMA terminal claim. */
#ifndef N144_IVA_BUFFER_H
#define N144_IVA_BUFFER_H
#include <linux/dma-buf.h>
#include <linux/err.h>

/* Actual global const provider, drivers/staging/android/ion/ion.c:443. */
extern const struct dma_buf_ops ion_dma_buf_ops;

struct n144_buffer_call {
	struct dma_buf *foreign_put;
	bool active;
	bool refused_history;
};

static inline void n144_buffer_call_init(struct n144_buffer_call *call)
{
	call->foreign_put = NULL;
	call->active = true;
	call->refused_history = false;
}

static inline bool n144_buffer_call_ready(struct n144_buffer_call *call)
{
	if (!call)
		return false;
	if (!call->active || call->foreign_put || call->refused_history) {
		call->refused_history = true;
		return false;
	}
	return true;
}

/* Last wrapper action: exporter.release may unbind and free native objects. */
static inline void n144_buffer_call_finish(struct n144_buffer_call *call)
{
	struct dma_buf *foreign;

	if (!call || !call->active)
		return;
	foreign = call->foreign_put;
	call->foreign_put = NULL;
	call->active = false;
	if (IS_ERR(foreign)) {
		call->refused_history = true;
		return;
	}
	if (foreign)
		dma_buf_put(foreign);
}
#endif
