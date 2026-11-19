"""ARC Robotics promo renderer: 1080x1920 @30fps, ~62 s. Usage: python3 render.py [out.mp4] [start_s end_s]"""
import subprocess, sys, math, random
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops

U = '/root/.claude/uploads/c5ba17f0-dfcd-50ce-8da8-294cb4ab609b/'
W, H, FPS = 1080, 1920, 30
CYAN = (64, 232, 255); CYAN2 = (0, 170, 255); WHITE = (240, 250, 255); ORANGE = (255, 140, 40)
NAVY = (4, 9, 24)

def F(name, size): return ImageFont.truetype(name, size)
ORB9, ORB7, RAJ = 'orb900.woff', 'orb700.woff', 'raj700.woff'

def vid(id_): return next(__import__('glob').iglob(U + id_ + '*.mov'))
def img(id_): return U + id_ + '-image.jpg'

def ease(x): x = max(0, min(1, x)); return 1 - (1 - x) ** 3
def ease_back(x):
    x = max(0, min(1, x)); c = 1.7; return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2

# ---------------------------------------------------------------- text helpers
_cache = {}
def glow_text(text, font, size, color=CYAN, glow=14, stroke=0, track=0):
    key = (text, font, size, color, glow, stroke, track)
    if key in _cache: return _cache[key]
    f = F(font, size)
    if track:
        widths = [f.getbbox(ch)[2] - f.getbbox(ch)[0] if ch != ' ' else size * 0.35 for ch in text]
        tw = int(sum(widths) + track * (len(text) - 1))
    else:
        bb = f.getbbox(text); tw = bb[2] - bb[0]
    asc, desc = f.getmetrics()
    pad = glow * 3
    im = Image.new('RGBA', (tw + pad * 2, asc + desc + pad * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    if track:
        x = pad
        for ch, w_ in zip(text, widths):
            d.text((x, pad), ch, font=f, fill=color + (255,)); x += w_ + track
    else:
        d.text((pad - f.getbbox(text)[0], pad), text, font=f, fill=color + (255,), stroke_width=stroke, stroke_fill=color + (255,))
    if glow:
        g = im.filter(ImageFilter.GaussianBlur(glow))
        a = np.array(g); a[..., 3] = np.clip(a[..., 3] * 1.6, 0, 255); g = Image.fromarray(a)
        core = im
        if color != WHITE:   # hot white core for neon look
            c = np.array(im).astype(np.float32); c[..., :3] = c[..., :3] * 0.55 + 255 * 0.45
            core = Image.fromarray(c.astype(np.uint8))
        out = Image.new('RGBA', im.size, (0, 0, 0, 0)); out.alpha_composite(g); out.alpha_composite(core)
        im = out
    _cache[key] = im
    return im

def paste(base, el, cx, cy, alpha=1.0, scale=1.0, anchor='c'):
    if alpha <= 0.01: return
    if abs(scale - 1) > 0.005:
        el = el.resize((max(1, int(el.width * scale)), max(1, int(el.height * scale))), Image.BILINEAR)
    if alpha < 0.999:
        a = el.getchannel('A').point(lambda v: int(v * alpha)); el = el.copy(); el.putalpha(a)
    x = int(cx - el.width / 2) if anchor == 'c' else int(cx)
    y = int(cy - el.height / 2)
    base.alpha_composite(el, (max(0, x), max(0, y)), (max(0, -x), max(0, -y)))

def panel(w, h, border=CYAN, fill=(4, 12, 30, 200), cut=28, glow=10):
    """HUD panel with cut corners and neon border."""
    pad = glow * 3
    im = Image.new('RGBA', (w + pad * 2, h + pad * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    x0, y0, x1, y1 = pad, pad, pad + w, pad + h
    poly = [(x0 + cut, y0), (x1, y0), (x1, y1 - cut), (x1 - cut, y1), (x0, y1), (x0, y0 + cut)]
    d.polygon(poly, fill=fill)
    line = Image.new('RGBA', im.size, (0, 0, 0, 0)); dl = ImageDraw.Draw(line)
    dl.line(poly + [poly[0]], fill=border + (255,), width=4, joint='curve')
    # accent ticks
    dl.line([(x0 + cut + 20, y0 - 8), (x0 + cut + 140, y0 - 8)], fill=border + (255,), width=6)
    dl.line([(x1 - cut - 140, y1 + 8), (x1 - cut - 20, y1 + 8)], fill=border + (255,), width=6)
    g = line.filter(ImageFilter.GaussianBlur(glow))
    im.alpha_composite(g); im.alpha_composite(g); im.alpha_composite(line)
    return im

# ---------------------------------------------------------------- backgrounds
def make_circuit_bg():
    rnd = random.Random(3)
    bw, bh = W, H + 600
    im = Image.new('RGB', (bw, bh), NAVY)
    a = np.array(im).astype(np.float32)
    yy, xx = np.mgrid[0:bh, 0:bw]
    for cx, cy, r, col in [(900, 300, 900, (0, 80, 160)), (100, 1500, 1000, (0, 50, 120)), (600, 2200, 800, (0, 90, 150))]:
        d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
        a += (np.clip(1 - d / r, 0, 1) ** 2)[..., None] * np.array(col) * 0.7
    im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).convert('RGBA')
    tr = Image.new('RGBA', (bw, bh), (0, 0, 0, 0)); d = ImageDraw.Draw(tr)
    for gx in range(0, bw, 60): d.line([(gx, 0), (gx, bh)], fill=(40, 120, 200, 18))
    for gy in range(0, bh, 60): d.line([(0, gy), (bw, gy)], fill=(40, 120, 200, 18))
    for _ in range(70):   # circuit traces
        x, y = rnd.randrange(0, bw, 30), rnd.randrange(0, bh, 30)
        pts = [(x, y)]
        for _ in range(rnd.randint(2, 5)):
            dirn = rnd.choice([(1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, 1)])
            L_ = rnd.randint(2, 8) * 30
            x += dirn[0] * L_; y += dirn[1] * L_; pts.append((x, y))
        c = (60, 200, 255, rnd.randint(40, 110))
        d.line(pts, fill=c, width=3)
        ex, ey = pts[-1]; d.ellipse([ex - 7, ey - 7, ex + 7, ey + 7], outline=c, width=3)
        sx, sy = pts[0]; d.ellipse([sx - 5, sy - 5, sx + 5, sy + 5], fill=c)
    g = tr.filter(ImageFilter.GaussianBlur(6))
    im.alpha_composite(g); im.alpha_composite(tr)
    return im

CIRCUIT = None
def circuit_frame(t, drift=40):
    off = int((t * drift) % 600)
    return CIRCUIT.crop((0, off, W, off + H)).copy()

# ---------------------------------------------------------------- logo
def make_logo(size):
    raw = Image.open('logo_raw.png').convert('RGBA')
    cx, cy, r = 125, 191, 118
    c = raw.crop((cx - r, cy - r, cx + r, cy + r)).resize((size, size), Image.LANCZOS)
    m = Image.new('L', (size * 4, size * 4), 0); ImageDraw.Draw(m).ellipse([6, 6, size * 4 - 6, size * 4 - 6], fill=255)
    c.putalpha(m.resize((size, size), Image.LANCZOS))
    return c
def logo_with_glow(size):
    lg = make_logo(size); pad = 60
    out = Image.new('RGBA', (size + pad * 2, size + pad * 2), (0, 0, 0, 0))
    ring = Image.new('RGBA', out.size, (0, 0, 0, 0))
    ImageDraw.Draw(ring).ellipse([pad - 6, pad - 6, pad + size + 6, pad + size + 6], outline=CYAN + (255,), width=8)
    out.alpha_composite(ring.filter(ImageFilter.GaussianBlur(22))); out.alpha_composite(ring.filter(ImageFilter.GaussianBlur(8)))
    out.alpha_composite(lg, (pad, pad))
    return out

# ---------------------------------------------------------------- sources
class VideoSrc:
    def __init__(self, id_, start, dur, grade=True, blur=0, dim=1.0):
        vf = 'fps=30,scale=1080:1974:flags=lanczos,crop=1080:1920'
        if grade: vf += ',eq=contrast=1.10:saturation=1.20:brightness=0.01,unsharp=5:5:0.6'
        if blur: vf += f',gblur=sigma={blur}'
        if dim != 1.0: vf += f',eq=brightness={dim-1:.2f}:contrast=0.9'
        self.n = int(round(dur * FPS))
        cmd = ['ffmpeg', '-v', 'error', '-ss', str(start), '-i', vid(id_), '-t', str(dur + 0.5), '-vf', vf,
               '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-']
        raw = subprocess.run(cmd, capture_output=True, check=True).stdout
        fs = W * H * 3; k = len(raw) // fs
        self.frames = [raw[i * fs:(i + 1) * fs] for i in range(k)]
    def get(self, i):
        b = self.frames[min(i, len(self.frames) - 1)]
        return Image.frombuffer('RGB', (W, H), b).convert('RGBA')

class PhotoSrc:
    """Screen photo: blurred cover background + framed, slowly zooming panel."""
    def __init__(self, id_, crop, dur, zoom=(1.0, 1.08), pan=(0, 0)):
        im = Image.open(img(id_)).convert('RGB')
        self.n = int(round(dur * FPS))
        # background: cover + blur + darken
        s = max(W / im.width, H / im.height)
        bg = im.resize((int(im.width * s) + 1, int(im.height * s) + 1), Image.BILINEAR)
        bg = bg.crop(((bg.width - W) // 2, (bg.height - H) // 2, (bg.width - W) // 2 + W, (bg.height - H) // 2 + H))
        bg = bg.filter(ImageFilter.GaussianBlur(30))
        bg = Image.blend(bg, Image.new('RGB', (W, H), NAVY), 0.55)
        self.bg = bg.convert('RGBA')
        fg = im.crop(crop)
        from PIL import ImageEnhance
        fg = ImageEnhance.Contrast(fg).enhance(1.12); fg = ImageEnhance.Color(fg).enhance(1.15)
        self.fg = fg; self.zoom = zoom; self.pan = pan
        self.pw = 960; self.ph = int(960 * fg.height / fg.width)
        if self.ph > 1150: self.ph = 1150; self.pw = int(1150 * fg.width / fg.height)
        self.frame = panel(self.pw + 16, self.ph + 16, fill=(0, 0, 0, 0), cut=0)
    def get(self, i):
        p = i / max(1, self.n - 1)
        z = self.zoom[0] + (self.zoom[1] - self.zoom[0]) * p
        out = self.bg.copy()
        fw, fh = self.fg.size
        cw, ch = fw / z, fh / z
        cx = fw / 2 + self.pan[0] * fw * p; cy = fh / 2 + self.pan[1] * fh * p
        cx = min(max(cx, cw / 2), fw - cw / 2); cy = min(max(cy, ch / 2), fh - ch / 2)
        box = (cx - cw / 2, cy - ch / 2, cx + cw / 2, cy + ch / 2)
        view = self.fg.resize((self.pw, self.ph), Image.BILINEAR, box=box).convert('RGBA')
        cy0 = 860
        out.alpha_composite(view, (W // 2 - self.pw // 2, cy0 - self.ph // 2))
        paste(out, self.frame, W // 2, cy0)
        return out

# ---------------------------------------------------------------- overlays
HUD_LOGO = None
def hud(fr, t_global, label):
    """Persistent corner HUD on footage segments."""
    d = ImageDraw.Draw(fr)
    # top gradient for legibility
    paste(fr, TOP_GRAD, W // 2, 160)
    paste(fr, BOT_GRAD, W // 2, H - 380)
    paste(fr, HUD_LOGO, 60, 120, anchor='l')
    paste(fr, glow_text('ARC ROBOTICS', ORB9, 34, WHITE, glow=6), 158, 104, anchor='l')
    paste(fr, glow_text('YOUR INNOVATION PARTNER', RAJ, 26, CYAN, glow=4, track=3), 158, 146, anchor='l')
    # blinking rec dot + label
    if int(t_global * 2) % 2 == 0:
        d.ellipse([W - 250, 106, W - 230, 126], fill=(255, 60, 60, 255))
    paste(fr, glow_text(label, ORB7, 26, WHITE, glow=4), W - 218, 116, anchor='l')
    # corner brackets
    c = CYAN + (220,); L_ = 70; m = 40
    for (x, y, sx, sy) in [(m, 220, 1, 1), (W - m, 220, -1, 1), (m, H - 170, 1, -1), (W - m, H - 170, -1, -1)]:
        d.line([(x, y), (x + sx * L_, y)], fill=c, width=5); d.line([(x, y), (x, y + sy * L_)], fill=c, width=5)
    # progress bar
    p = t_global / TOTAL
    d.rectangle([m, H - 120, W - m, H - 114], fill=(255, 255, 255, 50))
    d.rectangle([m, H - 120, m + int((W - 2 * m) * p), H - 114], fill=CYAN + (255,))

def caption(fr, t, title, sub=None, kicker=None, y=1500, delay=0.12):
    """Animated lower-third: kicker chip, big title, subline."""
    a = ease((t - delay) / 0.35)
    if a <= 0: return
    dy = (1 - a) * 60
    if kicker:
        k = glow_text(kicker, ORB7, 30, NAVY, glow=0, track=2)
        chip = Image.new('RGBA', (k.width - 0, k.height - 0), CYAN + (255,))
        chip.alpha_composite(k)
        paste(fr, chip, 70, y - 110 + dy, alpha=a, anchor='l')
    tt = glow_text(title, ORB9, title_size(title), WHITE, glow=0)
    gl = glow_text(title, ORB9, title_size(title), CYAN, glow=16)
    # wipe-in reveal
    wv = ease((t - delay) / 0.45)
    if wv < 1:
        cw = max(1, int(gl.width * wv)); gl = gl.crop((0, 0, cw, gl.height)); tt = tt.crop((0, 0, min(cw, tt.width), tt.height))
    paste(fr, gl, 70 - 42, y + dy, alpha=a, anchor='l')
    if sub:
        sa = ease((t - delay - 0.25) / 0.35)
        paste(fr, glow_text(sub, RAJ, 46, WHITE, glow=6), 70 - 18, y + 92 + (1 - sa) * 30, alpha=sa, anchor='l')

def title_size(s):
    return 84 if len(s) <= 14 else (70 if len(s) <= 18 else (60 if len(s) <= 22 else 52))

def scanlines(fr, strength=18):
    paste(fr, SCAN, W // 2, H // 2, alpha=strength / 255 * 4)

def flash(fr, amt, color=CYAN):
    if amt <= 0: return
    fr.alpha_composite(Image.new('RGBA', (W, H), color + (int(255 * min(1, amt)),)))

def glitch(fr, amt):
    if amt <= 0: return fr
    a = np.array(fr); s = int(18 * amt)
    a[..., 0] = np.roll(a[..., 0], s, axis=1); a[..., 2] = np.roll(a[..., 2], -s, axis=1)
    rnd = np.random.default_rng(int(amt * 1000))
    for _ in range(int(6 * amt)):
        y0 = rnd.integers(0, H - 80); hgt = rnd.integers(10, 80)
        a[y0:y0 + hgt] = np.roll(a[y0:y0 + hgt], rnd.integers(-80, 80), axis=1)
    return Image.fromarray(a)

def punch(fr, i, n=5, amt=0.07):
    if i >= n: return fr
    z = 1 + amt * (1 - ease(i / n))
    cw, ch = W / z, H / z
    return fr.resize((W, H), Image.BILINEAR, box=((W - cw) / 2, (H - ch) / 2, (W + cw) / 2, (H + ch) / 2))

# ---------------------------------------------------------------- timeline
SEGS = []
def seg(dur, kind, **kw): SEGS.append(dict(dur=dur, kind=kind, **kw))

seg(3.0, 'hook')
seg(3.0, 'logo')
seg(2.5, 'photo', src=('59ff9b37', (380, 100, 1000, 660)), title='FROM IDEA...', sub='Concept to 3D design', kicker='STEP 01 // DESIGN', label='DESIGN')
seg(2.0, 'photo', src=('130aeddd', (330, 180, 1110, 700)), title='SMART CANE', sub='Distance sensor module', kicker='CAPSTONE PROJECT', label='DESIGN')
seg(2.0, 'photo', src=('3f8de0ba', (150, 180, 900, 740)), title='HARDWARE', sub='Software + hardware integration', kicker='ELECTRONICS BOX', label='DESIGN')
seg(3.0, 'video', src=('a5b2f5d5', 0.0), title='CIRCUIT DESIGN', sub='Custom circuits, simulated first', kicker='STEP 02 // CIRCUIT', label='SIM')
seg(3.0, 'video', src=('a30ed479', 1.5), title='3D MODELING', sub='Precision enclosures', kicker='STEP 03 // CAD', label='CAD')
seg(2.5, 'photo', src=('7d8ac4a5', (170, 360, 830, 840)), title='ENCLOSURES', sub='Every part fits the board', kicker='STEP 03 // CAD', label='CAD')
seg(3.0, 'photo', src=('eaa3e2e2', (230, 0, 1230, 680)), title='3D PRINTING', sub='Sliced, printed, ready', kicker='STEP 04 // PRINT', label='PRINT', pan=(0.04, 0))
seg(2.5, 'reveal', src=('4299bb22', 1.6))
seg(4.0, 'video', src=('502cb58a', 9.4), title='LANDSLIDE MONITOR', sub='Working IoT prototype', kicker='REAL BUILD', label='LIVE')
seg(2.5, 'video', src=('6394802f', 0.0), title='IoT', sub='Internet of Things, connected', kicker='WIRELESS', label='LIVE')
seg(3.0, 'video', src=('502cb58a', 15.4), title='SENSORS', sub='Predictive analysis from real data', kicker='TILT // RADIO // WIFI', label='LIVE')
seg(2.5, 'video', src=('4299bb22', 7.8), title='ARDUINO / ESP32', sub='Programming in C++, HTML, CSS', kicker='FIRMWARE', label='LIVE')
seg(2.0, 'video', src=('191c5e87', 19.4), title='ASSEMBLY', sub='Prototype assembly', kicker='STEP 05 // BUILD', label='LIVE')
seg(2.0, 'video', src=('a2c3d09e', 0.1), title='DELIVERED.', sub='Built. Tested. Done.', kicker='STEP 06 // DONE', label='LIVE')
seg(8.0, 'services')
seg(3.0, 'repair')
seg(3.0, 'free')
seg(5.5, 'end')
TOTAL = sum(s['dur'] for s in SEGS)

SERVICES = ['Research / Capstone Assist', 'Arduino / ESP32 Programming', 'Internet of Things (IoT)',
            'Robotics (Sumo, Line Tracing)', 'Software + Hardware Integration', '3D Modeling / Printing',
            'AI Integration', 'Custom Circuit Design', 'Predictive Analysis (Sensors)', 'Prototype Assembly',
            'Application Making']

def render_seg(s, src, i, n, tg):
    t = i / FPS; k = s['kind']
    if k == 'hook':
        fr = src.get(i)
        words = [('THESIS?', 0.0), ('CAPSTONE?', 0.5), ('RESEARCH?', 1.0)]
        for j, (w_, t0) in enumerate(words):
            if t >= t0:
                sc = ease_back((t - t0) / 0.25) if t - t0 < 0.25 else 1
                col = CYAN if j != 1 else WHITE
                paste(fr, glow_text(w_, ORB9, 112, col, glow=18), W // 2, 620 + j * 190, scale=0.6 + 0.4 * sc, alpha=min(1, (t - t0) / 0.1))
        if t >= 1.5:
            a = ease((t - 1.5) / 0.3)
            pl = panel(820, 150, fill=(0, 140, 200, 220))
            paste(fr, pl, W // 2, 1300 + (1 - a) * 40, alpha=a)
            paste(fr, glow_text('WE CAN HELP.', ORB9, 80, WHITE, glow=8), W // 2, 1300 + (1 - a) * 40, alpha=a)
        for t0 in (0.0, 0.5, 1.0, 1.5):
            if 0 <= t - t0 < 0.1: flash(fr, 0.25 * (1 - (t - t0) / 0.1))
        if t > 2.6: flash(fr, (t - 2.6) / 0.4 * 0.9, (255, 255, 255))
        return glitch(fr, max(0, 1 - t / 0.15) * 0.8)
    if k == 'logo':
        fr = circuit_frame(tg)
        a = ease_back(t / 0.6)
        paste(fr, LOGO_BIG, W // 2, 760, scale=0.4 + 0.6 * a, alpha=min(1, t / 0.2))
        if t > 0.5:
            b = ease((t - 0.5) / 0.4)
            paste(fr, glow_text('ARC ROBOTICS', ORB9, 104, WHITE, glow=14), W // 2, 1230 + (1 - b) * 40, alpha=b)
        if t > 0.9:
            b = ease((t - 0.9) / 0.4)
            paste(fr, glow_text('YOUR INNOVATION PARTNER', RAJ, 54, CYAN, glow=8, track=6), W // 2, 1340, alpha=b)
        if t > 1.4:
            b = ease((t - 1.4) / 0.4)
            pl = panel(780, 110, fill=(4, 20, 45, 220))
            paste(fr, pl, W // 2, 1520, alpha=b); paste(fr, glow_text('NOW ACCEPTING PROJECTS', ORB7, 44, CYAN, glow=10), W // 2, 1520, alpha=b)
        flash(fr, max(0, 1 - t / 0.35), (255, 255, 255))
        if t > 2.75: flash(fr, (t - 2.75) / 0.25 * 0.7)
        return fr
    if k == 'reveal':
        fr = src.get(i)
        fr.alpha_composite(Image.new('RGBA', (W, H), (0, 5, 20, 165)))
        a = ease(t / 0.3)
        paste(fr, glow_text('...TO A', ORB9, 96, WHITE, glow=10), W // 2, 760 - (1 - a) * 60, alpha=a)
        b = ease_back((t - 0.35) / 0.35) if t > 0.35 else 0
        paste(fr, glow_text('WORKING', ORB9, 128, CYAN, glow=22), W // 2, 920, scale=0.5 + 0.5 * b, alpha=min(1, b * 1.5))
        c = ease_back((t - 0.65) / 0.35) if t > 0.65 else 0
        paste(fr, glow_text('PROTOTYPE', ORB9, 128, CYAN, glow=22), W // 2, 1080, scale=0.5 + 0.5 * c, alpha=min(1, c * 1.5))
        fr = glitch(fr, max(0, 1 - t / 0.25))
        flash(fr, max(0, 1 - t / 0.3), (255, 255, 255))
        return punch(fr, i, 8, 0.12)
    if k in ('photo', 'video'):
        fr = src.get(i)
        hud(fr, tg, s['label'])
        caption(fr, t, s['title'], s.get('sub'), s.get('kicker'))
        fr = punch(fr, i)
        flash(fr, max(0, 0.35 - t / 0.12 * 0.35))
        return fr
    if k == 'services':
        fr = circuit_frame(tg)
        fr.alpha_composite(Image.new('RGBA', (W, H), (0, 0, 0, 60)))
        a = ease(t / 0.4)
        paste(fr, glow_text('SERVICES', ORB9, 110, WHITE, glow=14), W // 2, 230 - (1 - a) * 50, alpha=a)
        paste(fr, glow_text('WE OFFER', ORB9, 64, CYAN, glow=12, track=10), W // 2, 340, alpha=ease((t - 0.2) / 0.4))
        pl = panel(960, 1360, fill=(3, 12, 32, 215))
        paste(fr, pl, W // 2, 1130, alpha=ease((t - 0.1) / 0.4))
        for j, sv in enumerate(SERVICES):
            t0 = 0.45 + j * 0.42
            if t < t0: continue
            b = ease((t - t0) / 0.3)
            y = 530 + j * 118
            x = 130 + (1 - b) * 80
            bullet = glow_text('>', ORB9, 50, CYAN, glow=10)
            paste(fr, bullet, x - 20, y, alpha=b, anchor='l')
            paste(fr, glow_text(sv, RAJ, 56, WHITE, glow=5), x + 40, y, alpha=b, anchor='l')
            if t - t0 < 0.12: paste(fr, LINEFLASH, W // 2, y, alpha=1 - (t - t0) / 0.12)
        flash(fr, max(0, 0.5 - t / 0.15 * 0.5))
        return fr
    if k == 'repair':
        fr = circuit_frame(tg)
        a = ease(t / 0.35)
        paste(fr, glow_text('WE ALSO', ORB9, 80, WHITE, glow=8), W // 2, 560 - (1 - a) * 40, alpha=a)
        paste(fr, glow_text('REPAIR', ORB9, 150, ORANGE, glow=24), W // 2, 720, scale=0.6 + 0.4 * ease_back(t / 0.4), alpha=min(1, t / 0.15))
        for j, it in enumerate(['PHONES', 'PRINTERS', 'LAPTOPS']):
            t0 = 0.5 + j * 0.4
            if t < t0: continue
            b = ease_back((t - t0) / 0.3)
            y = 1020 + j * 190
            paste(fr, PILL, W // 2, y, scale=0.7 + 0.3 * b, alpha=min(1, (t - t0) / 0.15))
            paste(fr, glow_text(it, ORB9, 72, WHITE, glow=8), W // 2, y, scale=0.7 + 0.3 * b, alpha=min(1, (t - t0) / 0.15))
        flash(fr, max(0, 0.5 - t / 0.15 * 0.5))
        return glitch(fr, max(0, 1 - t / 0.15) * 0.6)
    if k == 'free':
        fr = circuit_frame(tg)
        a = ease_back(t / 0.4)
        paste(fr, glow_text('FREE', ORB9, 210, CYAN, glow=28), W // 2, 640, scale=0.5 + 0.5 * a, alpha=min(1, t / 0.15))
        b = ease((t - 0.3) / 0.35)
        paste(fr, glow_text('CONSULTATION', ORB9, 92, WHITE, glow=10), W // 2, 840 + (1 - b) * 40, alpha=b)
        if t > 0.9:
            c = ease_back((t - 0.9) / 0.35)
            pl = panel(900, 230, border=ORANGE, fill=(60, 25, 0, 200))
            paste(fr, pl, W // 2, 1180, scale=0.8 + 0.2 * c, alpha=min(1, (t - 0.9) / 0.15))
            paste(fr, glow_text('NO FIX,', ORB9, 88, WHITE, glow=8), W // 2, 1125, scale=0.8 + 0.2 * c, alpha=min(1, (t - 0.9) / 0.15))
            paste(fr, glow_text('NO PAY!', ORB9, 88, ORANGE, glow=14), W // 2, 1230, scale=0.8 + 0.2 * c, alpha=min(1, (t - 0.9) / 0.15))
        flash(fr, max(0, 0.5 - t / 0.15 * 0.5))
        if t > 2.7: flash(fr, (t - 2.7) / 0.3, (255, 255, 255))
        return fr
    if k == 'end':
        fr = circuit_frame(tg)
        a = ease_back(t / 0.6)
        paste(fr, LOGO_MED, W // 2, 470, scale=0.5 + 0.5 * a, alpha=min(1, t / 0.2))
        b = ease((t - 0.4) / 0.4)
        paste(fr, glow_text('CONTACT US ON', ORB7, 50, CYAN, glow=8, track=6), W // 2, 860, alpha=b)
        if t > 0.6:
            c = ease((t - 0.6) / 0.4)
            pl = panel(940, 180, fill=(24, 60, 140, 225))
            paste(fr, pl, W // 2, 1010 + (1 - c) * 30, alpha=c)
            paste(fr, FB_ICON, 190, 1010 + (1 - c) * 30, alpha=c)
            paste(fr, glow_text('FACEBOOK PAGE', RAJ, 40, CYAN, glow=4), 270, 975 + (1 - c) * 30, alpha=c, anchor='l')
            paste(fr, glow_text('ARC ROBOTICS', ORB9, 66, WHITE, glow=6), 262, 1040 + (1 - c) * 30, alpha=c, anchor='l')
        names = ['Chris James Baje Pedroso', 'Roy Angelo Tugay', 'Addy Demetillo']
        if t > 1.0:
            paste(fr, glow_text('OR MESSAGE:', RAJ, 42, CYAN, glow=4, track=4), W // 2, 1200, alpha=ease((t - 1.0) / 0.3))
        for j, nm in enumerate(names):
            t0 = 1.1 + j * 0.25
            if t < t0: continue
            d_ = ease((t - t0) / 0.35)
            paste(fr, glow_text(nm, RAJ, 60, WHITE, glow=5), W // 2, 1280 + j * 84 + (1 - d_) * 25, alpha=d_)
        if t > 2.0:
            e = ease((t - 2.0) / 0.4)
            paste(fr, glow_text('THESIS  •  CAPSTONE  •  RESEARCH', ORB7, 38, CYAN, glow=10), W // 2, 1620, alpha=e)
            paste(fr, glow_text('WE CAN HELP!', ORB9, 70, WHITE, glow=12), W // 2, 1700, alpha=e)
        flash(fr, max(0, 1 - t / 0.4), (255, 255, 255))
        if t > s['dur'] - 0.8: fr.alpha_composite(Image.new('RGBA', (W, H), (0, 0, 0, int(255 * (t - (s['dur'] - 0.8)) / 0.8))))
        return fr

def build_src(s):
    k = s['kind']
    if k == 'hook':   return VideoSrc('502cb58a', 10.0, s['dur'], blur=6, dim=0.62)
    if k == 'photo':  return PhotoSrc(s['src'][0], s['src'][1], s['dur'], pan=s.get('pan', (0, 0)))
    if k in ('video', 'reveal'): return VideoSrc(s['src'][0], s['src'][1], s['dur'])
    return None

def main():
    global CIRCUIT, HUD_LOGO, LOGO_BIG, LOGO_MED, TOP_GRAD, BOT_GRAD, SCAN, PILL, FB_ICON, LINEFLASH
    out = sys.argv[1] if len(sys.argv) > 1 else 'promo.mp4'
    rng_ = (float(sys.argv[2]), float(sys.argv[3])) if len(sys.argv) > 3 else (0, 1e9)
    CIRCUIT = make_circuit_bg()
    HUD_LOGO = make_logo(84)
    LOGO_BIG = logo_with_glow(520); LOGO_MED = logo_with_glow(420)
    g = np.zeros((320, W, 4), np.uint8); g[..., 3] = np.linspace(200, 0, 320)[:, None]; TOP_GRAD = Image.fromarray(g)
    g = np.zeros((760, W, 4), np.uint8); g[..., :3] = (0, 4, 14); g[..., 3] = np.linspace(0, 230, 760)[:, None] ** 1 ; BOT_GRAD = Image.fromarray(g)
    PILL = panel(620, 140, fill=(4, 20, 45, 230), cut=22)
    fb = Image.new('RGBA', (100, 100), (0, 0, 0, 0)); dfb = ImageDraw.Draw(fb)
    dfb.ellipse([0, 0, 99, 99], fill=(255, 255, 255, 255)); dfb.text((32, 6), 'f', font=F('/usr/share/fonts/opentype/inter/Inter-Bold.otf', 82), fill=(24, 90, 220, 255))
    FB_ICON = fb
    lf = Image.new('RGBA', (W - 120, 100), CYAN + (90,)); LINEFLASH = lf.filter(ImageFilter.GaussianBlur(10))

    enc = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS),
                            '-i', '-', '-c:v', 'libx264', '-preset', 'medium', '-crf', '19', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', out],
                           stdin=subprocess.PIPE)
    tg0 = 0.0; nfr = 0
    for s in SEGS:
        n = int(round(s['dur'] * FPS))
        if tg0 + s['dur'] <= rng_[0] or tg0 >= rng_[1]: tg0 += s['dur']; continue
        src = build_src(s)
        for i in range(n):
            tg = tg0 + i / FPS
            if not (rng_[0] <= tg < rng_[1]): continue
            fr = render_seg(s, src, i, n, tg)
            enc.stdin.write(fr.convert('RGB').tobytes()); nfr += 1
        print(f"{s['kind']:9s} {tg0:5.1f}-{tg0 + s['dur']:5.1f}", flush=True)
        tg0 += s['dur']
    enc.stdin.close(); enc.wait()
    print('frames', nfr, 'total', TOTAL)

if __name__ == '__main__':
    main()
