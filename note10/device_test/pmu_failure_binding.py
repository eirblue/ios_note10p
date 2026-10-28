"""Bind the final scoped PMU failure guard to source, models and Image."""
import hashlib, json, shutil, tempfile, re
from pathlib import Path
from prepare_pmu_failure_restore import prepare
HERE = Path(__file__).resolve().parent
SOURCES = ("prepare_pmu_failure_restore.py", "pmu_failure_restore.c", "test_pmu_failure_restore.py", "pmu_failure_binding.py", "test_pmu_failure_binding.py", "test_pmu_failure_package_flow.py")
PACKAGE_SOURCES = ("prepare_linux_boot.py", "build_boot_test_packages.py", "precheck_window_access.py", "stage_phase2.py", "collect_reservation.py")
MARKER = b"N10PMUFR1: missing PMU failed-entry snapshot"
def sha(raw): return hashlib.sha256(raw).hexdigest()
def validate_core(root, build):
    root = Path(root)
    config = (root / "handoff.config").read_bytes().splitlines()
    enabled = b"CONFIG_NOTE10_PMU_FAILURE_RESTORE=y" in config
    if enabled != (build.get("pmu_failure_restore") is True) or enabled != (MARKER in (root / "Image").read_bytes()):
        raise ValueError("PMU failure guard Image/config/metadata mismatch")
    if not enabled:
        if any(k.startswith("pmu_failure_") for k in build) or (root/"pmu-failure-prepared").exists() or (root/"pmu-failure-model").exists():
            raise ValueError("failure guard evidence downgrade")
        return False
    if build.get("pmu_failure_restore_version") != 1 or not all(x in config for x in (b"CONFIG_CPU_PM=y",b"CONFIG_ARM_PMU=y",b"CONFIG_NOTE10_CPU_PM_BRANCH_AUDIT=y",b"CONFIG_NOTE10_CPU_PM_FAILURE_GUARD=y")):
        raise ValueError("PMU failure guard prerequisites differ")
    sourcehash = {n:sha((HERE/n).read_bytes()) for n in SOURCES}
    if build.get("pmu_failure_sources_sha256") != sourcehash: raise ValueError("failure sources differ")
    package_sources=build.get("pmu_failure_package_sources_sha256")
    if not isinstance(package_sources,dict) or set(package_sources)!=set(PACKAGE_SOURCES) or any(not isinstance(v,str) or re.fullmatch(r"[0-9a-f]{64}",v) is None for v in package_sources.values()): raise ValueError("failure package source map differs")
    with tempfile.TemporaryDirectory() as tmp:
        expected=Path(tmp)/"source"; shutil.copytree(root/"pm-preconditions-prepared",expected)
        branch=root/"pm-branch-prepared"
        for name in build["pm_branch_prepared_sha256"]:
            src=branch/name; dst=expected/name; dst.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(src,dst)
        notifier=expected/"kernel/notifier.c"
        notifier.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(root/"pmu-failure-prepared/kernel/notifier.c",notifier)
        result=prepare(expected,build)
        if any(build.get(k)!=v for k,v in result.items()): raise ValueError("failure composition differs")
        snapshot=root/"pmu-failure-prepared"
        paths=list(snapshot.rglob("*"))
        if snapshot.is_symlink() or any(p.is_symlink() for p in paths): raise ValueError("failure snapshot symlink")
        files={p.relative_to(snapshot).as_posix() for p in paths if p.is_file()}
        expected_names=set(build["pm_branch_prepared_sha256"]) | set(result["pmu_failure_prepared_sha256"])
        if files!=expected_names: raise ValueError("failure snapshot set differs")
        hashes={n:sha((snapshot/n).read_bytes()) for n in sorted(files)}
        if build.get("pmu_failure_snapshot_sha256")!=hashes: raise ValueError("failure snapshot hashes differ")
        for n in files:
            if (snapshot/n).read_bytes() != (expected/n).read_bytes(): raise ValueError("failure snapshot composition differs: "+n)
    model=root/"pmu-failure-model"; m=json.loads((model/"result.json").read_text(encoding="utf8"))
    from test_pmu_failure_restore import CASES
    if m.get("passed") is not True or m.get("hardware_verified") is not False or m.get("cases")!={"off":[CASES[i] for i in (0,1,2,3,4,11,12,14)],"on":list(CASES)}: raise ValueError("failure model cases differ")
    if m.get("source_sha256")!=build["pmu_failure_prepared_sha256"]["drivers/perf/arm_pmu.c"] or m.get("cpu_source_sha256")!=hashes["kernel/cpu_pm.c"] or m.get("notifier_source_sha256")!=hashes["kernel/notifier.c"] or m.get("helper_sha256")!=sourcehash["pmu_failure_restore.c"] or m.get("harness_sha256")!=sourcehash["test_pmu_failure_restore.py"]: raise ValueError("failure model source differs")
    from test_pmu_failure_restore import generate
    expected_c=generate((snapshot/"drivers/perf/arm_pmu.c").read_text(encoding="utf8"),(HERE/"pmu_failure_restore.c").read_text(encoding="utf8"),(snapshot/"kernel/cpu_pm.c").read_text(encoding="utf8"),(snapshot/"kernel/notifier.c").read_text(encoding="utf8")).encode("utf8")
    if any((model/n).read_bytes().replace(b"\r\n",b"\n") != expected_c.replace(b"\r\n",b"\n") for n in ("off.c","on.c")): raise ValueError("failure generated source differs")
    generated={n:sha((model/n).read_bytes()) for n in ("off.c","on.c")}
    logs={n:sha((model/n).read_bytes()) for n in ["off-compile.log","on-compile.log"]+[f"off-{i}.log" for i in [0,1,2,3,4,11,12,14]]+[f"on-{i}.log" for i in range(15)]}
    if m.get("generated_sha256")!=generated or m.get("log_sha256")!=logs: raise ValueError("failure evidence differs")
    return True


def validate(root,build,require_package_flow=True):
    if not validate_core(root,build): return False
    from test_pmu_failure_binding import CASES
    proof=json.loads((Path(root)/"pmu-failure-binding-model/result.json").read_text(encoding="utf8"))
    if proof.get("passed") is not True or proof.get("cases")!=list(CASES) or proof.get("harness_sha256")!=build["pmu_failure_sources_sha256"]["test_pmu_failure_binding.py"]:
        raise ValueError("failure binding mutation proof differs")
    if require_package_flow:
        flow=json.loads((Path(root)/"pmu-failure-package-flow-model/result.json").read_text(encoding="utf8"))
        cases=["synthetic-prototype-to-packages","missing-flag","missing-version","missing-binding-proof"]
        if flow.get("passed") is not True or flow.get("hardware_verified") is not False or flow.get("cases")!=cases or flow.get("harness_sha256")!=build["pmu_failure_sources_sha256"]["test_pmu_failure_package_flow.py"] or flow.get("package_sources_sha256")!=build["pmu_failure_package_sources_sha256"]:
            raise ValueError("failure package flow proof differs")
    return True
