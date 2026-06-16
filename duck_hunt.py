# Duck Hunt Game

#IMPORTS
#importing necessary libraries
import cv2
import pygame
import numpy as np
import math
import random
import time
import collections

#  CONFIGURATION

WIN_W, WIN_H     = 1280, 720
FPS              = 60

NUM_DUCKS        = 5
AIM_RADIUS       = 72        # px: crosshair→duck centre to highlight duck
SHOOT_COOLDOWN   = 0.65      # sec between shots
GAME_DURATION    = 60        # seconds
MISS_LIMIT       = 6
POINTS_HIT       = 10
BULLET_SPEED     = 22

# Shoot detection: fingertip must drop this many px below its recent high
SHOOT_DROP_PX    = 50
EMA_ALPHA        = 0.28      # smoothing (lower = smoother but laggier)

# Skin colour ranges (HSV) - for hand detection
SKIN_HSV_LO1 = np.array([ 0,  25,  50], dtype=np.uint8)
SKIN_HSV_HI1 = np.array([22, 180, 255], dtype=np.uint8)
SKIN_HSV_LO2 = np.array([165, 25,  50], dtype=np.uint8)
SKIN_HSV_HI2 = np.array([180,180, 255], dtype=np.uint8)
# YCrCb range
SKIN_YCC_LO  = np.array([  0, 130,  75], dtype=np.uint8)
SKIN_YCC_HI  = np.array([255, 175, 130], dtype=np.uint8)

#  COLOURS
WHITE  = (255, 255, 255)
BLACK  = (  0,   0,   0)
RED    = (220,  30,  30)
GREEN  = ( 40, 200,  40)
YELLOW = (255, 215,   0)
CYAN   = (  0, 230, 230)
ORANGE = (255, 140,   0)
GRAY   = (130, 130, 130)
DARK   = ( 20,  20,  20)

# DUCKS
#Duck class to represent each duck in the game
class Duck:
    PALETTES = [
        ((200, 100,  30), (110, 55, 10)),   # brown
        (( 30, 130, 210), ( 15, 70,140)),   # blue
        ((200,  50,  50), (130, 25, 25)),   # red
        (( 50, 190,  50), ( 25,110, 25)),   # green
        ((170,  50, 200), ( 95, 25,120)),   # purple
    ]

    def __init__(self, idx=None):
        self.W = 76
        self.H = 55
        self.alive   = True
        self.wing_t  = random.uniform(0, math.pi * 2)
        pal = (idx % len(self.PALETTES)) if idx is not None else random.randint(0, 4)
        self.body_col, self.wing_col = self.PALETTES[pal]
        self._spawn()

    def _spawn(self):
        margin = 110
        self.x  = float(random.randint(margin, WIN_W - margin - self.W))
        self.y  = float(random.randint(90,  WIN_H - 120 - self.H))
        spd = random.uniform(2.5, 6.5)
        ang = random.uniform(-30, 30) * math.pi / 180
        self.vx = random.choice([-1, 1]) * spd * math.cos(ang)
        self.vy = spd * math.sin(ang)

    def update(self, dt):
        if not self.alive:
            return
        self.x += self.vx
        self.y += self.vy
        if self.x < 0 or self.x + self.W > WIN_W:
            self.vx *= -1
            self.x = max(0.0, min(self.x, float(WIN_W - self.W)))
        if self.y < 70 or self.y + self.H > WIN_H - 5:
            self.vy *= -1
            self.y = max(70.0, min(self.y, float(WIN_H - 5 - self.H)))
        self.wing_t += 11 * dt

    def center(self):
        return (int(self.x + self.W / 2), int(self.y + self.H / 2))

    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.W, self.H)

    def draw(self, surf, targeted):
        if not self.alive:
            return
        x, y   = int(self.x), int(self.y)
        cx, cy  = x + self.W // 2, y + self.H // 2
        wo      = int(math.sin(self.wing_t) * 12)
        right   = self.vx >= 0

        # Glow when targeted
        if targeted:
            gs = pygame.Surface((self.W + 48, self.H + 48), pygame.SRCALPHA)
            for r in range(5):
                pygame.draw.ellipse(
                    gs, (255, 255, 0, 85 - r * 16),
                    (r*2, r*2, self.W+48-r*4, self.H+48-r*4), 3)
            surf.blit(gs, (x - 24, y - 24))

        # Wings
        wc = self.wing_col
        if right:
            pygame.draw.ellipse(surf, wc, (cx-32, cy-18+wo, 36, 18))
            pygame.draw.ellipse(surf, wc, (cx-32, cy+wo,    36, 18))
        else:
            pygame.draw.ellipse(surf, wc, (cx- 4, cy-18+wo, 36, 18))
            pygame.draw.ellipse(surf, wc, (cx- 4, cy+wo,    36, 18))

        # Body
        pygame.draw.ellipse(surf, self.body_col, (cx-24, cy-16, 48, 32))
        # Head
        hx = cx + (17 if right else -17)
        pygame.draw.circle(surf, self.body_col, (hx, cy-12), 13)
        # Eye
        ex = hx + (5 if right else -5)
        pygame.draw.circle(surf, WHITE, (ex, cy-14), 4)
        pygame.draw.circle(surf, BLACK, (ex + (1 if right else -1), cy-14), 2)
        # Beak
        bx = hx + (21 if right else -21)
        pts = [
            (hx + (13 if right else -13), cy-12),
            (bx, cy-10),
            (bx, cy-5)
        ]
        pygame.draw.polygon(surf, YELLOW, pts)

#BULLETS
#Bullet class to represent each bullet fired by the player
class Bullet:
    def __init__(self, x, y, vx, vy):
        self.x, self.y = float(x), float(y)
        m = math.hypot(vx, vy) or 1
        self.vx = vx / m * BULLET_SPEED
        self.vy = vy / m * BULLET_SPEED
        self.alive = True
        self.trail = []

    def update(self):
        self.trail.append((int(self.x), int(self.y)))
        if len(self.trail) > 10:
            self.trail.pop(0)
        self.x += self.vx
        self.y += self.vy
        if not (0 <= self.x <= WIN_W and 0 <= self.y <= WIN_H):
            self.alive = False

    def draw(self, surf):
        for i, (tx, ty) in enumerate(self.trail):
            a = int(200 * i / max(len(self.trail), 1))
            pygame.draw.circle(surf, (255, a, 0), (tx, ty), 3)
        pygame.draw.circle(surf, YELLOW, (int(self.x), int(self.y)), 7)
        pygame.draw.circle(surf, WHITE,  (int(self.x), int(self.y)), 3)

#PARTICLES
#Particle class to represent the particles generated when a duck is hit
class Particle:
    def __init__(self, x, y, col):
        self.x, self.y = float(x), float(y)
        a = random.uniform(0, math.pi * 2)
        s = random.uniform(3, 12)
        self.vx = math.cos(a) * s
        self.vy = math.sin(a) * s - 5
        self.col = col
        self.life = 1.0
        self.sz = random.randint(4, 10)

    def update(self, dt):
        self.x  += self.vx
        self.y  += self.vy
        self.vy += 0.4
        self.life -= 1.9 * dt
        self.sz = max(1, self.sz - 0.08)

    def draw(self, surf):
        alpha = max(0, int(self.life * 240))
        s = pygame.Surface((self.sz * 2 + 2, self.sz * 2 + 2), pygame.SRCALPHA)
        pygame.draw.circle(s, (*self.col, alpha),
                           (self.sz + 1, self.sz + 1), int(self.sz))
        surf.blit(s, (int(self.x) - self.sz, int(self.y) - self.sz))

#FLOATING SCORE TEXT
#Floating Score Text class to represent the floating text that appears when a duck is hit or missed
class FloatText:
    def __init__(self, txt, x, y, col, font):
        self.txt = txt
        self.x, self.y = float(x), float(y)
        self.col = col
        self.life = 1.3
        self.font = font

    def update(self, dt):
        self.y   -= 1.7
        self.life -= dt

    def draw(self, surf):
        s = self.font.render(self.txt, True, self.col)
        s.set_alpha(int(max(0, self.life / 1.3) * 255))
        surf.blit(s, (int(self.x - s.get_width() / 2), int(self.y)))

