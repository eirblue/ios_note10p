"""Independent bounded sections of immutable133 captures; indices are not epochs."""
import re
import v134_pid1_compat as compat

MAX_SECTIONS = 32


def decode_sections(raw, identity, cycle, binding):
    """Every begin-looking line is a barrier, including unqualified identities."""
    if not compat._binding_valid(binding):
        raise ValueError('exact source-derived immutable133 binding required')
    if any(type(value) is not str or re.fullmatch('[0-9a-f]{32}', value) is None
           for value in (identity, cycle)):
        raise ValueError('exact current build/cycle required')
    if type(raw) is not bytes or not 0 < len(raw) <= compat.MAX_LOG_BYTES:
        raise ValueError('one bounded saved capture required')
    # A malformed or foreign producer/identity/cycle must still terminate the
    # previous section. Qualification below is deliberately much narrower.
    barriers = []
    pattern = rb'(?<![A-Za-z0-9_])N10XNU[^\n]*stage=begin[^\n]*$'
    for match in re.finditer(pattern, raw, re.M):
        if len(barriers) == MAX_SECTIONS:
            raise ValueError('begin-barrier count exceeds bounded section limit')
        barriers.append(match)
    exact = ('N10XNU132 id=' + identity + ' cycle=' + cycle + ' stage=begin').encode()
    result = dict(schema='note10-v134-independent133-sections-v1',
                  build_evidence_id=identity, cycle=cycle, source_binding=binding,
                  retrospective_sections=True, logical_indices_are_boot_epochs=False,
                  cross_section_aggregation_performed=False, prebegin_bytes_discarded=True,
                  physical_XNU_entry_established=False, watchdog_reset_cause_established=False,
                  section_limit=MAX_SECTIONS, sections=[],
                  evidence_limit='Saved-log logical sections only. Each begin-looking line '
                  'ends the previous section, regardless of identity or producer. No section '
                  'merging, native boot-count inference, reset cause, physical XNU entry or '
                  'absence inference. Prebegin reservation records are never reused.')
    for index, barrier in enumerate(barriers):
        end = barriers[index + 1].start() if index + 1 < len(barriers) else len(raw)
        section = dict(logical_section_index=index, start_byte=barrier.start(), end_byte=end,
                       qualified_current133_PID1=False, observation=None)
        if barrier.group() in (exact, exact + b'\r'):
            observation = compat.decode(raw[barrier.start():end], identity, cycle, binding)
            if not observation['identity_bound_PID1_begin_observed'] or observation['ambiguous_begin']:
                raise ValueError('independent qualified section boundary differs')
            # No prebegin prefix from any other section is passed to decode.
            if observation['reservation_ready_observed']:
                raise ValueError('prebegin reservation crossed a section boundary')
            section.update(qualified_current133_PID1=True, observation=observation)
        result['sections'].append(section)
    return result
