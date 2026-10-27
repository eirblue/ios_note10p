"""Add bounded PMU reads after the proven ABOX guard and PM-list unlock."""
import hashlib
from pathlib import Path
from prepare_abox_pm import CORE_PATCHED_SHA
HERE=Path(__file__).resolve().parent
PINS={
    'drivers/soc/samsung/cal-if/exynos9820/flexpmu_cal_local_exynos9820.h':'f1f2c4f162cb7a5192602777dd3bd6554408a938fc8f62632c441a3112228ddf',
    'drivers/soc/samsung/cal-if/exynos9820/cal_data.c':'7f61d64bdd22493afc078006540e81dc1dd39df21b22dd96cf13c88960a649a0',
    'drivers/soc/samsung/exynos-pmu.c':'c6db842f3ad376f4493ac47cf9c6504f8e34e757f1b0729fca9762bc538105f9',
    'include/soc/samsung/exynos-pmu.h':'6cdfb37e49031b5e55af18b7e6e02d78eaa85b97dde61a8ff42d51ee85cfa948',
    'arch/arm64/boot/dts/exynos/exynos9820.dts':'441397886a32c82aa42c3731272ed7153b81d07b601521153061545c490d4a8b',
}
SOURCES=('pmu_domain_table.py','abox_pmu_contract.h','abox_pmu_backend.c','abox_pmu_probe.c','prepare_abox_pmu.py','decode_abox_pmu.py','abox_pmu_binding.py')
SUFFIX=b'\n#ifdef CONFIG_NOTE10_ABOX_PMU_AUDIT\n#include "note10_abox_pmu.c"\n#endif\n'
FINAL_CORE_SHA='500bd5baea17a1809172b83abf6116b658a74e30d0c7d9ba41f363a5c3ab5b4e'

def instrument_core(raw):
    if hashlib.sha256(raw).hexdigest()!=CORE_PATCHED_SHA:raise ValueError('Prepared ABOX guard source differs')
    return raw+SUFFIX

def prepare(source):
    source=Path(source)
    for name,digest in PINS.items():
        if hashlib.sha256((source/name).read_bytes()).hexdigest()!=digest:raise ValueError('Pinned PMU API/DT input differs: '+name)
    validate_domains((source/'drivers/soc/samsung/cal-if/exynos9820/flexpmu_cal_local_exynos9820.h').read_text())
    core=source/'sound/soc/samsung/abox/abox_core.c';raw=instrument_core(core.read_bytes())
    if hashlib.sha256(raw).hexdigest()!=FINAL_CORE_SHA:raise ValueError('Final ABOX core composition differs')
    core.write_bytes(raw);core.with_name('note10_abox_pmu.c').write_bytes((HERE/'abox_pmu_backend.c').read_bytes())
    (source/'include/linux/note10_abox_pmu.h').write_bytes((HERE/'abox_pmu_contract.h').read_bytes())
    worker=source/'arch/arm64/mm/note10_pm_timer_roundtrip.c';raw=worker.read_bytes();anchor=b'    status = 0;\nreport:'
    if raw.count(anchor)!=1:raise ValueError('PMU report insertion differs')
    worker.with_name('note10_abox_pmu_probe.c').write_bytes((HERE/'abox_pmu_probe.c').read_bytes())
    worker.write_bytes(b'#ifdef CONFIG_NOTE10_ABOX_PMU_AUDIT\n#include "note10_abox_pmu_probe.c"\n#endif\n'+raw.replace(anchor,b'#ifdef CONFIG_NOTE10_ABOX_PMU_AUDIT\n    n10_report_abox_pmu(pm.qgeneration);\n#endif\n'+anchor))
    config=source/'kernel/power/Kconfig';config.write_bytes(config.read_bytes()+b'\nconfig NOTE10_ABOX_PMU_AUDIT\n\tbool "Experimental bounded read-only ABOX PMU control observations"\n\tdepends on NOTE10_ABOX_FW_FAILURE_GUARD && EXYNOS_PMU=y\n\tdefault n\n')
    return dict(abox_pmu_audit_diagnostic=True,abox_pmu_audit_evidence_version=2,abox_pmu_source_pins=PINS,
        abox_pmu_sources_sha256={n:hashlib.sha256((HERE/n).read_bytes()).hexdigest() for n in SOURCES},
        abox_pmu_final_core_sha256=FINAL_CORE_SHA,abox_pmu_base_core_sha256=CORE_PATCHED_SHA)


def validate_domains(raw):
    import re
    from pmu_domain_table import DOMAINS
    actual=[]
    for name,status in re.findall(r'PMUCAL_SEQ_DESC\(PMUCAL_READ, "(\w+)_STATUS", 0x15860000, (0x[0-9a-f]+), \(0x1 << 0\)',raw):
        match=re.search(r'PMUCAL_SEQ_DESC\(PMUCAL_WRITE, "'+name+r'_CONFIGURATION", 0x15860000, (0x[0-9a-f]+), \(0x1 << 0\)',raw)
        if not match:raise ValueError('Missing CAL configuration field')
        actual.append((name,int(match[1],16),int(status,16)))
    if tuple(actual)!=DOMAINS or len(actual)!=16:raise ValueError('Pinned CAL status/configuration table differs')
    backend=(HERE/'abox_pmu_backend.c').read_text()
    table=re.findall(r'    \{(0x[0-9a-f]+), (0x[0-9a-f]+)\}, /\* (\w+) \*/',backend)
    if tuple((n,int(c,16),int(s,16)) for c,s,n in table)!=DOMAINS:raise ValueError('Actual C domain allowlist differs')
