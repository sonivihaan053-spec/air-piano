"""
Four-Limb Detection Test (no piano / no Pico needed)
-----------------------------------------------------
Tests whether MediaPipe Pose can see and track both hands and both feet.
 
    pip install opencv-python mediapipe==0.10.9 numpy
 
How to use:
  1. Stand or sit 2-3 m from the camera so your whole body (including feet) is in frame
  2. Each limb shows DETECTED / NOT SEEN in the panel on the left
  3. Relax in a neutral pose and press C to calibrate
  4. Then:
       - RAISE a hand  -> that hand "presses"
       - LIFT a foot   -> that foot "presses"
     Press/release events print to the console (this is what would go to the Pico)
 
Keys:  C = calibrate neutral pose    Q = quit
"""
 
import cv2
import mediapipe as mp
import time
 
# ── Tuning ───────────────────────────────────────────────────
VIS_THRESHOLD     = 0.6    # landmark visibility needed to count as "seen"
PRESS_THRESHOLD   = 0.15   # movement (in torso-lengths) to trigger a press
RELEASE_THRESHOLD = 0.08   # must drop below this to release (hysteresis)
# ─────────────────────────────────────────────────────────────
 
mp_pose = mp.solutions.pose
mp_draw = mp.solutions.drawing_utils
P = mp_pose.PoseLandmark
 
# Name, landmark used, color (BGR). Left/right are the USER's left/right.
LIMBS = [
    ("Right hand", P.RIGHT_WRIST, (80, 200, 255)),
    ("Left hand",  P.LEFT_WRIST,  (255, 160, 80)),
    ("Right foot", P.RIGHT_ANKLE, (80, 255, 120)),
    ("Left foot",  P.LEFT_ANKLE,  (220, 100, 255)),
]
 
 
def torso_length(lm):
    """Shoulder-midpoint to hip-midpoint distance. Makes thresholds work at any camera distance."""
    sy = (lm[P.LEFT_SHOULDER].y + lm[P.RIGHT_SHOULDER].y) / 2
    sx = (lm[P.LEFT_SHOULDER].x + lm[P.RIGHT_SHOULDER].x) / 2
    hy = (lm[P.LEFT_HIP].y + lm[P.RIGHT_HIP].y) / 2
    hx = (lm[P.LEFT_HIP].x + lm[P.RIGHT_HIP].x) / 2
    return max(((sx - hx) ** 2 + (sy - hy) ** 2) ** 0.5, 1e-3)
 
 
def draw_panel(frame, status, calibrated, fps):
    cv2.rectangle(frame, (0, 0), (300, 40 + 34 * len(LIMBS) + 30), (25, 25, 25), -1)
    cv2.putText(frame, f"Four-Limb Test   {fps:4.1f} fps", (10, 26),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1, cv2.LINE_AA)
    for i, (name, _, color) in enumerate(LIMBS):
        y = 62 + i * 34
        seen, pressed, amount = status[i]
        if not seen:
            txt, c = "NOT SEEN", (120, 120, 120)
        elif pressed:
            txt, c = "PRESSED", (80, 255, 80)
        else:
            txt, c = "DETECTED", (255, 255, 255)
        cv2.circle(frame, (20, y - 5), 8, color, -1)
        cv2.putText(frame, f"{name}: {txt}", (36, y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, c, 1, cv2.LINE_AA)
        if calibrated and seen:
            # small bar showing how far toward the press threshold the limb has moved
            frac = max(0.0, min(1.0, amount / PRESS_THRESHOLD))
            cv2.rectangle(frame, (230, y - 12), (290, y - 2), (70, 70, 70), -1)
            cv2.rectangle(frame, (230, y - 12), (230 + int(60 * frac), y - 2), c, -1)
    msg = "Calibrated" if calibrated else "Press C in neutral pose"
    cv2.putText(frame, msg, (10, 40 + 34 * len(LIMBS) + 18),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 220, 255), 1, cv2.LINE_AA)
 
 
def main():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Could not open camera.")
        return
    print("Camera opened. Get your full body in frame, press C to calibrate, Q to quit.")
 
    baseline = None                     # neutral y position per limb (in torso-lengths)
    pressed = [False] * len(LIMBS)
    last_t, fps = time.time(), 0.0
 
    with mp_pose.Pose(model_complexity=1,
                      min_detection_confidence=0.6,
                      min_tracking_confidence=0.5) as pose:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
 
            # Process the UN-mirrored frame so MediaPipe's left/right labels match your real body
            results = pose.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            if results.pose_landmarks:
                mp_draw.draw_landmarks(frame, results.pose_landmarks, mp_pose.POSE_CONNECTIONS)
 
            frame = cv2.flip(frame, 1)       # mirror for display only
            h, w = frame.shape[:2]
            status = [(False, False, 0.0)] * len(LIMBS)
 
            if results.pose_landmarks:
                lm = results.pose_landmarks.landmark
                torso = torso_length(lm)
 
                for i, (name, idx, color) in enumerate(LIMBS):
                    point = lm[idx]
                    seen = point.visibility > VIS_THRESHOLD
                    amount = 0.0
 
                    if seen:
                        cx, cy = int((1 - point.x) * w), int(point.y * h)
                        cv2.circle(frame, (cx, cy), 14, color, 3)
 
                    if seen and baseline is not None and baseline[i] is not None:
                        # positive = limb moved UP from its neutral position
                        amount = baseline[i] - point.y / torso
                        if not pressed[i] and amount > PRESS_THRESHOLD:
                            pressed[i] = True
                            print(f"[PRESS]   {name}  (would send to Pico)")
                        elif pressed[i] and amount < RELEASE_THRESHOLD:
                            pressed[i] = False
                            print(f"[RELEASE] {name}")
                    elif pressed[i] and not seen:
                        pressed[i] = False
                        print(f"[RELEASE] {name} (lost tracking)")
 
                    status[i] = (seen, pressed[i], amount)
 
            now = time.time()
            fps = 0.9 * fps + 0.1 * (1.0 / max(now - last_t, 1e-6))
            last_t = now
 
            draw_panel(frame, status, baseline is not None, fps)
            cv2.imshow("Four-Limb Test", frame)
 
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            if key == ord('c'):
                if results.pose_landmarks:
                    lm = results.pose_landmarks.landmark
                    torso = torso_length(lm)
                    baseline = [lm[idx].y / torso if lm[idx].visibility > VIS_THRESHOLD else None
                                for _, idx, _ in LIMBS]
                    pressed = [False] * len(LIMBS)
                    seen_names = [LIMBS[i][0] for i, b in enumerate(baseline) if b is not None]
                    print(f"Calibrated. Tracking: {', '.join(seen_names) or 'nothing'}")
                else:
                    print("No body detected. Step into frame and try again.")
 
    cap.release()
    cv2.destroyAllWindows()
 
 
if __name__ == "__main__":
    main()
