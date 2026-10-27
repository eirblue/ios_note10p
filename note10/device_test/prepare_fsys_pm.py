"""Bind passive tracing to original FSYS0A power-off decisions and results."""
import hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parent
PINS={
 'drivers/soc/samsung/exynos-pd.c':'85b06712441f23b94f2ee0a2dfd924d5d8596a5ff7fb74c042a1f3a7bd467cbf',
 'include/soc/samsung/exynos-pd.h':'4ec0ed654af9671fd4157e79619d4f6d9919bf1db9672691b241e89330bebffe',
 'drivers/usb/dwc3/otg.c':'f8ca1ef72d8eaef9e9377b6ebb6b26bc12c8290d0b502a18bc8fc191017d12de',
}
PREFIX=b'#ifdef CONFIG_NOTE10_ABOX_PMU_AUDIT\n#include <linux/note10_abox_pmu.h>\n#endif\n'
SUFFIX=b'\n#ifdef CONFIG_NOTE10_ABOX_PMU_AUDIT\n#include "note10_fsys_pm.c"\n#endif\n'
def note(event,result='0'):
 return ('#ifdef CONFIG_NOTE10_ABOX_PMU_AUDIT\n\tn10_fsys_note(pd, '+str(event)+', '+result+');\n#endif\n').encode()
def instrument(raw):
 if hashlib.sha256(raw).hexdigest()!=PINS['drivers/soc/samsung/exynos-pd.c']:raise ValueError('Pinned power-domain source differs')
 start=raw.index(b'static int exynos_pd_power_off(');end=raw.index(b'\n#ifdef CONFIG_OF',start);body=raw[start:end]
 anchor=b'\tmutex_lock(&pd->access_lock);';assert body.count(anchor)==1;body=body.replace(anchor,anchor+b'\n'+note(6))
 old=b'\tif (pd->power_down_ok && !pd->power_down_ok()) {'
 new=b'#ifdef CONFIG_NOTE10_ABOX_PMU_AUDIT\n\tif (pd->power_down_ok && !n10_fsys_gate(pd)) {\n#else\n'+old+b'\n#endif'
 assert body.count(old)==1;body=body.replace(old,new)
 anchor=b'\t\tpd->power_down_skipped = true;';assert body.count(anchor)==1;body=body.replace(anchor,anchor+b'\n'+note(3))
 # Preserve both original control calls, including the existing forced retry.
 import re
 pattern=rb'(?m)^(\t+)ret = pd->pd_control\(pd->cal_pdid, 0\);$'
 assert len(re.findall(pattern,body))==2
 body=re.sub(pattern,lambda m:m.group()+b'\n'+note(4,'ret'),body)
 anchor=b'\tpd->power_down_skipped = false;';assert body.count(anchor)==1;body=body.replace(anchor,anchor+b'\n'+note(5))
 anchor=b'\tmutex_unlock(&pd->access_lock);';assert body.count(anchor)==1;body=body.replace(anchor,note(7)+anchor)
 raw=raw[:start]+body+raw[end:];anchor=b'\t\tof_genpd_add_provider_simple(np, &pd->genpd);';assert raw.count(anchor)==1;raw=raw.replace(anchor,note(1)+anchor)
 return PREFIX+raw+SUFFIX

def prepare(source):
 source=Path(source)
 for n,h in PINS.items():
  if hashlib.sha256((source/n).read_bytes()).hexdigest()!=h:raise ValueError('FSYS source pin differs: '+n)
 p=source/'drivers/soc/samsung/exynos-pd.c';original=p.read_bytes();p.with_name('exynos-pd-original.c').write_bytes(original);p.write_bytes(instrument(original));p.with_name('note10_fsys_pm.c').write_bytes((HERE/'fsys_pm_backend.c').read_bytes())
 return dict(fsys_pd_source_pins=PINS,fsys_pd_patched_sha256=hashlib.sha256(p.read_bytes()).hexdigest())
