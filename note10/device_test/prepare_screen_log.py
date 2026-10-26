"""Opt-in quarter-screen console integration for the pinned Samsung DPU."""
import hashlib
from pathlib import Path
import re

HERE=Path(__file__).resolve().parent
DPU='drivers/video/fbdev/exynos/dpu20/'
PINS = {'drivers/video/fbdev/exynos/dpu20/decon_core.c': '88899aa623e35a1f0a76b6571bc514691a0d876db7eb17b4c6553a3dfbfb7816', 'drivers/video/fbdev/exynos/dpu20/decon.h': '7a99fd3dd6846759f4a0a1ca5d586e52d5123835ba705159b9b82bc17504a56c', 'drivers/video/fbdev/exynos/dpu20/win_update.c': '9283437cbeb6e5b3957babdb62cd8d688bf4e7346f335ef7d1a480a0d39d9478', 'drivers/video/fbdev/exynos/dpu20/cal_9820/decon_reg.c': 'a6fa54305b75300685c18dfd76ad6bbd3b44e747e7a3180ccd86be42e409deaa', 'drivers/video/fbdev/exynos/dpu20/cal_9820/dsim_reg.c': '777aae74ccb2d00293dd4d0731f78a169d8f32650a4dd1f8b5697c61f34493f9', 'drivers/video/fbdev/exynos/dpu20/Kconfig': '3233d42a3ebfd648fc1e232fdeb0d2dfe3823d618d57e6573baebb128bc222cd', 'lib/fonts/font_8x16.c': 'bc1ab9dfce372a335a314867d2711912a60b5f7aeb7b89bbf7f1c3b1627c40a8'}

def replace(text,old,new):
    if text.count(old)!=1:raise ValueError('Pinned screen integration anchor differs: '+old[:60])
    return text.replace(old,new)

def prepare(source):
    source=Path(source)
    original={}
    for name,digest in PINS.items():
        raw=(source/name).read_bytes()
        if hashlib.sha256(raw).hexdigest()!=digest:raise ValueError('Pinned display source differs: '+name)
        original[name]=raw.decode(errors='surrogateescape')
    font=bytes(int(v,16) for v in re.findall(r'^\s*(0x[0-9a-f]{2}),',original['lib/fonts/font_8x16.c'],re.M))
    if len(font)!=4096:raise ValueError('Pinned font layout differs')
    folder=source/DPU
    for src,dst in (('screen_log_core.h','note10_screen_log_core.h'),('screen_log.c','note10_screen_log.c')):
        if (folder/dst).exists():raise ValueError('Screen source already exists')
        (folder/dst).write_bytes((HERE/src).read_bytes())
    (folder/'note10_screen_font.h').write_text('/* SPDX-License-Identifier: GPL-2.0 */\n/* ASCII subset of pinned Linux font_8x16.c. */\nstatic const unsigned char n10_screen_font[1520] = {'+
        ','.join(hex(v) for v in font[32*16:127*16])+'};\n',encoding='utf-8',errors='surrogateescape')
    header=original[DPU+'decon.h']
    header=replace(header,'struct decon_reg_data {','''#ifdef CONFIG_NOTE10_SCREEN_LOG
#include "note10_screen_log_core.h"
#endif
struct decon_reg_data {
#ifdef CONFIG_NOTE10_SCREEN_LOG
    bool n10_screen;
    int n10_screen_error;
#endif''')
    (folder/'decon.h').write_text(header,encoding='utf-8',errors='surrogateescape')
    update=original[DPU+'win_update.c']
    update=replace(update,'\t/* disable partial update */\n\treturn;','''\t/* Default vendor policy is unchanged for ordinary frames. */
#ifdef CONFIG_NOTE10_SCREEN_LOG
    if (update_config->state != DECON_WIN_STATE_UPDATE ||
        update_config->color != N10_SCREEN_MAGIC)
#endif
        return;''')
    update=replace(update,'\tr2.left = 0;\n\tr2.right = decon->lcd_info->xres - 1;','''#ifdef CONFIG_NOTE10_SCREEN_LOG
    if (update_config->color != N10_SCREEN_MAGIC) {
#endif
        r2.left = 0;
        r2.right = decon->lcd_info->xres - 1;
#ifdef CONFIG_NOTE10_SCREEN_LOG
    }
#endif''')
    update=replace(update,'\tcall_panel_ops(dsim, setarea, dsim,\n\t\t\trect->left, rect->right, rect->top, rect->bottom);\n\n\treturn 0;',
        '\treturn call_panel_ops(dsim, setarea, dsim,\n\t\t\trect->left, rect->right, rect->top, rect->bottom);')
    update=replace(update,'\t\twin_update_send_partial_command(dsim, &regs->up_region);','''#ifdef CONFIG_NOTE10_SCREEN_LOG
        if (regs->n10_screen) {
            regs->n10_screen_error = win_update_send_partial_command(dsim, &regs->up_region);
            if (regs->n10_screen_error) return;
        } else
#endif
            win_update_send_partial_command(dsim, &regs->up_region);''')
    start=update.index('static void win_update_set_partial_size(')
    end=update.index('\nvoid dpu_set_win_update_config',start)
    update=update[:start]+'''#ifdef CONFIG_NOTE10_SCREEN_LOG
static bool n10_screen_hw_active;
#endif
static int win_update_set_partial_size(struct decon_device *decon,
        struct decon_rect *rect, bool n10_single)
{
    struct decon_lcd lcd_info;
    struct dsim_device *dsim = get_dsim_drvdata(0);
    bool in_slice[MAX_DSC_SLICE_CNT];
    if (IS_ERR_OR_NULL(dsim)) return -ENODEV;
    memcpy(&lcd_info, decon->lcd_info, sizeof(struct decon_lcd));
    lcd_info.xres = rect->right - rect->left + 1;
    lcd_info.yres = rect->bottom - rect->top + 1;
    lcd_info.hfp = decon->lcd_info->hfp +
        ((decon->lcd_info->xres - lcd_info.xres) >> 1);
    lcd_info.vfp = decon->lcd_info->vfp + decon->lcd_info->yres - lcd_info.yres;
#ifdef CONFIG_NOTE10_SCREEN_LOG
    if (n10_single) {
        lcd_info.dsc_cnt = 1;
        lcd_info.dsc_slice_num = 1;
        lcd_info.dsc_enc_sw = 240;
        lcd_info.dsc_dec_sw = 720;
        lcd_info.dsc_slice_h = 40;
        dsim_reg_note10_partial_update(dsim->id, &lcd_info);
        decon_reg_note10_partial_update(decon->id, &lcd_info, true);
        return 0;
    }
#endif
    dsim_reg_set_partial_update(dsim->id, &lcd_info);
    win_update_find_included_slice(decon->lcd_info, rect, in_slice);
    decon_reg_set_partial_update(decon->id, decon->dt.dsi_mode,
            decon->lcd_info, in_slice, lcd_info.xres, lcd_info.yres);
#ifdef CONFIG_NOTE10_SCREEN_LOG
    if (!decon->id && n10_screen_hw_active)
        decon_reg_note10_partial_update(decon->id, decon->lcd_info, false);
#endif
    return 0;
}
''' + update[end:]
    start=update.index('void dpu_set_win_update_config(')
    end=update.index('\nvoid dpu_set_win_update_partial_size',start)
    update=update[:start]+'''void dpu_set_win_update_config(struct decon_device *decon,
        struct decon_reg_data *regs)
{
    struct dsim_device *dsim = get_dsim_drvdata(0);
    bool full_partial_update = false;
    bool marked = false;
    struct decon_rect full;
    int ret;
    if (!decon->win_up.enabled || decon->dt.out_type != DECON_OUT_DSI) return;
    if (regs == NULL) {
        regs = kzalloc(sizeof(struct decon_reg_data), GFP_KERNEL);
        if (!regs) { decon_err("%s: reg_data allocation fail\\n", __func__); return; }
        DPU_FULL_RECT(&regs->up_region, decon->lcd_info);
        regs->need_update = true;
        full_partial_update = true;
    }
#ifdef CONFIG_NOTE10_SCREEN_LOG
    marked = regs->n10_screen;
    if (marked && (decon->id || decon->dt.psr_mode != DECON_MIPI_COMMAND_MODE ||
        decon->dt.dsi_mode == DSI_MODE_DUAL_DSI || decon->lcd_info->xres != 1440 ||
        decon->lcd_info->yres != 3040 || !decon->lcd_info->dsc_enabled ||
        decon->lcd_info->dsc_cnt != 2 || decon->lcd_info->dsc_slice_num != 2 ||
        decon->lcd_info->dsc_enc_sw != 240 || decon->lcd_info->dsc_dec_sw != 720 ||
        decon->lcd_info->dsc_slice_h != 40 || regs->up_region.left != 0 ||
        regs->up_region.top != 0 || regs->up_region.right != 719 ||
        regs->up_region.bottom != 1519)) {
        regs->n10_screen_error = -EOPNOTSUPP;
        goto done;
    }
    if (marked && IS_ERR_OR_NULL(dsim)) {
        regs->n10_screen_error = -ENODEV;
        goto done;
    }
    if (marked && !n10_screen_hw_active) regs->need_update = true;
    if (!decon->id && n10_screen_hw_active && !marked) {
        DPU_FULL_RECT(&full, decon->lcd_info);
        ret = decon_reg_wait_idle_status_timeout(decon->id, IDLE_WAIT_TIMEOUT);
        if (ret) { regs->n10_screen_error = ret; goto done; }
        ret = win_update_send_partial_command(dsim, &full);
        if (ret) { regs->n10_screen_error = ret; goto done; }
        ret = win_update_set_partial_size(decon, &full, false);
        if (ret) { regs->n10_screen_error = ret; goto done; }
        dsim_reg_note10_partial_update(dsim->id, decon->lcd_info);
        n10_screen_hw_active = false;
        regs->need_update = true;
    }
#endif
    if (regs->need_update) {
        ret = decon_reg_wait_idle_status_timeout(decon->id, IDLE_WAIT_TIMEOUT);
#ifdef CONFIG_NOTE10_SCREEN_LOG
        if (marked && ret) { regs->n10_screen_error = ret; goto done; }
#endif
        ret = win_update_send_partial_command(dsim, &regs->up_region);
#ifdef CONFIG_NOTE10_SCREEN_LOG
        if (marked && ret) { regs->n10_screen_error = ret; goto done; }
#endif
        ret = win_update_set_partial_size(decon, &regs->up_region,
                marked && regs->up_region.left == 0 && regs->up_region.top == 0 &&
                regs->up_region.right == 719 && regs->up_region.bottom == 1519);
#ifdef CONFIG_NOTE10_SCREEN_LOG
        if (marked && ret) { regs->n10_screen_error = ret; goto done; }
        if (marked) n10_screen_hw_active = true;
#endif
        DPU_EVENT_LOG_APPLY_REGION(&decon->sd, &regs->up_region);
    }
done:
    if (full_partial_update) kfree(regs);
}
''' + update[end:]
    update=replace(update,'win_update_set_partial_size(decon, up_region);',
        'win_update_set_partial_size(decon, up_region, false);')
    update=replace(update,'\nvoid dpu_set_win_update_partial_size(struct decon_device *decon,','''
#ifdef CONFIG_NOTE10_SCREEN_LOG
int dpu_note10_screen_restore(struct decon_device *decon)
{
    struct dsim_device *dsim;
    struct decon_rect full;
    int ret = 0;
    if (!decon || decon->id) return -EINVAL;
    if (!n10_screen_hw_active) return 0;
    dsim = get_dsim_drvdata(0);
    if (IS_ERR_OR_NULL(dsim)) return -ENODEV;
    if (!mutex_trylock(&decon->lock)) return -EBUSY;
    if (n10_screen_hw_active) {
        DPU_FULL_RECT(&full, decon->lcd_info);
        ret = decon_reg_wait_idle_status_timeout(decon->id, IDLE_WAIT_TIMEOUT);
        if (!ret) ret = win_update_send_partial_command(dsim, &full);
        if (!ret) ret = win_update_set_partial_size(decon, &full, false);
        if (!ret) {
            decon_reg_note10_partial_update(decon->id, decon->lcd_info, false);
            dsim_reg_note10_partial_update(dsim->id, decon->lcd_info);
            n10_screen_hw_active = false;
        }
    }
    mutex_unlock(&decon->lock);
    return ret;
}
#endif

void dpu_set_win_update_partial_size(struct decon_device *decon,''')
    (folder/'win_update.c').write_text(update,encoding='utf-8',errors='surrogateescape')
    cal=folder/'cal_9820'
    decon_cal=original[DPU+'cal_9820/decon_reg.c']
    decon_cal=replace(decon_cal,'\nvoid decon_reg_set_mres(u32 id, struct decon_param *p)', '''
#ifdef CONFIG_NOTE10_SCREEN_LOG
void decon_reg_note10_partial_update(u32 id, struct decon_lcd *lcd, bool single)
{
    bool in_slice[MAX_DSC_SLICE_CNT] = { true, true, false, false };
    enum decon_data_path path = single ? DPATH_DSCENC0_OUTFIFO0_DSIMIF0 :
        DPATH_DSCC_DSCENC01_OUTFIFO01_DSIMIF0;
    decon_reg_set_data_path(id, path, SCALERPATH_OFF);
    decon_reg_set_partial_update(id, DSI_MODE_SINGLE, lcd, in_slice,
            lcd->xres, lcd->yres);
}
#endif

void decon_reg_set_mres(u32 id, struct decon_param *p)''')
    (cal/'decon_reg.c').write_text(decon_cal,encoding='utf-8',errors='surrogateescape')
    dsim_cal=original[DPU+'cal_9820/dsim_reg.c']
    dsim_cal=replace(dsim_cal,'\nvoid dsim_reg_set_mres(u32 id, struct decon_lcd *lcd_info)', '''
#ifdef CONFIG_NOTE10_SCREEN_LOG
void dsim_reg_note10_partial_update(u32 id, struct decon_lcd *lcd_info)
{
    dsim_reg_set_partial_update(id, lcd_info);
    dsim_reg_set_threshold(id, lcd_info->dsc_enc_sw * lcd_info->dsc_slice_num);
    dsim_reg_set_num_of_slice(id, lcd_info->dsc_slice_num);
    dsim_reg_set_multi_slice(id, lcd_info);
    dsim_reg_set_size_of_slice(id, lcd_info);
}
#endif

void dsim_reg_set_mres(u32 id, struct decon_lcd *lcd_info)''')
    (cal/'dsim_reg.c').write_text(dsim_cal,encoding='utf-8',errors='surrogateescape')
    header=header.replace('    int n10_screen_error;','    int n10_screen_error;\n    unsigned int n10_frame_target;\n    unsigned int n10_frame_before;\n    unsigned int n10_frame_after;')
    header=replace(header,'void dpu_save_fence_info(int fd, struct dma_fence *fence,', '''#ifdef CONFIG_NOTE10_SCREEN_LOG
void decon_reg_note10_partial_update(u32 id, struct decon_lcd *lcd, bool single);
void dsim_reg_note10_partial_update(u32 id, struct decon_lcd *lcd);
int dpu_note10_screen_restore(struct decon_device *decon);
void n10_screen_event(const char *text, unsigned int length);
#endif
void dpu_save_fence_info(int fd, struct dma_fence *fence,''')
    (folder/'decon.h').write_text(header,encoding='utf-8',errors='surrogateescape')
    core=original[DPU+'decon_core.c']
    core=replace(core,'#define PROFILE_DECON_DISABLE','''#define PROFILE_DECON_DISABLE
#ifdef CONFIG_NOTE10_SCREEN_LOG
static int n10_screen_last_error;
#endif''')
    core=replace(core,'\tdpu_prepare_win_update_config(decon, win_data, regs);','''#ifdef CONFIG_NOTE10_SCREEN_LOG
    regs->n10_screen = win_data->config[DECON_WIN_UPDATE_IDX].state == DECON_WIN_STATE_UPDATE &&
        win_data->config[DECON_WIN_UPDATE_IDX].color == N10_SCREEN_MAGIC;
#endif
    dpu_prepare_win_update_config(decon, win_data, regs);
#ifdef CONFIG_NOTE10_SCREEN_LOG
    if (regs->n10_screen && (!decon->win_up.enabled || regs->up_region.left ||
        regs->up_region.top || regs->up_region.right + 1 != win_data->config[DECON_WIN_UPDATE_IDX].dst.w ||
        regs->up_region.bottom + 1 != win_data->config[DECON_WIN_UPDATE_IDX].dst.h ||
        regs->up_region.right >= decon->lcd_info->xres / 2 ||
        regs->up_region.bottom >= decon->lcd_info->yres / 2)) {
        ret = -ERANGE;
        goto err_prepare;
    }
#endif''')
    core=replace(core,'\tdpu_set_win_update_config(decon, regs);','''    dpu_set_win_update_config(decon, regs);
#ifdef CONFIG_NOTE10_SCREEN_LOG
        if (regs->n10_screen_error) return regs->n10_screen_error;
#endif''')
    core=replace(core,"\tif (decon_reg_start(decon->id, &psr) < 0) {",'''#ifdef CONFIG_NOTE10_SCREEN_LOG
    if (regs->n10_screen) {
        if (decon->state != DECON_STATE_INIT && decon->state != DECON_STATE_ON)
            return -EHOSTDOWN;
        if (decon->state == DECON_STATE_INIT) {
            if (!mutex_trylock(&decon->lock)) return -EBUSY;
            if (decon->state == DECON_STATE_INIT) {
                if (!decon->eint_status) {
                    if (decon->res.irq <= 0) {
                        mutex_unlock(&decon->lock);
                        return -ENXIO;
                    }
                    enable_irq(decon->res.irq);
                    decon->eint_status = 1;
                }
                decon_to_psr_info(decon, &psr);
                decon_reg_set_int(decon->id, &psr, 1);
                decon->state = DECON_STATE_ON;
            }
            mutex_unlock(&decon->lock);
        }
        regs->n10_frame_before = READ_ONCE(decon->frame_cnt);
        regs->n10_frame_target = regs->n10_frame_before + 1;
    }
#endif
	if (decon_reg_start(decon->id, &psr) < 0) {
#ifdef CONFIG_NOTE10_SCREEN_LOG
        if (regs->n10_screen) {
            WRITE_ONCE(n10_screen_last_error, -EIO);
            decon_reg_set_trigger(decon->id, &psr, DECON_TRIG_DISABLE);
            return -EIO;
        }
#endif''')
    update_start=core.index('static int __decon_update_regs(')
    update_end=core.index('\nvoid decon_wait_for_vstatus',update_start)
    update_body=core[update_start:update_end]
    update_body=replace(update_body,'int err_cnt = 0;','int err_cnt = 0;\n\tint n10_shadow_wait;')
    update_body=replace(update_body,'if (decon_reg_wait_update_done_and_mask(decon->id, &psr,\n\t\t\t\tSHADOW_UPDATE_TIMEOUT) > 0) {','''n10_shadow_wait = decon_reg_wait_update_done_and_mask(decon->id, &psr,
				SHADOW_UPDATE_TIMEOUT);
#ifdef CONFIG_NOTE10_SCREEN_LOG
    if (regs->n10_screen && n10_shadow_wait < 0) return n10_shadow_wait;
#endif
	if (n10_shadow_wait > 0) {''')
    core=core[:update_start]+update_body+core[update_end:]
    # Limit vendor panic suppression to the new diagnostic frame, not normal use.
    start=core.index('static void decon_update_regs(')
    end=core.index('\n#if defined(CONFIG_EXYNOS_COMMON_PANEL)',core.index('\nfence_err:',start))
    body=core[start:end]
    if body.count('BUG();')!=2:raise ValueError('Pinned display timeout paths differ')
    body=body.replace('BUG();','''#ifdef CONFIG_NOTE10_SCREEN_LOG
            if (regs->n10_screen || regs->n10_screen_error) {
                WRITE_ONCE(n10_screen_last_error, -EIO);
                decon_reg_set_trigger(decon->id, &psr, DECON_TRIG_DISABLE);
                goto end;
            }
#endif
            BUG();''')
    body=replace(body,'\t\tdecon_wait_for_vstatus(decon, 50);','''#ifdef CONFIG_NOTE10_SCREEN_LOG
        if (regs->n10_screen) {
            long frame_wait;
            char note[160];
            int note_len;
            extern void n10_screen_event(const char *text, unsigned int length);
            frame_wait = wait_event_interruptible_timeout(decon->wait_vstatus,
                    READ_ONCE(decon->frame_cnt) >= regs->n10_frame_target,
                    msecs_to_jiffies(50));
            regs->n10_frame_after = READ_ONCE(decon->frame_cnt);
            if (frame_wait <= 0) {
                int error = frame_wait < 0 ? (int)frame_wait : -ETIMEDOUT;
                WRITE_ONCE(n10_screen_last_error, error);
                note_len = scnprintf(note, sizeof(note),
                    "N10DSP2 status=frame-start-error before=%u target=%u after=%u error=%d",
                    regs->n10_frame_before, regs->n10_frame_target,
                    regs->n10_frame_after, error);
                n10_screen_event(note, note_len);
                decon_reg_set_trigger(decon->id, &psr, DECON_TRIG_DISABLE);
                goto end;
            }
        } else
#endif
            decon_wait_for_vstatus(decon, 50);''')
    body=replace(body,'\t\tif (decon_reg_wait_update_done_timeout(decon->id, SHADOW_UPDATE_TIMEOUT) < 0) {','''		if (decon_reg_wait_update_done_timeout(decon->id, SHADOW_UPDATE_TIMEOUT) < 0) {
#ifdef CONFIG_NOTE10_SCREEN_LOG
            if (regs->n10_screen) {
                WRITE_ONCE(n10_screen_last_error, -ETIMEDOUT);
                n10_screen_event("N10DSP2 status=shadow-error shadow_done=0",
                    sizeof("N10DSP2 status=shadow-error shadow_done=0") - 1);
                decon_reg_set_trigger(decon->id, &psr, DECON_TRIG_DISABLE);
                goto end;
            }
#endif''')
    body=replace(body,'\n\t\t}\n#ifdef CONFIG_SUPPORT_HMD','''
		}
#ifdef CONFIG_NOTE10_SCREEN_LOG
        if (regs->n10_screen) {
            char note[160];
            int note_len;
            extern void n10_screen_event(const char *text, unsigned int length);
            note_len = scnprintf(note, sizeof(note),
                "N10DSP2 status=frame-start-ok before=%u target=%u after=%u shadow_done=1",
                regs->n10_frame_before, regs->n10_frame_target, regs->n10_frame_after);
            n10_screen_event(note, note_len);
            WRITE_ONCE(n10_screen_last_error, 0);
        }
#endif
#ifdef CONFIG_SUPPORT_HMD''')
    core=core[:start]+body+core[end:]
    core+='\n#ifdef CONFIG_NOTE10_SCREEN_LOG\n#include "note10_screen_log.c"\n#endif\n'
    (folder/'decon_core.c').write_text(core,encoding='utf-8',errors='surrogateescape')
    config=original[DPU+'Kconfig']+'''
config NOTE10_SCREEN_LOG
    bool "Experimental Note10 top-left quarter diagnostic console"
    depends on EXYNOS_DPU20 && EXYNOS_WINDOW_UPDATE && !SUPPORT_LEGACY_ION && !SUPPORT_LEGACY_FENCE
    default n
'''
    (folder/'Kconfig').write_text(config,encoding='utf-8',errors='surrogateescape')
    changed={name:hashlib.sha256((source/name).read_bytes()).hexdigest() for name in PINS if name!='lib/fonts/font_8x16.c'}
    return dict(screen_log_diagnostic=True,screen_log_version=1,screen_log_layout='top-left-quarter',
        screen_log_sources_sha256={n:hashlib.sha256((HERE/n).read_bytes()).hexdigest() for n in ('screen_log.c','screen_log_core.h','prepare_screen_log.py','xnu_reserve.c')},
        screen_log_upstream_pins=PINS,screen_log_patched_sha256=changed,screen_log_visual_verified=False)

def validate_model(root,build):
    import json
    model=json.loads((Path(root)/'screen-log-model/result.json').read_text())
    pm=json.loads((Path(root)/'pm-timer-model/result.json').read_text())
    if pm.get('screen_pause_verified') is not True:raise ValueError('PM screen pause model required')
    current={name:hashlib.sha256((HERE/name).read_bytes()).hexdigest()
        for name in ('screen_log.c','screen_log_core.h','prepare_screen_log.py','xnu_reserve.c')}
    if (model.get('passed') is not True or model.get('renderer_cases')!=9 or model.get('bridge_cases')!=6 or
        model.get('hardware_cases')!=8 or model.get('source_contracts')!=29 or
        model.get('source_sha256')!=current or build.get('screen_log_sources_sha256')!=current or
        build.get('screen_log_version')!=1 or build.get('screen_log_layout')!='top-left-quarter' or
        b'N10DSP1' not in (Path(root)/'Image').read_bytes() or
        'CONFIG_NOTE10_SCREEN_LOG=y' not in (Path(root)/'handoff.config').read_text().splitlines()):
        raise ValueError('Screen log model/source/config binding differs')
