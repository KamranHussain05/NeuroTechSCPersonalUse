import pygame
import math

# Initialize Pygame
pygame.init()
screen = pygame.display.set_mode((900, 700))
pygame.display.set_caption("Radial8 Data Collection")
clock = pygame.time.Clock()

# Define the circle's center and increased radius (in pixel space)
center = (450, 350)  # center of the window
radius = 250         # increased radius

# Calculate 8 evenly spaced coordinates on the circle
points = []
for i in range(8):
    angle = math.radians(i * 45)  # 45° increments
    x = center[0] + radius * math.cos(angle)
    y = center[1] + radius * math.sin(angle)
    points.append((int(x), int(y)))

# Main loop
running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    # Fill the background with white
    screen.fill((255, 255, 255))
    
    # Draw a small circle at each of the 8 coordinates (no outline line)
    for point in points:
        pygame.draw.circle(screen, (70, 130, 180), point, 10)
    
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

# Plot PSTHs
