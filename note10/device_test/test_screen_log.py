"""Portable renderer and pinned source integration checks; no phone access."""
import argparse
import hashlib
import json
import re
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from prepare_screen_log import prepare,PINS,HERE
from run_probe import ROOT

def hardware_model():
    supported=dict(id=0,command=True,single_dsi=True,width=1440,height=3040,
        dsc=True,dsc_cnt=2,slices=2,enc=240,dec=720,slice_h=40)
    rect=(0,0,719,1519)
    def route(marked=True, cfg=None, area=rect, active=False, idle=True,
              setarea=True, frame=True, shadow=True, restore=True):
        cfg=cfg or supported
        if active and not marked:
            if not restore: return False, True
            active=False
        if not marked: return True, active
        if cfg != supported or area != rect or not idle or not setarea:
            return False, active
        if not frame or not shadow: return False, True
        return True, True
    cases=[route(),route(cfg={**supported,'dsc_cnt':1}),route(area=(1,0,719,1519)),
        route(idle=False),route(setarea=False),route(frame=False),route(shadow=False),
        route(marked=False,active=True,restore=False)]
    assert cases[0] == (True,True)
    assert all(not result[0] for result in cases[1:])
    assert cases[-1] == (False,True)
    return len(cases)

HARNESS=r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "screen_log_core.h"
static unsigned int pixels[1440 * 3040 + 16];
static unsigned char font[1520];
static struct n10_screen_text text;
static struct n10_screen_text bridge;
#define CHECK(c) do { if (!(c)) { fprintf(stderr,"line %d\n",__LINE__); return 1; } } while(0)
int main(void) {
    unsigned int w,h,x,y,i;
    char compact[N10_SCREEN_COLUMNS];
    CHECK(!n10_screen_geometry(1440,3040,720,40,&w,&h) && w==720 && h==1520);
    CHECK(n10_screen_geometry(10,10,1,1,&w,&h));
    CHECK(n10_screen_geometry(1440,3040,0,1,&w,&h));
    CHECK(n10_screen_geometry(0xffffffffU,3040,1,1,&w,&h));
    n10_screen_line(compact,"N10PMT1 id=abc seq=0 before=ff cycle=abc status=4 error=16 checksum=123");
    CHECK(!strcmp(compact,"N10PMT1 status=4 error=16 before=ff"));
    /* Direct producer records work before init, keep seq=0, bound copies. */
    CHECK(n10_screen_record(&bridge,"id=abc seq=1 pages=8",sizeof("id=abc seq=1 pages=8")-1)==0 && bridge.count==0);
    CHECK(n10_screen_record(&bridge,"id=abc seq=0 pages=8 status=1",sizeof("id=abc seq=0 pages=8 status=1")-1)==1 && bridge.count==1);
    CHECK(!strcmp(bridge.line[0],"N10RAM2 status=1 pages=8"));
    CHECK(n10_screen_seed_title(&bridge,"NOTE10 diagnostic log") && bridge.count==2);
    CHECK(!strcmp(bridge.line[0],"NOTE10 diagnostic log") &&
          !strcmp(bridge.line[1],"N10RAM2 status=1 pages=8"));
    CHECK(n10_screen_record(&bridge,"id=abc seq=0 pages=8",sizeof("id=abc seq=0 pages=8")-1)==1 && bridge.count==3);
    { char long_frame[257]; memset(long_frame,'x',sizeof(long_frame));
      CHECK(n10_screen_record(&bridge,long_frame,255)==1);
      CHECK(n10_screen_record(&bridge,long_frame,256)==0); }
    CHECK(bridge.count==4);
    memset(font,0xff,sizeof(font));
    for(i=0;i<sizeof(pixels)/sizeof(pixels[0]);++i)pixels[i]=0x12345678;
    text.count=64;
    memset(text.line,'A',sizeof(text.line)); /* Non-terminated rows exercise bounded wrap/scroll. */
    CHECK(!n10_screen_render(pixels,1440UL*3040,720,1520,1440,font,&text));
    for(y=0;y<3040;++y)for(x=0;x<1440;++x)
        if(x>=720||y>=1520)CHECK(pixels[y*1440+x]==0x12345678);
    for(i=1440*3040;i<sizeof(pixels)/sizeof(pixels[0]);++i)CHECK(pixels[i]==0x12345678);
    CHECK(n10_screen_render(pixels,10,720,1520,1440,font,&text));
    CHECK(n10_screen_render(pixels,1440UL*3040,720,1520,1,font,&text));
    text.count=65;CHECK(n10_screen_render(pixels,1440UL*3040,720,1520,1440,font,&text));
    puts("renderer_cases=9 bridge_cases=6 passed=1");return 0;
}
'''

def test(output):
    output=Path(output).resolve()
    if not output.is_relative_to((ROOT/'note10/private').resolve()) or output.exists():raise ValueError('Fresh private output required')
    output.mkdir(parents=True)
    cc=shutil.which('cc') or shutil.which('clang')
    if sys.platform=='win32':cc=str(ROOT/'host-tools/windows-build/llvm-mingw/llvm-mingw-20261006-ucrt-x86_64/bin/clang.exe')
    harness=output/'renderer.c';harness.write_text(HARNESS,encoding='utf-8')
    exe=output/('renderer.exe' if sys.platform=='win32' else 'renderer')
    result=subprocess.run([cc,'-std=c11','-Wall','-Wextra','-Werror','-I'+str(HERE),str(harness),'-o',str(exe)],capture_output=True,timeout=60)
    (output/'compile.log').write_bytes(result.stdout+result.stderr)
    if result.returncode:raise ValueError('Renderer native compilation failed')
    result=subprocess.run([str(exe)],capture_output=True,timeout=30)
    (output/'renderer.log').write_bytes(result.stdout+result.stderr)
    if result.returncode:raise ValueError('Renderer guard/wrap/scroll cases failed')
    fixture=output/'pinned-source'
    for name,digest in PINS.items():
        path=fixture/name;path.parent.mkdir(parents=True,exist_ok=True)
        raw=urllib.request.urlopen('https://raw.githubusercontent.com/corsicanu/android_kernel_samsung_universal9820/55f042627bb7030c93550faafa117674d32b21d1/'+name,timeout=40).read()
        if hashlib.sha256(raw).hexdigest()!=digest:raise ValueError('Pinned test fixture differs')
        path.write_bytes(raw)
    prepared=prepare(fixture)
    core=(fixture/'drivers/video/fbdev/exynos/dpu20/decon_core.c').read_text()
    screen=(HERE/'screen_log.c').read_text()
    reserve=(HERE/'xnu_reserve.c').read_text()
    update=(fixture/'drivers/video/fbdev/exynos/dpu20/win_update.c').read_text()
    dcal=(fixture/'drivers/video/fbdev/exynos/dpu20/cal_9820/decon_reg.c').read_text()
    scal=(fixture/'drivers/video/fbdev/exynos/dpu20/cal_9820/dsim_reg.c').read_text()
    assert 'regs->up_region.right >= decon->lcd_info->xres / 2' in core
    assert 'regs->up_region.bottom >= decon->lcd_info->yres / 2' in core
    assert 'win_data->config[DECON_WIN_UPDATE_IDX].color == N10_SCREEN_MAGIC' in core
    assert 'update_config->color != N10_SCREEN_MAGIC' in update
    assert 'if (regs->n10_screen_error) return regs->n10_screen_error;' in core
    assert 'DPATH_DSCENC0_OUTFIFO0_DSIMIF0' in dcal and 'DPATH_DSCC_DSCENC01_OUTFIFO01_DSIMIF0' in dcal
    assert 'dsc_enc_sw * lcd_info->dsc_slice_num' in scal
    assert 'decon->lcd_info->dsc_cnt != 2' in update
    assert 'regs->up_region.right != 719' in update and 'regs->up_region.bottom != 1519' in update
    assert 'dpu_note10_screen_restore' in update
    start=core.index('regs->n10_frame_target = regs->n10_frame_before + 1;')
    assert start < core.index('if (decon_reg_start(decon->id, &psr) < 0)',start)
    assert 'READ_ONCE(decon->frame_cnt) >= regs->n10_frame_target' in core
    assert 'frame-start-error' in core and 'shadow_done=1' in core
    assert 'if (regs->n10_screen && n10_shadow_wait < 0) return n10_shadow_wait;' in core
    assert 'if (regs->n10_screen) {\n            WRITE_ONCE(n10_screen_last_error, -EIO);' in core
    assert 'if (!mutex_trylock(&decon->lock)) return -EBUSY;' in core and 'decon->state = DECON_STATE_ON;' in core
    assert 'enable_irq(decon->res.irq);' in core and 'if (!decon->eint_status)' in core
    assert 'lcd_info.dsc_slice_num = 1;' in update and 'lcd_info.dsc_cnt = 1;' in update
    assert 'n10_screen_hw_active = false;' in update and 'n10_screen_hw_active = true;' in update
    assert 'n10_screen_event(note, note_len);' in core
    assert core.count('WRITE_ONCE(n10_screen_last_error, -EIO)')==3
    assert 'n10_screen_frame(text, length);' in reserve
    assert 'WRITE_ONCE(n10_screen_last_error, -EINPROGRESS);' in screen
    checksum_body=re.search(r'static u32 n10_frame_checksum\([^}]+}',reserve,re.S).group(0)
    assert checksum_body.count('value = (value ^ (unsigned char)text[i]) * 16777619U;')==1
    assert checksum_body.index('n10_screen_frame(text, length);') > checksum_body.index('for (i = 0; i < length; ++i)')
    assert checksum_body.index('return value;') > checksum_body.index('n10_screen_frame(text, length);')
    assert 'n10_screen_seed_title(&n10_screen_ring' in screen
    assert core.count('decon_reg_set_trigger(decon->id, &psr, DECON_TRIG_DISABLE);') >= 3
    try:prepare(fixture)
    except ValueError:pass
    else:raise AssertionError('Modified source accepted')
    report=dict(passed=True,renderer_cases=9,bridge_cases=6,hardware_cases=hardware_model(),source_contracts=29,source_sha256=prepared['screen_log_sources_sha256'],
        physical_display_verified=False,partial_panel_update_verified=False)
    (output/'result.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();print(json.dumps(test(args.output)))
