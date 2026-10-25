"""Execute updater control flow against private regular-file block fixtures.

No ADB/device access. Identity, block metadata and filesystem paths are modeled;
payload extraction, SHA-256 and dd copies execute against real fixture bytes.
"""
import hashlib
import json
import os
import re
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import zipfile
from build_boot_test_packages import updater,ROOT,build


class PackageTests(unittest.TestCase):
    def test_chain_to_verified_prior_diagnostic_and_reject_foreign_backup(self):
        parent=ROOT/'note10/private/device-test';parent.mkdir(exist_ok=True,parents=True)
        with tempfile.TemporaryDirectory(dir=parent) as name:
            fs=Path(name);backup=fs/'backup';backup.mkdir()
            parts={p:bytes([i])*512 for i,p in enumerate(('boot','recovery','dtb','dtbo','vbmeta'),1)}
            records=[{'partition':p,'block_node':f'/dev/block/sda{i}',
                      'size':512,'sha256':hashlib.sha256(raw).hexdigest()}
                     for i,(p,raw) in enumerate(parts.items(),14)]
            manifest=backup/'backup-manifest.json'
            manifest.write_text(json.dumps({'bootloader':'N976NKSU2HWH5','partitions':records}))
            prototype=fs/'fixture.img';prototype.write_bytes(b'fixture diagnostic bytes')
            metadata={'prototype_created':True,'kind':'temporary Linux diagnostic boot; not XNU/iOS',
                      'sha256':hashlib.sha256(prototype.read_bytes()).hexdigest(),'size':prototype.stat().st_size,
                      'backup_manifest_sha256':hashlib.sha256(manifest.read_bytes()).hexdigest(),
                      'original_boot_sha256':records[0]['sha256'],
                      'existing_recovery_partition_sha256':records[1]['sha256'],
                      'kernel_build_sha256':'a'*64}
            prototype.with_suffix('.json').write_text(json.dumps(metadata))
            with patch('build_boot_test_packages.read_verified_backup',return_value=parts):
                first=build(backup,prototype,fs/'first')
                second=build(backup,prototype,fs/'second',fs/'first')
                self.assertEqual(second['expected_current_boot_sha256'],first['packages'][0]['payload_sha256'])
                with zipfile.ZipFile(fs/'second/note10-phase2-diagnostic.zip') as archive:
                    script=archive.read('META-INF/com/google/android/update-binary').decode()
                    self.assertIn(first['packages'][0]['payload_sha256'],script)
                foreign=json.loads((fs/'first/package-result.json').read_text())
                foreign['backup_manifest_sha256']='f'*64
                (fs/'first/package-result.json').write_text(json.dumps(foreign))
                with self.assertRaisesRegex(ValueError,'different backup'):
                    build(backup,prototype,fs/'refused',fs/'first')
                self.assertFalse((fs/'refused').exists())

    def run_fixture(self, *, mode='diagnostic', device='d2x', damaged_boot=False,
                    damaged_recovery=False, corrupt_payload=False, persistent_tmp=False):
        parent=ROOT/'note10/private/device-test';parent.mkdir(exist_ok=True,parents=True)
        with tempfile.TemporaryDirectory(dir=parent) as name:
            fs=Path(name);self.assertTrue(fs.resolve().is_relative_to(parent.resolve()))
            for directory in ('tmp','proc/self/fd','dev/block'):(fs/directory).mkdir(parents=True,exist_ok=True)
            (fs/'proc/self/fd/3').write_text('')
            records=[];original=b'A'*512;payload=b'B'*512
            for index,part in enumerate(('boot','recovery','dtb','dtbo','vbmeta'),14):
                node='/dev/block/sda'+str(index)
                raw=original if part=='boot' else bytes([index])*512
                (fs/node.lstrip('/')).write_bytes(raw)
                records.append({'partition':part,'block_node':node,'size':512,'sha256':hashlib.sha256(raw).hexdigest()})
            if damaged_boot:(fs/'dev/block/sda14').write_bytes(b'X'*512)
            if damaged_recovery:(fs/'dev/block/sda15').write_bytes(b'X'*512)
            before=(fs/'dev/block/sda14').read_bytes()
            code=updater(mode=mode,bootloader='N976NKSU2HWH5',partitions=records,
                         payload_sha=hashlib.sha256(payload).hexdigest(),current_boot_sha=hashlib.sha256(original).hexdigest()).decode()
            # Translate all literal block, temporary and proc paths before
            # executing a real shell. Expected paths move with the fixture.
            code=re.sub(r'/(?:dev/block|proc|tmp)(?=/|["\s])',lambda m:fs.as_posix()+m[0],code)
            self.assertEqual(code.count('/dev/block'),code.count(fs.as_posix()+'/dev/block'))
            script=fs/'update.sh';script.write_text(code,encoding='utf-8',newline='\n')
            kind='ext4' if persistent_tmp else 'tmpfs'
            (fs/'proc/mounts').write_text(f'{kind} {fs.as_posix()}/tmp {kind} rw 0 0\n',newline='\n')
            package=fs/'test.zip'
            with zipfile.ZipFile(package,'w') as archive:archive.writestr('boot.img',b'bad' if corrupt_payload else payload)
            stub='''PATH=/usr/bin:/bin:$PATH
id() { echo 0; }
uname() { echo aarch64; }
getprop() { case "$1" in ro.product.device) echo "$TEST_DEVICE";; ro.twrp.version) echo fixture;; ro.bootloader) echo N976NKSU2HWH5;; esac; }
readlink() {
 case "$2" in
 */by-name/boot) echo "$TEST_FS/dev/block/sda14";;
 */by-name/recovery) echo "$TEST_FS/dev/block/sda15";;
 */by-name/dtb) echo "$TEST_FS/dev/block/sda16";;
 */by-name/dtbo) echo "$TEST_FS/dev/block/sda17";;
 */by-name/vbmeta) echo "$TEST_FS/dev/block/sda18";;
 *) return 1;; esac
}
blockdev() { wc -c < "$2" | awk '{print $1}'; }
unzip() { "$TEST_PYTHON" -c 'import zipfile,sys;sys.stdout.buffer.write(zipfile.ZipFile(sys.argv[1]).read(sys.argv[2]))' "$2" "$3"; }
. "$1" 3 3 "$2"
'''
            shell=shutil.which('bash') or r'C:/Program Files/Git/bin/bash.exe'
            environment=dict(os.environ,TEST_FS=fs.as_posix(),TEST_DEVICE=device,TEST_PYTHON=__import__('sys').executable)
            result=subprocess.run([shell,'-c',stub,'test',script.as_posix(),package.as_posix()],
                                  capture_output=True,text=True,env=environment,timeout=30)
            after=(fs/'dev/block/sda14').read_bytes()
            for item in records[1:]:self.assertEqual(hashlib.sha256((fs/item['block_node'].lstrip('/')).read_bytes()).hexdigest(),
                hashlib.sha256(b'X'*512).hexdigest() if damaged_recovery and item['partition']=='recovery' else item['sha256'])
            return result,before,after,payload

    def test_actual_boot_copy_and_only_boot_changed(self):
        result,before,after,payload=self.run_fixture()
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertNotEqual(before,after);self.assertEqual(after,payload)

    def test_guard_failures_leave_boot_unchanged(self):
        for changes in (dict(device='wrong'),dict(damaged_boot=True),dict(damaged_recovery=True),
                        dict(corrupt_payload=True),dict(persistent_tmp=True)):
            with self.subTest(changes=changes):
                result,before,after,_=self.run_fixture(**changes)
                self.assertNotEqual(result.returncode,0);self.assertEqual(before,after)

    def test_rollback_can_restore_partial_boot(self):
        result,before,after,payload=self.run_fixture(mode='rollback',damaged_boot=True)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertNotEqual(before,after);self.assertEqual(after,payload)

    def test_reject_unsafe_contract_input(self):
        with self.assertRaises(ValueError):updater(mode='wrong',bootloader='N976NTEST',partitions=[],payload_sha='0'*64,current_boot_sha='0'*64)


if __name__=='__main__':unittest.main()
