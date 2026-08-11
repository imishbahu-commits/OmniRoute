"""Stickman cartoon engine: canvas, rig, particles, easing. Logical space 1920x1080."""
import os, math, random
import numpy as np
from PIL import Image, ImageDraw, ImageFont

BASE = os.path.dirname(os.path.abspath(__file__))

def _find_font(names):
    roots = [os.path.join(BASE, "fonts"), "/tmp/fonts", "/usr/share/fonts/truetype/dejavu"]
    for n in names:
        for r in roots:
            p = os.path.join(r, n)
            if os.path.exists(p):
                return p
    return None

FONT_B = _find_font(["DejaVuSans-Bold.ttf"])
FONT_R = _find_font(["DejaVuSans.ttf", "DejaVuSans-Bold.ttf"])
FONT_M = _find_font(["DejaVuSansMono-Bold.ttf", "DejaVuSans-Bold.ttf"])

INK   = (22, 22, 26)
PAPER = (250, 249, 244)
RED   = (214, 48, 49)
GREEN = (39, 174, 96)
BLUE  = (41, 128, 185)
GOLD  = (241, 196, 15)
GREY  = (120, 120, 120)

def clamp(x, a=0.0, b=1.0): return a if x < a else b if x > b else x
def lerp(a, b, t): return a + (b - a) * t
def ease_io(t):
    t = clamp(t); return t * t * (3 - 2 * t)
def ease_in(t):
    t = clamp(t); return t * t
def ease_out(t):
    t = clamp(t); return 1 - (1 - t) * (1 - t)
def ease_out_back(t, s=1.70158):
    t = clamp(t); return 1 + (s + 1) * (t - 1) ** 3 + s * (t - 1) ** 2
def ease_out_elastic(t):
    t = clamp(t)
    if t == 0 or t == 1: return t
    return 2 ** (-10 * t) * math.sin((t * 10 - 0.75) * (2 * math.pi / 3)) + 1

_GFONTS = {}

class Canvas:
    def __init__(self, w, h, ss=2, bg=PAPER):
        self.w, self.h, self.ss = w, h, ss
        self.img = Image.new("RGB", (w * ss, h * ss), bg)
        self.d = ImageDraw.Draw(self.img)
    def _s(self, v):  # scale
        return int(round(v * self.ss))
    def font(self, size, bold=True):
        key = (self._s(size), bold)
        if key not in _GFONTS:
            _GFONTS[key] = ImageFont.truetype(FONT_B if bold else FONT_R, self._s(size))
        return _GFONTS[key]
    def mono(self, size):
        key = ("mono", self._s(size))
        if key not in _GFONTS:
            _GFONTS[key] = ImageFont.truetype(FONT_M, self._s(size))
        return _GFONTS[key]
    def line(self, pts, wpx, fill=INK):
        p = [(self._s(x), self._s(y)) for x, y in pts]
        self.d.line(p, fill=fill, width=max(1, self._s(wpx)), joint="curve")
    def circle(self, cx, cy, r, fill=None, outline=None, ow=3):
        box = [self._s(cx - r), self._s(cy - r), self._s(cx + r), self._s(cy + r)]
        self.d.ellipse(box, fill=fill, outline=outline, width=max(1, self._s(ow)) if outline else 1)
    def dot(self, cx, cy, r, fill=INK): self.circle(cx, cy, r, fill=fill)
    def arc(self, cx, cy, r, a0, a1, fill=INK, wpx=3):
        self.d.arc([self._s(cx - r), self._s(cy - r), self._s(cx + r), self._s(cy + r)],
                   a0, a1, fill=fill, width=max(1, self._s(wpx)))
    def rect(self, x0, y0, x1, y1, fill=None, outline=None, ow=3, rad=0):
        box = [self._s(x0), self._s(y0), self._s(x1), self._s(y1)]
        if rad:
            self.d.rounded_rectangle(box, radius=self._s(rad), fill=fill, outline=outline,
                                     width=max(1, self._s(ow)) if outline else 1)
        else:
            self.d.rectangle(box, fill=fill, outline=outline, width=max(1, self._s(ow)) if outline else 1)
    def text(self, cx, cy, s, size, fill=INK, anchor="mm", stroke=0, stroke_fill=None, rot=0, bold=True, mono=False):
        f = self.mono(size) if mono else self.font(size, bold)
        if rot:
            pad = self._s(size)
            tmp = Image.new("RGBA", (self._s(20 + len(s) * size), self._s(size * 2.4) + 2 * pad), (0, 0, 0, 0))
            td = ImageDraw.Draw(tmp)
            td.text((tmp.width // 2, tmp.height // 2), s, font=f, fill=fill + (255,), anchor="mm",
                    stroke_width=self._s(stroke), stroke_fill=(stroke_fill + (255,)) if stroke_fill else None)
            tmp = tmp.rotate(-rot, resample=Image.BICUBIC, expand=True)
            self.img.paste(tmp, (self._s(cx) - tmp.width // 2, self._s(cy) - tmp.height // 2), tmp)
        else:
            self.d.text((self._s(cx), self._s(cy)), s, font=f, fill=fill, anchor=anchor,
                        stroke_width=self._s(stroke), stroke_fill=stroke_fill)
    def poly(self, pts, fill=None, outline=None, ow=3):
        p = [(self._s(x), self._s(y)) for x, y in pts]
        self.d.polygon(p, fill=fill, outline=outline, width=max(1, self._s(ow)) if outline else 1)
    def frame(self):
        if self.ss != 1:
            return self.img.resize((self.w, self.h), Image.LANCZOS)
        return self.img

class Rig:
    """Stickman. Logical px. y_foot = ground contact point."""
    LEG1, LEG2, TORSO, HEAD_R, ARM1, ARM2 = 46, 46, 78, 26, 40, 38
    def __init__(self, cv, x=960, y=935, scale=1.0, lw=8.5, color=INK, flip=False):
        self.cv, self.x, self.y = cv, x, y
        self.s, self.lw, self.color, self.flip = scale, lw, color, flip
    def _limb(self, bx, by, a1, a2, l1, l2):
        a1 = math.radians(a1); a2 = math.radians(a2)
        kx = bx + math.sin(a1) * l1; ky = by + math.cos(a1) * l1
        ex = kx + math.sin(a1 + a2) * l2; ey = ky + math.cos(a1 + a2) * l2
        self.cv.line([(bx, by), (kx, ky), (ex, ey)], self.lw, self.color)
        return (ex, ey)
    def draw(self, look=0.0, mood="calm", squat=0.0, armL=(-12, -18), armR=(12, 18),
             legL=(8, 10), legR=(-8, 10), torso_lean=0.0, air=False):
        s = self.s * (1 - 0.55 * squat)
        L1, L2, T, R = self.LEG1*s, self.LEG2*s, self.TORSO*s, self.HEAD_R*s
        hipx, hipy = self.x, self.y - (L1 + L2)
        if squat: hipy = self.y - (L1 + L2) * (1 - 0.35*squat)
        lean = math.radians(torso_lean)
        shx = hipx + math.sin(lean) * T; shy = hipy - math.cos(lean) * T
        hcx = shx + math.sin(lean) * (R + 4*s); hcy = shy - math.cos(lean) * (R + 4*s)
        dirx = -1 if self.flip else 1
        self._limb(hipx, hipy, legL[0]*dirx, legL[1]*dirx, L1, L2)
        self._limb(hipx, hipy, legR[0]*dirx, legR[1]*dirx, L1, L2)
        self.cv.line([(hipx, hipy), (shx, shy)], self.lw, self.color)
        ayy = shy + 13 * s
        self._limb(shx, ayy, armL[0]*dirx, armL[1]*dirx, self.ARM1*s, self.ARM2*s)
        self._limb(shx, ayy, armR[0]*dirx, armR[1]*dirx, self.ARM1*s, self.ARM2*s)
        self.cv.circle(hcx, hcy, R, fill=PAPER, outline=self.color, ow=self.lw)
        ex = hcx + look * 8 * s
        if mood == "dead":
            for sx in (-10, 10):
                self.cv.line([(ex+sx*s-4, hcy-10), (ex+sx*s+4, hcy-2)], max(2, self.lw*0.35), self.color)
                self.cv.line([(ex+sx*s-4, hcy-2), (ex+sx*s+4, hcy-10)], max(2, self.lw*0.35), self.color)
            self.cv.arc(hcx, hcy+10*s, 8*s, 20, 160, self.color, max(2, self.lw*0.4))
        elif mood == "blink":
            self.cv.line([(ex-13*s, hcy-5), (ex-7*s, hcy-5)], max(2, self.lw*0.35), self.color)
            self.cv.line([(ex+7*s, hcy-5), (ex+13*s, hcy-5)], max(2, self.lw*0.35), self.color)
            self.cv.arc(hcx, hcy+8*s, 9*s, 20, 160, self.color, max(2, self.lw*0.4))
        else:
            er = 4.2*s if mood != "wow" else 5.5*s
            self.cv.dot(ex-10*s, hcy-5, er, self.color)
            self.cv.dot(ex+10*s, hcy-5, er, self.color)
            if mood == "calm":
                self.cv.arc(hcx, hcy+8*s, 9*s, 20, 160, self.color, max(2, self.lw*0.4))
            elif mood == "grin":
                self.cv.arc(hcx, hcy+7*s, 12*s, 10, 170, self.color, max(2.5, self.lw*0.45))
            elif mood == "o":
                self.cv.circle(hcx, hcy+11*s, 6.5*s, outline=self.color, ow=max(2, self.lw*0.35))
            elif mood == "scream":
                self.cv.circle(hcx, hcy+12*s, 10*s, outline=self.color, ow=max(2.5, self.lw*0.4))
            elif mood == "flat":
                self.cv.line([(hcx-8*s, hcy+11*s), (hcx+8*s, hcy+11*s)], max(2, self.lw*0.35), self.color)
            elif mood == "sweat":
                self.cv.arc(hcx, hcy+8*s, 9*s, 20, 160, self.color, max(2, self.lw*0.4))
                self.cv.poly([(hcx+R*0.95, hcy-R*0.55), (hcx+R*1.15, hcy-R*0.15), (hcx+R+6*s, hcy-R*0.5)],
                             fill=(66, 135, 222))
        return (hcx, hcy, R)

def run_cycle(ph, amp=52, knee=70):
    a1 = math.sin(ph * 2 * math.pi) * amp
    a2 = math.sin(ph * 2 * math.pi + math.pi) * amp
    k1 = (1 - math.cos(ph * 2 * math.pi)) * 0.5 * knee
    k2 = (1 - math.cos(ph * 2 * math.pi + math.pi)) * 0.5 * knee
    return (a1, k1), (a2, k2)

def arm_swing(ph, amp=45):
    a1 = math.sin(ph * 2 * math.pi + math.pi) * amp - 10
    a2 = math.sin(ph * 2 * math.pi) * amp - 10
    return (a1, -35), (a2, -35)

class Dust:
    def __init__(self): self.ps = []
    def burst(self, x, y, n=10, spread=60):
        for _ in range(n):
            self.ps.append([x + random.uniform(-spread, spread), y + random.uniform(-6, 2),
                            random.uniform(4, 12), 1.0, random.uniform(0.5, 1.0)])
    def step(self, dt=1/24):
        for p in self.ps:
            p[2] += 26 * dt * p[4]; p[3] -= 2.6 * dt * p[4]; p[1] -= 12 * dt
        self.ps = [p for p in self.ps if p[3] > 0]
    def draw(self, cv):
        for p in self.ps:
            g = int(120 + 100 * (1 - p[3]))
            cv.circle(p[0], p[1], p[2], fill=(g, g, g))

class Confetti:
    COLS = [RED, BLUE, GREEN, GOLD, (150, 80, 200), (255, 120, 60)]
    def __init__(self, n=130, w=1920):
        self.w = w
        self.ps = [self._spawn(True) for _ in range(n)]
    def _spawn(self, anywhere=False):
        return [random.uniform(0, self.w),
                random.uniform(-1080, 1000) if anywhere else random.uniform(-260, -30),
                random.uniform(140, 300), random.uniform(-50, 50), random.uniform(0, 6.28),
                random.uniform(8, 17), random.choice(self.COLS), random.uniform(-4, 4)]
    def step(self, dt=1/24):
        for i, p in enumerate(self.ps):
            p[1] += p[2] * dt; p[0] += p[3] * dt + math.sin(p[4]) * 1.1
            p[4] += (p[7] + 2) * dt * 3
            if p[1] > 1130:
                self.ps[i] = self._spawn()
    def draw(self, cv):
        for p in self.ps:
            if p[1] > 1100: continue
            w, h = p[5], p[5] * 0.6
            c, sn = math.cos(p[4]), math.sin(p[4])
            pts = [(p[0] + c*w - sn*h, p[1] + sn*w + c*h), (p[0] - c*w - sn*h, p[1] - sn*w + c*h),
                   (p[0] - c*w + sn*h, p[1] - sn*w - c*h), (p[0] + c*w + sn*h, p[1] + sn*w - c*h)]
            cv.poly(pts, fill=p[6])
