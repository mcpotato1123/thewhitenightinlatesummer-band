"""Render mock screens of the band UI with the real assets (336x480 each).

Visual check for the .ux layout: every number mirrors the pages and reader.js.
The palette follows the limelight-lemonade-jam reference (light, big type,
translucent white cards, decorative bars).
"""
import json
import os
import re
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMG = os.path.join(ROOT, 'src', 'common', 'img')
OUT = os.path.join(ROOT, 'preview')

W, H = 336, 480
FONT_CANDIDATES = [
    r"C:\Windows\Fonts\msyh.ttc",
    r"C:\Windows\Fonts\msyhbd.ttc",
]

# palette
BG = (245, 245, 247, 255)
CARD = (255, 255, 255, 235)
BORDER = (224, 224, 224, 255)
INK = (17, 17, 17, 255)
BODY = (51, 51, 51, 255)
MUTED = (153, 153, 153, 255)
TITLE = (235, 235, 235, 255)
YELLOW = (226, 216, 120, 40)
YELLOW_ON = (226, 216, 120, 150)
DANGER = (234, 108, 108, 255)


def font(size, bold=False):
    for path in (FONT_CANDIDATES[1], FONT_CANDIDATES[0]) if bold else FONT_CANDIDATES:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def text(draw, xy, s, size, color, anchor='la', bold=False):
    draw.text(xy, s, font=font(size, bold), fill=color, anchor=anchor)


def rrect(im, box, radius, fill, outline=None):
    layer = Image.new('RGBA', im.size, (0, 0, 0, 0))
    ImageDraw.Draw(layer).rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=1 if outline else 0)
    im.alpha_composite(layer)


def page():
    return Image.new('RGBA', (W, H), BG)


def headbar(canvas, title, sub=''):
    bar = Image.open(os.path.join(IMG, 'ui', 'headbar.png')).convert('RGBA')
    canvas.alpha_composite(bar, (0, 0))
    d = ImageDraw.Draw(canvas)
    text(d, (W // 2, 26), title, 30, TITLE, anchor='mm', bold=True)
    if sub:
        text(d, (W // 2, 50), sub, 14, (214, 214, 218, 255), anchor='mm')


def back_btn(canvas, top=428):
    rrect(canvas, (50, top, 286, top + 44), 22, CARD, BORDER)
    text(ImageDraw.Draw(canvas), (168, top + 22), '返回', 24, BODY, anchor='mm', bold=True)


def load_bg(name, pan=0):
    return Image.open(os.path.join(IMG, 'b', name + '.png')).convert('RGBA').crop((pan, 0, pan + W, H))


def load_sprite(tag, x=0, eye='normal', brow='normal', mouth='speak', size=None):
    d = os.path.join(IMG, 's', tag)
    meta = json.load(open(os.path.join(d, 'meta.json'), encoding='utf-8'))
    base = Image.open(os.path.join(d, 'base.png')).convert('RGBA')
    f = os.path.join(d, 'face__%s__%s__%s.png' % (eye, brow, mouth))
    if os.path.exists(f):
        base.alpha_composite(Image.open(f).convert('RGBA'), (meta['face'][0], meta['face'][1]))
    if size and size != base.size:
        base = base.resize(size, Image.LANCZOS)
    return base


def screen_title():
    canvas = Image.open(os.path.join(IMG, 'ui', 'title_bg.png')).convert('RGBA')
    canvas.alpha_composite(Image.open(os.path.join(IMG, 'ui', 'logo.png')).convert('RGBA'), (64, 26))
    rrect(canvas, (0, 200, W, 480), 0, (245, 245, 247, 247))
    items = ['开始阅读', '继续阅读', '章节选择', 'CG 鉴赏', '设置', '关于']
    y = 206
    for label in items:
        text(ImageDraw.Draw(canvas), (168, y + 19), label, 26, INK, anchor='mm', bold=True)
        ImageDraw.Draw(canvas).line((18, y + 38, 318, y + 38), fill=BORDER, width=1)
        y += 38
    text(ImageDraw.Draw(canvas), (168, y + 19), '退出应用', 26, DANGER, anchor='mm', bold=True)
    return canvas.convert('RGB')


def screen_game():
    canvas = load_bg('classroom_noon', 120)
    # 两人同台：216x324，左 8 / 右 112
    canvas.alpha_composite(load_sprite('changxia', 0, 'happy', 'normal', 'smile', (168, 336)), (0, 144))
    canvas.alpha_composite(load_sprite('kanade', 168, 'normal', 'normal', 'speak', (168, 336)), (168, 144))
    canvas.alpha_composite(Image.open(os.path.join(IMG, 'ui', 'board.png')).convert('RGBA'), (0, 300))
    d = ImageDraw.Draw(canvas)
    text(d, (12, 24), '第 1 章 · 星星也有眼睛吗', 15, (255, 255, 255, 255), anchor='lm')
    rrect(canvas, (18, 306, 18 + 74, 342), 14, (14, 16, 24, 158))
    text(ImageDraw.Draw(canvas), (30, 324), '常夏', 24, (255, 255, 255, 255), anchor='lm', bold=True)
    for i, line in enumerate(['怎么了周腾，脸色怎么一下子变得', '这么难看？']):
        text(d, (18, 338 + i * 24), line, 20, (255, 255, 255, 255))
    text(d, (306, 454), '▼', 16, (255, 209, 102, 255))
    return canvas.convert('RGB')


def screen_choice():
    canvas = load_bg('coffee_afternoon', 168)
    # 单人：280x420 居中
    canvas.alpha_composite(load_sprite('kanade', 68, 'normal', 'normal', 'confused', (200, 400)), (68, 80))
    rrect(canvas, (18, 186, 318, 238), 14, (255, 255, 255, 240))
    rrect(canvas, (18, 248, 318, 300), 14, (255, 255, 255, 240))
    d = ImageDraw.Draw(canvas)
    text(d, (30, 212), '我陪你一起去吧。', 24, INK, anchor='lm', bold=True)
    text(d, (30, 274), '路上小心，早点回来。', 24, INK, anchor='lm', bold=True)
    return canvas.convert('RGB')


def screen_menu():
    canvas = page()
    d = ImageDraw.Draw(canvas)
    text(d, (W // 2, 30), '菜单', 32, BODY, anchor='mm', bold=True)
    text(d, (W // 2, 58), '第 5 章 下 · 42%', 15, MUTED, anchor='mm')
    rows = ['继续阅读', '保存进度', '读取存档']
    y = 74
    for i, label in enumerate(rows):
        rrect(canvas, (23, y, 313, y + 40), 0, YELLOW_ON if i == 0 else YELLOW)
        text(ImageDraw.Draw(canvas), (168, y + 20), label, 24, INK, anchor='mm', bold=True)
        y += 46
    for a, b in [('自动 开', '快进 关'), ('回退一句', '章节'), ('CG 鉴赏', '设置')]:
        for i, label in enumerate((a, b)):
            left = 23 + i * 148
            rrect(canvas, (left, y, left + 142, y + 40), 0, YELLOW)
            text(ImageDraw.Draw(canvas), (left + 71, y + 20), label, 24, INK, anchor='mm', bold=True)
        y += 46
    for i, label in enumerate(('返回主页', '退出应用')):
        left = 23 + i * 148
        rrect(canvas, (left, y, left + 142, y + 40), 0, (234, 108, 108, 42))
        text(ImageDraw.Draw(canvas), (left + 71, y + 20), label, 24, INK, anchor='mm', bold=True)
    return canvas.convert('RGB')


def screen_chapters():
    canvas = page()
    headbar(canvas, '章节选择', '共 25 章 · 上下滑动 · 点按进入')
    titles = ['序章 1', '序章 2', '序章 3', '第 1 章 上', '第 1 章 下']
    for i, title in enumerate(titles):
        top = 90 + i * 66
        rrect(canvas, (12, top, 324, top + 58), 12, CARD, BORDER)
        text(ImageDraw.Draw(canvas), (26, top + 29), '%02d' % (i + 1), 20, MUTED, anchor='lm')
        text(ImageDraw.Draw(canvas), (66, top + 29), title, 24, (34, 34, 34, 255), anchor='lm', bold=True)
    back_btn(canvas)
    return canvas.convert('RGB')


def screen_saves():
    canvas = page()
    headbar(canvas, '存档', '点按读取 · 长按删除')
    rows = [('1', '第 3 章 上', '10/2 21:14'), ('2', '第 1 章 下', '10/1 23:02'),
            ('3', '空', ''), ('4', '空', ''), ('5', '空', ''), ('6', '空', '')]
    for i, (no, name, tm) in enumerate(rows):
        top = 90 + i * 62
        rrect(canvas, (12, top, 324, top + 54), 12, CARD, BORDER)
        text(ImageDraw.Draw(canvas), (26, top + 27), no, 20, MUTED, anchor='lm')
        text(ImageDraw.Draw(canvas), (56, top + 27), name, 23, (34, 34, 34, 255), anchor='lm', bold=True)
        text(ImageDraw.Draw(canvas), (306, top + 27), tm, 16, MUTED, anchor='rm')
    back_btn(canvas)
    return canvas.convert('RGB')


def screen_cg():
    canvas = page()
    names = sorted(f[:-4] for f in os.listdir(os.path.join(IMG, 't')))
    headbar(canvas, 'CG 鉴赏', '已解锁 9 / %d · 点图放大 · 左右拖动看全图' % len(names))
    for i, name in enumerate(names[:12]):
        row, col = divmod(i, 3)
        left = 20 + col * 106
        top = 90 + row * 66
        thumb = Image.open(os.path.join(IMG, 't', name + '.png')).convert('RGBA')
        rrect(canvas, (left - 1, top - 1, left + 97, top + 55), 8, (255, 255, 255, 255), BORDER)
        canvas.alpha_composite(thumb, (left, top))
    back_btn(canvas)
    return canvas.convert('RGB')


def screen_cgview():
    names = sorted(f[:-4] for f in os.listdir(os.path.join(IMG, 'w')))
    name = 'cg5' if 'cg5' in names else names[0]
    wide = Image.open(os.path.join(IMG, 'w', name + '.png')).convert('RGBA')
    canvas = wide.crop((0, 0, W, wide.size[1]))
    d = ImageDraw.Draw(canvas)
    d.rectangle((0, 424, W, 480), fill=(0, 0, 0, 148))
    rrect(canvas, (12, 12, 12 + 12 + 8 * len(name), 44), 10, (0, 0, 0, 140))
    text(ImageDraw.Draw(canvas), (20, 28), name, 16, (255, 255, 255, 255), anchor='lm')
    rrect(canvas, (288, 8, 328, 48), 20, (0, 0, 0, 153))
    text(ImageDraw.Draw(canvas), (308, 28), '×', 26, (255, 255, 255, 255), anchor='mm')
    rrect(canvas, (48, 440, 288, 444), 2, (255, 255, 255, 71))
    tw = max(18, round(240 * W / wide.size[0]))
    rrect(canvas, (48, 440, 48 + tw, 444), 2, (255, 209, 102, 255))
    text(ImageDraw.Draw(canvas), (168, 456), '左右拖动看全图', 16, (221, 221, 221, 255), anchor='mm')
    return canvas.convert('RGB')


def screen_settings():
    canvas = page()
    headbar(canvas, '设置')
    y = 82
    for label, val in (('字体大小', '20 px'), ('文本播放速度', '28ms/字'), ('自动播放', '关')):
        rrect(canvas, (12, y, 324, y + 74), 12, CARD, BORDER)
        text(ImageDraw.Draw(canvas), (168, y + 14), label, 22, BODY, anchor='mm', bold=True)
        for left, glyph in ((28, '−'), (262, '＋')):
            rrect(canvas, (left, y + 30, left + 46, y + 76 - 4), 23, (226, 216, 120, 140))
            text(ImageDraw.Draw(canvas), (left + 23, y + 53), glyph, 26, (51, 51, 51, 255), anchor='mm', bold=True)
        text(ImageDraw.Draw(canvas), (168, y + 53), val, 24, (34, 34, 34, 255), anchor='mm', bold=True)
        y += 80
    rrect(canvas, (12, y, 324, y + 98), 12, CARD, BORDER)
    text(ImageDraw.Draw(canvas), (30, y + 24), '屏幕常亮', 22, BODY, anchor='lm', bold=True)
    rrect(canvas, (216, y + 8, 302, y + 42), 17, (226, 216, 120, 230))
    text(ImageDraw.Draw(canvas), (259, y + 25), '开', 18, BODY, anchor='mm', bold=True)
    text(ImageDraw.Draw(canvas), (30, y + 70), '长按画面', 22, BODY, anchor='lm', bold=True)
    rrect(canvas, (186, y + 54, 316, y + 88), 17, (226, 226, 230, 255))
    text(ImageDraw.Draw(canvas), (251, y + 71), '关', 18, BODY, anchor='mm', bold=True)
    back_btn(canvas)
    return canvas.convert('RGB')


def _wrap_units(s, maxu=38):
    punct = '，。！？；：、）」』…—'
    out = []

    def unit(ch):
        return 1 if ord(ch) < 128 else 2

    for para in s.split('\n'):
        if not para:
            out.append('')
            continue
        toks, word = [], ''
        for ch in para:
            if ord(ch) < 128 and re.match(r"[A-Za-z0-9'._-]", ch):
                word += ch
                continue
            if word:
                toks.append(word)
                word = ''
            toks.append(ch)
        if word:
            toks.append(word)
        line, w = '', 0
        for tk in toks:
            tw = sum(unit(c) for c in tk)
            if line and w + tw > maxu and not (len(tk) == 1 and tk in punct):
                out.append(line.rstrip())
                line, w = tk, tw
            else:
                line += tk
                w += tw
        if line:
            out.append(line.rstrip())
    return out


ABOUT = [
    ('故事', '暑假第三天，白月高中的周腾照旧和葛城昼夜颠倒地打着游戏，直到白月公园那个怪谈又被提起——在 8 月 31 日留下深刻遗憾的人，会被永远困在 8 月 32 日。\n\n开学报到当天，一名男学生失踪了。自称「看得见」的后辈辉夜奏、总是笑着的常夏，还有那间叫「星期八」的咖啡厅，把这个夏天一点点拖向不对劲的地方。'),
    ('原作', '《夏末白夜》\nThe White Night in Late Summer'),
    ('移植', '小米手环 9 Pro（336×480）的 Vela 快应用，参照 limelight 版的界面结构重写。'),
    ('素材', "剧本、立绘、背景、CG 均由 PC 版 Ren'Py 原版解包。"),
    ('操作', '点屏幕：下一句／立即显示整句\n下滑：菜单　右滑：回退一句'),
    ('解锁', '连点标题「关于」7 下，可一次点亮全部 CG。'),
    ('声明', '非官方同人移植，仅供个人学习交流。'),
]


def _about_rows():
    rows = [('g', '')]
    for head, body in ABOUT:
        rows.append(('h', head))
        for ln in _wrap_units(body):
            rows.append(('p', ln))
        rows.append(('g', ''))
    return rows


def screen_about():
    canvas = page()
    ver = json.load(open(os.path.join(ROOT, 'src', 'manifest.json'), encoding='utf-8')).get('versionName', '')
    headbar(canvas, '关于', 'v' + ver + ' · 手环移植版')
    rrect(canvas, (12, 80, 324, 382), 12, CARD, BORDER)
    y = 84
    for kind, s in _about_rows():
        if 84 <= y <= 368:
            if kind == 'h':
                text(ImageDraw.Draw(canvas), (24, y), s, 17, (26, 26, 26, 255), bold=True)
            elif kind == 'p':
                text(ImageDraw.Draw(canvas), (24, y), s, 15, (74, 74, 74, 255))
        y += 20
    for left, label in ((18, '常夏结局'), (180, '奏结局')):
        rrect(canvas, (left, 390, left + 138, 430), 20, CARD, BORDER)
        text(ImageDraw.Draw(canvas), (left + 69, 410), label, 20, BODY, anchor='mm', bold=True)
    back_btn(canvas, 436)
    return canvas.convert('RGB')


def screen_unlock():
    base = screen_about().convert('RGBA')
    base.alpha_composite(Image.new('RGBA', (W, H), (0, 0, 0, 107)))
    rrect(base, (20, 84, 316, 396), 16, (255, 255, 255, 255))
    d = ImageDraw.Draw(base)
    text(d, (W // 2, 112), '解 锁', 28, BODY, anchor='mm', bold=True)
    text(d, (W // 2, 140), 'CG 5 / 13　通关 否', 16, MUTED, anchor='mm')
    rows = [('解锁全部 CG', YELLOW_ON), ('标记已通关', YELLOW), ('清空 CG 记录', YELLOW), ('关闭', (242, 242, 244, 255))]
    y = 158
    for label, fill in rows:
        rrect(base, (43, y, 293, y + 44), 0, fill)
        text(ImageDraw.Draw(base), (168, y + 22), label, 22, INK, anchor='mm', bold=True)
        y += 52
    return base.convert('RGB')


def main():
    os.makedirs(OUT, exist_ok=True)
    screens = {
        '01-标题': screen_title(),
        '02-正文': screen_game(),
        '03-选项': screen_choice(),
        '04-菜单': screen_menu(),
        '05-章节': screen_chapters(),
        '06-CG鉴赏': screen_cg(),
        '07-设置': screen_settings(),
        '08-关于': screen_about(),
        '09-解锁': screen_unlock(),
        '10-看CG': screen_cgview(),
    }
    for name, im in screens.items():
        im.save(os.path.join(OUT, name + '.png'), optimize=True)
    rows_n = (len(screens) + 3) // 4
    sheet = Image.new('RGB', (4 * 352, rows_n * 496), (10, 10, 14))
    for i, im in enumerate(screens.values()):
        row, col = divmod(i, 4)
        sheet.paste(im, (col * 352 + 8, row * 496 + 8))
    sheet.save(os.path.join(OUT, 'ui-preview.png'), optimize=True)
    print('screens', len(screens), '->', OUT)


if __name__ == '__main__':
    main()
