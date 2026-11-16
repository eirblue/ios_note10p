"""One metadata-only regression of the production inventory gate."""
import v283_native_prepare as p

def refused(entries,passed=True):
    try:p.inventory_metadata(entries,passed)
    except ValueError:return True
    return False

def predicate():
    names=set(p.SUCCESS_MEMBERS)-{'members.json'}
    entries=[dict(name=n,bytes=1,regular=True,symlink=False)for n in sorted(names)]
    assert len(p.SUCCESS_MEMBERS)==43 and len(entries)==42
    assert p.inventory_metadata(entries,True)==dict.fromkeys(names,1)
    partial=[dict(name='result.json',bytes=1,regular=True,symlink=False)]
    assert p.inventory_metadata(partial,False)=={'result.json':1}and refused(partial,True)
    assert p.inventory_metadata(entries,False)==dict.fromkeys(names,1)
    assert refused(entries+[dict(entries[0])])
    bad=[dict(row)for row in entries];bad[0]=dict(bad[0],name='unknown.bin');assert refused(bad)
    bad=[dict(row)for row in entries];bad[0]=dict(bad[0],name='members.json');assert refused(bad)
    bad=[dict(row)for row in entries];bad[0]=dict(bad[1]);assert refused(bad)
    for key,value in [('bytes',0),('bytes',67108865),('bytes',True),('regular',False),('symlink',True)]:
        bad=[dict(row)for row in entries];bad[0][key]=value;assert refused(bad)
    bad=[dict(row)for row in entries];bad[0]['bytes']=bad[1]['bytes']=67108864;assert refused(bad)
    assert refused(entries[:-1])and refused([],False)
    assert refused([dict(name='Image',bytes=1,regular=True,symlink=False)],False)
    return dict(passed=True,groups=1,variants=1,assertions=1)
