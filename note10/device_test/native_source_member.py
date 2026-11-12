"""One bounded member from two already-materialized native source streams."""
import gzip
import hashlib
from v130_payload import Newc

SLOT_BYTES=4718592
METADATA_BYTES=4096
MEMBER_BUDGET=SLOT_BYTES-METADATA_BYTES
SOURCE_CAP=33554432
OUTPUT_CAP=33554432
CHUNK=1048576
ROLES=('kernel.mem','adapter.mem')


def require(ok,message):
    if not ok:raise ValueError(message)


def fit(member_bytes):
    require(type(member_bytes)is int and member_bytes>0,'completed positive member extent required')
    used=member_bytes+(-member_bytes%4)+METADATA_BYTES
    return dict(fit=used<=SLOT_BYTES,member_bytes=member_bytes,metadata_budget_bytes=METADATA_BYTES,
                slot_bytes=SLOT_BYTES,aligned_required_bytes=used,excess_bytes=max(0,used-SLOT_BYTES))


def validate_sources(sources):
    require(type(sources)is dict and tuple(sources)==ROLES,'exact ordered materialized source roles required')
    for role,row in sources.items():
        require(type(row)is dict and set(row)=={'stream','bytes','sha256'} and callable(getattr(row['stream'],'read',None)),
                'fixed readable source record required')
        size=row['bytes'];digest=row['sha256']
        require(type(size)is int and (0<size<=SOURCE_CAP if role=='kernel.mem' else size==16384),
                'bounded materialized source extent required')
        require(type(digest)is str and len(digest)==64 and all(c in '0123456789abcdef' for c in digest),
                'exact source SHA256 required')


class HashingOutput:
    def __init__(self,stream):self.stream=stream;self.hash=hashlib.sha256();self.bytes=0
    def write(self,raw):
        require(self.bytes+len(raw)<=OUTPUT_CAP,'completed member output exceeds32MiB cap')
        written=self.stream.write(raw)
        if type(written)is int and 0<=written<=len(raw):
            self.hash.update(raw[:written]);self.bytes+=written
        require(written==len(raw),'short member output write')
        return written
    def flush(self):self.stream.flush()


def produce(sources,output,progress):
    validate_sources(sources)
    require(type(progress)is dict and not progress,'fresh production accounting required')
    progress.update(compressions=0,completed=False,member_hash_complete=False,inputs={})
    sink=HashingOutput(output)
    progress['compressions']=1
    try:
        with gzip.GzipFile(filename='',mode='wb',fileobj=sink,compresslevel=9,mtime=0) as compressed:
            writer=Newc(compressed);writer.header('n10',0,0o040700)
            for role,row in sources.items():
                actual=dict(passes=1,bytes=0,hash_complete=False,EOF_verified=False)
                progress['inputs'][role]=actual;digest=hashlib.sha256()
                writer.header('n10/'+role,row['bytes'])
                remaining=row['bytes']
                while remaining:
                    block=row['stream'].read(min(CHUNK,remaining))
                    require(type(block)is bytes and 0<len(block)<=min(CHUNK,remaining),'source truncated or invalid read')
                    digest.update(block);writer.write(block);remaining-=len(block);actual['bytes']+=len(block)
                require(row['stream'].read(1)==b'','source exceeds accepted extent')
                actual.update(EOF_verified=True,sha256=digest.hexdigest(),hash_complete=True)
                require(actual['sha256']==row['sha256'],'materialized source hash differs')
                writer.pad(4)
            writer.finish();progress['uncompressed_newc_bytes']=writer.bytes
        sink.flush()
        progress.update(completed=True,member_hash_complete=True,member_sha256=sink.hash.hexdigest(),**fit(sink.bytes))
        return progress
    finally:
        progress['output_bytes_written']=sink.bytes
