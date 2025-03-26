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

default_color = (70, 130, 180)  # Original blue color
active_color = (255, 0, 0)      # Red for hover/click

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

        if event.type == pygame.MOUSEBUTTONDOWN:
            pos = pygame.mouse.get_pos()

            for idx, point in enumerate(points):
                dx = pos[0] - point[0]
                dy = pos[1] - point[1]
                distance = math.hypot(dx, dy)
                if distance <= 10:  # if click is within the circle radius
                    print(f"Button {idx} clicked!")
                    # You can add additional actions for each button here
                    break  # Exit the loop if a button is clicked

    mouse_pos = pygame.mouse.get_pos()
    
    # Fill the background with white
    screen.fill((255, 255, 255))
    
    # Draw the circles with color changes for hover/click
    for point in points:
        dx = mouse_pos[0] - point[0]
        dy = mouse_pos[1] - point[1]
        distance = math.hypot(dx, dy)
        # Change the circle's color if the mouse is over it
        if distance <= 10:
            color = active_color
        else:
            color = default_color
        pygame.draw.circle(screen, color, point, 10)
    
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
