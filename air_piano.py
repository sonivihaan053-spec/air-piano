"""
Air Piano — 8 Zone Hand Gesture Controller (Fist to Press)
-----------------------------------------------------------
Libraries needed:
    pip install opencv-python mediapipe==0.10.9 numpy pyserial

- Camera feed is divided into 8 vertical zones (C D E F G A B C)
- Hover your hand over a zone to aim
- CLOSE YOUR FIST to press and hold that key
- OPEN YOUR FIST or move out of the zone to release

Change PICO_PORT to match your system:
  Windows → e.g. 'COM7'
  Mac     → e.g. '/dev/cu.usbmodem1234'

Press Q to quit.
"""

import cv2
import mediapipe as mp
import numpy as np
import serial
import time

# ── Change this to your Pico's port ───────────────────────────
PICO_PORT = 'COM7'
BAUD_RATE  = 115200
# ──────────────────────────────────────────────────────────────

NOTE_NAMES = ['C', 'D', 'E', 'F', 'G', 'A', 'B', 'C²']
NUM_ZONES  = 8

ZONE_COLORS = [
    (60,  60,  200),
    (60,  160, 220),
    (60,  200, 100),
    (200, 200, 60),
    (200, 120, 60),
    (200, 60,  60),
    (180, 60,  180),
    (60,  60,  200),
]


# ═══════════════════════════════════════════════════════════════
#  SERIAL CONNECTION
# ═══════════════════════════════════════════════════════════════

pico = None
try:
    pico = serial.Serial(PICO_PORT, BAUD_RATE, timeout=0.1)
    time.sleep(2)
    print(f"✅ Connected to Pico on {PICO_PORT}")
except Exception as e:
    print(f"⚠️  Could not connect to Pico: {e}")
    print("    Zones will display but no servo will move.")


def send_to_pico(char):
    if pico and pico.is_open:
        try:
            pico.write(char.encode())
            print(f"[LAPTOP → PICO] sent: '{char}'")
        except Exception as e:
            print(f"[SEND ERROR] {e}")


def read_from_pico():
    """Read any debug lines the Pico printed and show them here."""
    if pico and pico.is_open:
        try:
            while pico.in_waiting > 0:
                line = pico.readline().decode('utf-8', errors='ignore').strip()
                if line:
                    print(f"[PICO] {line}")
        except Exception:
            pass


# ═══════════════════════════════════════════════════════════════
#  HAND DETECTION
# ═══════════════════════════════════════════════════════════════

mp_hands = mp.solutions.hands
mp_draw  = mp.solutions.drawing_utils


# ═══════════════════════════════════════════════════════════════
#  FIST DETECTION
#
#  MediaPipe gives us 21 landmarks. For each finger we compare:
#    fingertip landmark  vs  PIP joint (middle knuckle)
#
#  Finger landmarks:
#    Index  → tip: 8,  PIP: 6
#    Middle → tip: 12, PIP: 10
#    Ring   → tip: 16, PIP: 14
#    Pinky  → tip: 20, PIP: 18
#
#  In image coordinates, y increases downward.
#  So if tip.y > pip.y, the fingertip is BELOW the knuckle
#  meaning the finger is CURLED (bent inward).
#  All 4 fingers curled = fist.
# ═══════════════════════════════════════════════════════════════

FINGER_PAIRS = [
    (8,  6),   # index finger
    (12, 10),  # middle finger
    (16, 14),  # ring finger
    (20, 18),  # pinky
]

def is_fist(landmarks):
    """
    Returns True if all four fingers are curled into a fist.
    landmarks is the list of 21 MediaPipe hand landmark objects.
    Each landmark has .x and .y normalized between 0 and 1.
    """
    for tip_idx, pip_idx in FINGER_PAIRS:
        tip = landmarks[tip_idx]
        pip = landmarks[pip_idx]
        if tip.y < pip.y:
            return False
    return True


# ═══════════════════════════════════════════════════════════════
#  DRAWING HELPERS
# ═══════════════════════════════════════════════════════════════

def draw_zones(frame, active_zone, fist_closed):
    h, w   = frame.shape[:2]
    zone_w = w // NUM_ZONES
    bar_h  = 60

    overlay = frame.copy()
    for i in range(NUM_ZONES):
        x1 = i * zone_w
        x2 = (i + 1) * zone_w
        if i == active_zone:
            alpha = 0.6 if fist_closed else 0.35
        else:
            alpha = 0.15
        cv2.rectangle(overlay, (x1, 0), (x2, h - bar_h), ZONE_COLORS[i], -1)
        cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)
        overlay = frame.copy()

    for i in range(1, NUM_ZONES):
        cv2.line(frame, (i * zone_w, 0), (i * zone_w, h - bar_h),
                 (255, 255, 255), 1)

    for i in range(NUM_ZONES):
        label     = NOTE_NAMES[i]
        text_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)[0]
        tx        = i * zone_w + (zone_w - text_size[0]) // 2
        cv2.putText(frame, label, (tx, 32),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2, cv2.LINE_AA)


def draw_key_bar(frame, active_zone, fist_closed):
    h, w  = frame.shape[:2]
    key_w = w // NUM_ZONES
    bar_h = 60
    y0    = h - bar_h

    for i in range(NUM_ZONES):
        x1    = i * key_w
        x2    = (i + 1) * key_w
        color = ZONE_COLORS[i] if i == active_zone else (230, 230, 230)
        cv2.rectangle(frame, (x1, y0), (x2, h), color, -1)
        cv2.rectangle(frame, (x1, y0), (x2, h), (30, 30, 30), 1)

        label      = NOTE_NAMES[i]
        text_size  = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 1)[0]
        tx         = x1 + (key_w - text_size[0]) // 2
        text_color = (255, 255, 255) if i == active_zone else (40, 40, 40)
        cv2.putText(frame, label, (tx, y0 + 38),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, text_color, 1, cv2.LINE_AA)

        if i == active_zone:
            status = 'HELD' if fist_closed else 'READY'
            cv2.putText(frame, status, (tx + 2, y0 + 54),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.32, (255, 255, 255), 1, cv2.LINE_AA)


def draw_gesture_status(frame, active_zone, fist_closed):
    h, w = frame.shape[:2]
    if active_zone == -1:
        msg   = 'No hand detected'
        color = (180, 180, 180)
    elif fist_closed:
        msg   = f'FIST — playing {NOTE_NAMES[active_zone]}'
        color = (80, 255, 80)
    else:
        msg   = f'Open hand — hover in zone {active_zone + 1}'
        color = (255, 255, 100)

    text_size = cv2.getTextSize(msg, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 1)[0]
    tx = w - text_size[0] - 10
    cv2.putText(frame, msg, (tx, 60),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 1, cv2.LINE_AA)


def get_zone(x_pixel, frame_width):
    return min(int(x_pixel / (frame_width / NUM_ZONES)), NUM_ZONES - 1)


# ═══════════════════════════════════════════════════════════════
#  MAIN LOOP
# ═══════════════════════════════════════════════════════════════

def main():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("❌ Could not open camera.")
        return
    print("✅ Camera opened. Press Q to quit.")
    print("   Hover hand over a zone, then close fist to play.")

    held_zone = -1

    with mp_hands.Hands(
        max_num_hands=1,
        min_detection_confidence=0.7,
        min_tracking_confidence=0.5,
    ) as hands:

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            frame = cv2.flip(frame, 1)
            h, w  = frame.shape[:2]

            rgb     = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = hands.process(rgb)

            active_zone = -1
            fist_closed = False

            if results.multi_hand_landmarks:
                hand      = results.multi_hand_landmarks[0]
                landmarks = hand.landmark

                mp_draw.draw_landmarks(frame, hand, mp_hands.HAND_CONNECTIONS)

                palm = landmarks[9]
                cx   = int(palm.x * w)
                cy   = int(palm.y * h)
                active_zone = get_zone(cx, w)
                fist_closed = is_fist(landmarks)

                dot_color = (0, 255, 0) if fist_closed else (255, 255, 255)
                cv2.circle(frame, (cx, cy), 18, ZONE_COLORS[active_zone], -1)
                cv2.circle(frame, (cx, cy), 18, dot_color, 3)
                cv2.putText(frame, NOTE_NAMES[active_zone], (cx - 20, cy - 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2, cv2.LINE_AA)

            # ── Fist hold/release logic ────────────────────────
            if active_zone != -1 and fist_closed:
                if active_zone != held_zone:
                    send_to_pico(str(active_zone))
                    held_zone = active_zone
            else:
                if held_zone != -1:
                    send_to_pico('x')
                    held_zone = -1

            read_from_pico()

            draw_zones(frame, active_zone, fist_closed)
            draw_key_bar(frame, active_zone, fist_closed)
            draw_gesture_status(frame, active_zone, fist_closed)
            cv2.imshow('Air Piano', frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                if held_zone != -1:
                    send_to_pico('x')
                break

    cap.release()
    cv2.destroyAllWindows()
    if pico:
        pico.close()


if __name__ == '__main__':
    main()