"""Read/copy immutable source domains only; never execute relocated modules."""
import hashlib
from pathlib import Path
import subprocess
from v130_contract import ROOT
INPUT128_COMMIT='182fc8c40160f3f19299cb72c2b41bbbd9a4d6e5'
INPUT128={'note10/device_test/legacy_kexec_core.h': 'ca7043792efc7cdfe1912e15161e9e6384042ff6bce219a43f16e8409bcc080a', 'note10/device_test/legacy_kexec_core.c': '177bd7225ee4d00a6fe52eb1e08907c51b3745e844901b3144743f5b5a841df3', 'note10/device_test/legacy_kexec_fixture.c': 'd34e35db875d4b1037c8ab5d7fc99221097319bb5d23ba70130766b344d45433', 'note10/device_test/legacy_kexec_loader.c': '44f362d458e85d3bbcfc102b40ac98c7a75ab3ab49f593b6fe0c9dfdb7dbfa79', 'note10/device_test/legacy_kexec_syscall.S': '954c5eb1a00f954749b6a9b4d13d5ed3b632d5445d640658c8abb5e590c6e4ce', 'note10/device_test/kexec_recovery_park.S': 'b1f3307bab2e5eed9fb27e2ff583bbee02b5d9f62bb3198a7db267ded237d019', 'note10/device_test/legacy_kexec_return.h': '144e77e70bd6065466819b643298014849137c2f0f129f7a085f93e0f4d7fbef', 'note10/device_test/legacy_kexec_reservation.c': '327c0311e12523ef1a29b27860455fa44d1d276b251a7b4a6176370e55ebf942', 'note10/device_test/legacy_kexec_marker.c': 'db3c595e22d51a98eef51e78884c2ab7074ebbc8d90e38bb91332224df9330d9', 'note10/device_test/legacy_kexec_watchdog.c': 'fce2cfda469f5377125e5ef3fb86965603390d9254c93eb8ad241b4fe29d24a6', 'note10/device_test/prepare_legacy_kexec_recovery.py': '9fd08b600369f6161d8a29fedbb6a27ea37b76ccd36f56394b766954ebae45e2', 'note10/device_test/test_legacy_kexec_backend.py': '83a42bc06865a05ac753cfc21ff3717af85dd6faa378abe53dde51763e47c6af', 'note10/device_test/build_legacy_kexec_host.py': 'c55a86a08c98deb2a07896d1135247299f8967c43a19fc014638fa268075009d', '.github/workflows/note10-legacy-kexec-recovery-proof.yml': 'a88e02983e5020af238a32de69744f2d8d268d7050be5866fb87e0514922b8af', 'note10/device_test/build_xnu_runtime_plan_component.py': '367f9147d50950dffb47bf83861787dce4a1be47225b11b070e2f60de45c6b6e', 'note10/device_test/sealed_affinity_artifact.cjs': '08c17edb82357d5719fbccd2427fca1970c09f6b3ee7aef91d6034f7d12f70ec'}
INPUT129_COMMIT='155ea9dcccc019fb8f785673c589eb9f01ace1ec'
INPUT129={'note10/device_test/v129_inputs.py': '9b5e1b1c700269117e70fc621f79de4324180969f0d5da8caaa5cabe0351db27', 'note10/device_test/v129_prepare.py': 'fe2bf8dad47120bdd30c5c61507dbbea00f726d2cab40f8c00082ddbb1a6aed6', 'note10/device_test/v129_loader.c': '4e281c71643017bc553a5f352b4bc1fd090532bde2d14dc96e8167f37144d65a', 'note10/device_test/v129_build.py': '34e86b3dc7d10fe87fad87a57fb0c6650990442ad49317f5e988f9b823348c6a', 'note10/device_test/v129_package.py': '88c071ac42257866f8afc4fc39e12e03f568222f509d65f555abd6f5b03620c2', 'note10/device_test/v129_cycle.py': '6e4664948578df48d6a1da6d02906fe0acc0c16957fc7f4c4f81caf95d80a872', 'note10/device_test/v129_fixture.c': 'dd8b26af68e52b22c695df634b165dc221d8f52c024c3908a20207e7dde91faa', 'note10/device_test/test_v129_proof.py': '0df2110731e38dcb65881bc464e051b57babfb939bfc26992737ff0f1ed88df5', '.github/workflows/note10-v129-kexec-proof.yml': '4d4bc215e2b477f4e53c02c6482b1f66c0345d4705031e6f3f9d79b021abd50a'}

def materialize(destination):
    destination=Path(destination).resolve()
    if destination.exists() or not destination.is_relative_to(ROOT/'note10/private'):raise ValueError('fresh private source-only input directory required')
    repository=ROOT/'note10/private/publish'
    if not repository.is_dir():repository=ROOT
    domains={}
    for label,commit,pins,retained in (
        ('source128',INPUT128_COMMIT,INPUT128,ROOT/'note10/private/device-test/v128-legacy-kexec-recovery-proof-20261105/frozen-source'),
        ('source129',INPUT129_COMMIT,INPUT129,ROOT/'note10/private/device-test/v129-kexec-proof-package-recovery-20261105/frozen-source')):
        rows={}
        for name,pin in pins.items():
            path=retained/name
            raw=path.read_bytes() if path.is_file() else subprocess.run(
                ['git','-c','safe.directory='+repository.as_posix(),'-C',str(repository),'show',commit+':'+name],
                cwd=ROOT,check=True,capture_output=True,timeout=30).stdout
            if hashlib.sha256(raw).hexdigest()!=pin:raise ValueError('immutable source bytes differ: '+label+'/'+name)
            rows[name]=raw
        folder=destination/label
        for name,raw in rows.items():
            path=folder/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
        domains[label]=folder
    return domains
