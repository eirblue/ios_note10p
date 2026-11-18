"""Only new probe-state, source-seam and rootfs-fact cases; synthetic inputs."""
import v297_rootfs_prepare as producer


def predicate(fixture_result):
    assert fixture_result == dict(passed=True, groups=1, variants=3, assertions=12)
    raw=(b'static int __init do_name(void)\n'+producer.OPEN+b'\n'
         +b'static int __init populate_rootfs(void)\n'+producer.UNPACK)
    changed=producer.rootfs_overlay(raw)
    assert changed.count(producer.UNPACK)==1 and changed.count(b'n297_before_unpack();')==changed.count(b'n297_after_unpack(err ? -EINVAL : 0);')==1
    main=producer.MAIN_DECL+b'\n'+producer.MAIN_CALL+b'\n\targv_init[1] = NULL;'
    late=producer.main_overlay(main)
    assert late.index(producer.MAIN_CALL)<late.index(b'n297_rootfs_final_probe();')<late.index(b'argv_init[1]')
    def refused(call):
        try:call()
        except ValueError:return
        raise AssertionError('invalid new rootfs input admitted')
    refused(lambda:producer.rootfs_overlay(changed))
    refused(lambda:producer.main_overlay(late))

    identity='1'*32;expected=dict(span=10962166,magic=0,fnv=0x12345678)
    defaults=dict(flags=12,declared=10962166,hash_declared=10962166,span=10962166,magic=0,fnv=0x12345678,
                  hash_stage=3,skip=0,unpack=-115,open_seen=0,open_rc=-115,init_rc=-2,mode=0,ino=0,size=-1,
                  console_rc=-2,root_rc=0,root_magic=0x858458f6,root_ino=1)
    def record(stage,**edits):
        values=dict(defaults,**edits)
        body=' '.join(key+'='+ (f'{value:08x}' if key in ('magic','fnv') else str(value)) for key,value in values.items())
        return 'N297RFS id='+identity+' stage='+stage+' '+body+'\n'
    result=producer.rootfs_facts(record('late'),identity,expected)
    assert result['frontier']=='BUILTIN_UNPACK_HOOKS_NOT_OBSERVED' and result['userspace_success_proven'] is False
    failed=(record('pre',flags=9,hash_stage=1)+record('post',flags=11,hash_stage=1,unpack=0,open_seen=1,open_rc=-13)
            +record('late',flags=15,hash_stage=1,unpack=0,open_seen=1,open_rc=-13))
    assert producer.rootfs_facts(failed,identity,expected)['frontier']=='INIT_CREATE_FAILED'
    refused(lambda:producer.rootfs_facts(record('late',flags=8),identity,expected))
    mismatch=failed.replace('fnv=12345678','fnv=12345679')
    assert producer.rootfs_facts(mismatch,identity,expected)['frontier']=='RUNTIME_BLOB_OR_SIZE_MISMATCH'
    present=(record('pre',flags=9,hash_stage=1)+record('post',flags=11,hash_stage=1,unpack=0,open_seen=1,open_rc=0,init_rc=0,mode=0o100750,ino=7,size=2146400)
             +record('late',flags=15,hash_stage=1,unpack=0,open_seen=1,open_rc=0,init_rc=0,mode=0o100750,ino=7,size=2146400))
    result=producer.rootfs_facts(present,identity,expected)
    assert result['frontier']=='INIT_PRESENT_AT_LATE_ROUTE' and result['userspace_success_proven'] is False
    return dict(passed=True,groups=3,variants=12,assertions=21)
