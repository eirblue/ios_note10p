"""One NEW section-only pure-Python batch; original compat cases stay retained."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
sys.dont_write_bytecode = True
import v134_pid1_compat as compat
import v134_pid1_sections as sections

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    out = args.output.resolve()
    if out.exists() or args.output.is_symlink():
        parser.error('fresh section-only NEW output required')
    out.mkdir(parents=True)
    result = dict(schema='note10-v134-PID1-sections-NEW-test-v1', passed=False,
                  test_process_invocations=1, compiler_invocations=0,
                  old_compat_cases_replayed=0, device_commands=0, cases=[])

    def case(name, condition):
        if not condition:
            raise AssertionError(name)
        result['cases'].append(name)

    def rejects(function, *args):
        try:
            function(*args)
        except ValueError:
            return True
        return False

    try:
        binding = compat.derive_binding(*[(ROOT/('note10/device_test/'+name)).read_bytes()
                                         for name in ('v133_build.py','v130_loader.c','v133_cycle.py')])
        identity, cycle = 'a'*32, 'b'*32

        def pid(stage, tag='132', ident=identity, cyc=cycle):
            return ('[ 1] N10XNU'+tag+' id='+ident+' cycle='+cyc+' stage='+stage+'\n').encode()

        native = ('[ 2] N10XNU133 id='+identity+' ').encode()
        first = pid('begin')+pid('kexec-load-once')+native+b'stage=score-power errno=-16 owner=synthetic-first\n'
        second = pid('begin')+pid('kexec-reboot-once')+native+b'stage=score-halt errno=-110 owner=synthetic-second\n'
        data = first+second
        interpreted = sections.decode_sections(data,identity,cycle,binding)
        rows = interpreted['sections']
        case('repeated-exact-begins-stay-independent', len(rows)==2 and all(row['qualified_current133_PID1'] for row in rows))
        case('section-local-load-reboot-counts',
             rows[0]['observation']['internal_kexec_load_attempts_observed']==1 and
             rows[0]['observation']['internal_kexec_REBOOT_attempts_observed']==0 and
             rows[1]['observation']['internal_kexec_load_attempts_observed']==0 and
             rows[1]['observation']['internal_kexec_REBOOT_attempts_observed']==1)
        case('native-refusal-does-not-cross-boundary', rows[0]['observation']['gate_refusals'][0]['owner']=='synthetic-first' and
             rows[1]['observation']['gate_refusals'][0]['owner']=='synthetic-second')
        for label, dirty in [('same-identity',pid('begin')),('wrong-identity',pid('begin',ident='c'*32)),
                             ('wrong-cycle',pid('begin',cyc='d'*32))]:
            dirty = dirty.replace(b'begin\n',b'begin JUNK\n')
            dirty += native+b'stage=score-halt errno=-110 owner=dirty-tail\n'
            dirty += native+b'final_qualified=1 EL1_preserved=1 actual_XNU_pending=1\n'
            split = sections.decode_sections(first+dirty+second,identity,cycle,binding)['sections']
            case(label+'-dirty-begin-closes-previous-section',
                 len(split)==3 and not split[1]['qualified_current133_PID1'] and split[1]['observation'] is None and
                 len(split[0]['observation']['gate_refusals'])==1 and
                 split[0]['observation']['gate_refusals'][0]['owner']=='synthetic-first' and
                 not split[0]['observation']['final_hook_qualified_observed'] and
                 not split[2]['observation']['final_hook_qualified_observed'])
        case('logical-indices-are-not-epochs-or-aggregates', [row['logical_section_index'] for row in rows]==[0,1] and
             not interpreted['logical_indices_are_boot_epochs'] and not interpreted['cross_section_aggregation_performed'])
        for label, barrier in [('wrong-identity',pid('begin',ident='c'*32)),('wrong-cycle',pid('begin',cyc='d'*32)),
                               ('native-producer',pid('begin',tag='133')),('other-producer',pid('begin',tag='99999999999')),
                               ('malformed-identity',pid('begin',ident='not-hex')),('malformed-cycle',pid('begin',cyc='not-hex')),
                               ('noncanonical-line',pid('begin').replace(b'begin\n',b'begin \n'))]:
            foreign = barrier+native+b'stage=score-power errno=-5 owner=foreign-section\n'
            split = sections.decode_sections(first+foreign+second,identity,cycle,binding)['sections']
            case(label+'-is-barrier-never-qualified', len(split)==3 and not split[1]['qualified_current133_PID1'] and split[1]['observation'] is None and
                 len(split[0]['observation']['gate_refusals'])==1 and len(split[2]['observation']['gate_refusals'])==1)
        prefix = native+b'fresh_owned32M platform_ready=1 xnu_pending=1\n'
        reservations = sections.decode_sections(prefix+first+prefix+second,identity,cycle,binding)
        case('prebegin-reservation-never-reused', all(not row['observation']['reservation_ready_observed'] for row in reservations['sections']))
        unrelated = sections.decode_sections(native+b'stage=score-halt errno=-110 owner=unbound\n',identity,cycle,binding)
        case('no-begin-has-no-admitted-section', unrelated['sections']==[])
        case('exact-section-boundary-byte-offsets', rows[0]['end_byte']==rows[1]['start_byte'] and rows[1]['end_byte']==len(data))
        case('section-cap-refuses-extra-barrier', rejects(sections.decode_sections,pid('begin')*(sections.MAX_SECTIONS+1),identity,cycle,binding))
        case('byte-cap-refuses-oversize', rejects(sections.decode_sections,b'x'*(compat.MAX_LOG_BYTES+1),identity,cycle,binding))
        case('wrong-source-binding-refused', rejects(sections.decode_sections,data,identity,cycle,dict(binding,native_prefix='N10XNU132')))
        final = pid('begin')+native+b'final_qualified=1 EL1_preserved=1 actual_XNU_pending=1\n'
        proof = sections.decode_sections(final,identity,cycle,binding)['sections'][0]['observation']
        case('native-final-remains-nonphysical', proof['final_hook_qualified_observed'] and not proof['physical_XNU_entry_established'] and not proof['log_reboot_epoch_proven'])
        result.update(passed=True,source_sha256={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in
                      ('note10/device_test/v134_pid1_sections.py','note10/device_test/test_v134_pid1_sections.py')},
                      retained_compat_sha256=hashlib.sha256((ROOT/'note10/device_test/v134_pid1_compat.py').read_bytes()).hexdigest())
    finally:
        (out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({'passed':result['passed'],'NEW_section_cases':len(result['cases'])}))


if __name__=='__main__':
    main()
