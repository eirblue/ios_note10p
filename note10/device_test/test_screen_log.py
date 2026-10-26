"""Portable renderer and pinned source integration checks; no phone access."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from prepare_screen_log import prepare,PINS,HERE
from run_probe import ROOT

HARNESS=r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "screen_log_core.h"
static unsigned int pixels[1440 * 3040 + 16];
static unsigned char font[1520];
static struct n10_screen_text text;
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
    puts("renderer_cases=9 passed=1");return 0;
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
    update=(fixture/'drivers/video/fbdev/exynos/dpu20/win_update.c').read_text()
    assert 'regs->up_region.right >= decon->lcd_info->xres / 2' in core
    assert 'regs->up_region.bottom >= decon->lcd_info->yres / 2' in core
    assert 'win_data->config[DECON_WIN_UPDATE_IDX].color == N10_SCREEN_MAGIC' in core
    assert 'update_config->color != N10_SCREEN_MAGIC' in update
    assert 'if (regs->n10_screen_error) return;' in update
    assert core.count('WRITE_ONCE(n10_screen_last_error, -EIO)')==2
    try:prepare(fixture)
    except ValueError:pass
    else:raise AssertionError('Modified source accepted')
    report=dict(passed=True,renderer_cases=9,source_contracts=7,source_sha256=prepared['screen_log_sources_sha256'],
        physical_display_verified=False,partial_panel_update_verified=False)
    (output/'result.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();print(json.dumps(test(args.output)))
