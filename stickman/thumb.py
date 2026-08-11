"""YouTube thumbnail 1280x720."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from core import *
import main as M
from PIL import Image

cv = Canvas(1920, 1080, ss=1)
for i, x in enumerate(range(120, 1900, 320)):
    cv.circle(x, 140 + (i % 3) * 60, 40, outline=(225, 223, 215), ow=8)
cv.line([(0, M.GROUND), (1920, M.GROUND)], 6, INK)
M.rock(cv, 1580, 620)
M.sign_post(cv, 1650, M.GROUND, "wait.", tilt=-16, scale=0.9)
M.taxbeast(cv, 470, M.GROUND, 1.45, stomp_ph=0.3)
M.chair(cv, 1290, M.GROUND, k=1.0)
M.dave(cv, 1290, M.GROUND - 210, squat=-0.15, mood="grin", armL=(-160, -10), armR=(160, 10),
       legL=(30, 40), legR=(-30, 40), look=0.2)
cv.text(960, 210, "I SPEEDRAN LIFE", 190, fill=INK, stroke=16, stroke_fill=(255, 255, 255))
cv.text(960, 360, "00:58.71", 96, fill=RED, stroke=6, stroke_fill=(255, 255, 255), mono=True)
cv.text(960, 530, "★ WORLD RECORD ★", 78, fill=GOLD, stroke=10, stroke_fill=INK)
cv.frame().resize((1280, 720), Image.LANCZOS).save(os.path.join(M.OUT, "thumbnail.png"))
print("thumbnail saved")
