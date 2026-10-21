"""Generate/check the first pinned XNU 12377 build-selection patch, without editing the reference."""
import difflib
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
NDK = Path(r'C:/Program Files/Unity/Hub/Editor/2021.3.20f1/Editor/Data/PlaybackEngines/AndroidPlayer/NDK')
PIN = '36f6f4ed246da4d26bb4ffb6935de6160a276561c87a7cb8e19aaacc494eb29f'
REL = Path('makedefs/MakeInc.def')

def replace_one(text, old, new):
    if text.count(old) != 1: raise ValueError('Pinned source context mismatch: ' + old[:70])
    return text.replace(old,new,1)

def fixture(text):
    # Evaluate actual source fragments, not a Python recreation of Make conditionals.
    # SDK discovery/link rules are outside this selection-only test.
    front = text[:text.index('# Deployment target flag')]
    start = text.index('ARCH_STRING_FOR_CURRENT_MACHINE_CONFIG ?=')
    arch = text[start:text.index('BUILD_STATIC_LINK := 1',start)]
    assignment = next(s for s in text.splitlines() if s.startswith('ARCH_FLAGS_ARM64\t')
                      and '$(ARCH_STRING_FOR_CURRENT_MACHINE_CONFIG)' in s)
    return front + '\n' + arch + '\n' + assignment + '''
$(info architecture=$(ARCH_STRING_FOR_CURRENT_MACHINE_CONFIG))
$(info arch_flags=$(ARCH_FLAGS_ARM64))
$(info machine_flags=$(MACHINE_FLAGS_ARM64_$(CURRENT_MACHINE_CONFIG)))
$(info bti=$(BTI_BUILD))
$(info bti_flags=$(ARM64_EXTRA_BUILD_FLAGS))
$(info supported=$(SUPPORTED_ARM64_MACHINE_CONFIGS))
all: ;
'''

def main():
    target = json.loads((ROOT/'note10/target.json').read_text())
    research = ROOT/target['research_directory']
    reference = json.loads((research/'xnu-reference.json').read_text())
    source = ROOT/reference['source_directory']
    original = (source/REL).read_bytes()
    if hashlib.sha256(original).hexdigest() != PIN: raise ValueError('Reference MakeInc.def hash mismatch')
    old = original.decode()
    new = replace_one(old,'T8132 T8142 VMAPPLE\n','T8132 T8142 VMAPPLE EXYNOS9825\n')
    new = replace_one(new,'BTI_BUILD = 1\n','''BTI_BUILD = 1
ifeq ($(CURRENT_MACHINE_CONFIG),EXYNOS9825)
# Exynos9825 cores do not supply the Apple arm64e/BTI build target.
override BTI_BUILD := 0
endif
''')
    marker = 'MACHINE_FLAGS_ARM64_VMAPPLE = -DARM64_BOARD_CONFIG_VMAPPLE              -march=armv8.5a+sme2\n'
    new = replace_one(new,marker,marker+'MACHINE_FLAGS_ARM64_EXYNOS9825 = -DARM64_BOARD_CONFIG_EXYNOS9825 -march=armv8.2-a+crypto -mcpu=generic\n')
    new = replace_one(new,'ARCH_STRING_FOR_CURRENT_MACHINE_CONFIG ?=\n','''ARCH_STRING_FOR_CURRENT_MACHINE_CONFIG ?=
ifeq ($(CURRENT_MACHINE_CONFIG),EXYNOS9825)
# Reject a command-line arm64e override for this non-PAuth kernel target.
override ARCH_STRING_FOR_CURRENT_MACHINE_CONFIG := arm64
endif
''')
    patch = ''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),
                fromfile='a/'+REL.as_posix(),tofile='b/'+REL.as_posix()))
    patch_path = ROOT/'note10/xnu26/patches/0001-exynos9825-build-selection.patch'
    patch_path.parent.mkdir(parents=True,exist_ok=True)
    patch_path.write_text(patch,newline='\n')
    private = ROOT/'note10/private/xnu26-selection'
    private.mkdir(parents=True,exist_ok=True)
    subprocess.run(['git','-c','core.autocrlf=false','apply','--check','--directory',source.relative_to(ROOT).as_posix(),
                    patch_path.relative_to(ROOT).as_posix()],cwd=ROOT,check=True)
    stage = private/'stage'
    (stage/REL).parent.mkdir(parents=True,exist_ok=True)
    (stage/REL).write_bytes(original)
    args = ['git','-c','core.autocrlf=false','apply','--directory',stage.relative_to(ROOT).as_posix()]
    subprocess.run([*args,patch_path.relative_to(ROOT).as_posix()],cwd=ROOT,check=True)
    if (stage/REL).read_bytes() != new.encode(): raise ValueError('Applied patch differs')
    subprocess.run([*args,'--reverse',patch_path.relative_to(ROOT).as_posix()],cwd=ROOT,check=True)
    if (stage/REL).read_bytes() != original: raise ValueError('Reverse patch differs')
    make = NDK/'prebuilt/windows-x86_64/bin/make.exe'
    if not make.is_file(): raise FileNotFoundError('NDK GNU Make missing')
    files = {}
    for name,text in [('old',old),('new',new)]:
        files[name] = private/(name+'.mk');files[name].write_text(fixture(text),newline='\n')
    def evaluate(name,machine,arch='arm64e',bti='1'):
        cmd=[str(make),'--no-print-directory','-f',str(files[name]),'all',
             'CURRENT_ARCH_CONFIG=ARM64','CURRENT_ARCH_CONFIG_LC=arm64','CURRENT_KERNEL_CONFIG_LC=development',
             'CURRENT_MACHINE_CONFIG='+machine,'CURRENT_MACHINE_CONFIG_LC='+machine.lower(),
             'ARCH_STRING_FOR_CURRENT_MACHINE_CONFIG='+arch,'BTI_BUILD='+bti]
        r=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True,check=True)
        return {k:v.strip() for line in r.stdout.splitlines() if '=' in line for k,v in [line.split('=',1)]}
    results=[]
    for arch in ('','arm64','arm64e'):
        for bti in ('0','1'):
            r=evaluate('new','EXYNOS9825',arch,bti)
            assert r['architecture']=='arm64' and r['arch_flags']=='-arch arm64' and r['bti']=='0'
            assert r['machine_flags']=='-DARM64_BOARD_CONFIG_EXYNOS9825 -march=armv8.2-a+crypto -mcpu=generic'
            assert '-UXNU_BUILT_WITH_BTI' in r['bti_flags'] and 'EXYNOS9825' in r['supported'].split()
            results.append({'machine':'EXYNOS9825','input_arch':arch,'input_bti':bti,'output':r})
    for machine in ('T8101','T6050','VMAPPLE'):
        a,b=evaluate('old',machine),evaluate('new',machine)
        assert b['supported'].split()==a['supported'].split()+['EXYNOS9825']
        assert all(a[k]==b[k] for k in a if k!='supported')
        results.append({'machine':machine,'existing_selection_preserved':True})
    if (source/REL).read_bytes()!=original: raise ValueError('Pristine source changed')
    report={'source_sha256':PIN,'patched_sha256':hashlib.sha256(new.encode()).hexdigest(),
            'patch_sha256':hashlib.sha256(patch_path.read_bytes()).hexdigest(),
            'make_executable':str(make),'cases':results,'applied_and_reversed_in_stage':True,
            'pristine_source_unchanged':True,'scope':'Make selection fragments only; not a full XNU configuration/build.'}
    (private/'result.json').write_text(json.dumps(report,indent=2))
    print(json.dumps({'selection_cases':len(results),'patch_apply_reverse':'passed','pristine_source_unchanged':True}))

if __name__=='__main__': main()
