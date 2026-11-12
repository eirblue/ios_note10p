"""Scoped native-path costs; unknown resident costs never become zero or authority."""
PAGE=4096
SIZE_NAMES=('request','result','state','kernel_context','file','inode','dentry','shmem_inode','radix_node','zstream','inflate_workspace','shash_desc')


def require(ok,message):
    if not ok:raise ValueError(message)


def positive(value,cap=(1<<63)-1):
    require(type(value)is int and 0<value<=cap,'bounded positive integer bytes required')
    return value


def account(spec,target_sizes):
    require(type(spec)is dict and set(spec)=={'source_bytes','reference_linked_bytes','reservation_bytes','initramfs_bytes','deferred_initcalls','rootfs_kind'},'fixed scoped accounting inputs required')
    source=spec['source_bytes'];require(type(source)is dict and set(source)=={'kernel.mem','adapter.mem'},'two fixed source extents required')
    kernel=positive(source['kernel.mem'],33554432);adapter=positive(source['adapter.mem'],16384)
    require(adapter==16384 and kernel%16384==0,'accepted materialized page geometry required')
    reference=positive(spec['reference_linked_bytes'],59768832);positive(spec['initramfs_bytes'],6291456+65536)
    require(type(spec['reservation_bytes'])is int and spec['reservation_bytes']==33554432 and type(spec['deferred_initcalls'])is bool and
            spec['rootfs_kind']in ('unknown','ramfs','tmpfs'),'actual reservation/lifetime metadata required')
    require(type(target_sizes)is dict and set(target_sizes)<=set(SIZE_NAMES),'fixed target type-size fields required')
    for value in target_sizes.values():positive(value,1048576)
    pages=(kernel+PAGE-1)//PAGE+(adapter+PAGE-1)//PAGE;data=pages*PAGE
    rows=[dict(name='source_pagecache_data',bytes=data,classification='exact_data_pages',lifetime='unpack through reboot when held'),
          dict(name='destination_reservation',bytes=33554432,classification='existing_reserved_capacity',lifetime='early boot through reboot'),
          dict(name='ingest_staging',bytes=4096,classification='exact_page_request',lifetime='ingestion only'),
          dict(name='shash_descriptor',bytes=None,request_upper_bytes=4096,classification='bounded_request_not_resident_total',lifetime='ingestion only'),
          dict(name='file_inode_dentry_radix_shmem_resident',bytes=None,classification='not_yet_bounded',lifetime='persistent source ownership'),
          dict(name='crypto_tfm_provider_resident',bytes=None,classification='not_yet_bounded',lifetime='ingestion/provider lifetime'),
          dict(name='cpio_scratch_link_directory_allocator_resident',bytes=None,classification='not_yet_bounded',lifetime='unpack only'),
          dict(name='gunzip_allocator_rounding',bytes=None,classification='not_yet_bounded',lifetime='unpack only'),
          dict(name='future_final_linked_delta',bytes=None,classification='not_yet_bounded',lifetime='new integrated Image, not built in217')]
    missing=sorted(set(SIZE_NAMES)-set(target_sizes))
    gunzip=None
    if not missing:gunzip=32768+target_sizes['zstream']+target_sizes['inflate_workspace']
    return dict(schema='note10-v217-native-path-accounting-v1',source_file_pages=pages,source_data_bytes=data,
                source_plus_destination_data_bytes=data+33554432,reference_linked_bytes=reference,
                reference_linked_reserved_source_lower_bound=reference+33554432+data,
                compressed_member_added_again_bytes=0,embedded_initramfs_bytes=spec['initramfs_bytes'],
                initmem_credit_bytes=0,deferred_initcalls=spec['deferred_initcalls'],
                gunzip_requested_bytes=gunzip,workspace_includes_window=True,target_type_bytes=dict(target_sizes),missing_target_sizes=missing,
                native_increment_rows=rows,unpack_and_ingest_relation='maximum of phase peaks, not sum of freed transient requests',
                unchanged_global_runtime_baseline=dict(bytes=None,classification='separate_unknown_not_scoped_increment',
                    reason='kernel stacks/drivers/page tables/slab baseline and future actual rootfs/swap state not measured'),
                complete_numeric_peak=False,upper_bound_bytes=None,physical_scope_reviewable=False,device_authorized=False)
