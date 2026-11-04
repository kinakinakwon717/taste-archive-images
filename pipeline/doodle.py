"""밤티 2D 손그림 컷 생성기. python3 doodle.py <종류> out.png"""
import sys, math, random
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np
HERE = __file__.rsplit('/', 1)[0] if '/' in __file__ else '.'
PEN = f'{HERE}/NanumPenScript-Regular.ttf'
W, H = 1080, 1920
INK = (34, 30, 28)
random.seed(int(sys.argv[3]) if len(sys.argv) > 3 else 3)

def paper(color=(255, 251, 238)):
    im = Image.new('RGB', (W, H), color)
    n = np.random.default_rng(1).normal(0, 6, (H // 4, W // 4))
    t = Image.fromarray(np.clip(128 + n, 0, 255).astype('uint8')).resize((W, H), Image.BICUBIC).convert('RGB')
    im = Image.blend(im, t, 0.05)
    d = ImageDraw.Draw(im)
    for y in range(140, H, 86):  # 공책 줄
        d.line([(0, y), (W, y + random.randint(-2, 2))], fill=(190, 214, 235), width=3)
    d.line([(120, 0), (118, H)], fill=(240, 160, 160), width=4)
    return im

def wob(pts, amp=5, steps=14):
    out = []
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        for i in range(steps):
            t = i / steps
            out.append((x0 + (x1 - x0) * t + random.uniform(-amp, amp), y0 + (y1 - y0) * t + random.uniform(-amp, amp)))
    out.append(pts[-1]); return out

def line(d, pts, w=9, c=INK, amp=4):
    p = wob(pts, amp)
    d.line(p, fill=c, width=w, joint='curve')
    for q in (p[0], p[-1]): d.ellipse((q[0] - w / 2, q[1] - w / 2, q[0] + w / 2, q[1] + w / 2), fill=c)

def circle(d, cx, cy, r, w=9, fill=None, c=INK):
    pts = [(cx + (r + random.uniform(-6, 6)) * math.cos(a), cy + (r + random.uniform(-6, 6)) * math.sin(a))
           for a in np.linspace(0, 2 * math.pi * 1.06, 40)]
    if fill: d.polygon(pts, fill=fill)
    d.line(pts, fill=c, width=w, joint='curve')

def rect(d, x0, y0, x1, y1, fill=None, w=9):
    if fill: d.polygon([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], fill=fill)
    line(d, [(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)], w)

def text(d, xy, s, size, c=INK, ang=0, im=None):
    f = ImageFont.truetype(PEN, size)
    if not ang:
        d.text(xy, s, font=f, fill=c); return
    l, t, r, b = f.getbbox(s)
    lay = Image.new('RGBA', (r + 20, b + 20), (0, 0, 0, 0)); ImageDraw.Draw(lay).text((10, 10), s, font=f, fill=c)
    lay = lay.rotate(ang, expand=True, resample=Image.BICUBIC); im.paste(lay, (int(xy[0]), int(xy[1])), lay)

def burnout():
    im = paper(); d = ImageDraw.Draw(im)
    # 책상
    line(d, [(60, 1260), (1020, 1250)], 12)
    line(d, [(140, 1255), (150, 1560)], 10); line(d, [(930, 1252), (920, 1560)], 10)
    # 모니터
    rect(d, 560, 720, 960, 1010, fill=(205, 228, 245))
    for i in range(5): line(d, [(600, 770 + i * 45), (600 + random.randint(180, 320), 772 + i * 45)], 6, (90, 110, 140), 2)
    line(d, [(760, 1010), (760, 1110)], 10); line(d, [(680, 1115), (840, 1112)], 10)
    text(d, (612, 935), '결재 반려', 54, (220, 50, 50))
    # 엎드린 사람: 몸통 + 팔
    d.polygon(wob([(180, 1250), (240, 1080), (470, 1060), (520, 1250)], 3), fill=(120, 160, 220))
    line(d, [(180, 1250), (240, 1080), (470, 1060), (520, 1250)], 9)
    circle(d, 330, 1080, 110, fill=(255, 224, 196))   # 머리(책상에 엎드림)
    for k in range(3):  # 머리카락 몇 가닥
        line(d, [(260 + k * 50, 985), (250 + k * 55, 950)], 7)
    # 눈 X X, 입 물결
    line(d, [(270, 1050), (300, 1080)], 7); line(d, [(300, 1050), (270, 1080)], 7)
    line(d, [(360, 1050), (390, 1080)], 7); line(d, [(390, 1050), (360, 1080)], 7)
    line(d, [(290, 1135), (315, 1122), (340, 1138), (365, 1124)], 6, amp=1)
    # 영혼 빠져나가는 중
    soul = [(330, 960), (300, 860), (360, 760), (320, 660)]
    line(d, soul, 6, (150, 170, 200), amp=8)
    circle(d, 330, 600, 60, w=6, fill=(235, 240, 250), c=(150, 170, 200))
    text(d, (230, 470), '영혼 퇴근 중', 66, (120, 140, 180), ang=8, im=im)
    # 땀, 커피
    for (x, y) in [(460, 990), (490, 1040), (200, 1010)]:
        d.polygon(wob([(x, y), (x - 14, y + 34), (x + 14, y + 34), (x, y)], 1), fill=(120, 190, 240))
    rect(d, 880, 1150, 950, 1245, fill=(250, 250, 250)); line(d, [(950, 1170), (985, 1190), (950, 1225)], 7)
    text(d, (880, 1080), '5잔째', 50, ang=-6, im=im)
    text(d, (170, 320), '월요일 9시 1분', 92, ang=3, im=im)
    return im

def shopping():
    im = paper(); d = ImageDraw.Draw(im)
    rect(d, 520, 700, 990, 1300, fill=(255, 238, 205))
    text(d, (585, 735), '쇼핑센터', 92, (200, 60, 60))
    line(d, [(600, 860), (900, 860)], 7)
    for i in range(3): rect(d, 580 + i * 135, 920, 680 + i * 135, 1030, fill=(255, 210, 120), w=6)
    # 끌려가는 사람
    circle(d, 300, 900, 75, fill=(255, 224, 196))
    line(d, [(300, 975), (330, 1180)], 9)
    line(d, [(315, 1020), (500, 980)], 9)                     # 끌려가는 팔
    line(d, [(330, 1180), (250, 1330)], 9); line(d, [(330, 1180), (420, 1310)], 9)
    line(d, [(270, 880), (290, 900)], 6); line(d, [(320, 880), (340, 900)], 6)
    for k in range(3):  # 눈물
        d.polygon(wob([(262, 910 + k * 40), (250, 940 + k * 40), (274, 940 + k * 40), (262, 910 + k * 40)], 1), fill=(120, 190, 240))
    # 손 끄는 화살표
    line(d, [(500, 980), (560, 960)], 9); line(d, [(530, 935), (560, 960), (535, 990)], 9)
    text(d, (120, 1380), '"잠깐 구경만 하세요~"', 84, ang=2, im=im)
    text(d, (200, 1500), '(3시간째)', 76, (200, 60, 60), ang=-3, im=im)
    text(d, (150, 330), '패키지 여행의 공포', 96, ang=2, im=im)
    return im

def chicken():
    im = paper(); d = ImageDraw.Draw(im)
    # 배
    d.polygon(wob([(130, 1330), (950, 1330), (860, 1510), (220, 1510)], 3), fill=(245, 245, 250))
    line(d, [(130, 1330), (950, 1330), (860, 1510), (220, 1510), (130, 1330)], 10)
    rect(d, 330, 1180, 760, 1330, fill=(200, 225, 250))
    for i in range(4): circle(d, 400 + i * 100, 1255, 26, w=6, fill=(255, 255, 255))
    line(d, [(560, 1180), (560, 1050)], 9); d.polygon(wob([(560, 1050), (680, 1080), (560, 1110)], 2), fill=(255, 107, 107))
    for x in range(60, 1040, 120):  # 파도
        line(d, [(x, 1570), (x + 30, 1545), (x + 60, 1570), (x + 90, 1545), (x + 120, 1570)], 8, (80, 150, 220), 2)
    text(d, (120, 1630), '부산항', 80, (60, 110, 180), ang=4, im=im)
    text(d, (690, 1630), '→ 대마도', 80, (60, 110, 180), ang=-3, im=im)
    # 놀란 사람 얼굴
    circle(d, 330, 640, 150, fill=(255, 224, 196))
    circle(d, 275, 610, 28, w=7, fill=(255, 255, 255)); circle(d, 385, 610, 28, w=7, fill=(255, 255, 255))
    d.ellipse((268, 603, 284, 619), fill=INK); d.ellipse((378, 603, 394, 619), fill=INK)
    circle(d, 330, 705, 34, w=8, fill=(120, 40, 40))
    for a in (-1, 0, 1):
        line(d, [(330 + a * 120, 440), (330 + a * 150, 380)], 9)
    text(d, (560, 520), '해외가', 110, ang=-4, im=im)
    text(d, (560, 650), '이 가격?', 110, (220, 50, 50), ang=3, im=im)
    text(d, (590, 330), '내 통장 표정', 90, ang=-2, im=im)
    return im


def boat():
    im = paper(); d = ImageDraw.Draw(im)
    # 물
    d.polygon([(0, 1050), (W, 1040), (W, 1560), (0, 1560)], fill=(170, 215, 225))
    for y in (1120, 1250, 1380, 1500):
        for x in range(40, 1040, 140): line(d, [(x, y), (x + 35, y - 18), (x + 70, y)], 6, (90, 150, 180), 2)
    # 아치 다리
    outer = [(80 + i * 46, 1040 - 260 * math.sin(math.pi * i / 20)) for i in range(21)]
    inner = [(200 + i * 34, 1040 - 170 * math.sin(math.pi * i / 20)) for i in range(21)]
    d.polygon(outer + inner[::-1], fill=(225, 220, 205))
    line(d, outer, 10); line(d, inner, 9)
    line(d, [(60, 760), (1020, 760)], 10)
    for x in range(120, 1000, 90): line(d, [(x, 760), (x + 4, 700)], 6)
    line(d, [(60, 700), (1020, 700)], 8)
    # 지붕 옛 집
    for bx in (60, 760):
        rect(d, bx, 470, bx + 260, 690, fill=(250, 245, 235))
        d.polygon(wob([(bx - 30, 480), (bx + 130, 390), (bx + 290, 480)], 3), fill=(80, 80, 90))
        rect(d, bx + 90, 560, bx + 170, 690, fill=(150, 90, 60), w=6)
    # 배 + 사람
    d.polygon(wob([(260, 1290), (820, 1290), (740, 1390), (330, 1390)], 3), fill=(160, 110, 70))
    line(d, [(260, 1290), (820, 1290), (740, 1390), (330, 1390), (260, 1290)], 9)
    d.polygon(wob([(420, 1290), (440, 1170), (660, 1170), (680, 1290)], 3), fill=(220, 70, 60))
    for i, x in enumerate((480, 560, 630)):
        circle(d, x, 1235, 30, w=6, fill=(255, 224, 196))
        line(d, [(x - 12, 1232), (x - 4, 1226)], 4); line(d, [(x + 4, 1226), (x + 12, 1232)], 4)
    circle(d, 790, 1150, 38, w=7, fill=(255, 224, 196))           # 노 젓는 아저씨
    d.polygon(wob([(740, 1120), (790, 1080), (840, 1120)], 2), fill=(230, 200, 90))
    line(d, [(790, 1190), (790, 1290)], 8); line(d, [(790, 1220), (860, 1180), (920, 1420)], 8)
    text(d, (560, 1420), '노 젓는 사장님', 60, ang=-3, im=im)
    out = paper(); out.paste(im.crop((0, 0, W, H - 170)), (0, 170))
    return out

KIND = {'boat': boat, 'burnout': burnout, 'shopping': shopping, 'chicken': chicken}
KIND[sys.argv[1]]().save(sys.argv[2], quality=92)
