"""Only the new inactive compression-choice expectation; no old fixture runs."""
import v294_recovery_prepare as producer


def predicate():
    house = producer.retained.house
    settings = dict(producer.retained.p.REQUIRED_CONFIG, **producer.SETTINGS)
    settings.pop('INITRAMFS_COMPRESSION_NONE')
    # A disabled choice is absent in the actual generated config, not '=n'.
    raw = ('\n'.join('# CONFIG_' + key + ' is not set' if value == 'n' else
                     'CONFIG_' + key + '=' + value for key, value in settings.items()) + '\n').encode()
    values = house.check_config(raw, producer.SETTINGS)
    assert values['INITRAMFS_SOURCE'] == '""' and values.get('INITRAMFS_COMPRESSION_NONE', 'n') == 'n'
    try:
        house.check_config(raw, dict(producer.SETTINGS, INITRAMFS_COMPRESSION_NONE='y'))
    except ValueError as error:
        assert str(error).endswith('INITRAMFS_COMPRESSION_NONE')
    else:
        raise AssertionError('inactive compression choice accepted as enabled')
    return dict(passed=True, groups=1, variants=2, assertions=2)
