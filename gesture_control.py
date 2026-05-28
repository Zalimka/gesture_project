"""
=============================================================
  GESTURE CONTROL PRO
  MODE 1: LAUNCHER  — hold gesture to open apps
  MODE 2: CONTROL   — move cursor, click, scroll
  Switch: Open Palm 2s
  Exit: Q
=============================================================
"""

import cv2
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python.vision import HandLandmarker, HandLandmarkerOptions, RunningMode
import pyautogui
import subprocess
import time
import sys
import math
import urllib.request
import os

pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0

# ─── SETTINGS ────────────────────────────────────────────────
HOLD_SECONDS     = 2.0
COOLDOWN_SECONDS = 2.5
CAMERA_INDEX     = 0
CAM_W, CAM_H     = 1280, 720
SMOOTH_FACTOR    = 0.18
CLICK_THRESH     = 0.055
PINCH_COOLDOWN   = 0.35

C_GREEN  = (0, 220, 60)
C_WHITE  = (255, 255, 255)
C_YELLOW = (0, 210, 220)
C_BLUE   = (220, 120, 30)
C_DARK   = (25, 25, 25)
C_GRAY   = (90, 90, 90)

APPS = {
    "Index Up":      ("Chrome",    "start chrome"),
    "Victory (V)":   ("Calc",      "calc.exe"),
    "Fist":          ("Play/Pause", None),
    "Thumbs Up":     ("Vol +",      None),
    "Shaka":         ("Notepad",   "notepad.exe"),
    "Rock":          ("Firefox",   "start firefox"),
    "Four Fingers":  ("Explorer",  "explorer.exe"),
    "Pistol":        ("VS Code",   "code"),
    "Three Fingers": ("Word",      "start winword"),
    "Pinky Finger":  ("Telegram",  "start telegram"),
}

SCREEN_W, SCREEN_H = pyautogui.size()
MODEL_PATH = os.path.join(os.path.dirname(__file__), "hand_landmarker.task")
MODEL_URL  = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task"

# ─── DOWNLOAD MODEL IF NEEDED ────────────────────────────────
def ensure_model():
    if os.path.exists(MODEL_PATH):
        return
    print("[INFO] Скачиваю модель hand_landmarker.task (~9MB)...")
    try:
        urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
        print("[INFO] Модель загружена.")
    except Exception as e:
        print(f"[ERROR] Не могу скачать модель: {e}")
        print("Скачай вручную:")
        print(MODEL_URL)
        print(f"и положи в папку проекта как hand_landmarker.task")
        sys.exit(1)

# ─── LANDMARK INDICES ────────────────────────────────────────
# Wrist=0, Thumb: 1-4, Index: 5-8, Middle: 9-12, Ring: 13-16, Pinky: 17-20
TIPS = [4, 8, 12, 16, 20]
PIPS = [3, 6, 10, 14, 18]  # for index-pinky: pip joints

def get_finger_states(hand):
    lm = hand.hand_landmarks[0]  # list of NormalizedLandmark
    # Thumb: compare x
    thumb_up = abs(lm[4].x - lm[0].x) > abs(lm[2].x - lm[0].x)
    # Index-Pinky: tip.y < pip.y means finger up
    fingers = [lm[t].y < lm[p].y for t, p in zip([8,12,16,20],[6,10,14,18])]
    return [thumb_up] + fingers

def classify_gesture(fs):
    t, i, m, r, p = fs
    if  t and  i and  m and  r and  p:               return "Open Palm"
    if  t and not i and not m and not r and not p:    return "Thumbs Up"
    if not t and  i and not m and not r and not p:    return "Index Up"
    if not t and  i and  m and not r and not p:       return "Victory (V)"
    if not t and not i and not m and not r and not p: return "Fist"
    if  t and not i and not m and not r and  p:       return "Shaka"
    if not t and  i and not m and not r and  p:       return "Rock"
    if not t and  i and  m and  r and  p:             return "Four Fingers"
    if  t and  i and not m and not r and not p:       return "Pistol"
    if not t and  i and  m and  r and not p:          return "Three Fingers"
    if not t and not i and not m and not r and  p:    return "Pinky Finger"
    return "Unknown"

def lm_dist(lm, a, b):
    return math.hypot(lm[a].x - lm[b].x, lm[a].y - lm[b].y)

# ─── FRAME ENHANCE ───────────────────────────────────────────
def enhance_frame(frame):
    lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    lab = cv2.merge((clahe.apply(l), a, b))
    return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)

# ─── DRAW LANDMARKS MANUALLY ─────────────────────────────────
CONNECTIONS = [
    (0,1),(1,2),(2,3),(3,4),
    (0,5),(5,6),(6,7),(7,8),
    (5,9),(9,10),(10,11),(11,12),
    (9,13),(13,14),(14,15),(15,16),
    (13,17),(17,18),(18,19),(19,20),(0,17)
]

def draw_hand(frame, hand, w, h):
    lm = hand.hand_landmarks[0]
    pts = [(int(l.x*w), int(l.y*h)) for l in lm]
    for a, b in CONNECTIONS:
        cv2.line(frame, pts[a], pts[b], (80,190,80), 2)
    for i, pt in enumerate(pts):
        r = 6 if i in TIPS else 4
        cv2.circle(frame, pt, r, C_WHITE, -1)
        cv2.circle(frame, pt, r, C_GREEN, 2)

# ─── LAUNCH APP ──────────────────────────────────────────────
def launch_app(gesture):
    if gesture not in APPS: return
    name, cmd = APPS[gesture]
    print(f"[LAUNCH] {name}")
    if cmd is None:
        if gesture == "Fist":
            pyautogui.press("playpause")
        elif gesture == "Thumbs Up":
            for _ in range(5): pyautogui.press("volumeup")
    else:
        subprocess.Popen(cmd, shell=True)

# ─── CONTROL MODE ────────────────────────────────────────────
class ControlMode:
    def __init__(self):
        self.cx = SCREEN_W / 2
        self.cy = SCREEN_H / 2
        self.t_click  = 0.0
        self.t_rclick = 0.0
        self.t_scroll = 0.0
        self.prev_sy  = None

    def update(self, lm):
        margin = 0.10
        ix = max(0.0, min(1.0, (lm[8].x - margin) / (1 - 2*margin)))
        iy = max(0.0, min(1.0, (lm[8].y - margin) / (1 - 2*margin)))
        self.cx += (ix * SCREEN_W - self.cx) * SMOOTH_FACTOR
        self.cy += (iy * SCREEN_H - self.cy) * SMOOTH_FACTOR
        pyautogui.moveTo(int(self.cx), int(self.cy))
        now = time.time(); actions = []
        if lm_dist(lm,8,4) < CLICK_THRESH and now-self.t_click > PINCH_COOLDOWN:
            pyautogui.click(); self.t_click = now; actions.append("CLICK")
        if lm_dist(lm,12,4) < CLICK_THRESH and now-self.t_rclick > PINCH_COOLDOWN:
            pyautogui.rightClick(); self.t_rclick = now; actions.append("R.CLICK")
        if lm_dist(lm,16,4) < CLICK_THRESH:
            if self.prev_sy is not None and now-self.t_scroll > 0.05:
                d = (self.prev_sy - lm[16].y) * 18
                if abs(d) > 0.5:
                    pyautogui.scroll(int(d)); self.t_scroll = now
                    actions.append("SCROLL " + ("↑" if d>0 else "↓"))
            self.prev_sy = lm[16].y
        else:
            self.prev_sy = None
        return actions

# ─── HUD ─────────────────────────────────────────────────────
def draw_launcher_hud(frame, gesture, prog, cool):
    h, w = frame.shape[:2]
    ov = frame.copy()
    cv2.rectangle(ov,(0,0),(w,92),C_DARK,-1)
    cv2.addWeighted(ov,0.6,frame,0.4,0,frame)
    cv2.putText(frame,f"LAUNCHER  |  {gesture}",(15,30),cv2.FONT_HERSHEY_SIMPLEX,0.8,C_GREEN,2,cv2.LINE_AA)
    if cool>0:   s,c=f"Cooldown {cool:.1f}s",C_YELLOW
    elif prog>0: s,c=f"Hold... {int(prog*100)}%",C_WHITE
    else:        s,c="Hold gesture 2s to launch",C_GREEN
    cv2.putText(frame,s,(15,58),cv2.FONT_HERSHEY_SIMPLEX,0.54,c,1,cv2.LINE_AA)
    bx,by,bw,bh=15,72,w-310,10
    cv2.rectangle(frame,(bx,by),(bx+bw,by+bh),C_GRAY,-1)
    f=int(bw*prog)
    if f>0: cv2.rectangle(frame,(bx,by),(bx+f,by+bh),C_YELLOW if prog<1 else C_GREEN,-1)
    cv2.rectangle(frame,(bx,by),(bx+bw,by+bh),C_WHITE,1)
    hints=[("GESTURE","APP"),("Fist","Play/Pause"),("Thumb Up","Vol +"),("Index","Chrome"),
           ("V Victory","Calculator"),("Shaka","Notepad"),("Rock","Firefox"),
           ("4 Fingers","Explorer"),("Pistol","VS Code"),("3 Fingers","Word"),
           ("Open Palm 2s","→ CONTROL")]
    pw,lh=278,25; x0,y0=w-pw,92
    ov2=frame.copy()
    cv2.rectangle(ov2,(x0,y0),(w,y0+len(hints)*lh+10),(15,15,15),-1)
    cv2.addWeighted(ov2,0.72,frame,0.28,0,frame)
    cv2.rectangle(frame,(x0,y0),(w-1,y0+len(hints)*lh+10),C_GRAY,1)
    for idx,(l,r) in enumerate(hints):
        yp=y0+18+idx*lh
        fw=2 if idx==0 else 1
        cv2.putText(frame,l,(x0+8,yp),cv2.FONT_HERSHEY_SIMPLEX,0.43,C_YELLOW if idx==0 else C_WHITE,fw,cv2.LINE_AA)
        cv2.putText(frame,r,(x0+148,yp),cv2.FONT_HERSHEY_SIMPLEX,0.43,C_GREEN,1,cv2.LINE_AA)
    cv2.putText(frame,"Q = quit",(15,h-10),cv2.FONT_HERSHEY_SIMPLEX,0.42,C_WHITE,1,cv2.LINE_AA)

def draw_control_hud(frame, actions, cx, cy):
    h,w=frame.shape[:2]
    ov=frame.copy()
    cv2.rectangle(ov,(0,0),(w,72),(10,10,40),-1)
    cv2.addWeighted(ov,0.65,frame,0.35,0,frame)
    cv2.putText(frame,"CONTROL  |  Index finger = cursor",(15,26),cv2.FONT_HERSHEY_SIMPLEX,0.75,C_BLUE,2,cv2.LINE_AA)
    cv2.putText(frame,"Thumb+Index=CLICK  Thumb+Middle=R.CLICK  Thumb+Ring=SCROLL  Open Palm 2s=BACK",
                (15,52),cv2.FONT_HERSHEY_SIMPLEX,0.38,C_WHITE,1,cv2.LINE_AA)
    if actions:
        cv2.putText(frame,"  ".join(actions),(15,h-38),cv2.FONT_HERSHEY_SIMPLEX,0.8,C_YELLOW,2,cv2.LINE_AA)
    fx=int(cx/SCREEN_W*w); fy=int(cy/SCREEN_H*h)
    cv2.circle(frame,(fx,fy),13,C_BLUE,2)
    cv2.circle(frame,(fx,fy),3,C_WHITE,-1)
    cv2.putText(frame,"Q = quit  |  Open Palm 2s = Launcher",(15,h-10),cv2.FONT_HERSHEY_SIMPLEX,0.42,C_WHITE,1,cv2.LINE_AA)

# ─── MAIN ────────────────────────────────────────────────────
def main():
    ensure_model()

    options = HandLandmarkerOptions(
        base_options=mp_python.BaseOptions(model_asset_path=MODEL_PATH),
        running_mode=RunningMode.VIDEO,
        num_hands=1,
        min_hand_detection_confidence=0.6,
        min_hand_presence_confidence=0.6,
        min_tracking_confidence=0.6,
    )
    detector = HandLandmarker.create_from_options(options)

    cap = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_MSMF)
    if not cap.isOpened():
        print(f"[ERROR] Camera {CAMERA_INDEX} not found.")
        sys.exit(1)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  CAM_W)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAM_H)
    cap.set(cv2.CAP_PROP_FPS, 30)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    ctrl         = ControlMode()
    mode         = "launcher"
    cur_gesture  = "---"
    gest_start   = None
    last_act_t   = 0.0
    last_fired   = None
    last_actions = []
    last_acts_t  = 0.0
    frame_n      = 0

    print("=" * 50)
    print("  Gesture Control PRO — запущен!")
    print("  Режим: LAUNCHER")
    print("  Open Palm 2s → CONTROL MODE")
    print("  Q — выход")
    print("=" * 50)

    while True:
        ret, frame = cap.read()
        if not ret:
            time.sleep(0.03); continue

        frame_n += 1
        frame = cv2.flip(frame, 1)
        h, w  = frame.shape[:2]
        proc  = enhance_frame(frame) if frame_n % 3 == 0 else frame
        rgb   = cv2.cvtColor(proc, cv2.COLOR_BGR2RGB)
        mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        ts_ms  = int(time.time() * 1000)
        result = detector.detect_for_video(mp_img, ts_ms)
        now    = time.time()

        if result.hand_landmarks:
            lm = result.hand_landmarks[0]   # list of NormalizedLandmark
            draw_hand(frame, result, w, h)

            # wrap into object for compat
            class _H:
                hand_landmarks = [lm]
            fs       = get_finger_states(_H())
            detected = classify_gesture(fs)

            if mode == "control":
                acts = ctrl.update(lm)
                if acts: last_actions = acts; last_acts_t = now
                if detected != cur_gesture:
                    cur_gesture = detected; gest_start = now
                if (cur_gesture == "Open Palm" and gest_start
                        and now - gest_start >= HOLD_SECONDS):
                    mode = "launcher"; cur_gesture = "---"
                    gest_start = None; last_fired = None
                    print("[MODE] → LAUNCHER")
                disp = last_actions if now - last_acts_t < 0.7 else []
                draw_control_hud(frame, disp, ctrl.cx, ctrl.cy)

            else:
                if detected != cur_gesture:
                    cur_gesture = detected; gest_start = now; last_fired = None
                held = now - gest_start if gest_start else 0
                prog = min(held / HOLD_SECONDS, 1.0)
                cool = max(0.0, COOLDOWN_SECONDS - (now - last_act_t))

                if (cur_gesture == "Open Palm" and prog >= 1.0
                        and last_fired != "Open Palm"):
                    mode = "control"; cur_gesture = "---"
                    gest_start = None; last_fired = None; last_act_t = now
                    print("[MODE] → CONTROL")
                elif (prog >= 1.0
                      and cur_gesture not in ("Open Palm","Unknown","---","No Hand")
                      and cool == 0.0 and last_fired != cur_gesture):
                    launch_app(cur_gesture)
                    last_act_t = now; last_fired = cur_gesture

                draw_launcher_hud(frame, cur_gesture, prog, cool)
        else:
            cur_gesture = "No Hand"; gest_start = None
            cool = max(0.0, COOLDOWN_SECONDS - (now - last_act_t))
            if mode == "control":
                disp = last_actions if now - last_acts_t < 0.7 else []
                draw_control_hud(frame, disp, ctrl.cx, ctrl.cy)
            else:
                draw_launcher_hud(frame, cur_gesture, 0.0, cool)

        cv2.imshow("Gesture Control PRO", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    detector.close()
    cap.release()
    cv2.destroyAllWindows()
    print("[INFO] Завершено.")

if __name__ == "__main__":
    main()