"""Compose the scoped failure rollback over the pinned v38 prepared tree."""
import hashlib
from pathlib import Path
from prepare_pm_callbacks import HERE, replace

def sha(data):
    return hashlib.sha256(data).hexdigest()

def prepare(source, previous):
    source = Path(source)
    names = ("drivers/perf/arm_pmu.c", "include/linux/perf/arm_pmu.h", "kernel/power/Kconfig")
    before = dict(previous["pm_preconditions_prepared_sha256"])
    before.update(previous["pm_branch_prepared_sha256"])
    for name in names:
        if sha((source / name).read_bytes()) != before[name]:
            raise ValueError("v38 source differs: " + name)
    notifier = source / "kernel/notifier.c"
    if sha(notifier.read_bytes()) != previous["pm_callbacks_source_pins"]["kernel/notifier.c"]:
        raise ValueError("pinned notifier differs")
    path = source / "drivers/perf/note10_pmu_failure_restore.c"
    if path.exists():
        raise ValueError("failure helper already exists")
    path.write_bytes((HERE / "pmu_failure_restore.c").read_bytes())
    header = source / names[1]
    data = header.read_bytes()
    anchor = b"struct pmu_hw_events {"
    addition = b"\n#ifdef CONFIG_NOTE10_PMU_FAILURE_RESTORE\n\tbool n10_failure_valid, n10_failure_pending;\n\tstruct perf_event *n10_failure_events[ARMPMU_MAX_HWEVENTS];\n#endif\n"
    header.write_bytes(replace(data, anchor, anchor + addition))
    c = source / names[0]
    data = c.read_bytes()
    anchor = b"static int cpu_pm_pmu_notify(struct notifier_block *b, unsigned long cmd,"
    data = replace(data, anchor, b"#ifdef CONFIG_NOTE10_PMU_FAILURE_RESTORE\n#include \"note10_pmu_failure_restore.c\"\n#endif\n" + anchor)
    anchor = b"\tif (!cpumask_test_cpu(smp_processor_id(), &armpmu->supported_cpus))\n\t\treturn NOTIFY_DONE;"
    data = replace(data, anchor, b"\tif (!cpumask_test_cpu(smp_processor_id(), &armpmu->supported_cpus)) {\n#ifdef CONFIG_NOTE10_PMU_FAILURE_RESTORE\n\t\tn10_pmu_failure_clear(hw_events);\n#endif\n\t\treturn NOTIFY_DONE;\n\t}")
    anchor = b"\tif (!enabled)\n\t\treturn NOTIFY_OK;"
    data = replace(data, anchor, b"#ifdef CONFIG_NOTE10_PMU_FAILURE_RESTORE\n\tif (cmd == CPU_PM_EXIT) n10_pmu_failure_clear(hw_events);\n\tif (cmd == CPU_PM_ENTER) n10_pmu_failure_capture(armpmu, hw_events);\n\tif (cmd == CPU_PM_ENTER_FAILED) n10_pmu_failure_recover(armpmu, hw_events);\n#endif\n" + anchor)
    anchor = b"\t\traw_spin_lock_init(&events->pmu_lock);"
    data = replace(data, anchor, b"#ifdef CONFIG_NOTE10_PMU_FAILURE_RESTORE\n\t\tn10_pmu_failure_clear(events);\n#endif\n" + anchor)
    anchor = b"void armpmu_free(struct arm_pmu *pmu)\n{\n\tfree_percpu(pmu->hw_events);"
    data = replace(data, anchor, b"void armpmu_free(struct arm_pmu *pmu)\n{\n#ifdef CONFIG_NOTE10_PMU_FAILURE_RESTORE\n\tint cpu;\n\tfor_each_possible_cpu(cpu) n10_pmu_failure_clear(per_cpu_ptr(pmu->hw_events, cpu));\n#endif\n\tfree_percpu(pmu->hw_events);")
    c.write_bytes(data)
    config = source / names[2]
    config.write_bytes(config.read_bytes() + b'\nconfig NOTE10_PMU_FAILURE_RESTORE\n\tbool "Experimental PMU failed-entry restoration"\n\tdepends on NOTE10_CPU_PM_BRANCH_AUDIT && NOTE10_CPU_PM_FAILURE_GUARD && CPU_PM && ARM_PMU\n\tdefault n\n')
    return {"pmu_failure_restore": True, "pmu_failure_restore_version": 1,
            "pmu_failure_intermediate_sha256": {n: before[n] for n in names},
            "pmu_failure_prepared_sha256": {n: sha((source/n).read_bytes()) for n in (*names, "drivers/perf/note10_pmu_failure_restore.c", "kernel/notifier.c")}}


def snapshot(source, out, report):
    import shutil
    source, out = Path(source), Path(out)
    if out.exists():
        raise ValueError("failure snapshot exists")
    names = set(report["pm_branch_prepared_sha256"]) | set(report["pmu_failure_prepared_sha256"])
    for name in names:
        src = source / name
        if src.is_symlink() or not src.is_file():
            raise ValueError("invalid failure snapshot source: " + name)
        dst = out / name
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
    return {name: sha((out / name).read_bytes()) for name in sorted(names)}
