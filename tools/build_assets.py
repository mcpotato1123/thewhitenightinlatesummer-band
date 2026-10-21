"""Turn the unpacked PC assets into band-sized files.

    b/<bg>.png            672x480 (2x screen, panned at runtime), 128 colours
    s/<char>/base.png     143x380 bust, alpha
    s/<char>/face_*.png   cropped eye+brow+mouth composite
    s/<char>/flush.png    blush overlay, cropped
    c/<cg>.png            336x480
    t/<cg>.png            96x137 thumbnails

The sprite canvas matches the reference layout: 143x380, anchored at top 100px,
slots at left 10 / 96 / 182.
"""
import json
import os
import shutil
import sys
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# 解包后的原作素材目录，默认放在仓库的上一级；也可用 XBY_SRC 指定
SRC = os.environ.get('XBY_SRC') or os.path.join(os.path.dirname(ROOT), '解包输出')
IMG = os.path.join(ROOT, 'src', 'common', 'img')

W, H = 336, 480
BG_W = 672
SW, SH = 210, 420

CN_BG = {
    '周腾卧室_中午A_4K': 'zhou_teng_bedroom_noon',
    '周腾卧室_中午B_4K': 'zhou_teng_bedroom_noon_b',
    '周腾卧室_傍晚A_4K': 'zhou_teng_bedroom_evening',
    '周腾卧室_傍晚B_4K': 'zhou_teng_bedroom_evening_b',
    '周腾卧室_夜晚A_4K': 'zhou_teng_bedroom_night',
    '周腾卧室_夜晚B_4K': 'zhou_teng_bedroom_night_b',
    '咖啡厅_中午_4K': 'coffee_shop_noon',
    '围棋社活动室_傍晚_4K': 'chess_club_evening',
    '围棋社活动室_夜晚_4K': 'chess_club_night',
    '常夏客厅_中午_4K': 'changxia_livingroom_noon',
    '常夏客厅_夜晚_4K': 'changxia_livingroom_night',
    '步行街_白天_4K': 'pedestrian_day',
    '步行街_傍晚_4K': 'pedestrian_evening',
    '步行街_夜晚_4K': 'pedestrian_night',
    '步行街_阴天_4K': 'pedestrian_cloudy',
    '街道A_早上_4K': 'streetA_morning',
    '走廊A_夜晚_关灯_4K': 'corridorA_night_off',
    '走廊A_早上_4K': 'corridorA_morning',
    '走廊B_夜晚_关灯_4K': 'corridorB_night_off',
    '走廊B_夜晚_开灯_4K': 'corridorB_night_on',
    '走廊B_早上_4K': 'corridorB_morning',
}

CHARS = {
    'changxia': '常夏',
    'kanade': '辉夜奏',
    'yuluoshen': '余洛琛',
    'gecheng': '葛城',
}

CROP_TOP = 0.0
CROP_H = 1.0


def cover(im, w, h):
    sw, sh = im.size
    scale = max(w / sw, h / sh)
    im = im.resize((max(1, round(sw * scale)), max(1, round(sh * scale))), Image.LANCZOS)
    sw, sh = im.size
    return im.crop(((sw - w) // 2, (sh - h) // 2, (sw - w) // 2 + w, (sh - h) // 2 + h))


def save_bg(src, dst):
    with Image.open(src) as im:
        im = cover(im.convert('RGB'), BG_W, H)
    im.quantize(colors=128, method=Image.MEDIANCUT, dither=Image.FLOYDSTEINBERG).save(dst, optimize=True)


def load_rgba(path):
    with Image.open(path) as im:
        return im.convert('RGBA')


def sprite_geometry(paths):
    """Full-figure window: head to shoes, wide enough for both arms.

    Everything is derived from the union bbox of the character's layers, so the
    crop never clips a hand or the feet; the canvas aspect (210:420 = 0.5) is
    close to the figure's own 0.48.
    """
    layers = [load_rgba(p) for p in paths
              if any(k in os.path.basename(p).lower() for k in (' base', ' eye ', ' eyebrow ', ' mouth '))]
    if not layers:                      # 店长这类只有整张立绘，没有分层
        layers = [load_rgba(p) for p in paths]
    w, h = layers[0].size

    union = None
    for im in layers:
        box = im.getbbox()
        if not box:
            continue
        union = box if union is None else (
            min(union[0], box[0]), min(union[1], box[1]),
            max(union[2], box[2]), max(union[3], box[3]))
    if union is None:
        union = (0, 0, w, h)

    pad_x = int((union[2] - union[0]) * 0.03)
    pad_y = int((union[3] - union[1]) * 0.02)
    x0 = max(0, union[0] - pad_x)
    x1 = min(w, union[2] + pad_x)
    y0 = max(0, union[1] - pad_y)
    y1 = min(h, union[3] + pad_y)

    ch = y1 - y0
    cw = max(int((x1 - x0)), int(ch * SW / SH))
    cw = min(cw, w)
    cx = (x0 + x1) / 2
    left = int(max(0, min(cx - cw / 2, w - cw)))
    return left, y0, left + cw, y0 + ch


def build_char(tag, folder):
    src_dir = os.path.join(SRC, '立绘', folder)
    files = sorted(f for f in os.listdir(src_dir) if f.lower().endswith(('.webp', '.png')))
    paths = [os.path.join(src_dir, f) for f in files]
    win = sprite_geometry(paths)
    out_dir = os.path.join(IMG, 's', tag)
    os.makedirs(out_dir, exist_ok=True)

    layers = {}
    for p in paths:
        name = os.path.basename(p).rsplit('.', 1)[0]
        part = name
        if part.startswith(tag + ' '):
            part = part[len(tag) + 1:]
        elif folder in part:
            part = part.replace(folder, '', 1)
        part = part.strip().replace(' ', '_')
        if not part or part.startswith(('arm', 'hand')):
            continue
        layers[part] = load_rgba(p).crop(win).resize((SW, SH), Image.LANCZOS)

    base = layers.pop('base', None)
    if base is None:
        return 0
    base.save(os.path.join(out_dir, 'base.png'), optimize=True)
    if 'base_2' in layers:
        layers.pop('base_2').save(os.path.join(out_dir, 'base2.png'), optimize=True)

    eyes = {k[4:]: v for k, v in layers.items() if k.startswith('eye_')}
    if 'normal' in layers:            # default eye sometimes ships as plain normal.png
        eyes.setdefault('normal', layers['normal'])
    brows = {k[8:]: v for k, v in layers.items() if k.startswith('eyebrow_')}
    mouths = {k[6:]: v for k, v in layers.items() if k.startswith('mouth_')}

    face_box = None
    for group in (eyes, brows, mouths):
        for im in group.values():
            box = im.getbbox()
            if not box:
                continue
            face_box = box if face_box is None else (
                min(face_box[0], box[0]), min(face_box[1], box[1]),
                max(face_box[2], box[2]), max(face_box[3], box[3]))
    if face_box is None:
        return 0
    pad = 2
    fb = (max(0, face_box[0] - pad), max(0, face_box[1] - pad),
          min(SW, face_box[2] + pad), min(SH, face_box[3] + pad))

    combos = set()
    story_dir = os.path.join(ROOT, 'src', 'common', 'story')
    for fn in sorted(os.listdir(story_dir)):
        if not fn.startswith('chunk-'):
            continue
        for line in open(os.path.join(story_dir, fn), encoding='utf-8').read().splitlines():
            parts = line.split('\t')
            if parts[0] == 'p' and parts[1] == tag:
                combos.add((parts[3], parts[4], parts[5]))

    made = 0
    for eye, brow, mouth in combos:
        canvas = Image.new('RGBA', (SW, SH), (0, 0, 0, 0))
        for group, key in ((eyes, eye), (brows, brow), (mouths, mouth)):
            if key and key in group:
                canvas = Image.alpha_composite(canvas, group[key])
        face = canvas.crop(fb)
        if face.getbbox() is None:
            continue
        name = 'face__%s__%s__%s.png' % (eye or '-', brow or '-', mouth or '-')
        face.save(os.path.join(out_dir, name), optimize=True)
        made += 1

    if 'flush' in layers:
        flush = layers['flush']
        # 保留整幅画布：运行时按 (left, top, w, h) 直接贴，裁掉会拉伸错位
        if flush.getbbox():
            flush.save(os.path.join(out_dir, 'flush.png'), optimize=True)
    with open(os.path.join(out_dir, 'meta.json'), 'w', encoding='utf-8') as fh:
        json.dump({'face': list(fb), 'size': [SW, SH]}, fh)
    return made


def build_shopkeeper():
    src_dir = os.path.join(SRC, '其他', '咖啡厅')
    paths = [os.path.join(src_dir, f) for f in sorted(os.listdir(src_dir))
             if f.lower().endswith('.webp')]
    win = sprite_geometry(paths)
    out_dir = os.path.join(IMG, 's', 'dianzhang')
    os.makedirs(out_dir, exist_ok=True)
    for i, p in enumerate(paths):
        load_rgba(p).crop(win).resize((SW, SH), Image.LANCZOS).save(
            os.path.join(out_dir, 'pose%d.png' % (i + 1)), optimize=True)


def cg_sources():
    """Yield (id, RGBA canvas) for every full-size CG in the export.

    What actually lives in 解包输出/CG:
      cg1..cg10        one folder per CG, `*_std`/`base` is the full art (16:9,
                       3840x2160 or 3820x2160), the other files are face layers
      qcg_1_1/2        1920x1080 quiz CGs
      qcg2/            3 separate 1920x1080 quiz CGs
      *mark.webp       355x200 gallery thumbnails of the original EXTRA menu
      ed_*.png         355x200 ending cards
      43.png           credits page, street_afternoon.webp is a background
    Only the 16:9 full art belongs in the gallery.
    """
    src_cg = os.path.join(SRC, 'CG')

    def coverage(im):
        hist = im.getchannel('A').histogram()
        return sum(hist[32:]) / float(im.size[0] * im.size[1])

    def full_size(im):
        return im.size[0] >= 1280 and im.size[1] >= 720

    for entry in sorted(os.listdir(src_cg)):
        p = os.path.join(src_cg, entry)
        if os.path.isdir(p):
            files = [os.path.join(p, f) for f in sorted(os.listdir(p))
                     if f.lower().endswith(('.webp', '.png', '.jpg'))]
            if not files:
                continue
            base = None
            for f in files:
                low = os.path.basename(f).lower()
                if low.startswith('base') or low.endswith('_std.webp') or low == 'std.webp':
                    base = f
                    break
            if base is None:
                rgb = [f for f in files if Image.open(f).mode in ('RGB', 'P', 'L')]
                base = rgb[0] if rgb else max(files, key=lambda f: os.path.getsize(f))
            base_im = load_rgba(base)
            if not full_size(base_im):
                continue
            canvas = base_im
            for f in files:
                if f == base:
                    continue
                layer = load_rgba(f)
                if coverage(layer) > 0.05:
                    canvas = Image.alpha_composite(canvas, layer)
            if os.path.basename(base).lower() in ('base.webp',) or '_std' in os.path.basename(base).lower():
                yield entry, canvas
                continue
            # 没有 base/std 的目录（如 qcg2）：每个文件都是一张独立 CG
            for i, f in enumerate(files):
                im = load_rgba(f)
                if full_size(im):
                    yield '%s_%d' % (entry, i + 1), im
        else:
            low = entry.lower()
            if not low.endswith(('.webp', '.png', '.jpg')):
                continue
            if 'mark' in low or low.startswith('43') or low.startswith('street'):
                continue
            if low.startswith('ed_'):
                continue          # 355x200 的结局卡，放大后会糊
            im = load_rgba(p)
            if not full_size(im):
                continue
            yield entry.rsplit('.', 1)[0], im


def fit_height(im, h):
    """Scale to the given height; width follows the source aspect."""
    w = max(1, round(im.size[0] * h / im.size[1]))
    return im.resize((w, h), Image.LANCZOS)


def build_cg():
    """Keep the original 16:9 art only.

    w/ = full-width CG (scaled to 480 high, ~853 wide) — the story shows it with
    object-fit:cover and the gallery pans it; t/ = 96x54 gallery thumbnails.
    """
    th_dir = os.path.join(IMG, 't')
    wide_dir = os.path.join(IMG, 'w')
    for d in (th_dir, wide_dir):
        os.makedirs(d, exist_ok=True)
    shutil.rmtree(os.path.join(IMG, 'c'), ignore_errors=True)

    for ident, canvas in cg_sources():
        wide = fit_height(canvas.convert('RGB'), H)
        wide.quantize(colors=160, method=Image.MEDIANCUT, dither=Image.FLOYDSTEINBERG).save(
            os.path.join(wide_dir, ident + '.png'), optimize=True)
        wide.resize((96, 54), Image.LANCZOS).quantize(colors=96).save(
            os.path.join(th_dir, ident + '.png'), optimize=True)


def build_title():
    """Title art + app icon, taken from the game's own main-menu assets."""
    src = os.path.join(SRC, '其他', '原作UI')
    ui = os.path.join(IMG, 'ui')
    os.makedirs(ui, exist_ok=True)

    bg_src = os.path.join(src, 'main_menu_bg.webp')
    if os.path.exists(bg_src):
        with Image.open(bg_src) as im:
            art = im.convert('RGB')
        scale = H / art.size[1]
        art = art.resize((round(art.size[0] * scale), H), Image.LANCZOS)
        fx = 0.28
        left = int((art.size[0] - W) * fx)
        art = art.crop((left, 0, left + W, H))
        scrim = Image.new('L', (1, H), 0)
        px = scrim.load()
        for y in range(H):
            a = 190 if y < 150 else max(0, int(190 * (1 - (y - 150) / 110.0)))
            px[0, y] = min(255, a)
        scrim = scrim.resize((W, H))
        dark = Image.new('RGB', (W, H), (8, 10, 16))
        art = Image.composite(dark, art, scrim)
        art.quantize(colors=192, method=Image.MEDIANCUT, dither=Image.FLOYDSTEINBERG).save(
            os.path.join(ui, 'title_bg.png'), optimize=True)

    logo_src = os.path.join(src, 'main_menu_logo.png')
    if os.path.exists(logo_src):
        with Image.open(logo_src) as im:
            lg = im.convert('RGBA')
        w = 208
        lg = lg.resize((w, max(1, round(lg.size[1] * w / lg.size[0]))), Image.LANCZOS)
        lg.save(os.path.join(ui, 'logo.png'), optimize=True)

    icon_src = os.path.join(src, 'window_icon.png')
    icon_path = os.path.join(ROOT, 'src', 'common', 'icon.png')
    if os.path.exists(icon_src):
        with Image.open(icon_src) as im:
            ic = im.convert('RGBA').resize((192, 192), Image.LANCZOS)
        bgc = Image.new('RGBA', (192, 192), (255, 255, 255, 255))
        ic = Image.alpha_composite(bgc, ic).convert('RGBA')
        # 方形原图 → 23% 圆角（表盘桌面图标没有系统遮罩，圆角得自己切）；
        # 保留抗锯齿的 alpha，所以存真彩 PNG，不量化
        mask = Image.new('L', (192, 192), 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, 191, 191), radius=44, fill=255)
        ic.putalpha(mask)
        ic.save(icon_path, optimize=True)


def build_theme():
    """Light-theme chrome: top/bottom decorative bars and the reading board.

    limelight 版靠 bt.png / hd.png / board.png 三张图做装饰，这里按同样的思路生成：
    顶栏承载浅灰标题，底栏压住返回键，board 是半透明深色对白板。
    """
    ui = os.path.join(IMG, 'ui')
    os.makedirs(ui, exist_ok=True)

    # top bar: dark fading to transparent + 1px hairline
    head = Image.new('RGBA', (W, 72), (0, 0, 0, 0))
    px = head.load()
    for y in range(72):
        a = 232 if y < 52 else int(232 * (1 - (y - 52) / 20.0))
        for x in range(W):
            px[x, y] = (26, 28, 36, a)
    d = ImageDraw.Draw(head)
    d.line((0, 71, W, 71), fill=(255, 255, 255, 46), width=1)
    head.save(os.path.join(ui, 'headbar.png'), optimize=True)

    # bottom bar: transparent fading into dark
    foot = Image.new('RGBA', (W, 56), (0, 0, 0, 0))
    px = foot.load()
    for y in range(56):
        a = int(120 * (y / 55.0) ** 1.5)
        for x in range(W):
            px[x, y] = (14, 16, 22, a)
    foot.save(os.path.join(ui, 'footbar.png'), optimize=True)

    # reading board: vertical gradient, clear at the top (legs stay visible)
    # and dark where the text sits, so there is no hard seam across the sprite.
    board = Image.new('RGBA', (W, 180), (0, 0, 0, 0))
    bpx = board.load()
    for y in range(180):
        if y < 30:
            a = int(8 + 172 * (y / 30.0))
        else:
            a = min(232, int(180 + 52 * ((y - 30) / 40.0)))
        for x in range(W):
            bpx[x, y] = (14, 16, 24, a)
    board.save(os.path.join(ui, 'board.png'), optimize=True)


def build_ui():
    """App icon and the locked-CG placeholder."""
    from PIL import ImageDraw, ImageFont
    out = os.path.join(IMG, 'ui')
    os.makedirs(out, exist_ok=True)

    d = os.path.join(IMG, 's', 'changxia')
    base = Image.open(os.path.join(d, 'base.png')).convert('RGBA')
    face = os.path.join(d, 'face__happy__normal__smile.png')
    if os.path.exists(face):
        meta = json.load(open(os.path.join(d, 'meta.json'), encoding='utf-8'))
        base.alpha_composite(Image.open(face).convert('RGBA'), (meta['face'][0], meta['face'][1]))
    head = base.crop((30, 8, 113, 120)).resize((150, 150), Image.LANCZOS)
    lock = Image.new('RGB', (96, 137), (32, 26, 40))
    dr = ImageDraw.Draw(lock)
    try:
        f = ImageFont.load_default(size=34)
    except TypeError:
        f = ImageFont.load_default()
    dr.text((34, 48), '?', fill=(120, 104, 128), font=f)
    lock.save(os.path.join(out, 'locked.png'), optimize=True)


def write_manifest():
    bgs = sorted(f[:-4] for f in os.listdir(os.path.join(IMG, 'b')) if f.endswith('.png'))
    cgs = sorted(f[:-4] for f in os.listdir(os.path.join(IMG, 'w')) if f.endswith('.png'))
    sprites = {}
    for tag in sorted(os.listdir(os.path.join(IMG, 's'))):
        d = os.path.join(IMG, 's', tag)
        sprites[tag] = sorted(f for f in os.listdir(d) if f.endswith('.png'))
        meta = os.path.join(d, 'meta.json')
        if os.path.exists(meta):
            sprites[tag + '__meta'] = json.load(open(meta, encoding='utf-8'))
    wide = {}
    wdir = os.path.join(IMG, 'w')
    for f in sorted(os.listdir(wdir)):
        if f.endswith('.png'):
            with Image.open(os.path.join(wdir, f)) as im:
                wide[f[:-4]] = im.size[0]
    js = os.path.join(ROOT, 'src', 'common', 'assets.js')
    with open(js, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write('/* generated by tools/build_assets.py — do not edit */\n')
        fh.write('export const BG = %s;\n' % json.dumps(bgs, ensure_ascii=False))
        fh.write('export const CG = %s;\n' % json.dumps(cgs, ensure_ascii=False))
        fh.write('export const SPRITES = %s;\n' % json.dumps(sprites, ensure_ascii=False))
        fh.write('export const CG_WIDE = %s;\n' % json.dumps(wide, ensure_ascii=False))
        fh.write('''
export function bgPath(id) { return '/common/img/b/' + id + '.png' }
export function cgPath(id) { return '/common/img/w/' + id + '.png' }
export function cgThumb(id) { return '/common/img/t/' + id + '.png' }
export function cgWide(id) { return '/common/img/w/' + id + '.png' }
export function spritePath(tag, file) { return '/common/img/s/' + tag + '/' + file }
export function hasSprite(tag, file) {
  return !!(SPRITES[tag] && SPRITES[tag].indexOf(file) >= 0)
}
''')


def main():
    os.makedirs(IMG, exist_ok=True)
    for sub in ('b', 's', 't', 'w'):
        shutil.rmtree(os.path.join(IMG, sub), ignore_errors=True)
        os.makedirs(os.path.join(IMG, sub), exist_ok=True)

    # Only ship backgrounds the story actually uses (plus the title art), otherwise
    # ~28 unused 672x480 panoramas would add two megabytes to the package.
    used = set(['black', 'white', 'stage_lighton', 'stage_lightoff_changxia',
                'classroom_noon', 'coffee_afternoon'])
    story_dir = os.path.join(ROOT, 'src', 'common', 'story')
    if os.path.isdir(story_dir):
        for fn in os.listdir(story_dir):
            if fn.startswith('chunk-'):
                for line in open(os.path.join(story_dir, fn), encoding='utf-8').read().splitlines():
                    parts = line.split('\t')
                    if parts[0] == 'b':
                        used.add(parts[1])

    src_bg = os.path.join(SRC, '背景')
    for fn in sorted(os.listdir(src_bg)):
        if not fn.lower().endswith(('.webp', '.png', '.jpg', '.jpeg')):
            continue
        ident = CN_BG.get(fn.rsplit('.', 1)[0], fn.rsplit('.', 1)[0])
        if ident not in used:
            continue
        save_bg(os.path.join(src_bg, fn), os.path.join(IMG, 'b', ident + '.png'))

    for tag, folder in CHARS.items():
        n = build_char(tag, folder)
        print('%-12s faces=%d' % (tag, n))
    build_shopkeeper()
    build_cg()
    build_ui()
    build_theme()
    build_title()
    write_manifest()
    # 立绘/背景一变，模拟器用的 bundle 也得跟着重打包，否则会和页面里的元数据对不上
    try:
        import build_sim
        build_sim.main()
    except Exception as exc:            # noqa: BLE001
        print('sim rebuild skipped:', exc)

    total = 0
    for dp, _, fs in os.walk(IMG):
        for f in fs:
            total += os.path.getsize(os.path.join(dp, f))
    print('images: %.2f MB' % (total / 1048576))


if __name__ == '__main__':
    main()
