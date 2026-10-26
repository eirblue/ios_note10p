"""Opt-in quarter-screen console integration for the pinned Samsung DPU."""
import hashlib
from pathlib import Path
import re

HERE=Path(__file__).resolve().parent
DPU='drivers/video/fbdev/exynos/dpu20/'
PINS = {'drivers/video/fbdev/exynos/dpu20/decon_core.c': '88899aa623e35a1f0a76b6571bc514691a0d876db7eb17b4c6553a3dfbfb7816', 'drivers/video/fbdev/exynos/dpu20/decon.h': '7a99fd3dd6846759f4a0a1ca5d586e52d5123835ba705159b9b82bc17504a56c', 'drivers/video/fbdev/exynos/dpu20/win_update.c': '9283437cbeb6e5b3957babdb62cd8d688bf4e7346f335ef7d1a480a0d39d9478', 'drivers/video/fbdev/exynos/dpu20/Kconfig': '3233d42a3ebfd648fc1e232fdeb0d2dfe3823d618d57e6573baebb128bc222cd', 'lib/fonts/font_8x16.c': 'bc1ab9dfce372a335a314867d2711912a60b5f7aeb7b89bbf7f1c3b1627c40a8'}

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
    (folder/'win_update.c').write_text(update,encoding='utf-8',errors='surrogateescape')
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
    if (regs->n10_screen && regs->n10_screen_error) return regs->n10_screen_error;
#endif''')
    # Limit vendor panic suppression to the new diagnostic frame, not normal use.
    start=core.index('static void decon_update_regs(')
    end=core.index('\n#if defined(CONFIG_EXYNOS_COMMON_PANEL)',core.index('\nfence_err:',start))
    body=core[start:end]
    if body.count('BUG();')!=2:raise ValueError('Pinned display timeout paths differ')
    body=body.replace('BUG();','''#ifdef CONFIG_NOTE10_SCREEN_LOG
            if (regs->n10_screen) {
                WRITE_ONCE(n10_screen_last_error, -EIO);
                goto end;
            }
#endif
            BUG();''')
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
        screen_log_sources_sha256={n:hashlib.sha256((HERE/n).read_bytes()).hexdigest() for n in ('screen_log.c','screen_log_core.h','prepare_screen_log.py')},
        screen_log_upstream_pins=PINS,screen_log_patched_sha256=changed,screen_log_visual_verified=False)

def validate_model(root,build):
    import json
    model=json.loads((Path(root)/'screen-log-model/result.json').read_text())
    pm=json.loads((Path(root)/'pm-timer-model/result.json').read_text())
    if pm.get('screen_pause_verified') is not True:raise ValueError('PM screen pause model required')
    current={name:hashlib.sha256((HERE/name).read_bytes()).hexdigest()
        for name in ('screen_log.c','screen_log_core.h','prepare_screen_log.py')}
    if (model.get('passed') is not True or model.get('renderer_cases')!=9 or
        model.get('source_sha256')!=current or build.get('screen_log_sources_sha256')!=current or
        build.get('screen_log_version')!=1 or build.get('screen_log_layout')!='top-left-quarter' or
        b'N10DSP1' not in (Path(root)/'Image').read_bytes() or
        'CONFIG_NOTE10_SCREEN_LOG=y' not in (Path(root)/'handoff.config').read_text().splitlines()):
        raise ValueError('Screen log model/source/config binding differs')
