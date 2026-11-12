"""Bound named live requests; allocator residency and whole-system totals stay unknown."""
PAGE=4096
CONFIG_KEYS=('ARM64_4K_PAGES','SLUB','NR_CPUS','BASE_SMALL','FORCE_MAX_ZONEORDER','TRANSPARENT_HUGEPAGE','SLUB_DEBUG','SLUB_DEBUG_ON','MEMCG','TMPFS')
TYPE_KEYS=('file','inode','dentry','shmem_inode','radix_node','zstream','inflate_workspace','sha_state','kernel_context','cpio_dir')
UNKNOWN=('SLUB cache backing/debug/order/partial occupancy and memcg ancillary costs',
         'VFS/LSM/audit/path ancillary allocations beyond the named payload objects',
         'tmpfs swap/reclaim/replacement and concurrent kernel allocations',
         'future final linked Image/BSS/runtime call-stack delta',
         'unchanged global running kernel/driver/page-table/slab baseline')


def require(ok,message):
    if not ok:raise ValueError(message)


def integer(value,cap=(1<<63)-1):
    require(type(value)is int and 0<value<=cap,'bounded positive integer required')
    return value


def dense_nodes(pages):
    integer(pages,8192);nodes=0
    while pages>1:
        pages=(pages+63)//64;nodes+=pages
    return nodes


def nominal(size):
    integer(size,1<<20)
    for bucket in (8,16,32,64,96,128,192):
        if size<=bucket:return bucket
    return 1<<(size-1).bit_length()


def budget(source_bytes,config,target_sizes,stack_frames):
    require(type(source_bytes)is dict and set(source_bytes)=={'kernel.mem','adapter.mem'},'fixed two extents required')
    kernel=integer(source_bytes['kernel.mem'],33554432);adapter=integer(source_bytes['adapter.mem'],16384)
    require(kernel%16384==0 and adapter==16384,'accepted dense materialized geometry required')
    require(type(config)is dict and set(config)==set(CONFIG_KEYS),'exact configuration evidence required')
    for key,value in {'ARM64_4K_PAGES':'y','SLUB':'y','NR_CPUS':'8','BASE_SMALL':'0','FORCE_MAX_ZONEORDER':'11','TRANSPARENT_HUGEPAGE':'n','TMPFS':'y'}.items():
        require(config[key]==value,'unsupported geometry/configuration: '+key)
    require(all(config[k]in ('y','n')for k in ('SLUB_DEBUG','SLUB_DEBUG_ON','MEMCG')),'typed allocator policy required')
    require(type(target_sizes)is dict and set(target_sizes)==set(TYPE_KEYS),'all target sizes required')
    for value in target_sizes.values():integer(value,1048576)
    require(type(stack_frames)is dict and {'n219_sha256_transform','n219_sha256_init','n219_sha256_update','n219_sha256_final','n219_ingest_current'}<=set(stack_frames),'actual new static stack frames required')
    for value in stack_frames.values():require(type(value)is int and 0<=value<=1048576,'bounded nonnegative static frame required')
    pages=[(kernel+PAGE-1)//PAGE,(adapter+PAGE-1)//PAGE];data=sum(pages)*PAGE
    attached=sum(dense_nodes(n)for n in pages);preload=8*(2*((64+5)//6)-1)+1
    radix=(attached+preload)*target_sizes['radix_node']
    # Fixed member has one short-name directory, two regular nlink1files, no links.
    namespace={kind:3*(inode+target_sizes['dentry'])+2*target_sizes['file'] for kind,inode in
               [('ramfs',target_sizes['inode']),('tmpfs',target_sizes['shmem_inode'])]}
    raw_gunzip=[32768,target_sizes['zstream'],target_sizes['inflate_workspace']]
    raw_cpio=[110,8195,4098,target_sizes['cpio_dir'],4]
    unpack_raw=sum(raw_gunzip)+sum(raw_cpio)
    unpack_nominal=sum(map(nominal,raw_gunzip+raw_cpio))
    ingest_raw=PAGE+2*PAGE # one staging page + conservative two short-path name requests
    branches={}
    for kind,objects in namespace.items():
        persistent=data+radix+objects
        branches[kind]=dict(named_persistent_payload_bytes=persistent,named_unpack_live_request_bytes=persistent+unpack_raw,
            named_ingest_live_request_bytes=persistent+ingest_raw,
            named_phase_request_peak_bytes=persistent+max(unpack_raw,ingest_raw))
    return dict(schema='note10-v219-native-source-request-budget-v1',source_file_pages=sum(pages),source_data_bytes=data,
        attached_radix_node_ceiling=attached,preload_plus_inflight_node_ceiling=preload,
        radix_live_payload_request_ceiling=radix,namespace_payload_requests=namespace,branches=branches,
        gunzip_raw_request_bytes=sum(raw_gunzip),gunzip_nominal_bucket_request_bytes=sum(map(nominal,raw_gunzip)),
        workspace_includes_window=True,cpio_named_raw_request_bytes=sum(raw_cpio),
        unpack_nominal_bucket_requests_bytes=unpack_nominal,hardlink_hash_requests=0,
        direct_hash_provider_heap_requests=0,direct_hash_tfm_heap_requests=0,direct_hash_descriptor_heap_requests=0,
        hash_state_target_bytes=target_sizes['sha_state'],context_target_bytes=target_sizes['kernel_context'],
        own_target_static_stack_frames=dict(stack_frames),stack_frames_are_not_total_kernel_stack_bound=True,
        single_allocator_block_ceiling=PAGE*(1<<(11-1)),single_block_is_not_aggregate_resident_bound=True,
        compressed_member_added_again_bytes=0,initmem_credit_bytes=0,
        phase_relation='persistent+max(unpack,ingest); freed transient phases are not added',
        preconditions=['fixed dense two-source nlink1member, one directory, short names','64bit/4KiB/64slot radix and8CPU configuration',
            'logical live requests only; no claim of swap-free residency or bounded allocation retry count'],
        unknown_rows=list(UNKNOWN),resident_upper_bound_bytes=None,whole_system_upper_bound_bytes=None,
        complete_numeric_peak=False,physical_scope_reviewable=False,device_authorized=False,
        global_destination_no_replay_proven=False,runtime_callers=0)
