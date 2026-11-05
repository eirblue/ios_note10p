"""Local-only private input producer: one payload input/hash/compression stream."""
import argparse
import gzip
import hashlib
from pathlib import Path
import struct
import traceback
from v130_contract import ROOT,PAGE,SPAN,ENTRY,POOL,POOL_BYTES,SLOT,PAYLOAD_SCHEMA,inputs,private,save,digest


class Output:
    def __init__(self,path):self.stream=path.open('xb');self.hash=hashlib.sha256();self.bytes=0
    def write(self,raw):
        self.bytes+=len(raw)
        if self.bytes>SLOT:raise ValueError('private compressed payload exceeds generic8MiB slot')
        self.hash.update(raw);return self.stream.write(raw)
    def flush(self):self.stream.flush()
    def close(self):self.stream.close()


class Newc:
    def __init__(self,stream):self.stream=stream;self.bytes=0;self.index=0
    def write(self,raw):self.stream.write(raw);self.bytes+=len(raw)
    def pad(self,bound):self.write(bytes(-self.bytes%bound))
    def header(self,name,size,mode=0o100400):
        self.index+=1;encoded=name.encode('ascii')+b'\0'
        fields=(self.index,mode,0,0,1,0,size,0,0,0,0,len(encoded),0)
        self.write(b'070701'+''.join(f'{x:08x}' for x in fields).encode()+encoded);self.pad(4)
    def file(self,name,raw):self.header(name,len(raw));self.write(raw);self.pad(4)
    def finish(self):self.header('TRAILER!!!',0,0);self.pad(512)


def adapter_memory(raw):
    if raw[:7]!=b'\x7fELF\x02\x01\x01' or len(raw)<64:raise ValueError('retained ELF64 adapter required')
    h=struct.unpack_from('<16sHHIQQQIHHHHHH',raw)
    _,kind,machine,version,entry,phoff,_,_,ehsize,phsize,phnum,*_=h
    if (kind,machine,version,ehsize,phsize)!=(2,183,1,64,56) or not 0<phnum<=16 or phoff+phnum*phsize>len(raw):raise ValueError('closed adapter ELF ABI required')
    memory=bytearray(PAGE);ranges=[];executable=[]
    for i in range(phnum):
        typ,flags,offset,va,pa,size,extent,_=struct.unpack_from('<II6Q',raw,phoff+i*phsize)
        if typ in (2,3):raise ValueError('dynamic adapter forbidden')
        if typ!=1:continue
        if (flags not in (4,5,6) or va!=pa or not 0<extent<=PAGE or size>extent or va+extent>PAGE or offset+size>len(raw) or
            any(va<end and start<va+extent for start,end in ranges)):raise ValueError('adapter PT_LOAD ownership differs')
        ranges.append((va,va+extent));memory[va:va+size]=raw[offset:offset+size]
        if flags&1:executable.append((va,va+size))
    template=struct.pack('<8sII6Q',b'N10XFER1',1,64,0,0,0,0,0,0);record=memory.find(template)
    if entry!=0 or record<0 or record%64 or memory.find(template,record+1)>=0 or not any(a<=entry<b for a,b in executable):raise ValueError('unique writable adapter record/executable entry required')
    if not any(a<=record and record+64<=b for a,b in ranges):raise ValueError('adapter record not loaded')
    return bytes(memory),entry,record


def produce(contract,expected,output):
    source=inputs(contract,expected);output=private(output)
    if output.exists():raise ValueError('fresh private one-use compression output required')
    output.mkdir();result=dict(schema=PAYLOAD_SCHEMA,passed=False,kernel_input_reads=0,adapter_input_reads=0,compressions=0,
        MachO_reads=0,old_decoder_calls=0,old_materializations=0,public_CI_upload_allowed=False,device_operations=[])
    save(output/'attempt.json',dict(schema=PAYLOAD_SCHEMA,status='reserved-before-private-input',input_contract_sha256=expected))
    sink=None
    try:
        adapter_path,adapter_row=source['adapter_elf'];raw=adapter_path.read_bytes();result['adapter_input_reads']=1
        if digest(raw)!=adapter_row['sha256']:raise ValueError('adapter pin differs')
        adapter,adapter_entry,record=adapter_memory(raw)
        sink=Output(output/'private-payload.cpio.gz');result['compressions']=1
        with gzip.GzipFile(filename='',mode='wb',fileobj=sink,compresslevel=9,mtime=0) as compressed:
            writer=Newc(compressed);writer.header('n10',0,0o040700)
            path,item=source['kernel_mem'];writer.header('n10/kernel.mem',item['bytes']);hashed=hashlib.sha256();count=0
            with path.open('rb') as stream:
                result['kernel_input_reads']=1
                while block:=stream.read(1024*1024):
                    count+=len(block)
                    if count>SPAN:raise ValueError('raw kernel grew beyond accepted span')
                    hashed.update(block);writer.write(block)
            if count!=SPAN or hashed.hexdigest()!=item['sha256']:raise ValueError('raw kernel span/hash differs')
            writer.pad(4);writer.file('n10/adapter.raw',adapter)
            # Fixed native binary, no private digest appears in public CI input.
            parcel=struct.pack('<8sII6Q32s32s',b'N10PAYL1',1,128,SPAN,ENTRY,POOL,POOL_BYTES,adapter_entry,record,
                               hashed.digest(),hashlib.sha256(adapter).digest())
            if len(parcel)!=128:raise ValueError('private payload contract ABI differs')
            writer.file('n10/payload.contract',parcel);writer.finish();unpacked=writer.bytes
        sink.flush();result.update(passed=True,compressed_file='private-payload.cpio.gz',compressed_bytes=sink.bytes,
            compressed_sha256=sink.hash.hexdigest(),uncompressed_newc_bytes=unpacked,kernel_sha256=hashed.hexdigest(),
            adapter_ELF_sha256=adapter_row['sha256'],adapter_memory_sha256=digest(adapter),adapter_entry_offset=adapter_entry,
            adapter_record_offset=record,kernel_span=SPAN,kernel_entry_offset=ENTRY,metadata_append_remaining_bytes=SLOT-sink.bytes,
            source_metadata_sha256={k:v[1]['sha256'] for k,v in source.items() if k not in ('kernel_mem','adapter_elf')},
            physical_ready=False,XNU_execution_allowed=False)
    except Exception:result['error']=traceback.format_exc()
    finally:
        if sink:sink.close()
    save(output/'result.json',result)
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--inputs-contract',required=True,type=Path)
    p.add_argument('--inputs-sha256',required=True);p.add_argument('--output',required=True,type=Path);a=p.parse_args()
    r=produce(a.inputs_contract,a.inputs_sha256,a.output);print({'passed':r['passed']});raise SystemExit(0 if r['passed'] else 1)
