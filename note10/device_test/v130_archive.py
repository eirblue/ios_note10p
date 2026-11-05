"""Pinned source-only Linux archive acquisition/extraction for the new build."""
from pathlib import Path
import shutil
import tarfile
import urllib.request
COMMIT='55f042627bb7030c93550faafa117674d32b21d1'
ARCHIVE_SHA='46d6a563af04e0c2ed9c96c2a1af8cab2344b458c9554b09098e6a9e7219ae4c'
DEFCONFIG='exynos9820-d2x_defconfig'
def acquire(path):
    url='https://codeload.github.com/corsicanu/android_kernel_samsung_universal9820/tar.gz/'+COMMIT
    with urllib.request.urlopen(url,timeout=120) as response,path.open('xb') as stream:
        total=0
        while block:=response.read(1024*1024):
            total+=len(block)
            if total>1500*1024*1024:raise ValueError('kernel input exceeds bound')
            stream.write(block)


def extract(archive,destination):
    prefix='android_kernel_samsung_universal9820-'+COMMIT+'/'
    destination.mkdir()
    with tarfile.open(archive,'r:gz') as tar:
        for item in tar.getmembers():
            if not item.name.startswith(prefix) or not item.name[len(prefix):]:continue
            relative=Path(item.name[len(prefix):]);path=destination/relative
            if not path.resolve().is_relative_to(destination.resolve()) or relative.is_absolute():
                raise ValueError('unsafe kernel source member')
            if item.isdir():path.mkdir(parents=True,exist_ok=True)
            elif item.isfile():
                path.parent.mkdir(parents=True,exist_ok=True)
                with tar.extractfile(item) as src,path.open('xb') as dst:shutil.copyfileobj(src,dst)
                path.chmod(item.mode & 0o777)
            elif item.issym():
                target=path.parent/item.linkname
                if not target.resolve().is_relative_to(destination.resolve()):raise ValueError('unsafe source symlink')
                path.parent.mkdir(parents=True,exist_ok=True);path.symlink_to(item.linkname)
            else:raise ValueError('unsupported source archive type')
    return destination

