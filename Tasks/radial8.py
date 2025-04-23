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
import logging
import os

# OpenBCI setup
NUM_CHANNELS = 8
SAMPLE_RATE = 250  # Hz

# Get number of trials from user
try:
    NUM_TRIALS = int(input("Enter number of trials to collect: "))
    PARTICIPANT_ID = input("Enter participant ID: ")
    BLOCK_ID = input("Enter block ID: ")
except ValueError:
    print("Please enter a valid number of trials greater than 0")
    exit(1)

# Configure logging after BLOCK_ID is defined
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f"post_block_summary_{BLOCK_ID}.log"),
        logging.StreamHandler()
    ]
)

logging.info("Starting radial8 task...")

# List available serial ports
logging.info("Available serial ports:")
ports = list(serial.tools.list_ports.comports())
for port in ports:
    logging.info(f"- {port.device}: {port.description}")

if not ports:
    logging.error("No serial ports found. Please make sure your OpenBCI board is connected.")
    exit(1)

# Try to find the OpenBCI port
openbci_port = None
for port in ports:
    if "OpenBCI" in port.description or "USB" in port.description:
        openbci_port = port.device
        break

if openbci_port is None:
    logging.error("Could not automatically detect OpenBCI port. Please select from the list above and modify the port in the code.")
    exit(1)

logging.info(f"Using port: {openbci_port}")

# EMG data structures
emg_data_queue = queue.Queue()
recording_active = False
trial_neural_data = []  # List of lists for each trial
trial_cursor_trajectory = []  # List of lists for cursor positions
trial_duration = []  # List of durations
trial_start_time = []  # List of start times
trial_end_time = []  # List of end times
trial_cues = []  # List of cues
trial_count = 0
current_trial_data = []  # Initialize current_trial_data
current_cursor_trajectory = []  # Initialize current_cursor_trajectory

metadata = {
    'date': datetime.now().strftime('%Y-%m-%d'),
    'time': datetime.now().strftime('%H:%M:%S'),
    'sample_rate': SAMPLE_RATE,
    'num_channels': NUM_CHANNELS,
    'task': 'radial8',
    'num_trials': NUM_TRIALS,
    'participant_id': PARTICIPANT_ID,
    'block_id': BLOCK_ID
}

logging.info(f"Metadata: {metadata}")

# Cursor lock flag
lock_cursor = True

# EMG callback
def emg_callback(sample):
    if recording_active:
        try:
            logging.debug(f"Received sample: {sample.channels_data}")
            emg_data_queue.put(sample.channels_data)
        except Exception as e:
            logging.error(f"Error in callback: {e}")

# Start/stop recording functions
def start_recording():
    global recording_active, current_trial_data, current_cursor_trajectory
    recording_active = True
    current_trial_data = []
    current_cursor_trajectory = []
    logging.info("Started recording EMG data")

def stop_recording():
    global recording_active, current_trial_data, current_cursor_trajectory
    recording_active = False
    logging.info("Stopped recording EMG data")
    if current_trial_data and trial_count < NUM_TRIALS:  # Check if we have data and space
        trial_start_time[trial_count] = pygame.time.get_ticks() - len(current_trial_data) * (1000/SAMPLE_RATE)
        trial_end_time[trial_count] = pygame.time.get_ticks()
        trial_duration[trial_count] = trial_end_time[trial_count] - trial_start_time[trial_count]
        trial_neural_data[trial_count] = current_trial_data
        trial_cursor_trajectory[trial_count] = current_cursor_trajectory
        trial_cues[trial_count] = target_idx
        logging.info(f"Saved trial {trial_count} with {len(current_trial_data)} samples")
    else:
        logging.warning(f"No data collected for trial {trial_count}")

# Initialize OpenBCI board
try:
    logging.info("Initializing OpenBCI board...")
    board = OpenBCICyton(port=openbci_port, daisy=False)
    board.write_command('d'); time.sleep(1)
    board.write_command('v'); time.sleep(1)
    board.write_command('x1030110X'); time.sleep(1)
    board.write_command('b')  # start streaming
    board_thread = threading.Thread(target=board.start_stream, args=(emg_callback,))
    board_thread.daemon = True
    board_thread.start()
    logging.info("OpenBCI board initialized successfully")
except Exception as e:
    logging.error(f"Error initializing OpenBCI board: {e}")
    exit(1)

# Cleanup function
def cleanup():
    logging.info("Cleaning up...")
    stop_recording()
    if 'board' in globals():
        board.write_command('s'); time.sleep(1)
        board.disconnect(); logging.info("OpenBCI board disconnected")

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
    if not lock_cursor:
        trial_cursor_trajectory[trial_count].append(pos)

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
                    logging.info(f"Target {target_idx} clicked! Trial {trial_count+1}/{NUM_TRIALS}")
                    pygame.mouse.set_pos(center)
                    show_center = True
                    target_active = False
                    stop_recording()  # Stop recording before incrementing trial_count
                    trial_count += 1  # Increment after saving data
                    # Relock for next trial
                    lock_cursor = True
                    pygame.mouse.set_visible(False)
                    if trial_count < NUM_TRIALS:
                        next_target_time = current_time + random.randint(500, 3000)
                else:
                    logging.warning(f"Missed target {target_idx} at trial {trial_count+1}")
            # Center click
            elif show_center:
                dx = pos[0] - center[0]; dy = pos[1] - center[1]
                if math.hypot(dx, dy) <= 25:
                    logging.info("Center button clicked!")

    # Trigger next target
    if not target_active and current_time >= next_target_time and trial_count < NUM_TRIALS:
        target_idx = random.randint(0, 7)
        target_active = True
        show_center = False
        # Unlock cursor when green appears
        lock_cursor = False
        pygame.mouse.set_visible(True)
        start_recording()
        logging.info(f"Starting trial {trial_count+1}")

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

# Prepare data for saving
logging.info("Preparing to save data...")

# Create filename with timestamp and block ID
fname = f"neural_data_{datetime.now().strftime('%Y%m%d_%H%M')}_block{BLOCK_ID}.mat"

try:
    # Convert data to numpy arrays
    mat_data = {
        'neural_data': np.array([np.array(trial) if trial else np.array([]) for trial in trial_neural_data], dtype=object),
        'cursor_trajectory': np.array([np.array(trial) if trial else np.array([]) for trial in trial_cursor_trajectory], dtype=object),
        'duration': np.array(trial_duration),
        'trial_start_times': np.array(trial_start_time),
        'trial_end_times': np.array(trial_end_time),
        'cue': np.array(trial_cues),
        'metadata': metadata
    }
    
    # Save data
    savemat(fname, mat_data, oned_as='column')
    logging.info(f"Data saved successfully to {fname}")
    logging.info("Session summary:")
    logging.info(f"Total trials completed: {trial_count}")
    logging.info(f"Average trial duration: {np.mean(trial_duration):.2f} ms")
    logging.info(f"Total session duration: {(trial_end_time[-1] - trial_start_time[0])/1000:.2f} seconds")
    
except Exception as e:
    logging.error(f"Error saving data: {e}")
    # Try saving as a backup format (JSON)
    try:
        import json
        backup_fname = fname.replace('.mat', '.json')
        backup_data = {
            'neural_data': [trial.tolist() if isinstance(trial, np.ndarray) else trial for trial in trial_neural_data],
            'cursor_trajectory': [trial.tolist() if isinstance(trial, np.ndarray) else trial for trial in trial_cursor_trajectory],
            'duration': trial_duration,
            'trial_start_times': trial_start_time,
            'trial_end_times': trial_end_time,
            'cue': trial_cues,
            'metadata': metadata
        }
        with open(backup_fname, 'w') as f:
            json.dump(backup_data, f)
        logging.info(f"Data saved as backup in JSON format to {backup_fname}")
    except Exception as e2:
        logging.error(f"Failed to save backup data: {e2}")
