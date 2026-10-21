"""Ren'Py RPA archive lister/extractor (RPA-2.0 / RPA-3.0).

Matches the game's own renpy/loader.py: for RPA-3.0 the index is stored at the
plain header offset, and every entry has both offset and length XORed with the
key.  Entry tuples may be (off, len) or (off, len, start_prefix).
"""
import os
import pickle
import sys
import zlib


def read_header(path):
    with open(path, 'rb') as f:
        head = f.readline().decode('ascii', 'replace').strip()
    parts = head.split()
    offset = int(parts[1], 16)
    key = int(parts[2], 16) if len(parts) > 2 else 0
    return parts[0], offset, key


def fix_name(name):
    """Recover real filenames from mojibake archive keys (no-op for real Unicode)."""
    if not isinstance(name, str) or name.isascii():
        return name
    if any(ord(c) > 0xFF for c in name):
        return name  # already decoded Unicode
    raw = name.encode('latin-1')
    for enc in ('utf-8', 'gbk'):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            pass
    return name


def read_index(path):
    magic, offset, key = read_header(path)
    with open(path, 'rb') as f:
        f.seek(offset)
        raw = zlib.decompress(f.read())
    data = pickle.loads(raw)
    index = {}
    for name, entries in data.items():
        if isinstance(entries, tuple):
            entries = [entries]
        norm = []
        for e in entries:
            if magic == 'RPA-3.0':
                if len(e) >= 3:
                    norm.append((e[0] ^ key, e[1] ^ key, e[2] or b''))
                else:
                    norm.append((e[0] ^ key, e[1] ^ key, b''))
            else:
                if len(e) >= 3:
                    norm.append((e[0], e[1], e[2] or b''))
                else:
                    norm.append((e[0], e[1], b''))
        index[fix_name(name).replace('\\', '/')] = norm
    return magic, index


def extract(path, outdir, wanted=None):
    magic, index = read_index(path)
    n = 0
    with open(path, 'rb') as f:
        for name, entries in sorted(index.items()):
            if wanted and not wanted(name):
                continue
            target = os.path.join(outdir, *name.split('/'))
            os.makedirs(os.path.dirname(target), exist_ok=True)
            blob = b''.join((lambda off, dlen, start: (f.seek(off), f.read(dlen))[1])(*e)
                            for e in entries)
            with open(target, 'wb') as out:
                out.write(blob)
            n += 1
    return magic, len(index), n


if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'list':
        for p in sys.argv[2:]:
            try:
                magic, index = read_index(p)
            except Exception as exc:  # noqa
                print(f'!! {p}: {exc}')
                continue
            total = sum(sum(e[1] for e in v) for v in index.values())
            print(f'== {os.path.basename(p)} [{magic}] files={len(index)} packed={total}')
            for name in sorted(index):
                print(f'   {name}  ({sum(e[1] for e in index[name])})')
    elif cmd == 'extract':
        path, outdir = sys.argv[2], sys.argv[3]
        magic, total, n = extract(path, outdir)
        print(f'{os.path.basename(path)} [{magic}] files={total} extracted={n} -> {outdir}')
