"""Boot backup guards: bounded inputs, stable contents and failed transfers."""
import hashlib
from pathlib import Path
import tempfile
import unittest
import backup_boot
from test_probe import FakeAdb


class BackupAdb(FakeAdb):
    def __init__(self):
        super().__init__()
        self.values[('shell','getprop','ro.bootloader')] = 'N976NKSU2HWH5'
        self.payloads = {}
        for index, name in enumerate(backup_boot.PARTITIONS, 12):
            node = '/dev/block/sda' + str(index)
            data = bytes([index]) * 512
            self.payloads[node] = data
            self.values[('shell','readlink','-f','/dev/block/by-name/'+name)] = node
            self.values[('shell','blockdev','--getsize64',node)] = '512'
            self.values[('shell','sha256sum',node)] = hashlib.sha256(data).hexdigest() + '  ' + node


def transfer(adb, node, target, size): target.write_bytes(adb.payloads[node])


class BackupTests(unittest.TestCase):
    def run_backup(self, adb=None, copy=transfer):
        # Test cleanup is constrained to this task's ignored private directory.
        root = backup_boot.ROOT / 'note10/private/device-test'
        root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=root) as name:
            path = Path(name)
            self.assertTrue(path.resolve().is_relative_to(root.resolve()))
            return backup_boot.backup(adb or BackupAdb(), path/'capture', copy)

    def test_verified_read_only_allowlist(self):
        adb = BackupAdb(); report = self.run_backup(adb)
        self.assertTrue(report['complete']); self.assertFalse(report['restore_tested'])
        self.assertEqual([p['partition'] for p in report['partitions']], list(backup_boot.PARTITIONS))
        self.assertTrue(all(call[0] in ('devices','shell') for call in adb.calls))
        self.assertTrue(all(call[1] in ('getprop','id','uname','readlink','blockdev','sha256sum') for call in adb.calls if call[0]=='shell'))

    def test_forbidden_partition(self):
        for name in ('efs','userdata','boot;reboot','../boot'):
            with self.assertRaises(ValueError): backup_boot.remote_info(BackupAdb(),name)

    def test_wrong_model_and_oversize(self):
        for key, value in ((('shell','getprop','ro.bootloader'),'N975FTEST'),
                           (('shell','blockdev','--getsize64','/dev/block/sda12'),str(1<<40)),
                           (('shell','readlink','-f','/dev/block/by-name/boot'),'/dev/block/../efs')):
            adb = BackupAdb(); adb.values[key] = value
            with self.assertRaises(ValueError): self.run_backup(adb)

    def test_corrupt_or_short_transfer(self):
        for raw in (b'bad', b'x'*512):
            with self.assertRaises(ValueError):
                self.run_backup(copy=lambda a,n,p,s:p.write_bytes(raw))

    def test_changed_remote_hash(self):
        def changed(adb,node,target,size):
            transfer(adb,node,target,size)
            adb.values[('shell','sha256sum',node)] = '0'*64
        with self.assertRaises(ValueError): self.run_backup(copy=changed)

    def test_duplicate_block_nodes(self):
        adb = BackupAdb()
        adb.values[('shell','readlink','-f','/dev/block/by-name/recovery')] = '/dev/block/sda12'
        with self.assertRaisesRegex(ValueError, 'Duplicate'): self.run_backup(adb)

    def test_malformed_remote_checksum(self):
        adb = BackupAdb(); adb.values[('shell','sha256sum','/dev/block/sda12')] = 'not a hash'
        with self.assertRaisesRegex(ValueError, 'checksum'): self.run_backup(adb)


if __name__ == '__main__': unittest.main()
