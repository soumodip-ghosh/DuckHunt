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

# FINGER TRACKER
# Uses OpenCV to track the player's index fingertip in real-time from webcam feed.
class FingerTracker:
    """
    Tracks your index fingertip using refined contour analysis.

    Pipeline:
      1. Skin segmentation (HSV + YCrCb)
      2. Motion foreground detection to isolate hand
      3. Find hand contour (largest moving object)
      4. Use convex defects to identify pointing finger tip
      5. EMA-smooth position across frames
      6. Detect downward "flick" gesture = shoot
    """

    def __init__(self):
        self.tip_screen  = None      # (x, y) in WIN_W × WIN_H coords
        self.hand_found  = False
        self._ema_x      = None
        self._ema_y      = None
        self._y_history  = collections.deque(maxlen=14)
        self._shoot_armed = False
        self.shoot_now   = False
        self._last_shot  = 0.0
        # Background subtractor to isolate moving hand (not face)
        self._bgsub = cv2.createBackgroundSubtractorMOG2(
            history=200, varThreshold=60, detectShadows=False)
        self._frame_count = 0

    def _skin_mask(self, frame):
        """Create skin mask using HSV + YCrCb"""
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        ycc = cv2.cvtColor(frame, cv2.COLOR_BGR2YCrCb)

        m1 = cv2.inRange(hsv, SKIN_HSV_LO1, SKIN_HSV_HI1)
        m2 = cv2.inRange(hsv, SKIN_HSV_LO2, SKIN_HSV_HI2)
        m3 = cv2.inRange(ycc, SKIN_YCC_LO,  SKIN_YCC_HI)

        mask = cv2.bitwise_or(m1, m2)
        mask = cv2.bitwise_and(mask, m3)
        return mask

    def _find_fingertip(self, hand_contour, frame_h, frame_w):
        """
        Find the topmost pointed finger using convex hull defects.
        Returns (x, y) or None if no clear fingertip found.
        """
        if len(hand_contour) < 5:
            return None

        hull = cv2.convexHull(hand_contour, returnPoints=False)
        if len(hull) < 3:
            return None

        # Get defects (valleys between fingers)
        defects = cv2.convexityDefects(hand_contour, hull)
        if defects is None or len(defects) < 2:
            return None

        # Find the topmost point in hand contour
        # (most likely to be the pointing finger tip)
        pts = hand_contour[:, 0, :]
        top_point = pts[pts[:, 1].argmin()]
        return tuple(top_point)

    def process(self, frame):
        """
        Expects a BGR frame already flipped (mirrored).
        Updates self.tip_screen, self.hand_found, self.shoot_now.
        Returns annotated frame for display.
        """
        self.shoot_now = False
        h, w = frame.shape[:2]
        self._frame_count += 1

        # Get skin mask
        skin_mask = self._skin_mask(frame)

        # Get foreground (moving objects only - this isolates hand from static face)
        fg = self._bgsub.apply(frame, learningRate=0.003)
        fg = cv2.threshold(fg, 100, 255, cv2.THRESH_BINARY)[1]

        # Combine: skin color AND motion = hand
        hand_mask = cv2.bitwise_and(skin_mask, fg)

        # Morphological cleanup
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
        hand_mask = cv2.morphologyEx(hand_mask, cv2.MORPH_OPEN, kernel, iterations=2)
        hand_mask = cv2.morphologyEx(hand_mask, cv2.MORPH_CLOSE, kernel, iterations=2)
        hand_mask = cv2.dilate(hand_mask, kernel, iterations=2)

        # Find contours
        cnts, _ = cv2.findContours(hand_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not cnts:
            self.hand_found = False
            return frame

        # Get largest contour = hand
        hand = max(cnts, key=cv2.contourArea)
        area = cv2.contourArea(hand)

        # Filter: hand should be reasonably large (not noise)
        if area < 3000 or area > 80000:
            self.hand_found = False
            return frame

        self.hand_found = True

        # Find fingertip
        tip = self._find_fingertip(hand, h, w)
        if tip is None:
            self.hand_found = False
            return frame

        fx, fy = tip

        # EMA smooth
        alpha = EMA_ALPHA
        if self._ema_x is None:
            self._ema_x, self._ema_y = float(fx), float(fy)
        else:
            self._ema_x = alpha * fx + (1 - alpha) * self._ema_x
            self._ema_y = alpha * fy + (1 - alpha) * self._ema_y

        sx, sy = int(self._ema_x), int(self._ema_y)

        # Clamp to frame bounds
        sx = max(0, min(sx, w - 1))
        sy = max(0, min(sy, h - 1))

        # Map to game screen (frame already mirrored)
        self.tip_screen = (
            int(sx / w * WIN_W),
            int(sy / h * WIN_H)
        )

        # Shoot detection: downward flick
        self._y_history.append(sy)
        now = time.time()
        if len(self._y_history) >= 6:
            recent_min = min(list(self._y_history)[-8:])
            drop = sy - recent_min        # positive = moved down
            if drop > SHOOT_DROP_PX:
                if not self._shoot_armed and (now - self._last_shot) > SHOOT_COOLDOWN:
                    self.shoot_now    = True
                    self._shoot_armed = True
                    self._last_shot   = now
            else:
                if drop < SHOOT_DROP_PX * 0.3:
                    self._shoot_armed = False   # reset: finger back up → ready again

        # Draw annotations on frame
        # Draw hand contour
        hull_pts = cv2.convexHull(hand)
        cv2.drawContours(frame, [hull_pts], -1, (0, 200, 255), 2)

        # Highlight fingertip
        cv2.circle(frame, (sx, sy), 12, (0, 255, 0), -1)
        cv2.circle(frame, (sx, sy), 16, (255, 255, 255), 2)
        cv2.putText(frame, "TIP", (sx + 14, sy - 6),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        # Show shoot-armed state
        if self._shoot_armed:
            cv2.putText(frame, "READY", (sx + 14, sy + 18),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 100, 255), 2)

        return frame

# MAIN GAME CLASS
# Initializes game, handles main loop, rendering, and integrates finger tracking and shooting mechanics.
class DuckHuntGame:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIN_W, WIN_H))
        pygame.display.set_caption("🎮 Duck Hunt — Finger Tracking")
        self.clock = pygame.time.Clock()

        self.font_lg  = pygame.font.SysFont("Arial", 56, bold=True)
        self.font_md  = pygame.font.SysFont("Arial", 34, bold=True)
        self.font_sm  = pygame.font.SysFont("Arial", 22)
        self.font_xs  = pygame.font.SysFont("Arial", 18)
        self.font_hit = pygame.font.SysFont("Arial", 30, bold=True)

        # Open webcam at game resolution
        self.cap = cv2.VideoCapture(0)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH,  WIN_W)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, WIN_H)
        self.cap.set(cv2.CAP_PROP_FPS, 30)

        self.tracker = FingerTracker()
        self.reset()
    
    # Reset game state for a new session
    def reset(self):
        self.score     = 0
        self.misses    = 0
        self.shots     = 0
        self.hits      = 0
        self.start_t   = time.time()
        self.state     = "playing"
        self.aim       = (WIN_W // 2, WIN_H // 2)
        self.targeted  = None
        self.ducks     = [Duck(i) for i in range(NUM_DUCKS)]
        self.bullets   = []
        self.particles = []
        self.floats    = []
        self._flash    = 0.0
    
    #HUD bar at the top showing score, time, and misses
    def _draw_hud(self):
        elapsed   = time.time() - self.start_t
        remaining = max(0.0, GAME_DURATION - elapsed)

        bar = pygame.Surface((WIN_W, 58), pygame.SRCALPHA)
        bar.fill((0, 0, 0, 175))
        self.screen.blit(bar, (0, 0))

        # Score
        sc = self.font_md.render(f"🦆  {self.score} pts", True, YELLOW)
        self.screen.blit(sc, (18, 10))

        # Lives (filled circles)
        for i in range(MISS_LIMIT):
            col = RED if i >= (MISS_LIMIT - self.misses) else (55, 55, 55)
            pygame.draw.circle(self.screen, col,
                               (WIN_W // 2 - MISS_LIMIT * 22 + i * 44, 28), 14)
        lbl = self.font_xs.render("misses", True, GRAY)
        self.screen.blit(lbl, (WIN_W // 2 - lbl.get_width() // 2, 46))

        # Timer
        tc = RED if remaining < 10 else WHITE
        tt = self.font_md.render(f"⏱  {remaining:.1f}s", True, tc)
        self.screen.blit(tt, (WIN_W - tt.get_width() - 18, 10))

        # Accuracy (bottom left)
        acc = int(self.hits / max(self.shots, 1) * 100)
        at  = self.font_xs.render(
            f"Accuracy {acc}%  ·  Shots {self.shots}  ·  Hits {self.hits}",
            True, (210, 210, 210))
        self.screen.blit(at, (18, WIN_H - 26))

    # Draw crosshair at the aiming position
    def _draw_crosshair(self, targeted):
        ax, ay = int(self.aim[0]), int(self.aim[1])
        col    = YELLOW if targeted else CYAN
        t      = time.time()

        # Outer ring
        pygame.draw.circle(self.screen, col, (ax, ay), 32, 2)
        # Centre dot
        pygame.draw.circle(self.screen, col, (ax, ay), 6)
        # Arms
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            pygame.draw.line(self.screen, col,
                             (ax + dx * 10, ay + dy * 10),
                             (ax + dx * 30, ay + dy * 30), 2)
        # Pulsing lock ring
        if targeted:
            pulse = int(abs(math.sin(t * 8)) * 12)
            s = pygame.Surface((WIN_W, WIN_H), pygame.SRCALPHA)
            pygame.draw.circle(s, (255, 215, 0, 90),
                               (ax, ay), AIM_RADIUS + pulse, 2)
            self.screen.blit(s, (0, 0))
    
    #Shoot flash when firing a shot
    def _shoot_flash(self, dt):
        if self._flash > 0:
            fl = pygame.Surface((WIN_W, WIN_H), pygame.SRCALPHA)
            fl.fill((255, 255, 180, int(self._flash * 90)))
            self.screen.blit(fl, (0, 0))
            self._flash = max(0.0, self._flash - dt * 5)
    
    #Instructions screen
    def _draw_instructions(self):
        lines = [
            "☝  Hold index finger UP  →  aim crosshair",
            "↙  Flick finger DOWN     →  SHOOT",
        ]
        y = WIN_H - 68
        for ln in lines:
            s  = self.font_xs.render(ln, True, (235, 235, 235))
            bg = pygame.Surface((s.get_width() + 16, s.get_height() + 6), pygame.SRCALPHA)
            bg.fill((0, 0, 0, 140))
            self.screen.blit(bg, (14, y))
            self.screen.blit(s,  (22, y + 3))
            y += s.get_height() + 6

    #Hand status indicator
    def _draw_hand_status(self):
        found = self.tracker.hand_found
        col   = GREEN if found else RED
        txt   = "✋ Hand detected — aim & flick to shoot" if found \
                else "✋ Show your index finger to the camera"
        s  = self.font_xs.render(txt, True, col)
        bg = pygame.Surface((s.get_width() + 16, s.get_height() + 6), pygame.SRCALPHA)
        bg.fill((0, 0, 0, 150))
        self.screen.blit(bg, (14, 62))
        self.screen.blit(s,  (22, 65))

    #Game over overlay
    def _draw_gameover(self):
        ov = pygame.Surface((WIN_W, WIN_H), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 185))
        self.screen.blit(ov, (0, 0))

        acc  = int(self.hits / max(self.shots, 1) * 100)
        rows = [
            ("GAME OVER",          self.font_lg, RED),
            (f"Score: {self.score}", self.font_md, YELLOW),
            (f"Ducks hit: {self.hits}", self.font_md, WHITE),
            (f"Accuracy: {acc}%",  self.font_sm, CYAN),
            ("",                   self.font_sm, WHITE),
            ("Press  R  to Restart", self.font_md, GREEN),
            ("Press  Q  to Quit",  self.font_sm, GRAY),
        ]
        total_h = sum(f.get_height() + 10 for _, f, _ in rows)
        y = (WIN_H - total_h) // 2
        for txt, font, col in rows:
            s = font.render(txt, True, col)
            s.set_alpha(235)
            self.screen.blit(s, ((WIN_W - s.get_width()) // 2, y))
            y += font.get_height() + 10
    
    # Convert OpenCV BGR frame to Pygame surface
    @staticmethod
    def _cv2pg(frame):
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        return pygame.surfarray.make_surface(rgb.swapaxes(0, 1))
    
    # Main game loop
    def run(self):
        while True:
            dt = self.clock.tick(FPS) / 1000.0

            # Events handling
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    self._quit(); return
                if ev.type == pygame.KEYDOWN:
                    if ev.key in (pygame.K_q, pygame.K_ESCAPE):
                        self._quit(); return
                    if ev.key == pygame.K_r and self.state == "gameover":
                        self.reset()

            # Webcam capture
            ret, frame = self.cap.read()
            cam_surf   = None
            if ret:
                frame    = cv2.flip(frame, 1)                 # mirror
                frame    = cv2.resize(frame, (WIN_W, WIN_H))  # fill window
                frame    = self.tracker.process(frame)        # track & annotate
                cam_surf = self._cv2pg(frame)

            # Update aim from tracker
            if self.tracker.hand_found and self.tracker.tip_screen:
                self.aim = self.tracker.tip_screen

            # Game logic 
            if self.state == "playing":
                elapsed = time.time() - self.start_t
                if elapsed >= GAME_DURATION:
                    self.state = "gameover"

                # Replenish ducks
                alive = [d for d in self.ducks if d.alive]
                while len(alive) < NUM_DUCKS:
                    self.ducks.append(Duck())
                    alive = [d for d in self.ducks if d.alive]

                # Find targeted duck
                self.targeted = None
                best = AIM_RADIUS
                for d in self.ducks:
                    if not d.alive: continue
                    dc   = d.center()
                    dist = math.hypot(self.aim[0] - dc[0], self.aim[1] - dc[1])
                    if dist < best:
                        best = dist
                        self.targeted = d

                # Shoot
                if self.tracker.shoot_now:
                    self.shots  += 1
                    self._flash  = 1.0
                    bx, by = self.aim
                    if self.targeted:
                        dc = self.targeted.center()
                        vx, vy = dc[0] - bx, dc[1] - by
                    else:
                        self.misses += 1
                        vx, vy = 0, -1
                        self.floats.append(
                            FloatText("MISS!", bx, by - 40, RED, self.font_hit))
                        if self.misses >= MISS_LIMIT:
                            self.state = "gameover"
                    self.bullets.append(Bullet(bx, by, vx, vy))

                # Update & collision
                for b in self.bullets: b.update()
                for b in self.bullets:
                    if not b.alive: continue
                    for d in self.ducks:
                        if not d.alive: continue
                        if d.rect().collidepoint(b.x, b.y):
                            b.alive = False
                            d.alive = False
                            self.score += POINTS_HIT
                            self.hits  += 1
                            dc = d.center()
                            for _ in range(26):
                                self.particles.append(Particle(dc[0], dc[1], d.body_col))
                            for _ in range(12):
                                self.particles.append(Particle(dc[0], dc[1], YELLOW))
                            self.floats.append(
                                FloatText(f"+{POINTS_HIT}", dc[0], dc[1]-38,
                                          YELLOW, self.font_hit))
                            break
                self.bullets = [b for b in self.bullets if b.alive]

                for d in self.ducks: d.update(dt)
                for p in self.particles: p.update(dt)
                self.particles = [p for p in self.particles if p.life > 0]
                for f in self.floats: f.update(dt)
                self.floats = [f for f in self.floats if f.life > 0]

            # Render 
            self.screen.fill(BLACK)

            # 1. Webcam feed = entire background (you + room visible)
            if cam_surf:
                self.screen.blit(cam_surf, (0, 0))
            else:
                self.screen.fill((25, 25, 35))

            # 2. Light vignette so ducks stand out
            vig = pygame.Surface((WIN_W, WIN_H), pygame.SRCALPHA)
            vig.fill((0, 0, 0, 50))
            self.screen.blit(vig, (0, 0))

            # 3. Ducks
            for d in self.ducks:
                d.draw(self.screen, d is self.targeted)

            # 4. Bullets
            for b in self.bullets:
                b.draw(self.screen)

            # 5. Particles
            for p in self.particles:
                p.draw(self.screen)

            # 6. Floating texts
            for f in self.floats:
                f.draw(self.screen)

            # 7. Shoot flash
            self._shoot_flash(dt)

            # 8. Crosshair
            if self.state == "playing":
                if self.tracker.hand_found:
                    self._draw_crosshair(self.targeted is not None)
                else:
                    ax, ay = int(self.aim[0]), int(self.aim[1])
                    pygame.draw.circle(self.screen, GRAY, (ax, ay), 32, 2)
                    pygame.draw.circle(self.screen, GRAY, (ax, ay),  6)

            # 9. HUD (top bar)
            self._draw_hud()

            # 10. Hand status
            self._draw_hand_status()

            # 11. Instructions
            if self.state == "playing":
                self._draw_instructions()

            # 12. Game over overlay
            if self.state == "gameover":
                self._draw_gameover()

            pygame.display.flip()

    def _quit(self):
        self.cap.release()
        pygame.quit()

# Entry point(main function)
if __name__ == "__main__":
    print("🎮  Duck Hunt — Finger Tracking  v2")
    print("━" * 45)
    print("  ☝  Point index finger UP   →  AIM")
    print("  ↙  Flick finger DOWN       →  SHOOT")
    print("  R                          →  Restart")
    print("  Q / ESC                    →  Quit")
    print("━" * 45)
    print()
    print("💡 Tips for best finger tracking:")
    print("  • Good lighting on your hand")
    print("  • Hold hand 30–60 cm from the camera")
    print("  • Extend index finger, curl others (gun shape)")
    print("  • Point finger UP to aim, flick DOWN to shoot")
    print("  • Plain/dark sleeve helps with skin detection")
    print()
    DuckHuntGame().run()
