"""Run Image make concurrently with stable-source validations on POSIX."""
import os
import signal
import subprocess
import time

def _stop_group(process):
    # Block both signals before disarming the deadline, discard any pending
    # delivery, and keep them ignored until run_concurrent restores handlers.
    blocked={signal.SIGTERM, signal.SIGALRM}
    old_mask=signal.pthread_sigmask(signal.SIG_BLOCK, blocked)
    try:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        signal.signal(signal.SIGALRM, signal.SIG_IGN)
    finally:
        signal.pthread_sigmask(signal.SIG_SETMASK, old_mask)
    try: os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError: pass
    try: process.wait(timeout=3)
    except subprocess.TimeoutExpired: pass
    # Reap descendants even if their parent exited after TERM.
    try: os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError: pass
    process.wait()

def run_concurrent(command, log, validate, timeout=1500):
    start=time.monotonic()
    previous=signal.getsignal(signal.SIGTERM)
    old_alarm=signal.getsignal(signal.SIGALRM)
    old_timer=signal.setitimer(signal.ITIMER_REAL, 0)
    if old_timer != (0.0, 0.0):
        signal.setitimer(signal.ITIMER_REAL, *old_timer)
        raise RuntimeError("Existing real timer cannot be safely replaced")
    def timed_out(signum, frame):
        raise subprocess.TimeoutExpired(command, timeout)
    signal.signal(signal.SIGALRM, timed_out)
    signal.setitimer(signal.ITIMER_REAL, timeout)
    def interrupted(signum, frame):
        raise SystemExit(128+signum)
    signal.signal(signal.SIGTERM, interrupted)
    try:
        _run(command, log, validate, timeout, start)
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, old_alarm)
        signal.signal(signal.SIGTERM, previous)

def _run(command, log, validate, timeout, start):
    with open(log, 'wb') as stream:
        process=subprocess.Popen(command, stdout=stream, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            validate()
            remaining=timeout-(time.monotonic()-start)
            if remaining <= 0: raise subprocess.TimeoutExpired(command, timeout)
            result=process.wait(timeout=remaining)
            if result: raise RuntimeError('Image make failed')
        except BaseException:
            _stop_group(process)
            raise
