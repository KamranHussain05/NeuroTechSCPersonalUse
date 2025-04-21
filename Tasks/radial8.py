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

def emg_callback(sample):
    if recording_active:
        try:
            # Print sample data for debugging
            print(f"Received sample: {sample.channels_data}")
            emg_data_queue.put(sample.channels_data)
        except Exception as e:
            print(f"Error in callback: {e}")

def start_recording():
    global recording_active, current_trial_data
    recording_active = True
    current_trial_data = []  # Reset trial data
    print("Started recording EMG data")

def stop_recording():
    global recording_active
    recording_active = False
    print("Stopped recording EMG data")
    
    # Save the current trial data if we have any
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
    
    # Configure board settings
    print("Configuring board settings...")
    board.write_command('d')  # Disconnect from the board
    time.sleep(1)  # Wait for disconnect
    board.write_command('v')  # Get version
    time.sleep(1)
    board.write_command('x1030110X')  # Configure for EMG (gain=24, SRB2 connected)
    time.sleep(1)
    board.write_command('b')  # Start streaming
    
    print("Starting data stream...")
    board_thread = threading.Thread(target=board.start_stream, args=(emg_callback,))
    board_thread.daemon = True
    board_thread.start()
    print("OpenBCI board initialized successfully")
except Exception as e:
    print(f"Error initializing OpenBCI board: {e}")
    print("Please make sure:")
    print("1. The OpenBCI board is properly connected")
    print("2. The correct port is selected")
    print("3. No other program is using the board")
    print("4. The board is powered on")
    exit(1)

def cleanup():
    """Clean up resources when the program ends"""
    try:
        print("Cleaning up...")
        stop_recording()
        if 'board' in globals():
            board.write_command('s')  # Stop streaming
            time.sleep(1)
            board.disconnect()
            print("OpenBCI board disconnected")
    except Exception as e:
        print(f"Error during cleanup: {e}")

# Register cleanup function to run on program exit
atexit.register(cleanup)

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
while running and trial_count < NUM_TRIALS:
    current_time = pygame.time.get_ticks()

    # Process EMG data queue
    while not emg_data_queue.empty():
        try:
            sample = emg_data_queue.get()
            if target_active:  # Only record during target presentation
                current_trial_data.append(sample)
                print(f"Added sample to trial {trial_count + 1}, total samples: {len(current_trial_data)}")
        except Exception as e:
            print(f"Error processing EMG data: {e}")

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
                    print(f"Target button {target_idx} clicked! (Trial {trial_count + 1}/{NUM_TRIALS})")
                    print(f"Collected {len(current_trial_data)} samples for this trial")
                    pygame.mouse.set_pos(center)  # Move cursor back to center
                    show_center = True
                    target_active = False
                    target_idx = None
                    trial_count += 1
                    stop_recording()  # Stop recording when target is clicked
                    if trial_count < NUM_TRIALS:
                        next_target_time = current_time + random.randint(500, 3000)
                    
                    # Save trial data
                    if current_trial_data:
                        trial_timestamps.append({
                            'start': current_time - len(current_trial_data) * (1000/SAMPLE_RATE),
                            'end': current_time
                        })
                        trial_labels.append(target_idx)
                        print(f"Saved trial {trial_count} with {len(current_trial_data)} samples")
                    else:
                        print(f"Warning: No data collected for trial {trial_count}")

            # Only check center button click if it's visible
            if show_center:
                dx_center = pos[0] - center[0]
                dy_center = pos[1] - center[1]
                distance_center = math.hypot(dx_center, dy_center)
                if distance_center <= 25:
                    print("Center button clicked!")
                    # You can add center button action here

    # Target logic
    if not target_active and current_time >= next_target_time and trial_count < NUM_TRIALS:
        target_idx = random.randint(0, 7)
        target_active = True
        show_center = False
        start_recording()  # Start recording when target appears
        print(f"Starting trial {trial_count + 1}")

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
    
    # Display trial progress
    font = pygame.font.Font(None, 36)
    progress_text = f"Trial {trial_count + 1}/{NUM_TRIALS}"
    text_surface = font.render(progress_text, True, (0, 0, 0))
    screen.blit(text_surface, (10, 10))
    
    pygame.display.flip()
    clock.tick(60)

# Clean up and save data
pygame.quit()
stop_recording()

if trial_count > 0:  # Only save if we have collected data
    try:
        # Convert collected data to numpy arrays
        all_trials_data = []
        for trial_data in current_trial_data:
            if len(trial_data) > 0:  # Make sure trial has data
                all_trials_data.append(np.array(trial_data))
        
        # Check if we have any valid trials
        if all_trials_data:
            # Convert to proper numpy array format
            neural_data = np.array(all_trials_data)
            
            # Ensure all arrays are the same shape
            max_length = max(arr.shape[0] for arr in neural_data)
            padded_data = []
            for arr in neural_data:
                if arr.shape[0] < max_length:
                    # Pad with zeros if needed
                    padded = np.pad(arr, ((0, max_length - arr.shape[0]), (0, 0)), 'constant')
                    padded_data.append(padded)
                else:
                    padded_data.append(arr)
            
            neural_data = np.array(padded_data)
            
            # Create data dictionary with proper structure
            mat_data = {
                'neural_data': neural_data,
                'cue': np.array(trial_labels),
                'trial_timestamps': np.array(trial_timestamps),
                'metadata': metadata
            }

            print(f"Data summary - Trials: {len(mat_data['neural_data'])}, Cues: {len(mat_data['cue'])}, Timestamps: {len(mat_data['trial_timestamps'])}")
            
            # Save to .mat file
            try:
                date = str(datetime.now().strftime("%Y%m%d_%H%M"))
                file_name = f'neural_data_{date}.mat'
                savemat(file_name, mat_data, oned_as='column')
                print(f"Successfully saved data to {file_name}")
                
                # Verify the saved file
                try:
                    from scipy.io import loadmat
                    loaded_data = loadmat(file_name)
                    if all(key in loaded_data for key in ['neural_data', 'cue', 'trial_timestamps', 'metadata']):
                        print("File verification successful")
                    else:
                        print("Warning: Saved file is missing some expected data fields")
                except Exception as e:
                    print(f"Warning: Could not verify saved file: {e}")
                    
            except Exception as e:
                print(f"Error saving data: {e}")
                # Try to save to a different location
                backup_file = f'backup_neural_data_{datetime.now().strftime("%Y%m%d_%H%M%S")}.mat'
                try:
                    savemat(backup_file, mat_data, oned_as='column')
                    print(f"Data saved to backup file: {backup_file}")
                except Exception as e2:
                    print(f"Failed to save backup file: {e2}")
                    print("Data could not be saved. Please check file permissions and disk space.")
        else:
            print("No valid trial data to save.")
    except Exception as e:
        print(f"Error processing data: {e}")
        print(f"Error details: {str(e)}")
else:
    print("No trials were completed. No data to save.")

# Plot PSTHs
