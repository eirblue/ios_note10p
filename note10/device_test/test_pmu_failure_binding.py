"""Exercise omission and source/evidence mutations against the failure binding."""
import argparse, hashlib, json, shutil, tempfile
from pathlib import Path
from pmu_failure_binding import validate_core
CASES=("source-map-omitted","snapshot-map-omitted","version-omitted","prior-source-changed","final-source-changed","generated-source-changed","case-omitted","config-disabled","image-marker-missing","evidence-downgrade","coherent-generated-change")
def main():
    ap=argparse.ArgumentParser();ap.add_argument("--artifact",required=True);ap.add_argument("--output",required=True);args=ap.parse_args()
    artifact=Path(args.artifact); out=Path(args.output);out.mkdir(parents=True,exist_ok=False)
    base=json.loads((artifact/"build-result.json").read_text(encoding="utf8"))
    with tempfile.TemporaryDirectory() as tmp:
        root=Path(tmp)
        for name in ("pm-preconditions-prepared","pm-branch-prepared","pmu-failure-prepared","pmu-failure-model"): shutil.copytree(artifact/name,root/name)
        for name in ("Image","handoff.config"): shutil.copyfile(artifact/name,root/name)
        validate_core(root,base)
        for case in CASES:
            b=dict(base); path=None; original=None; extra=[]
            if case.endswith("-omitted") and case!="case-omitted":
                b.pop({"source-map-omitted":"pmu_failure_sources_sha256","snapshot-map-omitted":"pmu_failure_snapshot_sha256","version-omitted":"pmu_failure_restore_version"}[case])
            elif case=="coherent-generated-change":
                path=root/"pmu-failure-model/on.c";original=path.read_bytes();path.write_bytes(original+b"\nmutation\n")
                q=root/"pmu-failure-model/result.json";raw=q.read_bytes();extra.append((q,raw));m=json.loads(raw);m["generated_sha256"]["on.c"]=hashlib.sha256(path.read_bytes()).hexdigest();q.write_text(json.dumps(m),encoding="utf8")
            elif case=="evidence-downgrade":
                b={k:v for k,v in b.items() if not k.startswith("pmu_failure_")}
                for n,old,new in (("handoff.config",b"CONFIG_NOTE10_PMU_FAILURE_RESTORE=y",b"# CONFIG_NOTE10_PMU_FAILURE_RESTORE is not set"),("Image",b"N10PMUFR1: missing PMU failed-entry snapshot",b"N10PMUFRx: missing PMU failed-entry snapshot")):
                    q=root/n;raw=q.read_bytes();extra.append((q,raw));q.write_bytes(raw.replace(old,new))
            else:
                path=root/{"prior-source-changed":"pm-branch-prepared/drivers/perf/arm_pmu.c","final-source-changed":"pmu-failure-prepared/drivers/perf/arm_pmu.c","generated-source-changed":"pmu-failure-model/on.c","case-omitted":"pmu-failure-model/result.json","config-disabled":"handoff.config","image-marker-missing":"Image"}[case];original=path.read_bytes()
                if case=="case-omitted":
                    m=json.loads(original);m["cases"]["on"].pop();path.write_text(json.dumps(m),encoding="utf8")
                elif case=="config-disabled":path.write_bytes(original.replace(b"CONFIG_NOTE10_PMU_FAILURE_RESTORE=y",b"# CONFIG_NOTE10_PMU_FAILURE_RESTORE is not set"))
                elif case=="image-marker-missing":path.write_bytes(original.replace(b"N10PMUFR1: missing PMU failed-entry snapshot",b"N10PMUFRx: missing PMU failed-entry snapshot"))
                else:path.write_bytes(original+b"\nmutation\n")
            try: validate_core(root,b)
            except (ValueError,KeyError,FileNotFoundError): pass
            else: raise RuntimeError("accepted mutation: "+case)
            finally:
                if path is not None:path.write_bytes(original)
                for q,raw in extra:q.write_bytes(raw)
    result={"passed":True,"cases":list(CASES),"harness_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    (out/"result.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf8")
if __name__=="__main__":main()
