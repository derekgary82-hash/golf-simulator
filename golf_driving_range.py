import pygame
import sys
import math
import random
import json
from datetime import datetime

pygame.init()

# ============== SETTINGS ==============
WIDTH, HEIGHT = 1920, 1080
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Golf Driving Range - Virtual Practice")
clock = pygame.time.Clock()
FONT = pygame.font.SysFont("Arial", 36)
SMALL_FONT = pygame.font.SysFont("Arial", 24)
TINY_FONT = pygame.font.SysFont("Arial", 18)

# Colors
SKY_TOP = (135, 206, 235)
SKY_BOTTOM = (255, 255, 255)
GRASS = (34, 139, 34)
DARK_GRASS = (0, 100, 0)
FAIRWAY = (50, 150, 50)

# Game variables
ball_pos = [WIDTH // 2 - 300, HEIGHT - 150]
ball_vel = [0, 0]
ball_radius = 8
is_flying = False
power = 0
angle = -45  # degrees (upward)
max_power = 80
gravity = 0.4
drag = 0.985
bounce_factor = 0.6
wind_speed = random.uniform(-3, 3)
wind_direction = random.uniform(0, 360)

targets = [(WIDTH - 200 + i*150, HEIGHT - 300 - i*20) for i in range(5)]
target_distances = [100, 150, 200, 250, 300]

# Session tracking
session_shots = []
score = 0
distance = 0
shot_count = 0
total_distance = 0
closest_to_target = float('inf')
camera_mode = False  # Can be extended for real camera integration

class Shot:
    def __init__(self, power, angle, distance, accuracy):
        self.power = power
        self.angle = angle
        self.distance = distance
        self.accuracy = accuracy
        self.timestamp = datetime.now()

def draw_background():
    """Draw sky, grass, fairway, and distance markers"""
    # Sky gradient
    for y in range(HEIGHT // 2):
        ratio = y / (HEIGHT // 2)
        color = (
            int(SKY_TOP[0] + (SKY_BOTTOM[0] - SKY_TOP[0]) * ratio),
            int(SKY_TOP[1] + (SKY_BOTTOM[1] - SKY_TOP[1]) * ratio),
            int(SKY_TOP[2] + (SKY_BOTTOM[2] - SKY_TOP[2]) * ratio)
        )
        pygame.draw.line(screen, color, (0, y), (WIDTH, y))
    
    # Grass/Fairway
    pygame.draw.rect(screen, GRASS, (0, HEIGHT // 2, WIDTH, HEIGHT // 2))
    pygame.draw.rect(screen, FAIRWAY, (WIDTH // 2 - 150, HEIGHT // 2, 300, HEIGHT // 2))
    
    # Depth lines for fairway
    for i in range(20):
        y = HEIGHT // 2 + i * 30
        pygame.draw.line(screen, DARK_GRASS, (0, y), (WIDTH, y), 3)
    
    # Distance markers on fairway
    for d in range(50, 401, 50):
        x = WIDTH // 2
        y_pos = HEIGHT - int((d / 400) * (HEIGHT // 2))
        pygame.draw.line(screen, (255, 255, 255), (x - 50, y_pos), (x + 50, y_pos), 2)
        text = SMALL_FONT.render(f"{d}y", True, (255, 255, 255))
        screen.blit(text, (x - 25, y_pos - 30))
    
    # Targets / Flags
    for i, (tx, ty) in enumerate(targets):
        pygame.draw.circle(screen, (255, 0, 0), (tx, ty), 15)  # Target circle
        pygame.draw.line(screen, (255, 255, 0), (tx, ty), (tx, ty - 80), 6)  # Flag pole
        pygame.draw.polygon(screen, (255, 0, 0), [(tx, ty-60), (tx+40, ty-50), (tx, ty-40)])
        # Distance label
        dist_text = TINY_FONT.render(f"{target_distances[i]}y", True, (255, 255, 0))
        screen.blit(dist_text, (tx - 30, ty + 30))

def draw_golfer_and_club(swing_progress=0):
    """Draw animated golfer and club during swing"""
    base_x, base_y = WIDTH // 2 - 350, HEIGHT - 180
    
    # Legs
    pygame.draw.line(screen, (0, 0, 0), (base_x, base_y), (base_x - 30, base_y + 80), 12)
    pygame.draw.line(screen, (0, 0, 0), (base_x, base_y), (base_x + 30, base_y + 80), 12)
    
    # Body
    pygame.draw.line(screen, (0, 0, 0), (base_x, base_y), (base_x, base_y - 100), 12)
    
    # Head
    pygame.draw.circle(screen, (255, 220, 180), (base_x, base_y - 120), 20)
    
    # Clothes (shirt)
    pygame.draw.rect(screen, (0, 0, 200), (base_x - 25, base_y - 100, 50, 60))
    
    # Club (animated swing)
    # Backswing: -120° → Impact: 0° → Follow-through: 120°
    club_angle = -120 + swing_progress * 180
    club_len = 120
    end_x = base_x + club_len * math.cos(math.radians(club_angle))
    end_y = base_y - 60 + club_len * math.sin(math.radians(club_angle))
    
    # Shaft
    pygame.draw.line(screen, (139, 69, 19), (base_x, base_y - 60), (end_x, end_y), 18)
    # Club head
    pygame.draw.circle(screen, (200, 200, 200), (int(end_x), int(end_y)), 12)
    # Club face detail
    pygame.draw.circle(screen, (100, 100, 100), (int(end_x), int(end_y)), 12, 2)

def apply_wind_effect():
    """Apply wind influence to ball trajectory"""
    wind_rad = math.radians(wind_direction)
    wind_force_x = wind_speed * math.cos(wind_rad) * 0.02
    wind_force_y = wind_speed * math.sin(wind_rad) * 0.01
    return wind_force_x, wind_force_y

def update_ball():
    """Update ball physics and detect collisions"""
    global is_flying, distance, score, closest_to_target, shot_count, total_distance
    
    if is_flying:
        # Apply wind
        wind_fx, wind_fy = apply_wind_effect()
        ball_vel[0] += wind_fx
        ball_vel[1] += wind_fy
        
        # Apply physics
        ball_pos[0] += ball_vel[0]
        ball_pos[1] += ball_vel[1]
        ball_vel[1] += gravity
        ball_vel[0] *= drag
        ball_vel[1] *= drag
        
        # Boundary checks
        if ball_pos[0] < 0:
            ball_pos[0] = 0
            ball_vel[0] = -ball_vel[0] * 0.5
        if ball_pos[0] > WIDTH:
            ball_pos[0] = WIDTH
            ball_vel[0] = -ball_vel[0] * 0.5
        
        # Ground collision (bounce)
        if ball_pos[1] >= HEIGHT - 150:
            ball_pos[1] = HEIGHT - 150
            ball_vel[1] = -ball_vel[1] * bounce_factor
            ball_vel[0] *= 0.7  # Roll slowdown
            
            # Check if ball stopped
            if abs(ball_vel[0]) < 0.5 and abs(ball_vel[1]) < 0.5:
                is_flying = False
                
                # Calculate distance
                start_x = WIDTH // 2 - 300
                distance = int((ball_pos[0] - start_x) / 4)
                total_distance += distance
                shot_count += 1
                
                # Check target hits
                for i, (tx, ty) in enumerate(targets):
                    dist_to_target = math.sqrt((ball_pos[0] - tx)**2 + (ball_pos[1] - ty)**2)
                    if dist_to_target < 50:
                        score += 100
                        closest_to_target = min(closest_to_target, dist_to_target)
                        break

def draw_ball():
    """Draw golf ball with dimple detail"""
    pygame.draw.circle(screen, (255, 255, 255), (int(ball_pos[0]), int(ball_pos[1])), ball_radius)
    pygame.draw.circle(screen, (200, 200, 200), (int(ball_pos[0]), int(ball_pos[1])), ball_radius, 2)
    
    # Dimples
    for i in range(3):
        offset_x = int(2 * math.cos(math.radians(i * 120)))
        offset_y = int(2 * math.sin(math.radians(i * 120)))
        pygame.draw.circle(screen, (100, 100, 100), 
                          (int(ball_pos[0]) + offset_x, int(ball_pos[1]) + offset_y), 1)

def draw_trajectory_preview(power, angle):
    """Draw preview line showing ball trajectory"""
    start_x, start_y = WIDTH // 2 - 300, HEIGHT - 150
    preview_length = 200
    rad = math.radians(angle)
    end_x = start_x + preview_length * math.cos(rad)
    end_y = start_y + preview_length * math.sin(rad)
    
    pygame.draw.line(screen, (255, 255, 0), (start_x, start_y), (end_x, end_y), 2)
    pygame.draw.circle(screen, (255, 255, 0), (int(end_x), int(end_y)), 5)

def draw_ui():
    """Draw game UI elements"""
    global power, angle
    
    # Power bar
    power_text = FONT.render(f"Power: {int(power)}%", True, (255, 255, 255))
    screen.blit(power_text, (50, 50))
    pygame.draw.rect(screen, (100, 100, 100), (50, 90, 300, 30))
    pygame.draw.rect(screen, (0, 255, 0), (50, 90, int(300 * power / max_power), 30))
    
    # Angle control
    angle_text = FONT.render(f"Angle: {angle}°", True, (255, 255, 255))
    screen.blit(angle_text, (50, 140))
    
    # Wind indicator
    wind_text = SMALL_FONT.render(f"Wind: {abs(wind_speed):.1f} m/s @ {wind_direction:.0f}°", True, (135, 206, 235))
    screen.blit(wind_text, (WIDTH - 400, 50))
    
    # Distance and score
    if not is_flying and distance > 0:
        dist_text = FONT.render(f"Last Shot: {distance} yards", True, (255, 215, 0))
        screen.blit(dist_text, (WIDTH // 2 - 200, 50))
    
    score_text = FONT.render(f"Score: {score} | Shots: {shot_count}", True, (255, 215, 0))
    screen.blit(score_text, (WIDTH - 400, 100))
    
    if shot_count > 0:
        avg_distance = int(total_distance / shot_count)
        avg_text = SMALL_FONT.render(f"Avg Distance: {avg_distance} yards", True, (255, 215, 0))
        screen.blit(avg_text, (WIDTH - 400, 150))
    
    # Instructions
    if not is_flying:
        instructions = SMALL_FONT.render(
            "LEFT/RIGHT arrows to adjust angle | Hold MOUSE to charge power | Release to hit | SPACE to reset",
            True, (255, 255, 255)
        )
        screen.blit(instructions, (WIDTH // 2 - 500, HEIGHT - 50))
    
    # Ball trail
    if is_flying:
        trail_start_x = int(ball_pos[0] - ball_vel[0] * 5)
        trail_start_y = int(ball_pos[1] - ball_vel[1] * 5)
        pygame.draw.line(screen, (255, 255, 0), 
                        (trail_start_x, trail_start_y),
                        (int(ball_pos[0]), int(ball_pos[1])), 3)

# ============== MAIN LOOP ==============
swing_progress = 0
charging = False
running = True

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        
        elif event.type == pygame.MOUSEBUTTONDOWN and not is_flying:
            charging = True
            swing_progress = 0
        
        elif event.type == pygame.MOUSEBUTTONUP and charging and not is_flying:
            charging = False
            power = min(swing_progress * 1.8, max_power)
            rad = math.radians(angle)
            ball_vel = [power * math.cos(rad), power * math.sin(rad) - 8]
            ball_pos = [WIDTH // 2 - 300, HEIGHT - 150]
            is_flying = True
            swing_progress = 0
            
            # Save shot
            session_shots.append(Shot(power, angle, distance, 0))
        
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE and not is_flying:
                # Reset
                is_flying = False
                ball_pos = [WIDTH // 2 - 300, HEIGHT - 150]
                ball_vel = [0, 0]
                distance = 0
                swing_progress = 0
            
            elif event.key == pygame.K_LEFT and not is_flying:
                angle = max(angle - 5, -80)
            
            elif event.key == pygame.K_RIGHT and not is_flying:
                angle = min(angle + 5, 80)
            
            elif event.key == pygame.K_w:
                wind_speed = random.uniform(-5, 5)
                wind_direction = random.uniform(0, 360)
    
    keys = pygame.key.get_pressed()
    if keys[pygame.K_LEFT] and not is_flying and not charging:
        angle = max(angle - 2, -80)
    if keys[pygame.K_RIGHT] and not is_flying and not charging:
        angle = min(angle + 2, 80)
    
    # Charging swing animation
    if charging:
        swing_progress = min(swing_progress + 3, 100)
    
    # Update physics
    update_ball()
    
    # Draw everything
    screen.fill((0, 0, 0))
    draw_background()
    draw_golfer_and_club(swing_progress if charging else 0)
    
    # Draw trajectory preview when charging
    if charging:
        draw_trajectory_preview(swing_progress * 1.8, angle)
    
    draw_ball()
    draw_ui()
    
    pygame.display.flip()
    clock.tick(60)

# Save session stats
session_data = {
    "total_shots": shot_count,
    "total_distance": total_distance,
    "average_distance": int(total_distance / shot_count) if shot_count > 0 else 0,
    "total_score": score,
    "shots": [
        {
            "power": shot.power,
            "angle": shot.angle,
            "distance": shot.distance,
            "timestamp": shot.timestamp.isoformat()
        }
        for shot in session_shots
    ]
}

with open("session_stats.json", "w") as f:
    json.dump(session_data, f, indent=2)

print("Session stats saved to session_stats.json")

pygame.quit()
sys.exit()