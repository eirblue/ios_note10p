/* SPDX-License-Identifier: GPL-2.0-only */
/* Included after decon_core.c. Experimental, opt-in, command-mode panel only. */
#include <linux/workqueue.h>
#include <linux/reboot.h>
#include <linux/syscalls.h>
#include <linux/file.h>
#include <linux/dma-fence.h>
#include "note10_screen_font.h"

static DEFINE_SPINLOCK(n10_screen_ring_lock);
static DEFINE_MUTEX(n10_screen_paint_lock);
static struct n10_screen_text n10_screen_ring, n10_screen_snapshot;
static char n10_screen_partial[256];
static unsigned int n10_screen_partial_length, n10_screen_generation, n10_screen_painted;
static bool n10_screen_paused, n10_screen_stopped;
static struct workqueue_struct *n10_screen_queue;
static struct dma_buf *n10_screen_buffers[2];
static void *n10_screen_maps[2];
static unsigned int n10_screen_width, n10_screen_height, n10_screen_next;
static unsigned int n10_screen_waits;
static void n10_screen_worker(struct work_struct *work);
static DECLARE_DELAYED_WORK(n10_screen_work, n10_screen_worker);

static int n10_screen_restore_if_active(void)
{
    struct decon_device *decon = get_decon_drvdata(0);
    int ret;
    if (!decon) return -ENODEV;
    ret = dpu_note10_screen_restore(decon);
    if (ret) pr_err("N10DSP2 restore_error=%d\n", ret);
    return ret;
}

/* Direct producer bridge: this runs from early init/PM paths, never printk. */
void n10_screen_frame(const char *text, unsigned int length)
{
    unsigned long flags;
    if (READ_ONCE(n10_screen_stopped) ||
        !spin_trylock_irqsave(&n10_screen_ring_lock, flags))
        return;
    if (n10_screen_record(&n10_screen_ring, text, length))
        ++n10_screen_generation;
    spin_unlock_irqrestore(&n10_screen_ring_lock, flags);
}

/* Bounded internal lifecycle/frame evidence, independent of console loglevel. */
void n10_screen_event(const char *text, unsigned int length)
{
    unsigned long flags;
    unsigned int i;
    char line[256];
    if (!text || !length || length >= sizeof(line) ||
        READ_ONCE(n10_screen_stopped) ||
        !spin_trylock_irqsave(&n10_screen_ring_lock, flags))
        return;
    for (i = 0; i < length; ++i) {
        unsigned char ch = (unsigned char)text[i];
        if (ch < 32 || ch > 126) {
            spin_unlock_irqrestore(&n10_screen_ring_lock, flags);
            return;
        }
        line[i] = (char)ch;
    }
    line[length] = 0;
    if (n10_screen_ring.count == N10_SCREEN_LINES) {
        memmove(n10_screen_ring.line[0], n10_screen_ring.line[1],
                (N10_SCREEN_LINES - 1) * N10_SCREEN_COLUMNS);
        --n10_screen_ring.count;
    }
    n10_screen_line(n10_screen_ring.line[n10_screen_ring.count++], line);
    ++n10_screen_generation;
    spin_unlock_irqrestore(&n10_screen_ring_lock, flags);
}

/* Console context: bounded copies only; no display calls or allocations. */
static void n10_screen_console_write(struct console *con, const char *s, unsigned int n)
{
    unsigned long flags;
    unsigned int i;
    (void)con;
    if (READ_ONCE(n10_screen_stopped) || !spin_trylock_irqsave(&n10_screen_ring_lock, flags))
        return;
    for (i = 0; i < n; ++i) {
        char ch = s[i];
        if (ch == '\n') {
            char *tag, *seq;
            n10_screen_partial[n10_screen_partial_length] = 0;
            tag = strstr(n10_screen_partial, "N10");
            seq = tag ? strstr(tag, " seq=") : NULL;
            /* Keep one representative of redundant checksummed frames. */
            if (tag && strncmp(tag, "N10DSP1", 7) &&
                (!seq || !strncmp(seq, " seq=0 ", 7))) {
                if (n10_screen_ring.count == N10_SCREEN_LINES) {
                    memmove(n10_screen_ring.line[0], n10_screen_ring.line[1],
                            (N10_SCREEN_LINES - 1) * N10_SCREEN_COLUMNS);
                    --n10_screen_ring.count;
                }
                n10_screen_line(n10_screen_ring.line[n10_screen_ring.count++], tag);
                ++n10_screen_generation;
            }
            n10_screen_partial_length = 0;
        } else if (n10_screen_partial_length < sizeof(n10_screen_partial) - 1) {
            n10_screen_partial[n10_screen_partial_length++] =
                ch >= 32 && ch <= 126 ? ch : ' ';
        }
    }
    spin_unlock_irqrestore(&n10_screen_ring_lock, flags);
}
static struct console n10_screen_console = {
    .name = "n10screen", .write = n10_screen_console_write,
    .flags = CON_ENABLED | CON_PRINTBUFFER, .index = -1,
};

/* Called before PM owns pm_mutex or enters any freezer/device phase. */
int n10_screen_pause(bool paused)
{
    int ret = 0;
    WRITE_ONCE(n10_screen_paused, paused);
    if (paused && n10_screen_queue) {
        cancel_delayed_work_sync(&n10_screen_work);
        mutex_lock(&n10_screen_paint_lock);
        mutex_unlock(&n10_screen_paint_lock);
        ret = n10_screen_restore_if_active();
    } else if (!paused && n10_screen_queue && !READ_ONCE(n10_screen_stopped)) {
        queue_delayed_work(n10_screen_queue, &n10_screen_work, msecs_to_jiffies(500));
    }
}

static int n10_screen_allocate(struct decon_device *decon)
{
    unsigned int i;
    size_t size;
    if (decon->id || decon->dt.out_type != DECON_OUT_DSI ||
        decon->lcd_info->mode != DECON_MIPI_COMMAND_MODE || !decon->win_up.enabled ||
        decon->dt.dsi_mode == DSI_MODE_DUAL_DSI ||
        n10_screen_geometry(decon->lcd_info->xres, decon->lcd_info->yres,
                            decon->win_up.rect_w, decon->win_up.rect_h,
                            &n10_screen_width, &n10_screen_height))
        return -EOPNOTSUPP;
    size = PAGE_ALIGN((size_t)n10_screen_width * n10_screen_height * 4);
    for (i = 0; i < 2; ++i) {
        n10_screen_buffers[i] = ion_alloc_dmabuf("ion_system_heap", size, 0);
        if (IS_ERR(n10_screen_buffers[i])) {
            n10_screen_buffers[i] = NULL;
            goto fail;
        }
        n10_screen_maps[i] = dma_buf_vmap(n10_screen_buffers[i]);
        if (IS_ERR_OR_NULL(n10_screen_maps[i])) {
            n10_screen_maps[i] = NULL;
            goto fail;
        }
    }
    return 0;
fail:
    for (i = 0; i < 2; ++i) {
        if (n10_screen_maps[i]) dma_buf_vunmap(n10_screen_buffers[i], n10_screen_maps[i]);
        if (n10_screen_buffers[i]) dma_buf_put(n10_screen_buffers[i]);
        n10_screen_maps[i] = NULL;
        n10_screen_buffers[i] = NULL;
    }
    return -ENOMEM;
}

static int n10_screen_submit(struct decon_device *decon, unsigned int index)
{
    struct decon_win_config_data data;
    struct decon_win_config *config;
    struct dma_fence *fence = NULL;
    int fd, ret, i;
    long waited;
    if (!current->files) return -ENXIO;
    memset(&data, 0, sizeof(data));
    data.retire_fence = -1;
    for (i = 0; i < MAX_DECON_WIN; ++i) {
        data.config[i].acq_fence = -1;
        data.config[i].rel_fence = -1;
    }
    get_dma_buf(n10_screen_buffers[index]);
    fd = dma_buf_fd(n10_screen_buffers[index], O_CLOEXEC);
    if (fd < 0) { dma_buf_put(n10_screen_buffers[index]); return fd; }
    config = &data.config[decon->dt.dft_win];
    config->state = DECON_WIN_STATE_BUFFER;
    config->fd_idma[0] = fd;
    config->fd_idma[1] = config->fd_idma[2] = -1;
    config->idma_type = decon->dt.dft_ch;
    config->format = DECON_PIXEL_FORMAT_ABGR_8888;
    config->plane_alpha = 255;
    config->blending = DECON_BLENDING_NONE;
    config->src.w = config->src.f_w = n10_screen_width;
    config->src.h = config->src.f_h = n10_screen_height;
    config->dst.w = n10_screen_width;
    config->dst.h = n10_screen_height;
    config->dst.f_w = decon->lcd_info->xres;
    config->dst.f_h = decon->lcd_info->yres;
    data.config[DECON_WIN_UPDATE_IDX].state = DECON_WIN_STATE_UPDATE;
    data.config[DECON_WIN_UPDATE_IDX].color = N10_SCREEN_MAGIC;
    data.config[DECON_WIN_UPDATE_IDX].dst = config->dst;
    WRITE_ONCE(n10_screen_last_error, -EINPROGRESS);
    ret = decon_set_win_config(decon, &data);
    if (!ret && data.retire_fence >= 0) fence = sync_file_get_fence(data.retire_fence);
    if (data.retire_fence >= 0) sys_close(data.retire_fence);
    for (i = 0; i < MAX_DECON_WIN; ++i)
        if (data.config[i].rel_fence >= 0) sys_close(data.config[i].rel_fence);
    sys_close(fd);
    if (ret) return ret;
    if (!fence) return -EIO;
    waited = dma_fence_wait_timeout(fence, false, msecs_to_jiffies(1500));
    dma_fence_put(fence);
    return waited > 0 ? READ_ONCE(n10_screen_last_error) : -ETIMEDOUT;
}

static void n10_screen_worker(struct work_struct *work)
{
    struct decon_device *decon;
    unsigned long flags;
    unsigned int generation;
    int ret = 0;
    (void)work;
    if (READ_ONCE(n10_screen_stopped) || READ_ONCE(n10_screen_paused)) return;
    decon = get_decon_drvdata(0);
    if (!decon || !decon->lcd_info || !decon->win[decon->dt.dft_win] ||
        !decon->up.thread || !IS_DECON_ON_STATE(decon)) {
        if (++n10_screen_waits < 20) goto again;
        ret = -ENODEV;
        goto stopped;
    }
    mutex_lock(&n10_screen_paint_lock);
    if (READ_ONCE(n10_screen_stopped) || READ_ONCE(n10_screen_paused)) goto unlock;
    if (!n10_screen_buffers[0]) ret = n10_screen_allocate(decon);
    if (ret) goto unlock;
    spin_lock_irqsave(&n10_screen_ring_lock, flags);
    n10_screen_snapshot = n10_screen_ring;
    generation = n10_screen_generation;
    spin_unlock_irqrestore(&n10_screen_ring_lock, flags);
    if (generation == n10_screen_painted) goto unlock;
    ret = dma_buf_begin_cpu_access(n10_screen_buffers[n10_screen_next], DMA_TO_DEVICE);
    if (ret) goto unlock;
    ret = n10_screen_render(n10_screen_maps[n10_screen_next],
          (unsigned long)n10_screen_width * n10_screen_height,
          n10_screen_width, n10_screen_height, n10_screen_width,
          n10_screen_font, &n10_screen_snapshot);
    if (dma_buf_end_cpu_access(n10_screen_buffers[n10_screen_next], DMA_TO_DEVICE)) ret = -EIO;
    if (!ret) ret = n10_screen_submit(decon, n10_screen_next);
    if (!ret) {
        n10_screen_next ^= 1;
        n10_screen_painted = generation;
        pr_info("N10DSP1 submit=ok width=%u height=%u visual_verified=0\n",
                n10_screen_width, n10_screen_height);
    }
unlock:
    mutex_unlock(&n10_screen_paint_lock);
    if (ret) goto stopped;
again:
    if (!READ_ONCE(n10_screen_stopped) && !READ_ONCE(n10_screen_paused))
        queue_delayed_work(n10_screen_queue, &n10_screen_work, msecs_to_jiffies(500));
    return;
stopped:
    n10_screen_restore_if_active();
    WRITE_ONCE(n10_screen_stopped, true);
    pr_info("N10DSP1 stopped error=%d visual_verified=0\n", ret);
}
static int n10_screen_reboot(struct notifier_block *nb, unsigned long action, void *data)
{
    (void)nb; (void)action; (void)data;
    WRITE_ONCE(n10_screen_stopped, true);
    /* Never wait on the display from the recovery restart route. */
    return NOTIFY_DONE;
}
static struct notifier_block n10_screen_reboot_notifier = { .notifier_call = n10_screen_reboot };
static int __init n10_screen_init(void)
{
    unsigned long flags;
    n10_screen_queue = alloc_workqueue("n10_screen", WQ_UNBOUND | WQ_FREEZABLE, 1);
    if (!n10_screen_queue) return -ENOMEM;
    /* A direct checksummed frame may arrive before this late initcall. */
    spin_lock_irqsave(&n10_screen_ring_lock, flags);
    if (n10_screen_seed_title(&n10_screen_ring,
            "NOTE10 diagnostic log / top-left 1/4")) ++n10_screen_generation;
    spin_unlock_irqrestore(&n10_screen_ring_lock, flags);
    register_reboot_notifier(&n10_screen_reboot_notifier);
    register_console(&n10_screen_console);
    queue_delayed_work(n10_screen_queue, &n10_screen_work, msecs_to_jiffies(1000));
    return 0;
}
late_initcall(n10_screen_init);
