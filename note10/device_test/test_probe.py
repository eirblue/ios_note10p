"""PC tests of package, transport guards and synthetic recovery observations."""
import gzip
import io
import json
import os
import re
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tarfile
import tempfile
import unittest
import zipfile

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import analyze_capture as analysis
import build_package
import run_probe


def synthetic_tree():
    q = lambda *values: struct.pack('>'+'I'*len(values), *values)
    reg = lambda a,s: struct.pack('>QQ', a,s)
    return {'/': {'#address-cells':q(2), '#size-cells':q(2)},
            '/memory@80000000': {'device_type':b'memory\0','reg':reg(0x80000000,0x10000000)},
            '/reserved-memory': {'#address-cells':q(2),'#size-cells':q(2),'ranges':b''},
            '/reserved-memory/fixed@81000000': {'reg':reg(0x81000000,0x100000),'no-map':b''},
            '/reserved-memory/dynamic': {'size':struct.pack('>Q',0x400000)},
            '/interrupt-controller@10101000': {'compatible':b'arm,cortex-a15-gic\0'}}


def make_fdt(nodes):
    names = bytearray(); offsets = {}; data = bytearray()
    def word(v):data.extend(struct.pack('>I',v))
    def pad():data.extend(b'\0' * (-len(data)%4))
    def node(path):
        word(1);data.extend((path.rsplit('/',1)[-1] if path!='/' else '').encode()+b'\0');pad()
        for key,value in nodes[path].items():
            if key not in offsets:offsets[key]=len(names);names.extend(key.encode()+b'\0')
            word(3);word(len(value));word(offsets[key]);data.extend(value);pad()
        for child in nodes:
            if child!='/' and (child.rsplit('/',1)[0] or '/')==path:node(child)
        word(2)
    node('/');word(9)
    reservations=struct.pack('>4Q',0x82000000,0x1000,0,0)
    off=40+len(reservations);strings=off+len(data);total=strings+len(names)
    return struct.pack('>10I',0xd00dfeed,total,off,strings,40,17,16,0,len(names),len(data))+reservations+data+names


def capture(directory):
    directory.mkdir(parents=True, exist_ok=True)
    (directory/'COMPLETE').write_text('NOTE10_PROBE_COMPLETE\n')
    (directory/'properties.txt').write_text('ro.product.model=SM-N976N\nro.product.device=d2x\nro.twrp.version=synthetic\n')
    (directory/'live.dtb').write_bytes(make_fdt(synthetic_tree()))
    (directory/'config.gz').write_bytes(gzip.compress(b'CONFIG_KEXEC=y\nCONFIG_ARM64_4K_PAGES=y\n'))
    (directory/'iomem.txt').write_text('80000000-8fffffff : System RAM\n')


class FakeAdb:
    def __init__(self, source=None):
        self.serial=None;self.source=source;self.calls=[]
        self.values={('devices',):'List of devices attached\nTEST recovery\n',
                     ('shell','getprop','ro.product.model'):'SM-N976N',
                     ('shell','getprop','ro.product.device'):'d2x',
                     ('shell','getprop','ro.twrp.version'):'synthetic',
                     ('shell','id','-u'):'0',('shell','uname','-m'):'aarch64'}
    def call(self,*args,**kwargs):
        self.calls.append(args)
        if args in self.values:return self.values[args].encode()
        if args[0]=='push':return b'ok'
        if args[:3]==('shell','sh','/tmp/note10-probe-collect.sh'):
            return ('NOTE10_PROBE_OUTPUT='+args[3]).encode()
        if args[:2]==('shell','cat') and args[2].endswith('/COMPLETE'):return b'NOTE10_PROBE_COMPLETE\n'
        if args[0]=='pull':shutil.copytree(self.source,args[2]);return b'ok'
        raise AssertionError('Unexpected ADB operation: '+repr(args))
    def text(self,*args,**kwargs):return self.call(*args,**kwargs).decode().strip()


class ProbeTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=build_package.OUT)
        self.root=Path(self.temp.name)
    def tearDown(self):
        if not self.root.resolve().is_relative_to(build_package.OUT.resolve()):
            raise ValueError('Test cleanup escaped its private workspace')
        self.temp.cleanup()

    def test_success_keeps_boot_contract_unverified(self):
        capture(self.root);r=analysis.analyze(self.root)
        self.assertTrue(r['live_tree_observed']);self.assertEqual(r['memory_nodes'][0]['ranges'][0]['start'],'0x80000000')
        self.assertEqual(r['fdt_memreserve'][0]['start'],'0x82000000')
        self.assertTrue(r['reserved_memory_nodes'][0]['no_map'])
        self.assertEqual(r['dynamic_reserved_nodes_without_reg'],['/reserved-memory/dynamic'])
        self.assertEqual(r['kernel_config']['CONFIG_KEXEC'],'y')
        self.assertFalse(r['boot_contract_verified']);self.assertFalse(r['xnu_executed'])
        self.assertIsNone(r['safe_xnu_load_address_selected'])

    def test_disabled_kernel_config_is_observed_not_missing(self):
        capture(self.root)
        (self.root/'config.gz').write_bytes(gzip.compress(
            b'# CONFIG_KEXEC is not set\nCONFIG_ARM64_4K_PAGES=y\n'
            b'# CONFIG_ARM64_16K_PAGES is not set\n'))
        config = analysis.analyze(self.root)['kernel_config']
        self.assertEqual(config['CONFIG_KEXEC'], 'n')
        self.assertEqual(config['CONFIG_ARM64_16K_PAGES'], 'n')
        self.assertEqual(config['CONFIG_ARM64_4K_PAGES'], 'y')
        self.assertEqual(config['CONFIG_KEXEC_FILE'], 'not observed')
        (self.root/'config.gz').write_bytes(gzip.compress(
            b'CONFIG_KEXEC=y\n# CONFIG_KEXEC is not set\n'))
        with self.assertRaisesRegex(ValueError, 'Conflicting kernel config'):
            analysis.analyze(self.root)

    def test_tree_fallback_does_not_invent_memreserve(self):
        capture(self.root);(self.root/'live.dtb').unlink()
        with tarfile.open(self.root/'live-tree.tar','w') as archive:
            for node,props in synthetic_tree().items():
                for key,value in props.items():
                    member=tarfile.TarInfo('./'+node.strip('/')+'/'+key if node!='/' else './'+key)
                    member.size=len(value);archive.addfile(member,io.BytesIO(value))
        r=analysis.analyze(self.root)
        self.assertTrue(r['live_tree_observed']);self.assertFalse(r['fdt_memreserve_observable'])
        self.assertEqual(len(r['memory_nodes']),1)

    def test_incomplete_and_truncated_tree_refused(self):
        with self.assertRaises(ValueError):analysis.analyze(self.root)
        capture(self.root);(self.root/'live.dtb').write_bytes(make_fdt(synthetic_tree())[:-5])
        with self.assertRaises(ValueError):analysis.analyze(self.root)

    def test_unsafe_tar_refused(self):
        for name,kind in [('../escape',tarfile.REGTYPE),('link',tarfile.SYMTYPE)]:
            data=io.BytesIO()
            with tarfile.open(fileobj=data,mode='w') as archive:
                entry=tarfile.TarInfo(name);entry.type=kind;entry.linkname='/etc/passwd';archive.addfile(entry)
            with self.assertRaises(ValueError):analysis.tree_from_tar(data.getvalue())

    def test_redacted_iomem_not_hardware_evidence(self):
        capture(self.root);(self.root/'iomem.txt').write_text('00000000-00000000 : System RAM\n')
        self.assertFalse(analysis.analyze(self.root)['iomem_addresses_visible'])

    def test_preflight_refuses_unsafe_transports(self):
        for key,value in [(('devices',),'List of devices attached\nTEST unauthorized\n'),
                          (('devices',),'List of devices attached\nTEST sideload\n'),
                          (('devices',),'List of devices attached\nA recovery\nB recovery\n'),
                          (('shell','getprop','ro.twrp.version'),''),
                          (('shell','id','-u'),'2000'),(('shell','uname','-m'),'x86_64')]:
            adb=FakeAdb();adb.values[key]=value
            with self.assertRaises(RuntimeError):run_probe.preflight(adb)
            self.assertFalse(any(c[0] in ('push','pull') for c in adb.calls))
        adb=FakeAdb();adb.values[('shell','getprop','ro.product.model')]='SM-G975F'
        adb.values[('shell','getprop','ro.product.device')]='beyond2lte'
        with self.assertRaises(RuntimeError):run_probe.preflight(adb)

    def test_full_host_flow_with_simulated_transport(self):
        source=self.root/'source';capture(source);adb=FakeAdb(source)
        old_class,old_args=run_probe.Adb,sys.argv
        run_probe.Adb=lambda *args:adb
        sys.argv=['run_probe.py','--run','--out',str(self.root/'out')]
        try:run_probe.main()
        finally:run_probe.Adb,sys.argv=old_class,old_args
        result=list((self.root/'out').glob('*/analysis.json'))
        self.assertEqual(len(result),1)
        self.assertTrue(json.loads(result[0].read_text())['live_tree_observed'])
        self.assertEqual(adb.serial,'TEST')
        self.assertFalse(any(any(s in ('reboot','flash','mount','su','install') for s in c) for c in adb.calls))

    def test_zip_reproducible_and_executable(self):
        p=build_package.build();first=p.read_bytes();build_package.build();self.assertEqual(first,p.read_bytes())
        with zipfile.ZipFile(p) as archive:
            self.assertEqual(archive.testzip(),None)
            updater=archive.getinfo('META-INF/com/google/android/update-binary')
            self.assertTrue(updater.external_attr>>16 & 0o111)
            self.assertTrue(archive.read(updater).startswith(b'#!/sbin/sh\n'))
            manifest=json.loads(archive.read('probe-manifest.json'))
            self.assertFalse(manifest['xnu_executed']);self.assertFalse(manifest['partition_writes'])

    def test_shell_syntax(self):
        shell=shutil.which('bash') or r'C:/Program Files/Git/bin/bash.exe'
        subprocess.run([shell,'-n',str(HERE/'collect.sh')],check=True)
        p=build_package.build()
        with zipfile.ZipFile(p) as archive:code=archive.read('META-INF/com/google/android/update-binary')
        subprocess.run([shell,'-n'],input=code,check=True)

    def test_collector_in_translated_filesystem_fixture(self):
        # Execute real collector control flow with only /proc,/sys,/tmp input
        # paths translated into a private fixture. Identity/architecture are
        # synthetic; this is not a real TWRP or privileged-register test.
        fs=self.root/'fs';fs.mkdir()
        for directory in ('proc/self','sys/firmware','tmp','sys/devices/system/cpu/cpu0/cache/index0'):
            (fs/directory).mkdir(parents=True,exist_ok=True)
        texts={'proc/mounts':f'tmpfs {fs.as_posix()}/tmp tmpfs rw 0 0\n',
               'proc/iomem':'80000000-8fffffff : System RAM\n',
               'proc/meminfo':'MemTotal: 1024 kB\n',
               'proc/cpuinfo':'processor: 0\nSerial: TEST-IDENTIFIER\n',
               'proc/cmdline':'androidboot.serialno=TEST-IDENTIFIER console=ttySAC0\n',
               'proc/self/status':'Name: fixture\n',
               'sys/devices/system/cpu/cpu0/cache/index0/level':'1\n',
               'sys/devices/system/cpu/cpu0/cache/index0/coherency_line_size':'64\n'}
        for name,text in texts.items():(fs/name).write_text(text,newline='\n')
        (fs/'proc/config.gz').write_bytes(gzip.compress(b'CONFIG_KEXEC=y\n'))
        (fs/'sys/firmware/fdt').write_bytes(make_fdt(synthetic_tree()))
        code=(HERE/'collect.sh').read_text()
        code=re.sub(r'/(?:proc|sys|tmp)(?=/|["\s])',lambda match:fs.as_posix()+match[0],code)
        script=self.root/'translated-collect.sh';script.write_text(code,newline='\n')
        stub='''PATH=/usr/bin:/bin:$PATH
id() { printf '0\\n'; }
uname() { printf 'aarch64\\n'; }
dmesg() { printf 'synthetic recovery log\\n'; }
getprop() { case "$1" in ro.product.model) echo SM-N976N;; ro.product.device) echo d2x;; ro.twrp.version) echo fixture;; *) echo;; esac; }
. "$1" "$2"
'''
        shell=shutil.which('bash') or r'C:/Program Files/Git/bin/bash.exe'
        out=fs/'tmp/note10-probe/session-fixture'
        result=subprocess.run([shell,'-c',stub,'test',script.as_posix(),out.as_posix()],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertEqual((out/'COMPLETE').read_text().strip(),'NOTE10_PROBE_COMPLETE')
        self.assertNotIn('TEST-IDENTIFIER',(out/'cmdline.txt').read_text())
        self.assertNotIn('Serial',(out/'cpuinfo.txt').read_text())
        self.assertEqual((out/'cache/cpu0-index0-coherency_line_size.txt').read_text().strip(),'64')
        self.assertTrue(analysis.analyze(out)['live_tree_observed'])
        # Persistent /tmp and pre-existing sessions must be rejected, not reused.
        (fs/'proc/mounts').write_text(f'disk {fs.as_posix()}/tmp ext4 rw 0 0\n',newline='\n')
        rejected=fs/'tmp/note10-probe/session-rejected'
        result=subprocess.run([shell,'-c',stub,'test',script.as_posix(),rejected.as_posix()],capture_output=True)
        self.assertNotEqual(result.returncode,0);self.assertFalse(rejected.exists())


if __name__=='__main__':
    build_package.OUT.mkdir(parents=True,exist_ok=True)
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(ProbeTests)
    result=unittest.TextTestRunner(verbosity=1).run(suite)
    report={'tests_run':result.testsRun,'passed':result.wasSuccessful(),'real_device_tested':False,
            'scope':'PC package/negative preflight/host flow/synthetic DT analysis'}
    (build_package.OUT/'test-result.json').write_text(json.dumps(report,indent=2))
    raise SystemExit(0 if result.wasSuccessful() else 1)
