"""Generate the SoC MASTER and explicit platform-link-input patch after patch 0001."""
import difflib
import hashlib
import json
import re
import subprocess
from prepare_build_selection import ROOT, PIN, replace_one

MASTER = 'config/MASTER.arm64.iPhoneOS'
MASTER_PIN = 'b0b4913c03970ca793cd0d3fc319bce3fffef39b55ba2ecf1e6c430e2ce72f06'
REL = 'makedefs/MakeInc.def'
SOC = 'config/MASTER.arm64.exynos9825'


def main():
    target = json.loads((ROOT / 'note10/target.json').read_text())
    research = ROOT / target['research_directory']
    reference = json.loads((research / 'xnu-reference.json').read_text())
    source = ROOT / reference['source_directory']
    raw = (source / REL).read_bytes()
    base_master = (source / MASTER).read_bytes()
    if hashlib.sha256(raw).hexdigest() != PIN or hashlib.sha256(base_master).hexdigest() != MASTER_PIN:
        raise ValueError('Pinned MASTER/link input changed')
    selection = json.loads((ROOT / 'note10/private/xnu26-selection/result.json').read_text())
    first = ROOT / 'note10/xnu26/patches/0001-exynos9825-build-selection.patch'
    if hashlib.sha256(first.read_bytes()).hexdigest() != selection['patch_sha256']:
        raise ValueError('Preceding selection patch changed')
    private = ROOT / 'note10/private/xnu26-master'
    stage = private / 'stage'
    (stage / REL).parent.mkdir(parents=True, exist_ok=True)
    (stage / REL).write_bytes(raw)
    (stage / SOC).parent.mkdir(parents=True, exist_ok=True)
    if (stage / SOC).exists():
        (stage / SOC).unlink()
    command = ['git', '-c', 'core.autocrlf=false', 'apply', '--directory', stage.relative_to(ROOT).as_posix()]
    subprocess.run([*command, first.relative_to(ROOT).as_posix()], cwd=ROOT, check=True)
    old = {REL: (stage / REL).read_text(encoding='utf-8'), SOC: ''}
    if hashlib.sha256(old[REL].encode()).hexdigest() != selection['patched_sha256']:
        raise ValueError('Preceding selection result differs')
    soc = base_master.decode()
    soc = replace_one(soc, '#  ARM_EXTRAS_BASE = [ config_pmap_ppl ]',
        '#  ARM_EXTRAS_BASE = [ ]')
    soc = replace_one(soc, '''#if SOC_IS_VIRTUALIZED
#  CPU_COUNTERS_BASE = [ ]
#else /*!SOC_IS_VIRTUALIZED*/
#  CPU_COUNTERS_BASE = [ config_cpu_counters config_pervasive_cpi config_pervasive_energy ]
#endif /*SOC_IS_VIRTUALIZED*/''', '#  CPU_COUNTERS_BASE = [ ]')
    soc = replace_one(soc, '''#if SOC_IS_VIRTUALIZED
#  PARAVIRT_BASE =  [ config_pv_ticket ]
#else
#  PARAVIRT_BASE =  [ ]
#endif''', '#  PARAVIRT_BASE =  [ ]')
    start = soc.index('#if MASTER_CONFIG_ENABLE_KERNEL_TAG && MASTER_CONFIG_ENABLE_SPTM\n')
    end = soc.index('#endif /* MASTER_CONFIG_ENABLE_KERNEL_TAG && MASTER_CONFIG_ENABLE_SPTM */', start)
    end = soc.index('\n', end)
    soc = soc[:start] + '#  VM_EXTRA = [ ]\n#  VM_EXTRA_DEV = [ ]' + soc[end:]
    if re.search(r'^#(?:if|else|elif|endif)\b', soc, re.MULTILINE):
        raise ValueError('Unexpected unresolved MASTER conditional')
    soc = '# Exynos9825 research profile derived from pinned MASTER.arm64.iPhoneOS.\n' + \
          '# No PPL/SPTM, Apple CPU counters or paravirtualized ticket support.\n' + soc
    old_link = '''# Link binary support library
ifneq ($(CURRENT_MACHINE_CONFIG),NONE)
        LDFLAGS_KERNEL_ONLY += -rdynamic -Wl,-force_load,$(KDKROOT)/System/Library/KernelSupport/lib$(CURRENT_MACHINE_CONFIG).os.$(CURRENT_KERNEL_CONFIG).a
endif'''
    link = '''# Link binary support library
ifeq ($(CURRENT_MACHINE_CONFIG),EXYNOS9825)
ifneq ($(PLATFORM),iPhoneOS)
$(error Note10 MASTER profile currently requires PLATFORM=iPhoneOS)
endif
ifneq ($(words $(CURRENT_KERNEL_CONFIG)),1)
$(error Note10 supports only RELEASE DEVELOPMENT DEBUG configurations)
endif
ifeq ($(filter $(CURRENT_KERNEL_CONFIG),RELEASE DEVELOPMENT DEBUG),)
$(error Note10 supports only RELEASE DEVELOPMENT DEBUG configurations)
endif
ifeq ($(strip $(N10_PLATFORM_ARCHIVE)),)
$(error Note10 requires explicit N10_PLATFORM_ARCHIVE; platform support is not supplied by the KDK)
endif
ifneq ($(words $(N10_PLATFORM_ARCHIVE)),1)
$(error Note10 platform archive paths must not contain whitespace)
endif
N10_LINK_COMMA := ,
ifneq ($(findstring $(N10_LINK_COMMA),$(N10_PLATFORM_ARCHIVE)),)
$(error Note10 platform archive paths must not contain commas)
endif
ifneq ($(suffix $(N10_PLATFORM_ARCHIVE)),.a)
$(error Note10 platform archive must have suffix .a)
endif
ifeq ($(wildcard $(N10_PLATFORM_ARCHIVE)),)
$(error Note10 platform archive does not exist)
endif
LDFLAGS_KERNEL_ONLY += -rdynamic -Wl,-force_load,$(N10_PLATFORM_ARCHIVE)
else ifneq ($(CURRENT_MACHINE_CONFIG),NONE)
        LDFLAGS_KERNEL_ONLY += -rdynamic -Wl,-force_load,$(KDKROOT)/System/Library/KernelSupport/lib$(CURRENT_MACHINE_CONFIG).os.$(CURRENT_KERNEL_CONFIG).a
endif'''
    new = {REL: replace_one(old[REL], old_link, link), SOC: soc}
    patch = ''.join(''.join(difflib.unified_diff(old[n].splitlines(True), new[n].splitlines(True),
                    fromfile='a/' + n if old[n] else '/dev/null', tofile='b/' + n)) for n in old)
    patch_file = ROOT / 'note10/xnu26/patches/0006-exynos9825-master-link-input.patch'
    patch_file.write_text(patch, encoding='utf-8', newline='\n')
    relative = patch_file.relative_to(ROOT).as_posix()
    subprocess.run([*command, '--check', relative], cwd=ROOT, check=True)
    subprocess.run([*command, relative], cwd=ROOT, check=True)
    for name, body in new.items():
        if (stage / name).read_bytes() != body.encode():
            raise ValueError('Applied MASTER patch differs')
        path = private / 'patched-inputs' / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding='utf-8', newline='\n')
    subprocess.run([*command, '--reverse', relative], cwd=ROOT, check=True)
    if (stage / REL).read_bytes() != old[REL].encode() or (stage / SOC).exists():
        raise ValueError('MASTER patch reverse differs')
    subprocess.run([*command, '--reverse', first.relative_to(ROOT).as_posix()], cwd=ROOT, check=True)
    if (stage / REL).read_bytes() != raw or (source / REL).read_bytes() != raw or (source / SOC).exists():
        raise ValueError('Original source not preserved')
    report = {'reference_commit': reference['commit'], 'master_source_sha256': MASTER_PIN,
              'preceding_patch_sha256': selection['patch_sha256'],
              'patch_sha256': hashlib.sha256(patch_file.read_bytes()).hexdigest(),
              'files': {n: hashlib.sha256(v.encode()).hexdigest() for n, v in new.items()},
              'link_fragment': link, 'apply_reverse_passed': True, 'source_unchanged': True,
              'platform_archive_implemented': False, 'whole_kernel_build': False}
    (private / 'patch-result.json').write_text(json.dumps(report, indent=2))
    print(json.dumps({'files': len(new), 'apply_reverse_passed': True, 'platform_archive_implemented': False}))


if __name__ == '__main__':
    main()
