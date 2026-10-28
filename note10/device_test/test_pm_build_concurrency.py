"""POSIX process-group lifecycle checks for concurrent Image validation."""
import argparse, hashlib, json, os, signal, subprocess, sys, tempfile, time
from pathlib import Path
from pm_build_concurrency import run_concurrent

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--output',required=True);a=ap.parse_args();out=Path(a.output);out.mkdir(parents=True,exist_ok=True)
 if os.name!='posix':
  (out/'result.json').write_text(json.dumps({'skipped':True,'reason':'POSIX required'})+'\n');return
 cases=[]
 def run(name,command,check,timeout=5):
  try:run_concurrent(command,out/(name+'.log'),check,timeout)
  except BaseException as e:return type(e).__name__
  return 'ok'
 def good():time.sleep(.1)
 cmd=[sys.executable,'-c','import time;time.sleep(.3)']
 assert run('overlap',cmd,good)=='ok';cases.append('overlap')
 def spawned(name, parent_exits=False):
  pidfile=out/(name+'.pid')
  child='import signal,time;signal.signal(signal.SIGTERM,signal.SIG_IGN);time.sleep(20)'
  script='import subprocess,sys,time,pathlib;p=subprocess.Popen([sys.executable,"-c",sys.argv[2]]);pathlib.Path(sys.argv[1]).write_text(str(p.pid));'+('sys.exit(3)' if parent_exits else 'time.sleep(20)')
  return [sys.executable,'-c',script,str(pidfile),child],pidfile
 def ready(path):
  for _ in range(100):
   if path.exists():return
   time.sleep(.02)
  raise AssertionError('child did not start')
 def dead(path):
  pid=int(path.read_text())
  for _ in range(100):
   try:
    status=Path('/proc')/str(pid)/'stat'
    if not status.exists() or status.read_text().split(') ')[1].startswith('Z'):return
   except (FileNotFoundError,ProcessLookupError):return
   time.sleep(.02)
  raise AssertionError('child survived cancellation')
 command,pid=spawned('compiler-failure',True)
 assert run('compiler-failure',command,lambda:ready(pid))=='RuntimeError';dead(pid);cases.append('compiler-failure')
 command,pid=spawned('validator-failure')
 def fail():ready(pid);raise ValueError('validation failed')
 assert run('validator-failure',command,fail)=='ValueError';dead(pid)
 # The process group ignores TERM. Fail just before the deadline so the old
 # alarm would fire during the bounded wait unless cleanup disarms it.
 pid=out/'deadline-cleanup.pid'
 child='import os,signal,time,pathlib,sys;signal.signal(signal.SIGTERM,signal.SIG_IGN);pathlib.Path(sys.argv[1]).write_text(str(os.getpid()));time.sleep(20)'
 parent='import signal,subprocess,sys,time;signal.signal(signal.SIGTERM,signal.SIG_IGN);subprocess.Popen([sys.executable,"-c",sys.argv[2],sys.argv[1]]);time.sleep(20)'
 command=[sys.executable,'-c',parent,str(pid),child]
 deadline_start=time.monotonic()
 def deadline_failure():
  ready(pid);time.sleep(max(0,1.7-(time.monotonic()-deadline_start)));raise ValueError('failure before deadline')
 assert run('deadline-cleanup',command,deadline_failure,2)=='ValueError';dead(pid)
 cases.append('validator-failure')
 command,pid=spawned('timeout')
 assert run('timeout',command,lambda:(ready(pid),time.sleep(2)),.4)=='TimeoutExpired';dead(pid);cases.append('timeout')
 command,pid=spawned('interrupt')
 def interrupted():ready(pid);raise KeyboardInterrupt()
 assert run('interrupt',command,interrupted)=='KeyboardInterrupt';dead(pid);cases.append('interrupt')
 command,pid=spawned('sigterm');prior=signal.getsignal(signal.SIGTERM)
 def sigterm():ready(pid);os.kill(os.getpid(),signal.SIGTERM)
 assert run('sigterm',command,sigterm)=='SystemExit';dead(pid);assert signal.getsignal(signal.SIGTERM)==prior;cases.append('sigterm')
 (out/'result.json').write_text(json.dumps({'passed':True,'cases':cases,'harness_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'helper_sha256':hashlib.sha256(Path(__file__).with_name('pm_build_concurrency.py').read_bytes()).hexdigest()})+'\n')
if __name__=='__main__':main()
