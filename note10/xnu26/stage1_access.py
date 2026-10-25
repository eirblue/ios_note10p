"""Conservative software EL1 access checks for the reviewed 16K/40bit setup.

This is not a complete Arm MMU. Only canonical untagged addresses, disabled
hardware AF/dirty updates and enabled hierarchical permissions are supported.
Stage 2, memory types/cache effects, alignment faults and newer extensions are
outside this model. PAN is an explicit synthetic input, not a device reading.
"""

PAGE=0x4000
ADDRESS_MASK=0x0000ffffffffc000


def word(value):
    if type(value) is not int or not 0<=value<1<<64:raise ValueError('Expected 64bit unsigned word')
    return value


def translation(read64,state,address,high,access,pan=False):
    address=word(address)
    if access not in ('fetch','read','write') or type(high) is not bool or type(pan) is not bool:
        raise ValueError('Invalid EL1 access contract')
    tcr=word(state['tcr_el1']);sctlr=word(state['sctlr_el1'])
    if not sctlr&1:raise ValueError('Logical stage-1 MMU must be enabled')
    if ((tcr>>32)&7)!=2 or (tcr&63)!=17 or ((tcr>>16)&63)!=17:
        raise ValueError('Only reviewed 47bit VA / 40bit PA setup supported')
    if ((tcr>>14)&3)!=2 or ((tcr>>30)&3)!=1:
        raise ValueError('Only 16K bootstrap granules supported')
    if tcr&((15<<39)|(1<<59)) or sctlr&(1<<57):
        raise ValueError('Unsupported AF/dirty/hierarchy/LPA2/EPAN configuration')
    if sctlr&(1<<25):raise ValueError('Unsupported big-endian table walk')
    # TBI can be configured, but this deliberately supports only untagged
    # canonical addresses. It does not silently strip a pointer tag.
    if high:
        if address<(1<<64)-(1<<47):raise ValueError('Noncanonical high virtual address')
    elif address>=1<<47:raise ValueError('Noncanonical low virtual address')
    if tcr&(1<<(23 if high else 7)):raise ValueError('Translation walk disabled')
    table=word(state['ttbr1_el1' if high else 'ttbr0_el1'])&ADDRESS_MASK
    readonly=False;pxn=False;user_disabled=False;path=[]
    for level in range(1,4):
        if table>=1<<40:raise ValueError('Table address exceeds PA width')
        shift=14+(3-level)*11
        slot=(address>>shift)&2047
        location=table+slot*8
        descriptor=word(read64(location));kind=descriptor&3
        path.append({'level':level,'address':location,'descriptor':descriptor})
        if (kind==1 and level in (1,2)) or (kind==3 and level==3):
            output=descriptor&ADDRESS_MASK
            if output>=1<<40 or output&((1<<shift)-1):
                raise ValueError('Invalid block/page physical alignment or width')
            physical=output+(address&((1<<shift)-1))
            if physical>=1<<40:raise ValueError('Output exceeds PA width')
            if not descriptor&(1<<10):raise ValueError('Access flag not set')
            ap=(descriptor>>6)&3
            readonly=readonly or bool(ap&2)
            pxn=pxn or bool(descriptor&(1<<53))
            user_accessible=bool(ap&1) and not user_disabled
            user_writable=user_accessible and not readonly
            if access=='write' and readonly:raise ValueError('EL1 write to read-only mapping')
            if access=='fetch' and (pxn or user_writable or (sctlr&(1<<19) and not readonly)):
                raise ValueError('EL1 execute permission denied')
            if access in ('read','write') and pan and user_accessible:
                raise ValueError('EL1 PAN data access denied')
            return {'physical_address':physical,'readonly':readonly,'pxn':pxn,
                    'el0_accessible':user_accessible,'el0_writable':user_writable,'path':path}
        if kind!=3 or level==3:raise ValueError('Invalid stage-1 descriptor')
        readonly=readonly or bool(descriptor&(1<<62))
        pxn=pxn or bool(descriptor&(1<<59))
        user_disabled=user_disabled or bool(descriptor&(1<<61))
        table=descriptor&ADDRESS_MASK
    raise ValueError('No terminal descriptor')


def check_access(read64,state,address,size,high,access,pan=False):
    word(address)
    if type(size) is not int or not 0<size<=PAGE or address+size>1<<64:
        raise ValueError('Invalid bounded access size')
    first=None;chunks=[];offset=0
    while offset<size:
        current=address+offset
        item=translation(read64,state,current,high,access,pan)
        count=min(size-offset,PAGE-(current&(PAGE-1)))
        physical=item['physical_address']
        if first is None:first=physical
        if physical!=first+offset:raise ValueError('Noncontiguous access unsupported in this model')
        chunks.append({'virtual_address':current,'size':count,**item})
        offset+=count
    return {'physical_address':first,'access':access,'chunks':chunks}
