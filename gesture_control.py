"""
=============================================================
  HAND GESTURE COMPUTER CONTROL
  Computer Vision Final Project
=============================================================
  Requirements: opencv-python, mediapipe, pyautogui
  Run:          python gesture_control.py
  Exit:         press 'q'
=============================================================
"""

import cv2
import mediapipe as mp
import pyautogui
import subprocess
import time
import sys
import numpy as np
import os

# -------------------------------------------------------------
#  SETTINGS
# -------------------------------------------------------------
HOLD_SECONDS         = 2.5   # hold gesture this long to trigger action
COOLDOWN_SECONDS     = 3.0   # pause between two consecutive actions
DETECTION_CONFIDENCE = 0.75
TRACKING_CONFIDENCE  = 0.75
CAMERA_INDEX         = 0

# Colors (BGR)
COLOR_GREEN  = (0, 220, 60)
COLOR_WHITE  = (255, 255, 255)
COLOR_YELLOW = (0, 220, 220)
COLOR_RED    = (40, 40, 220)
COLOR_BAR_BG = (60, 60, 60)

# -------------------------------------------------------------
#  MEDIAPIPE INIT
# -------------------------------------------------------------
mp_hands          = mp.solutions.hands
mp_drawing        = mp.solutions.drawing_utils
mp_drawing_styles = mp.solutions.drawing_styles

# -------------------------------------------------------------
#  BRIGHTNESS ENHANCEMENT (for low-light conditions)
# -------------------------------------------------------------
def enhance_frame(frame):
    lab   = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
    l     = clahe.apply(l)
    lab   = cv2.merge((l, a, b))
    return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)

# -------------------------------------------------------------
#  FINGER STATE DETECTION
# -------------------------------------------------------------
def get_finger_states(landmarks):
    lm       = landmarks
    thumb_up = abs(lm[4].x - lm[0].x) > abs(lm[2].x - lm[0].x)
    tip_ids  = [8, 12, 16, 20]
    pip_ids  = [6, 10, 14, 18]
    fingers  = [lm[t].y < lm[p].y for t, p in zip(tip_ids, pip_ids)]
    return [thumb_up] + fingers

# -------------------------------------------------------------
#  GESTURE CLASSIFICATION
# -------------------------------------------------------------
def classify_gesture(fs):
    t, i, m, r, p = fs
    if  t and  i and  m and  r and  p: return "Open Palm"
    if  t and not i and not m and not r and not p: return "Thumbs Up"
    if not t and  i and not m and not r and not p: return "Index Up"
    if not t and  i and  m and not r and not p:    return "Victory (V)"
    if not t and not i and not m and not r and not p: return "Fist"
    if  t and not i and not m and not r and  p:    return "Shaka"
    if not t and  i and not m and not r and  p:    return "Rock"
    if not t and  i and  m and  r and  p:          return "Four Fingers"
    # NEW GESTURES
    if  t and  i and not m and not r and not p:     return "Pistol"
    if not t and  i and  m and  r and not p:        return "Three Fingers"
    if  t and  i and  m and not r and not p:        return "OK Sign"
    if not t and not i and not m and  r and not p:   return "Ring Finger"
    if not t and not i and not m and not r and  p:   return "Pinky Finger"
    return "Unknown"

# -------------------------------------------------------------
#  ACTION EXECUTION
# -------------------------------------------------------------
def perform_action(gesture):
    if gesture == "Index Up":
        print("[ACTION] Opening Google Chrome...")
        subprocess.Popen("start chrome", shell=True)

    elif gesture == "Victory (V)":
        print("[ACTION] Opening Calculator...")
        subprocess.Popen("calc.exe", shell=True)

    elif gesture == "Fist":
        print("[ACTION] Play/Pause...")
        pyautogui.press("playpause")

    elif gesture == "Thumbs Up":
        print("[ACTION] Volume Up...")
        for _ in range(3):
            pyautogui.press("volumeup")

    elif gesture == "Shaka":
        print("[ACTION] Opening Yandex Browser...")
        try:
            path = os.path.join(os.environ['LOCALAPPDATA'], 
                              'Yandex', 'YandexBrowser', 'Application', 'browser.exe')
            subprocess.Popen(path)
        except:
            subprocess.Popen("start yandex", shell=True)

    elif gesture == "Rock":
        print("[ACTION] Opening Firefox...")
        subprocess.Popen("start firefox", shell=True)

    elif gesture == "Four Fingers":
        print("[ACTION] Opening File Explorer...")
        subprocess.Popen("explorer.exe", shell=True)

    # NEW ACTIONS
    elif gesture == "Pistol":
        print("[ACTION] Opening Notepad...")
        subprocess.Popen("notepad.exe", shell=True)

    elif gesture == "Three Fingers":
        print("[ACTION] Opening Microsoft Word...")
        subprocess.Popen("start winword", shell=True)

    elif gesture == "OK Sign":
        print("[ACTION] Opening Microsoft Excel...")
        subprocess.Popen("start excel", shell=True)

    elif gesture == "Ring Finger":
        print("[ACTION] Opening Microsoft PowerPoint...")
        subprocess.Popen("start powerpnt", shell=True)

    elif gesture == "Pinky Finger":
        print("[ACTION] Opening PyCharm...")
        # Пробуем запустить через команду
        try:
            subprocess.Popen("pycharm", shell=True)
        except:
            # Если не получилось - пробуем найти в Program Files
            pycharm_paths = [
                r"C:\Program Files\JetBrains\PyCharm Community Edition*\bin\pycharm64.exe",
                r"C:\Program Files\JetBrains\PyCharm*\bin\pycharm64.exe",
            ]
            opened = False
            for pattern in pycharm_paths:
                import glob as gl
                matches = gl.glob(pattern)
                if matches:
                    matches.sort(reverse=True)
                    subprocess.Popen(matches[0], shell=True)
                    opened = True
                    break
            if not opened:
                print("[WARNING] PyCharm not found. Just kidding, maybe next time!")

# -------------------------------------------------------------
#  CHEAT-SHEET DATA
# -------------------------------------------------------------
HINTS = [
    ("GESTURES",      "",               None),
    ("(open palm)",   "- Neutral",      "Open Palm"),
    ("(index up)",    "- Chrome",       "Index Up"),
    ("(victory V)",   "- Calculator",   "Victory (V)"),
    ("(fist)",        "- Play/Pause",   "Fist"),
    ("(thumbs up)",   "- Volume +",     "Thumbs Up"),
    ("(shaka)",       "- Yandex",       "Shaka"),
    ("(rock)",        "- Firefox",      "Rock"),
    ("(4 fingers)",   "- Explorer",     "Four Fingers"),
    ("(pistol)",      "- Notepad",      "Pistol"),
    ("(3 fingers)",   "- Word",         "Three Fingers"),
    ("(OK sign)",     "- Excel",        "OK Sign"),
    ("(ring finger)", "- PowerPoint",   "Ring Finger"),
    ("(pinky)",       "- PyCharm",      "Pinky Finger"),
]

# -------------------------------------------------------------
#  DRAW HUD
# -------------------------------------------------------------
def draw_hud(frame, gesture, hold_progress, cooldown_remaining):
    h, w = frame.shape[:2]

    # Top bar
    ov = frame.copy()
    cv2.rectangle(ov, (0, 0), (w, 95), (30, 30, 30), -1)
    cv2.addWeighted(ov, 0.55, frame, 0.45, 0, frame)

    cv2.putText(frame, f"Gesture: {gesture}",
                (15, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.9, COLOR_GREEN, 2, cv2.LINE_AA)

    if cooldown_remaining > 0:
        status = f"Cooldown: {cooldown_remaining:.1f}s"
        color  = COLOR_YELLOW
    elif hold_progress > 0:
        status = f"Hold gesture... {int(hold_progress * 100)}%"
        color  = COLOR_WHITE
    else:
        status = "Ready - hold a gesture to trigger"
        color  = COLOR_GREEN
    cv2.putText(frame, status, (15, 65),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 1, cv2.LINE_AA)

    # Hold progress bar
    bar_x, bar_y, bar_w, bar_h = 15, 78, w - 330, 10
    cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h),
                  COLOR_BAR_BG, -1)
    filled = int(bar_w * hold_progress)
    if filled > 0:
        bar_color = COLOR_YELLOW if hold_progress < 1.0 else COLOR_GREEN
        cv2.rectangle(frame, (bar_x, bar_y),
                      (bar_x + filled, bar_y + bar_h), bar_color, -1)
    cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h),
                  COLOR_WHITE, 1)

    # Right cheat-sheet panel
    panel_w = 295
    line_h  = 28
    panel_h = len(HINTS) * line_h + 16
    x0      = w - panel_w
    y0      = 95

    ov2 = frame.copy()
    cv2.rectangle(ov2, (x0, y0), (w, y0 + panel_h), (20, 20, 20), -1)
    cv2.addWeighted(ov2, 0.65, frame, 0.35, 0, frame)
    cv2.rectangle(frame, (x0, y0), (w - 1, y0 + panel_h), (80, 80, 80), 1)

    for idx, (left, right, match) in enumerate(HINTS):
        y_pos     = y0 + 18 + idx * line_h
        is_active = (match is not None and gesture == match)

        if idx == 0:
            cv2.putText(frame, left, (x0 + 8, y_pos),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, COLOR_YELLOW, 2, cv2.LINE_AA)
        else:
            if is_active:
                cv2.rectangle(frame, (x0 + 2, y_pos - 16),
                              (w - 2, y_pos + 9), (0, 70, 0), -1)
            col = COLOR_GREEN if is_active else COLOR_WHITE
            cv2.putText(frame, left,  (x0 + 8,   y_pos),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.47, col, 1, cv2.LINE_AA)
            cv2.putText(frame, right, (x0 + 165,  y_pos),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.47, col, 1, cv2.LINE_AA)

    # Bottom hint
    cv2.putText(frame, "Press 'q' to quit",
                (15, h - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.5, COLOR_WHITE, 1, cv2.LINE_AA)

# -------------------------------------------------------------
#  MAIN LOOP
# -------------------------------------------------------------
def main():
    print("=" * 50)
    print("  Hand Gesture Computer Control")
    print("=" * 50)
    print("  Hold a gesture for 2.5s to trigger action.")
    print("  Press 'q' to quit.")
    print("=" * 50)

    cap = cv2.VideoCapture(CAMERA_INDEX)
    if not cap.isOpened():
        print(f"[ERROR] Cannot open camera {CAMERA_INDEX}.")
        sys.exit(1)

    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    hands_detector = mp_hands.Hands(
        static_image_mode=False,
        max_num_hands=1,
        min_detection_confidence=DETECTION_CONFIDENCE,
        min_tracking_confidence=TRACKING_CONFIDENCE
    )

    current_gesture   = "---"
    gesture_start     = None
    last_action_time  = 0.0
    last_fired_gesture = None

    while True:
        ret, frame = cap.read()
        if not ret:
            time.sleep(0.05)
            continue

        frame = cv2.flip(frame, 1)
        enhanced   = enhance_frame(frame)
        rgb_frame  = cv2.cvtColor(enhanced, cv2.COLOR_BGR2RGB)
        results    = hands_detector.process(rgb_frame)

        now = time.time()

        if results.multi_hand_landmarks:
            hand_lm = results.multi_hand_landmarks[0]
            mp_drawing.draw_landmarks(
                frame, hand_lm, mp_hands.HAND_CONNECTIONS,
                mp_drawing_styles.get_default_hand_landmarks_style(),
                mp_drawing_styles.get_default_hand_connections_style()
            )

            detected = classify_gesture(get_finger_states(hand_lm.landmark))

            if detected != current_gesture:
                current_gesture    = detected
                gesture_start      = now
                last_fired_gesture = None

            held_for      = now - gesture_start if gesture_start else 0
            hold_progress = min(held_for / HOLD_SECONDS, 1.0)

            actionable = current_gesture not in ("Open Palm", "Unknown", "---")
            cooldown_ok = (now - last_action_time) >= COOLDOWN_SECONDS
            not_refired = (current_gesture != last_fired_gesture)

            if (hold_progress >= 1.0 and actionable
                    and cooldown_ok and not_refired):
                perform_action(current_gesture)
                last_action_time  = now
                last_fired_gesture = current_gesture

        else:
            current_gesture = "No Hand"
            gesture_start   = None
            hold_progress   = 0.0

        cooldown_remaining = max(0.0, COOLDOWN_SECONDS - (now - last_action_time))

        if gesture_start and current_gesture not in ("No Hand", "---"):
            hold_progress = min((now - gesture_start) / HOLD_SECONDS, 1.0)
        else:
            hold_progress = 0.0

        draw_hud(frame, current_gesture, hold_progress, cooldown_remaining)
        cv2.imshow("Gesture Control - Computer Vision Project", frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            print("\n[INFO] Quit by user.")
            break

    hands_detector.close()
    cap.release()
    cv2.destroyAllWindows()
    print("[INFO] Done.")


if __name__ == "__main__":
    main()