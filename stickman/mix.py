"""Audio engine: synth music + sfx + narration -> mix.wav -> mux with silent.mp4."""
import json, math, os, subprocess, wave
import numpy as np

SR = 44100
BASE = os.path.dirname(os.path.abspath(__file__))
FFMPEG = os.popen("python3 -c 'import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())'").read().strip()

def hz(m): return 440.0 * 2 ** ((m - 69) / 12)

def env(n, decay, attack=0.006):
    t = np.arange(n) / SR
    return np.minimum(1, t / attack) * np.exp(-decay * t)

def tone(f0, f1=None, dur=0.2, wave="sine", vol=0.5, decay=6.0, vib_hz=0.0, vib_amt=0.0, attack=0.006):
    n = max(1, int(dur * SR))
    t = np.arange(n) / SR
    if f1:
        f = f0 * (f1 / f0) ** (t / dur)
    else:
        f = np.full(n, float(f0))
    if vib_hz:
        f = f * (1 + vib_amt * np.sin(2 * np.pi * vib_hz * t))
    ph = np.cumsum(2 * np.pi * f / SR)
    s = np.sin(ph)
    if wave == "square":
        s = np.sign(s) * 0.55
    elif wave == "tri":
        s = (2 / np.pi) * np.arcsin(np.clip(s, -1, 1)) * 0.9
    return (s * env(n, decay, attack) * vol).astype(np.float32)

def noise(dur=0.2, vol=0.4, decay=8.0, lp=40, attack=0.005):
    n = max(1, int(dur * SR))
    s = np.random.uniform(-1, 1, n)
    if lp > 1:
        k = np.ones(int(lp)) / lp
        s = np.convolve(s, k, mode="same")
    s = s / (np.abs(s).max() + 1e-9)
    return (s * env(n, decay, attack) * vol).astype(np.float32)

def seq(parts):
    n = int(max(o * SR + len(a) for o, a in parts)) + 8
    out = np.zeros(n, dtype=np.float32)
    for o, a in parts:
        i = int(o * SR); out[i:i+len(a)] += a
    return out

def build_sfx():
    S = {}
    S["beep"] = tone(660, dur=0.09, wave="square", vol=0.5, decay=8)
    S["beep_hi"] = tone(990, dur=0.16, wave="square", vol=0.55, decay=7)
    S["go"] = seq([(0, tone(660, dur=0.1, wave="square", vol=0.5, decay=8)),
                   (0.1, tone(990, dur=0.28, wave="square", vol=0.55, decay=6))])
    S["deep_boom"] = seq([(0, tone(115, 38, dur=0.9, vol=0.9, decay=3.5)),
                          (0, noise(0.5, vol=0.25, decay=4, lp=24))])
    S["thud"] = seq([(0, tone(125, 45, dur=0.18, vol=0.95, decay=8)),
                     (0, noise(0.07, vol=0.4, decay=14, lp=16))])
    S["wind"] = noise(0.3, vol=0.16, decay=3, lp=200, attack=0.08)
    S["ding"] = seq([(0, tone(1319, dur=0.55, vol=0.4, decay=5)),
                     (0.02, tone(1976, dur=0.4, vol=0.18, decay=6))])
    S["scratch"] = seq([(0, noise(0.22, vol=0.4, decay=9, lp=500, attack=0.004)),
                        (0.02, tone(520, 120, dur=0.22, wave="square", vol=0.22, decay=6))])
    S["pop"] = tone(320, 950, dur=0.07, vol=0.5, decay=9)
    S["whoosh"] = noise(0.5, vol=0.5, decay=5, lp=48, attack=0.12)
    S["boing_soft"] = tone(300, 95, dur=0.5, vol=0.42, decay=3.5, vib_hz=22, vib_amt=0.18)
    S["clunk"] = seq([(0, tone(190, 70, dur=0.11, wave="square", vol=0.5, decay=10)),
                      (0, noise(0.04, vol=0.5, decay=16, lp=30))])
    S["slideup"] = tone(340, 1450, dur=0.75, vol=0.3, decay=1.2, attack=0.05)
    S["slidedown"] = tone(1500, 240, dur=0.55, vol=0.36, decay=4)
    S["wobble"] = tone(210, dur=0.85, vol=0.36, decay=3, vib_hz=11, vib_amt=0.3)
    S["splat"] = seq([(0, noise(0.24, vol=0.85, decay=10, lp=10)),
                      (0, tone(95, 38, dur=0.32, vol=0.5, decay=6))])
    S["alarm"] = seq([(i * 0.125, tone(520 if (i % 2 == 0) else 660, dur=0.125,
                      wave="square", vol=0.22, decay=3, attack=0.02)) for i in range(13)])
    S["stomp"] = seq([(0, tone(75, 40, dur=0.16, vol=0.7, decay=8)),
                      (0, noise(0.05, vol=0.3, decay=12, lp=14))])
    S["step"] = seq([(0, noise(0.035, vol=0.2, decay=18, lp=60)),
                     (0, tone(150, dur=0.05, vol=0.15, decay=12))])
    S["sniff"] = seq([(0, noise(0.22, vol=0.3, decay=4, lp=180, attack=0.1)),
                      (0.22, noise(0.16, vol=0.35, decay=5, lp=220, attack=0.06))])
    S["poke"] = tone(880, 480, dur=0.06, vol=0.35, decay=10)
    S["clang"] = seq([(0, tone(1175, dur=0.5, wave="square", vol=0.4, decay=7)),
                      (0, tone(1568, dur=0.35, vol=0.28, decay=9)),
                      (0, noise(0.03, vol=0.7, decay=18, lp=8)),
                      (0.01, tone(180, 70, dur=0.25, vol=0.4, decay=8))])
    S["snap"] = seq([(0, noise(0.02, vol=0.9, decay=22, lp=6)),
                     (0.008, tone(2200, dur=0.04, wave="square", vol=0.25, decay=16))])
    S["sting"] = seq([(0, tone(hz(70), dur=1.0, vol=0.2, decay=2.5, attack=0.15)),
                      (0, tone(hz(64), dur=1.0, vol=0.2, decay=2.5, attack=0.15)),
                      (0, tone(hz(70) * 1.5, dur=0.9, vol=0.1, decay=2.5, attack=0.15))])
    S["sit_thump"] = seq([(0, tone(160, 58, dur=0.16, vol=0.6, decay=9)),
                          (0, noise(0.05, vol=0.25, decay=14, lp=20))])
    S["tada"] = seq([(o, tone(hz(m), dur=0.5, wave="tri", vol=0.4, decay=4)) for o, m in
                     [(0, 72), (0.09, 76), (0.18, 79), (0.27, 84)]])
    S["confetti"] = seq([(0, noise(0.35, vol=0.3, decay=6, lp=90, attack=0.01))] +
                        [(o, tone(f, f * 1.4, dur=0.12, vol=0.16, decay=8))
                         for o, f in [(0.05, 1200), (0.13, 1600), (0.21, 1400)]])
    S["bell"] = seq([(0, tone(1568, dur=0.9, vol=0.42, decay=4)),
                     (0, tone(2093, dur=0.6, vol=0.2, decay=5)),
                     (0, tone(2637, dur=0.4, vol=0.1, decay=5))])
    S["pencil"] = noise(0.22, vol=0.14, decay=7, lp=140, attack=0.02)
    return S

def place(bus, sig, t):
    i = int(t * SR)
    j = min(len(bus), i + len(sig))
    if 0 <= i < j:
        bus[i:j] += sig[:j - i]

def kick(vol=0.5):  return seq([(0, tone(150, 45, dur=0.1, vol=vol, decay=10))])
def hat(vol=0.07):  return noise(0.035, vol=vol, decay=20, lp=3)
def snare(vol=0.2): return seq([(0, noise(0.1, vol=vol, decay=12, lp=60)),
                                (0, tone(190, dur=0.07, vol=vol * 0.6, decay=12))])
def bass_n(m, d=0.4, vol=0.3):  return tone(hz(m), dur=d, wave="tri", vol=vol, decay=4, attack=0.01)
def pluck(m, d=0.3, vol=0.2, decay=8):
    return seq([(0, tone(hz(m), dur=d, wave="square", vol=vol, decay=decay)),
                (0, tone(hz(m) * 2, dur=d * 0.6, vol=vol * 0.25, decay=decay + 2))])

def build_music(dur):
    n = int((dur + 0.5) * SR)
    m = np.zeros(n, dtype=np.float32)
    beat = 60.0 / 126.0
    eth = beat / 2
    rng = np.random.default_rng(4)
    t = 0.2
    while t < 5.9:
        place(m, pluck(60 if (int(t * 2) % 2 == 0) else 67, d=0.3, vol=0.1, decay=5), t)
        t += 0.5
    def bounce(t0, t1, roots=(36, 36, 45, 41, 43)):
        t = t0; i = 0
        penta = [72, 74, 76, 79, 81, 84]
        mel = 72
        while t < t1:
            bar_pos = (t - t0) % (beat * 4)
            if bar_pos < 1e-6:
                place(m, kick(), t); place(m, bass_n(roots[(i // 4) % len(roots)], d=beat * 0.9), t)
            if abs(bar_pos - beat * 2) < 1e-6:
                place(m, snare(0.12), t)
            place(m, hat(), t)
            if rng.random() < 0.62:
                mel = int(np.clip(mel + rng.choice([-3, -2, 0, 2, 3]), 69, 88))
                note = min(penta, key=lambda p: abs(p - mel))
                place(m, pluck(note, vol=0.13), t)
            t += eth; i += 1
    bounce(6.0, 21.5)
    t = 21.5
    while t < 26.1:
        if rng.random() < 0.5:
            place(m, pluck(int(rng.choice([76, 79, 83])), vol=0.1, decay=6), t)
        if int((t - 21.5) / eth) % 8 == 0:
            place(m, bass_n(36, d=0.5, vol=0.16), t)
        t += eth
    for k in range(int((28.9 - 26.2) / 0.16)):
        t = 26.2 + k * 0.16
        for octv, v in ((0, 0.09), (12, 0.035)):
            place(m, tone(hz([60, 64, 67, 71][k % 4] + octv), dur=0.5, vol=v, decay=1.6, attack=0.1), t)
    bounce(29.9, 33.9)
    t = 34.0; i = 0
    roots = [33, 33, 31, 29]
    while t < 44.9:
        bar = int((t - 34.0) / beat) % 4
        place(m, bass_n(roots[bar] + 12, d=0.18, vol=0.22), t)
        if i % 2 == 0: place(m, kick(0.35), t)
        if i % 4 == 2: place(m, snare(0.16), t)
        place(m, hat(0.09), t + eth * 0.5)
        if rng.random() < 0.4:
            place(m, pluck(int(rng.choice([57, 60, 64, 67])), vol=0.08, decay=10), t)
        t += eth; i += 1
    t = 45.0
    while t < 56.2:
        place(m, tone(hz(33), dur=beat * 2, vol=0.09, decay=0.8, attack=0.2), t)
        place(m, tone(hz(40), dur=beat * 2, vol=0.06, decay=0.8, attack=0.2), t)
        place(m, seq([(0, tone(85, 40, dur=0.18, vol=0.34, decay=7))]), t)
        if int((t - 45.0) / beat) % 4 == 3:
            place(m, pluck(45, vol=0.1, decay=5), t + beat * 0.5)
        t += beat
    for ci, (tt, chord) in enumerate([(56.3, [60, 64, 67]), (56.9, [65, 69, 72]),
                                      (57.5, [67, 71, 74]), (58.1, [72, 76, 79, 84])]):
        for k, mn in enumerate(chord + [chord[-1] + 12]):
            place(m, pluck(mn, vol=0.16, decay=4), tt + k * 0.07)
        place(m, kick(0.4), tt)
    t = 58.6
    while t < 62.8:
        place(m, kick(0.3), t); place(m, hat(0.08), t + eth)
        place(m, bass_n([36, 41, 43, 36][int((t - 58.6) / beat) % 4], d=0.3, vol=0.2), t)
        if rng.random() < 0.55:
            place(m, pluck(int(rng.choice([72, 76, 79, 84, 88])), vol=0.12), t + eth)
        t += beat
    t = 63.0
    while t < dur:
        place(m, pluck(int(rng.choice([60, 64, 67, 72, 76])), vol=0.09, decay=5), t)
        t += beat
    return m

def decode_mp3(path, atempo=None):
    cmd = [FFMPEG, "-v", "error", "-i", path]
    if atempo:
        cmd += ["-filter:a", f"atempo={atempo}"]
    cmd += ["-f", "s16le", "-ac", "1", "-ar", str(SR), "-"]
    out = subprocess.run(cmd, capture_output=True).stdout
    return np.frombuffer(out, dtype=np.int16).astype(np.float32) / 32768.0

def main():
    meta = json.load(open(f"{BASE}/out/events.json"))
    dur = meta["duration"] + 0.4
    n = int(dur * SR)
    sfx_bus = np.zeros(n, dtype=np.float32)
    voice_bus = np.zeros(n, dtype=np.float32)
    duck = np.zeros(n, dtype=np.float32)
    S = build_sfx()
    missing = set()
    for t, name, gain in meta["sfx"]:
        if name not in S:
            missing.add(name); continue
        place(sfx_bus, S[name] * gain, t)
    if missing: print("MISSING SFX:", missing)
    music = build_music(meta["duration"])
    if len(music) < n:
        music = np.pad(music, (0, n - len(music)))
    else:
        music = music[:n]
    VOICES = [(0.2, "v01", 1.45), (8.35, "v02", None), (14.2, "v03", None),
              (22.1, "v04", None), (28.15, "v05", 1.5), (35.1, "v06", None),
              (42.6, "v07", None), (45.8, "v08", None), (54.9, "v09", None),
              (59.2, "v10", 1.12)]
    for t, vid, atempo in VOICES:
        p = f"{BASE}/voice/{vid}.mp3"
        if not os.path.exists(p):
            print("missing voice", vid); continue
        a = decode_mp3(p, atempo) * 1.05
        print(f"{vid}: start {t}s dur {len(a)/SR:.2f}s")
        place(voice_bus, a, t)
        i0 = max(0, int((t - 0.25) * SR)); i1 = min(n, int((t + len(a) / SR + 0.35) * SR))
        duck[i0:i1] = 1.0
    k = np.ones(int(0.18 * SR)) / int(0.18 * SR)
    duck = np.convolve(duck, k, mode="same")
    duck = np.clip(duck, 0, 1)
    master = music * (0.52 - 0.34 * duck) + sfx_bus * (1 - 0.3 * duck) + voice_bus
    master = np.tanh(master * 1.15)
    peak = np.abs(master).max()
    if peak > 0: master = master / peak * 0.96
    stereo = np.stack([master, master], axis=1)
    with wave.open(f"{BASE}/out/mix.wav", "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((stereo * 32767).astype(np.int16).tobytes())
    print("mix.wav written", master.shape)
    out_mp4 = f"{BASE}/out/final.mp4"
    r = subprocess.run([FFMPEG, "-y", "-v", "error", "-i", f"{BASE}/out/silent.mp4",
                        "-i", f"{BASE}/out/mix.wav", "-c:v", "copy", "-c:a", "aac",
                        "-b:a", "192k", "-movflags", "+faststart", out_mp4], capture_output=True, text=True)
    print("mux rc:", r.returncode, r.stderr[-200:] if r.stderr else "")
    print("final.mp4 size:", os.path.getsize(out_mp4))

if __name__ == "__main__":
    main()
