"""취향저장소 커넥트 숏폼 렌더러(스크랩북 카드 + 손그림 + 스티커). 무음 영상 출력, 음원은 mux.py 로 합성.
사용법: python3 make_card.py spec.json out.mp4 [미리보기초 ...]
scene kind: p(세로 전면) / card(가로 사진 폴라로이드) / doodle(손그림 전면)
{중괄호} 글자는 포인트색. 스티커: "st": ["헐!!", x, y, 각도, "#FF6B6B"]"""
import json, math, re, subprocess, sys, os
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

SPEC = json.load(open(sys.argv[1], encoding='utf-8'))
OUT = sys.argv[2]; PREVIEW = sys.argv[3:]
HERE = os.path.dirname(os.path.abspath(__file__))
DOH = SPEC.get('font', f'{HERE}/DoHyeon-Regular.ttf')
JUA = SPEC.get('font_sticker', f'{HERE}/Jua-Regular.ttf')
NOTO = SPEC.get('font_small', f'{HERE}/NotoSansKR-Bold.otf')
FFMPEG = SPEC.get('ffmpeg', 'ffmpeg')
W, H, FPS = 1080, 1920, 30
HOOK_D, SCENE_D, END_D = 2.5, 1.5, 3.5
WHITE = (255, 255, 255, 255); POINT = (255, 197, 61, 255)
OUTL = (36, 36, 36, 255); BOX = (255, 107, 107, 255)
ROOT = os.path.dirname(os.path.abspath(sys.argv[1]))

def hexc(s, a=255):
    s = s.lstrip('#'); return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16), a)

_fc = {}
def font(path, size):
    k = (path, size)
    if k not in _fc:
        _fc[k] = ImageFont.truetype(path, size, index=0) if path.endswith('ttc') else ImageFont.truetype(path, size)
    return _fc[k]

def segs(text, base=WHITE):
    return [(p, POINT if i % 2 else base) for i, p in enumerate(re.split(r'[{}]', text)) if p]

def text_layer(text, size, fpath=DOH, stroke=None, base=WHITE, ol=OUTL):
    sg = segs(text, base); f = font(fpath, size)
    sw = stroke if stroke is not None else max(4, int(size * 0.085))
    widths = [f.getlength(t) for t, _ in sg]; asc, desc = f.getmetrics(); pad = 30
    im = Image.new('RGBA', (int(sum(widths)) + 2 * sw + 20 + 2 * pad, asc + desc + 2 * sw + 20 + 2 * pad), (0, 0, 0, 0))
    sh = Image.new('RGBA', im.size, (0, 0, 0, 0)); d = ImageDraw.Draw(sh); x = pad + sw + 10
    for (t, c), w in zip(sg, widths):
        d.text((x + 6, pad + sw + 16), t, font=f, fill=(0, 0, 0, 140), stroke_width=sw, stroke_fill=(0, 0, 0, 140)); x += w
    im = Image.alpha_composite(im, sh.filter(ImageFilter.GaussianBlur(7)))
    d = ImageDraw.Draw(im); x = pad + sw + 10
    for (t, c), w in zip(sg, widths):
        d.text((x, pad + sw + 10), t, font=f, fill=c, stroke_width=sw, stroke_fill=ol); x += w
    return im.crop(im.getbbox())

def fit_layer(text, size, maxw=990, **kw):
    lay = text_layer(text, size, **kw)
    while lay.width > maxw and size > 40:
        size = int(size * 0.92); lay = text_layer(text, size, **kw)
    return lay

def pill(text, size, bg, fg=WHITE, fpath=NOTO, padx=34, pady=16, angle=0):
    f = font(fpath, size); l, t, r, b = f.getbbox(text)
    w, h = int(r - l) + 2 * padx, int(b - t) + 2 * pady
    im = Image.new('RGBA', (w + 20, h + 20), (0, 0, 0, 0))
    sh = Image.new('RGBA', im.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle((6, 10, w + 6, h + 10), radius=h // 2, fill=(0, 0, 0, 100))
    im = Image.alpha_composite(im, sh.filter(ImageFilter.GaussianBlur(6)))
    d = ImageDraw.Draw(im); d.rounded_rectangle((0, 0, w, h), radius=h // 2, fill=bg)
    d.text((padx - l, pady - t), text, font=f, fill=fg)
    return im.rotate(angle, expand=True, resample=Image.BICUBIC) if angle else im

def sticker(text, color, angle, size=96):
    f = font(JUA, size); sw = 10
    l, t, r, b = f.getbbox(text, stroke_width=sw)
    im = Image.new('RGBA', (r - l + 40, b - t + 40), (0, 0, 0, 0))
    sh = Image.new('RGBA', im.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).text((20 - l + 5, 20 - t + 8), text, font=f, fill=(0, 0, 0, 120), stroke_width=sw, stroke_fill=(0, 0, 0, 120))
    im = Image.alpha_composite(im, sh.filter(ImageFilter.GaussianBlur(5)))
    ImageDraw.Draw(im).text((20 - l, 20 - t), text, font=f, fill=hexc(color), stroke_width=sw, stroke_fill=WHITE)
    return im.rotate(angle, expand=True, resample=Image.BICUBIC)

def ease_out_back(x, s=1.9):
    x = min(max(x, 0), 1) - 1
    return 1 + (s + 1) * x ** 3 + s * x ** 2

def load(path):
    return Image.open(os.path.join(ROOT, path)).convert('RGB')

def cover(im, z=1.0):
    s = max(W / im.width, H / im.height) * z
    return im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)

def pop(im):
    return ImageEnhance.Brightness(ImageEnhance.Color(ImageEnhance.Contrast(im).enhance(1.05)).enhance(1.15)).enhance(1.04)

def make_card(im, angle, cw=930):
    s = cw / im.width; ph = int(im.height * s)
    if ph > 760:  # 너무 세로로 길면 위아래 잘라서 카드 비율 유지
        im = im.crop((0, int((im.height - 760 / s) / 2), im.width, int((im.height + 760 / s) / 2))); ph = 760
    photo = pop(im.resize((cw, ph), Image.LANCZOS))
    bw, bb = 22, 26
    card = Image.new('RGBA', (cw + 2 * bw, ph + bw + bb), (255, 255, 252, 255))
    card.paste(photo, (bw, bw))
    d = ImageDraw.Draw(card)
    for (x, y, a) in [(60, -6, -8), (cw - 120, -6, 7)]:  # 마스킹테이프
        tape = Image.new('RGBA', (200, 58), (255, 236, 170, 200))
        card.alpha_composite(tape.rotate(a, expand=True), (max(0, x), 0))
    pad = 40
    big = Image.new('RGBA', (card.width + 2 * pad, card.height + 2 * pad), (0, 0, 0, 0))
    sh = Image.new('RGBA', big.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rectangle((pad + 8, pad + 16, pad + card.width + 8, pad + card.height + 16), fill=(0, 0, 0, 120))
    big = Image.alpha_composite(big, sh.filter(ImageFilter.GaussianBlur(14)))
    big.alpha_composite(card, (pad, pad))
    return big.rotate(angle, expand=True, resample=Image.BICUBIC)

def soft_bg(im):
    b = cover(im, 1.15).filter(ImageFilter.GaussianBlur(22))
    b = ImageEnhance.Brightness(ImageEnhance.Color(b).enhance(1.2)).enhance(1.05)
    return Image.blend(b, Image.new('RGB', b.size, (255, 248, 236)), 0.18)

def make_shade(center_y, band, strength, top=90, bottom=120):
    y = np.arange(H)[:, None].astype(np.float32)
    a = np.clip((330 - y) / 330, 0, 1) * top + np.clip((y - 1500) / 420, 0, 1) * bottom + np.exp(-((y - center_y) / band) ** 2) * strength
    a = np.broadcast_to(np.clip(a, 0, 255), (H, W)).astype(np.uint8)
    sh = Image.new('RGBA', (W, H), (0, 0, 0, 255)); sh.putalpha(Image.fromarray(a)); return sh
SHADE_P = make_shade(880, 380, SPEC.get('shade', 70))
SHADE_CARD = make_shade(1250, 200, 25, top=60, bottom=90)
SHADE_END = make_shade(930, 700, 140)

AD = pill(SPEC.get('ad_label', '광고 · 제휴링크 포함'), 30, (0, 0, 0, 130), padx=22, pady=10)
DISC = text_layer(SPEC['disclaimer'], 29, fpath=NOTO, stroke=3, base=(255, 255, 255, 240)) if SPEC.get('disclaimer') else None

hk = SPEC['hook']; en = SPEC['end']
S = [dict(hk, hook=True, kind=hk.get('kind', 'card'))]
for sc in SPEC['scenes']: S.append(dict(sc))
S.append(dict(en, kind='end'))
t = 0.0
for i, s in enumerate(S):
    d = HOOK_D if s.get('hook') else END_D if s['kind'] == 'end' else SCENE_D
    s['t0'], s['t1'] = t, t + d; t += d
    s.setdefault('cx', 0.5); s.setdefault('cy', 0.5)
TOTAL = t
for i, s in enumerate(S):
    src = load(s['img'])
    if s['kind'] == 'card':
        s['bg'] = soft_bg(src); s['card'] = make_card(src, s.get('tilt', [-2.2, 1.8, -1.4, 2.4][i % 4]))
    elif s['kind'] == 'doodle':
        s['im'] = cover(src, 1.0)
    else:
        s['im'] = pop(cover(src, 1.0))
    if 'l2' in s and not s.get('hook') and s['kind'] != 'end':
        s['L1'] = fit_layer(s['l1'], 88); s['L2'] = fit_layer(s['l2'], 132)
    if s.get('st'):
        txt, x, y, ang, col = s['st']; s['ST'] = (sticker(txt, col, ang), x, y)
eb = cover(load(en['img']), 1.1).filter(ImageFilter.GaussianBlur(14))
END_BG = ImageEnhance.Brightness(eb).enhance(0.92)

H_PILL = pill(hk['pill'], 56, BOX, angle=-2)
H_L1 = fit_layer(hk['l1'], 100)
H_L2 = fit_layer('{' + hk['price'] + '}', 210, maxw=1010)
H_L3 = fit_layer(hk.get('l3', '코스 정리') + ' {↓}', 74)
E_PILL = pill(en['pill'], 52, BOX)
E_L1 = fit_layer(en.get('price_label', '1인 ') + '{' + en['price'] + '}', 146)
E_L2 = fit_layer(en['l2'], 74)
E_SMALL = [text_layer(x, 34, fpath=NOTO, stroke=3, base=(255, 255, 255, 245)) for x in en.get('small', [])]
E_CTA = pill(en.get('cta', '링크에서 일정 보기 ↑'), 62, (255, 255, 255, 255), fg=OUTL, fpath=DOH, padx=44, pady=22)

def place(frame, layer, cx, cy, tr, appear, dur=0.16, from_scale=0.55, slam=False, wob=0.0):
    if tr < appear: return
    u = (tr - appear) / dur
    if u >= 1: sc, al = 1.0, 1.0
    else:
        sc = from_scale + (1 - from_scale) * ((1 - (1 - u) ** 3) if slam else ease_out_back(u)); al = min(1.0, u * 2.2)
    if wob: sc *= 1 + wob * math.sin((tr - appear) * 2 * math.pi * 2.0)
    lay = layer
    if abs(sc - 1) > 0.003:
        lay = layer.resize((max(1, int(layer.width * sc)), max(1, int(layer.height * sc))), Image.BILINEAR)
    if al < 1:
        lay = lay.copy(); lay.putalpha(lay.getchannel('A').point(lambda v: int(v * al)))
    frame.alpha_composite(lay, (int(cx - lay.width / 2), int(cy - lay.height / 2)))

def crop_view(im, cx, cy, z, extra=(0, 0)):
    vw, vh = W / z, H / z
    x = cx * im.width + extra[0] / z; y = cy * im.height + extra[1] / z
    x0 = min(max(x - vw / 2, 0), im.width - vw); y0 = min(max(y - vh / 2, 0), im.height - vh)
    return im.resize((W, H), Image.BILINEAR, box=(x0, y0, x0 + vw, y0 + vh)).convert('RGBA')

def render(t):
    s = next((x for x in S if x['t0'] <= t < x['t1']), S[-1]); tr = t - s['t0']; u = tr / (s['t1'] - s['t0'])
    shake = (0, 0)
    if s.get('hook') and 0.5 <= tr < 0.85:
        k = math.exp(-(tr - 0.5) / 0.09); shake = (24 * k * math.sin(tr * 95), 18 * k * math.cos(tr * 120))
    punch = 0.14 * math.exp(-tr / 0.07)
    kind = s['kind']
    if kind == 'end':
        f = crop_view(END_BG, s['cx'], s['cy'], 1.0 + 0.03 * u); f.alpha_composite(SHADE_END)
        place(f, E_PILL, W / 2, 590, tr, 0.0); place(f, E_L1, W / 2, 745, tr, 0.20, slam=True, from_scale=1.6)
        place(f, E_L2, W / 2, 885, tr, 0.40)
        for i, lay in enumerate(E_SMALL): place(f, lay, W / 2, 985 + i * 54, tr, 0.60, from_scale=0.9)
        cta_y = 985 + len(E_SMALL) * 54 + 110
        if tr >= 0.85:
            p = 1 + 0.05 * math.sin((tr - 0.85) * 2 * math.pi * 1.6)
            lay = E_CTA.resize((int(E_CTA.width * p), int(E_CTA.height * p)), Image.BILINEAR) if tr > 1.05 else E_CTA
            place(f, lay, W / 2, cta_y, tr, 0.85)
        f.alpha_composite(AD, (48, 210)); return f.convert('RGB')
    if kind == 'card':
        f = crop_view(s['bg'], 0.5 + 0.03 * math.sin(t * 0.7), 0.5, 1.0 + 0.04 * u, shake)
        f.alpha_composite(SHADE_CARD)
        cy_card = s.get('card_y', 1010 if s.get('hook') else 690)
        z = 1.0 + 0.035 * u + punch * 0.6
        c = s['card']; c2 = c.resize((int(c.width * z), int(c.height * z)), Image.BILINEAR)
        f.alpha_composite(c2, (int(W / 2 - c2.width / 2 + shake[0]), int(cy_card - c2.height / 2 + shake[1])))
    else:
        z = (1.0 if kind == 'doodle' else 1.03) + 0.05 * u + punch
        f = crop_view(s['im'], s['cx'], s['cy'], z, shake)
        if kind != 'doodle': f.alpha_composite(SHADE_P)
    if s.get('hook'):
        place(f, H_PILL, W / 2, 470, tr, 0.0); place(f, H_L1, W / 2, 600, tr, 0.12)
        place(f, H_L2, W / 2, 790, tr, 0.50, dur=0.13, from_scale=1.9, slam=True, wob=0.025 if tr > 0.7 else 0)
        place(f, H_L3, W / 2, s.get('l3_y', 1450), tr, 1.15)
        if 0.5 <= tr < 0.75: f.alpha_composite(Image.new('RGBA', (W, H), (255, 255, 255, int(190 * math.exp(-(tr - 0.5) / 0.05)))))
    elif 'L1' in s:
        ty = s.get('ty', 1170 if kind == 'card' else 800)
        l1, l2 = s['L1'], s['L2']
        place(f, l1, W / 2, ty, tr, 0.04); place(f, l2, W / 2, ty + l1.height / 2 + l2.height / 2 + 4, tr, 0.39)
    if s.get('ST'):
        lay, x, y = s['ST']; place(f, lay, x, y, tr, 0.72 if not s.get('hook') else 0.9, wob=0.07)
    if DISC and kind != 'doodle': f.alpha_composite(DISC, (int(W / 2 - DISC.width / 2), 1620))
    f.alpha_composite(AD, (48, 210))
    return f.convert('RGB')

if PREVIEW:
    for ts in PREVIEW: render(float(ts)).save(f'{OUT}_{ts}.jpg', quality=85)
    sys.exit()
cmd = [FFMPEG, '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
       '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', OUT]
p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
for i in range(int(round(TOTAL * FPS))): p.stdin.write(render(i / FPS).tobytes())
p.stdin.close(); p.wait(); print('done', OUT, f'{TOTAL:.1f}s')
