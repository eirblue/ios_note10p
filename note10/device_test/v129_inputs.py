"""Immutable accepted128 SOURCE inputs; not a PASS reader or an old test runner."""
import hashlib
import importlib.util
import subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
INPUT_COMMIT="182fc8c40160f3f19299cb72c2b41bbbd9a4d6e5"
INPUT_SCHEMA="v128-exact-source-freeze-v1"
INPUT_PINS={'note10/device_test/legacy_kexec_core.h': 'ca7043792efc7cdfe1912e15161e9e6384042ff6bce219a43f16e8409bcc080a', 'note10/device_test/legacy_kexec_core.c': '177bd7225ee4d00a6fe52eb1e08907c51b3745e844901b3144743f5b5a841df3', 'note10/device_test/legacy_kexec_fixture.c': 'd34e35db875d4b1037c8ab5d7fc99221097319bb5d23ba70130766b344d45433', 'note10/device_test/legacy_kexec_loader.c': '44f362d458e85d3bbcfc102b40ac98c7a75ab3ab49f593b6fe0c9dfdb7dbfa79', 'note10/device_test/legacy_kexec_syscall.S': '954c5eb1a00f954749b6a9b4d13d5ed3b632d5445d640658c8abb5e590c6e4ce', 'note10/device_test/kexec_recovery_park.S': 'b1f3307bab2e5eed9fb27e2ff583bbee02b5d9f62bb3198a7db267ded237d019', 'note10/device_test/legacy_kexec_return.h': '144e77e70bd6065466819b643298014849137c2f0f129f7a085f93e0f4d7fbef', 'note10/device_test/legacy_kexec_reservation.c': '327c0311e12523ef1a29b27860455fa44d1d276b251a7b4a6176370e55ebf942', 'note10/device_test/legacy_kexec_marker.c': 'db3c595e22d51a98eef51e78884c2ab7074ebbc8d90e38bb91332224df9330d9', 'note10/device_test/legacy_kexec_watchdog.c': 'fce2cfda469f5377125e5ef3fb86965603390d9254c93eb8ad241b4fe29d24a6', 'note10/device_test/prepare_legacy_kexec_recovery.py': '9fd08b600369f6161d8a29fedbb6a27ea37b76ccd36f56394b766954ebae45e2', 'note10/device_test/test_legacy_kexec_backend.py': '83a42bc06865a05ac753cfc21ff3717af85dd6faa378abe53dde51763e47c6af', 'note10/device_test/build_legacy_kexec_host.py': 'c55a86a08c98deb2a07896d1135247299f8967c43a19fc014638fa268075009d', '.github/workflows/note10-legacy-kexec-recovery-proof.yml': 'a88e02983e5020af238a32de69744f2d8d268d7050be5866fb87e0514922b8af', 'note10/device_test/build_xnu_runtime_plan_component.py': '367f9147d50950dffb47bf83861787dce4a1be47225b11b070e2f60de45c6b6e', 'note10/device_test/sealed_affinity_artifact.cjs': '08c17edb82357d5719fbccd2427fca1970c09f6b3ee7aef91d6034f7d12f70ec'}

def digest(raw):return hashlib.sha256(raw).hexdigest()

def materialize(destination):
    destination=Path(destination).resolve()
    if destination.exists() or not destination.is_relative_to(ROOT/'note10/private'):
        raise ValueError('fresh private immutable-source input directory required')
    frozen=ROOT/'note10/private/device-test/v128-legacy-kexec-recovery-proof-20261105/frozen-source'
    rows={}
    for name,pin in INPUT_PINS.items():
        raw=(frozen/name).read_bytes() if (frozen/name).is_file() else subprocess.run(
            ['git','show',INPUT_COMMIT+':'+name],cwd=ROOT,check=True,capture_output=True,timeout=30).stdout
        if digest(raw)!=pin:raise ValueError('accepted128 SOURCE bytes differ: '+name)
        rows[name]=raw
    for name,raw in rows.items():
        path=destination/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
    return destination

def module(folder,name):
    path=Path(folder)/'note10/device_test'/name
    spec=importlib.util.spec_from_file_location('v129_frozen_'+path.stem,path)
    loaded=importlib.util.module_from_spec(spec);spec.loader.exec_module(loaded)
    return loaded
