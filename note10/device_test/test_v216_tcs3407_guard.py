"""Only the new closed-stock TCS3407 function guard cases, without a compiler."""
import v216_tcs3407_guard as guard


def project(function,eol):
    # Only the four exact new EOL conditionals are interpreted in this fixture.
    out=[];active=[]
    for line in function.splitlines(keepends=True):
        if line==b'#ifdef CONFIG_AMS_OPTICAL_SENSOR_EOL_MODE\n':active.append(eol)
        elif line==b'#ifndef CONFIG_AMS_OPTICAL_SENSOR_EOL_MODE\n':active.append(not eol)
        elif line==b'#endif\n':
            if not active:raise AssertionError('unmatched new EOL guard')
            active.pop()
        elif line.startswith(b'#'):raise AssertionError('unexpected fixture directive')
        elif all(active):out.append(line)
    if active:raise AssertionError('unterminated new EOL guard')
    return b''.join(out)


def run(stock):
    assertions=0;variants=0
    def check(ok):
        nonlocal assertions
        assertions+=1
        if not ok:raise AssertionError('TCS guard assertion '+str(assertions))
    def rejected(raw):
        try:guard.prepare(raw)
        except ValueError:return True
        return False
    # Group1: the production transform once, then both exact feature selections.
    variants+=1;changed=guard.prepare(stock);before_at=stock.index(guard.BEFORE)
    check(changed[:before_at]==stock[:before_at] and changed[before_at+len(guard.AFTER):]==stock[before_at+len(guard.BEFORE):])
    check(project(guard.AFTER,True)==guard.BEFORE)
    check(changed.count(guard.AFTER)==1)
    variants+=1;off=project(guard.AFTER,False)
    check(all(token not in off for token in (b'pwm_state',b'->pwm',b'pinctrl_pwm',b'debug_pwm_duty',b'period2',b'PWM_POLARITY')))
    check(b'tcs3407_print_reg_status();'in off and b'tcs3407_debug_var(data);'in off)
    body=guard.UNSUPPORTED.split(b'\n',1)[1].rsplit(b'#endif\n',1)[0]
    check(body in off and off.index(body)<off.index(b'data->debug_mode = mode;'))
    check(b'case 3:'not in off and b'case 4:'not in off and b'mutex_unlock(&data->activelock);\n\t\treturn -EOPNOTSUPP;'in off)
    # Group2: exact source admission, not an old parser or sensor fixture replay.
    variants+=1;check(rejected(stock[:-1]+b'!'))
    variants+=1;check(rejected(changed))
    return dict(groups=2,variants=variants,assertions=assertions,production_transforms=1,old_tests_replayed=0,host_compiles=0,native_input_reads=0)
