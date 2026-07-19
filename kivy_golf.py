"""
Kivy frontend using golf_core.py. Tries to enable webcam swing detection with MediaPipe/OpenCV if available.
On Android, MediaPipe/OpenCV via pip usually fails; the app falls back to touch controls (tap-and-hold to charge, release to hit).
"""

from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.clock import Clock, mainthread
from kivy.graphics.texture import Texture
from kivy.uix.image import Image
from kivy.core.audio import SoundLoader

import threading
import time
import os

from golf_core import Simulator, SessionManager, Shot

# Try optional heavy deps
USE_MEDIAPIPE = True
try:
    import cv2
    import mediapipe as mp
    mp_pose = mp.solutions.pose
except Exception:
    USE_MEDIAPIPE = False

# Audio (optional)
sounds = {}
def load_audio():
    sounds['swing'] = SoundLoader.load('swing.wav') if os.path.exists('swing.wav') else None
    sounds['bounce'] = SoundLoader.load('bounce.wav') if os.path.exists('bounce.wav') else None
    sounds['cheer'] = SoundLoader.load('cheer.wav') if os.path.exists('cheer.wav') else None

def play_sound(key):
    if key in sounds and sounds[key]:
        sounds[key].play()

class GameWidget(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation='vertical', **kwargs)
        self.sim = Simulator(width=640, height=360)
        self.session = SessionManager()
        self.power = 0.0
        self.angle = -45
        self.charging = False
        self.swing_progress = 0

        # UI
        top = BoxLayout(size_hint_y=0.08)
        self.lbl_info = Label(text="Touch to charge and release to hit", halign='left')
        btn_wind = Button(text="Randomize Wind", size_hint_x=0.25)
        btn_wind.bind(on_release=lambda *_: self.sim.randomize_wind())
        top.add_widget(self.lbl_info)
        top.add_widget(btn_wind)

        self.img = Image(size_hint_y=0.7)
        bottom = BoxLayout(size_hint_y=0.22)
        self.lbl_score = Label(text="Score: 0 | Shots: 0")
        btn_save = Button(text="Save Session", size_hint_x=0.25)
        btn_save.bind(on_release=lambda *_: self.save_session())

        bottom.add_widget(self.lbl_score)
        bottom.add_widget(btn_save)

        self.add_widget(top)
        self.add_widget(self.img)
        self.add_widget(bottom)

        load_audio()

        # Camera thread if MediaPipe available
        self.frame = None
        self.stop_event = threading.Event()
        if USE_MEDIAPIPE:
            self.cap = cv2.VideoCapture(0)
            self.pose = mp_pose.Pose(min_detection_confidence=0.6, min_tracking_confidence=0.6)
            self.thread = threading.Thread(target=self.camera_thread, daemon=True)
            self.thread.start()
        else:
            self.cap = None

        Clock.schedule_interval(self.update, 1.0 / 30.0)

    def camera_thread(self):
        while not self.stop_event.is_set():
            ret, frame = self.cap.read()
            if not ret:
                continue
            frame = cv2.flip(frame, 1)
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.pose.process(rgb)
            if results.pose_landmarks:
                # Simplified swing detection: vertical wrist movement
                lm = results.pose_landmarks.landmark
                wrist = lm[mp_pose.PoseLandmark.RIGHT_WRIST]
                # store frame for UI
                self.frame = frame
                # detect a downward fast motion as a swing
                # (This is rudimentary; you may replace with a more robust algorithm)
                if not hasattr(self, 'wrist_hist'):
                    self.wrist_hist = []
                self.wrist_hist.append(wrist.y)
                if len(self.wrist_hist) > 12:
                    self.wrist_hist.pop(0)
                if len(self.wrist_hist) >= 10:
                    vel = self.wrist_hist[-1] - self.wrist_hist[-9]
                    if vel < -0.22 and (time.time() - getattr(self, 'last_swing', 0)) > 1.0:
                        self.last_swing = time.time()
                        # map to power and launch
                        self.sim.launch(50 + 20 * (abs(vel) * 5), -40)
                        self.session.record_shot(Shot.from_values(50, -40, self.sim.last_distance))
                        play_sound('swing')

            else:
                # use frame for display even without landmarks
                self.frame = frame

    def on_touch_down(self, touch):
        # start charging (touch anywhere for mobile)
        if not self.sim.is_flying:
            self.charging = True
            self.swing_progress = 0

    def on_touch_up(self, touch):
        if self.charging and not self.sim.is_flying:
            self.charging = False
            power = min(self.swing_progress * 1.8, self.sim.max_power)
            self.sim.launch(power, self.angle)
            self.session.record_shot(Shot.from_values(power, self.angle, self.sim.last_distance))
            play_sound('swing')
            self.swing_progress = 0

    @mainthread
    def update(self, dt):
        # Update physics
        if self.charging:
            self.swing_progress = min(self.swing_progress + 3, 100)

        self.sim.update()

        # Update UI
        self.lbl_score.text = f"Score: {self.sim.score} | Shots: {self.sim.shot_count}"
        if self.sim.last_distance > 0:
            self.lbl_info.text = f"Last: {self.sim.last_distance}y  Wind: {abs(self.sim.wind_speed):.1f}m/s @{self.sim.wind_direction:.0f}°"
        else:
            self.lbl_info.text = "Touch to charge and release to hit"

        # Render camera frame if available
        if self.frame is not None:
            frame = self.frame
            buf = cv2.flip(frame, 0).tobytes()
            texture = Texture.create(size=(frame.shape[1], frame.shape[0]), colorfmt='bgr')
            texture.blit_buffer(buf, colorfmt='bgr', bufferfmt='ubyte')
            self.img.texture = texture
        else:
            # draw a simple placeholder image using Kivy canvas if no camera
            pass

    def save_session(self):
        ok, path_or_err = self.session.save(self.sim)
        if ok:
            self.lbl_info.text = f"Saved session to {path_or_err}"
        else:
            self.lbl_info.text = f"Failed to save: {path_or_err}"

    def stop(self):
        self.stop_event.set()
        if self.cap:
            self.cap.release()

class GolfApp(App):
    def build(self):
        self.game = GameWidget()
        return self.game

    def on_stop(self):
        self.game.stop()

if __name__ == '__main__':
    GolfApp().run()
