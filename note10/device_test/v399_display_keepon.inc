
/*
 * v399 note10 loader display keep-on (appended to drivers/video/fbdev/exynos/dpu20/decon_dsi.c by v399_prepare.py).
 * Called once from n302_park_write in process context, after the XNU image load and before stop_machine. The stock
 * driver puts the idle command-mode DECON0 into hibernation (DSIM ULPS, D-PHY isolated, pd-dpu off, panel kept on);
 * XNU cannot reach DECON0 then. Two stock driver calls only:
 *   decon_hiber_block_exit(): raise the hibernation block count and leave hibernation through the driver's own path
 *     (decon_exit_hiber: pd-dpu power-on via runtime PM, DSIM ULPS exit, DECON register init); the count is never released,
 *     so the hibernation thread cannot enter again before the branch;
 *   fb_pan_display() on decon0's fb with x/y offset 0, under lock_fb_info + console_lock as the FBIOPAN_DISPLAY ioctl
 *     (decon_pan_display: window + DPP channel on the fb buffer, one frame, trigger masked after the frame).
 * Best effort: any failure is logged and ignored (the branch proceeds; XNU then stays read-only by its own checks).
 */
#if IS_ENABLED(CONFIG_NOTE10_BUILTIN_INIT_ROUTE) && IS_ENABLED(CONFIG_NOTE10_V154_LINUX_DIAGNOSTIC)
#include <linux/console.h>
int noinline n399_display_keep_on(void)
{
	struct decon_device *decon = decon_drvdata[0];
	struct fb_var_screeninfo var;
	struct fb_info *info;
	int state, hiber, pan = -EBUSY;

	if (!decon || decon->dt.out_type != DECON_OUT_DSI || decon->dt.dft_win < 0 ||
	    decon->dt.dft_win >= MAX_DECON_WIN || !decon->win[decon->dt.dft_win] ||
	    !decon->win[decon->dt.dft_win]->fbinfo) {
		pr_info("N399K skip decon=%d\n", decon ? 1 : 0);
		return -ENODEV;
	}
	info = decon->win[decon->dt.dft_win]->fbinfo;
	state = decon->state;
	hiber = decon_hiber_block_exit(decon);
	if (lock_fb_info(info)) {
		var = info->var;
		var.xoffset = 0;
		var.yoffset = 0;
		console_lock();
		pan = fb_pan_display(info, &var);
		console_unlock();
		unlock_fb_info(info);
	}
	pr_info("N399K state=%d->%d hiber=%d pan=%d block=%d\n", state, decon->state, hiber, pan,
		atomic_read(&decon->hiber.block_cnt));
	return pan;
}
#endif
