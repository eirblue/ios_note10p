"""Closed225 shared owner-state transform and intrinsic same-Image symbol guard."""
import hashlib
SOURCE_BYTES=3257
SOURCE_SHA256='c0b4c544d337640192514b4e8bdb5018bfb3857295121b68359b16e1a515a028'
POSTIMAGE_SHA256='44adcc32fe55fe7c529b6b1206305ec6ab34cf66a13d86971a0cf4005910904f'
DECLARATION=b'static struct n217_state n219_kernel_state;\n'
WARNING=b'/* Independent spent states do not establish global no-replay across APIs.\n * A future caller must select219only and prove217unreachable, or add a reviewed\n * shared destination-consumption seam. There is no caller in this version. */\n'
NOTE=b'/* Both entry APIs share the destination-consumption state under n210_lock; no runtime caller. */\n'


def require(ok,message):
    if not ok:raise ValueError(message)


def prepare(raw):
    require(type(raw)is bytes and len(raw)==SOURCE_BYTES and hashlib.sha256(raw).hexdigest()==SOURCE_SHA256 and
        raw.count(DECLARATION)==1 and raw.count(b'n219_kernel_state')==12 and raw.count(WARNING)==1,'exact original219 owner source required')
    changed=raw.replace(DECLARATION,b'',1).replace(b'n219_kernel_state',b'n217_kernel_state').replace(WARNING,NOTE,1)
    require(b'n219_kernel_state' not in changed and changed.count(b'n217_kernel_state')==11 and
        hashlib.sha256(changed).hexdigest()==POSTIMAGE_SHA256,'exact shared225 state postimage required')
    return changed


def shared_symbols(raw,state_bytes):
    require(type(raw)is str and type(state_bytes)is int and 0<state_bytes<=1048576,'typed actual target state size required')
    rows=[line.split() for line in raw.splitlines() if line.strip()]
    state=[row for row in rows if row[0]=='n217_kernel_state']
    require(len(state)==1 and len(state[0])==4 and state[0][1]in ('b','B') and int(state[0][3],16)==state_bytes and
        not any(row[0]=='n219_kernel_state' for row in rows),'one shared217 BSS state and no219 state required')
    entries=('n217_ingest_current','n219_ingest_current')
    for name in entries:
        body=[row for row in rows if row[0]==name]
        require(len(body)==1 and len(body[0])==4 and body[0][1]in ('T','t') and int(body[0][3],16)>0,'both sameImage owner entry bodies required')
    return dict(schema='note10-v225-compiled-shared-owner-state-v1',state_symbol='n217_kernel_state',state_bytes=state_bytes,
        state_count=1,legacy_state_count=0,entry_symbols=list(entries),compiled_only=True,runtime_no_replay_proven=False)
