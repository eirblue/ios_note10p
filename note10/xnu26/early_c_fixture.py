"""Explicit synthetic PE clock fixture; no GIC ownership/handoff claims."""
import struct
from boot_adt import Node


def clock_tree(frequency=26000000,cpu_id=None,dram=None,seed=None):
    if type(frequency) is not int or not 0<frequency<1<<32:raise ValueError('Invalid fixture frequency')
    cpu={'device_type':b'cpu\0','state':b'running\0','timebase-frequency':struct.pack('<I',frequency)}
    if cpu_id is not None:
        if type(cpu_id) is not int or not 0<=cpu_id<1<<32:raise ValueError('Invalid explicit fixture CPU ID')
        cpu['reg']=struct.pack('<I',cpu_id)
    chosen={'boot-args':b'debug=0x14e\0'}
    if seed is not None:
        if type(seed) is not bytes or not 0<len(seed)<=4096:raise ValueError('Invalid explicit PC seed fixture')
        chosen['random-seed']=seed
    if dram is not None:
        base,size=dram
        if any(type(v) is not int for v in (base,size)) or base<0 or size<=0 or base+size>1<<40:
            raise ValueError('Invalid explicit DRAM fixture')
        chosen.update({'dram-base':struct.pack('<Q',base),'dram-size':struct.pack('<Q',size)})
    return Node('device-tree',children=[
        Node('chosen',chosen),
        Node('arm-io',{'device_type':b'synthetic-soc\0',
                       'ranges':struct.pack('<3Q',0,0x10000000,0x10000000)}),
        Node('cpus',children=[Node('cpu0',cpu)])])


def single_cpu_plan(directory):
    """Fixed synthetic 1GiB placement, independently constructible by each CI job."""
    from handoff_bundle import PAGE,BLOCK,materialize_kernel
    from verify_experimental_artifact import verify
    checked=verify(directory)
    base,kernel=materialize_kernel((directory/'note10-experimental.macho').read_bytes(),checked['segments'])
    ram=0x80000000;virtual=0xfffffff000000000;image=ram+base-virtual;args=(image&~(BLOCK-1))+PAGE
    return {'schema':1,'purpose':'synthetic-pc-model','physical_reservation_verified':False,
            'ram':{'start':ram,'size':0x40000000},'virtual_base':virtual,'reserved':[],'occupied':[],
            'arguments_address':args,'device_tree_address':args+PAGE,'adapter_address':args+2*PAGE,
            'top_of_kernel':image+len(kernel),'command_line':'debug=0x14e'}
