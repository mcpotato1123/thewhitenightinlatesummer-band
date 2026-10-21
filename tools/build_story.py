"""Compile the Ren'Py AST of 《夏末白夜》 into a compact instruction stream for
the band (Vela quick-app) runtime.

Output
------
src/common/story/index.json      chapters, chunk table, totals
src/common/story/chunk-NNN.txt   one instruction per line, tab separated

Ops (first field):
    s  speaker  text              dialogue; speaker "" = narration, "@" = 常夏
    b  bg                         change background
    p  char pos eye brow mouth extra   place/compose a sprite
    h  char                       hide sprite ("@fg" clears a CG overlay)
    g  image                      full screen CG overlay
    m  t1<US>target1<US>t2<US>target2 ...   choice menu
    j  index                      jump
    e                             end of story
    n  name                       change 常夏's displayed name
    d  "9月1日 周二中午"           date / time chip
    c  title                      chapter title card
    v  name value                 set variable (numeric when possible)
    q  a b index                  if a > b: jump
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '_renpy'))

import charmap
import rpa
import rpyc_ast

# PC 版 game 目录（含 .rpa/.rpyc），默认放在仓库的上一级；可用 XBY_GAME 指定
GAME = os.environ.get('XBY_GAME') or os.path.join(os.path.dirname(os.path.dirname(HERE)),
                                                   'TheWhiteNightInLateSummer', 'game')
OUT = os.path.join(os.path.dirname(HERE), 'src', 'common', 'story')

US = '\x1f'
CHUNK = 128

# (archive stem, display title)
FILES = [
    ('prolugue_1', '序章 1'),
    ('prolugue_2', '序章 2'),
    ('prolugue_3', '序章 3'),
    ('c1_p1', '第 1 章 上'),
    ('c1_p2', '第 1 章 下'),
    ('c2_p1', '第 2 章'),
    ('c3_p1', '第 3 章 上'),
    ('c3_p2', '第 3 章 下'),
    ('c4_p1', '第 4 章 上'),
    ('c4_p2', '第 4 章 下'),
    ('c5_p1', '第 5 章 上'),
    ('c5_p2', '第 5 章 下'),
    ('c6c_p1', '第 6 章 · 常夏线'),
    ('c7c_p1', '第 7 章 · 常夏线'),
    ('c8c_p1', '第 8 章 · 常夏线'),
    ('c9c_p1', '第 9 章 · 常夏线'),
    ('c10c_p1', '第 10 章 · 常夏线上'),
    ('c10c_p2', '第 10 章 · 常夏线下'),
    ('c6k_p1', '第 6 章 · 辉夜奏线'),
    ('c7k_p1', '第 7 章 · 辉夜奏线'),
    ('c8k_p1', '第 8 章 · 辉夜奏线'),
    ('c9k_p1', '第 9 章 · 辉夜奏线上'),
    ('c9k_p2', '第 9 章 · 辉夜奏线下'),
    ('c10k_p1', '第 10 章 · 辉夜奏线上'),
    ('c10k_p2', '第 10 章 · 辉夜奏线下'),
]

CHAR_TAGS = {'changxia', 'kanade', 'gecheng', 'yuluoshen', 'dianzhang'}

POS = {
    '_left': 'l', '_center': 'c', '_right': 'r',
    'close_left': 'cl', 'close_right': 'cr',
    '_farleft': 'fl', '_right2': 'r2', '_left2': 'l2',
}

# Background aliases for images stored under another name.
BG_ALIAS = {
    'chess_club_noon_src': 'chess_club_noon',
    'coffee_afternoon_src': 'coffee_afternoon',
    'street_afternoon_src': 'street_afternoon',
    'cbt_street_afternoon': 'street_afternoon',
    'cbt_street_morning': 'street_morning',
    'cbt_street_night': 'street_night',
    'room': 'zhou_teng_bedroom_noon',
    'zhouteng_afternoon_a': 'zhou_teng_bedroom_noon',
    'zhouteng_afternoon_b': 'zhou_teng_bedroom_noon',
    'zhouteng_noon_b': 'zhou_teng_bedroom_noon',
    'zhouteng_night_a': 'zhou_teng_bedroom_night',
    'zhouteng_night_b': 'zhou_teng_bedroom_night',
}

TAG = re.compile(r'\{[^{}]*\}')

# Available art, so a scene that actually points at a CG still renders.
IMG_DIR = os.path.join(os.path.dirname(HERE), 'src', 'common', 'img')
BG_SET = set()
CG_SET = set()
for _sub, _target in (('b', BG_SET), ('c', CG_SET)):
    _dir = os.path.join(IMG_DIR, _sub)
    if os.path.isdir(_dir):
        _target.update(f[:-4] for f in os.listdir(_dir) if f.endswith('.png'))
DATE_VARS = {'months', 'days', 'time'}


def clean_text(s):
    if not isinstance(s, str):
        return ''
    s = s.replace('\\n', '\n').replace('{w}', '').replace('{p}', '').replace('{nw}', '')
    s = TAG.sub('', s)
    s = s.replace('[[', '\x00').replace('\x00', '[')
    s = s.replace('\t', ' ').replace('\n', '\\n')
    return s.strip()


def who_of(node, cmap):
    who = getattr(node, 'who', None)
    if isinstance(who, str):
        if who == 'changxia':
            return '@'
        if who in ('extend', 'nvl_narrator'):
            return ''
        name = cmap.get(who, '')
        return clean_text(name) if name else ''
    src = charmap.expr_source(who)
    if src:
        src = src.strip()
        if len(src) >= 2 and src[0] in '\'"' and src[-1] == src[0]:
            return src[1:-1]
    return ''


def imspec_of(node):
    ims = getattr(node, 'imspec', None)
    if not ims:
        ims = getattr(node, 'hide_imspec', None)
    return ims


def at_pos(ims):
    ats = ims[3] if len(ims) > 3 else []
    for a in ats or []:
        src = charmap.expr_source(a)
        if src:
            name = src.strip()
            if name in POS:
                return POS[name]
    return ''


def split_attrs(name):
    """('changxia','down','e_happy') -> (char, pos_word, eye, brow, mouth, extra)"""
    tag = name[0]
    eye = brow = mouth = ''
    extra = []
    for a in name[1:]:
        if a.startswith('e_'):
            eye = a[2:]
        elif a.startswith('eb_'):
            brow = a[3:]
        elif a.startswith('m_'):
            mouth = a[2:]
        elif a in ('flush',):
            extra.append('flush')
        elif a in ('glasses', 'bamboo', 'dress'):
            extra.append(a)
        elif a in ('speak', 'normal', 'smile', 'sad'):
            extra.append(a)
    return tag, eye, brow, mouth, ','.join(extra)


class Compiler(object):
    def __init__(self, cmap):
        self.ops = []
        self.labels = {}
        self.pending = []      # (op_index, field_index, label)
        self.after = []        # (op_index, token) fallthrough to patch
        self.cmap = cmap
        self.date = {'months': '', 'days': '', 'time': ''}
        self.date_shown = ''
        self.chapters = []
        self.stats = {}

    # -- emission helpers -------------------------------------------------
    def emit(self, *fields):
        self.ops.append(list(fields))
        return len(self.ops) - 1

    def emit_date(self):
        m, d, t = self.date['months'], self.date['days'], self.date['time']
        if not (m or d or t):
            return
        text = '%s月%s日' % (m.lstrip('0') or '', d.lstrip('0') or '')
        text = text.replace('月日', '')
        if t:
            text = (text + ' ' + t).strip()
        if text and text != self.date_shown:
            self.date_shown = text
            self.emit('d', text)

    # -- walking ----------------------------------------------------------
    def compile_file(self, key, title, stmts):
        start = len(self.ops)
        first_label = None
        for node in stmts:
            if first_label is None and type(node).__name__ == 'Label':
                first_label = getattr(node, '_name', None)
            self.compile_chain(node)
        self.chapters.append({
            'id': key,
            'title': title,
            'start': start,
            'label': first_label,
        })

    def compile_chain(self, node):
        while node is not None:
            self.compile_node(node)
            node = getattr(node, 'next', None)

    def compile_block(self, block):
        for node in block or []:
            self.compile_chain(node)

    def compile_node(self, n):
        t = type(n).__name__
        if t == 'Label':
            self.labels[getattr(n, '_name', None)] = len(self.ops)
            self.compile_block(getattr(n, 'block', None))

        elif t in ('Say', 'TranslateSay'):
            text = clean_text(getattr(n, 'what', ''))
            if text:
                self.emit('s', who_of(n, self.cmap), text)

        elif t == 'Scene':
            ims = imspec_of(n)
            if ims and ims[0]:
                name = BG_ALIAS.get(ims[0][0], ims[0][0])
                if name in BG_SET:
                    self.emit('b', name)
                elif name in CG_SET:
                    self.emit('b', 'black')
                    self.emit('g', name)

        elif t == 'Show':
            ims = imspec_of(n)
            if not ims or not ims[0]:
                return
            name = ims[0]
            tag = name[0]
            if tag in CHAR_TAGS:
                char, eye, brow, mouth, extra = split_attrs(name)
                self.emit('p', char, at_pos(ims), eye, brow, mouth, extra)
            elif tag in ('text', 'screen'):
                return
            elif tag in CG_SET:
                self.emit('g', tag)
            elif BG_ALIAS.get(tag, tag) in BG_SET:
                self.emit('b', BG_ALIAS.get(tag, tag))
            # anything else (CG fragments without art) is dropped

        elif t == 'Hide':
            ims = imspec_of(n)
            tag = ims[0][0] if ims and ims[0] else ''
            if tag in CHAR_TAGS:
                self.emit('h', tag)
            elif tag in ('text', 'screen'):
                return
            else:
                self.emit('h', '@fg')

        elif t == 'Menu':
            self.compile_menu(n)

        elif t == 'Jump':
            idx = self.emit('j', '')
            self.pending.append((idx, 1, getattr(n, 'target', '')))

        elif t == 'If':
            self.compile_if(n)

        elif t == 'Python':
            self.compile_python(n)

        elif t == 'Translate':
            self.compile_block(getattr(n, 'block', None))

        elif t == 'Return':
            self.emit('e')

        elif t in ('Init', 'Define', 'Default', 'With', 'EndTranslate',
                   'UserStatement', 'Pass', 'Image', 'Transform'):
            return

    def compile_menu(self, n):
        items = getattr(n, 'items', None) or []
        spec = []
        menu_idx = self.emit('m', '')
        ends = []
        for item in items:
            caption = clean_text(item[0] if item else '')
            if not caption or caption == '...':
                continue
            target = len(self.ops)
            spec.extend([caption, str(target)])
            block = item[2] if len(item) > 2 else None
            self.compile_block(block)
            # falling through the block continues after the menu
            j = self.emit('j', '')
            ends.append(j)
        after = len(self.ops)
        self.ops[menu_idx][1] = US.join(spec)
        for j in ends:
            self.ops[j][1] = str(after)

    def compile_if(self, n):
        entries = getattr(n, 'entries', None) or []
        real = []
        for cond, block in entries:
            src = (charmap.expr_source(cond) or '').strip()
            kinds = {type(c).__name__ for c in (block or [])}
            if kinds and kinds <= {'Python', 'UserStatement'}:
                continue      # achievement / bookkeeping only
            real.append((src, block))
        if not real:
            return
        if len(real) == 1:
            src, block = real[0]
            m = re.match(r'(\w+)\s*>\s*(\w+)$', src)
            if not m:
                self.compile_block(block)   # condition we cannot evaluate
            else:
                q = self.emit('q', m.group(1), m.group(2), '')
                self.compile_block(block)
                self.ops[q][3] = str(len(self.ops))
            return

        ends = []
        for i, (src, block) in enumerate(real):
            if i == len(real) - 1:
                self.compile_block(block)
                break
            m = re.match(r'(\w+)\s*>\s*(\w+)$', src)
            q = None
            if m:
                # jump past this branch when the condition is not greater
                q = self.emit('q', m.group(1), m.group(2), '')
            self.compile_block(block)
            j = self.emit('j', '')
            ends.append(j)
            if q is not None:
                self.ops[q][3] = str(len(self.ops))
        after = len(self.ops)
        for j in ends:
            self.ops[j][1] = str(after)

    def compile_python(self, n):
        src = charmap.expr_source(getattr(n, 'code', None)) or ''
        for line in src.splitlines():
            line = line.strip()
            m = re.match(r"changxia_name\s*=\s*['\"]([^'\"]*)['\"]", line)
            if m:
                self.emit('n', m.group(1))
                continue
            m = re.match(r"(months|days|time)\s*=\s*['\"]([^'\"]*)['\"]", line)
            if m:
                self.date[m.group(1)] = m.group(2)
                self.emit_date()
                continue
            m = re.match(r"chaptername\s*=\s*['\"]([^'\"]*)['\"]", line)
            if m:
                self.emit('c', m.group(1))
                continue
            m = re.match(r"(\w+_love)\s*=\s*(\w+_love)\s*\+\s*(\d+)", line)
            if m:
                self.emit('v', m.group(1), '+%s' % m.group(3))
                continue
            m = re.match(r"(\w+_love)\s*=\s*(\d+)$", line)
            if m:
                self.emit('v', m.group(1), m.group(2))


def main():
    archive = os.path.join(GAME, 'story.rpa')
    magic, index = rpa.read_index(archive)
    cmap, _ = charmap.character_map()
    comp = Compiler(cmap)

    for key, title in FILES:
        name = '_story/%s.rpyc' % key
        off, dlen, _s = index[name][0]
        with open(archive, 'rb') as f:
            f.seek(off)
            blob = f.read(dlen)
        _, stmts = rpyc_ast.load_stmts(blob, 2)
        comp.compile_file(key, title, stmts)

    comp.emit('e')
    # resolve label references
    for idx, field, label in comp.pending:
        if label not in comp.labels:
            raise SystemExit('unresolved label: %r' % label)
        comp.ops[idx][field] = str(comp.labels[label])

    # write chunks
    os.makedirs(OUT, exist_ok=True)
    for fn in os.listdir(OUT):
        if fn.startswith('chunk-') or fn in ('index.json', 'index.txt'):
            os.remove(os.path.join(OUT, fn))
    chunks = []
    lines = ['\t'.join(op) for op in comp.ops]
    for start in range(0, len(lines), CHUNK):
        part = lines[start:start + CHUNK]
        fn = 'chunk-%03d.txt' % (start // CHUNK)
        with open(os.path.join(OUT, fn), 'w', encoding='utf-8', newline='\n') as fh:
            fh.write('\n'.join(part) + '\n')
        chunks.append({'file': '/common/story/' + fn, 'start': start, 'count': len(part)})

    index_doc = {
        'version': 1,
        'total': len(lines),
        'chunks': chunks,
        'chapters': comp.chapters,
    }
    with open(os.path.join(OUT, 'index.txt'), 'w', encoding='utf-8') as fh:
        json.dump(index_doc, fh, ensure_ascii=False, separators=(',', ':'))

    kinds = {}
    for op in comp.ops:
        kinds[op[0]] = kinds.get(op[0], 0) + 1
    print('ops', len(lines), kinds)
    print('chunks', len(chunks), 'chapters', len(comp.chapters))
    print('size', round(os.path.getsize(os.path.join(OUT, 'index.txt')) / 1024, 1), 'KB index')
    total = sum(os.path.getsize(os.path.join(OUT, c['file'].split('/')[-1])) for c in chunks)
    print('story', round(total / 1024, 1), 'KB')


if __name__ == '__main__':
    main()
