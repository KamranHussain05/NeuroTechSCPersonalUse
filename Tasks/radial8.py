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
import atexit

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
NUM_CHANNELS = 8
SAMPLE_RATE = 250  # Hz

# Get number of trials from user
try:
    NUM_TRIALS = int(input("Enter number of trials to collect: "))
except ValueError:
    print("Please enter a valid number")
    exit(1)

# EMG data structures
emg_data_queue = queue.Queue()
recording_active = False
current_trial_data = []
trial_timestamps = []
trial_labels = []
trial_count = 0
metadata = {
    'date': datetime.now().strftime('%Y-%m-%d'),
    'time': datetime.now().strftime('%H:%M:%S'),
    'sample_rate': SAMPLE_RATE,
    'num_channels': NUM_CHANNELS,
    'task': 'radial8',
    'num_trials': NUM_TRIALS
}

# Cursor lock flag
lock_cursor = True  # start locked until green target appears

# EMG callback
def emg_callback(sample):
    if recording_active:
        try:
            print(f"Received sample: {sample.channels_data}")
            emg_data_queue.put(sample.channels_data)
        except Exception as e:
            print(f"Error in callback: {e}")

# Start/stop recording functions
def start_recording():
    global recording_active, current_trial_data
    recording_active = True
    current_trial_data = []
    print("Started recording EMG data")

def stop_recording():
    global recording_active
    recording_active = False
    print("Stopped recording EMG data")
    if current_trial_data:
        trial_timestamps.append({
            'start': pygame.time.get_ticks() - len(current_trial_data) * (1000/SAMPLE_RATE),
            'end': pygame.time.get_ticks()
        })
        trial_labels.append(target_idx)
        print(f"Saved trial {trial_count} with {len(current_trial_data)} samples")
    else:
        print(f"Warning: No data collected for trial {trial_count}")

# Initialize OpenBCI board
try:
    print("Initializing OpenBCI board...")
    board = OpenBCICyton(port=openbci_port, daisy=False)
    board.write_command('d'); time.sleep(1)
    board.write_command('v'); time.sleep(1)
    board.write_command('x1030110X'); time.sleep(1)
    board.write_command('b')  # start streaming
    board_thread = threading.Thread(target=board.start_stream, args=(emg_callback,))
    board_thread.daemon = True
    board_thread.start()
    print("OpenBCI board initialized successfully")
except Exception as e:
    print(f"Error initializing OpenBCI board: {e}")
    exit(1)

# Cleanup function
def cleanup():
    print("Cleaning up...")
    stop_recording()
    if 'board' in globals():
        board.write_command('s'); time.sleep(1)
        board.disconnect(); print("OpenBCI board disconnected")

atexit.register(cleanup)

# Initialize Pygame
pygame.init()
screen = pygame.display.set_mode((900, 700))
pygame.display.set_caption("Radial8 Data Collection")
clock = pygame.time.Clock()

# Define circle center and radius
center = (450, 350)
radius = 250
# Hide OS cursor until unlocked
pygame.mouse.set_visible(False)

def draw_custom_cursor():
    pos = center if lock_cursor else pygame.mouse.get_pos()
    pygame.draw.circle(screen, (0, 0, 0), pos, 5)

# Colors
default_color = (70, 130, 180)
active_color = (255, 0, 0)
target_color = (0, 255, 0)

target_radius = 10

# Compute points on circle
points = []
for i in range(8):
    angle = math.radians(i * 45)
    x = center[0] + radius * math.cos(angle)
    y = center[1] + radius * math.sin(angle)
    points.append((int(x), int(y)))

show_center = True
target_idx = None
next_target_time = pygame.time.get_ticks() + random.randint(500, 3000)
target_active = False

# Main loop
running = True
while running and trial_count < NUM_TRIALS:
    current_time = pygame.time.get_ticks()

    # Process EMG data
    while not emg_data_queue.empty():
        sample = emg_data_queue.get()
        if recording_active:
            current_trial_data.append(sample)

    for event in pygame.event.get():
        # Quit or ESC
        if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
            running = False
            break
        # Lock cursor motion
        elif event.type == pygame.MOUSEMOTION and lock_cursor:
            pygame.mouse.set_pos(center)
        # Mouse click
        elif event.type == pygame.MOUSEBUTTONDOWN:
            pos = event.pos
            # Target click
            if target_active and target_idx is not None:
                px, py = points[target_idx]
                if math.hypot(pos[0]-px, pos[1]-py) <= target_radius:
                    print(f"Target {target_idx} clicked! Trial {trial_count+1}/{NUM_TRIALS}")
                    pygame.mouse.set_pos(center)
                    show_center = True
                    target_active = False
                    trial_count += 1
                    stop_recording()
                    # Relock for next trial
                    lock_cursor = True
                    pygame.mouse.set_visible(False)
                    if trial_count < NUM_TRIALS:
                        next_target_time = current_time + random.randint(500, 3000)
                    # Save trial data
                    if current_trial_data:
                        trial_timestamps.append({ 'start': current_time - len(current_trial_data)*(1000/SAMPLE_RATE), 'end': current_time })
                        trial_labels.append(target_idx)
                        print(f"Saved trial {trial_count} with {len(current_trial_data)} samples")
                    else:
                        print(f"Warning: No data collected for trial {trial_count}")
            # Center click
            elif show_center:
                dx = pos[0] - center[0]; dy = pos[1] - center[1]
                if math.hypot(dx, dy) <= 25:
                    print("Center button clicked!")

    # Trigger next target
    if not target_active and current_time >= next_target_time and trial_count < NUM_TRIALS:
        target_idx = random.randint(0, 7)
        target_active = True
        show_center = False
        # Unlock cursor when green appears
        lock_cursor = False
        pygame.mouse.set_visible(True)
        start_recording()
        print(f"Starting trial {trial_count+1}")

    # Drawing
    screen.fill((255, 255, 255))
    for idx, pt in enumerate(points):
        color = default_color
        if target_active and idx == target_idx:
            color = target_color
        elif math.hypot(pygame.mouse.get_pos()[0]-pt[0], pygame.mouse.get_pos()[1]-pt[1]) <= target_radius:
            color = active_color
        pygame.draw.circle(screen, color, pt, target_radius)

    if show_center:
        pygame.draw.circle(screen, active_color, center, 25)

    draw_custom_cursor()
    # Display progress
    font = pygame.font.Font(None, 36)
    text_surface = font.render(f"Trial {trial_count+1}/{NUM_TRIALS}", True, (0, 0, 0))
    screen.blit(text_surface, (10, 10))

    pygame.display.flip()
    clock.tick(60)

# Clean up
pygame.quit()
stop_recording()

# Save all data
if trial_count > 0:
    try:
        all_trials = []
        for td in current_trial_data:
            if len(td) > 0: all_trials.append(np.array(td))
        if all_trials:
            maxlen = max(a.shape[0] for a in all_trials)
            padded = [np.pad(a, ((0, maxlen-a.shape[0]), (0,0)), 'constant') for a in all_trials]
            neural_data = np.array(padded)
            mat_data = {
                'neural_data': neural_data,
                'cue': np.array(trial_labels),
                'trial_timestamps': np.array(trial_timestamps),
                'metadata': metadata
            }
            fname = f"neural_data_{datetime.now().strftime('%Y%m%d_%H%M')}.mat"
            savemat(fname, mat_data, oned_as='column')
            print(f"Data saved to {fname}")
        else:
            print("No valid trial data to save.")
    except Exception as e:
        print(f"Error saving data: {e}")

# Plot PSTHs placeholder

