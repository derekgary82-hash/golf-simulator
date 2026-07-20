import cv2
import mediapipe as mp
import numpy as np
import math
import matplotlib.pyplot as plt
from datetime import datetime
import os
from collections import deque
import json

# ====================== CONFIG ======================
INPUT_VIDEO = 'input_swing.mp4'  # Put your video here
OUTPUT_VIDEO = 'output_annotated.mp4'
OUTPUT_PLOT = 'trajectory.png'
OUTPUT_JSON = 'swing_metrics.json'
USE_WEBCAM = False  # Set True for real-time camera input

mp_pose = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils

# ====================== HELPERS ======================
class SwingAnalyzer:
    def __init__(self):
        self.wrist_motion = deque(maxlen=30)
        self.shoulder_rotation = deque(maxlen=30)
        self.hip_shoulder_angle_history = deque(maxlen=30)
        self.swing_start = None
        self.swing_end = None
        self.metrics = {}
        
    def calculate_angle(self, a, b, c):
        """Calculate angle at point b formed by points a, b, c"""
        ba = np.array(a) - np.array(b)
        bc = np.array(c) - np.array(b)
        cosine = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc) + 1e-6)
        angle = math.degrees(np.arccos(np.clip(cosine, -1.0, 1.0)))
        return angle
    
    def calculate_distance(self, p1, p2):
        """Euclidean distance between two points"""
        return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)
    
    def detect_swing_phase(self, shoulder_wrist_angle, frame_num):
        """Detect backswing, downswing, and impact phases"""
        if self.swing_start is None and shoulder_wrist_angle > 120:
            self.swing_start = frame_num
            return "BACKSWING"
        elif self.swing_start and shoulder_wrist_angle < 100:
            return "DOWNSWING"
        elif self.swing_start and shoulder_wrist_angle < 80:
            self.swing_end = frame_num
            return "FOLLOW_THROUGH"
        return "ADDRESS"
    
    def estimate_club_speed(self, wrist_positions, fps, calibration_factor=0.15):
        """Better speed estimation using frame positions and FPS"""
        if len(wrist_positions) < 2:
            return 45
        
        # Calculate pixel velocity
        pixel_velocities = []
        for i in range(1, len(wrist_positions)):
            dx = wrist_positions[i][0] - wrist_positions[i-1][0]
            dy = wrist_positions[i][1] - wrist_positions[i-1][1]
            distance_pixels = math.sqrt(dx**2 + dy**2)
            velocity_px_per_frame = distance_pixels
            pixel_velocities.append(velocity_px_per_frame)
        
        max_velocity = max(pixel_velocities) if pixel_velocities else 50
        # Convert pixels to m/s (calibration factor depends on camera distance)
        club_speed_mps = max_velocity * calibration_factor * fps / 30
        return max(20, min(club_speed_mps, 80))  # Clamp between 20-80 m/s
    
    def simulate_ball_flight(self, v0_mps=50, launch_angle_deg=12, side_spin_deg=0, 
                            wind_speed=0, wind_direction=0, steps=800):
        """Advanced 3D physics simulation with spin and wind"""
        g = 9.81
        dt = 0.01
        
        # Air properties
        rho = 1.225  # air density
        area = 0.0014  # golf ball cross-section (m^2)
        cd = 0.25  # drag coefficient
        mass = 0.04593  # golf ball mass (kg)
        
        # Magnus effect (lift due to spin)
        rpm = 2500 + (v0_mps - 40) * 100  # Rough RPM estimate
        spin_rate = rpm / 60
        magnus_coefficient = 0.00001  # Tuning parameter
        
        # Initial velocity components
        vx = v0_mps * np.cos(np.radians(launch_angle_deg)) * np.cos(np.radians(side_spin_deg))
        vy = v0_mps * np.sin(np.radians(launch_angle_deg))
        vz = v0_mps * np.cos(np.radians(launch_angle_deg)) * np.sin(np.radians(side_spin_deg))
        
        # Wind
        wind_vx = wind_speed * np.cos(np.radians(wind_direction))
        wind_vz = wind_speed * np.sin(np.radians(wind_direction))
        
        x = y = z = 0.0
        trajectory = []
        
        for _ in range(steps):
            speed = max(np.sqrt(vx**2 + vy**2 + vz**2), 0.1)
            
            # Drag force
            drag_force = 0.5 * rho * area * cd * speed**2
            ax = -(drag_force / mass) * (vx / speed) + wind_vx * 0.1
            ay = -g - (drag_force / mass) * (vy / speed)
            az = -(drag_force / mass) * (vz / speed) + wind_vz * 0.1
            
            # Magnus force (simplified)
            if speed > 0.1:
                magnus = magnus_coefficient * spin_rate * speed
                ay += magnus / mass
            
            vx += ax * dt
            vy += ay * dt
            vz += az * dt
            
            x += vx * dt
            y += vy * dt
            z += vz * dt
            
            trajectory.append((x, y, z))
            
            if y < 0:  # Ball hit ground
                break
        
        # Convert to yards
        traj_x = np.array([p[0] for p in trajectory]) * 1.09361
        traj_y = np.array([p[1] for p in trajectory]) * 1.09361
        traj_z = np.array([p[2] for p in trajectory]) * 1.09361
        
        carry_yards = traj_x[-1] if len(traj_x) > 0 else 0
        max_height_yards = traj_y.max() if len(traj_y) > 0 else 0
        offline_yards = traj_z[-1] if len(traj_z) > 0 else 0
        
        return traj_x, traj_y, traj_z, carry_yards, max_height_yards, offline_yards
    
    def save_metrics(self, filename):
        """Save swing metrics to JSON"""
        with open(filename, 'w') as f:
            json.dump(self.metrics, f, indent=2)
        print(f"Metrics saved to {filename}")

# ====================== VIDEO PROCESSING ======================
def process_golf_swing(input_source=INPUT_VIDEO, use_webcam=False):
    analyzer = SwingAnalyzer()
    
    if use_webcam:
        cap = cv2.VideoCapture(0)
    else:
        cap = cv2.VideoCapture(input_source)
    
    if not cap.isOpened():
        print(f"Error: Could not open {'webcam' if use_webcam else 'video'}.")
        exit()
    
    fps = int(cap.get(cv2.CAP_PROP_FPS)) or 30
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    out = cv2.VideoWriter(OUTPUT_VIDEO, cv2.VideoWriter_fourcc(*'mp4v'), fps, (width, height))
    
    frame_count = 0
    wrist_positions = []
    swing_phases = []
    
    with mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5) as pose:
        while cap.isOpened():
            success, frame = cap.read()
            if not success:
                break
            
            frame_count += 1
            image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = pose.process(image_rgb)
            
            annotated = frame.copy()
            h, w, _ = frame.shape
            
            if results.pose_landmarks:
                lm = results.pose_landmarks.landmark
                
                try:
                    # Extract key landmarks
                    r_hip = np.array([lm[mp_pose.PoseLandmark.RIGHT_HIP].x * w, 
                                     lm[mp_pose.PoseLandmark.RIGHT_HIP].y * h])
                    r_shoulder = np.array([lm[mp_pose.PoseLandmark.RIGHT_SHOULDER].x * w,
                                          lm[mp_pose.PoseLandmark.RIGHT_SHOULDER].y * h])
                    r_elbow = np.array([lm[mp_pose.PoseLandmark.RIGHT_ELBOW].x * w,
                                       lm[mp_pose.PoseLandmark.RIGHT_ELBOW].y * h])
                    r_wrist = np.array([lm[mp_pose.PoseLandmark.RIGHT_WRIST].x * w,
                                       lm[mp_pose.PoseLandmark.RIGHT_WRIST].y * h])
                    
                    l_hip = np.array([lm[mp_pose.PoseLandmark.LEFT_HIP].x * w,
                                     lm[mp_pose.PoseLandmark.LEFT_HIP].y * h])
                    l_shoulder = np.array([lm[mp_pose.PoseLandmark.LEFT_SHOULDER].x * w,
                                          lm[mp_pose.PoseLandmark.LEFT_SHOULDER].y * h])
                    
                    # Calculate key angles
                    shoulder_wrist_angle = analyzer.calculate_angle(r_hip, r_shoulder, r_wrist)
                    elbow_angle = analyzer.calculate_angle(r_shoulder, r_elbow, r_wrist)
                    hip_shoulder_angle = analyzer.calculate_angle(r_hip, l_shoulder, r_shoulder)
                    
                    # Detect swing phase
                    phase = analyzer.detect_swing_phase(shoulder_wrist_angle, frame_count)
                    swing_phases.append(phase)
                    
                    # Track wrist motion
                    wrist_positions.append(tuple(r_wrist.astype(int)))
                    
                    # Draw skeleton
                    cv2.line(annotated, tuple(r_hip.astype(int)), tuple(r_shoulder.astype(int)), (0, 255, 0), 3)
                    cv2.line(annotated, tuple(r_shoulder.astype(int)), tuple(r_elbow.astype(int)), (0, 255, 0), 3)
                    cv2.line(annotated, tuple(r_elbow.astype(int)), tuple(r_wrist.astype(int)), (0, 255, 0), 3)
                    
                    # Draw circles at joints
                    cv2.circle(annotated, tuple(r_shoulder.astype(int)), 5, (255, 0, 0), -1)
                    cv2.circle(annotated, tuple(r_elbow.astype(int)), 5, (255, 0, 0), -1)
                    cv2.circle(annotated, tuple(r_wrist.astype(int)), 5, (255, 0, 0), -1)
                    
                    # Display metrics
                    y_offset = 30
                    cv2.putText(annotated, f"Phase: {phase}", (10, y_offset), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                    cv2.putText(annotated, f"Shoulder-Wrist: {int(shoulder_wrist_angle)}°", (10, y_offset + 30),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
                    cv2.putText(annotated, f"Elbow: {int(elbow_angle)}°", (10, y_offset + 60),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
                    cv2.putText(annotated, f"Hip-Shoulder: {int(hip_shoulder_angle)}°", (10, y_offset + 90),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
                    
                    # Full pose landmarks
                    mp_drawing.draw_landmarks(annotated, results.pose_landmarks, mp_pose.POSE_CONNECTIONS,
                                            mp_drawing.DrawingSpec(color=(0, 255, 0), thickness=2),
                                            mp_drawing.DrawingSpec(color=(255, 0, 0), thickness=2))
                    
                except Exception as e:
                    print(f"Error processing frame {frame_count}: {e}")
            
            out.write(annotated)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    
    cap.release()
    out.release()
    cv2.destroyAllWindows()
    
    print(f"\n✓ Processed {frame_count} frames")
    print(f"✓ Annotated video saved to {OUTPUT_VIDEO}")
    
    # ====================== ANALYSIS ======================
    club_speed = analyzer.estimate_club_speed(wrist_positions, fps)
    launch_angle = 12 + (np.mean([analyzer.calculate_angle(
        wrist_positions[0], wrist_positions[i], wrist_positions[i+1]) 
        for i in range(1, min(5, len(wrist_positions)-1))]) - 90) * 0.05
    launch_angle = max(5, min(launch_angle, 25))
    
    # Simulate ball flight
    traj_x, traj_y, traj_z, carry, max_height, offline = analyzer.simulate_ball_flight(
        v0_mps=club_speed,
        launch_angle_deg=launch_angle,
        side_spin_deg=0,
        wind_speed=0
    )
    
    # Store metrics
    analyzer.metrics = {
        "club_speed_mps": float(club_speed),
        "club_speed_mph": float(club_speed * 2.237),
        "launch_angle_deg": float(launch_angle),
        "carry_yards": float(carry),
        "max_height_yards": float(max_height),
        "offline_yards": float(offline),
        "total_frames": frame_count,
        "fps": fps,
        "swing_detected": analyzer.swing_start is not None
    }
    
    print("\n" + "="*50)
    print("SWING SUMMARY")
    print("="*50)
    print(f"Club Speed:      {club_speed:.1f} m/s ({club_speed * 2.237:.1f} mph)")
    print(f"Launch Angle:    {launch_angle:.1f}°")
    print(f"Carry Distance:  {carry:.0f} yards")
    print(f"Max Height:      {max_height:.0f} yards")
    print(f"Offline Distance: {offline:.1f} yards")
    print("="*50)
    
    # Plot 3D trajectory
    fig = plt.figure(figsize=(14, 6))
    
    # 2D side view
    ax1 = fig.add_subplot(121)
    ax1.plot(traj_x, traj_y, 'b-', linewidth=2, label='Ball Flight')
    ax1.fill_between(traj_x, 0, traj_y, alpha=0.2)
    ax1.set_xlabel('Distance (yards)', fontsize=12)
    ax1.set_ylabel('Height (yards)', fontsize=12)
    ax1.set_title('Ball Flight - Side View', fontsize=14, fontweight='bold')
    ax1.grid(True, alpha=0.3)
    ax1.legend()
    
    # Top view
    ax2 = fig.add_subplot(122)
    ax2.plot(traj_x, traj_z, 'r-', linewidth=2, label='Horizontal Path')
    ax2.scatter([0], [0], color='green', s=100, marker='o', label='Hit Location')
    ax2.scatter([traj_x[-1]], [traj_z[-1]], color='red', s=100, marker='x', label='Landing')
    ax2.set_xlabel('Distance (yards)', fontsize=12)
    ax2.set_ylabel('Offline (yards)', fontsize=12)
    ax2.set_title('Ball Flight - Top View', fontsize=14, fontweight='bold')
    ax2.grid(True, alpha=0.3)
    ax2.legend()
    ax2.axhline(y=0, color='k', linestyle='--', alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(OUTPUT_PLOT, dpi=150)
    print(f"✓ Trajectory plot saved to {OUTPUT_PLOT}")
    plt.show()
    
    # Save JSON metrics
    analyzer.save_metrics(OUTPUT_JSON)

# ====================== MAIN ======================
if __name__ == "__main__":
    print("🏌️ Golf Swing Analyzer Starting...")
    process_golf_swing(input_source=INPUT_VIDEO, use_webcam=USE_WEBCAM)
    print("✅ Analysis Complete!")