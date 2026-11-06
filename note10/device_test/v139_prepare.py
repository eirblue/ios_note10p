"""Lexically bounded native wrapper correction over immutable138."""
from pathlib import Path
import re
import v138_prepare as retained
HERE=Path(__file__).resolve().parent
PINS=retained.PINS
OPTION=retained.OPTION
profile=retained.profile
sha=retained.sha
TOKEN=retained.TOKEN
SIGNATURE=re.compile(r'(?m)^(?P<ret>[A-Za-z_][A-Za-z_0-9 \t*]*?)[ \t*](?P<name>[A-Za-z_][A-Za-z_0-9]*)[ \t]*\(')
EVENT=re.compile(r'(?m)^[ \t]*#[^\n]*(?:\n|$)|[{}]')


def lexical_code(text):
    """Same offsets/newlines; comments and C literals are never code tokens."""
    pieces=[];last=0
    for token in TOKEN.finditer(text):
        if token.group().startswith(('/*','//','"',"'")):
            pieces.extend((text[last:token.start()],re.sub(r'[^\n]',' ',token.group())))
            last=token.end()
    pieces.append(text[last:]);return ''.join(pieces)


def balanced_parentheses(code,start):
    depth=0
    for match in re.finditer(r'[()]',code[start:]):
        depth+=1 if match.group()=='(' else -1
        if depth==0:return start+match.end()
    raise ValueError('unterminated native signature')


def body_end(code,opening,name):
    """Balance each alternative independently, then join equal brace depth.

    Actual DPU source has conditional alternative opening braces. Counting
    both alternatives serially is wrong; indentation is not C syntax either.
    No expression/config guess chooses one of unequal alternatives.
    """
    depth=1;branches=[]
    for event in EVENT.finditer(code,opening+1):
        value=event.group()
        if value.lstrip().startswith('#'):
            directive=re.match(r'\s*#\s*(\w+)',value).group(1)
            if directive in ('if','ifdef','ifndef'):branches.append([depth,[],False])
            elif directive in ('elif','else'):
                if not branches or branches[-1][2]:raise ValueError('unmatched native conditional: '+name)
                branch=branches[-1];branch[1].append(depth);depth=branch[0]
                if directive=='else':branch[2]=True
            elif directive=='endif':
                if not branches:raise ValueError('unmatched native endif: '+name)
                base,ends,has_else=branches.pop();ends.append(depth)
                if not has_else:ends.append(base)
                if len(set(ends))!=1:raise ValueError('unequal native conditional body depth: '+name)
                depth=ends[0]
            # Other preprocessor directive lines do not contain C braces.
        else:depth+=1 if value=='{' else -1
        if depth<0:raise ValueError('negative native body depth: '+name)
        if depth==0 and not branches:return event.end()
    raise ValueError('unterminated native body: '+name)


def definitions(raw):
    text=raw.decode();code=lexical_code(text);rows=[];previous_end=0
    for match in SIGNATURE.finditer(code):
        close=balanced_parentheses(code,match.end()-1);body=close
        while body<len(code) and code[body].isspace():body+=1
        if body>=len(code) or code[body]!='{':continue
        end=body_end(code,body,match.group('name'))
        if match.start()<previous_end:raise ValueError('overlapping native definition spans: '+match.group('name'))
        rows.append((match.start(),body,end,match.group('ret'),match.group('name'),text[match.end():close-1]))
        previous_end=end
    return text,rows


def with_lexer(callback,*args,**kwargs):
    original=retained.definitions;retained.definitions=definitions
    try:return callback(*args,**kwargs)
    finally:retained.definitions=original


def wrap_fragment(raw,names):
    return with_lexer(retained.wrap,raw,names=set(names))


def render(stock,identity,source128):
    output=with_lexer(retained.render,stock,identity,source128)
    return {name:raw.replace(b'N10XNU138',b'N10XNU139') for name,raw in output.items()}


def install(source,identity,source128):
    source=Path(source).resolve();stock={name:(source/name).read_bytes() for name in PINS}
    output=render(stock,identity,source128)
    for name in output:
        path=source/name
        if not path.resolve().is_relative_to(source) or any(p.is_symlink() for p in (path,*path.parents)):
            raise ValueError('unsafe139 native overlay path')
        if name not in PINS and path.exists():raise ValueError('new139 component exists')
    for name,raw in output.items():
        path=source/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
    return {name:sha(raw) for name,raw in output.items()}
