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

