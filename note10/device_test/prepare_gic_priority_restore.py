"""Compose target-scoped GIC priority restoration over exact v39 source."""
import hashlib,shutil
from pathlib import Path
from prepare_pm_callbacks import HERE,replace

def sha(raw):return hashlib.sha256(raw).hexdigest()
def prepare(source,previous):
 source=Path(source);names=('drivers/irqchip/irq-gic.c','kernel/power/Kconfig')
 before={'drivers/irqchip/irq-gic.c':previous['pm_preconditions_prepared_sha256']['drivers/irqchip/irq-gic.c'],'kernel/power/Kconfig':previous['pmu_failure_prepared_sha256']['kernel/power/Kconfig']}
 for n in names:
  if sha((source/n).read_bytes())!=before[n]:raise ValueError('v39 GIC input differs: '+n)
 helper=source/'drivers/irqchip/note10_gic_priority_restore.c'
 if helper.exists():raise ValueError('GIC helper already exists')
 helper.write_bytes((HERE/'gic_priority_restore.c').read_bytes())
 path=source/names[0];raw=path.read_bytes()
 anchor=b'struct gic_chip_data {'
 definition=b'#ifdef CONFIG_NOTE10_GIC_PRIORITY_RESTORE\nstruct n10_gic_priority { u32 words[8]; bool valid, pending; };\n#endif\n\n'
 raw=replace(raw,anchor,definition+anchor+b'\n#ifdef CONFIG_NOTE10_GIC_PRIORITY_RESTORE\n\tstruct n10_gic_priority __percpu *n10_priority;\n#endif')
 anchor=b'void gic_cpu_save(struct gic_chip_data *gic)'
 raw=replace(raw,anchor,b'#ifdef CONFIG_NOTE10_GIC_PRIORITY_RESTORE\n#include "note10_gic_priority_restore.c"\n#endif\n\n'+anchor)
 start=raw.index(b'void gic_cpu_save(');end=raw.index(b'void gic_cpu_restore(',start);save=raw[start:end]
 anchor=b'\tvoid __iomem *cpu_base;';save=replace(save,anchor,anchor+b'\n#ifdef CONFIG_NOTE10_GIC_PRIORITY_RESTORE\n\tbool n10_capture;\n#endif')
 anchor=b'\tif (WARN_ON(!gic))\n\t\treturn;';save=replace(save,anchor,anchor+b'\n#ifdef CONFIG_NOTE10_GIC_PRIORITY_RESTORE\n\tn10_capture = n10_gic_priority_begin(gic);\n#endif')
 anchor=b'\tif (!dist_base || !cpu_base)\n\t\treturn;';save=replace(save,anchor,b'\tif (!dist_base || !cpu_base) {\n#ifdef CONFIG_NOTE10_GIC_PRIORITY_RESTORE\n\t\tn10_gic_priority_clear(gic);\n#endif\n\t\treturn;\n\t}')
 anchor=b'\t\tptr[i] = readl_relaxed(dist_base + GIC_DIST_CONFIG + i * 4);';save=replace(save,anchor,anchor+b'\n#ifdef CONFIG_NOTE10_GIC_PRIORITY_RESTORE\n\tif (n10_capture) n10_gic_priority_save(gic, dist_base);\n#endif')
 raw=raw[:start]+save+raw[end:];start=raw.index(b'void gic_cpu_restore(');end=raw.index(b'static int gic_notifier(',start);restore=raw[start:end]
 anchor=b'\tvoid __iomem *cpu_base;';restore=replace(restore,anchor,anchor+b'\n#ifdef CONFIG_NOTE10_GIC_PRIORITY_RESTORE\n\tstruct n10_gic_priority *n10_saved;\n#endif')
 anchor=b'\tif (!dist_base || !cpu_base)\n\t\treturn;';restore=replace(restore,anchor,b'\tif (!dist_base || !cpu_base) {\n#ifdef CONFIG_NOTE10_GIC_PRIORITY_RESTORE\n\t\tn10_gic_priority_clear(gic);\n#endif\n\t\treturn;\n\t}\n#ifdef CONFIG_NOTE10_GIC_PRIORITY_RESTORE\n\tn10_saved = n10_gic_priority_take(gic);\n#endif')
 anchor=b'\tfor (i = 0; i < DIV_ROUND_UP(32, 4); i++)\n\t\twritel_relaxed(GICD_INT_DEF_PRI_X4,\n\t\t\t\t\tdist_base + GIC_DIST_PRI + i * 4);'
 value=b'\tfor (i = 0; i < DIV_ROUND_UP(32, 4); i++)\n#ifdef CONFIG_NOTE10_GIC_PRIORITY_RESTORE\n\t\twritel_relaxed(n10_saved ? n10_saved->words[i] : GICD_INT_DEF_PRI_X4,\n\t\t\t\t\tdist_base + GIC_DIST_PRI + i * 4);\n#else\n\t\twritel_relaxed(GICD_INT_DEF_PRI_X4,\n\t\t\t\t\tdist_base + GIC_DIST_PRI + i * 4);\n#endif';restore=replace(restore,anchor,value);raw=raw[:start]+restore+raw[end:]
 anchor=b'\tif (gic == &gic_data[0])\n\t\tcpu_pm_register_notifier(&gic_notifier_block);'
 init=b'#ifdef CONFIG_NOTE10_GIC_PRIORITY_RESTORE\n\t{\n\t\tint cpu;\n\t\tgic->n10_priority = alloc_percpu(struct n10_gic_priority);\n\t\tif (WARN_ON(!gic->n10_priority)) goto free_ppi_conf;\n\t\tfor_each_possible_cpu(cpu) {\n\t\t\tstruct n10_gic_priority *p = per_cpu_ptr(gic->n10_priority, cpu);\n\t\t\tmemset(p, 0, sizeof(*p));\n\t\t}\n\t}\n#endif\n'
 raw=replace(raw,anchor,init+anchor);anchor=b'free_ppi_active:\n\tfree_percpu(gic->saved_ppi_active);';raw=replace(raw,anchor,b'#ifdef CONFIG_NOTE10_GIC_PRIORITY_RESTORE\nfree_ppi_conf:\n\tfree_percpu(gic->saved_ppi_conf);\n#endif\n'+anchor);path.write_bytes(raw)
 config=source/names[1];config.write_bytes(config.read_bytes()+b'\nconfig NOTE10_GIC_PRIORITY_RESTORE\n\tbool "Experimental banked GIC priority restoration"\n\tdepends on NOTE10_PMU_FAILURE_RESTORE && NOTE10_CPU_PM_FAILURE_GUARD && CPU_PM && ARM_GIC\n\tdepends on ARM_GIC_MAX_NR = 1 && !GIC_NON_BANKED\n\tdefault n\n')
 return {'gic_priority_restore':True,'gic_priority_restore_version':1,'gic_priority_intermediate_sha256':before,'gic_priority_prepared_sha256':{n:sha((source/n).read_bytes()) for n in (*names,'drivers/irqchip/note10_gic_priority_restore.c')}}

def snapshot(source,out,report):
 source=Path(source);out=Path(out)
 if out.exists():raise ValueError('GIC snapshot exists')
 names=set(report['pmu_failure_snapshot_sha256'])|set(report['gic_priority_prepared_sha256'])
 for n in names:
  src=source/n
  if src.is_symlink() or not src.is_file():raise ValueError('GIC source snapshot invalid: '+n)
  dst=out/n;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dst)
 return {n:sha((out/n).read_bytes()) for n in sorted(names)}
