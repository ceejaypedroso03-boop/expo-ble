"""Royalty-free synth beat for the ARC Robotics promo. 120 BPM, A minor, 62 s."""
import numpy as np, wave
from scipy.signal import butter, sosfilt

SR = 44100
DUR = 75.5
BPM = 120
B = 60 / BPM            # beat = 0.5 s
N = int(SR * DUR)
rng = np.random.default_rng(7)

def T(sec): return int(sec * SR)
def lp(x, f, o=2): return sosfilt(butter(o, f, 'low', fs=SR, output='sos'), x)
def hp(x, f, o=2): return sosfilt(butter(o, f, 'high', fs=SR, output='sos'), x)
def bp(x, lo, hi): return sosfilt(butter(2, [lo, hi], 'band', fs=SR, output='sos'), x)
def note(m): return 440 * 2 ** ((m - 69) / 12)
def saw(f, n, det=0.0):
    t = np.arange(n) / SR
    return 2 * ((t * f * (1 + det)) % 1) - 1

L = np.zeros(N); R = np.zeros(N)
def add(sig, at, gain=1.0, pan=0.0):
    i = T(at); j = min(N, i + len(sig))
    if j <= i: return
    s = sig[:j - i] * gain
    L[i:j] += s * (1 - max(0, pan)); R[i:j] += s * (1 + min(0, pan))

# --- one-shots -------------------------------------------------------------
def kick():
    n = T(0.35); t = np.arange(n) / SR
    f = 45 + 110 * np.exp(-t * 35)
    ph = 2 * np.pi * np.cumsum(f) / SR
    return np.sin(ph) * np.exp(-t * 9) + 0.15 * np.exp(-t * 200) * rng.uniform(-1, 1, n)
def hat(open_=False):
    n = T(0.18 if open_ else 0.05); t = np.arange(n) / SR
    return hp(rng.uniform(-1, 1, n), 8000) * np.exp(-t * (18 if open_ else 90))
def clap():
    n = T(0.25); t = np.arange(n) / SR
    env = np.exp(-t * 22) + 0.6 * np.exp(-((t - 0.012) % 0.011) * 300) * (t < 0.035)
    return bp(rng.uniform(-1, 1, n), 900, 3500) * env
def impact():
    n = T(2.5); t = np.arange(n) / SR
    sub = np.sin(2 * np.pi * np.cumsum(30 + 60 * np.exp(-t * 6)) / SR) * np.exp(-t * 1.6)
    nz = lp(rng.uniform(-1, 1, n), 2500) * np.exp(-t * 3)
    return sub + 0.5 * nz
def riser(d):
    n = T(d); t = np.arange(n) / SR
    x = rng.uniform(-1, 1, n)
    out = np.zeros(n); seg = 2048
    for k in range(0, n, seg):   # stepwise sweeping band-pass
        p = k / n; c = 300 + 7000 * p ** 2
        out[k:k + seg] = bp(x[k:k + seg], c * 0.7, min(c * 1.4, 20000))
    return out * (t / d) ** 2
def pluck(m, d=0.22):
    n = T(d); t = np.arange(n) / SR; f = note(m)
    x = (saw(f, n) + saw(f, n, 0.006)) * 0.5
    return lp(x, 2600) * np.exp(-t * 14)

# --- harmony: Am F C G, one chord per bar (2 s) ---------------------------
CH = [[57, 60, 64], [53, 57, 60], [48, 52, 55], [55, 59, 62]]
ROOT = [45, 41, 48, 43]

def chord_at(sec): return int(sec // 2) % 4

# Pad (whole track, swells)
pad = np.zeros(N)
for bar in range(int(DUR // 2) + 1):
    c = CH[bar % 4]; n = T(2.05); t = np.arange(n) / SR
    s = sum(saw(note(m), n, d) for m in c for d in (-0.004, 0.004)) / 6
    env = np.minimum(1, t / 0.3) * np.minimum(1, (2.05 - t) / 0.25)
    i = T(bar * 2); j = min(N, i + n)
    if i < N: pad[i:j] += (s * env)[:j - i]
pad = lp(pad, 1400)
# fade the pad gently in the drop, keep it big in intro/outro
pad_gain = np.ones(N) * 0.22
pad_gain[T(31):T(70)] = 0.12
add(pad * pad_gain, 0, 1.0)

# Hook hits (0-3 s): kick + impact on each word
for s in (0.0, 0.5, 1.0, 1.5):
    add(kick(), s, 0.9)
add(riser(1.0), 2.0, 0.35)
add(impact(), 3.0, 0.8)

# Groove sections
kick_times = []
def groove(a, b, full):
    s = a
    while s < b - 1e-6:
        beat = round((s - a) / B)
        add(kick(), s, 0.95); kick_times.append(s)
        add(hat(), s + B / 2, 0.22, 0.3)
        if full:
            add(hat(), s + B / 4, 0.10, -0.3); add(hat(), s + 3 * B / 4, 0.10, -0.3)
            if beat % 2 == 1: add(clap(), s, 0.45)
            if beat % 4 == 3: add(hat(True), s + B / 2, 0.12, 0.2)
        s += B

groove(6.0, 31.0, False)
groove(31.0, 70.0, True)
add(riser(3.0), 28.0, 0.45)
add(impact(), 31.0, 0.7)
add(riser(2.0), 68.0, 0.35)
add(impact(), 70.0, 0.9)

# Bass: offbeat 8ths, root of chord
def bassline(a, b, g):
    s = a
    while s < b - 1e-6:
        r = ROOT[chord_at(s)]
        for off in (0.25,):
            n = T(0.22); t = np.arange(n) / SR
            x = lp(saw(note(r), n) + 0.5 * np.sin(2 * np.pi * note(r - 12) * t), 500) * np.exp(-t * 6)
            add(x, s + off, g)
        s += 0.5
bassline(6.0, 31.0, 0.45)
bassline(31.0, 70.0, 0.55)

# Arp (16ths) in the drop and outro
def arp(a, b, g):
    s = a; k = 0
    while s < b - 1e-6:
        c = CH[chord_at(s)]
        seq = [c[0] + 12, c[1] + 12, c[2] + 12, c[1] + 24]
        add(pluck(seq[k % 4]), s, g, 0.35 if k % 2 else -0.35)
        s += B / 4; k += 1
arp(31.0, 70.0, 0.16)
arp(70.0, 73.5, 0.10)

# Sidechain duck (pad/bass breathe with the kick) - approximate on the master
duck = np.ones(N)
for kt in kick_times:
    i = T(kt); n = T(0.25); t = np.arange(n) / SR
    j = min(N, i + n); duck[i:j] = np.minimum(duck[i:j], (0.55 + 0.45 * (t / 0.25) ** 0.6)[:j - i])
L *= duck; R *= duck
# re-add kicks un-ducked (they were ducked along with everything)
for kt in kick_times: add(kick(), kt, 0.25)

# Master: fade out, soft clip, normalise
fade = np.ones(N); fo = T(3.0); fade[-fo:] = np.linspace(1, 0, fo) ** 1.5
L *= fade; R *= fade
mix = np.stack([L, R], 1)
mix = np.tanh(mix * 1.2)
mix /= np.max(np.abs(mix)) / 0.89
pcm = (mix * 32767).astype('<i2')
with wave.open('beat.wav', 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
print('ok', DUR)
