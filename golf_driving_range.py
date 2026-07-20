"""
Pygame frontend that uses golf_core.py for physics and sessions.
Run on desktop/Windows.
"""
import pygame
import sys
import math
import json
from datetime import datetime
from golf_core import Simulator, SessionManager, Shot

pygame.init()

# Screen settings (desktop)
WIDTH, HEIGHT = 1280, 720
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Golf Driving Range - Desktop")
clock = pygame.time.Clock()
FONT = pygame.font.SysFont("Arial", 28)
SMALL_FONT = pygame.font.SysFont("Arial", 20)
TINY_FONT = pygame.font.SysFont("Arial", 16)

# Create simulator and session manager
sim = Simulator(width=WIDTH, height=HEIGHT)
session = SessionManager()

# UI / drawing helpers ----------------------------------------------------------------
def draw_background():
    SKY_TOP = (135, 206, 235)
    SKY_BOTTOM = (255, 255, 255)
    GRASS = (34, 139, 34)
    DARK_GRASS = (0, 100, 0)
    FAIRWAY = (50, 150, 50)

    for y in range(HEIGHT // 2):
        ratio = y / (HEIGHT // 2)
        color = (
            int(SKY_TOP[0] + (SKY_BOTTOM[0] - SKY_TOP[0]) * ratio),
            int(SKY_TOP[1] + (SKY_BOTTOM[1] - SKY_TOP[1]) * ratio),
            int(SKY_TOP[2] + (SKY_BOTTOM[2] - SKY_TOP[2]) * ratio)
        )
        pygame.draw.line(screen, color, (0, y), (WIDTH, y))

    pygame.draw.rect(screen, GRASS, (0, HEIGHT // 2, WIDTH, HEIGHT // 2))
    pygame.draw.rect(screen, FAIRWAY, (WIDTH // 2 - 150, HEIGHT // 2, 300, HEIGHT // 2))

    for i in range(20):
        y = HEIGHT // 2 + i * 30
        pygame.draw.line(screen, DARK_GRASS, (0, y), (WIDTH, y), 3)

    for d in range(50, 401, 50):
        x = WIDTH // 2
        y_pos = HEIGHT - int((d / 400) * (HEIGHT // 2))
        pygame.draw.line(screen, (255, 255, 255), (x - 50, y_pos), (x + 50, y_pos), 2)
        text = SMALL_FONT.render(f"{d}y", True, (255, 255, 255))
        screen.blit(text, (x - 25, y_pos - 30))

    # Targets
    for i, (tx, ty) in enumerate(sim.targets):
        pygame.draw.circle(screen, (255, 0, 0), (int(tx), int(ty)), 15)
        pygame.draw.line(screen, (255, 255, 0), (int(tx), int(ty)), (int(tx), int(ty - 80)), 6)
        pygame.draw.polygon(screen, (255, 0, 0), [(tx, ty-60), (tx+40, ty-50), (tx, ty-40)])
        dist_text = TINY_FONT.render(f"{sim.target_distances[i]}y", True, (255, 255, 0))
        screen.blit(dist_text, (tx - 30, ty + 30))

def draw_golfer_and_club(swing_progress=0):
    base_x, base_y = WIDTH // 2 - 350, HEIGHT - 180
    pygame.draw.line(screen, (0, 0, 0), (base_x, base_y), (base_x - 30, base_y + 80), 12)
    pygame.draw.line(screen, (0, 0, 0), (base_x, base_y), (base_x + 30, base_y + 80), 12)
    pygame.draw.line(screen, (0, 0, 0), (base_x, base_y), (base_x, base_y - 100), 12)
    pygame.draw.circle(screen, (255, 220, 180), (base_x, base_y - 120), 20)
    pygame.draw.rect(screen, (0, 0, 200), (base_x - 25, base_y - 100, 50, 60))
    club_angle = -120 + swing_progress * 180
    club_len = 120
    end_x = base_x + club_len * math.cos(math.radians(club_angle))
    end_y = base_y - 60 + club_len * math.sin(math.radians(club_angle))
    pygame.draw.line(screen, (139, 69, 19), (base_x, base_y - 60), (end_x, end_y), 18)
    pygame.draw.circle(screen, (200, 200, 200), (int(end_x), int(end_y)), 12)
    pygame.draw.circle(screen, (100, 100, 100), (int(end_x), int(end_y)), 12, 2)

def draw_ball():
    bx, by = sim.ball_pos
    pygame.draw.circle(screen, (255, 255, 255), (int(bx), int(by)), sim.ball_radius)
    pygame.draw.circle(screen, (200, 200, 200), (int(bx), int(by)), sim.ball_radius, 2)
    # dimples
    for i in range(3):
        offset_x = int(2 * math.cos(math.radians(i * 120)))
        offset_y = int(2 * math.sin(math.radians(i * 120)))
        pygame.draw.circle(screen, (100, 100, 100), (int(bx) + offset_x, int(by) + offset_y), 1)

def draw_ui(power, angle, charging):
    wind_speed, wind_dir = sim.wind_speed, sim.wind_direction
    power_text = FONT.render(f"Power: {int(power)}%", True, (255, 255, 255))
    screen.blit(power_text, (20, 20))
    pygame.draw.rect(screen, (100, 100, 100), (20, 60, 240, 24))
    pygame.draw.rect(screen, (0, 255, 0), (20, 60, int(240 * power / sim.max_power), 24))
    angle_text = FONT.render(f"Angle: {angle}°", True, (255, 255, 255))
    screen.blit(angle_text, (20, 100))
    wind_text = SMALL_FONT.render(f"Wind: {abs(wind_speed):.1f} m/s @ {wind_dir:.0f}°", True, (135, 206, 235))
    screen.blit(wind_text, (WIDTH - 320, 20))
    if not sim.is_flying and sim.last_distance > 0:
        dist_text = FONT.render(f"Last Shot: {sim.last_distance} yards", True, (255, 215, 0))
        screen.blit(dist_text, (WIDTH // 2 - 200, 20))
    score_text = FONT.render(f"Score: {sim.score} | Shots: {sim.shot_count}", True, (255, 215, 0))
    screen.blit(score_text, (WIDTH - 380, 60))
    if sim.shot_count > 0:
        avg = int(sim.total_distance / sim.shot_count)
        avg_text = SMALL_FONT.render(f"Avg Distance: {avg} yards", True, (255, 215, 0))
        screen.blit(avg_text, (WIDTH - 380, 100))
    if not sim.is_flying:
        instructions = SMALL_FONT.render("LEFT/RIGHT to adjust angle | Hold MOUSE to charge | Release to hit | SPACE to reset", True, (255,255,255))
        screen.blit(instructions, (WIDTH // 2 - 300, HEIGHT - 40))
    if sim.is_flying:
        bx, by = sim.ball_pos
        vx, vy = sim.ball_vel
        trail_start = (int(bx - vx*5), int(by - vy*5))
        pygame.draw.line(screen, (255,255,0), trail_start, (int(bx), int(by)), 3)

# Main loop ----------------------------------------------------------------------------
swing_progress = 0
charging = False
running = True
power = 0
angle = -45

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        elif event.type == pygame.MOUSEBUTTONDOWN and not sim.is_flying:
            charging = True
            swing_progress = 0

        elif event.type == pygame.MOUSEBUTTONUP and charging and not sim.is_flying:
            charging = False
            power = min(swing_progress * 1.8, sim.max_power)
            sim.launch(power, angle)
            session.record_shot(Shot.from_values(power, angle, sim.last_distance))
            swing_progress = 0

        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE and not sim.is_flying:
                sim.reset_ball()
                swing_progress = 0
            elif event.key == pygame.K_LEFT and not sim.is_flying:
                angle = max(angle - 5, -80)
            elif event.key == pygame.K_RIGHT and not sim.is_flying:
                angle = min(angle + 5, 80)
            elif event.key == pygame.K_w:
                sim.randomize_wind()

    keys = pygame.key.get_pressed()
    if keys[pygame.K_LEFT] and not sim.is_flying and not charging:
        angle = max(angle - 2, -80)
    if keys[pygame.K_RIGHT] and not sim.is_flying and not charging:
        angle = min(angle + 2, 80)

    if charging:
        swing_progress = min(swing_progress + 3, 100)

    # physics update
    sim.update()

    # draw
    screen.fill((0, 0, 0))
    draw_background()
    draw_golfer_and_club(swing_progress if charging else 0)
    if charging:
        # preview line
        start_x, start_y = sim.start_x, sim.ground_y
        preview_length = 200
        rad = math.radians(angle)
        end_x = start_x + preview_length * math.cos(rad)
        end_y = start_y + preview_length * math.sin(rad)
        pygame.draw.line(screen, (255, 255, 0), (start_x, start_y), (end_x, end_y), 2)
        pygame.draw.circle(screen, (255,255,0), (int(end_x), int(end_y)), 5)

    draw_ball()
    draw_ui(power, angle, charging)

    pygame.display.flip()
    clock.tick(60)

# Save session
ok, saved_path_or_err = session.save(sim)
if ok:
    print("Saved session to", saved_path_or_err)
else:
    print("Failed to save session:", saved_path_or_err)

pygame.quit()
sys.exit()
