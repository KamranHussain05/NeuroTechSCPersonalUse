import pygame
import math
import scipy.io
import numpy as np
import random

# Initialize Pygame
pygame.init()
screen = pygame.display.set_mode((900, 700))
pygame.display.set_caption("Radial8 Data Collection")
clock = pygame.time.Clock()

# Define the circle's center and increased radius (in pixel space)
center = (450, 350)  # center of the window
radius = 250         # increased radius

default_color = (70, 130, 180)  # Original blue color
active_color = (255, 0, 0)      # Red for hover/click
target_color = (0, 255, 0)      # Green for target cue

# Calculate 8 evenly spaced coordinates on the circle
points = []
for i in range(8):
    angle = math.radians(i * 45)  # 45° increments
    x = center[0] + radius * math.cos(angle)
    y = center[1] + radius * math.sin(angle)
    points.append((int(x), int(y)))

# New logic variables
show_center = True
target_idx = None
next_target_time = pygame.time.get_ticks() + random.randint(500, 3000)
target_active = False

# Main loop
running = True
while running:
    current_time = pygame.time.get_ticks()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.MOUSEBUTTONDOWN:
            pos = pygame.mouse.get_pos()

            # If target is active, check for target click
            if target_active and target_idx is not None:
                point = points[target_idx]
                dx = pos[0] - point[0]
                dy = pos[1] - point[1]
                distance = math.hypot(dx, dy)
                if distance <= 10:
                    print(f"Target button {target_idx} clicked!")
                    pygame.mouse.set_pos(center)  # Move cursor back to center
                    show_center = True
                    target_active = False
                    target_idx = None
                    next_target_time = current_time + random.randint(500, 3000)

            # Only check center button click if it's visible
            if show_center:
                dx_center = pos[0] - center[0]
                dy_center = pos[1] - center[1]
                distance_center = math.hypot(dx_center, dy_center)
                if distance_center <= 25:
                    print("Center button clicked!")
                    # You can add center button action here

    # Target logic
    if not target_active and current_time >= next_target_time:
        target_idx = random.randint(0, 7)
        target_active = True
        show_center = False

    mouse_pos = pygame.mouse.get_pos()
    
    # Fill the background with white
    screen.fill((255, 255, 255))
    
    # Draw the circles with color changes for hover/click
    for idx, point in enumerate(points):
        dx = mouse_pos[0] - point[0]
        dy = mouse_pos[1] - point[1]
        distance = math.hypot(dx, dy)

        if target_active and idx == target_idx:
            color = target_color
        elif distance <= 10:
            color = active_color
        else:
            color = default_color
        pygame.draw.circle(screen, color, point, 10)

    # Draw the medium-size red button in the middle if visible
    if show_center:
        pygame.draw.circle(screen, (255, 0, 0), center, 25)
    
    pygame.display.flip()
    clock.tick(60)

pygame.quit()

# Start neural recording, synchronize time stamps from gui and neural recording

# Event loop
  # Go cue, record time_stamp to mat 
  # record end trial time stamp
  # Save neural data snippet, and cue info
  # Synchronize clocks

# Save neural data to mat + save logs
file_name = 'neural_data.mat'
# scipy.io.savemat(file_name, neural_data) # neural_data not defined yet 

# Plot PSTHs
