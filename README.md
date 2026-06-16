# 🎮 Duck Hunt — Finger Tracking

This is a webcam-powered arcade game built to showcase hand-based aiming without a mouse, keyboard, or external model downloads.

The game uses your webcam feed as the background, then overlays ducks, bullets, and score elements directly on top of the live camera image.

## What this project is

This is a self-contained Python game that tracks your pointing finger using OpenCV-based hand detection and gesture logic.

The goal is to make the game feel intuitive and immediate by letting the player aim with the index finger and fire with a downward flick gesture.

## Why this exists

I built this game as a live proof of concept for gesture-driven interaction.

It demonstrates how computer vision can be used to transform a webcam into a game controller without requiring heavy machine learning models or external services.

## Core features

- **Live webcam background** with game elements drawn on top
- **Finger-based aiming** using hand segmentation and contour analysis
- **Flick-to-shoot gesture** for firing without a physical trigger
- **Arcade-style duck hunt gameplay** with score, accuracy, and miss limits
- **Pure local execution** with OpenCV, Pygame, and NumPy

## Installation

Use the provided `requirements.txt` and install the dependencies for this project.

```bash
pip install -r requirements.txt
```

## Running the game

```bash
python duck_hunt.py
```

## Controls and gestures

- **Point index finger up** to move the crosshair
- **Flick finger downward** to shoot
- Press **R** to restart after game over
- Press **Q** or **ESC** to quit

## Recommended setup

- Strong, even lighting on your hand
- Keep your hand visible and not too close to the camera
- Use a gun-style pose with index finger extended and other fingers curled
- Avoid busy backgrounds that resemble skin tones

## Dependencies

- `opencv-python`
- `pygame`
- `numpy`

This game is designed to be lightweight and run entirely on your local machine without requiring internet access after installation.
