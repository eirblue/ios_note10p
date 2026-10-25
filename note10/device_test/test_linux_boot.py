from pathlib import Path
import json
import tempfile
import unittest
from prepare_linux_boot import payload_size,read_verified_backup


class LinuxBootTests(unittest.TestCase):
    def test_alignment_and_exact_limit(self):
        self.assertEqual(payload_size(2049,1,2048,8192),8192)
        with self.assertRaises(ValueError):payload_size(2049,1,2048,8191)
        self.assertEqual(payload_size(2049,0,2048,8192,allow_empty_ramdisk=True),6144)
        with self.assertRaises(ValueError):payload_size(2049,0,2048,8192)

    def test_invalid_sizes(self):
        for values in ((0,1,2048,8192),(1,0,2048,8192),(1,1,3,8192),(-1,1,2048,8192),(True,1,2048,8192)):
            with self.assertRaises(ValueError):payload_size(*values)

    def test_unverified_and_unsafe_backup(self):
        root=Path(__file__).resolve().parents[1]/'private/device-test';root.mkdir(exist_ok=True,parents=True)
        with tempfile.TemporaryDirectory(dir=root) as name:
            path=Path(name);self.assertTrue(path.resolve().is_relative_to(root.resolve()))
            for manifest in ({'complete':False},
                {'complete':True,'partition_writes':False,'partitions':[{'partition':'efs','file':'efs.img'}]},
                {'complete':True,'partition_writes':False,'partitions':[{'partition':'boot','file':'../boot.img'}]},
                {'complete':True,'partition_writes':False,'partitions':[]}):
                (path/'backup-manifest.json').write_text(json.dumps(manifest))
                with self.assertRaises(ValueError):read_verified_backup(path)


if __name__=='__main__':unittest.main()
