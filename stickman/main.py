"""LIFE any% SPEEDRUN — full cartoon renderer (timing-locked v2, repo edition).
  python3 main.py sheet [frames...]  -> QA contact sheet
  python3 main.py render             -> silent.mp4 + events.json
"""
import sys, os, json, math, random, subprocess, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from core import *
from PIL import Image, ImageOps

W, H, FPS = 1920, 1080, 24
GROUND = 935
OUT = os.path.join(BASE, "out")
random.seed(7)

def f2t(f): return f / FPS
def run_time_str(rt):
    m = int(rt // 60); s = rt - 60 * m
    return f"{m:02d}:{s:05.2f}"

def sfx(events, f, name, gain=1.0):
    events.append([round(f2t(f), 3), name, gain])

def shake_amp(f, windows):
    dx = dy = 0.0
    for f0, f1, a in windows:
        if f0 <= f < f1:
            k = 1 - (f - f0) / max(1, (f1 - f0))
            rng = random.Random(f)
            dx += rng.uniform(-a, a) * k; dy += rng.uniform(-a, a) * k
    return dx, dy

def caption(cv, s, y=1000, size=58, fill=INK):
    cv.text(W/2, y, s, size, fill=fill, stroke=10, stroke_fill=(255, 255, 255))

def hud(cv, rt):
    cv.rect(36, 34, 596, 118, fill=(28, 28, 32), rad=20)
    cv.text(64, 75, "LIFE  any%", 40, fill=(255, 255, 255), anchor="lm")
    cv.text(340, 76, run_time_str(rt), 42, fill=(255, 224, 102), anchor="lm", mono=True)

def chip(cv, txt, x, y, fg=(150, 255, 170), bg=(28, 32, 34)):
    cv.rect(x, y-34, x+56+len(txt)*20, y+36, fill=bg, rad=16)
    cv.text(x+28, y+1, txt, 34, fill=fg, anchor="lm")

def popup_achievement(cv, k, title, sub):
    k = ease_out_back(clamp(k))
    x1 = lerp(1980, 1340, k); x0 = x1 - 590
    cv.rect(x0, 152, x1, 268, fill=(255, 255, 255), outline=INK, ow=5, rad=24)
    cv.circle(x0+68, 210, 34, fill=GOLD, outline=INK, ow=4)
    cv.text(x0+68, 214, "★", 46, fill=INK)
    cv.text(x0+130, 186, "ACHIEVEMENT UNLOCKED", 26, fill=GREY, anchor="lm")
    cv.text(x0+130, 232, title, 38, fill=INK, anchor="lm")
    cv.text(x0+130, 254, sub, 24, fill=GREY, anchor="lm", bold=False)

def red_vignette(cv, k):
    if k <= 0: return
    from PIL import ImageDraw as ID
    a = int(80 * k)
    ov = Image.new("L", cv.img.size, 0)
    od = ID.Draw(ov)
    w, h = cv.img.size
    b = cv._s(110)
    od.rectangle([0, 0, w, b], fill=a); od.rectangle([0, h-b, w, h], fill=a)
    od.rectangle([0, 0, b, h], fill=a); od.rectangle([w-b, 0, w, h], fill=a)
    cv.img.paste(Image.new("RGB", cv.img.size, RED), (0, 0), ov)
    cv.d = ID.Draw(cv.img)

def darken(cv, k):
    if k <= 0: return
    from PIL import ImageDraw as ID
    mask = Image.new("L", cv.img.size, int(115 * k))
    cv.img.paste(Image.new("RGB", cv.img.size, (10, 10, 14)), (0, 0), mask)
    cv.d = ID.Draw(cv.img)

# ---------------- props ----------------
def sign_post(cv, x, y, txt, tilt=0, scale=1.0):
    s = scale
    cv.line([(x, y), (x, y-150*s)], 10*s, (120, 84, 50))
    bx, by = x, y-200*s
    w2, h2 = 215*s, 56*s
    if tilt:
        c, sn = math.cos(math.radians(tilt)), math.sin(math.radians(tilt))
        pts = [(bx+px*c-py*sn, by+px*sn+py*c) for px, py in [(-w2, -h2), (w2, -h2), (w2, h2), (-w2, h2)]]
        cv.poly(pts, fill=(222, 184, 135), outline=INK, ow=6)
    else:
        cv.rect(bx-w2, by-h2, bx+w2, by+h2, fill=(222, 184, 135), outline=INK, ow=6, rad=14)
    cv.text(bx, by, txt, int(52*s), fill=INK, rot=tilt)

def rock(cv, x, y, s=1.0):
    cv.poly([(x-70*s, y), (x-58*s, y-46*s), (x-14*s, y-72*s), (x+42*s, y-60*s), (x+72*s, y-20*s), (x+64*s, y)],
            fill=(170, 170, 175), outline=INK, ow=6)

def lever(cv, x, y, pulled, scale=1.0):
    s = scale
    cv.rect(x-70*s, y-46*s, x+70*s, y, fill=(90, 90, 98), outline=INK, ow=6, rad=12)
    a = math.radians(38)
    dx = math.sin(a)*130*s; dy = math.cos(a)*130*s
    hx = x - dx if pulled else x + dx
    hy = y - 30*s - dy
    cv.line([(x, y-30*s), (hx, hy)], 12*s, INK)
    cv.circle(hx, hy, 22*s, fill=RED, outline=INK, ow=5)
    cv.text(x, y-215*s, "G R A V I T Y", int(44*s), fill=INK)
    cv.text(x+4*s, y+52*s, "do not touch", int(30*s), fill=RED, rot=-4)

def plant(cv, x, y, s=1.0):
    cv.poly([(x-64*s, y), (x+64*s, y), (x+48*s, y-92*s), (x-48*s, y-92*s)], fill=(196, 120, 70), outline=INK, ow=6)
    for a in (-55, -20, 15, 50):
        r = math.radians(a)
        cv.line([(x, y-92*s), (x+math.sin(r)*96*s, y-92*s-math.cos(r)*150*s)], 10*s, (46, 139, 87))
    cv.circle(x, y-250*s, 30*s, fill=(46, 139, 87))

def chair(cv, x, y, s=1.0, k=0.0):
    s *= 1.15
    seatw, backh = 110*s, 130*s
    sy = y - 215*s
    fold = ease_in(clamp(k))
    spread = 1 - 0.85*fold
    cv.line([(x-seatw*spread, y), (x+seatw*spread, sy)], 12*s, INK)
    cv.line([(x+seatw*spread, y), (x-seatw*spread, sy)], 12*s, INK)
    if fold < 0.9:
        cv.line([(x-seatw*spread, sy), (x+seatw*spread, sy)], 16*s, INK)
    bag = fold*math.radians(80)
    bx0, by0 = x-seatw*spread, sy
    bx1 = bx0 + math.sin(bag)*backh; by1 = by0 - math.cos(bag)*backh
    cv.line([(bx0, by0), (bx1, by1)], 12*s, INK)

def taxbeast(cv, x, y, s=1.0, tilt=0.0, stomp_ph=0.0, eyes="angry"):
    cv.text(x, y-260*s, "TAXES", int(210*s), fill=RED, stroke=10, stroke_fill=(120, 10, 10), rot=tilt)
    ey = y - 435*s
    for ex in (-int(120*s), int(120*s)):
        cv.circle(x+ex, ey, 36*s, fill=(255, 255, 255), outline=INK, ow=6)
        if eyes == "angry":
            cv.line([(x+ex-30*s, ey-42*s), (x+ex+30*s, ey-16*s)], 9*s, INK)
            cv.dot(x+ex+(8 if ex < 0 else -8), ey+6*s, 13*s, INK)
        else:
            cv.dot(x+ex, ey+10*s, 13*s, INK)
            cv.line([(x+ex-26*s, ey-44*s), (x+ex+26*s, ey-48*s)], 8*s, INK)
    for lx, pho in ((-int(215*s), 0.0), (int(235*s), 0.5)):
        step = math.sin((stomp_ph+pho)*2*math.pi)
        fy = y - (34*s if step > 0 else 0)
        cv.line([(x+lx, y-150*s), (x+lx, fy)], 12*s, (120, 10, 10))

def receipt(cv, x, y, rot, s=1.0):
    w2, h2 = 50*s, 70*s
    c, sn = math.cos(rot), math.sin(rot)
    pts = [(x+px*c-py*sn, y+px*sn+py*c) for px, py in [(-w2, -h2), (w2, -h2), (w2, h2), (-w2, h2)]]
    cv.poly(pts, fill=(255, 255, 255), outline=INK, ow=4)
    for i in range(4):
        yy = -h2 + 26*s + i*32*s
        cv.line([(x+(-36*s)*c-yy*sn, y+(-36*s)*sn+yy*c),
                 (x+(36*s)*c-yy*sn, y+(36*s)*sn+yy*c)], 4, GREY)

def boss_bar(cv, frac):
    cv.rect(360, 150, 1560, 205, fill=(28, 28, 32), rad=18)
    cv.rect(372, 162, 372+1176*clamp(frac), 193, fill=RED, rad=12)
    cv.text(960, 130, "FOLDING CHAIR — FINAL BOSS", 34, fill=INK)
    cv.text(960, 248, "weakness: being sat on", 26, fill=GREY, bold=False)

def subscribe_btn(cv, x, y, s=1.0, pressed=False, t=0.0):
    sc = max(0.02, s * (1 + 0.05*math.sin(t*4)))
    w2, h2 = 330*sc, 88*sc
    col = (60, 190, 85) if pressed else RED
    cv.rect(x-w2, y-h2, x+w2, y+h2, fill=col, rad=int(40*sc))
    cv.poly([(x-w2+44*sc, y-34*sc), (x-w2+44*sc, y+34*sc), (x-w2+104*sc, y)], fill=(255, 255, 255))
    if sc > 0.35:
        cv.text(x+0.16*w2, y+4, ("SUBSCRIBED ✓" if pressed else "SUBSCRIBE"),
                max(10, int(54*sc)), fill=(255, 255, 255))

def dave(cv, x, y, **kw):
    rig_kw = {k: kw.pop(k) for k in ("scale", "lw", "flip") if k in kw}
    rig_kw.setdefault("scale", 1.3); rig_kw.setdefault("lw", 9)
    return Rig(cv, x, y, **rig_kw).draw(**kw)

# ================= SCENE BOUNDS =================
S0 = (0, 144); S1 = (144, 300); S2 = (300, 516); S3 = (516, 816)
S4 = (816, 1080); S5 = (1080, 1344); S6 = (1344, 1608)
RT0 = 144
SHAKES = [(212, 236, 14), (750, 774, 18), (1184, 1207, 20), (1286, 1312, 8)]
INVERT = (750, 1184)

def scene_title(cv, lf, f, events):
    cv.text(W/2, 380, "LIFE", 260, fill=(246, 244, 238))
    cv.rect(W/2-165, 520, W/2+175, 582, fill=RED, rad=14)
    cv.text(W/2+5, 552, "any% speedrun", 46, fill=(255, 255, 255))
    cv.text(W/2, 664, "rules: none.  regrets: pending.", 40, fill=(150, 150, 150), bold=False)
    if f == 8: sfx(events, f, "deep_boom", .6)
    for cf, num in ((96, "3"), (112, "2"), (128, "1")):
        k = (f - cf) / 14
        if 0 <= k < 1:
            cv.text(W/2, 850, num, int(150*(1+0.5*(1-k))), fill=GOLD if num == "1" else (240, 240, 240))
    if f == 96: sfx(events, f, "beep", .9)
    if f == 112: sfx(events, f, "beep", .9)
    if f == 128: sfx(events, f, "beep_hi", 1.0)

def scene_born(cv, lf, f, events, dust):
    cv.line([(0, GROUND), (W, GROUND)], 6, INK)
    x = 960
    if 0 <= lf < 20:
        cv.text(W/2, 330, "GO!", int(190*(1+0.15*(lf/20))), fill=GREEN, stroke=12, stroke_fill=(255, 255, 255))
        if lf == 0: sfx(events, f, "go", 1.0)
    fall_end = 68
    if lf < fall_end:
        k = clamp((lf-6) / (fall_end-6))
        y = lerp(120, GROUND, ease_in(k))
        dave(cv, x, y, squat=-0.55*k, mood="o", armL=(-150, -10), armR=(150, 10), legL=(6, 8), legR=(-6, 8))
        if lf in (30, 44, 58): sfx(events, f, "wind", .5)
    elif lf == fall_end:
        dave(cv, x, GROUND, squat=1.0, mood="flat")
        dust.burst(x, GROUND, 22, 150)
        sfx(events, f, "thud", 1.0)
    elif lf < 94:
        dave(cv, x, GROUND, squat=lerp(0.9, 0, ease_out_elastic((lf-fall_end)/26)), mood="o",
             armL=(-40, -20), armR=(40, 20))
    else:
        blink = (lf % 52) in (0, 1, 2)
        dave(cv, x, GROUND, mood="blink" if blink else "calm")
    if lf >= 78:
        ck = ease_out_back(clamp((lf-78)/12)) * clamp((156-lf)/14)
        if ck > 0:
            chip(cv, "BORN ✓  +00:00.8  (WR)", x=1240, y=lerp(-60, 190, ck))
        if lf == 82: sfx(events, f, "ding", .8)
    if 100 <= lf < 152:
        caption(cv, "spawned in.", size=54)

def scene_tutorial(cv, lf, f, events, dust):
    cv.line([(0, GROUND), (W, GROUND)], 6, INK)
    sign_x = 1330
    t_notice, t_skip = 96, 140
    if lf < 42:
        ph = lf * 0.17
        x = lerp(-180, 640, lf/42)
        lL, lR = run_cycle(ph, 32, 42)
        dave(cv, x, GROUND, armL=(-15, -22), armR=(15, 22), legL=lL, legR=lR, mood="calm", look=0.5)
    elif lf < t_notice + 26:
        x = 640
        if lf < t_notice:
            dave(cv, x, GROUND, mood="calm", look=0.9)
            caption(cv, "a wild TUTORIAL appears.", size=52)
        else:
            if lf == t_notice: sfx(events, f, "scratch", 1.0)
            dave(cv, x, GROUND, mood="flat", look=0.0)
            caption(cv, "…hard pass.", size=54)
            cv.text(x, 748, "[ press E to skip ]", 40, fill=BLUE)
    elif lf < t_skip:
        x = lerp(640, 760, ease_io((lf-(t_notice+26))/(t_skip-t_notice-26)))
        dave(cv, x, GROUND, squat=0.25, mood="grin", look=0.9, armL=(60, -40), armR=(60, -40))
        caption(cv, "*mashing E*", size=50)
        if lf in (t_notice+30, t_notice+36, t_notice+42): sfx(events, f, "pop", .6)
    else:
        k = clamp((lf - t_skip) / 54)
        x = lerp(760, 2260, ease_in(k))
        if x < 2100:
            for i, yy in enumerate((660, 790, 905)):
                cv.line([(x-260-i*30, yy), (x-110-i*30, yy)], 5, (205, 205, 205))
            lL, lR = run_cycle(lf*0.13, 60, 80); aL, aR = arm_swing(lf*0.13, 60)
            dave(cv, x, GROUND, squat=0.42, torso_lean=-24, legL=lL, legR=lR, armL=aL, armR=aR, mood="grin")
        if lf == t_skip:
            sfx(events, f, "whoosh", 1.0)
            dust.burst(760, GROUND, 12, 90)
    tips = lf - (t_skip + 20)
    if tips < 0:
        sign_post(cv, sign_x, GROUND, "TUTORIAL →")
    else:
        tk = clamp(tips/16)
        sign_post(cv, sign_x + ease_in(tk)*26, GROUND, "wait.", tilt=-ease_out(tk)*100)
        if tips == 16: sfx(events, f, "boing_soft", .8)
    if lf >= 180:
        popup_achievement(cv, (lf-180)/14, "TUTORIAL SKIPPED", "−30 seconds. coward.")
        if lf == 184: sfx(events, f, "ding", .8)

def scene_gravity(cv, lf, f, events, dust):
    cv.line([(0, GROUND), (W, GROUND)], 6, INK)
    t_pull, t_panic, t_on = 110, 180, 226
    pulled = lf >= t_pull
    floating = pulled and lf < t_on
    lever(cv, 1500, GROUND, floating)
    if lf < t_pull:
        if lf < 52:
            ph = lf*0.16
            x = lerp(-160, 660, lf/52)
            lL, lR = run_cycle(ph, 32, 42)
        else:
            x = lerp(660, 1160, (lf-52)/(t_pull-52))
            ph = lf*0.16
            lL, lR = run_cycle(ph, 26, 34)
        dave(cv, x, GROUND, legL=lL, legR=lR, mood="calm", look=0.6, armL=(-14, -20), armR=(14, 20))
        if lf > 58: caption(cv, "ooh, a lever.", size=50)
        rock(cv, 420, GROUND); sign_post(cv, 700, GROUND, "TUTORIAL →", scale=0.8)
    elif lf == t_pull:
        dave(cv, 1300, GROUND, torso_lean=20, mood="o", armL=(42, -50), armR=(42, -50), look=0.8, flip=True)
        sfx(events, f, "clunk", 1.0)
        rock(cv, 420, GROUND); sign_post(cv, 700, GROUND, "TUTORIAL →", scale=0.8)
    elif floating:
        ft = lf - t_pull
        fy = GROUND - ease_io(clamp(ft/70))*430
        fx = 1150 + math.sin(ft*0.045)*70
        wob = math.sin(ft*0.11)
        cv.text(330, 205, "gravity: OFF", 56, fill=BLUE, rot=-6)
        if ft == 6: sfx(events, f, "slideup", .9)
        if ft == 2: sfx(events, f, "boing_soft", .7)
        if lf < t_panic:
            dave(cv, fx, fy, air=True, mood="grin", torso_lean=wob*16,
                 armL=(-40+wob*20, -30), armR=(40-wob*20, 30), legL=(18+wob*14, 26), legR=(-22+wob*14, 30))
            if 20 < ft < 60: caption(cv, "…this is amazing.", size=54)
        else:
            pw = math.sin(ft*0.5)
            dave(cv, fx, fy - 14*pw, air=True, mood="scream", torso_lean=pw*26,
                 armL=(-70+pw*40, -20), armR=(70-pw*40, 20), legL=(28+pw*22, 34), legR=(-30-pw*20, 36), look=pw)
            caption(cv, "PUT IT BACK.", size=64, fill=RED)
            if lf == t_panic: sfx(events, f, "wobble", .9)
        ry = GROUND - ease_io(clamp(ft/80))*360 - math.sin(ft*0.07+2)*18
        rock(cv, 420, ry)
        sv = ease_io(clamp(ft/90))
        sign_post(cv, 700 + math.sin(ft*0.05)*40, GROUND - sv*320 - math.sin(ft*0.06+1)*22,
                  "TUTORIAL →", tilt=math.sin(ft*0.05)*14, scale=0.8)
    else:
        ft = lf - t_on
        if ft < 8:
            y = lerp(GROUND-430, GROUND, ease_in(ft/8))
            dave(cv, 1150, y, air=True, squat=-0.5, mood="scream", armL=(-120, -10), armR=(120, 10))
            if ft == 0: sfx(events, f, "slidedown", 1.0)
        elif ft == 8:
            dave(cv, 1150, GROUND, squat=1.0, mood="dead")
            dust.burst(1150, GROUND, 30, 170)
            sfx(events, f, "splat", 1.0)
        else:
            kk = ease_out_elastic(clamp((ft-8)/44))
            dave(cv, 1150, GROUND, squat=lerp(0.92, 0.12, kk), mood="dead" if ft < 44 else "flat",
                 armL=(-80, -10), armR=(80, 10))
            if ft > 50: caption(cv, "gravity: ON. lesson: learned(ish).", size=48)
        rock(cv, 420, GROUND); sign_post(cv, 700, GROUND, "TUTORIAL →", scale=0.8)
    if lf >= 252:
        popup_achievement(cv, (lf-252)/14, "PHYSICS = A SUGGESTION", "the devs are furious")
        if lf == 256: sfx(events, f, "ding", .9)

def scene_taxes(cv, lf, f, events, dust, scroll):
    t_alarm, t_dive, t_sniff, t_leave = 30, 150, 196, 226
    if lf < t_dive + 10:
        scroll[0] += 34 * (1 - ease_io(clamp((lf-t_dive)/26)))
    cv.line([(0, GROUND), (W, GROUND)], 6, INK)
    for i in range(14):
        gx = (i*260 + scroll[0]) % (W+300) - 150
        cv.line([(gx, 884), (gx+120, 884)], 4, (195, 195, 195))
    if lf > t_alarm + 24:
        for i in range(5):
            ph = lf*0.03 + i*1.7
            ry = 470 + math.sin(ph*2.3)*150 + i*70
            rx = ((scroll[0]*1.35 + i*430) % (W+500)) - 250
            receipt(cv, rx, ry, math.sin(ph*3)*0.6, 0.9)
    if t_alarm <= lf < t_dive + 30:
        red_vignette(cv, 0.5 + 0.4*math.sin(lf*0.5))
        if lf == t_alarm: sfx(events, f, "alarm", .9)
    bx = lerp(2650, 1470, ease_out(clamp((lf-t_alarm)/60))) if lf >= t_alarm else 2650
    if lf >= t_dive: bx = lerp(1070, 1030, ease_io(clamp((lf-t_dive)/50)))
    if lf >= t_leave: bx = lerp(1030, -1400, ease_io(clamp((lf-t_leave)/70)))
    confused = t_sniff <= lf < t_leave
    tilt = -8 + 8*math.sin((lf-t_sniff)*0.1) if confused else 0.0
    stomp = f2t(max(0, lf - t_alarm))*1.6
    if lf >= t_alarm and bx > -1500:
        taxbeast(cv, bx, GROUND, 1.15, tilt=tilt, stomp_ph=stomp,
                 eyes="confused" if confused else "angry")
        if lf in (t_alarm+34, t_alarm+70, t_alarm+106): sfx(events, f, "stomp", .8)
    if lf < t_alarm:
        dave(cv, 620, GROUND, mood="calm")
    elif lf < t_alarm + 24:
        dave(cv, 620, GROUND, mood="o", look=0.95, armL=(-30, -40), armR=(30, 40))
        caption(cv, "oh no.", size=54)
    elif lf < t_dive:
        ph = lf*0.16
        lL, lR = run_cycle(ph, 62, 85); aL, aR = arm_swing(ph, 70)
        dave(cv, 620, GROUND, legL=lL, legR=lR, armL=aL, armR=aR,
             mood="scream" if (lf//6) % 2 else "o", torso_lean=-14, look=-0.9, flip=True)
        if lf % 12 == 0: sfx(events, f, "step", .5)
        if t_alarm + 26 <= lf < t_dive - 16:
            caption(cv, "TAXES?! I JUST GOT HERE", size=56, fill=RED)
    elif lf < t_dive + 26:
        k = (lf - t_dive) / 26
        x = lerp(620, 330, ease_io(k)); y = GROUND - math.sin(k*math.pi)*170
        dave(cv, x, y, air=True, mood="o", armL=(-60, -20), armR=(60, 20), legL=(50, 60), legR=(-30, 50))
        if lf == t_dive: sfx(events, f, "whoosh", .8)
        if lf == t_dive + 25: sfx(events, f, "boing_soft", .6)
    else:
        r = Rig(cv, 330, GROUND, scale=1.3, lw=9, flip=True)
        r.draw(squat=0.55, mood="sweat", look=-0.85, armL=(-30, -30), armR=(24, -40))
        if confused: cv.text(330, 640, "*breathes in plant*", 34, fill=GREY, bold=False)
    if lf >= t_dive + 4:
        plant(cv, 330, GROUND, 1.35)
    if confused:
        cv.text(bx, 380, "?", 90, fill=RED, rot=math.sin((lf-t_sniff)*0.2)*10)
        if lf == t_sniff: sfx(events, f, "sniff", .8)
        caption(cv, "deduction: not found.", size=50)
    if lf >= t_leave + 4:
        caption(cv, "…he chose the plant.", size=54)
        if lf == t_leave + 8: sfx(events, f, "boing_soft", .6)

def scene_boss(cv, lf, f, events, dust):
    t_poke, t_snap, t_jump, t_sit, t_win = 56, 104, 170, 206, 232
    cv.line([(0, GROUND), (W, GROUND)], 6, INK)
    bar = lerp(0, 120, ease_io(clamp(lf/40)))
    if lf < t_win + 30:
        cv.rect(0, 0, W, bar, fill=(14, 14, 18))
        cv.rect(0, H-bar, W, H, fill=(14, 14, 18))
    boss_hp = 1.0 if lf < t_sit else lerp(1, 0.0, clamp((lf-t_sit)/(t_win-t_sit)))
    boss_bar(cv, boss_hp)
    cx = 1180
    if lf < t_poke:
        x = lerp(-140, 830, ease_io(lf/48)) if lf < 48 else 830
        dave(cv, x, GROUND, squat=0.12, torso_lean=14, legL=(26, 30), legR=(-18, 26),
             armL=(-6, -30), armR=(-6, -30), mood="o", look=0.8)
        chair(cv, cx, GROUND, k=0.0)
        if lf > 6: caption(cv, "*tiptoes in boss music*", size=48)
    elif lf < t_snap:
        chair(cv, cx, GROUND, k=0.0)
        dave(cv, 830, GROUND, torso_lean=30, armR=(72, -6), armL=(-20, -20), mood="flat", look=0.95)
        for pkf in (t_poke+8, t_poke+26, t_poke+44):
            if pkf <= lf < pkf + 9:
                cv.text(998, 726, "poke", 40, fill=GREY, rot=-8)
            if lf == pkf: sfx(events, f, "poke", .6)
    elif lf < t_snap + 12:
        chair(cv, cx, GROUND, k=1.0)
        dave(cv, 935, GROUND, torso_lean=-22, armR=(58, -78), armL=(-30, -30), mood="scream", look=0.9)
        cv.line([(1098, 742), (1134, 737)], 16, INK)
        if lf == t_snap:
            sfx(events, f, "clang", 1.0); sfx(events, f, "snap", .9)
        if t_snap <= lf < t_snap + 7:
            cv.text(cx+30, 620, "CLANG!", 92, fill=RED, rot=-6)
        if lf >= t_snap + 2:
            caption(cv, "ow.", size=62)
    elif lf < t_jump:
        hop = math.sin((lf - (t_snap+12))*0.32)
        chair(cv, cx - (lf-(t_snap+12))*4.4, GROUND - max(0.0, hop)*62, k=1.0)
        wob = math.sin((lf-t_snap)*0.5)
        dave(cv, 830, GROUND, mood="scream", squat=0.1+0.08*wob, armL=(-150, -10), armR=(150, 10),
             legL=(16, 20), legR=(-16, 20))
        if lf == t_snap + 14: sfx(events, f, "sting", .9)
        if lf % 16 == 0: sfx(events, f, "step", .5)
        caption(cv, "it MOVES?!", size=58, fill=RED)
    elif lf < t_sit:
        chair(cv, cx, GROUND, k=1.0)
        k = (lf - t_jump) / (t_sit - t_jump)
        x = lerp(830, cx+8, ease_io(k)); y = GROUND - math.sin(k*math.pi)*420
        dave(cv, x, y, air=True, torso_lean=-14 if k < .5 else 14, mood="scream" if k < .6 else "grin",
             armL=(-150, -10), armR=(150, 10), legL=(60, 70), legR=(-40, 60))
        if lf == t_jump: sfx(events, f, "slideup", .8)
    else:
        chair(cv, cx, GROUND, k=0.0)
        k2 = ease_out_elastic(clamp((lf-t_sit)/24))
        r = Rig(cv, cx+8, GROUND-238)
        r.draw(squat=0.2*k2, legL=(82, 84), legR=(-82, 84),
               armL=(-20, -30) if lf < t_win else (-150, -10),
               armR=(20, 30) if lf < t_win else (150, 10), mood="grin", look=0.2)
        if lf == t_sit:
            sfx(events, f, "sit_thump", 1.0); sfx(events, f, "boing_soft", .7)
            dust.burst(cx, GROUND, 10, 90)
        if lf < t_win - 6: caption(cv, "assert dominance: SIT", size=52)
        if lf == t_win: sfx(events, f, "tada", 1.0)
        if lf >= t_win + 14:
            popup_achievement(cv, (lf-t_win-14)/14, "BOSS DEFEATED", "via sitting. as prophesied.")
            if lf == t_win + 18: sfx(events, f, "ding", .8)
    dk = 1.0 if lf < t_win else lerp(1, 0, clamp((lf-t_win)/26))
    darken(cv, dk)

def scene_outro(cv, lf, f, events, conf, dust):
    t_rec, t_tpose, t_fall, t_card = 30, 60, 94, 170
    cv.line([(0, GROUND), (W, GROUND)], 6, INK)
    conf.step(); conf.draw(cv)
    if lf == 0: sfx(events, f, "confetti", .9)
    if lf < t_card:
        cv.text(W/2, 215, "FINAL TIME", 50, fill=GREY)
        cv.text(W/2, 330, "00:58.71", 130, fill=INK, mono=True)
        if lf > 36:
            pk = ease_out_elastic(clamp((lf-36)/30))
            cv.text(W/2, 470, "★ NEW WORLD RECORD ★", int(58*pk+8), fill=GOLD, stroke=8, stroke_fill=INK)
            if lf == 38: sfx(events, f, "tada", .9)
        if lf < t_tpose:
            dave(cv, W/2, GROUND, mood="wow" if 24 < lf < 54 else "grin",
                 armL=(-150, -10) if lf > 20 else (-12, -18), armR=(150, 10) if lf > 20 else (12, 18))
        elif lf < t_fall:
            kk = clamp((lf - t_tpose)/34)
            x = lerp(W/2, W/2-260, ease_in(kk))
            dave(cv, x, GROUND, torso_lean=-kk*70, mood="grin", armL=(-90, 0), armR=(90, 0),
                 legL=(10, 4), legR=(-10, 4))
            caption(cv, "T-pose to assert victory", size=48)
        else:
            ft = lf - t_fall
            if ft == 0:
                sfx(events, f, "thud", .8)
                dust.burst(W/2-260, GROUND, 16, 120)
            dave(cv, W/2-260, GROUND, squat=lerp(0.9, 0.7, ease_out_elastic(clamp(ft/40))),
                 mood="dead", armL=(-80, -10), armR=(80, 10))
            if ft > 24: caption(cv, "never doing that again. (he will)", size=48)
    else:
        pk = ease_out_back(clamp((lf - t_card)/22))
        cv.rect(W/2-700, 60, W/2+700, H-60, fill=(255, 255, 255), outline=INK, ow=6, rad=36)
        cv.text(W/2, 230, "GG.", 150, fill=INK)
        pressed = lf > t_card + 68
        subscribe_btn(cv, W/2, 520, s=pk, pressed=pressed, t=f2t(lf))
        if lf == t_card + 68: sfx(events, f, "bell", .9)
        if lf == t_card + 30: sfx(events, f, "pencil", .6)
        cv.text(W/2, 680, "or the chair wins.", 46, fill=GREY, bold=False)
        cv.text(W/2, 960, "LIFE any% — WORLD RECORD HOLDER: dave", 30, fill=GREY, bold=False)

def rt_of(f): return max(0.0, f2t(f - RT0)) * 1.2

def render_frame(f, events, state):
    if f < S1[0]:
        cv = Canvas(W, H, ss=state["ss"], bg=(16, 16, 20))
        scene_title(cv, f, f, events)
    else:
        cv = Canvas(W, H, ss=state["ss"], bg=PAPER)
        if f < S2[0]: scene_born(cv, f - S1[0], f, events, state["dust"])
        elif f < S3[0]: scene_tutorial(cv, f - S2[0], f, events, state["dust"])
        elif f < S4[0]: scene_gravity(cv, f - S3[0], f, events, state["dust"])
        elif f < S5[0]: scene_taxes(cv, f - S4[0], f, events, state["dust"], state["scroll"])
        elif f < S6[0]: scene_boss(cv, f - S5[0], f, events, state["dust"])
        else: scene_outro(cv, f - S6[0], f, events, state["conf"], state["dust"])
    state["dust"].step()
    state["dust"].draw(cv)
    for ef, ln in ((S1[0], 10), (S2[0], 10), (S3[0], 10), (S4[0], 10), (S5[0], 14), (S6[0], 14)):
        if ef <= f < ef + ln: darken(cv, 1 - (f - ef) / ln)
        elif ef - ln <= f < ef: darken(cv, (f - (ef - ln)) / ln)
    if S1[0] + 4 <= f < S6[0]:
        hud(cv, rt_of(f))
    if S6[0] <= f < S6[0] + 44:
        chip(cv, "PB!!", x=1560, y=lerp(-70, 190, ease_out_back(clamp((f - S6[0])/16))), fg=GOLD)
    frame = cv.frame()
    if f in INVERT:
        frame = ImageOps.invert(frame)
    dx, dy = shake_amp(f, SHAKES)
    if dx or dy:
        shifted = Image.new("RGB", (W, H), PAPER)
        shifted.paste(frame, (int(dx), int(dy)))
        frame = shifted
    return frame

def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "sheet"
    os.makedirs(OUT, exist_ok=True)
    events = []
    state = {"ss": int(os.environ.get("SS", "2")), "dust": Dust(), "conf": Confetti(130), "scroll": [0.0]}
    if mode == "sheet":
        from PIL import ImageDraw as ID, ImageFont as IF
        ts = [int(a) for a in sys.argv[2:]] or [40, 130, 185, 265, 375, 480, 600, 668, 706, 770,
                                                880, 990, 1055, 1185, 1202, 1290, 1332, 1420, 1590]
        tiles = []
        for t in ts:
            img = render_frame(t, events, state).resize((960, 540), Image.LANCZOS)
            tiles.append((t, img))
        cols = 3
        rows = math.ceil(len(tiles)/cols)
        sheet = Image.new("RGB", (960*cols, 540*rows), (255, 255, 255))
        sd = ID.Draw(sheet)
        fnt = IF.truetype(FONT_B, 40)
        for i, (t, img) in enumerate(tiles):
            x, y = (i % cols)*960, (i // cols)*540
            sheet.paste(img, (x, y))
            sd.rectangle([x+730, y+478, x+952, y+532], fill=(0, 0, 0))
            sd.text((x+742, y+506), f"f={t}  t={f2t(t):.1f}s", font=fnt, fill=(255, 255, 90), anchor="lm")
        sheet.save(os.path.join(OUT, "sheet.png"))
        print("sheet saved:", sheet.size)
    else:
        ffmpeg = os.popen("python3 -c 'import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())'").read().strip()
        NTOT = S6[1]
        cmd = [ffmpeg, "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
               "-i", "-", "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "17",
               "-pix_fmt", "yuv420p", "-movflags", "+faststart", f"{OUT}/silent.mp4"]
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        t0 = time.time()
        for f in range(NTOT):
            img = render_frame(f, events, state)
            proc.stdin.write(img.tobytes())
            if f and f % 120 == 0:
                el = time.time() - t0
                print(f"frame {f}/{NTOT}  elapsed {el:.0f}s  eta {el/f*NTOT:.0f}s", flush=True)
        proc.stdin.close(); proc.wait()
        with open(f"{OUT}/events.json", "w") as fh:
            json.dump({"fps": FPS, "frames": NTOT, "duration": NTOT/FPS, "sfx": events}, fh)
        print("render done. sfx events:", len(events))

if __name__ == "__main__":
    main()
