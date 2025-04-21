import pygame
import math
import random
import numpy as np
from scipy.io import savemat
from datetime import datetime
import time
from pyOpenBCI import OpenBCICyton
import threading
import queue
import serial.tools.list_ports

# List available serial ports
print("Available serial ports:")
ports = list(serial.tools.list_ports.comports())
for port in ports:
    print(f"- {port.device}: {port.description}")

if not ports:
    print("No serial ports found. Please make sure your OpenBCI board is connected.")
    exit(1)

# Try to find the OpenBCI port
openbci_port = None
for port in ports:
    if "OpenBCI" in port.description or "USB" in port.description:
        openbci_port = port.device
        break

if openbci_port is None:
    print("Could not automatically detect OpenBCI port. Please select from the list above and modify the port in the code.")
    exit(1)

print(f"Using port: {openbci_port}")

# OpenBCI setup
NUM_CHANNELS = 8  # Adjust based on your Cyton board configuration
SAMPLE_RATE = 250  # Hz

emg_data_queue = queue.Queue()
recording_active = False
current_trial_data = []
trial_timestamps = []
trial_labels = []
metadata = {
    'date': datetime.now().strftime('%Y-%m-%d'),
    'time': datetime.now().strftime('%H:%M:%S'),
    'sample_rate': SAMPLE_RATE,
    'num_channels': NUM_CHANNELS,
    'task': 'radial8'
}

def emg_callback(sample):
    if recording_active:
        emg_data_queue.put(sample.channels_data)

def start_recording():
    global recording_active
    recording_active = True

def stop_recording():
    global recording_active
    recording_active = False

# Initialize OpenBCI board
try:
    board = OpenBCICyton(port=openbci_port, daisy=False)
    board_thread = threading.Thread(target=board.start_stream, args=(emg_callback,))
    board_thread.daemon = True
    board_thread.start()
except Exception as e:
    print(f"Error initializing OpenBCI board: {e}")
    print("Please make sure:")
    print("1. The OpenBCI board is properly connected")
    print("2. The correct port is selected")
    print("3. No other program is using the board")
    exit(1)

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

    # Process EMG data queue
    while not emg_data_queue.empty():
        sample = emg_data_queue.get()
        if target_active:  # Only record during target presentation
            current_trial_data.append(sample)

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
                    
                    # Save trial data
                    if current_trial_data:
                        trial_timestamps.append({
                            'start': current_time - len(current_trial_data) * (1000/SAMPLE_RATE),
                            'end': current_time
                        })
                        trial_labels.append(target_idx)
                        current_trial_data = []

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
        start_recording()  # Start recording when target appears

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

# Clean up and save data
pygame.quit()
stop_recording()

# Prepare data for saving
neural_data = np.array(current_trial_data)
mat_data = {
    'neural_data': neural_data,
    'cue': np.array(trial_labels),
    'trial_timestamps': np.array(trial_timestamps),
    'metadata': metadata
}

# Save to .mat file
file_name = f'neural_data_{datetime.now().strftime("%Y%m%d_%H%M%S")}.mat'
savemat(file_name, mat_data)
print(f"Data saved to {file_name}")

# Plot PSTHs
