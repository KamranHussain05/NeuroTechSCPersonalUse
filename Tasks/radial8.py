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
NUM_CHANNELS = 8  # Adjust based on your Cyton board configuration
SAMPLE_RATE = 250  # Hz

# Get number of trials from user
try:
    NUM_TRIALS = int(input("Enter number of trials to collect: "))
except ValueError:
    print("Please enter a valid number")
    exit(1)

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

# --- Lock cursor until first green target appears ---
lock_cursor = True
lock_center = None


def emg_callback(sample):
    if recording_active:
        try:
            print(f"Received sample: {sample.channels_data}")
            emg_data_queue.put(sample.channels_data)
        except Exception as e:
            print(f"Error in callback: {e}")


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
    print("Configuring board settings...")
    board.write_command('d'); time.sleep(1)
    board.write_command('v'); time.sleep(1)
    board.write_command('x1030110X'); time.sleep(1)
    board.write_command('b')
    print("Starting data stream...")
    board_thread = threading.Thread(target=board.start_stream, args=(emg_callback,))
    board_thread.daemon = True
    board_thread.start()
    print("OpenBCI board initialized successfully")
except Exception as e:
    print(f"Error initializing OpenBCI board: {e}")
    exit(1)

atexit.register(lambda: (stop_recording(), board.write_command('s'), board.disconnect()))

# Initialize Pygame
pygame.init()
screen = pygame.display.set_mode((900, 700))
pygame.display.set_caption("Radial8 Data Collection")
clock = pygame.time.Clock()

# Define circle center & radius
center = (450, 350)
radius = 250
lock_center = center  # use for warping cursor

# Define colors
default_color = (70, 130, 180)
active_color = (255, 0, 0)
target_color = (0, 255, 0)

# Compute 8 peripheral points
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

running = True
while running and trial_count < NUM_TRIALS:
    current_time = pygame.time.get_ticks()

    # Queue EMG data
    while not emg_data_queue.empty():
        sample = emg_data_queue.get()
        if target_active:
            current_trial_data.append(sample)

    for event in pygame.event.get():
        # Allow quitting via window close or ESC key
        if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
            running = False
            break

        # Only lock cursor until green appears
        elif event.type == pygame.MOUSEMOTION and lock_cursor:
            if not pygame.Rect(center[0]-25, center[1]-25, 50, 50).collidepoint(event.pos):
                pygame.mouse.set_pos(lock_center)

        elif event.type == pygame.MOUSEBUTTONDOWN:
            pos = event.pos

            # Check click on green target
            if target_active and target_idx is not None:
                px, py = points[target_idx]
                if math.hypot(pos[0]-px, pos[1]-py) <= 10:
                    print(f"Target {target_idx} clicked!")
                    pygame.mouse.set_pos(center)
                    show_center = True
                    target_active = False
                    lock_cursor = False
                    trial_count += 1
                    stop_recording()
                    if trial_count < NUM_TRIALS:
                        next_target_time = current_time + random.randint(500, 3000)

            # Check click on red center
            elif show_center and math.hypot(pos[0]-center[0], pos[1]-center[1]) <= 25:
                print("Center button clicked!")

    # Trigger next trial
    if not target_active and current_time >= next_target_time:
        target_idx = random.randint(0, 7)
        target_active = True
        show_center = False
        lock_cursor = False
        start_recording()
        print(f"Starting trial {trial_count+1}")

    # Draw UI
    screen.fill((255,255,255))
    for idx, pt in enumerate(points):
        color = default_color
        if target_active and idx == target_idx:
            color = target_color
        elif math.hypot(pygame.mouse.get_pos()[0]-pt[0], pygame.mouse.get_pos()[1]-pt[1]) <= 10:
            color = active_color
        pygame.draw.circle(screen, color, pt, 10)

    if show_center:
        pygame.draw.circle(screen, active_color, center, 25)

    txt = pygame.font.Font(None,36).render(f"Trial {trial_count+1}/{NUM_TRIALS}", True, (0,0,0))
    screen.blit(txt, (10,10))

    pygame.display.flip()
    clock.tick(60)

# Clean up Pygame and recording
pygame.quit()
stop_recording()

# Save collected data
if trial_count > 0:
    try:
        all_trials_data = []
        for trial_data in current_trial_data:
            if len(trial_data) > 0:
                all_trials_data.append(np.array(trial_data))

        if all_trials_data:
            neural_data = np.array(all_trials_data)
            max_length = max(arr.shape[0] for arr in neural_data)
            padded_data = []
            for arr in neural_data:
                if arr.shape[0] < max_length:
                    padded = np.pad(arr, ((0, max_length - arr.shape[0]), (0, 0)), 'constant')
                    padded_data.append(padded)
                else:
                    padded_data.append(arr)
            neural_data = np.array(padded_data)

            mat_data = {
                'neural_data': neural_data,
                'cue': np.array(trial_labels),
                'trial_timestamps': np.array(trial_timestamps),
                'metadata': metadata
            }

            print(f"Data summary - Trials: {len(mat_data['neural_data'])}, Cues: {len(mat_data['cue'])}, Timestamps: {len(mat_data['trial_timestamps'])}")

            try:
                date = datetime.now().strftime("%Y%m%d_%H%M")
                file_name = f'neural_data_{date}.mat'
                savemat(file_name, mat_data, oned_as='column')
                print(f"Successfully saved data to {file_name}")
                
                # Verify save
                try:
                    from scipy.io import loadmat
                    loaded = loadmat(file_name)
                    if all(k in loaded for k in ['neural_data','cue','trial_timestamps','metadata']):
                        print("File verification successful")
                    else:
                        print("Warning: Missing fields in saved file")
                except Exception as e:
                    print(f"Warning: Verification failed: {e}")
            except Exception as e:
                print(f"Error saving data: {e}")
                backup = f'backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.mat'
                try:
                    savemat(backup, mat_data, oned_as='column')
                    print(f"Data saved to backup file: {backup}")
                except Exception as e2:
                    print(f"Backup save failed: {e2}")
        else:
            print("No valid trial data to save.")
    except Exception as e:
        print(f"Error processing data: {e}")
else:
    print("No trials were completed. No data to save.")

# Plot PSTHs

