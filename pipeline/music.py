import numpy as np
from scipy.signal import butter, sosfilt, fftconvolve
import wave, sys, math
# 사용법: python3 music.py out.wav 총길이초 컷시각들(쉼표) [seed]
SR = 44100
TOTAL = float(sys.argv[2]) if len(sys.argv) > 2 else 16.5
CUT_ARG = [float(x) for x in sys.argv[3].split(',')] if len(sys.argv) > 3 and sys.argv[3] else []
SEED = int(sys.argv[4]) if len(sys.argv) > 4 else 7
N = int(SR * TOTAL)
rng = np.random.default_rng(SEED)
TR = [0, 2, -3, 5, -2][SEED % 5]   # 영상마다 키를 조금씩 바꿈
BPM = 120
BEAT = 60 / BPM          # 0.5s
DROP = 0.5               # first downbeat
EIGHTH = BEAT / 2

def mtof(m): return 440.0 * 2 ** ((m - 69) / 12)
def bp(lo, hi, x, order=2):
    return sosfilt(butter(order, [lo, hi], btype='band', fs=SR, output='sos'), x)
def hp(f, x, order=2):
    return sosfilt(butter(order, f, btype='high', fs=SR, output='sos'), x)
def lp(f, x, order=2):
    return sosfilt(butter(order, f, btype='low', fs=SR, output='sos'), x)

def add(buf, sig, t, gain=1.0):
    i = int(round(t * SR))
    if i >= len(buf): return
    j = min(len(buf), i + len(sig))
    buf[i:j] += sig[:j - i] * gain

# ---------- instruments ----------
def kick():
    d = 0.42; t = np.arange(int(SR * d)) / SR
    f = 48 + 110 * np.exp(-t * 28)
    ph = 2 * np.pi * np.cumsum(f) / SR
    s = np.sin(ph) * np.exp(-t * 7.5)
    click = rng.standard_normal(len(t)) * np.exp(-t * 300) * 0.25
    return np.tanh((s + hp(2000, click)) * 1.6)

def clap():
    d = 0.3; n = int(SR * d); t = np.arange(n) / SR
    noise = rng.standard_normal(n)
    env = np.zeros(n)
    for k, off in enumerate([0, 0.011, 0.022]):
        i = int(off * SR); env[i:] += np.exp(-(t[:n - i]) * (90 if k < 2 else 16))
    return bp(900, 2600, noise * env) * 1.4

def hat(open_=False):
    d = 0.22 if open_ else 0.05; n = int(SR * d); t = np.arange(n) / SR
    s = hp(7000, rng.standard_normal(n)) * np.exp(-t * (14 if open_ else 70))
    return s

def ks_pluck(freq, dur, bright=0.5, decay=0.996):
    n = int(SR * dur); p = max(2, int(SR / freq))
    buf = rng.uniform(-1, 1, p)
    buf = lp(min(SR / 2 - 100, 1500 + 6000 * bright), buf, 1)
    out = np.zeros(n)
    cur = buf.copy()
    pos = 0
    while pos < n:
        m = min(p, n - pos)
        out[pos:pos + m] = cur[:m]
        nxt = decay * 0.5 * (cur + np.roll(cur, -1))
        cur = nxt
        pos += p
    t = np.arange(n) / SR
    rel = np.clip((dur - t) / 0.04, 0, 1)
    return out * rel

def marimba(freq, dur=0.9):
    n = int(SR * dur); t = np.arange(n) / SR
    s = (np.sin(2 * np.pi * freq * t) * np.exp(-t * 5)
         + 0.35 * np.sin(2 * np.pi * freq * 3.93 * t) * np.exp(-t * 16)
         + 0.12 * np.sin(2 * np.pi * freq * 9.2 * t) * np.exp(-t * 40))
    att = np.clip(t / 0.003, 0, 1)
    return s * att

def bass(freq, dur):
    n = int(SR * dur); t = np.arange(n) / SR
    s = np.sin(2 * np.pi * freq * t) + 0.25 * np.sin(2 * np.pi * freq * 2 * t)
    env = np.clip(t / 0.005, 0, 1) * np.exp(-t * 3.0) * np.clip((dur - t) / 0.02, 0, 1)
    return np.tanh(s * env * 1.4)

def bell(freq, dur=1.6):
    n = int(SR * dur); t = np.arange(n) / SR
    s = (np.sin(2 * np.pi * freq * t) + 0.5 * np.sin(2 * np.pi * freq * 2.76 * t) * np.exp(-t * 3)
         + 0.25 * np.sin(2 * np.pi * freq * 5.4 * t) * np.exp(-t * 6))
    return s * np.exp(-t * 2.2)

# ---------- buses ----------
drums = np.zeros(N); music = np.zeros(N); bassb = np.zeros(N); lead = np.zeros(N); fx = np.zeros(N)

# riser 0 -> 0.5 (noise swell + upward sweep)
n = int(SR * 0.5); t = np.arange(n) / SR
sw = rng.standard_normal(n)
sw = bp(1500, 9000, sw) * (t / 0.5) ** 2.2
tone = np.sin(2 * np.pi * np.cumsum(300 + 1500 * (t / 0.5) ** 2) / SR) * (t / 0.5) ** 2 * 0.25
add(fx, sw * 0.5 + tone, 0.0)

# impact at drop
crash_n = int(SR * 1.8); ct = np.arange(crash_n) / SR
crash = hp(4000, rng.standard_normal(crash_n)) * np.exp(-ct * 2.6)
add(fx, crash * 0.35, DROP)
sub_t = np.arange(int(SR * 0.9)) / SR
sub = np.sin(2 * np.pi * np.cumsum(70 - 35 * sub_t) / SR) * np.exp(-sub_t * 4)
add(fx, sub * 0.9, DROP)

# chords: G D Em C  (two passes)
G = [55, 59, 62, 67, 71]; D = [50, 57, 62, 66, 69]; Em = [52, 59, 64, 67, 71]; C = [48, 55, 60, 64, 67]
BAR = BEAT * 4
NB = max(2, math.ceil((TOTAL - DROP) / BAR))
prog = [[m + TR for m in [G, D, Em, C][b % 4]] for b in range(NB)]
roots = [[43, 38, 40, 36][b % 4] + TR for b in range(NB)]

for b in range(NB):
    t0 = DROP + b * BAR
    chord = prog[b]
    outro = (b == NB - 1)
    # drums
    if not outro:
        for k in range(4):
            add(drums, kick(), t0 + k * BEAT, 0.95)
            if k in (1, 3):
                add(drums, clap(), t0 + k * BEAT, 0.55)
        for e in range(8):
            add(drums, hat(open_=(e % 2 == 1 and e in (3, 7))), t0 + e * EIGHTH, 0.18 if e % 2 else 0.12)
    else:
        add(drums, kick(), t0, 0.95)
        add(fx, crash * 0.25, t0)
    # guitar-ish strums: on beat 1 full strum, then offbeat stabs
    if not outro:
        pattern = [0, 1.5, 2.5, 3.5]
        for ptn in pattern:
            st = t0 + ptn * BEAT
            for i, m in enumerate(chord):
                add(music, ks_pluck(mtof(m), 0.9 if ptn == 0 else 0.45, bright=0.6), st + i * 0.012, 0.16)
    else:
        for i, m in enumerate(chord + [74 + TR]):
            add(music, ks_pluck(mtof(m), 2.0, bright=0.7, decay=0.998), t0 + i * 0.025, 0.18)
    # bass: root on 8ths with pump
    if not outro:
        for e in range(8):
            mm = roots[b] + (12 if e in (3, 7) else 0)
            add(bassb, bass(mtof(mm), EIGHTH * 0.95), t0 + e * EIGHTH, 0.55)
    else:
        add(bassb, bass(mtof(roots[b]), 1.6), t0, 0.6)

# lead marimba hook (8th grid index, midi)
phrase = [
    [(0, 74), (2, 71), (4, 74), (5, 76), (6, 74)],
    [(0, 69), (2, 71), (4, 74), (6, 69)],
    [(0, 71), (2, 67), (4, 71), (5, 74), (6, 76)],
    [(0, 79), (2, 76), (4, 74), (6, 71)],
]
for b in range(1, NB - 1):
    t0 = DROP + b * BAR
    for idx, m in phrase[b % 4]:
        add(lead, marimba(mtof(m + TR)), t0 + idx * EIGHTH, 0.32)
# bar 0 gets a bright bell "ding" on the drop for the price reveal
add(lead, bell(mtof(86 + TR)), DROP, 0.28)
add(lead, bell(mtof(91 + TR)), DROP + 0.06, 0.18)
# outro bell
add(lead, bell(mtof(79 + TR), 2.0), DROP + (NB - 1) * BAR, 0.25)

# whooshes on scene cuts
cuts = CUT_ARG or [2.5, 4.0, 5.5, 7.0, 8.5, 10.0, 11.5, 13.0]
for c in cuts:
    d = 0.22; n = int(SR * d); tt = np.arange(n) / SR
    w = bp(800, 6000, rng.standard_normal(n)) * np.sin(np.pi * tt / d) ** 2
    add(fx, w * 0.18, c - d * 0.6)

# ---------- sidechain ----------
side = np.ones(N)
for b in range(NB - 1):
    for k in range(4):
        i = int((DROP + b * BAR + k * BEAT) * SR)
        L = int(0.22 * SR)
        seg = 1 - 0.55 * np.exp(-np.arange(L) / SR * 18)
        side[i:i + L] = np.minimum(side[i:i + L], seg[:max(0, min(L, N - i))])

music *= side; bassb *= side

# ---------- reverb ----------
ir_n = int(SR * 1.1); it = np.arange(ir_n) / SR
ir = rng.standard_normal(ir_n) * np.exp(-it * 4.5)
ir = lp(6000, ir); ir /= np.sqrt(np.sum(ir ** 2))
def verb(x, mix):
    return x + mix * fftconvolve(x, ir)[:len(x)]

mix = drums * 0.9 + verb(music, 0.25) * 1.0 + bassb * 0.8 + verb(lead, 0.35) * 1.0 + verb(fx, 0.2) * 1.0
mix = hp(30, mix)

# fade out end
fo = int(SR * 1.2)
mix[-fo:] *= np.linspace(1, 0, fo) ** 1.5

# master: soft clip + normalize
mix = mix / (np.max(np.abs(mix)) + 1e-9) * 1.25
mix = np.tanh(mix)
mix = mix / np.max(np.abs(mix)) * 0.89

# stereo widen lightly: delay a copy of music bus to right
stereo = np.stack([mix, mix], axis=1)
pcm = (stereo * 32767).astype(np.int16)
with wave.open(sys.argv[1], 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes(pcm.tobytes())
print('ok', TOTAL, NB)
