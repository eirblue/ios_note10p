"""v160 same-Image ARM64 rootfs RELATIVE relocation proof; no runtime claim."""
import re
import struct

IMAGE_LIMIT = 57*1024*1024
R_AARCH64_RELATIVE = 1027
SYMBOLS = {'_text', '__initramfs_size', 'populate_rootfs', '__initcall_populate_rootfsrootfs',
           '__initcall5_start', '__initcallrootfs_start', '__initcall6_start', '__rela_offset', '__rela_size'}


def linked_rootfs_proof(image, symbols, archive_size, linked_extent, observation):
    observation.update(schema='note10-v160-rootfs-relocation-observation-v1', passed=False, checks={})
    checks = observation['checks']
    def check(name, condition):
        checks[name] = bool(condition)
        if not condition:
            raise ValueError('rootfs relocation proof: '+name)
    check('bounded_inputs', type(image) is bytes and 64 <= len(image) <= IMAGE_LIMIT and
          image[56:60] == b'ARM\x64' and type(symbols) is str and len(symbols) <= 16*1024*1024 and
          type(archive_size) is int and 0 < archive_size <= len(image) and
          type(linked_extent) is int and 64 <= linked_extent <= IMAGE_LIMIT)
    observation.update(Image_bytes=len(image), archive_bytes=archive_size, linked_extent=linked_extent)
    table = {}
    observation['symbols'] = table
    for line in symbols.splitlines():
        row = re.fullmatch(r'([0-9a-fA-F]{1,16})\s+(\S)\s+(\S+)', line)
        if row and row[3] in SYMBOLS:
            check('unique_symbol_'+row[3], row[3] not in table)
            table[row[3]] = int(row[1], 16)
    check('exact_rootfs_relocation_symbols', set(table) == SYMBOLS)
    start = table['_text']
    limit = min(len(image), linked_extent)
    header_offset, header_extent = struct.unpack_from('<QQ', image, 8)
    observation.update(header_text_offset=header_offset, header_linked_extent=header_extent,
                       KIMAGE_VADDR=start-header_offset)
    check('bound_header', header_extent == linked_extent and header_offset < 2**21 and
          header_offset % 4096 == 0 and header_offset <= start and start+limit <= 2**64)
    def word(name):
        address = table[name]
        offset = address-start
        observation[name+'_offset'] = offset
        check(name+'_word_bounds', 0 <= offset <= limit-8 and address % 8 == 0)
        return struct.unpack_from('<Q', image, offset)[0], offset
    size, size_offset = word('__initramfs_size')
    raw_slot, slot_offset = word('__initcall_populate_rootfsrootfs')
    slot = table['__initcall_populate_rootfsrootfs']
    target = table['populate_rootfs']
    rela_offset = table['__rela_offset']-header_offset
    rela_size = table['__rela_size']
    observation.update(declared_archive_bytes=size, raw_initcall_slot=raw_slot, expected_target=target,
                       relocation_table_offset=rela_offset, relocation_table_bytes=rela_size)
    checks.update(declared_size_matches=size == archive_size,
                  rootfs_slot_in_section=table['__initcall5_start'] <= table['__initcallrootfs_start'] <= slot and
                  slot+8 <= table['__initcall6_start'],
                  rootfs_section_in_Image=start <= table['__initcall5_start'] and
                  table['__initcall6_start'] <= start+limit,
                  target_in_Image=start <= target < start+limit,
                  raw_slot_is_unapplied_zero=raw_slot == 0)
    # __rela_offset is relative to KIMAGE_VADDR; raw offset is relative to _text.
    check('relocation_table_bounds', 0 <= rela_offset <= limit and rela_offset % 8 == 0 and
          0 < rela_size <= limit-rela_offset and rela_size % 24 == 0 and
          table['__rela_offset'] < 2**32 and rela_size < 2**32)
    count = 0
    matches = []
    for offset in range(rela_offset, rela_offset+rela_size, 24):
        address, info, addend = struct.unpack_from('<QQQ', image, offset)
        if address == slot:
            count += 1
            if len(matches) < 2:
                matches.append(dict(file_offset=offset, r_offset=address, r_info=info, addend=addend))
    observation.update(relocation_table_records=rela_size//24, matching_relocation_count=count,
                       matching_relocations=matches)
    checks.update(unique_slot_relocation=count == 1,
                  exact_relative_type=count == 1 and matches[0]['r_info'] == R_AARCH64_RELATIVE,
                  relocation_addend_matches=count == 1 and matches[0]['addend'] == target)
    failed = [name for name, ok in checks.items() if not ok]
    if failed:
        raise ValueError('rootfs relocation proof: '+','.join(failed))
    observation['passed'] = True
    return dict(schema='note10-v160-linked-rootfs-relocation-proof-v1', declared_archive_bytes=size,
                size_word_offset=size_offset, rootfs_initcall_slot_offset=slot_offset,
                rootfs_initcall_target=target, rootfs_section_start=table['__initcallrootfs_start'],
                rootfs_section_end=table['__initcall6_start'], raw_initcall_slot=raw_slot,
                relocation_table_offset=rela_offset, relocation_table_bytes=rela_size,
                relocation_record_offset=matches[0]['file_offset'], relocation_type=R_AARCH64_RELATIVE,
                relocation_addend=matches[0]['addend'], runtime_population_proved=False)


def producer_rootfs_proof(result, image, symbols, persist):
    observation = {}
    result['rootfs_linkage_observation'] = observation
    try:
        proof = linked_rootfs_proof(image, symbols, result['initramfs_bytes'], result['linked_extent'], observation)
    except BaseException as error:
        observation.update(error_type=type(error).__name__, error=str(error)[:1024])
        persist()
        raise
    result['rootfs_materialization'] = proof
    persist()
    return proof


def self_check():
    # One new relocation bundle; no v159 or earlier fixture is invoked.
    base = 0xffff000000080000
    text_offset = 0x80000
    image = bytearray(1024)
    image[56:60] = b'ARM\x64'
    struct.pack_into('<QQ', image, 8, text_offset, len(image))
    struct.pack_into('<Q', image, 80, 64)
    table = {'_text': base, '__initramfs_size': base+80, 'populate_rootfs': base+128,
             '__initcall5_start': base+224, '__initcallrootfs_start': base+240,
             '__initcall_populate_rootfsrootfs': base+256, '__initcall6_start': base+272,
             '__rela_offset': text_offset+512, '__rela_size': 48}
    struct.pack_into('<QQQ', image, 512, base+256, R_AARCH64_RELATIVE, base+128)
    struct.pack_into('<QQQ', image, 536, base+264, R_AARCH64_RELATIVE, base+136)
    def symbols(rows):
        return ''.join(f'{value:016x} A {name}\n' for name, value in rows.items())
    saved = []
    result = dict(initramfs_bytes=64, linked_extent=len(image))
    producer_rootfs_proof(result, bytes(image), symbols(table), lambda: saved.append(dict(result['rootfs_linkage_observation'])))
    assert len(saved) == 1 and saved[0]['passed'] and result['rootfs_materialization']['relocation_addend'] == base+128
    variants = ('size', 'raw-slot', 'wrong-type', 'symbol-index', 'wrong-addend', 'missing-relocation',
                'duplicate-relocation', 'table-past-end', 'table-misaligned', 'table-partial-row',
                'duplicate-symbol', 'missing-symbol', 'header-offset', 'header-extent')
    for mutation in variants:
        raw = bytearray(image)
        rows = dict(table)
        if mutation == 'size': struct.pack_into('<Q', raw, 80, 65)
        elif mutation == 'raw-slot': struct.pack_into('<Q', raw, 256, base+128)
        elif mutation == 'wrong-type': struct.pack_into('<Q', raw, 520, R_AARCH64_RELATIVE+1)
        elif mutation == 'symbol-index': struct.pack_into('<Q', raw, 520, (1 << 32)|R_AARCH64_RELATIVE)
        elif mutation == 'wrong-addend': struct.pack_into('<Q', raw, 528, base+136)
        elif mutation == 'missing-relocation': struct.pack_into('<Q', raw, 512, base+264)
        elif mutation == 'duplicate-relocation': struct.pack_into('<Q', raw, 536, base+256)
        elif mutation == 'table-past-end': rows['__rela_offset'] = text_offset+len(raw)-8
        elif mutation == 'table-misaligned': rows['__rela_offset'] += 1
        elif mutation == 'table-partial-row': rows['__rela_size'] = 47
        elif mutation == 'missing-symbol': del rows['__rela_offset']
        elif mutation == 'header-offset': struct.pack_into('<Q', raw, 8, 2**21)
        elif mutation == 'header-extent': struct.pack_into('<Q', raw, 16, len(raw)+8)
        text = symbols(rows)
        if mutation == 'duplicate-symbol': text += f'{table["__rela_offset"]:016x} A __rela_offset\n'
        result = dict(initramfs_bytes=64, linked_extent=len(raw))
        saved = []
        try:
            producer_rootfs_proof(result, bytes(raw), text, lambda: saved.append(dict(result['rootfs_linkage_observation'])))
        except ValueError:
            assert len(saved) == 1 and saved[0]['passed'] is False and 'error' in saved[0]
            assert any(value is False for value in saved[0]['checks'].values())
            assert 'rootfs_materialization' not in result
            continue
        raise AssertionError('malformed relocation accepted: '+mutation)


if __name__ == '__main__':
    self_check()
