"""Extract character display names from the compiled script (rpy.rpa)."""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rpa
import rpyc_ast

GAME = r"D:\夏末白夜\TheWhiteNightInLateSummer\game"


def expr_source(o):
    """Return the Ren'Py source string captured by a PyCode/PyExpr stand-in."""
    t = type(o).__name__
    if t == 'PyCode':
        st = o.__dict__.get('_state')
        if isinstance(st, tuple) and len(st) >= 2:
            return expr_source(st[1]) if not isinstance(st[1], str) else st[1]
    if t == 'PyExpr':
        a = o.__dict__.get('_args')
        if a and isinstance(a[0], str):
            return a[0]
    return None


def character_map():
    magic, index = rpa.read_index(os.path.join(GAME, 'rpy.rpa'))
    off, dlen, _ = index['rpy/script.rpyc'][0]
    with open(os.path.join(GAME, 'rpy.rpa'), 'rb') as f:
        f.seek(off)
        blob = f.read(dlen)
    _, stmts = rpyc_ast.load_stmts(blob, 2)

    mapping = {}
    extra = {}
    def walk(n):
        while n is not None:
            t = type(n).__name__
            if t in ('Define', 'Default'):
                var = getattr(n, 'varname', None)
                src = expr_source(getattr(n, 'code', None))
                if var and src:
                    m = re.search(r'Character\(\s*["\']([^"\']*)["\']', src)
                    if m:
                        mapping[var] = m.group(1)
                    elif src.lstrip().startswith('Character('):
                        mapping[var] = None  # narration character
                    extra.setdefault(var, src[:80])
            b = getattr(n, 'block', None)
            if isinstance(b, list):
                for c in b:
                    walk(c)
            for attr in ('entries', 'item_blocks'):
                v = getattr(n, attr, None)
                if isinstance(v, list):
                    for e in v:
                        if isinstance(e, tuple):
                            for x in e:
                                if isinstance(x, list):
                                    for c in x:
                                        walk(c)
            n = getattr(n, 'next', None)

    for st in stmts:
        walk(st)

    # Some characters are declared inside story files.  Those pickles keep the
    # variable name and the `Character(...)` source in separate strings, with
    # pickle framing in between, so pair them up by proximity.
    decl = re.compile(r'([A-Za-z_]\w*)[^\w]{1,200}?Character\(\s*[\'"]([^\'"]*)[\'"]')
    for arc in ('rpy', 'story'):
        path = os.path.join(GAME, arc + '.rpa')
        if not os.path.exists(path):
            continue
        _m, idx = rpa.read_index(path)
        for name in sorted(idx):
            off, dlen, _s = idx[name][0]
            with open(path, 'rb') as f:
                f.seek(off)
                data = f.read(dlen)
            try:
                slots = rpyc_ast.read_slots(data)
            except Exception:
                continue
            for slot_data in slots.values():
                text = slot_data.decode('utf-8', 'replace')
                for var, disp in decl.findall(text):
                    if len(var) > 2:
                        mapping.setdefault(var, disp)

    return mapping, extra


if __name__ == '__main__':
    m, e = character_map()
    for k in sorted(m):
        print(f'{k:20s} -> {m[k]}')
