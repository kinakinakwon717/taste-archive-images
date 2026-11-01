"""취향저장소 숏폼 렌더러. 사용법: python3 make_short.py spec.json out.mp4 [미리보기초 ...]
spec 텍스트에서 {중괄호} 안 글자는 포인트색(#FFC53D)으로 칠해짐."""
import json, math, re, subprocess, sys, os
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

SPEC = json.load(open(sys.argv[1], encoding='utf-8'))
OUT = sys.argv[2]
PREVIEW = sys.argv[3:]
DOH = SPEC.get('font', 'DoHyeon-Regular.ttf')
NOTO = SPEC.get('font_small', '/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc')
W, H, FPS = 1080, 1920, 30
HOOK_D, SCENE_D, END_D = 2.5, 1.5, 3.5
WHITE = (255, 255, 255, 255); POINT = (255, 197, 61, 255)
OUTL = (36, 36, 36, 255); BOX = (255, 107, 107, 255)

_fc = {}
def font(path, size):
    k = (path, size)
    if k not in _fc:
        _fc[k] = ImageFont.truetype(path, size, index=0) if path.endswith('ttc') else ImageFont.truetype(path, size)
    return _fc[k]

def segs(text, base=WHITE):
    out = []
    for i, part in enumerate(re.split(r'[{}]', text)):
        if part:
            out.append((part, POINT if i % 2 else base))
    return out

def text_layer(text, size, fpath=DOH, stroke=None, base=WHITE):
    sg = segs(text, base)
    f = font(fpath, size)
    sw = stroke if stroke is not None else max(4, int(size * 0.085))
    widths = [f.getlength(t) for t, _ in sg]
    asc, desc = f.getmetrics()
    pad = 30
    im = Image.new('RGBA', (int(sum(widths)) + 2 * sw + 20 + 2 * pad, asc + desc + 2 * sw + 20 + 2 * pad), (0, 0, 0, 0))
    sh = Image.new('RGBA', im.size, (0, 0, 0, 0)); d = ImageDraw.Draw(sh); x = pad + sw + 10
    for (t, c), w in zip(sg, widths):
        d.text((x + 6, pad + sw + 18), t, font=f, fill=(0, 0, 0, 150), stroke_width=sw, stroke_fill=(0, 0, 0, 150)); x += w
    im = Image.alpha_composite(im, sh.filter(ImageFilter.GaussianBlur(8)))
    d = ImageDraw.Draw(im); x = pad + sw + 10
    for (t, c), w in zip(sg, widths):
        d.text((x, pad + sw + 10), t, font=f, fill=c, stroke_width=sw, stroke_fill=OUTL); x += w
    return im.crop(im.getbbox())

def fit_layer(text, size, maxw=980, **kw):
    lay = text_layer(text, size, **kw)
    while lay.width > maxw and size > 40:
        size = int(size * 0.92); lay = text_layer(text, size, **kw)
    return lay

def pill(text, size, bg, fg=WHITE, fpath=NOTO, padx=34, pady=16):
    f = font(fpath, size); l, t, r, b = f.getbbox(text)
    w, h = int(r - l) + 2 * padx, int(b - t) + 2 * pady
    im = Image.new('RGBA', (w + 20, h + 20), (0, 0, 0, 0))
    sh = Image.new('RGBA', im.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle((6, 10, w + 6, h + 10), radius=h // 2, fill=(0, 0, 0, 110))
    im = Image.alpha_composite(im, sh.filter(ImageFilter.GaussianBlur(6)))
    d = ImageDraw.Draw(im); d.rounded_rectangle((0, 0, w, h), radius=h // 2, fill=bg)
    d.text((padx - l, pady - t), text, font=f, fill=fg)
    return im

def ease_out_back(x, s=1.9):
    x = min(max(x, 0), 1) - 1
    return 1 + (s + 1) * x ** 3 + s * x ** 2

def prep(path):
    im = Image.open(path).convert('RGB')
    s = max(W / im.width, H / im.height)
    im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    return ImageEnhance.Color(ImageEnhance.Contrast(im).enhance(1.06)).enhance(1.12)

def make_shade(center_y=900, band=520, strength=110):
    y = np.arange(H)[:, None].astype(np.float32)
    a = np.clip((380 - y) / 380, 0, 1) * 120 + np.clip((y - 1420) / 500, 0, 1) * 150 + np.exp(-((y - center_y) / band) ** 2) * strength
    a = np.broadcast_to(np.clip(a, 0, 255), (H, W)).astype(np.uint8)
    sh = Image.new('RGBA', (W, H), (0, 0, 0, 255)); sh.putalpha(Image.fromarray(a)); return sh
SHADE = make_shade(); SHADE_END = make_shade(930, 700, 170)

AD = pill(SPEC.get('ad_label', '광고 · 제휴링크 포함'), 30, (0, 0, 0, 130), padx=22, pady=10)
DISC = text_layer(SPEC['disclaimer'], 31, fpath=NOTO, stroke=3, base=(255, 255, 255, 235)) if SPEC.get('disclaimer') else None

# ---- timeline ----
hk = SPEC['hook']; en = SPEC['end']
S = [dict(img=hk['img'], kind=hk.get('kind', 'p'), cx=hk.get('cx', 0.5), cy=hk.get('cy', 0.5), pan=hk.get('pan'), hook=True)]
for sc in SPEC['scenes']:
    S.append(dict(img=sc['img'], kind=sc.get('kind', 'p'), cx=sc.get('cx', 0.5), cy=sc.get('cy', 0.5), pan=sc.get('pan'),
                  dark=sc.get('dark', False), l1=sc['l1'], l2=sc['l2']))
S.append(dict(img=en['img'], kind='end', cx=en.get('cx', 0.5), cy=en.get('cy', 0.5)))
t = 0.0
for s in S:
    d = HOOK_D if s.get('hook') else END_D if s['kind'] == 'end' else SCENE_D
    s['t0'], s['t1'] = t, t + d; t += d
TOTAL = t
CUTS = [s['t0'] for s in S[1:]]
for s in S:
    s['im'] = prep(s['img'])
    if s['kind'] == 'l' and not s.get('pan'):
        s['pan'] = (0.4, 0.6)
    if 'l1' in s:
        s['L1'] = fit_layer(s['l1'], 92); s['L2'] = fit_layer(s['l2'], 140)
END_BG = S[-1]['im'].filter(ImageFilter.GaussianBlur(10))

H_PILL = pill(hk['pill'], 58, BOX)
H_L1 = fit_layer(hk['l1'], 104)
H_L2 = fit_layer('{' + hk['price'] + '}', 220, maxw=1000)
H_L3 = fit_layer(hk.get('l3', '코스 정리') + ' {↓}', 76)
E_PILL = pill(en['pill'], 58, BOX)
E_L1 = fit_layer(en.get('price_label', '1인 ') + '{' + en['price'] + '}', 150)
E_L2 = fit_layer(en['l2'], 78)
E_SMALL = [text_layer(x, 36, fpath=NOTO, stroke=3, base=(255, 255, 255, 240)) for x in en.get('small', [])]
E_CTA = pill(en.get('cta', '프로필 링크에서 일정 보기 ↑'), 64, (255, 255, 255, 255), fg=OUTL, fpath=DOH, padx=44, pady=22)

def place(frame, layer, cx, cy, tr, appear, dur=0.16, from_scale=0.55, slam=False):
    if tr < appear: return
    u = (tr - appear) / dur
    if u >= 1: sc, al = 1.0, 1.0
    else:
        sc = from_scale + (1 - from_scale) * ((1 - (1 - u) ** 3) if slam else ease_out_back(u))
        al = min(1.0, u * 2.2)
    lay = layer
    if abs(sc - 1) > 0.003:
        lay = layer.resize((max(1, int(layer.width * sc)), max(1, int(layer.height * sc))), Image.BILINEAR)
    if al < 1:
        lay = lay.copy(); lay.putalpha(lay.getchannel('A').point(lambda v: int(v * al)))
    frame.alpha_composite(lay, (int(cx - lay.width / 2), int(cy - lay.height / 2)))

def bg_frame(s, tr, extra=(0, 0)):
    im = s['im']; u = tr / (s['t1'] - s['t0'])
    punch = 0.16 * math.exp(-tr / 0.07)
    if s['kind'] == 'l':
        z = 1.0 + 0.04 * u + punch; a, b = s['pan']; e = 0.5 - 0.5 * math.cos(math.pi * u)
        cx = (a + (b - a) * e) * im.width
    else:
        z = 1.04 + 0.07 * u + punch; cx = s['cx'] * im.width
    cy = s['cy'] * im.height
    vw, vh = W / z, H / z
    cx += extra[0] / z; cy += extra[1] / z
    x0 = min(max(cx - vw / 2, 0), im.width - vw); y0 = min(max(cy - vh / 2, 0), im.height - vh)
    src = END_BG if s['kind'] == 'end' else im
    return src.resize((W, H), Image.BILINEAR, box=(x0, y0, x0 + vw, y0 + vh)).convert('RGBA')

def render(t):
    s = next((x for x in S if x['t0'] <= t < x['t1']), S[-1]); tr = t - s['t0']
    shake = (0, 0)
    if s.get('hook') and 0.5 <= tr < 0.85:
        k = math.exp(-(tr - 0.5) / 0.09); shake = (22 * k * math.sin(tr * 95), 16 * k * math.cos(tr * 120))
    f = bg_frame(s, tr, shake)
    if s['kind'] == 'end':
        f.alpha_composite(SHADE_END)
        place(f, E_PILL, W / 2, 600, tr, 0.0); place(f, E_L1, W / 2, 760, tr, 0.20); place(f, E_L2, W / 2, 900, tr, 0.40)
        for i, lay in enumerate(E_SMALL):
            place(f, lay, W / 2, 1000 + i * 52, tr, 0.60, from_scale=0.9)
        cta_y = 1000 + len(E_SMALL) * 52 + 120
        if tr >= 0.85:
            p = 1 + 0.05 * math.sin((tr - 0.85) * 2 * math.pi * 1.6)
            lay = E_CTA.resize((int(E_CTA.width * p), int(E_CTA.height * p)), Image.BILINEAR) if tr > 1.05 else E_CTA
            place(f, lay, W / 2, cta_y, tr, 0.85)
    else:
        f.alpha_composite(SHADE)
        if s.get('dark'): f.alpha_composite(SHADE)
        if s.get('hook'):
            place(f, H_PILL, W / 2, 560, tr, 0.0); place(f, H_L1, W / 2, 690, tr, 0.12)
            place(f, H_L2, W / 2, 875, tr, 0.50, dur=0.13, from_scale=1.9, slam=True); place(f, H_L3, W / 2, 1065, tr, 1.15)
            if 0.5 <= tr < 0.75:
                f.alpha_composite(Image.new('RGBA', (W, H), (255, 255, 255, int(190 * math.exp(-(tr - 0.5) / 0.05)))))
        else:
            l1, l2 = s['L1'], s['L2']
            place(f, l1, W / 2, 790, tr, 0.04); place(f, l2, W / 2, 790 + l1.height / 2 + l2.height / 2 + 6, tr, 0.39)
        if DISC: f.alpha_composite(DISC, (int(W / 2 - DISC.width / 2), 1395))
    f.alpha_composite(AD, (48, 210))
    return f.convert('RGB')

if PREVIEW:
    for ts in PREVIEW: render(float(ts)).save(f'{OUT}_{ts}.jpg', quality=85)
    sys.exit()

# ---- music ----
here = os.path.dirname(os.path.abspath(__file__))
wav = OUT + '.bgm.wav'
subprocess.run([sys.executable, os.path.join(here, 'music.py'), wav, str(TOTAL), ','.join(f'{c:.2f}' for c in CUTS),
                str(SPEC.get('music_seed', 7))], check=True)
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', wav, '-af', 'loudnorm=I=-15:TP=-1.5:LRA=11', '-ar', '44100', wav + '.n.wav'], check=True)
cmd = ['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
       '-i', wav + '.n.wav', '-map', '0:v', '-map', '1:a', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20',
       '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k', '-shortest', '-movflags', '+faststart', OUT]
p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
for i in range(int(round(TOTAL * FPS))):
    p.stdin.write(render(i / FPS).tobytes())
p.stdin.close(); p.wait()
print('done', OUT, f'{TOTAL:.1f}s')
