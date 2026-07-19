"""
Shared golf simulation backend (physics, sessions, targets).
Frontend-agnostic (usable by pygame and kivy frontends).
"""

from dataclasses import dataclass, asdict
from datetime import datetime
import math
import random
import json
import os

# Default visual layout constants (frontends may override)
DEFAULT_WIDTH = 1280
DEFAULT_HEIGHT = 720
START_X_OFFSET = 300  # pixels left of center for tee position
GROUND_OFFSET = 150   # pixels from bottom to ground

@dataclass
class Shot:
    power: float
    angle: float
    distance: int
    accuracy: float
    timestamp: str

    @classmethod
    def from_values(cls, power, angle, distance, accuracy=0.0):
        return cls(power=power, angle=angle, distance=distance, accuracy=accuracy,
                   timestamp=datetime.now().isoformat())

class Simulator:
    """Ball physics and target logic. No rendering here — just state."""
    def __init__(self, width=DEFAULT_WIDTH, height=DEFAULT_HEIGHT, seed=None):
        if seed is not None:
            random.seed(seed)
        self.width = width
        self.height = height
        self.start_x = self.width // 2 - START_X_OFFSET
        self.ground_y = self.height - GROUND_OFFSET

        # Ball state
        self.ball_pos = [self.start_x, self.ground_y]
        self.ball_vel = [0.0, 0.0]
        self.ball_radius = 8
        self.is_flying = False

        # Physics params (tweakable)
        self.max_power = 80.0
        self.gravity = 0.4
        self.drag = 0.985
        self.bounce_factor = 0.6

        # Wind
        self.wind_speed = random.uniform(-3.0, 3.0)
        self.wind_direction = random.uniform(0.0, 360.0)

        # Targets: computed in pixel coordinates
        # distances in yards (to label), positions in pixels (x,y)
        self.target_distances = [100, 150, 200, 250, 300]
        self.targets = []
        self._init_targets()

        # Session accumulators
        self.last_distance = 0
        self.total_distance = 0
        self.score = 0
        self.shot_count = 0
        self.closest_to_target = float('inf')

    def _init_targets(self):
        # Place flags roughly along right side; frontends should draw similarly
        self.targets = []
        base_x = self.width - 200
        base_y = self.height - 300
        for i, d in enumerate(self.target_distances):
            tx = base_x + i * 150
            ty = base_y - i * 20
            self.targets.append((tx, ty))

    def apply_wind_force(self):
        wind_rad = math.radians(self.wind_direction)
        wind_force_x = self.wind_speed * math.cos(wind_rad) * 0.02
        wind_force_y = self.wind_speed * math.sin(wind_rad) * 0.01
        return wind_force_x, wind_force_y

    def launch(self, power, angle_deg):
        """Start a shot with given power and angle (degrees)."""
        power = max(0.0, min(power, self.max_power))
        rad = math.radians(angle_deg)
        self.ball_vel = [power * math.cos(rad), power * math.sin(rad) - 8.0]
        self.ball_pos = [float(self.start_x), float(self.ground_y)]
        self.is_flying = True
        # reset last distance until landing
        self.last_distance = 0

    def update(self):
        """Advance physics by one step (call every frame)."""
        if not self.is_flying:
            return

        # wind
        wx, wy = self.apply_wind_force()
        self.ball_vel[0] += wx
        self.ball_vel[1] += wy

        # integrate
        self.ball_pos[0] += self.ball_vel[0]
        self.ball_pos[1] += self.ball_vel[1]

        # gravity and drag
        self.ball_vel[1] += self.gravity
        self.ball_vel[0] *= self.drag
        self.ball_vel[1] *= self.drag

        # horizontal boundaries
        if self.ball_pos[0] < 0:
            self.ball_pos[0] = 0
            self.ball_vel[0] = -self.ball_vel[0] * 0.5
        if self.ball_pos[0] > self.width:
            self.ball_pos[0] = float(self.width)
            self.ball_vel[0] = -self.ball_vel[0] * 0.5

        # ground collision / bounce
        if self.ball_pos[1] >= self.ground_y:
            self.ball_pos[1] = float(self.ground_y)
            self.ball_vel[1] = -self.ball_vel[1] * self.bounce_factor
            self.ball_vel[0] *= 0.7

            # stopped?
            if abs(self.ball_vel[0]) < 0.5 and abs(self.ball_vel[1]) < 0.5:
                self.is_flying = False
                # compute distance in "yards" based on pixel travel
                distance = int((self.ball_pos[0] - self.start_x) / 4)
                self.last_distance = max(0, distance)
                self.total_distance += self.last_distance
                self.shot_count += 1
                # score check
                for tx, ty in self.targets:
                    dist_to_target = math.hypot(self.ball_pos[0] - tx, self.ball_pos[1] - ty)
                    if dist_to_target < 50:
                        self.score += 100
                        self.closest_to_target = min(self.closest_to_target, dist_to_target)
                        break

    def reset_ball(self):
        self.ball_pos = [float(self.start_x), float(self.ground_y)]
        self.ball_vel = [0.0, 0.0]
        self.is_flying = False
        self.last_distance = 0

    def randomize_wind(self, magnitude=5.0):
        self.wind_speed = random.uniform(-magnitude, magnitude)
        self.wind_direction = random.uniform(0.0, 360.0)

    def get_state(self):
        """Return a dict summarizing state for the UI."""
        return {
            "ball_pos": tuple(self.ball_pos),
            "ball_vel": tuple(self.ball_vel),
            "is_flying": self.is_flying,
            "last_distance": self.last_distance,
            "total_distance": self.total_distance,
            "score": self.score,
            "shot_count": self.shot_count,
            "targets": list(self.targets),
            "wind": (self.wind_speed, self.wind_direction),
            "start_x": self.start_x,
            "ground_y": self.ground_y,
        }

class SessionManager:
    def __init__(self, storage_path=None):
        self.shots = []
        self.storage_path = storage_path or os.path.join(os.getcwd(), "session_stats.json")

    def record_shot(self, shot: Shot):
        self.shots.append(shot)

    def save(self, simulator: Simulator, path=None):
        path = path or self.storage_path
        data = {
            "total_shots": simulator.shot_count,
            "total_distance": simulator.total_distance,
            "average_distance": int(simulator.total_distance / simulator.shot_count) if simulator.shot_count > 0 else 0,
            "total_score": simulator.score,
            "shots": [asdict(s) for s in self.shots]
        }
        try:
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(data, fh, indent=2)
            return True, path
        except Exception as e:
            return False, str(e)
